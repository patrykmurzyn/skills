# Agent instructions

This repo holds public Agent Skills. README.md covers the layout and install.

- Create or change a skill with the `skill-authoring` skill: find friction (optional), then scope, write and test. New skills never skip scoping. Friction findings from `friction-mining` or `friction-probe` are input to scoping, never a skill by themselves. Vet third-party skills with `skill-vetting`, and review installed ones with `skill-review`.
- One job per skill. Related skills share a group folder, `skills/<group>/`. Names are unique across the repo.
- When a skill in a group is added, renamed or removed, update the group's router skill in the same change.
- Every change to a skill names the failure it fixes (a baseline run, a failed eval or a user correction) in the commit message.
- Frontmatter: `name`, `description`, `license: MIT`, and `metadata` with `author: patrykmurzyn`, `version` (quoted semver) and `status` (`experimental`, `stable` or `deprecated`). Nothing else: claude.ai rejects other fields, and `scripts/validate.sh` does too.
- Bump `metadata.version` on every change to a skill: patch for wording, minor for new behaviour, major for a changed contract. Set `stable` only after the skill's evals have run and passed. A `deprecated` skill is removed in the next release.
- Skills refer to other skills by name in backticks, never by path.
- Write skills and docs in English.
- After any change, `scripts/validate.sh` must pass. Then run `uv run scripts/catalog.py` and add a line to CHANGELOG.md under Unreleased.
- Fixtures that are meant to fail live in `evals/files/`; the tooling skips that folder.
- Eval workspaces (`*-workspace/`) stay out of git.
- Install third-party skills with their own tool after vetting; don't copy them here. A modified fork keeps its license and names its origin in `metadata.source`.
- This repo is public: no secrets, personal data or machine-specific paths.
- Don't push, tag or publish without the owner's explicit yes.
