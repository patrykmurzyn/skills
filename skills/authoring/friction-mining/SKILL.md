---
name: friction-mining
description: Mines the user's local Claude Code and Codex history for recurring agent friction such as failed tool calls, retries, denials, interruptions and corrections. Use when asked what agents keep struggling with in a project or across projects. Step 0 of `skill-authoring`.
license: MIT
metadata:
  author: patrykmurzyn
  version: "0.1.1"
  status: experimental
---

# Friction mining

Without this skill, an agent reads the project's own notes (self-reports), ranks one-off stumbles as "most common", and misses the noise that hits every session. Work from trace signals, keep only what repeats or costs a lot, and let the user pick what moves on.

Everything here is read-only. The only writes are into the working folder below.

## 1. Scope

- **project**: sessions whose working directory is inside the project or one of its git worktrees. Findings feed project skills and the project's `AGENTS.md`.
- **global**: every session. Findings feed global skills and global agent instructions.

If the user named neither, ask once, with a guess: "project `(git root of the current directory)`, last 7 days?" Guess global when the current directory is not inside a project. Default period: 7 days.

## 2. Working folder

| Scope | Folder |
| --- | --- |
| project | `(project root)/.friction/` |
| global | `~/.local/state/agent-friction/` |

- Create it if missing, with a `.gitignore` inside that contains `*`, so nothing in it is ever committed and no tracked file changes. Leave the project's own `.gitignore` and `.git/info/exclude` alone.
- In a git repo, confirm with `git check-ignore -q .friction/ledger.txt`; it must exit 0.
- `ledger.txt` lists session IDs to keep out of mining, one per line with a `#` comment: probes, baselines and evals run for this work. Create it if missing.
- Each run writes to a new `(date)-mining/` subfolder (add `-2`, `-3` on the same day). Earlier runs stay untouched.

## 3. Extract

```sh
uv run scripts/signals.py --project PATH --days 7 \
  --exclude-ledger PATH/.friction/ledger.txt --output RUN/signals.json
```

Drop `--project` for global scope. `--format jsonl` gives one line per signal, for drilling into a group. `--help` lists every flag. The script skips the session running it, its subagents and sessions run in temp folders.

Read the summary like this:

- `top_groups`: signals with the same tool and error key, ranked by sessions affected.
- `noise_lines`: lines filling most shell outputs, such as a shell start-up warning. They are one environment finding, and they bury real errors in every quote.
- `error_in_output`: a shell error inside a command that still exited 0. The agent often never noticed it.
- `exploration`: calls before the first edit. Open the slowest sessions to see what the agent was looking for.
- `correction_candidate`: a typed message that starts like a correction. Read each one in context before counting it.
- `repeated_user_text`: the same text pasted into several sessions. The user is re-explaining something, which is a strong finding.

## 4. Confirm in the transcript

Before a theme becomes a finding, open one or two of its sessions at the quoted spot and read about 20 lines around it: what the agent was trying to do, how many calls it took to recover, whether the user had to step in. Find a transcript by its 8-character ID: `~/.claude/projects/*/(ID)*.jsonl`, or for Codex `~/.codex/sessions/**/rollout-*(ID)*.jsonl`. Read the spot with `grep -n`, never the whole file.

## 5. Turn signals into findings

- A finding is one cause, not one error string. Unquoted globs failing in `grep`, `sed` and `ls` are one finding.
- Keep a finding when it shows in 2 or more sessions, or once at high cost: the user interrupted, 5 or more wasted calls, or a wrong result delivered. Everything else goes under "Left out" with its reason.
- Notes, logs and summaries the agents wrote are self-report. Pair each with a trace signal, or mark its basis `self-report`.
- Leave out friction caused by the mining itself and by runs in the ledger.
- Rank by sessions affected, then cost. Show at most 7 findings.
- Give each finding a mechanism hint. The decision belongs to `skill-scoping`.

## 6. Report

Fill in [the findings template](assets/findings.md). Save it as `findings.md`, and the same records as `findings.jsonl`, in the run folder. In chat, send the findings with the folder path, and ask which numbers to take to `skill-scoping`.

This skill only reports. It never creates skills and never edits `AGENTS.md`, settings or memory.

## Privacy

- Quote at most 200 characters, taken from the script output, which redacts tokens, keys, emails and the home path. Check each quote before it leaves the run folder.
- Paraphrase instead of quoting pasted meetings, documents, customer data or anything personal.
- Never open files that a transcript points to, such as `.env` or `.secrets`.

## One session

`friction-probe` uses this skill to check a probe run against its trace:

```sh
uv run scripts/signals.py --session TRANSCRIPT.jsonl --format jsonl
```

## Gotchas

- Claude Code folder names under `~/.claude/projects/` drop characters (`acme.web` becomes `acme-web`). Pass the real project path; the script matches each entry's `cwd`.
- `claude -p` runs and desktop app sessions both log `entrypoint` `sdk-cli`, and most Codex sessions log `codex_exec`. Metadata can't tell a probe from real work: only the ledger can.
- Grepping transcripts for error words misleads. Text such as `InputValidationError` sits in the system prompt of nearly every session. Use the script's structured fields.
- Subagent transcripts are separate files: Claude keeps them under the session's `subagents/` folder, and Codex gives them their own rollout with a `parent_thread_id`. The summary counts them apart.
- In Polish, a message starting "No" usually means "well", not a refusal. Correction candidates need reading.
- Claude Code deletes transcripts after 30 days by default, so a long period may return less than it says.
