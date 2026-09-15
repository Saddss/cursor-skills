---
name: search-first
description: >-
  Research-before-coding workflow. Search the repo, framework APIs, libraries,
  and existing patterns before writing custom code. Use when adding a feature
  to a mature framework (vLLM, SGLang, TRT-LLM, benchmark harness), before
  creating a utility/helper, or when the user asks to "add X functionality".
license: MIT
metadata:
  author: Affaan Mustafa (Everything Claude Code)
  upstream: https://github.com/affaan-m/everything-claude-code/tree/main/skills/search-first
  adapted_for: Saddss/cursor-skills (Cursor paths + inference-framework triggers)
---

> **Vendored from [everything-claude-code](https://github.com/affaan-m/everything-claude-code) under MIT.** Paths adapted for Cursor; inference-framework triggers added.

# Search First — Research Before You Code

Systematizes "search for existing solutions before implementing."

## Trigger

Use when:
- Adding a feature to a **mature framework** (find similar implementations first)
- Starting functionality that likely already exists in-repo or upstream
- Before creating a new utility, helper, registry entry, or abstraction
- User says "add X" and you are about to write code

## Workflow

```
0. TOOL PREFLIGHT     — which search channels are available; report gaps honestly
1. NEED ANALYSIS      — what is needed; language/framework constraints
2. PARALLEL SEARCH    — repo rg + framework docs + package registry + GitHub
3. EVALUATE           — score candidates (fit, maintenance, license, deps)
4. DECIDE             — Adopt / Extend / Compose / Build
5. IMPLEMENT          — minimal custom code informed by research
```

## Decision Matrix

| Signal | Action |
|--------|--------|
| Exact match in repo or upstream, well-maintained | **Adopt** — use directly |
| Partial match or existing hook/plugin point | **Extend** — thin wrapper at seam |
| Multiple weak matches | **Compose** — combine 2–3 small pieces |
| Nothing suitable | **Build** — custom, but informed by research |

## Step 0: Tool Availability Preflight

| Channel | Check | If missing |
|---------|-------|------------|
| Repository search | `rg` through modules, tests, configs | State only visible files were inspected |
| Framework patterns | Similar features, registries, plugins, custom op hooks | Read adjacent files + tests |
| Package registry | `pip`, `npm`, project lockfile | Web/docs search only |
| GitHub CLI | `gh auth status` | Public web or local git history |
| MCP / docs tools | Available MCP tool list | Official docs / web search |
| Skills | `~/.cursor/skills/` | Say no local skill catalog was checked |

## Quick Mode (default for small changes)

Before writing code, run through:

0. **Does this already exist in the repo?** → `rg` modules/tests for similar names and call sites
1. **How did the framework add similar features?** → find 1–2 reference implementations
2. **Is there an upstream API / plugin / registry?** → extend instead of invent
3. **Is there a maintained library?** → npm/PyPI/GitHub
4. **Is there a Cursor skill?** → `~/.cursor/skills/`

## Full Mode (non-trivial features)

Launch parallel explore subagents via Cursor `Task` tool:

```
Task(subagent_type="explore", prompt="
  Find how [FRAMEWORK] implements [FEATURE] or closest equivalent.
  Return: file paths, extension points, test patterns, recommendation Adopt/Extend/Build.
")
```

Combine with `parallel-exploring` when the codebase is large.

## Mature Framework Checklist

When touching vLLM / SGLang / TRT-LLM / serving stacks:

- [ ] Found at least one **in-repo reference implementation** of similar scope
- [ ] Identified the **public seam** (registry, plugin, model class, runner hook)
- [ ] Checked tests for how the feature is exercised
- [ ] Confirmed change follows **existing file layout and naming**
- [ ] Documented why **Extend** beats **Build** (or why Build is unavoidable)

## Anti-Patterns

- **Jumping to code** without searching the repo
- **Reinventing framework mechanisms** (custom registry when one exists)
- **Silent skipping** — claiming "nothing found" when search was incomplete
- **Over-customizing** a library until it loses its benefits
- **Dependency bloat** — massive package for one small helper

## Integration

| Phase | Pair with |
|-------|-----------|
| Before design | `parallel-exploring`, `brainstorming` |
| After plan | `writing-plans`, `tdd` |
| Before PR | `simplify-code`, `verification-before-completion` |
