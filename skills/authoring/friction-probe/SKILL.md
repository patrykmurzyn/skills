---
name: friction-probe
description: Sends a fresh agent through a real task in a project and records where it gets lost, what confused it and what it had to guess. Use when the user wants to see what an agent struggles with in a codebase before improving skills, AGENTS.md or docs. Step 0 of `skill-authoring`.
license: MIT
metadata:
  author: patrykmurzyn
  version: "0.1.0"
  status: experimental
---

# Friction probe

Given a task and an invitation to ask questions, an agent writes a good plan and asks about the task's design, but keeps no record of where the project itself slowed it down. This skill gets that record from an agent that knows nothing yet, then checks it against the run's trace.

The probe never edits the project. Its proposed fix is a by-product: hand it over, don't apply it.

## 1. Pick the task

- Use a real task from the user: a ticket, an issue, a bug. If there is none, propose two from the project (open issues, recent fix commits) and ask.
- The task must make the agent search more than one area of the project. A one-file change shows almost nothing: a baseline probe asked to add a flag to one script finished in 3 turns with a single friction note.
- Write down what you already know about the answer, and keep it out of the prompt. Your hints would hide exactly the friction you want to see.

## 2. Prepare the run

- Working folder: `(project root)/.friction/`, created if missing with a `.gitignore` inside that contains `*`. In a git repo, confirm with `git check-ignore -q .friction/ledger.txt`.
- Run folder: `.friction/(date)-probe-(short task slug)/`. Save the filled-in prompt there as `prompt.md`.
- Fill in [the probe prompt](assets/probe-prompt.md) with the task, word for word.
- Record `git status --porcelain` before the run. Tool flags don't make a shell read-only.

## 3. Run it, after a yes

Default: a fresh headless agent from the family you are running in, started in the project root. A headless run is a paid session, so first tell the user the agent, the model, the turn cap (default 30) and that it can't edit files, and wait for a yes.

Claude Code:

```sh
claude -p "$(cat RUN/prompt.md)" --disallowedTools "Edit Write NotebookEdit" \
  --max-turns 30 --output-format json > RUN/result.json
```

Codex:

```sh
codex exec --sandbox read-only --json -o RUN/answer.md "$(cat RUN/prompt.md)" > RUN/events.jsonl
```

If the user wants you to do the task yourself instead, keep the same friction log as you work, starting before your first search. Mark every entry's basis `self-report` until step 5.

## 4. Record it

- Add the probe's session ID to `.friction/ledger.txt` with a comment, so `friction-mining` never counts the probe as real work. Claude: `session_id` in `result.json`. Codex: `thread_id` in the `thread.started` event of `events.jsonl`.
- Compare `git status --porcelain` with the run before. If anything changed, tell the user what and ask before reverting.
- A Claude run that hit the turn cap ends with `subtype` `error_max_turns`. Treat its log as partial and say so.

## 5. Check the log against the trace

Self-reports leave out confusion the agent settled by guessing. Load `friction-mining` and extract the probe's own transcript in its one-session mode. The transcript is `~/.claude/projects/*/(session ID).jsonl` or `~/.codex/sessions/**/rollout-*(thread ID).jsonl`.

For each log entry, find its trace: the empty searches, files read twice, failed commands. Then:

- in the log and in the trace: basis `both`;
- only in the log: basis `self-report`;
- only in the trace (an error the probe never mentioned, a long search before the first useful read): add it, basis `trace`.

## 6. Report

Write the findings in the record format from `friction-mining` (its findings template) and save them in the run folder. One probe gives a frequency of 1 of 1; say so. A probe finding stands on its own only at high cost. Otherwise mark it to confirm with a second probe or with `friction-mining`.

Send the findings, the probe's proposed fix as a separate short section, and the run folder path. Ask which findings go to `skill-scoping`. Never edit skills, `AGENTS.md` or docs from here.

## Gotchas

- `--disallowedTools` leaves Bash open, so a Claude probe can still write files. The prompt forbids it and the `git status` check catches it. Codex's read-only sandbox blocks writes itself.
- Headless runs look like real sessions in the history (the same `sdk-cli` or `codex_exec` entry point), so the ledger is the only way to keep them out of mining.
