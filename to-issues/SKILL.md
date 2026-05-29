---
name: to-issues
description: >-
  Break a plan, spec, or PRD into independently-grabbable GitHub issues using
  tracer-bullet vertical slices. Use when converting a plan into issues, splitting
  a benchmark study / routing feature / multi-PR infra work into tickets, or
  preparing AFK-agent-ready tasks.
license: MIT
metadata:
  author: Matt Pocock
  upstream: https://github.com/mattpocock/skills/tree/main/skills/engineering/to-issues
  adapted_for: Saddss/cursor-skills (inference triggers; setup skill name normalized)
---

> **Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) under MIT.**

# To Issues

Break a plan into independently-grabbable issues using **vertical slices** (tracer bullets).

Issue tracker and triage labels live in `docs/agents/` — run **`setup-matt-pocock-skills`** in the target repo first if missing.

## Process

### 1. Gather context

Work from conversation context. If the user passes an issue number, URL, or path, fetch it (`gh issue view`, or read local markdown per `docs/agents/issue-tracker.md`).

### 2. Explore the codebase (optional)

If not already explored, scan the repo. Issue titles and bodies use the project **domain glossary** and respect **ADRs** in the touched area.

### 3. Draft vertical slices

Each issue is a thin slice through **all integration layers** end-to-end — not a horizontal layer (e.g. "only tests" or "only router").

- **AFK** — agent can implement and merge without human decisions (prefer this)
- **HITL** — needs human review, architecture call, or external dependency

Rules:
- Each slice delivers a narrow but **complete** verifiable path
- Prefer many thin slices over few thick ones
- For infra: a slice might be "one routing policy + fake server test + metrics hook" — still end-to-end within that policy

### 4. Quiz the user

Present a numbered list. Per slice:

- **Title**
- **Type**: HITL / AFK
- **Blocked by**: other slices (if any)
- **User stories covered** (if source material has them)

Ask: granularity OK? dependencies correct? merge/split? AFK/HITL labels right?

Iterate until approved.

### 5. Publish issues

Publish in dependency order (blockers first). Default label: **`ready-for-agent`** unless told otherwise.

```markdown
## Parent

Reference to parent issue (omit if none).

## What to build

End-to-end behavior of this slice — not layer-by-layer file lists.
Avoid stale file paths. Exception: prototype snippets that encode a decision (state machine, reducer) — inline trimmed excerpt + note source.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by

- #NNN or "None — can start immediately"
```

Do **not** close or modify parent issues.

## Integration

| Before | After |
|--------|-------|
| `writing-plans`, `grill-with-docs`, approved spec | Issues on tracker |
| Issues published | `executing-plans` or agent picks AFK issue |
| PR ready | `review` |
