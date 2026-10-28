# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Regenerate the skill catalog in README.md from each SKILL.md frontmatter.

Usage: uv run scripts/catalog.py [--check]

Options:
  --check   Change nothing; exit 1 if the catalog in README.md is out of date.

Exit codes: 0 up to date or rewritten, 1 out of date (--check) or README markers missing.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
START, END = "<!-- catalog:start -->", "<!-- catalog:end -->"


def frontmatter(skill_md: pathlib.Path) -> dict:
    match = re.match(r"^---\n(.*?)\n---", skill_md.read_text(encoding="utf-8"), re.S)
    data = yaml.safe_load(match.group(1)) if match else None
    return data if isinstance(data, dict) else {}


def table() -> str:
    skills_root = ROOT / "skills"
    rows = []
    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        if "evals" in skill_md.relative_to(skills_root).parts:
            continue
        fm = frontmatter(skill_md)
        meta = fm.get("metadata") or {}
        folder = skill_md.parent
        group = folder.parent.name if folder.parent != skills_root else ""
        name = fm.get("name", folder.name)
        description = " ".join(str(fm.get("description", "")).split())
        description = re.split(r"(?<=\.)\s+(?=Use |Step )", description)[0].replace("|", "\\|")
        link = folder.relative_to(ROOT).as_posix() + "/SKILL.md"
        rows.append(
            f"| [`{name}`]({link}) | {description} | {group} | {meta.get('status', '')} |"
        )
    if not rows:
        return "_No skills yet._"
    header = "| Skill | What it does | Group | Status |\n| --- | --- | --- | --- |"
    return header + "\n" + "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the skill catalog in README.md.")
    parser.add_argument("--check", action="store_true", help="exit 1 if the catalog is out of date")
    args = parser.parse_args()

    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print(f"Error: README.md must contain {START} and {END}.", file=sys.stderr)
        return 1
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    updated = f"{head}{START}\n{table()}\n{END}{tail}"

    if updated == text:
        print("Catalog is up to date.", file=sys.stderr)
        return 0
    if args.check:
        print("Catalog is out of date. Run: uv run scripts/catalog.py", file=sys.stderr)
        return 1
    README.write_text(updated, encoding="utf-8")
    print("Catalog updated in README.md.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
