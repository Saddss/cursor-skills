---
name: setup-matt-pocock-skills
description: >-
  Scaffold docs/agents/ in a target repo — issue tracker (GitHub/GitLab/local),
  triage labels, domain doc layout. Run once per repo before to-issues, review,
  or other skills that read docs/agents/issue-tracker.md.
license: MIT
metadata:
  author: Matt Pocock
  upstream: https://github.com/mattpocock/skills/tree/main/skills/engineering/setup-matt-pocock-skills
  adapted_for: Saddss/cursor-skills (Cursor AGENTS.md; reference templates bundled)
---

> **Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) under MIT.** Seed templates in this directory.

# Setup Agent Skills (per-repo)

Scaffold configuration that **`to-issues`**, **`review`**, and related skills consume:

- **Issue tracker** — GitHub / GitLab / local markdown / other
- **Triage labels** — map canonical roles to your label strings
- **Domain docs** — `CONTEXT.md` / `CONTEXT-MAP.md` / ADR layout

Prompt-driven: explore → confirm with user → write files.

## Process

### 1. Explore

- `git remote -v` — GitHub? GitLab?
- `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`
- `CONTEXT.md`, `CONTEXT-MAP.md`, `docs/adr/`
- `docs/agents/` — already set up?
- `.scratch/` — local issue convention?

### 2. Three decisions (one at a time)

**A — Issue tracker:** GitHub (`gh`), GitLab (`glab`), local markdown (`.scratch/`), or describe other.

**B — Triage labels:** Map canonical roles to your strings:

| Role | Default string |
|------|----------------|
| needs-triage | `needs-triage` |
| needs-info | `needs-info` |
| ready-for-agent | `ready-for-agent` |
| ready-for-human | `ready-for-human` |
| wontfix | `wontfix` |

**C — Domain docs:** single-context (`CONTEXT.md` + `docs/adr/`) or multi-context (`CONTEXT-MAP.md`).

### 3. Confirm draft

Show user before writing:

- `## Agent skills` block for `AGENTS.md` or `CLAUDE.md`
- `docs/agents/issue-tracker.md`
- `docs/agents/triage-labels.md`
- `docs/agents/domain.md`

### 4. Write

Edit existing `AGENTS.md` or `CLAUDE.md` (prefer whichever exists; don't duplicate). Update existing `## Agent skills` block in-place if present.

```markdown
## Agent skills

### Issue tracker

[summary]. See `docs/agents/issue-tracker.md`.

### Triage labels

[summary]. See `docs/agents/triage-labels.md`.

### Domain docs

[single/multi-context]. See `docs/agents/domain.md`.
```

Seed from bundled templates:

- [issue-tracker-github.md](issue-tracker-github.md)
- [issue-tracker-gitlab.md](issue-tracker-gitlab.md)
- [issue-tracker-local.md](issue-tracker-local.md)
- [triage-labels.md](triage-labels.md)
- [domain.md](domain.md)

### 5. Done

Tell user which skills now read these files. Edit `docs/agents/*.md` directly later; re-run only to switch trackers.

## When to run

Once per repo (e.g. `production-stack`, `llm-inference-benchmarking`) before first `to-issues` or `review`.
