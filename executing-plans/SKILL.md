---
name: executing-plans
description: >-
  Execute a written implementation plan task-by-task with verification
  checkpoints. Use after writing-plans when implementing multi-step features
  in mature frameworks; stop when blocked instead of guessing.
license: MIT
metadata:
  author: Jesse Vincent (Superpowers)
  upstream: https://github.com/obra/superpowers/tree/main/skills/executing-plans
  adapted_for: Saddss/cursor-skills (Cursor Task tool; verification-before-completion handoff)
---

> **Vendored from [obra/superpowers](https://github.com/obra/superpowers) under MIT.** Finishing handoff mapped to verification-before-completion.

# Executing Plans

Load plan, review critically, execute tasks, verify, report.

**Announce:** "Using the executing-plans skill to implement this plan."

## Step 1: Load and Review

1. Read the plan file
2. Review critically — gaps, wrong paths, missing tests?
3. If concerns: raise with user **before** starting
4. If OK: track tasks (TodoWrite or checkbox list in plan)

## Step 2: Execute Tasks

For each task:

1. Mark in progress
2. Follow each step exactly (use `tdd` when plan says write test first)
3. Run verifications specified in the plan
4. Mark complete only after verification passes

**Never commit on `main`/`master` without explicit user consent** — use a feature branch.

## Step 3: Complete

After all tasks:

1. Invoke **`verification-before-completion`** — run full test/lint/build evidence
2. Optionally invoke **`simplify-code`** on branch diff before PR
3. Summarize: what changed, commands run, evidence

## When to STOP

Stop immediately when:

- Blocker (missing dep, test fails, unclear instruction)
- Plan has critical gaps
- Verification fails repeatedly

**Ask for clarification — do not guess.**

## When to Revisit Plan

Return to Step 1 when:

- User updates the plan
- Fundamental approach must change

## Integration

| Required | Skill |
|----------|-------|
| Plan input | `writing-plans` |
| Test steps | `tdd` |
| Done gate | `verification-before-completion` |
| PR prep | `simplify-code` |
