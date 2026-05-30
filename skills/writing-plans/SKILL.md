---
name: writing-plans
description: >-
  Write bite-sized implementation plans from an approved spec. Use after
  brainstorming or grill-with-docs, before touching code on multi-step features
  in mature codebases (vLLM, SGLang, inference harness, serving stack patches).
license: MIT
metadata:
  author: Jesse Vincent (Superpowers)
  upstream: https://github.com/obra/superpowers/tree/main/skills/writing-plans
  adapted_for: Saddss/cursor-skills (Cursor skill names; docs/plans layout)
---

> **Vendored from [obra/superpowers](https://github.com/obra/superpowers) under MIT.** Sub-skill references mapped to Cursor skills.

# Writing Plans

Write implementation plans assuming the engineer has **zero codebase context** but is skilled. Bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

**Announce:** "Using the writing-plans skill to create the implementation plan."

**Save to:** `docs/plans/YYYY-MM-DD-<feature-name>.md` (user preference overrides)

## Scope Check

If the spec covers multiple independent subsystems, split into **separate plans** — one per subsystem, each shippable on its own.

## File Structure (lock before tasks)

- Map every file to create/modify and its responsibility
- **In existing codebases, follow established patterns** — do not unilaterally restructure
- Prefer focused files; split only when the plan requires it
- Files that change together should live together

## Task Granularity

Each step = one action (~2–5 minutes):

- Write failing test → run (must fail) → minimal implementation → run (must pass) → commit

## Plan Header (required)

```markdown
# [Feature Name] Implementation Plan

> **For agents:** Use `executing-plans` (inline) or Task subagents per task. Steps use `- [ ]` checkboxes.

**Goal:** [one sentence]

**Architecture:** [2–3 sentences — extension point, files, pattern followed]

**Reference implementations:** [similar in-repo features copied as pattern]

---
```

## Task Template

Each task MUST include:

- **Files:** exact paths (create / modify with line ranges when known)
- **Steps:** with complete code snippets — no "add error handling" without code
- **Commands:** exact run command + expected output (FAIL/PASS)

## No Placeholders (plan failures)

Never write: TBD, TODO, "implement later", "similar to Task N", "write tests for the above" without code.

## Self-Review

1. **Spec coverage** — every requirement maps to a task
2. **Placeholder scan** — fix all vague steps
3. **Type/name consistency** — symbols match across tasks

## Execution Handoff

After saving the plan:

**Plan saved to `docs/plans/<file>.md`. Execution options:**

1. **Inline** — `executing-plans` in this session (checkpoints between tasks)
2. **Subagent per task** — Cursor `Task` tool, review between tasks

Ask which approach. Then use `executing-plans` or Task-driven execution with `tdd` per step.

## Integration

| Input | Output |
|-------|--------|
| `brainstorming` / `grill-with-docs` spec | This plan |
| This plan | `executing-plans` + `tdd` |
| Before PR | `simplify-code`, `verification-before-completion` |
