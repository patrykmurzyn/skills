---
name: skill-authoring
description: Creates a new agent skill or reworks an existing one as small, tested, single-job skills. Use when asked to make a skill, turn a workflow into a skill, or split or improve a skill.
license: MIT
metadata:
  author: patrykmurzyn
  version: "0.3.1"
  status: experimental
---

# Skill authoring

Skills written in one pass tend to be long, generic and untested. Route the work through small skills instead, loading only the one the current step needs.

| Step | Skill | Job | Done when |
| --- | --- | --- | --- |
| 0 | `friction-mining` or `friction-probe` | Find what agents struggle with: mine past sessions, or send a fresh agent through a real task | the user picks findings to scope |
| 1 | `skill-scoping` | Decide whether it should be a skill at all, give it one job, find what a fresh agent gets wrong without it | the user agrees to the brief |
| 2 | `skill-writing` | Turn the brief into a spec-valid skill folder | files written, validation passes |
| 3 | `skill-testing` | Prove it triggers on the right requests and beats working without it | evals pass, or the gaps are reported |
| 4 | `skill-review` | Keep released skills healthy: usage, corrections, new models, retirement | run monthly and after each model release |

Start where the request starts:

- "What do my agents keep struggling with?" or "what should I build next?": step 0. Past sessions exist: `friction-mining`. A new project or one specific task: `friction-probe`.
- New skill, workflow to capture, or "split this skill": step 1.
- Rework of an existing skill: step 1 in rework mode, so the current version becomes the baseline.
- "This skill fires on the wrong requests" or "does it work?": step 3, then step 2 for the fix.
- A small wording change to a skill whose scope is fine: step 2, then validation from step 3.
- Installing someone else's skill is not authoring: load `skill-vetting`.

## House rules

These are this repo's opinionated rules. They apply to every step and override general habits; a user's own instructions still come first.

- **One job per skill.** Prefer several small skills to one large one. A workflow with stages becomes a router like this one plus one skill per stage, and each stage skill must be useful on its own. When a stage skill is added, renamed or removed, update its router's table in the same change.
- **Skills may use other skills.** Refer to them by name in backticks and say when to load them ("once the files exist, load `skill-testing`"). Never point at another skill's files by path: install locations differ per agent and per machine.
- **Spend context only on what the agent lacks.** Each line must fix a mistake a fresh agent would make.
- **Change on evidence.** Every new line answers an observed failure: a baseline run, a test, or a user correction. Name it when you propose the change.
- **Ask right before acting.** A skill that sends, deletes, deploys, spends or edits agent memory and config stays discoverable, and asks the user for a yes immediately before that step, naming exactly what will happen.
- **Ask once per step.** Put all questions in one message, each with your guess and the default you'll use.
