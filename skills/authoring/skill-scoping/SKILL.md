---
name: skill-scoping
description: Decides whether a need deserves an agent skill and defines its single job, boundaries and what a fresh agent gets wrong without it. Use before writing or reworking a skill, or when a skill feels too big or overlaps another. Step 1 of `skill-authoring`.
license: MIT
metadata:
  author: patrykmurzyn
  version: "0.2.0"
  status: experimental
---

# Skill scoping

Most weak skills fail before a line is written: they restate what the model already knows, or try to do three jobs. Produce a brief before any file changes.

## 1. Gather evidence

Read before you ask. The best sources are concrete and local:

- the conversation: steps that worked, corrections the user made, formats going in and out;
- project artifacts: `AGENTS.md`, runbooks, scripts, schemas, review comments, issues, and the git history of fixes, which shows what actually went wrong;
- the skills your agent already lists.

Generic best-practice articles are not evidence. Ask only what the sources can't settle, and label guesses: "my guess is X, because Y".

## 2. Decide whether it is a skill

Pick the lightest mechanism that prevents the failure:

| The need | Use |
| --- | --- |
| One right answer that code can check | a script, CI check or hook |
| A short rule that should always apply | a line in `AGENTS.md` |
| Work that needs its own context, model or tools | a subagent, not a skill |
| A procedure or judgment used in the current thread, only when relevant | a skill |
| Judgment plus a step that must never be skipped | a thin skill plus a guard (script or hook) |

If it isn't a skill, name the mechanism, say why, and stop.

## 3. Cut it to one job

- Write the job as one sentence with one main verb. If it needs "and", you probably have two skills.
- Each request should belong to exactly one skill. On overlap, extend the neighbour, or record the boundary as "Not for X; use `Y`".
- A workflow with stages becomes a router (a table of steps and skills) plus one small skill per stage. Each stage skill must also work alone.
- Too narrow fails too: two skills that always load together should be one.

## 4. Classify it

- **Kind**, which decides how `skill-writing` steers and how `skill-testing` tests:
  - *judgment*: writing, review, design;
  - *fragile*: exact commands or formats;
  - *discipline*: a rule the agent knows but skips under pressure;
  - *reference*: facts to look up.
- **Lifetime**, which decides when `skill-review` retires it:
  - *capability uplift*: teaches what the model can't yet do; a newer model may make it unnecessary;
  - *encoded preference*: the user's or team's way of working; it lasts.

## 5. Run a baseline

When the task is safe to run, have a fresh agent with the same tools do one realistic task without the skill: a subagent, `claude -p` or `codex exec`. Give it the request and the raw inputs only, never the answer you expect or the problem you suspect. Your own attempt doesn't count, because you already know too much. If you can't start one, give the user the prompt to run.

Record what it got wrong: that is the skill's content. If it got nothing wrong, the skill may not be needed.

## 6. Pre-mortem

Picture three failures: it loads on the wrong request, it stays silent when needed, it acts without permission. Note each one that is plausible; `skill-testing` turns them into test cases.

## 7. Write the brief

Fill in [the brief template](assets/brief.md) and show it to the user in one message, open questions first. Once they agree, load `skill-writing`.

## Rework mode

When the skill already exists:

- The current version is the baseline. Snapshot it before anything changes.
- Before removing a rule, find out why it was added (Chesterton's fence): check the git log, the changelog and the user's past corrections.
- Before renaming, splitting or removing a skill, find its callers: routers that list it, skills and `AGENTS.md` files that name it.

## Gotchas

- Lists and rules the user edits (a style list, a glossary) belong in the project, not in the skill folder, unless the skill is personal.
- Avoid names of built-in skills such as `skill-creator` and `create-skill`.
