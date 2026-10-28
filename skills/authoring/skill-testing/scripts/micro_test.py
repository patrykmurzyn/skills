# /// script
# requires-python = ">=3.10"
# ///
"""Run one prompt with and without a candidate instruction, in fresh agent sessions.

Usage: uv run scripts/micro_test.py PROMPT_FILE --guidance FILE [--guidance FILE ...]
                                    --out DIR [--reps N] [--agent claude|codex]
                                    [--model MODEL] [--flag REGEX] [--timeout SEC]

Arms: "control" (the prompt alone) and one arm per --guidance file (the guidance,
a blank line, then the prompt). Each rep is a fresh headless session started in an
empty temp directory; outputs are saved as DIR/<arm>/rep-<n>.md for reading by hand.

Cost: every rep is a paid agent session, (1 + guidance files) x reps in total.

Output: JSON summary on stdout: per arm, reps, errors, and with --flag the number of
outputs matching REGEX (a pointer to what to read, not a verdict). Progress on stderr.

Examples:
  uv run scripts/micro_test.py prompt.md --guidance recipe.md --reps 5 --out ws/micro/recipe
  uv run scripts/micro_test.py prompt.md --guidance a.md --guidance b.md --flag "(?i)as an ai" --out ws/micro/ab

Exit codes: 0 finished, 1 bad input, 2 agent CLI not found.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile


def run_claude(prompt: str, model: str | None, timeout: float) -> str:
    command = ["claude", "-p", prompt, "--output-format", "json"] + (["--model", model] if model else [])
    with tempfile.TemporaryDirectory(prefix="micro-test-") as cwd:
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip()[:300] or f"exit code {done.returncode}")
    return str(json.loads(done.stdout).get("result", ""))


def run_codex(prompt: str, model: str | None, timeout: float) -> str:
    with tempfile.TemporaryDirectory(prefix="micro-test-") as cwd:
        last = pathlib.Path(cwd) / "last-message.md"
        command = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only",
                   "--output-last-message", str(last)] + (["--model", model] if model else []) + [prompt]
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        if done.returncode != 0 or not last.exists():
            raise RuntimeError(done.stderr.strip()[:300] or f"exit code {done.returncode}")
        return last.read_text(encoding="utf-8")


RUNNERS = {"claude": run_claude, "codex": run_codex}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one prompt with and without candidate instructions, in fresh agent sessions.",
        epilog="Exit codes: 0 finished, 1 bad input, 2 agent CLI not found.",
    )
    parser.add_argument("prompt", type=pathlib.Path, metavar="PROMPT_FILE")
    parser.add_argument("--guidance", type=pathlib.Path, action="append", required=True, metavar="FILE")
    parser.add_argument("--out", type=pathlib.Path, required=True, metavar="DIR")
    parser.add_argument("--reps", type=int, default=5, help="runs per arm (default: 5)")
    parser.add_argument("--agent", choices=sorted(RUNNERS), default="claude")
    parser.add_argument("--model", help="pin the model for every arm")
    parser.add_argument("--flag", help="regex that marks outputs worth reading first")
    parser.add_argument("--timeout", type=float, default=300, help="seconds per run (default: 300)")
    args = parser.parse_args()

    try:
        prompt = args.prompt.read_text(encoding="utf-8").strip()
        arms = {"control": prompt}
        for path in args.guidance:
            arm = path.stem if path.stem != "control" else "guidance-control"
            if arm in arms:
                raise ValueError(f"two guidance files share the name '{arm}'; rename one")
            arms[arm] = path.read_text(encoding="utf-8").strip() + "\n\n" + prompt
        flag = re.compile(args.flag) if args.flag else None
    except (OSError, ValueError, re.error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.reps < 1:
        print("Error: --reps must be at least 1.", file=sys.stderr)
        return 1
    if shutil.which(args.agent) is None:
        print(f"Error: the '{args.agent}' CLI is not on PATH.", file=sys.stderr)
        return 2

    print(f"{len(arms)} arms x {args.reps} reps = {len(arms) * args.reps} {args.agent} sessions", file=sys.stderr)
    summary = {}
    for arm, text in arms.items():
        folder = args.out / arm
        folder.mkdir(parents=True, exist_ok=True)
        errors = flagged = 0
        for rep in range(1, args.reps + 1):
            try:
                output = RUNNERS[args.agent](text, args.model, args.timeout)
            except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                errors += 1
                output = f"ERROR: {exc}"
            (folder / f"rep-{rep}.md").write_text(output + "\n", encoding="utf-8")
            if flag and flag.search(output):
                flagged += 1
            print(f"{arm} rep {rep}/{args.reps} done", file=sys.stderr)
        summary[arm] = {"reps": args.reps, "errors": errors, "flagged": flagged if flag else None,
                        "outputs": str(folder)}
    print(json.dumps({"agent": args.agent, "model": args.model, "flag": args.flag, "arms": summary}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
