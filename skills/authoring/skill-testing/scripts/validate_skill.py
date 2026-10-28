# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Validate Agent Skill folders against the spec and basic safety rules.

Usage: uv run scripts/validate_skill.py [--require FIELDS] [--format text|json] SKILL_DIR...

Errors (exit 1):
  SKILL.md missing, or no YAML frontmatter
  name: missing, over 64 chars, not lowercase a-z/0-9/single hyphens, differs from the folder, reserved
  description: missing, over 1024 chars, contains XML/HTML tags
  compatibility over 500 chars; metadata values not strings; allowed-tools not a string
  SKILL.md body over 500 lines or file 20,000 bytes or more; unfinished placeholders
  (<...>, TODO, TBD, FIXME) in SKILL.md prose
  in any text file: hidden Unicode (zero-width, bidi controls, tag characters),
  more than 10 blank lines in a row (padding), secret-like strings
  in Markdown: HTML comments, broken relative links
  the same name in two folders; a --require field missing
Warnings:
  description over 300 chars; body over ~5000 tokens; frontmatter outside the spec
  (errors with --strict-spec); Claude Code-only syntax in Markdown; no evals/ folder
Files under evals/files/ are fixtures and are not scanned.

Options:
  --require FIELDS  Comma-separated fields that must be present, dotted for nesting,
                    e.g. license,metadata.version
  --strict-spec     Treat frontmatter fields outside the spec as errors (claude.ai rejects them)
  --format FORMAT   text (default) or json

Examples:
  uv run scripts/validate_skill.py ~/.agents/skills/my-skill
  uv run scripts/validate_skill.py --format json skills/*/*

Exit codes: 0 valid (warnings allowed), 1 errors found, 2 bad arguments.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

import yaml

SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
AGENT_FIELDS = {
    "disable-model-invocation": "Claude Code and Cursor",
    "paths": "Claude Code and Cursor",
    "when_to_use": "Claude Code",
    "user-invocable": "Claude Code",
    "argument-hint": "Claude Code",
    "arguments": "Claude Code",
    "disallowed-tools": "Claude Code",
    "model": "Claude Code",
    "effort": "Claude Code",
    "context": "Claude Code",
    "agent": "Claude Code",
    "background": "Claude Code",
    "hooks": "Claude Code",
    "shell": "Claude Code",
}
RESERVED = {"skill-creator", "create-skill", "synced"}
DESCRIPTION_TARGET = 300
MAX_SKILL_MD_BYTES = 20_000  # Claude Code keeps ~5,000 tokens of a skill after compaction
MAX_BLANK_RUN = 10  # long blank runs push hidden text below the visible end of a file
TEXT_SUFFIXES = {".md", ".txt", ".py", ".sh", ".js", ".mjs", ".ts", ".json", ".yaml", ".yml", ".toml"}

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
XML_TAG_RE = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")
# Zero-width characters, bidi controls, word joiners, BOM and Unicode tag characters.
HIDDEN_RANGES = [(0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x2064), (0x2066, 0x2069),
                 (0xFEFF, 0xFEFF), (0xE0000, 0xE007F)]
HIDDEN_RE = re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in HIDDEN_RANGES) + "]")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SECRET_RES = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("API key (sk-...)", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
FENCE_RE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^<>\n]{0,80}>|\b(?:TODO|TBD|FIXME)\b")
CLAUDE_ONLY_RES = [
    ("inline shell command (an exclamation mark before a backticked command)", re.compile(r"!`[^`]+`")),
    ("CLAUDE_SKILL_DIR variable", re.compile(r"\$\{CLAUDE_SKILL_DIR\}")),
]


class Report:
    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.name: str | None = None
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def error(self, message: str, file: str = "SKILL.md", line: int | None = None) -> None:
        self.errors.append({"file": file, "line": line, "message": message})

    def warn(self, message: str, file: str = "SKILL.md", line: int | None = None) -> None:
        self.warnings.append({"file": file, "line": line, "message": message})


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    after = text.find("\n", end + 1)
    return text[4:end], (text[after + 1:] if after != -1 else "")


def dotted(data: dict, path: str):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def text_files(skill_dir: pathlib.Path):
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir)
        if rel.parts[:2] == ("evals", "files"):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path, rel.as_posix()


def placeholders(body: str) -> list[tuple[int, str]]:
    """Template placeholders left in prose (code blocks and inline code are ignored)."""
    blank_code = lambda m: re.sub(r"[^\n]", " ", m.group())  # keep line numbers
    prose = INLINE_CODE_RE.sub(blank_code, FENCE_RE.sub(blank_code, body))
    found = []
    for number, line in enumerate(prose.splitlines(), 1):
        for match in PLACEHOLDER_RE.finditer(line):
            if "://" not in match.group():
                found.append((number, match.group()))
    return found


def check_frontmatter(report: Report, fm: dict, folder: str, required: list[str], strict: bool) -> None:
    name = fm.get("name")
    if not isinstance(name, str) or not name:
        report.error("name is required")
    else:
        report.name = name
        if len(name) > 64:
            report.error(f"name is {len(name)} chars; the maximum is 64")
        if not NAME_RE.match(name):
            report.error(
                f"name '{name}' may contain only lowercase a-z, 0-9 and single hyphens, "
                "and must not start or end with a hyphen"
            )
        if name != folder:
            report.error(f"name '{name}' must equal the folder name '{folder}'")
        if name in RESERVED:
            report.error(f"name '{name}' is reserved or used by a built-in skill; pick another")

    description = fm.get("description")
    if not isinstance(description, str) or not description.strip():
        report.error("description is required: what the skill does and when to use it")
    else:
        if len(description) > 1024:
            report.error(f"description is {len(description)} chars; the maximum is 1024")
        elif len(description) > DESCRIPTION_TARGET:
            report.warn(
                f"description is {len(description)} chars; aim for about 250, "
                "since every installed skill's description loads at startup"
            )
        if XML_TAG_RE.search(description):
            report.error("description must not contain XML or HTML tags")

    if "compatibility" in fm:
        value = fm["compatibility"]
        if not isinstance(value, str) or not 1 <= len(value) <= 500:
            report.error("compatibility must be a string of 1-500 chars")
    if "license" in fm and not isinstance(fm["license"], str):
        report.error("license must be a string")
    if "metadata" in fm:
        metadata = fm["metadata"]
        if not isinstance(metadata, dict):
            report.error("metadata must map string keys to string values")
        else:
            for key, value in metadata.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    report.error(f"metadata.{key} must be a string; quote it, e.g. version: \"1.0\"")
    if "allowed-tools" in fm and not isinstance(fm["allowed-tools"], str):
        report.error("allowed-tools must be a space-separated string")

    for key in fm:
        if key in SPEC_FIELDS:
            continue
        where = AGENT_FIELDS.get(key)
        message = (f"field '{key}' works only in {where}" if where
                   else f"field '{key}' is outside the Agent Skills spec")
        if strict:
            report.error(f"{message}; claude.ai upload rejects fields outside the spec")
        else:
            report.warn(f"{message}; other agents ignore it")

    for field in required:
        if dotted(fm, field) in (None, ""):
            report.error(f"required field '{field}' is missing")


def check_files(report: Report, skill_dir: pathlib.Path) -> None:
    for path, rel in text_files(skill_dir):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            report.error("file is not valid UTF-8", file=rel)
            continue
        is_markdown = path.suffix.lower() == ".md"
        blank_run = 0
        for number, line in enumerate(content.splitlines(), 1):
            blank_run = blank_run + 1 if not line.strip() else 0
            if blank_run == MAX_BLANK_RUN + 1:
                report.error(f"more than {MAX_BLANK_RUN} blank lines in a row; padding can hide text "
                             "below the visible end of a file", file=rel, line=number)
            for match in HIDDEN_RE.finditer(line):
                report.error(f"hidden Unicode character U+{ord(match.group()):04X}", file=rel, line=number)
            for label, pattern in SECRET_RES:
                if pattern.search(line):
                    report.error(f"looks like a {label}; never commit secrets", file=rel, line=number)
            if not is_markdown:
                continue
            if "<!--" in line:
                report.error("HTML comment in Markdown; skills must not contain hidden text", file=rel, line=number)
            for match in LINK_RE.finditer(line):
                target = match.group(1)
                if URL_SCHEME_RE.match(target) or target.startswith("#"):
                    continue
                local = target.split("#", 1)[0]
                if local and not (path.parent / local).exists():
                    report.error(f"broken link '{target}'", file=rel, line=number)
            for label, pattern in CLAUDE_ONLY_RES:
                if pattern.search(line):
                    report.warn(f"{label} works only in Claude Code", file=rel, line=number)


def check_skill(skill_dir: pathlib.Path, required: list[str], strict: bool = False) -> Report:
    report = Report(skill_dir)
    skill_md = skill_dir / "SKILL.md"
    if not skill_dir.is_dir():
        report.error("not a directory", file=".")
        return report
    if not skill_md.is_file():
        report.error("SKILL.md is missing", file=".")
        return report

    size = skill_md.stat().st_size
    if size >= MAX_SKILL_MD_BYTES:
        report.error(f"SKILL.md is {size} bytes; keep it under {MAX_SKILL_MD_BYTES} so it survives "
                     "context compaction. Move detail to references/")
    fm_text, body = split_frontmatter(skill_md.read_text(encoding="utf-8"))
    if fm_text is None:
        report.error("SKILL.md must start with YAML frontmatter between '---' lines", line=1)
        return report
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        report.error(f"frontmatter is not valid YAML: {exc}", line=1)
        return report
    if not isinstance(fm, dict):
        report.error("frontmatter must be a YAML mapping", line=1)
        return report

    check_frontmatter(report, fm, skill_dir.name, required, strict)

    body_start = len(fm_text.splitlines()) + 3
    for number, text in placeholders(body):
        report.error(f"unfinished placeholder '{text}'", line=body_start + number - 1)

    body_lines = len(body.splitlines())
    if body_lines > 500:
        report.error(f"SKILL.md body is {body_lines} lines; the maximum is 500. Move detail to references/")
    if len(body) // 4 > 5000:
        report.warn(f"SKILL.md body is ~{len(body) // 4} tokens; aim for under 5000")
    if not (skill_dir / "evals").is_dir():
        report.warn("no evals/ folder; add test cases before marking the skill stable", file=".")

    check_files(report, skill_dir)
    return report


def location(item: dict) -> str:
    return f"{item['file']}:{item['line']}" if item["line"] else item["file"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Agent Skill folders.",
        epilog="Exit codes: 0 valid, 1 errors found, 2 bad arguments.",
    )
    parser.add_argument("skills", nargs="+", type=pathlib.Path, metavar="SKILL_DIR")
    parser.add_argument("--require", default="", metavar="FIELDS", help="comma-separated required fields")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--strict-spec", action="store_true",
                        help="treat frontmatter fields outside the spec as errors")
    args = parser.parse_args()

    required = [field.strip() for field in args.require.split(",") if field.strip()]
    reports = [check_skill(path.resolve(), required, args.strict_spec) for path in args.skills]

    seen: dict[str, Report] = {}
    for report in reports:
        if report.name is None:
            continue
        if report.name in seen:
            other = seen[report.name]
            for a, b in ((report, other), (other, report)):
                a.error(f"name '{a.name}' is also used by {os.path.relpath(b.path)}")
        else:
            seen[report.name] = report

    failed = any(report.errors for report in reports)
    if args.format == "json":
        print(json.dumps({
            "valid": not failed,
            "skills": [
                {"path": str(r.path), "name": r.name, "errors": r.errors, "warnings": r.warnings}
                for r in reports
            ],
        }, indent=2))
    else:
        for report in reports:
            status = "FAIL" if report.errors else "ok"
            print(f"{status:<4}  {os.path.relpath(report.path)}  "
                  f"({len(report.errors)} errors, {len(report.warnings)} warnings)")
            for item in report.errors:
                print(f"      error    {location(item)}  {item['message']}")
            for item in report.warnings:
                print(f"      warning  {location(item)}  {item['message']}")
        total_errors = sum(len(r.errors) for r in reports)
        total_warnings = sum(len(r.warnings) for r in reports)
        print(f"\n{len(reports)} skill(s): {total_errors} errors, {total_warnings} warnings")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
