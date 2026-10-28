# Micro-tests of wording

Read this before adding or rewording an instruction that should change behaviour. A micro-test isolates one line, so you learn whether that line works before paying for a full eval. The method follows obra/superpowers' writing-skills.

## Procedure

1. Write `prompt.md`: one realistic request that exposes the failure, with any input inline.
2. Write `guidance.md`: only the candidate instruction, worded as it would appear in the skill. For two candidate wordings, write two files and run each as its own arm.
3. Run both arms in fresh sessions, five or more reps each:

   ```sh
   uv run scripts/micro_test.py prompt.md --guidance guidance.md --reps 5 --out <name>-workspace/micro/<instruction>
   ```

   Add `--flag REGEX` to count a pattern that signals the failure; the counts only point you to outputs to read.
4. Read every output in both arms, and every flagged match, by hand. A regex hit is not a verdict.
5. Decide:
   - the control arm never fails: drop the line, the agent already behaves;
   - the guidance arm fails as often as the control: reword it (check the form against the failure type in `skill-writing`), or the instruction is the wrong tool;
   - the guidance arm is consistent and the control isn't: keep the line;
   - either arm varies a lot between reps: the wording is ambiguous; add an example or a default.

## Rules

- Always keep a no-guidance control arm. Without it, you can't tell the line's effect from the model's habits.
- One instruction per test. Several lines at once can't tell you which one worked.
- Variance is a result, not noise to average away.
- Don't add a nuance clause to a wording that won ("unless it matters"): in superpowers' tests one such clause turned a consistent result noisy.
