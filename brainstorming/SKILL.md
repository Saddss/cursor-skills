---
name: brainstorming
description: >-
  Use before any creative work — adding features, modifying behavior, or
  extending a mature framework (vLLM, SGLang, TRT-LLM, benchmark harness).
  Explores intent, constraints, and design; requires user approval before code.
license: MIT
metadata:
  author: Jesse Vincent (Superpowers)
  upstream: https://github.com/obra/superpowers/tree/main/skills/brainstorming
  adapted_for: Saddss/cursor-skills (Cursor paths; docs/plans layout; inference triggers)
---

> **Vendored from [obra/superpowers](https://github.com/obra/superpowers) under MIT.** Spec/plan paths and framework triggers adapted for Cursor.

# Brainstorming Ideas Into Designs

Turn ideas into designs and specs through dialogue **before** implementation.

**HARD-GATE:** Do NOT write code, scaffold, or invoke implementation skills until design is presented and the user approves. No exceptions — "simple" changes are where assumptions waste the most time.

## Checklist (in order)

1. **Explore project context** — files, docs, recent commits, similar features
2. **Ask clarifying questions** — one at a time; purpose, constraints, success criteria
3. **Propose 2–3 approaches** — trade-offs + recommendation
4. **Present design** — section by section; user approval after each
5. **Write design doc** — `docs/specs/YYYY-MM-DD-<topic>-design.md` (user path overrides)
6. **Spec self-review** — placeholders, contradictions, ambiguity, scope
7. **User reviews spec** — wait for approval before planning
8. **Transition** — invoke `writing-plans` (only next skill)

## Working in Existing / Mature Codebases

- Explore current structure **before** proposing changes; **follow established patterns**
- Find how similar features were added (extension points, tests, config)
- Include **targeted** improvements only where they serve this feature — no unrelated refactors
- If scope spans multiple subsystems, **decompose first**; brainstorm one sub-project at a time

## Design Principles

- **YAGNI** — remove unnecessary features from every design
- **One question at a time** — do not overwhelm
- **2–3 alternatives** before settling
- **Incremental validation** — approval before moving on
- **Clear boundaries** — each unit has one purpose and a testable interface

## Spec Self-Review

1. Placeholder scan — no TBD/TODO/vague requirements
2. Internal consistency — architecture matches feature descriptions
3. Scope check — single plan or needs decomposition?
4. Ambiguity check — resolve dual interpretations explicitly

## After Approval

Ask:

> Spec written to `<path>`. Review it and confirm before we write the implementation plan.

Then invoke **`writing-plans` only**. Do not skip to coding.

## Optional: Visual Companion

For UI/layout questions, browser mockups may help. Offer once, in its own message; user can decline. See [visual-companion.md](visual-companion.md). Text-only is fine for backend / kernel / benchmark work.

## Integration

| Before | After |
|--------|-------|
| `search-first`, `parallel-exploring`, `grill-with-docs` | `writing-plans` → `executing-plans` + `tdd` |
