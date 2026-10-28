# Portability across agents

Read this when choosing where a skill is installed, or before adding a frontmatter field outside the Agent Skills spec. Checked against vendor documentation in October 2026; agents change quickly, so confirm in the linked docs when a detail matters.

## Where agents load skills

| Folder | Claude Code | Codex | Cursor |
| --- | --- | --- | --- |
| `~/.agents/skills/` | no | yes | yes |
| `~/.claude/skills/` | yes | no | yes |
| `<repo>/.agents/skills/` | no | yes, from the working directory up to the repo root | yes |
| `<repo>/.claude/skills/` | yes, from the working directory up to the repo root | no | yes |
| Plugins | yes, named `plugin:skill` | yes | yes |

- Keep one real copy in `.agents/skills/` and symlink it into `.claude/skills/`. All three agents follow symlinks; extra copies drift apart.
- Claude Code loads a skill once even when several folders point at it. Personal skills win over project skills with the same name. `synced` is reserved.
- Codex shows same-name skills side by side, ships its own `skill-creator`, and caps the initial skill list at about 2% of the context window, shortening descriptions first.

## Frontmatter beyond the spec

The spec defines `name`, `description`, `license`, `compatibility`, `metadata` and the experimental `allowed-tools`. Agents that don't know a field ignore it, so a skill that relies on one behaves differently elsewhere. Uploading to claude.ai, or packaging, fails with "Unexpected key(s) in SKILL.md frontmatter" for any other field.

| Field | Works in | Effect |
| --- | --- | --- |
| `disable-model-invocation` | Claude Code, Cursor | loads only when invoked by name |
| `paths` | Claude Code, Cursor | loads only for matching files |
| `user-invocable` | Claude Code | `false` hides the skill from the `/` menu |
| `allowed-tools`, `disallowed-tools` | Claude Code | pre-approves or removes tools while the skill runs |
| `model`, `effort` | Claude Code | overrides the model or effort for the turn |
| `context: fork`, `agent` | Claude Code | runs the skill in a subagent |

Codex keeps its extras outside the frontmatter, in `agents/openai.yaml` inside the skill folder: display name, icon, invocation policy and tool dependencies such as MCP servers.

## Explicit-only skills

The default for a skill with side effects is to stay discoverable and ask for a yes right before the step (OpenAI's Codex skill-creator takes the same line: "Do not infer explicit-only invocation from sensitive operations"). Make a skill explicit-only only when the user asks; then set both switches:

```yaml
# SKILL.md frontmatter (Claude Code, Cursor)
disable-model-invocation: true
```

```yaml
# agents/openai.yaml (Codex)
policy:
  allow_implicit_invocation: false
```

A plain request never loads an explicit-only skill. If agents should know it exists, add a one-line pointer in the project's `AGENTS.md`.

## Hiding without deleting

- Claude Code: the `skillOverrides` setting maps a skill name to `on`, `name-only`, `user-invocable-only` or `off`, without editing its SKILL.md. Plugin skills are managed in `/plugin` instead.
- Codex: disable a skill in its config rather than deleting the folder.

## Context budgets

- Claude Code truncates `description` plus `when_to_use` at 1,536 characters in the listing.
- After compaction, Claude Code re-attaches each invoked skill's first 5,000 tokens, within a 25,000-token budget shared by all skills, most recent first.
- Codex caps the initial skill list at about 2% of the context window.

## Sources

- Agent Skills specification: https://agentskills.io/specification
- Claude Code skills: https://code.claude.com/docs/en/skills
- Codex skills: https://developers.openai.com/codex/skills
- Cursor skills: https://cursor.com/docs/skills
- Placement notes adapted from overment's skill-shaper (MIT): https://github.com/overment/skills
