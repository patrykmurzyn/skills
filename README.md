# Skills

Small, single-job [Agent Skills](https://agentskills.io) for Claude Code, Codex and any other agent that supports the format. Each skill does one thing well; larger workflows are router skills that call smaller skills by name.

## Catalog

<!-- catalog:start -->
| Group | Skill | What it does | Version | Status |
| --- | --- | --- | --- | --- |
| authoring | [`skill-authoring`](skills/authoring/skill-authoring/SKILL.md) | Creates a new agent skill or reworks an existing one as small, tested, single-job skills. Use when asked to make a skill, turn a workflow into a skill, or split or improve a skill. | 0.2.0 | experimental |
| authoring | [`skill-review`](skills/authoring/skill-review/SKILL.md) | Reviews installed agent skills for unused, misfiring or outdated ones, and turns the user's repeated corrections into skill fixes. Use for a periodic skill check-up, after a new model release, or when skills seem to be ignored. Step 4 of `skill-authoring`. | 0.1.0 | experimental |
| authoring | [`skill-scoping`](skills/authoring/skill-scoping/SKILL.md) | Decides whether a need deserves an agent skill and defines its single job, boundaries and what a fresh agent gets wrong without it. Use before writing or reworking a skill, or when a skill feels too big or overlaps another. Step 1 of `skill-authoring`. | 0.2.0 | experimental |
| authoring | [`skill-testing`](skills/authoring/skill-testing/SKILL.md) | Tests whether an agent skill is valid, loads on the right requests and does better than no skill or its previous version. Use when checking, evaluating or debugging a skill. Step 3 of `skill-authoring`. | 0.2.0 | experimental |
| authoring | [`skill-vetting`](skills/authoring/skill-vetting/SKILL.md) | Checks a third-party agent skill for hidden instructions, risky scripts and overlap before it is installed. Use when the user wants to install or copy a skill from GitHub, skills.sh or any other source. | 0.1.0 | experimental |
| authoring | [`skill-writing`](skills/authoring/skill-writing/SKILL.md) | Writes or edits an agent skill folder (SKILL.md, description, references, scripts) to the Agent Skills spec. Use when a skill's scope is settled and its files need writing or rewriting. Step 2 of `skill-authoring`. | 0.2.0 | experimental |
<!-- catalog:end -->

Skills stay `experimental` until their evals have run and passed.

## Install

Requires git. Validation and evals also need [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/patrykmurzyn/skills.git
cd skills
scripts/install.sh --dry-run   # preview
scripts/install.sh             # link every skill
```

`install.sh` symlinks each skill folder into `~/.agents/skills/` (Codex, Cursor and other clients) and `~/.claude/skills/` (Claude Code), so one `git pull` updates every agent. It never touches a file or folder it didn't create, and `scripts/install.sh --uninstall` removes only its own links.

Start a new agent session after installing: agents discover skills at startup.

## Use

Ask in your own words, for example "turn this workflow into a skill", or call a skill by name: `/skill-authoring` in Claude Code, `$skill-authoring` in Codex.

## Layout

```text
skills/<group>/<skill>/   one folder per skill, grouped by topic
  SKILL.md                frontmatter + instructions (required)
  references/             detail the agent loads on demand
  scripts/                code the agent runs
  assets/                 templates and schemas
  evals/                  trigger and output test cases
scripts/                  repo tooling: install, validate, catalog
```

## Principles

- **One job per skill.** A workflow with stages becomes a router skill plus one small skill per stage.
- **Skills may use other skills,** by name and never by path.
- **Only what the agent lacks.** Every line fixes a mistake a fresh agent would otherwise make.
- **Tested, not trusted.** Every change passes spec validation; a skill becomes `stable` only after trigger evals and with/without-skill output evals.
- **Maintained.** Skills are reviewed against real usage and the user's corrections, re-tested on new models, and retired when a model no longer needs them.
- **Vetted.** Third-party skills are read raw and checked for hidden instructions before they are installed.
- **Portable.** Frontmatter stays within the Agent Skills spec, so the same skill works in Claude Code, Codex, Cursor and claude.ai.

The working rules live in the `skill-authoring` skills and in [AGENTS.md](AGENTS.md).

## Development

```sh
scripts/validate.sh            # spec, size, links, hidden Unicode, secrets
uv run scripts/catalog.py      # regenerate the catalog above
```

For trigger and output evals, use the `skill-testing` skill. CI runs validation and checks that the catalog is up to date on every push.

## License

[MIT](LICENSE)
