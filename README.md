# Skills

[![validate](https://github.com/patrykmurzyn/skills/actions/workflows/validate.yml/badge.svg)](https://github.com/patrykmurzyn/skills/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Small, tested [Agent Skills](https://agentskills.io) for Claude Code, Codex and any agent that supports the format. Their first job is helping you build good skills of your own.

## Why

Most skills are written in one pass: long, generic, and never checked against what an agent actually gets wrong. They restate what the model already knows, try to do three jobs at once, and quietly stop working when models or habits change.

These skills turn skill-building into a short, evidence-driven loop. Find where agents really struggle, decide whether that even needs a skill, write the smallest skill that fixes it, prove it beats working without it, and keep it honest over time. Each skill does one job; a router skill ties them together.

## How it works

```text
 0. find friction          1. scope           2. write          3. test           4. maintain
 friction-mining     ──►   skill-scoping ──►  skill-writing ──► skill-testing ──► skill-review
 friction-probe            (is it a skill?)   (to the spec)     (does it help?)   (usage, new models)

 skill-authoring routes between the steps · skill-vetting checks other people's skills before install
```

- **Evidence first.** Mining your real Claude Code and Codex history, or sending a fresh agent through a real task, shows what agents actually stumble on.
- **Not everything is a skill.** Scoping often ends in a line in `AGENTS.md`, a script or a hook instead.
- **Tested against a baseline.** A skill earns its place only if it beats a fresh agent working without it.

## Install

Pick **one** method per agent; installing the same skills twice loads them twice. Start a new agent session afterwards: skills are discovered at startup.

<details>
<summary><b>Claude Code</b> (plugin)</summary>

```text
/plugin marketplace add patrykmurzyn/skills
/plugin install authoring@patrykmurzyn
```

On Claude Code 2.1.275 or later, one step works too: `/plugin install authoring --marketplace patrykmurzyn/skills`. Plugin skills are namespaced, so the router is `/authoring:skill-authoring`.

</details>

<details>
<summary><b>Codex, Cursor and other agents</b> (<code>skills</code> CLI)</summary>

```sh
npx skills add patrykmurzyn/skills                          # pick skills and agents interactively
npx skills add patrykmurzyn/skills --skill skill-authoring  # a single skill
```

</details>

<details>
<summary><b>From source</b> (symlinks, for development)</summary>

```sh
git clone https://github.com/patrykmurzyn/skills.git
cd skills
scripts/install.sh --dry-run   # preview
scripts/install.sh             # link every skill
```

`install.sh` links each skill folder into `~/.agents/skills/` (Codex, Cursor and others) and `~/.claude/skills/` (Claude Code), so one `git pull` updates every agent. It never touches a file it didn't create; `scripts/install.sh --uninstall` removes only its own links. Validation and evals need [uv](https://docs.astral.sh/uv/).

</details>

## Use

Ask in your own words. The right skill loads from its description:

| You say | Loads |
| --- | --- |
| "What do my agents keep struggling with in this repo?" | `friction-mining` |
| "Have a fresh agent try ticket #42 and tell me where it gets lost." | `friction-probe` |
| "Turn what we just did into a skill." | `skill-authoring` |
| "Does my changelog skill actually help?" | `skill-testing` |
| "Install the skill from github.com/someone/skills." | `skill-vetting` |

Or call one by name: `/skill-authoring` in Claude Code (`/authoring:skill-authoring` as a plugin), `$skill-authoring` in Codex.

## Catalog

<!-- catalog:start -->
| Skill | What it does | Group | Status |
| --- | --- | --- | --- |
| [`friction-mining`](skills/authoring/friction-mining/SKILL.md) | Mines the user's local Claude Code and Codex history for recurring agent friction such as failed tool calls, retries, denials, interruptions and corrections. | authoring | experimental |
| [`friction-probe`](skills/authoring/friction-probe/SKILL.md) | Sends a fresh agent through a real task in a project and records where it gets lost, what confused it and what it had to guess. | authoring | experimental |
| [`skill-authoring`](skills/authoring/skill-authoring/SKILL.md) | Creates a new agent skill or reworks an existing one as small, tested, single-job skills. | authoring | experimental |
| [`skill-review`](skills/authoring/skill-review/SKILL.md) | Reviews installed agent skills for unused, misfiring or outdated ones, and turns the user's repeated corrections into skill fixes. | authoring | experimental |
| [`skill-scoping`](skills/authoring/skill-scoping/SKILL.md) | Decides whether a need deserves an agent skill and defines its single job, boundaries and what a fresh agent gets wrong without it. | authoring | experimental |
| [`skill-testing`](skills/authoring/skill-testing/SKILL.md) | Tests whether an agent skill is valid, loads on the right requests and does better than no skill or its previous version. | authoring | experimental |
| [`skill-vetting`](skills/authoring/skill-vetting/SKILL.md) | Checks a third-party agent skill for hidden instructions, risky scripts and overlap before it is installed. | authoring | experimental |
| [`skill-writing`](skills/authoring/skill-writing/SKILL.md) | Writes or edits an agent skill folder (SKILL.md, description, references, scripts) to the Agent Skills spec. | authoring | experimental |
<!-- catalog:end -->

All skills are `experimental` until their trigger and output evals have run and passed.

## Safety

Skills steer your agent's tools and shell, so read a skill before you install it, including this repo's. `skill-vetting` does that check for you on any third-party skill. Skills here that read your agent history do so read-only and locally, redact secrets from anything they quote, and ask before any step that costs money or changes your setup.

`evals/files/` folders hold deliberately broken or malicious-looking test fixtures. They are named `SKILL.fixture.md`, so no agent loads them as skills.

## Principles

- **One job per skill.** A workflow with stages becomes a router plus one small skill per stage; skills refer to each other by name, never by path.
- **Only what the agent lacks.** Every line fixes a mistake a fresh agent would otherwise make.
- **Change on evidence.** Every change names the failure it fixes: a baseline run, a failed eval or a user correction.
- **Portable.** Frontmatter stays within the Agent Skills spec, so the same skill works in Claude Code, Codex, Cursor and claude.ai.

## Development

```text
skills/<group>/<skill>/   one folder per skill
  SKILL.md                frontmatter + instructions
  references/ scripts/ assets/
  evals/                  trigger queries, output cases, fixtures
scripts/                  install.sh · validate.sh · catalog.py
.claude-plugin/           marketplace manifest
```

```sh
scripts/validate.sh            # spec, size, links, hidden Unicode, padding, secrets, nested skills
uv run scripts/catalog.py      # regenerate the catalog above
```

Trigger and output evals run through the `skill-testing` skill. CI runs validation and the catalog check on every push. See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) for the rules, and [CHANGELOG.md](CHANGELOG.md) for history.

## License

[MIT](LICENSE)
