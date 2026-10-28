# /// script
# requires-python = ">=3.10"
# ///
"""Extract friction signals from local Claude Code and Codex transcripts, read-only.

Usage: uv run scripts/signals.py [--project PATH] [--days N] [--session FILE ...]
                                 [--exclude-ledger FILE] [--exclude-session ID ...]
                                 [--no-subagents] [--include-temp] [--format summary|jsonl]
                                 [--limit N] [--output FILE]

Reads, read-only:
  Claude Code  ~/.claude/projects/**/*.jsonl   (subagents in <session>/subagents/)
  Codex        $CODEX_HOME/sessions/**/*.jsonl (CODEX_HOME defaults to ~/.codex)

Scope:
  no --project      global: every session in the period
  --project PATH    sessions whose cwd is PATH, inside it, or inside one of its git
                    worktrees; Codex sessions also match on the git remote URL
  --session FILE    exactly these transcript files (ignores --project and --days)

Signals: tool_error, error_in_output (a shell error in a command that exited 0),
permission_denied, interrupted, retry_after_error, compaction and
correction_candidate (a typed message that starts like "no", "stop", "nie").
The summary adds noise lines (output lines that fill most shell results, such as
shell start-up warnings), calls before the first edit, and user text repeated
across sessions.

Skipped: sessions run in a temp folder, and the session running this script with
its subagents ($CLAUDE_CODE_SESSION_ID, or $CODEX_THREAD_ID when Codex sets it).
Quotes are redacted (tokens, keys, emails, home path) and truncated.

Options:
  --project PATH        Only sessions in this project (default: global).
  --days N              Look back N days (default: 7).
  --session FILE        A transcript file to read (repeatable).
  --exclude-ledger FILE Session IDs to skip, one per line, '#' comments allowed.
  --exclude-session ID  A session ID (or a prefix of 8+ chars) to skip (repeatable).
  --no-subagents        Skip subagent transcripts.
  --include-temp        Keep sessions run in a temp folder (skipped by default:
                        eval and baseline runs start there).
  --format FORMAT       summary (default, one JSON object) or jsonl (one signal per line).
  --limit N             Groups and examples to list in the summary (default: 25).
  --output FILE         Write to FILE instead of stdout.

Examples:
  uv run scripts/signals.py --project ~/code/app --days 7 --exclude-ledger ~/code/app/.friction/ledger.txt
  uv run scripts/signals.py --session ~/.claude/projects/-x/1234.jsonl --format jsonl

Exit codes: 0 report written, 1 bad arguments.
"""

# Transcript readers (roots, parse_time, recent_files) are copied
# from skill-review's usage.py, not imported: skills install one folder at a time.

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict

HOME = pathlib.Path.home()
CLAUDE_ROOT = HOME / ".claude" / "projects"
CODEX_ROOT = pathlib.Path(os.environ.get("CODEX_HOME", HOME / ".codex")) / "sessions"
CLAUDE_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
QUOTE_MAX = 200
KEY_MAX = 60

# Redaction: (pattern, replacement). Patterns are assembled so this file holds no real-looking secret.
DASH5 = "-" * 5
SECRET_RES = [
    (re.compile(DASH5 + r"BEGIN [A-Z ]*PRIVATE KEY" + DASH5 + r"[\s\S]*?(?:" + DASH5 + r"END [A-Z ]*PRIVATE KEY" + DASH5 + r"|$)"), "[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]{4,}){1,2}"), "[REDACTED]"),  # JWT, also after a v1. prefix
    (re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"), "[REDACTED]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "[REDACTED]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "[REDACTED]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "[REDACTED]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"), "[REDACTED]"),
    (re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|authorization|cookie)(\"?\s*[:=]\s*\"?)[^\s\"',;&]{4,}"),
     r"\1\2[REDACTED]"),
    (re.compile(r"(?i)([?&](?:code|token|key|sig|signature|access_token|state)=)[^&\s\"']+"), r"\1[REDACTED]"),
    # long opaque strings (hashes, base64) that mix letters and digits
    (re.compile(r"(?<![A-Za-z0-9+_=-])(?=[A-Za-z0-9+_=-]*\d)(?=[A-Za-z0-9+_=-]*[A-Za-z])[A-Za-z0-9+_=-]{32,}"), "[REDACTED]"),
]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HOME_RE = re.compile(re.escape(str(HOME)))

# Correction candidates: the first words of a typed user message (English and Polish).
# Polish letters are built with chr() so this file stays ASCII.
_PL = {"z'": chr(0x17A), "z.": chr(0x17C), "o'": chr(0xF3), "l/": chr(0x142)}
CORRECTION_RE = re.compile(
    r"^\W*(no\b|nope|not that|stop\b|wait\b|don'?t\b|do not\b|actually\b|wrong\b|that'?s not|"
    r"i said|i told you|i asked|why did you|again\b|instead\b|undo\b|revert\b|"
    r"nie\b|czekaj|poczekaj|[z" + _PL["z'"] + r"]le\b|przecie[z" + _PL["z."] + r"]|"
    r"m[o" + _PL["o'"] + r"]wi[l" + _PL["l/"] + r"]em|prosi[l" + _PL["l/"] + r"]em|"
    r"cofnij|znowu|jeszcze raz|zamiast|dlaczego)",
    re.IGNORECASE,
)
ERRORISH_RE = re.compile(r"(?i)error|unknown|not found|no such|denied|fail|invalid|cannot|can't|unrecognized|refused|timed? ?out")
# A shell error inside a command that still exited 0 ("bfs: error: Unknown argument").
STDERR_LINE_RE = re.compile(
    r"^[\w.()/-]+(?::\d+)*: (?:error:|.*(?:unknown argument|unrecognized option|invalid option|"
    r"illegal option|command not found|no matches found|not a git repository))", re.IGNORECASE | re.MULTILINE)
EXIT_LINE_RE = re.compile(r"^(Exit code \d+|Process exited with code \d+|Wall time.*|Output:|Script completed)$")
PATH_RE = re.compile(r"(?:~|/)[^\s:'\"`,)]+")
NUM_RE = re.compile(r"\d+")
WORD_RE = re.compile("[a-z0-9" + chr(0xC0) + "-" + chr(0x24F) + "]+")


def redact(text: str) -> str:
    text = HOME_RE.sub("~", text)
    for pattern, replacement in SECRET_RES:
        text = pattern.sub(replacement, text)
    return EMAIL_RE.sub("[EMAIL]", text)


def quote(text: str, limit: int = QUOTE_MAX) -> str:
    text = redact(" ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 3] + "..."


def normalize_key(line: str) -> str:
    line = HOME_RE.sub("~", line)
    line = PATH_RE.sub("PATH", line)
    line = NUM_RE.sub("N", line)
    return redact(" ".join(line.split()))[:KEY_MAX]


def parse_time(value) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def recent_files(root: pathlib.Path, cutoff: dt.datetime):
    if not root.is_dir():
        return
    for path in root.rglob("*.jsonl"):
        try:
            if dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc) >= cutoff:
                yield path
        except OSError:
            continue


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return "" if content is None else str(content)


def program_of(command: str) -> str:
    """First program of a shell command, skipping cd/env prefixes: 'git status', 'rg', 'find'."""
    head = re.split(r"[\"'\n]|<<", command, maxsplit=1)[0]  # quoted code and heredocs are not commands
    for segment in re.split(r"&&|\|\||;|\|", head):
        words = segment.strip().split()
        while words and re.match(r"^[A-Z_][A-Z0-9_]*=", words[0]):
            words = words[1:]
        while words and words[0] in ("then", "do", "else", "time", "sudo", "env", "!", "{", "("):
            words = words[1:]
        if not words or words[0] in ("cd", "set", "export", "source", ".", "for", "while", "until", "if",
                                     "case", "done", "fi", "esac", "}", ")"):
            continue
        name = os.path.basename(words[0])
        if name in ("git", "npm", "pnpm", "yarn", "uv", "docker", "gh", "cargo", "go", "bun", "npx", "uvx") and len(words) > 1:
            return f"{name} {words[1]}"
        return name
    return ""


class Session:
    def __init__(self, agent: str, path: pathlib.Path):
        self.agent = agent
        self.path = path
        self.id = ""
        self.parent = ""
        self.subagent = False
        self.cwds: set[str] = set()
        self.remote = ""
        self.first: dt.datetime | None = None
        self.calls = 0
        self.first_edit_at: int | None = None
        self.signals: list[dict] = []
        self.shell_outputs: list[set[str]] = []
        self.user_texts: list[str] = []
        self.errors: list[tuple[str, str, str]] = []  # (tool, raw error text, call signature)

    def touch(self, when: dt.datetime | None) -> None:
        if when and (self.first is None or when < self.first):
            self.first = when

    def edit(self) -> None:
        if self.first_edit_at is None:
            self.first_edit_at = self.calls

    def add(self, kind: str, tool: str, key: str, text: str, when: dt.datetime | None) -> None:
        self.signals.append({"type": kind, "tool": tool, "key": key, "quote": quote(text),
                             "date": when.date().isoformat() if when else ""})

    def add_shell_output(self, output: str, name: str = "", failed: bool = False,
                         when: dt.datetime | None = None) -> None:
        lines = {line.strip() for line in output.splitlines() if 10 <= len(line.strip()) <= 200}
        self.shell_outputs.append(lines)
        if not failed:
            match = STDERR_LINE_RE.search(output)
            if match:
                end = output.find("\n", match.start())
                line = output[match.start(): end if end >= 0 else len(output)]
                self.signals.append({"type": "error_in_output", "tool": name, "raw": line,
                                     "date": when.date().isoformat() if when else ""})


def read_claude(path: pathlib.Path, cutoff: dt.datetime | None) -> Session:
    session = Session("claude", path)
    session.subagent = path.parent.name == "subagents"
    session.id = path.stem
    if session.subagent:
        session.parent = path.parent.parent.name
    calls: dict[str, tuple[str, str]] = {}
    seen_tool_call = False
    with open(path, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if '"type":"user"' not in line and '"type":"assistant"' not in line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            when = parse_time(entry.get("timestamp"))
            if cutoff and (when is None or when < cutoff):
                continue
            session.touch(when)
            if entry.get("cwd"):
                session.cwds.add(entry["cwd"])
            if entry.get("isCompactSummary"):
                session.add("compaction", "", "context compacted", "context compacted", when)
                continue
            content = (entry.get("message") or {}).get("content")
            if entry.get("type") == "assistant":
                for item in content if isinstance(content, list) else []:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        name = str(item.get("name", ""))
                        tool_input = item.get("input") or {}
                        if name == "Bash":
                            name = "Bash:" + program_of(str(tool_input.get("command", "")))
                        elif name.startswith("mcp__") and name.count("__") >= 2:
                            server, tool = name[5:].split("__", 1)
                            name = f"mcp:{server}.{tool}"
                        calls[str(item.get("id"))] = (name, json.dumps(tool_input, sort_keys=True)[:2000])
                        session.calls += 1
                        seen_tool_call = True
                        if name in CLAUDE_EDIT_TOOLS:
                            session.edit()
                continue
            decision = entry.get("permissionDecision") or {}
            if isinstance(content, list) and any(isinstance(i, dict) and i.get("type") == "tool_result" for i in content):
                for item in content:
                    if not (isinstance(item, dict) and item.get("type") == "tool_result"):
                        continue
                    name, signature = calls.get(str(item.get("tool_use_id")), ("?", ""))
                    output = text_of(item.get("content"))
                    if name.startswith("Bash"):
                        session.add_shell_output(output, name, bool(item.get("is_error")), when)
                    if output.startswith("The user doesn't want to proceed"):
                        session.add("permission_denied", name, "rejected by user", output[:120], when)
                    elif isinstance(decision, dict) and decision.get("decision") == "reject":
                        session.add("permission_denied", name, "rejected by " + str(decision.get("reasonType", "config")), output, when)
                    elif item.get("is_error"):
                        session.errors.append((name, output, signature))
                        session.signals.append({"type": "tool_error", "tool": name, "raw": output,
                                                "date": when.date().isoformat() if when else ""})
                continue
            text = text_of(content).strip()
            if entry.get("isMeta") or not text:
                continue
            if text.startswith("[Request interrupted by user"):
                session.add("interrupted", "", "interrupted by user", text, when)
                continue
            if text.startswith("<") or session.subagent:
                continue
            session.user_texts.append(text)
            if seen_tool_call and CORRECTION_RE.match(text[:80]):
                session.add("correction_candidate", "", "user correction?", text, when)
    return session


def read_codex(path: pathlib.Path, cutoff: dt.datetime | None) -> Session:
    session = Session("codex", path)
    seen_tool_call = False
    with open(path, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not any(marker in line for marker in ('"session_meta"', '"item_completed"', '"turn_aborted"', '"compacted"')):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = entry.get("payload") or {}
            if entry.get("type") == "session_meta":
                session.id = str(payload.get("id") or payload.get("session_id") or path.stem)
                session.parent = str(payload.get("parent_thread_id") or "")
                session.subagent = bool(session.parent) or isinstance(payload.get("source"), dict)
                if payload.get("cwd"):
                    session.cwds.add(str(payload["cwd"]))
                session.remote = str((payload.get("git") or {}).get("repository_url") or "")
                continue
            when = parse_time(entry.get("timestamp"))
            if cutoff and (when is None or when < cutoff):
                continue
            session.touch(when)
            if entry.get("type") == "compacted":
                session.add("compaction", "", "context compacted", "context compacted", when)
                continue
            kind = payload.get("type")
            if kind == "turn_aborted":
                session.add("interrupted", "", "turn aborted: " + str(payload.get("reason", "")), "turn aborted", when)
                continue
            if kind != "item_completed":
                continue
            item = payload.get("item") or {}
            itype = item.get("type")
            if itype == "CommandExecution":
                command = item.get("command")
                script = command[-1] if isinstance(command, list) and command else str(command or "")
                name = "shell:" + program_of(script)
                session.calls += 1
                seen_tool_call = True
                output = str(item.get("aggregated_output") or "")
                status, code = item.get("status"), item.get("exit_code")
                session.add_shell_output(output, name, status == "failed" or code not in (0, None), when)
                if status == "declined":
                    session.add("permission_denied", name, "declined", script, when)
                elif status == "failed" or (isinstance(code, int) and code != 0):
                    raw = f"Exit code {code}\n{output}"
                    session.errors.append((name, raw, script[:2000]))
                    session.signals.append({"type": "tool_error", "tool": name, "raw": raw,
                                            "date": when.date().isoformat() if when else ""})
            elif itype == "McpToolCall":
                name = f"mcp:{item.get('server')}.{item.get('tool')}"
                session.calls += 1
                seen_tool_call = True
                result = item.get("result") or {}
                if item.get("status") == "failed" or item.get("error") or (isinstance(result, dict) and result.get("isError")):
                    raw = text_of(item.get("error") or (result.get("content") if isinstance(result, dict) else ""))
                    sig = json.dumps(item.get("arguments"), sort_keys=True)[:2000]
                    session.errors.append((name, raw, sig))
                    session.signals.append({"type": "tool_error", "tool": name, "raw": raw,
                                            "date": when.date().isoformat() if when else ""})
            elif itype == "FileChange":
                session.calls += 1
                seen_tool_call = True
                session.edit()
            elif itype == "ContextCompaction":
                session.add("compaction", "", "context compacted", "context compacted", when)
            elif itype == "UserMessage":
                text = text_of(item.get("content")).strip()
                if not text or text.startswith("<") or session.subagent:
                    continue
                session.user_texts.append(text)
                if seen_tool_call and CORRECTION_RE.match(text[:80]):
                    session.add("correction_candidate", "", "user correction?", text, when)
    if not session.id:
        session.id = path.stem
    return session


def project_matcher(project: pathlib.Path):
    roots = {str(project)}
    remote = ""
    try:
        out = subprocess.run(["git", "-C", str(project), "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, timeout=10)
        roots |= {line[9:] for line in out.stdout.splitlines() if line.startswith("worktree ")}
        out = subprocess.run(["git", "-C", str(project), "config", "--get", "remote.origin.url"],
                             capture_output=True, text=True, timeout=10)
        remote = out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    def inside(cwd: str) -> bool:
        cwd = cwd.removeprefix("file://").rstrip("/")
        return any(cwd == root or cwd.startswith(root.rstrip("/") + "/") for root in roots)

    def match(session: Session) -> bool:
        if remote and session.remote and session.remote == remote:
            return True
        return any(inside(cwd) for cwd in session.cwds)

    return match


TEMP_PREFIXES = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")


def in_temp(cwd: str) -> bool:
    cwd = cwd.removeprefix("file://").rstrip("/") + "/"
    tmpdir = os.environ.get("TMPDIR", "").rstrip("/")
    return cwd.startswith(TEMP_PREFIXES) or bool(tmpdir and cwd.startswith(tmpdir + "/"))


def error_key(raw: str, noise: set[str]) -> tuple[str, str]:
    lines = [line.strip() for line in raw.splitlines()]
    lines = [line for line in lines if line and line not in noise and not EXIT_LINE_RE.match(line)]
    if not lines:
        first = raw.strip().splitlines()[0] if raw.strip() else "(no output)"
        return normalize_key(first), quote(first)
    pick = next((line for line in lines if ERRORISH_RE.search(line)), lines[0])
    return normalize_key(pick), quote(" / ".join(lines[:2]))


def shingles(text: str) -> set[str]:
    words = WORD_RE.findall(text.lower())
    return {" ".join(words[i:i + 4]) for i in range(max(0, len(words) - 3))}


def repeated_texts(sessions: list[Session], limit: int) -> list[dict]:
    messages = []
    for index, session in enumerate(sessions):
        for text in session.user_texts:
            if len(text.split()) >= 12:
                messages.append((index, text, shingles(text[:4000])))
    messages = messages[:3000]
    by_shingle: dict[str, list[int]] = defaultdict(list)
    for number, (_, _, grams) in enumerate(messages):
        for gram in grams:
            by_shingle[gram].append(number)
    parent = list(range(len(messages)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for number, (owner, _, grams) in enumerate(messages):
        shared = Counter(other for gram in grams for other in by_shingle[gram] if other > number)
        for other, count in shared.items():
            if messages[other][0] == owner:
                continue
            union = len(grams | messages[other][2]) or 1
            if count / union >= 0.5:
                parent[find(other)] = find(number)
    groups: dict[int, list[int]] = defaultdict(list)
    for number in range(len(messages)):
        groups[find(number)].append(number)
    result = []
    for members in groups.values():
        owners = {messages[m][0] for m in members}
        if len(owners) >= 2:
            result.append({"sessions": len(owners), "messages": len(members),
                           "quote": quote(messages[members[0]][1], 160),
                           "session_ids": sorted(sessions[o].id[:8] for o in owners)[:10]})
    result.sort(key=lambda r: -r["sessions"])
    return result[:limit]


def main() -> int:
    if any(arg in ("-h", "--help") for arg in sys.argv[1:]):
        print(__doc__.strip())
        return 0
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--project", type=pathlib.Path)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--session", type=pathlib.Path, action="append", default=[], metavar="FILE")
    parser.add_argument("--exclude-ledger", type=pathlib.Path, metavar="FILE")
    parser.add_argument("--exclude-session", action="append", default=[], metavar="ID")
    parser.add_argument("--no-subagents", action="store_true")
    parser.add_argument("--include-temp", action="store_true")
    parser.add_argument("--format", choices=["summary", "jsonl"], default="summary")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--output", type=pathlib.Path, metavar="FILE")
    args = parser.parse_args()

    if args.days < 1 or args.limit < 1:
        print("Error: --days and --limit must be at least 1.", file=sys.stderr)
        return 1
    for path in args.session:
        if not path.is_file():
            print(f"Error: --session file not found: {path}. Pass a transcript .jsonl path.", file=sys.stderr)
            return 1
    if args.project and not args.project.expanduser().is_dir():
        print(f"Error: --project is not a directory: {args.project}.", file=sys.stderr)
        return 1

    excluded = [s.strip() for s in args.exclude_session if s.strip()]
    if args.exclude_ledger:
        if args.exclude_ledger.is_file():
            for line in args.exclude_ledger.read_text(encoding="utf-8").splitlines():
                line = line.split("#", 1)[0].strip()
                if line:
                    excluded.append(line.split()[0])
        else:
            print(f"Note: ledger {args.exclude_ledger} not found; nothing excluded from it.", file=sys.stderr)
    for variable in ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID"):  # the session running this script
        current = os.environ.get(variable, "").strip()
        if current:
            excluded.append(current)

    def is_excluded(session: Session) -> bool:
        ids = [session.id, session.parent, session.path.stem]
        return any(i and e and len(e) >= 8 and (i.startswith(e) or e.startswith(i)) for i in ids for e in excluded)

    if args.session:
        cutoff = None
        sources = [("codex" if CODEX_ROOT in p.resolve().parents or p.name.startswith("rollout-") else "claude", p)
                   for p in args.session]
        scope = "sessions"
    else:
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
        sources = [("claude", p) for p in recent_files(CLAUDE_ROOT, cutoff)]
        sources += [("codex", p) for p in recent_files(CODEX_ROOT, cutoff)]
        scope = f"project:{redact(str(args.project.expanduser().resolve()))}" if args.project else "global"

    matcher = project_matcher(args.project.expanduser().resolve()) if args.project and not args.session else None
    sessions: list[Session] = []
    skipped = Counter()
    for agent, path in sources:
        session = read_claude(path, cutoff) if agent == "claude" else read_codex(path, cutoff)
        if session.first is None:
            continue
        if args.no_subagents and session.subagent:
            skipped["subagent"] += 1
            continue
        if matcher and not matcher(session):
            continue
        if not args.include_temp and not args.session and session.cwds and all(in_temp(c) for c in session.cwds):
            skipped["temp_dir"] += 1
            continue
        if is_excluded(session):
            skipped["excluded"] += 1
            continue
        sessions.append(session)

    # Noise lines: lines that fill at least half of the shell outputs of the sessions
    # they appear in (shell start-up warnings, aliases), seen 3+ times.
    line_outputs: Counter = Counter()
    line_sessions: dict[str, set[int]] = defaultdict(set)
    for index, session in enumerate(sessions):
        for lines in session.shell_outputs:
            for line in lines:
                line_outputs[line] += 1
                line_sessions[line].add(index)
    noise_sessions: Counter = Counter()
    for line, count in line_outputs.items():
        owners = line_sessions[line]
        total = sum(len(sessions[i].shell_outputs) for i in owners)
        if count >= 3 and count / total >= 0.5:
            noise_sessions[line] = len(owners)
    noise = set(noise_sessions)
    noise_min = 1

    # Finish tool_error signals and detect retries after an error.
    for session in sessions:
        failed_signatures: set[str] = set()
        repeated: Counter = Counter()
        for name, _, signature in session.errors:
            if signature and signature in failed_signatures:
                repeated[(name, signature)] += 1
            failed_signatures.add(signature)
        for (name, signature), count in repeated.items():
            session.signals.append({"type": "retry_after_error", "tool": name, "key": "same call repeated after it failed",
                                    "quote": quote(signature, 160), "date": "", "count": count})
        for signal in session.signals:
            if "raw" in signal:
                signal["key"], signal["quote"] = error_key(signal.pop("raw"), noise)

    records = []
    for session in sessions:
        for signal in session.signals:
            record = {"agent": session.agent, "session": session.id[:8], "subagent": session.subagent}
            record.update(signal)
            records.append(record)

    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        if args.format == "jsonl":
            for record in records:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            return 0

        groups: dict[tuple, dict] = {}
        for record in records:
            key = (record["type"], record["tool"], record["key"])
            group = groups.setdefault(key, {"type": key[0], "tool": key[1], "key": key[2],
                                            "occurrences": 0, "sessions": set(), "examples": []})
            group["occurrences"] += record.get("count", 1)
            group["sessions"].add((record["agent"], record["session"]))
            if len(group["examples"]) < 2 and record["session"] not in {e["session"] for e in group["examples"]}:
                group["examples"].append({"agent": record["agent"], "session": record["session"],
                                          "date": record["date"], "quote": record["quote"]})
        ranked = sorted(groups.values(), key=lambda g: (-len(g["sessions"]), -g["occurrences"]))
        by_tool = Counter((r["tool"] or "-") for r in records if r["type"] == "tool_error")

        main_sessions = [s for s in sessions if not s.subagent]
        before_edit = [s.first_edit_at for s in main_sessions if s.first_edit_at is not None]
        report = {
            "scope": scope,
            "days": None if args.session else args.days,
            "sessions": {
                "claude": sum(1 for s in sessions if s.agent == "claude" and not s.subagent),
                "codex": sum(1 for s in sessions if s.agent == "codex" and not s.subagent),
                "subagents": sum(1 for s in sessions if s.subagent),
                "skipped": dict(skipped),
            },
            "tool_calls": sum(s.calls for s in sessions),
            "signal_counts": dict(Counter(r["type"] for r in records).most_common()),
            "tool_errors_by_tool": dict(by_tool.most_common(args.limit)),
            "top_groups": [
                {**{k: v for k, v in g.items() if k != "sessions"}, "sessions": len(g["sessions"])}
                for g in ranked[: args.limit]
            ],
            "noise_lines": [{"line": quote(line, 160), "sessions": count}
                            for line, count in noise_sessions.most_common() if count >= noise_min][: args.limit],
            "exploration": {
                "sessions_with_edits": len(before_edit),
                "sessions_without_edits": len(main_sessions) - len(before_edit),
                "median_calls_before_first_edit": statistics.median(before_edit) if before_edit else None,
                "max_calls_before_first_edit": max(before_edit) if before_edit else None,
                "slowest": sorted(({"agent": s.agent, "session": s.id[:8], "calls_before_first_edit": s.first_edit_at}
                                   for s in main_sessions if s.first_edit_at is not None),
                                  key=lambda r: -r["calls_before_first_edit"])[:5],
            },
            "repeated_user_text": repeated_texts(main_sessions, args.limit),
        }
        out.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        return 0
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    sys.exit(main())
