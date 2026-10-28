# Contributing

Thanks for helping. This repo is opinionated about what makes a good skill, so a few rules keep it that way.

## Issues

The most useful issue shows a skill failing: what you asked, what the agent did, and which skill loaded (or didn't). Include the agent and model you used.

## Pull requests

- **Name the failure your change fixes:** a baseline run, a failed eval or a real session where the skill went wrong. Changes without an observed failure are usually declined.
- **One job per skill.** If a change adds a second job, it is probably a new skill.
- **Use the skills to change the skills.** `skill-authoring` routes you through scoping, writing and testing; [AGENTS.md](AGENTS.md) lists the repo rules your agent will follow.
- **Before you push:**

  ```sh
  scripts/validate.sh
  uv run scripts/catalog.py
  ```

  Bump the skill's `metadata.version` and add a line to [CHANGELOG.md](CHANGELOG.md) under Unreleased.

- **Fixtures:** test files that look like skills go in `evals/files/` and are named `SKILL.fixture.md`, never `SKILL.md`.

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE).
