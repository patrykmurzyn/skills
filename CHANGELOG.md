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
- `friction-mining` 0.1.0: mines local Claude Code and Codex transcripts for recurring agent friction (`signals.py`: tool errors, shell errors in commands that exited 0, denials, interrupts, retries, compactions, correction candidates, noise lines, calls before the first edit, repeated user text), with redacted quotes and the shared findings template. Baseline: an unaided agent ranked one-off issues from self-reported notes and missed shell noise present in most sessions.
- `friction-probe` 0.1.0: sends a fresh read-only agent through a real task with a friction-log prompt, records its session in a ledger, and checks the log against the trace. Baseline: an unaided agent asked task-design questions and kept no record of where the project slowed it down.

### Changed

- Repo: Claude Code marketplace manifest (`.claude-plugin/marketplace.json`, plugin `authoring`), README rewritten with per-agent install, usage examples and a safety note, `CONTRIBUTING.md`, one-line catalog entries.
- Eval fixtures that look like skills are named `SKILL.fixture.md` and documented in `evals/files/README.md`; `validate.sh` fails on any nested `SKILL.md`. Observed failure: Codex scans skill folders recursively and loaded both fixtures as real skills.
- `skill-authoring` 0.3.1, `skill-testing` 0.2.1, `skill-vetting` 0.1.1, `friction-mining` 0.1.1: neutral example names, fixture naming rule, wording of the router's house rules.
- `skill-authoring` 0.3.0: step 0 (discovery) routes to `friction-mining` and `friction-probe`.
- `skill-review` 0.2.0: the corrections step reads only sessions where the reviewed skill ran (`usage.py --sessions SKILL`); friction across all history moves to `friction-mining`.
- `skill-scoping` 0.2.1: friction findings are an evidence source.
