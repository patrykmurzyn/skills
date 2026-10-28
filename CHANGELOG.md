# Changelog

Notable changes to this repo. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Each skill carries its own version in `metadata.version`.

## [Unreleased]

### Added

- Repo tooling: `scripts/install.sh`, `scripts/validate.sh`, `scripts/catalog.py` and a CI workflow.
- `authoring` group: `skill-authoring` (router), `skill-scoping`, `skill-writing`, `skill-testing`, all experimental.
- `skill-review` 0.1.0: usage report from local Claude Code and Codex transcripts (`usage.py`), corrections to fixes, re-tests on new models, hide and retire.
- `skill-vetting` 0.1.0: checks third-party skills for concealment, protected-file writes, risky code and overlap before install.
- `skill-testing` 0.2.0: wording micro-tests (`micro_test.py`), pressure tests for discipline skills, process graders, assertion review, `--model` for trigger evals; the validator now catches blank-line padding, unfinished placeholders, files of 20,000 bytes or more, and (with `--strict-spec`) fields claude.ai rejects.
- `skill-writing` 0.2.0: the instruction form follows the failure type, descriptions never summarize steps, compaction-aware ordering, ask-before-mutation for side effects, state kept outside the skill folder.
- `skill-scoping` 0.2.0: kind (judgment, fragile, discipline, reference) and lifetime (capability uplift, encoded preference), rework mode with Chesterton's fence and caller checks, pre-mortem, evidence from project artifacts.
- `skill-authoring` 0.2.0: step 4 (`skill-review`), entry to `skill-vetting`, router-sync and change-on-evidence rules.
