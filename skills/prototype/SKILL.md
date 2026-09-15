---
name: prototype
description: >-
  Build throwaway prototypes to validate a design before production code.
  Terminal state-machine for routing/cache/overload logic, or UI variants on one
  route. Use when prototyping, sanity-checking a state model, exploring routing
  policies, or saying "prototype this" / "let me play with it".
license: MIT
metadata:
  author: Matt Pocock
  upstream: https://github.com/mattpocock/skills/tree/main/skills/engineering/prototype
  adapted_for: Saddss/cursor-skills (inference/routing triggers added)
---

> **Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) under MIT.**

# Prototype

**Throwaway code that answers one question.** The question decides the shape.

## Pick a branch

- **Logic / state / routing policy?** → [LOGIC.md](LOGIC.md) — interactive terminal TUI over a pure reducer/state machine
- **Layout / UI?** → [UI.md](UI.md) — multiple variants on one route via `?variant=`

If ambiguous: backend/routing module → LOGIC; page/component → UI. State the assumption at the top.

## Rules (both branches)

1. **Clearly marked throwaway** — name/path says prototype; live near the real module
2. **One command to run** — `python …`, `pnpm …`, Makefile target
3. **No persistence by default** — in-memory unless persistence is the question
4. **No polish** — no tests, minimal error handling, no abstractions
5. **Surface state** — print/render full state after every action
6. **Delete or absorb** — capture answer in ADR/issue/NOTES.md, then delete shell

## When done

The **answer** is what you keep. For routing/cache work, fold the validated reducer/policy into production code; delete the TUI.

## Integration

| Before | After |
|--------|-------|
| `brainstorming`, `grill-with-docs` | Validated design |
| Prototype verdict | `writing-plans` or `to-issues` (inline decision snippets in issues OK) |
| Production impl | `executing-plans` + `tdd` |
