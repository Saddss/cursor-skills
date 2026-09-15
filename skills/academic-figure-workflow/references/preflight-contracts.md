# Figure preflight contracts

Use these ledgers before coordinates or styling. They convert recurring visual mistakes into information that automatic QA can check.

## 1. Argument contract

| Field | Required content |
|---|---|
| Figure claim | One sentence the figure proves or explains |
| Manuscript location | Section and paragraph where the figure is introduced |
| Evidence | Text, design decision, experiment, or source supporting each element |
| Reading order | Primary path and any secondary path |
| Final size | Physical width and height in the manuscript |
| Explicit omissions | Details delegated to another figure, table, equation, or正文 |

If two independent claims compete for the title, split the figure.

## 2. Node and edge ledger

Record every structural relation before drawing it.

| Edge ID | Source | Relation | Target | Source side | Target side | Role |
|---|---|---|---|---|---|---|
| e1 | request | enters | router | right | left | data |

Rules:

- Every visible node maps to a real operation, state, resource, actor, or decision.
- A junction exists only for a real aggregation, comparison, or synchronization operation.
- Independent flows entering one container use separate named ports; do not invent a merge node.
- A nested container uses two relations: external source → intact container, then internal source → internal target.
- Every structural SVG path binds to named anchors and sides. An edge that cannot be read as “source — relation — target” is rejected before layout.

## 3. Typography ledger

Assign a semantic role before fitting text.

| Group | Members | Family | Size | Weight |
|---|---|---|---:|---:|
| module-title | all peer module titles | Noto Sans CJK SC | 22 px | 400 |

Peer module titles, paired candidates, parallel conclusions, peer flow nodes, and peer legend labels each need a `data-typography-group`. Group size spread is 0 px and family/weight sets each contain one value. If one label does not fit, change the layout or line break; never shrink only that label.

## 4. Visual vocabulary and legend ledger

List every colour, fill, texture, arrow line style, and marker that carries meaning.

| Key | Encoding | Meaning | Reused? | Explanation |
|---|---|---|---|---|
| hot-write | blue solid arrow | reusable write | yes | legend |
| time-step | grey solid arrow | local transition | no | adjacent direct label |

For every reused meaning-bearing arrow style, put `data-legend-key="..."` on structural instances and the same key in `data-legend-for="..."` on exactly one legend sample. The two key sets must match. A one-off process arrow may omit a legend only when an adjacent label states its complete meaning.

## 5. Repeated-structure ledger

Identify structures readers compare: hot/cold pools, candidate a/b, baseline/proposed paths, or peer workers. Record the invariant dimensions, baselines, internal grids, connector styles, and deliberate semantic differences. Comparison structures must be generated as one component, not positioned independently.

## 6. DOCX mutation contract

Choose the smallest permitted package change before touching the Word file.

| Revision type | Allowed changed members | Required check |
|---|---|---|
| Same-size/aspect figure replacement | One resolved `word/media/...` member | Entire package diff allowlist |
| Drawing extent or alt-text change | Target media plus `word/document.xml` | Exact target drawing diff, protected-page render, package allowlist |
| Caption/cross-reference edit | Explicit XML members required by that edit | Field/caption regression plus protected-page render |

For a same-size/aspect replacement, do not parse and serialize `document.xml`, do not update alt text “while here”, and do not accept a prefix-only cover comparison. Use `scripts/docx_change_guard.py replace`; it refuses aspect mismatch and proves that every other ZIP member remains byte-identical.

## 7. Feedback-to-gate loop

When a user finds a defect:

1. Reproduce it on the rendered artifact.
2. Classify the failure as argument, typography, geometry, legend, export, or manuscript mutation.
3. Audit every current figure for the same class; do not patch only the screenshot.
4. Add or tighten semantic metadata.
5. Add a deterministic check or regression fixture.
6. Demonstrate the old artifact fails and the corrected artifact passes.
7. Update the maintained failure-mode reference and template if the rule affects new figures.

A correction is not complete if it changes only coordinates in one figure while leaving the same failure possible in the next figure.
