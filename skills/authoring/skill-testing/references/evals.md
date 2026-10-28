# Output evals

Read this before the first with/without-skill run. The method follows https://agentskills.io/skill-creation/evaluating-skills, Anthropic's skill-creator and OpenAI's eval-skills guidance.

## Test cases

`evals/evals.json` in the skill under test:

```json
{
  "skill_name": "<name>",
  "evals": [
    {
      "id": 1,
      "prompt": "A realistic request, with paths and context, as a user would type it.",
      "expected_output": "What success looks like, in plain words.",
      "files": ["evals/files/input.csv"],
      "assertions": []
    }
  ]
}
```

- Start with 2–3 cases: varied phrasing and detail, at least one edge case, and the pre-mortem cases from the brief.
- Each manual correction the user had to make is a candidate case.
- Fixtures go in `evals/files/`. Fixtures meant to fail validation are fine there.
- Leave `assertions` empty until you have seen the first outputs; you rarely know what good looks like before that.

## Workspace

Keep results next to the skill, never inside it, and out of git:

```text
<name>-workspace/
└── iteration-1/
    ├── eval-<short-id>/
    │   ├── with_skill/      outputs/, transcript, timing.json, grading.json
    │   └── without_skill/   (or old_skill/ when reworking)
    ├── benchmark.json
    └── feedback.json
```

When reworking, snapshot the current version first (`cp -r <skill> <name>-workspace/skill-snapshot/`) and use it as the baseline arm, `old_skill/`. A rework is judged against the old version, not against no skill.

## Runs

- Each run starts with a clean context: a subagent or a headless session (`claude -p`, `codex exec`).
- Give the runner the skill path (or none), the prompt, the input files and an output folder in a temp workspace. Never give it the expected answer, the suspected bug or your conclusions.
- Pin the model for every arm (`--model`), and repeat on each model the skill must support.
- Keep the transcript, and record `timing.json` as `{"total_tokens": n, "duration_ms": n}` as soon as a run ends. Subagent notifications report these and they aren't saved anywhere else. `codex exec --json` reports token usage in its events.

## Graders

Give each case one grader on the result and one on the process.

- **Result:** assertions that are specific and checkable ("the output is valid JSON", "the report lists at least 3 risks"). Test behaviour, not wording: no exact phrases, headings or regexes over generated prose.
- **Process:** from the transcript, check the skill loaded (with-skill arm only), the tools ran in the right order, the agent didn't thrash (count commands and retries), and the token cost.
- Grade each assertion PASS or FAIL in `grading.json`, quoting evidence from the output. No evidence, no PASS: a heading without substance fails.
- Use a script for mechanical checks and an LLM for judgment. Use a blind comparison, where the judge doesn't know which arm is which, to compare two versions that both pass.

## Review the assertions too

While grading, flag assertions that are trivially satisfied, and outcomes that matter but no assertion checks. A passing grade on a weak assertion is worse than none: it creates false confidence. Fix the assertions before the next iteration.

## Analyse

Aggregate to `benchmark.json`: pass rate, time and tokens per arm, and the delta. Then:

- Drop assertions that pass in both arms; they don't measure the skill.
- Fix or drop assertions that fail in both; the case or the assertion is broken.
- Leave with-only graders ("skill loaded") out of the delta.
- Study assertions that pass only with the skill: that is the skill's value.
- Flag any assertion that does worse with the skill: the skill hurts there.
- Treat high variance between runs as a finding (ambiguous instructions).
- Weigh the cost: a skill that doubles tokens for a 2-point gain may not be worth it.
- Ask the user to review the outputs and record specific comments in `feedback.json`; an empty entry means the case looked fine.
