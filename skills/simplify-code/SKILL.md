---
name: simplify-code
description: >-
  Simplify and refine recently changed code for clarity, reuse, and efficiency
  while preserving behavior. Use before opening a PR, after implementing a
  feature in a mature framework, or when asked to clean up a branch diff.
license: MIT
metadata:
  author: Kieran Klaassen (Compound Engineering)
  upstream: https://github.com/EveryInc/compound-engineering-plugin/tree/main/plugins/compound-engineering/skills/ce-simplify-code
  adapted_for: Saddss/cursor-skills (Cursor Task tool; renamed from ce-simplify-code)
---

> **Vendored from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) under MIT.** Renamed `simplify-code`; Cursor Task for parallel review.

# Simplify Code

Simplify changed code for clarity and consistency **without changing behavior**. Prefer readable, explicit code over overly compact solutions.

## Step 1: Identify Scope

1. User-named scope wins — do not widen
2. In git: default to `git diff origin/main...` (or upstream base); else `git diff HEAD`
3. No diff: most recently modified files in conversation
4. Empty scope: ask user — do not guess

## Step 2: Parallel Review (3 lenses)

Run three reviews on the same diff. In Cursor, use **one message with three `Task` calls** (or sequential if Task unavailable):

### Lens 1 — Reuse

- Existing utilities that replace new code?
- Duplicate functions vs similar patterns elsewhere?
- Inline logic that should call existing helpers?

### Lens 2 — Quality

Flag: redundant state, parameter sprawl, copy-paste variants, leaky abstractions, stringly-typed constants, deep nesting (3+ levels), comments that narrate WHAT not WHY, dead code/unused imports.

**Balance:** fewer lines ≠ goal; faster comprehension = goal. Do not inline named helpers or remove abstractions used for testing without checking `git blame`.

### Lens 3 — Efficiency

Flag: redundant work, missed parallelism, hot-path bloat, no-op updates in loops, TOCTOU existence checks, unbounded structures, overly broad reads.

## Step 3: Fix

Aggregate findings; fix directly. Skip false positives silently. Each fix must preserve behavior — if unsure, skip.

## Step 4: Verify

- Run project **lint + typecheck** (if configured)
- Run **tests scoped to changed paths**; broaden if shared utilities changed
- Report failures with command output — do not weaken assertions to pass

## Step 5: Summarize

What was already good vs improved; which checks ran and results. If no changes needed, say so.

## Integration

Use after `executing-plans` / feature work, before PR, with **`verification-before-completion`**.
