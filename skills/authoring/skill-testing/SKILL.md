---
name: skill-testing
description: Tests whether an agent skill is valid, loads on the right requests and does better than no skill or its previous version. Use when checking, evaluating or debugging a skill. Step 3 of `skill-authoring`.
license: MIT
metadata:
  author: patrykmurzyn
  version: "0.2.0"
  status: experimental
---

# Skill testing

A skill that reads well can still be invalid, never load, load on the wrong requests, or do no better than no skill. Test those layers in order and stop at the first that fails. Every run that starts an agent session costs money: tell the user how many sessions a step needs and get a yes first.

## 1. Validate (free, every change)

```sh
uv run scripts/validate_skill.py <skill-dir>...
```

It checks the spec, size limits (500 lines, 20,000 bytes), unfinished placeholders, broken links, hidden Unicode, blank-line padding, HTML comments and secret-like strings, and reports duplicate names. Add `--strict-spec` for skills that may go to claude.ai. Inside a skills repo, run the repo's `scripts/validate.sh` instead. Fix every error and read every warning.

## 2. Micro-test the wording (behaviour-shaping lines)

Before a full eval, test a new or disputed instruction on its own: the same prompt with and without the line, five or more fresh runs per arm, every output read by hand. If the control arm doesn't show the failure, the line isn't needed. If results vary a lot between runs, the wording is ambiguous. Read [micro-tests](references/micro-tests.md) for the script and the procedure.

## 3. Trigger evals

Write `evals/trigger-queries.json` in the skill under test:

```json
{"skill": "<name>", "queries": [
  {"query": "...", "should_trigger": true, "split": "train"}
]}
```

- About 20 realistic queries: half should load the skill, half are near misses that share its words but need something else. Use file paths, casual tone, typos and the user's own language. Add the pre-mortem cases from the brief.
- Put about 40% in `"split": "validation"` and never tune the description on them.
- Should-trigger queries must need the skill. Agents skip skills for simple one-step requests, however well the description matches.

```sh
uv run scripts/trigger_eval.py <skill>/evals/trigger-queries.json --agent claude --runs 3
uv run scripts/trigger_eval.py <skill>/evals/trigger-queries.json --agent codex --runs 3
```

Use `--limit 2 --runs 1` for a cheap smoke test and `--model` to test each model the skill will run on, smaller models included. A query passes at a trigger rate of 0.5 or more if it should load the skill, and below 0.5 if it shouldn't. Fix failures through `skill-writing`: widen when it applies if it under-triggers, add the boundary if it false-triggers. Keep the version with the best validation pass rate, which is not always the last; stop after about five rounds.

## 4. Output evals

Run each case in a fresh context with the skill, and again without it, or with the snapshot of the previous version when reworking. Give the runner the request and the raw inputs only, never the expected answer or the suspected bug. Grade results and process, review the assertions themselves, and pin the model so a model change isn't mistaken for a skill change. Read [the eval guide](references/evals.md) before the first run.

## 5. Pressure tests (discipline skills only)

For a skill whose kind is *discipline*, a calm test proves little: the agent knows the rule and breaks it when rushed. Run pressure scenarios and record the excuses word for word. Read [pressure tests](references/pressure.md) for the method.

## 6. Iterate

Hand `skill-writing` the failed assertions, the user's feedback and what the transcripts show:

- logic every run rewrote, which becomes a bundled script;
- instructions the agent followed though they didn't apply, which get cut;
- reference files it never opened or kept re-reading, which get moved or merged.

Generalize instead of patching single cases, keep the skill lean, bump `metadata.version`, and re-run. Stop when feedback is empty or the gains stop. Set `status: stable` only after the evals pass.

## Gotchas

- Your own session is not a fresh context. You know what the skill should do, so your run proves nothing; test in a new one.
- `trigger_eval.py` runs each query in an empty temp directory, so project `AGENTS.md` files and project skills don't leak into the result. The skill under test must be installed globally.
- Codex trigger detection is heuristic: it looks for the skill's SKILL.md in Codex's item events. Confirm surprising results in a transcript.
- A grader that only checks "the skill was used" inflates the with-skill score; leave it out of the with/without comparison.
- A skill with identical results with and without it adds nothing. Cut it or rescope it with `skill-scoping`.
