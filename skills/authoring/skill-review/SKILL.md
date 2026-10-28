---
name: skill-review
description: Reviews installed agent skills for unused, misfiring or outdated ones, and turns the user's repeated corrections into skill fixes. Use for a periodic skill check-up, after a new model release, or when skills seem to be ignored. Step 4 of `skill-authoring`.
license: MIT
metadata:
  author: patrykmurzyn
  version: "0.2.0"
  status: experimental
---

# Skill review

Skills decay quietly: descriptions stop matching how the user asks, new models outgrow them, and corrections the user keeps repeating never reach the skill. Review on a schedule, and change nothing without the user's yes.

## 1. Usage

```sh
uv run scripts/usage.py --days 30
```

It reads the local Claude Code and Codex transcripts, read-only, and reports per installed skill the number of sessions that used it, per agent, and the last use, plus installed skills never used. In Claude Code, `/skill-doctor` adds what each skill costs in context. Read the result like this:

- Never used, though the user did that kind of task: it under-triggers. Run trigger evals with `skill-testing`.
- Never used, and nobody does that task: a candidate to hide or retire.
- Used often: the skill most worth testing well.

## 2. Corrections

Read only the sessions where the reviewed skill ran:

```sh
uv run scripts/usage.py --sessions SKILL --days 30
```

In each, find the moments after the skill loaded where the user corrected the agent or explained the same thing again. Quote each correction word for word, then route it:

- caused by the skill's instructions or a gap in them: a gotcha and an eval case for that skill (`skill-writing`, then `skill-testing`);
- a rule the skill states and the agent broke: set the skill's kind to discipline and run pressure tests (`skill-testing`).

Repeated friction outside any skill's sessions is not this step: load `friction-mining` for it.

Never copy secrets or personal data from a transcript into a skill.

## 3. New model release

Re-run each skill's evals with the new model pinned (`skill-testing`). If the no-skill arm now passes, the skill isn't broken; it is no longer needed. Propose retiring it, starting with capability-uplift skills. If results drop, the skill needs rework.

## 4. Decide per skill

| Finding | Proposal |
| --- | --- |
| Works and gets used | keep |
| Under-triggers or false-triggers | fix the description (`skill-writing`, then trigger evals) |
| Repeated corrections | add gotchas and eval cases (`skill-writing`) |
| Overlaps another skill, or does two jobs | rescope (`skill-scoping`, rework mode) |
| Rarely needed but worth keeping | hide it: Claude Code `skillOverrides` set to `name-only` or `off`; disable it in Codex config |
| Outgrown by the model, or dead | retire it: `status: deprecated`, a CHANGELOG entry, callers updated, removed in the next release |

## 5. Report

Fill in [the report template](assets/report.md) and send it in one message. Ask for a yes per proposal, then apply only the approved ones through the skill named in the table.

## Schedule

Run monthly and after each model release. A recurring run (cron, a scheduled agent task) changes the user's setup: propose it, and set it up only after a yes. An unattended run only writes the report; it never edits a skill.

## Gotchas

- Claude Code deletes old transcripts (after 30 days by default), so "never used" means "not in the kept history".
- A skill the user starts by typing `/name` may not appear as a Skill tool call, so `usage.py` can undercount skills invoked by hand.
- Codex counts are heuristic: they count tool calls that read a skill's SKILL.md, not the skill list Codex puts in its own prompt.
