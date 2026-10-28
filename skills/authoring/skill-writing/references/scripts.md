# Scripts in skills

Read this before adding a file to `scripts/`. Agents read a script's output and exit code to decide what to do next, so design for that reader.

## When to bundle one

- Every test run rewrote the same helper (a parser, a chart builder, a validator).
- An exact sequence must run the same way every time.
- An existing tool with a few flags is enough: call it directly with a pinned version (`uvx ruff@0.8.0`, `npx eslint@9`) instead of writing a script.

## Interface

- **No interactive prompts.** Agents run in non-interactive shells and a prompt hangs forever. Take input from flags, environment variables or stdin.
- **`--help`** gives a one-line purpose, the flags, two examples and the exit codes. Keep it short: it lands in the agent's context.
- **Errors say what to do next:** what was wrong, what was expected, the command to try. "Error: --format must be json or csv. Received: xml".
- **Data on stdout, diagnostics on stderr.** Prefer JSON or CSV for data.
- **Exit codes:** 0 success, distinct non-zero codes for distinct failures, all listed in `--help`.
- **Idempotent:** agents retry. "Create if missing" beats "fail if exists".
- **Safe by default:** `--dry-run` for anything stateful, and an explicit flag such as `--force` for destructive steps.
- **State outside the skill:** write logs, caches and config to the project or a data directory (for example `${XDG_STATE_HOME:-~/.local/state}/<skill>/`), never into the skill folder.
- **Bounded output:** harnesses truncate long output (often 10–30K characters). Summarize by default and offer `--limit`/`--offset`, or write to a file passed with `--output`.

## Dependencies

- Python: declare dependencies inline (PEP 723) and run with `uv run scripts/x.py`:

  ```python
  # /// script
  # requires-python = ">=3.10"
  # dependencies = ["pyyaml>=6,<7"]
  # ///
  ```

- Pin versions. State runtime requirements in the `compatibility` field.

## In SKILL.md

List each script with a one-line purpose and show the exact command, with paths relative to the skill root. Call scripts through their interpreter (`uv run scripts/x.py`, `bash scripts/x.sh`): the executable bit is often lost when a skill is downloaded or copied.

```markdown
- `scripts/check.py`: validates the output. Run `uv run scripts/check.py out/`; fix and re-run until it exits 0.
```
