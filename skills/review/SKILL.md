---
name: review
description: >-
  Two-axis branch review — Standards (CONTRIBUTING.md, CONTEXT, ADRs) and Spec
  (issue/PRD/plan). Runs parallel sub-agents on git diff. Use before PR, when
  reviewing a branch, or after implementing routing/benchmark/harness changes.
license: MIT
metadata:
  author: Matt Pocock
  upstream: https://github.com/mattpocock/skills/tree/main/skills/in-progress/review
  adapted_for: Saddss/cursor-skills (Agent → Cursor Task; inference triggers)
---

> **Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) under MIT.** Upstream status: in-progress.

# Review

Review diff between `HEAD` and a user-supplied fixed point on **two independent axes**:

- **Standards** — matches documented coding standards?
- **Spec** — matches originating issue / PRD / plan?

Run both as **parallel Cursor `Task` subagents**, then aggregate without merging findings.

## Process

### 1. Pin the fixed point

Commit SHA, branch, tag, `main`, `HEAD~5`, etc. If unspecified, ask: "Review against what?"

```bash
git diff <fixed-point>...HEAD
git log <fixed-point>..HEAD --oneline
```

### 2. Identify spec source

1. Issue refs in commits (`#123`, `Closes #45`) — fetch via `docs/agents/issue-tracker.md` or `gh issue view`
2. User-provided path (e.g. `docs/plans/*.md`, `.cursor/plans/*.md`)
3. `docs/specs/`, `docs/plans/`, `.scratch/` matching branch/feature name
4. If none: ask user; Spec axis reports "no spec available"

### 3. Identify standards sources

Collect paths — e.g. `CONTRIBUTING.md`, `AGENTS.md`, `CONTEXT.md`, `docs/adr/`, linter configs. Note machine-enforced rules; don't re-check what CI already enforces.

### 4. Parallel sub-agents

One message, two `Task` calls (`subagent_type="generalPurpose"` or `explore`):

**Standards prompt:** diff command, commit list, standards file list. "Read standards, read diff. Report violations with file+rule citation. Hard vs judgement. Skip tooling-enforced. Under 400 words."

**Spec prompt:** diff command, commit list, spec contents/path. "Read spec, read diff. Report: (a) missing/partial requirements, (b) scope creep, (c) likely wrong implementations. Quote spec lines. Under 400 words."

Skip Spec sub-agent if no spec.

### 5. Aggregate

Present under `## Standards` and `## Spec` — do not rerank or merge axes.

End with one-line summary: counts per axis, worst single issue (if any).

## Why two axes

- Standards pass, Spec fail → correct style, wrong feature
- Spec pass, Standards fail → right feature, wrong conventions

## Integration

| When | Pair with |
|------|-----------|
| After `executing-plans` | Before PR |
| With `simplify-code` | review = correctness; simplify = clarity |
| After `to-issues` | Spec axis uses issue acceptance criteria |
