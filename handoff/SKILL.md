---
name: handoff
description: >-
  Compact the current conversation into a handoff document for another agent
  to pick up. Use when ending a long session, switching agents, or handing
  off benchmark runs, profiling investigations, or multi-step infra work.
license: MIT
metadata:
  author: Matt Pocock
  upstream: https://github.com/mattpocock/skills/tree/main/skills/productivity/handoff
  adapted_for: Saddss/cursor-skills (Claude argument-hint removed; otherwise verbatim)
---

> **Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) under MIT.** See `LICENSE-MIT-Matt-Pocock.txt`.

# Handoff

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS — not the current workspace.

Include a **Suggested skills** section listing skills the next agent should invoke (e.g. `diagnose`, `perf-analysis`, `perf-nsight-systems`).

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user describes what the next session will focus on, tailor the doc accordingly.
