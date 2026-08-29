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

For SVG work, read [references/visual-spec.md](references/visual-spec.md). For any revision or final delivery, also read [references/failure-modes.md](references/failure-modes.md). When inserting into Word/WPS, read [references/docx-wps-insertion.md](references/docx-wps-insertion.md).

## Non-negotiable gates

1. **Argument gate**: define one central claim, target section, evidence source, and what the figure intentionally omits. Do not invent modules, data, mechanisms, or results.
2. **Final-size gate**: choose the physical insertion size before layout. Set SVG `width`/`height` in `mm` and a proportional `viewBox`; do not design at an arbitrary canvas then shrink it in Word.
3. **Editability gate**: keep text as `<text>`, shapes as vectors, and semantic grouping readable. Raster screenshots are previews, not source.
4. **Geometry gate**: no text overlap, boundary collision, clipping, or line-through-text. Every structural arrow has an explicit source, target, side, centerline, and terminal gap.
5. **Typography gate**: use real installed fonts and real weights only. No shadows, outlines, fake bold, malformed glyphs, or spaces used as layout controls.
6. **Rendered gate**: measure after `document.fonts.ready`, export a 600 dpi PNG, inspect the actual pixels, and repeat until automatic issues are zero.
7. **Manuscript gate**: render the DOCX/WPS page after insertion. Check page flow, caption, aspect ratio, image sharpness, and that no floating object covers text.

Do not bypass a failed gate by deleting a required arrow, shortening the scientific statement, shrinking text below the floor, or converting the figure into a decorative image.

## Workflow

### 1. Write the figure contract

Record beside the source:

- central claim and target manuscript section;
- evidence/code/text supporting every node and edge;
- reading order;
- figure type and final physical size;
- elements intentionally delegated to a detail figure, table, equation, or正文;
- caption draft and alt-text draft.

For a complex system, split one overloaded panorama into a restrained overview plus detail figures. The overview shows only innovation boundaries and the principal flow.

### 2. Build the layout before styling

- Establish a grid, repeated module sizes, shared baselines, and whitespace groups.
- Lay out text using final fonts before drawing connectors.
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
- alignment/stack/style groups for repeated semantic structures.

These attributes make visual intent testable instead of relying on eyesight.

### 4. Run deterministic QA

From the skill directory:

```bash
uv run scripts/qa_svg.py /path/to/figure-directory
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
- whitespace forms groups instead of appearing accidental;
- colour is redundant with line style, texture, position, or direct labels.

Automatic QA is necessary but not sufficient.

### 6. Insert and validate in DOCX/WPS

Prefer the editable SVG when the target WPS version renders it reliably; otherwise embed the verified 600 dpi PNG and retain the SVG beside the document. Lock aspect ratio and use an inline drawing unless the template explicitly requires floating layout.

Update both OOXML extents when replacing an image, preserve the approved cover/template, and render the affected page to a temporary preview. Follow `docx-wps-insertion.md` exactly.

### 7. Version and hand off

- Create a new version; never overwrite an approved baseline.
- Keep the editable source, preview, QA reports, figure contract/caption, and optional requested exports.
- Remove only clearly disposable build artifacts; do not delete reference versions without authorization.
- Report the final source path, preview path, manuscript path, QA result, and unresolved limitations.

## Completion criteria

A figure is complete only if the scientific contract is supported, automatic QA reports zero issues, manual pixel review passes, and—when applicable—the rendered DOCX/WPS page passes without modifying protected template content.
