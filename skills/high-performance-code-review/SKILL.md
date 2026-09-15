---
name: high-performance-code-review
description: Review pull requests and code changes for high-performance Python, PyTorch, CUDA, and distributed systems using a correctness-first P0-P4 rubric. Use when the user asks for a strict production-grade review, especially for inference, GPU, concurrency, or performance-sensitive code.
metadata:
  source: "https://github.com/zhaochenyang20/sglang-diffusion-routing/issues/32"
---

# High-Performance Code Review

Review the actual diff in its repository context. Read relevant call sites, tests, configuration, and local contributor instructions before judging an isolated line. Repository-specific rules override this default rubric.

## Review sequence

Address these dimensions in order:

1. **Summary and technical background** — Explain what changes and the underlying mechanisms that matter, such as tensor shapes, memory layout, synchronization, CUDA behavior, distributed communication, attention, KV cache, or tensor parallelism. Assess whether the change is necessary, duplicates existing behavior, or adds unjustified complexity.
2. **Code quality and correctness** — Review changed lines strictly with the P0-P4 rubric below. Trace behavior across relevant call sites rather than relying on the diff alone.
3. **Goal completeness** — Compare implementation with the stated goal. Identify missing edge cases, production assumptions, and over- or under-engineering.
4. **Generated-code risk** — Flag code that appears insufficiently understood or verified, but only when concrete evidence supports the concern. Treat authorship as uncertain; review observable problems rather than claiming AI use from style alone.

## P0-P4 rubric

Use the labels only for actionable findings:

- `[P0-BLOCKER]` correctness: latent bugs, races, shape or dtype errors, leaks, invalid invariants, unsafe exception handling, or missing validation at public/system boundaries.
- `[P1-PERF]` performance: host-device synchronization, `.item()`/`.cpu()`/`.tolist()` in hot inference paths, avoidable Python loops, CPU fallbacks, allocation churn, wide lock scope, or GPU/I/O work while holding a lock.
- `[P2-MAINTAIN]` maintainability: material duplication, oversized or mixed-responsibility units, unclear naming, magic values, dependency tangles, circular imports, or public API inconsistency.
- `[P3-STYLE]` design clarity: avoidable mutation, dynamic attributes, incomplete branching, confusing control flow, missing public type hints, or stale debug code/comments.
- `[P4-PROCESS]` verification: missing contract tests, reproducible verification commands, important CI coverage, deterministic seeds, or failure-path tests.

Do not mechanically report preference-level nits. A severity reflects impact, not which rubric heading mentions the issue.

## Review standards

- Fail fast for programmer invariants; use clear input errors at public APIs and system boundaries. Prefer guard clauses to deep nesting.
- Keep exception scopes narrow. Do not swallow failures or add speculative fallback behavior.
- State thread-safety guarantees for shared components. Minimize lock scope and prefer message passing over shared mutable state when it materially simplifies concurrency.
- Bound long-lived caches and buffers. Use context managers for files, sockets, streams, and other owned resources.
- Keep GPU hot paths device-resident and vectorized. Require measurements before adding manual cache clearing or memory-management workarounds.
- Prefer cohesive helpers and precise names. As review heuristics, investigate duplicated blocks over roughly five lines, functions over roughly fifty lines, and files over roughly two thousand lines; do not treat thresholds as automatic defects.
- Keep imports ordered standard-library, third-party, then local; avoid wildcard imports and isolate heavy optional imports when appropriate.
- Prefer explicit, typed public interfaces and pure functions. In-place operations are acceptable when a measured hot path requires them and the reason is documented.
- Tests should validate observable contracts, pin randomness when relevant, and make verification commands copyable.

## Finding quality

Before reporting a finding, verify that it is introduced or exposed by the change, reproducible from the code, and not already prevented elsewhere. For every finding:

1. cite the tightest changed line range;
2. explain the concrete failure or cost and when it occurs;
3. assign one P0-P4 label;
4. propose a practical fix or test.

Potential generated-code warning signs include generic abstractions that ignore repository constraints, broad defensive branches, verbose obvious comments paired with missing domain reasoning, broad exception swallowing, inconsistent naming, and textbook implementations that miss system invariants. Report the underlying defect with evidence; do not use “AI-generated” as a standalone finding.

## Output contract

Lead with findings ordered by severity and then file/line. Keep summary and background concise after the findings, followed by goal-completeness and verification gaps. If there are no actionable findings, say so explicitly and mention residual risks or tests not run; never substitute a bare “LGTM.”
