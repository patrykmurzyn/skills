# Friction findings: (project or "global"), (date)

**Source:** mining (last N days) | probe (task) · **Sessions examined:** (Claude n, Codex n, subagents n) · **Excluded:** (ledger, temp folders)

Reply with the numbers to take to `skill-scoping`. Nothing changes until you pick.

## F1. (What happened, in one line: "Agents pass unquoted globs to grep in zsh and the command fails")

- **Evidence:**
  - (agent) `(session, 8 chars)` (date), (signal type): "(quote, at most 200 characters, redacted)"
  - (a second session)
- **Frequency:** (sessions affected) of (sessions examined); (occurrences) times
- **Cost:** low | medium | high: (wasted calls or turns, interrupts, re-explanations)
- **Basis:** trace | self-report | both
- **Mechanism hint:** script or hook | AGENTS.md line | skill | docs | tool error message | environment fix: (one line why)

## Left out

- (signal): (why: one session and low cost, caused by the mining itself, or not the agent's friction)

## Record fields

`findings.jsonl` holds one object per finding:

```json
{"id": "F1", "title": "", "source": "mining", "scope": "project:~/code/app",
 "evidence": [{"agent": "claude", "session": "1a2b3c4d", "date": "2026-10-27",
               "signal": "error_in_output", "quote": ""}],
 "frequency": {"sessions": 0, "of": 0, "occurrences": 0},
 "cost": "medium", "cost_note": "", "basis": "trace",
 "mechanism_hint": "AGENTS.md line", "status": "new"}
```

`status` is `new` until the user answers, then `picked` or `dropped`.
