---
name: verification-before-completion
description: >-
  Before claiming work is complete, fixed, or passing — run verification
  commands and cite evidence. Use before commit/PR, after implementing features
  or benchmark fixes, when saying tests pass or bug is fixed.
license: MIT
metadata:
  author: Jesse Vincent (Superpowers)
  upstream: https://github.com/obra/superpowers/tree/main/skills/verification-before-completion
  adapted_for: Saddss/cursor-skills (inference/benchmark triggers in description)
---

> **Vendored from [obra/superpowers](https://github.com/obra/superpowers) under MIT.** Inference triggers added to description.

# Verification Before Completion

**Core principle:** Evidence before claims, always.

## Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you have not run the verification command **in this message**, you cannot claim it passes.

## Gate Function

```
BEFORE claiming success or expressing satisfaction:

1. IDENTIFY — what command proves the claim?
2. RUN     — full command, fresh, complete
3. READ    — full output, exit code, failure count
4. VERIFY  — output supports the claim?
5. ONLY THEN — state the claim WITH evidence
```

Skip any step = not verified.

## Common Failures

| Claim | Requires | Not sufficient |
|-------|----------|----------------|
| Tests pass | Command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter: 0 errors | Partial file check |
| Build succeeds | Build exit 0 | Linter only |
| Bug fixed | Repro test passes | Code changed, assumed fixed |
| Benchmark improved | Rerun with numbers | Single old log |
| Agent done | VCS diff + verify | Agent said "success" |

## Red Flags — STOP

- "should", "probably", "seems to"
- "Done!", "Perfect!", "Great!" before verification
- Commit/PR without running checks
- Trusting subagent reports without independent verify

## Patterns

```
✅ [pytest …] → 42 passed → "All tests pass"
❌ "Should pass now"

✅ Revert fix → test FAILS → restore → PASS  (regression test)
❌ "Added a regression test" (no red-green proof)
```

## When to Apply

Always before: completion claims, satisfaction, commit, PR, next task, delegating to agents.

## Integration

Final gate after `executing-plans`, `tdd`, `simplify-code`, `diagnose`, and benchmark runs.
