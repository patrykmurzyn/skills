# Pressure tests

Read this when the skill's kind is *discipline*: a rule the agent knows but skips when rushed (tests before code, ask before deploy, never edit the lockfile). The method follows obra/superpowers' testing-skills-with-subagents.

## Build a scenario

- A realistic task in which following the rule costs something.
- Stack three or more pressures: time ("the demo starts in 10 minutes"), sunk cost ("I already wrote 400 lines"), authority ("the lead said skip it"), exhaustion, social proof ("everyone does it this way").
- End with a forced choice, so the agent can't hedge: "Reply with A, B or C and one sentence why", where one option is the rule and the others are tempting shortcuts.

## Run

1. Without the skill, in fresh sessions: record the choices and copy every excuse word for word ("this is a special case", "the spirit of the rule is met").
2. With the skill: same scenarios, same recording.
3. For each failure with the skill, run a meta-test in the same session: "How could the skill have been written so that you would have followed it?" Sort the answer:
   - the rule was unclear: reword it;
   - the excuse wasn't anticipated: add it to the skill with a counter;
   - the rule itself is wrong for this case: take it to the user, it may need a scoped exception.

## Feed back into the skill

- An excuses table: each recorded excuse, and the one-line counter to it.
- Red flags: phrases that signal the agent is about to break the rule ("just this once", "to save time").
- Re-run the scenarios until the with-skill arm holds; then add one fresh scenario the skill never saw, to check it generalizes.
