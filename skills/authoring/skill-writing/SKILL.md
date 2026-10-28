---
name: skill-writing
description: Writes or edits an agent skill folder (SKILL.md, description, references, scripts) to the Agent Skills spec. Use when a skill's scope is settled and its files need writing or rewriting. Step 2 of `skill-authoring`.
license: MIT
metadata:
  author: patrykmurzyn
  version: "0.2.0"
  status: experimental
---

# Skill writing

Write the smallest skill that fixes what the baseline got wrong. The input is a brief from `skill-scoping`; if there is none, write its fields down first. When reworking, change only what the brief's evidence supports.

## Folder

```text
<name>/
├── SKILL.md      required; under 500 lines and 20,000 bytes
├── references/   detail the agent loads only when needed
├── scripts/      code the agent runs
├── assets/       templates, schemas, data
└── evals/        test cases for `skill-testing`
```

Create only the folders you use. Start from [the template](assets/SKILL.template.md).

## Frontmatter

- `name`: lowercase `a-z`, `0-9` and single hyphens, at most 64 characters, no hyphen at either end, identical to the folder name.
- `description`: at most 1,024 characters (aim for about 250), no XML tags.
- `license`, and `metadata` with string values only (quote versions: `"0.1.0"`).
- `compatibility` only for real requirements, such as "Requires uv and network access".
- Nothing else by default: claude.ai rejects any other field on upload. Read [portability](references/portability.md) before adding an agent-specific one.
- In a skills repo, also follow its `AGENTS.md` (required metadata, versioning).

## Description

The description is the only text an agent sees when it chooses a skill.

- Say what the skill is for and when to use it, in the words a user would type: third person, one or two sentences, trigger words first.
- Never summarize the steps. An agent that reads a workflow in the description follows that summary and skips the body.
- No lists of examples, file types or features. One clear phrase generalizes better than a list.
- Add "Not for X; use `Y`" only for a near miss the wording would otherwise catch.
- For a stage of a router, end with "Step n of `router-name`".
- If tests show it under-triggers, widen *when* it applies (the user's intent, cases where the user never names the domain). Don't paste in keywords from failed queries.

## Body

Order by importance. After context compaction, Claude Code keeps only the first ~5,000 tokens of each skill, so the rules that must survive go first and optional detail goes last or into references.

- Open with at most one sentence on what goes wrong without the skill. Then give only what the agent lacks: local facts, defaults, and the steps the baseline got wrong. Cut general know-how.
- Choose the form of each instruction by the failure it fixes:

| Baseline failure | Write | Avoid |
| --- | --- | --- |
| Knows the rule, skips it under pressure | a prohibition, the excuses it will make with a counter for each, and red flags | soft wording ("prefer", "consider") |
| Output has the wrong shape | a positive recipe: what the output is, its parts, in order | a list of don'ts |
| Leaves out a required part | a required slot in the template it fills in | a reminder in prose |
| Should act differently depending on a condition | a conditional on something observable ("if the brief exists, use it") | a rule plus exceptions |
| Lacks judgment for open-ended work | one or two named concepts that carry a method ("steelman", "inverted pyramid"), how each applies, and questions the agent asks itself | personas, praise |
| Gets an exact procedure wrong | exact commands, a checklist and a validation loop: run the check, fix, re-run until it passes | prose descriptions of the steps |

- Write the positive form. "Answer in two sentences" beats "don't be verbose", which names the thing it forbids.
- No nuance clauses such as "unless it matters": they reopen the rule. Write a real exception as its own conditional.
- Give a default, not a menu: one tool, plus a short escape hatch for the exception.
- Explain why when a rule isn't obvious. Reasons outlast ALWAYS and NEVER.
- Point to living sources (a tool's `--help`, its docs URL) instead of copying them; the environment is the source of truth and a copy goes stale.
- End with a `## Gotchas` section of facts that defy reasonable assumptions. Keep it in SKILL.md, where the agent reads it before it hits the problem.
- For a fixed output format, give a template: inline if short, in `assets/` if long.

## Progressive disclosure

- Move detail needed only sometimes into `references/<topic>.md`, one level deep, linked with relative paths from the skill root.
- Every link says when to read it: "Read the error guide if the API returns a non-200 status", never a bare "see references/".

## Scripts

Bundle a script when every run would rewrite the same logic, or when one exact sequence must run. Read [the script guide](references/scripts.md) before writing one, and list each script in SKILL.md with a one-line purpose and its exact command.

## Other skills

Refer to another skill by name in backticks, with the moment to load it. Don't copy its content and don't link to its files: install paths differ per agent and machine.

## Side effects and state

- A skill that sends, deletes, deploys, spends or edits agent memory or config stays discoverable. Right before that step it shows exactly what will happen and waits for the user's yes. A yes covers that one step only.
- Steps that retry or change external systems need a stopping condition proportional to the risk ("stop after 3 failed deploys and report").
- Make a skill explicit-only only when the user asks for it; [portability](references/portability.md) has the switches.
- A skill never edits `MEMORY.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules` or agent settings without that yes.
- State (config, logs, caches) lives outside the skill folder, in the project or a data directory: installed skills are often symlinks into a shared repo.

## Placement

- Skills repo (it has `scripts/validate.sh`): `skills/<group>/<name>/`, then run `scripts/install.sh`.
- Project-specific: `<repo>/.agents/skills/<name>/` plus a relative symlink in `<repo>/.claude/skills/`.
- Personal, no repo: `~/.agents/skills/<name>/` plus a symlink in `~/.claude/skills/`.

When done, load `skill-testing` to validate and test.

## Gotchas

- Claude Code does not search category subfolders of a skills directory; each skill folder must sit (or be linked) directly inside it.
- Codex lists two skills with the same name side by side and the user must pick; keep names unique.
- Claude Code runs inline shell commands and substitutes its skill-directory variable in SKILL.md bodies; other agents show them as plain text. Don't use either in a portable skill.
- Skill listings are budgeted: Claude Code truncates each description at 1,536 characters and Codex caps the whole list at about 2% of the context, so the trigger words go first.
