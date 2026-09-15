---
name: academic-figure-workflow
description: Create, revise, and validate publication-style academic figures for papers, theses, and technical reports, especially editable SVG mechanism/architecture diagrams and their DOCX/WPS insertion. Use for 论文作图, 学术架构图, 机理图, SVG 绘图, 图片重排, 文字/箭头对齐, 图注, 600 dpi 预览, 图片插入 Word/WPS, or when repeated visual defects must be eliminated with deterministic QA. Do not use for photorealistic illustration or decorative presentation slides.
---

# Academic Figure Workflow

Create figures as evidence-backed, editable technical artifacts. A figure is ready only when the source, rendered preview, geometry QA, caption, and manuscript insertion all agree.

## Route by figure type

- Mechanism, architecture, workflow, or conceptual diagram: use hand-authored SVG with explicit coordinates and semantic metadata.
- Quantitative plot: use reproducible plotting code and source data; never draw values by eye.
- Photorealistic or illustrative bitmap: use an image-generation workflow only after the user asks for that medium. Do not use image generation for text-heavy academic diagrams.
- Existing DOCX/WPS figure replacement: preserve the document template and replace only the intended drawing/media relationship.

Before creating or substantially rebuilding a figure, read [references/preflight-contracts.md](references/preflight-contracts.md). For SVG work, read [references/visual-spec.md](references/visual-spec.md). For any revision or final delivery, also read [references/failure-modes.md](references/failure-modes.md). When inserting into Word/WPS, read [references/docx-wps-insertion.md](references/docx-wps-insertion.md).

## Non-negotiable gates

1. **Argument gate**: define one central claim, target section, evidence source, and what the figure intentionally omits. Do not invent modules, data, mechanisms, or results.
2. **Final-size gate**: choose the physical insertion size before layout. Set SVG `width`/`height` in `mm` and a proportional `viewBox`; do not design at an arbitrary canvas then shrink it in Word.
3. **Editability gate**: keep text as `<text>`, shapes as vectors, and semantic grouping readable. Raster screenshots are previews, not source.
4. **Geometry gate**: no text overlap, boundary collision, clipping, or line-through-text. Every structural arrow has an explicit source, target, side, centerline, and terminal gap.
5. **Typography gate**: use real installed fonts and real weights only. No shadows, outlines, fake bold, malformed glyphs, or spaces used as layout controls.
6. **Vocabulary gate**: every reused colour, texture, marker, and arrow style has one declared meaning. Every meaning-bearing arrow style is covered by exactly one legend item or by a complete adjacent direct label.
7. **Rendered gate**: measure after `document.fonts.ready`, export a 600 dpi PNG, inspect the actual pixels, and repeat until automatic issues are zero.
8. **Mutation gate**: choose a DOCX package-member allowlist before editing. A same-size/aspect image replacement may change only its resolved `word/media/...` member; `document.xml` must remain byte-identical.
9. **Manuscript gate**: render the protected page and affected pages after insertion. Check page flow, caption, aspect ratio, image sharpness, and that no floating object covers text. LibreOffice rendering is necessary but does not replace the package-scope invariant for WPS.

Do not bypass a failed gate by deleting a required arrow, shortening the scientific statement, shrinking text below the floor, or converting the figure into a decorative image.

## Workflow

### 1. Write the figure contract

Complete the argument, node/edge, typography, visual-vocabulary, repeated-structure, and—when relevant—DOCX mutation ledgers from `preflight-contracts.md`. At minimum record:

- central claim and target manuscript section;
- evidence/code/text supporting every node and edge;
- reading order;
- figure type and final physical size;
- elements intentionally delegated to a detail figure, table, equation, or正文;
- caption draft and alt-text draft.

For a complex system, split one overloaded panorama into a restrained overview plus detail figures. The overview shows only innovation boundaries and the principal flow.

### 2. Build the layout before styling

- Write the semantic graph before coordinates: for every structural edge record source object, relation, target object, source side, and target side. An edge whose origin or destination cannot be stated precisely is not ready to draw.
- Establish a grid, repeated module sizes, shared baselines, and whitespace groups.
- Lay out text using final fonts before drawing connectors.
- Assign typography by semantic role, not by available space. Parallel conclusions, peer module titles, paired candidates, peer flow nodes, and peer legend labels must share one typography group with identical family, size, and weight. Reflow or resize the layout instead of shrinking one long item.
- Reserve connector channels after placing nodes and before drawing arrows. At 160 mm final width, keep the visible shaft of a primary structural arrow at least 5 mm; if it is shorter, change column spacing or module width instead of enlarging the arrowhead.
- Prefer straight horizontal/vertical connectors. If a turn is semantically unavoidable, use one broad curve or one well-spaced bend; never use border-following, tight corner turns, or several short bends.
- Use a junction node only when the system really performs aggregation, comparison, or synchronization. If independent flows merely enter the same container, connect them to distinct named ports; never invent a “merge” box or circle just to tidy the lines.
- Treat paired candidates as one component: equal card geometry, labels at the same relative baseline, quantitative bars on a common baseline, and input arrows that are either mirrored with equal length or strictly parallel.
- For nested containers, connect the external source to the intact container boundary, then draw a separate internal edge between contained nodes. Never cut or erase a container border to admit an arrow.
- Give feedback loops their own routing band. Reorient the control-plane layout when possible so ordinary edges are straight and only one broad feedback curve remains.
- Keep paired structures isomorphic: same dimensions, internal grid, arrow style, and alignment; use colour/line style only for semantic differences.
- For mixed time scales, place the fast request/data plane above and the slow resource/control plane below. Never squeeze a control bar between two business lanes.
- If a label does not fit a gap with safe margins, widen/reflow the layout or move the label to a dedicated band. Never reduce font size or add spaces to force fit.

Start from [assets/paper-figure-template.svg](assets/paper-figure-template.svg) when useful.

### 3. Add semantic SVG contracts

Use the metadata described in `visual-spec.md`:

- `data-boundary-obstacle="true"` for module boundaries;
- `data-anchor-id` for source/target anchors;
- `data-source-id`, `data-source-side`, `data-target-id`, and `data-target-side` for structural arrows;
- `data-arrow-role="annotation"` for intentionally unconstrained annotation arrows;
- `data-typography-group` for text items that must share font family, size, and weight;
- `data-legend-key` and `data-legend-for` for every arrow style whose colour or line pattern carries reusable meaning;
- alignment/stack/style groups for repeated semantic structures.

These attributes make visual intent testable instead of relying on eyesight.

### 4. Run deterministic QA

From the skill directory:

```bash
uv run scripts/qa_svg.py /path/to/figure-directory --pattern '图3-*.svg'
```

This writes 600 dpi PNG previews and JSON/Markdown reports. PDF export is opt-in:

```bash
uv run scripts/qa_svg.py /path/to/figure-directory --pdf
```

Use `--audit-only` when exports must not change. Fix all reported issues and rerun until `PASS` with zero issues. Do not declare success from source inspection alone.

### 5. Perform manual pixel review

Inspect the final-size PNG at 100% and zoomed views. Verify:

- reading order and information density look like a paper, not a slide;
- labels sit close to the objects they explain;
- arrows hit the visual centre of the intended side with consistent weight, head size, direction, length, and gap;
- no text has shadows, soft edges, font substitution, odd glyph shape, or baseline drift;
- peer labels have identical apparent size and weight; no long label was silently reduced to fit;
- whitespace forms groups instead of appearing accidental;
- colour is redundant with line style, texture, position, or direct labels.
- the legend covers every meaning-bearing arrow style exactly once; a directly labelled one-off process arrow does not need a duplicate legend entry.
- every arrow can be read aloud as “source — relation — target”; no junction, short stub, or boundary crossing leaves that sentence ambiguous;
- every visible node denotes an actual operation or state; no cosmetic “merge” node was invented solely for routing convenience;
- primary arrows are not visually stunted, and every necessary turn has a generous routing channel instead of grazing a corner.

Automatic QA is necessary but not sufficient.

### 6. Insert and validate in DOCX/WPS

Prefer the editable SVG when the target WPS version renders it reliably; otherwise embed the verified 600 dpi PNG and retain the SVG beside the document. Lock aspect ratio and use an inline drawing unless the template explicitly requires floating layout.

For a same-size/aspect replacement, change only the resolved media member and keep every XML member byte-identical:

```bash
uv run scripts/docx_change_guard.py replace baseline.docx revised.docx \
  --rel-id rId5 --replacement figure.png
```

Do not reserialize `document.xml` merely to update alt text or metadata. If the drawing extent genuinely must change, treat that as a broader XML revision with an explicit allowlist, target-drawing diff, and protected-page render. Follow `docx-wps-insertion.md` exactly.

### 7. Turn feedback into a general gate

When a defect is found, reproduce it on the rendered artifact, audit the entire current figure set for the same failure class, add semantic metadata, add or tighten an automatic check, and show the old artifact failing and the corrected artifact passing. Update the maintained reference or template when the rule affects future figures. A one-coordinate patch is not a completed correction if the next new figure can repeat the same mistake.

### 8. Version and hand off

- Create a new version; never overwrite an approved baseline.
- Keep the editable source, preview, QA reports, figure contract/caption, and optional requested exports.
- Remove only clearly disposable build artifacts; do not delete reference versions without authorization.
- Report the final source path, preview path, manuscript path, QA result, and unresolved limitations.

## Completion criteria

A figure is complete only if the scientific contract is supported, automatic QA reports zero issues, manual pixel review passes, the legend and typography ledgers close, and—when applicable—the DOCX package diff stays within its declared allowlist while protected and affected pages pass rendered review.
