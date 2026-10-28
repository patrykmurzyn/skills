# /// script
# requires-python = ">=3.10"
# ///
"""Measure how often an agent loads a skill for each query.

Usage: uv run scripts/trigger_eval.py QUERIES_JSON [--agent claude|codex] [--runs N]
                                      [--split train|validation|all] [--limit N]
                                      [--timeout SEC] [--model MODEL] [--output FILE]

Each run is a fresh headless session in an empty temp directory, stopped as soon
as the skill loads or after --timeout seconds:
  claude  `claude -p --output-format stream-json --verbose --max-turns 3`
          hit = a Skill tool call for the skill, or a Read of its SKILL.md
  codex   `codex exec --json --sandbox read-only`
          hit = an item event that mentions <skill>/SKILL.md (heuristic)
The skill must be installed where the agent finds it globally.

Cost: every run is a paid agent session, queries x runs in total.
Use --limit 2 --runs 1 for a cheap smoke test.

QUERIES_JSON:
  {"skill": "my-skill",
   "queries": [{"query": "...", "should_trigger": true, "split": "train"}]}

Output: JSON on stdout (or --output FILE). Per query: hits, runs, trigger_rate,
statuses and pass (rate >= 0.5 if should_trigger, below 0.5 otherwise); plus the
pass rate per split. Progress goes to stderr.

Exit codes: 0 finished, 1 bad input, 2 agent CLI not found.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def claude_command(query: str, model: str | None) -> list[str]:
    command = ["claude", "-p", query, "--output-format", "stream-json", "--verbose", "--max-turns", "3"]
    return command + (["--model", model] if model else [])


def claude_hit(event: dict, skill: str) -> bool:
    for node in walk(event):
        if node.get("type") != "tool_use":
            continue
        tool_input = node.get("input") or {}
        if node.get("name") == "Skill" and str(tool_input.get("skill", "")).split(":")[-1] == skill:
            return True
        if node.get("name") == "Read" and str(tool_input.get("file_path", "")).endswith(f"/{skill}/SKILL.md"):
            return True
    return False


def codex_command(query: str, model: str | None) -> list[str]:
    command = ["codex", "exec", "--json", "--skip-git-repo-check", "--sandbox", "read-only"]
    return command + (["--model", model] if model else []) + [query]


def codex_hit(event: dict, skill: str) -> bool:
    return str(event.get("type", "")).startswith("item.") and f"/{skill}/SKILL.md" in json.dumps(event)


AGENTS = {"claude": (claude_command, claude_hit), "codex": (codex_command, codex_hit)}


def run_once(agent: str, query: str, skill: str, timeout: float, model: str | None) -> str:
    """Return 'hit', 'miss', 'timeout' or 'error'."""
    make_command, is_hit = AGENTS[agent]
    with tempfile.TemporaryDirectory(prefix="trigger-eval-") as cwd:
        proc = subprocess.Popen(
            make_command(query, model), cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        timed_out = threading.Event()

        def stop() -> None:
            timed_out.set()
            proc.kill()

        timer = threading.Timer(timeout, stop)
        timer.start()
        hit = False
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if is_hit(event, skill):
                    hit = True
                    break
        finally:
            timer.cancel()
            if proc.poll() is None:
                proc.kill()
            proc.wait()
    if hit:
        return "hit"
    if timed_out.is_set():
        return "timeout"
    return "miss" if proc.returncode == 0 else "error"


def load_queries(path: pathlib.Path) -> tuple[str, list[dict]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    skill = data.get("skill") if isinstance(data, dict) else None
    queries = data.get("queries") if isinstance(data, dict) else None
    if not isinstance(skill, str) or not isinstance(queries, list) or not queries:
        raise ValueError('expected {"skill": "<name>", "queries": [...]} with at least one query')
    for index, item in enumerate(queries):
        if not isinstance(item, dict) or not isinstance(item.get("query"), str) \
                or not isinstance(item.get("should_trigger"), bool):
            raise ValueError(f'queries[{index}] needs "query" (string) and "should_trigger" (true/false)')
        if item.get("split", "train") not in ("train", "validation"):
            raise ValueError(f'queries[{index}].split must be "train" or "validation"')
    return skill, queries


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure how often an agent loads a skill for each query.",
        epilog="Exit codes: 0 finished, 1 bad input, 2 agent CLI not found.",
    )
    parser.add_argument("queries", type=pathlib.Path, metavar="QUERIES_JSON")
    parser.add_argument("--agent", choices=sorted(AGENTS), default="claude")
    parser.add_argument("--runs", type=int, default=3, help="runs per query (default: 3)")
    parser.add_argument("--split", choices=["train", "validation", "all"], default="all")
    parser.add_argument("--limit", type=int, default=0, help="only the first N queries after filtering")
    parser.add_argument("--timeout", type=float, default=180, help="seconds per run (default: 180)")
    parser.add_argument("--model", help="pin the model (passed to the agent CLI as --model)")
    parser.add_argument("--output", type=pathlib.Path, help="write the JSON report here instead of stdout")
    args = parser.parse_args()

    try:
        skill, queries = load_queries(args.queries)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.runs < 1:
        print("Error: --runs must be at least 1.", file=sys.stderr)
        return 1
    if shutil.which(args.agent) is None:
        print(f"Error: the '{args.agent}' CLI is not on PATH.", file=sys.stderr)
        return 2

    selected = [q for q in queries if args.split == "all" or q.get("split", "train") == args.split]
    if args.limit > 0:
        selected = selected[: args.limit]
    print(f"{skill}: {len(selected)} queries x {args.runs} runs = "
          f"{len(selected) * args.runs} {args.agent} sessions", file=sys.stderr)

    results = []
    for number, item in enumerate(selected, 1):
        statuses = [run_once(args.agent, item["query"], skill, args.timeout, args.model)
                    for _ in range(args.runs)]
        hits = statuses.count("hit")
        rate = hits / args.runs
        passed = rate >= 0.5 if item["should_trigger"] else rate < 0.5
        results.append({
            "query": item["query"], "should_trigger": item["should_trigger"],
            "split": item.get("split", "train"), "hits": hits, "runs": args.runs,
            "trigger_rate": round(rate, 2), "statuses": statuses, "pass": passed,
        })
        print(f"[{number}/{len(selected)}] {'pass' if passed else 'FAIL'}  rate {rate:.2f}  "
              f"{item['query'][:70]}", file=sys.stderr)

    summary = {}
    for split in ("train", "validation"):
        rows = [r for r in results if r["split"] == split]
        if rows:
            summary[split] = {"passed": sum(r["pass"] for r in rows), "total": len(rows),
                              "pass_rate": round(sum(r["pass"] for r in rows) / len(rows), 2)}
    report = json.dumps({"skill": skill, "agent": args.agent, "model": args.model,
                         "summary": summary, "results": results}, indent=2)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
