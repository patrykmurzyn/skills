# /// script
# requires-python = ">=3.10"
# ///
"""Report in how many sessions each installed skill was used, from local Claude Code and Codex transcripts.

Usage: uv run scripts/usage.py [--days N] [--skills-dir DIR ...] [--format table|json]
                               [--sessions SKILL]

Reads, read-only:
  Claude Code  ~/.claude/projects/**/*.jsonl          a Skill tool call names the skill
  Codex        $CODEX_HOME/sessions/**/*.jsonl         a tool call that reads <name>/SKILL.md
               (CODEX_HOME defaults to ~/.codex)       (heuristic; the skill list Codex puts
                                                        in its prompt is not counted)
Installed skills are the folders in ~/.agents/skills and ~/.claude/skills, plus --skills-dir.
A skill counts once per session (transcript file), however often it was read in it.
Only tool-call names and inputs are parsed; the report holds counts and dates, no conversation text.

Options:
  --days N           Only count uses in the last N days (default: 30).
  --skills-dir DIR   Another folder of installed skills (repeatable).
  --format FORMAT    table (default) or json.
  --sessions SKILL   Instead of the report, list as JSON the transcript files of the
                     sessions that used SKILL, newest first (for the corrections step).

Examples:
  uv run scripts/usage.py
  uv run scripts/usage.py --days 90 --format json
  uv run scripts/usage.py --sessions skill-writing

Exit codes: 0 report written, 1 bad arguments.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys

HOME = pathlib.Path.home()
CLAUDE_ROOT = HOME / ".claude" / "projects"
CODEX_ROOT = pathlib.Path(os.environ.get("CODEX_HOME", HOME / ".codex")) / "sessions"
DEFAULT_SKILL_DIRS = [HOME / ".agents" / "skills", HOME / ".claude" / "skills"]
CODEX_TOOL_TYPES = {"custom_tool_call", "function_call", "local_shell_call"}
SKILL_PATH_RE = re.compile(r"/([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md")


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


def claude_uses(cutoff: dt.datetime):
    for path in recent_files(CLAUDE_ROOT, cutoff):
        with open(path, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if '"Skill"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                when = parse_time(entry.get("timestamp"))
                if when is None or when < cutoff:
                    continue
                content = (entry.get("message") or {}).get("content")
                for item in content if isinstance(content, list) else []:
                    if isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Skill":
                        name = str((item.get("input") or {}).get("skill", "")).split(":")[-1]
                        if name:
                            yield name, when, path


def codex_uses(cutoff: dt.datetime):
    for path in recent_files(CODEX_ROOT, cutoff):
        with open(path, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if "SKILL.md" not in line or '"response_item"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = entry.get("payload") or {}
                if payload.get("type") not in CODEX_TOOL_TYPES:
                    continue
                when = parse_time(entry.get("timestamp"))
                if when is None or when < cutoff:
                    continue
                text = json.dumps({k: payload.get(k) for k in ("input", "arguments", "action")})
                for name in set(SKILL_PATH_RE.findall(text)):
                    yield name, when, path


def installed(dirs: list[pathlib.Path]) -> set[str]:
    names = set()
    for folder in dirs:
        if not folder.is_dir():
            continue
        for entry in folder.iterdir():
            if entry.name != "synced" and (entry / "SKILL.md").is_file():
                names.add(entry.name)
    return names


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report skill usage from local Claude Code and Codex transcripts.",
        epilog="Exit codes: 0 report written, 1 bad arguments.",
    )
    parser.add_argument("--days", type=int, default=30, help="look back N days (default: 30)")
    parser.add_argument("--skills-dir", type=pathlib.Path, action="append", default=[], metavar="DIR")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--sessions", metavar="SKILL")
    args = parser.parse_args()
    if args.days < 1:
        print("Error: --days must be at least 1.", file=sys.stderr)
        return 1

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    stats: dict[str, dict] = {}
    for agent, uses in (("claude", claude_uses(cutoff)), ("codex", codex_uses(cutoff))):
        for name, when, session in uses:
            row = stats.setdefault(name, {"claude": set(), "codex": set(), "last_used": None})
            row[agent].add(session)
            if row["last_used"] is None or when > row["last_used"]:
                row["last_used"] = when

    if args.sessions:
        last: dict[tuple[str, pathlib.Path], dt.datetime] = {}
        for agent, uses in (("claude", claude_uses(cutoff)), ("codex", codex_uses(cutoff))):
            for name, when, session in uses:
                if name == args.sessions and ((agent, session) not in last or when > last[(agent, session)]):
                    last[(agent, session)] = when
        rows = sorted(last.items(), key=lambda kv: kv[1], reverse=True)
        print(json.dumps({"skill": args.sessions, "days": args.days, "sessions": [
            {"agent": agent, "path": str(path), "last_used": when.isoformat(timespec="seconds")}
            for (agent, path), when in rows]}, indent=2))
        return 0

    names = installed(DEFAULT_SKILL_DIRS + args.skills_dir)
    report = {
        "days": args.days,
        "sources": {"claude": str(CLAUDE_ROOT), "codex": str(CODEX_ROOT)},
        "skills": [
            {"skill": name, "installed": name in names,
             "claude": len(row["claude"]), "codex": len(row["codex"]),
             "last_used": row["last_used"].date().isoformat()}
            for name, row in sorted(stats.items(), key=lambda kv: -(len(kv[1]["claude"]) + len(kv[1]["codex"])))
        ],
        "never_used": sorted(names - set(stats)),
    }

    if args.format == "json":
        print(json.dumps(report, indent=2))
        return 0
    print(f"Sessions using each skill, last {args.days} days (Claude Code: Skill tool calls; Codex: SKILL.md reads)\n")
    print(f"{'skill':<34} {'claude':>6} {'codex':>6}  last used   installed")
    for row in report["skills"]:
        print(f"{row['skill']:<34} {row['claude']:>6} {row['codex']:>6}  {row['last_used']}  "
              f"{'yes' if row['installed'] else 'no'}")
    print(f"\nInstalled, never used ({len(report['never_used'])}): " + (", ".join(report["never_used"]) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
