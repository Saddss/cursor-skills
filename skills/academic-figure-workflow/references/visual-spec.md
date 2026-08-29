# Academic SVG visual specification

Apply these rules to mechanism, architecture, workflow, and conceptual figures. Values are defaults for a 150–160 mm-wide thesis figure; adjust only when the manuscript template requires it, then preserve the same physical relationships.

## Canvas and grid

- Declare physical `width` and `height` in millimetres. Use a proportional `viewBox` such as `0 0 1600 820` for `160mm × 82mm`.
- Keep at least 1.5 mm canvas safety margin.
- Use a 2 mm baseline grid for module edges, text baselines, and connector terminals. Common spacing tokens are 2, 4, 6, 8, and 12 mm.
- Repeated modules must be equal width, equal height, and equally spaced. When dimensions differ for semantic reasons, align their centre axes or a common edge.
- Treat a label, its symbol, and its arrow as one optical group. Numeric centring is not enough when font width or colour weight creates visible imbalance; optical correction up to 1 mm is acceptable.

## Typography

- Chinese labels: `Noto Sans CJK SC`, with `Microsoft YaHei` as a WPS fallback.
- Latin/math: `Liberation Sans` or Arial. Symbols not covered there may use `DejaVu Sans`.
- Use installed Regular 400 and Bold 700 only. Do not request synthetic 500/600 weights.
- At 160 mm final width, ordinary SVG text must be at least 19 user-space px (about 5.3 pt after insertion); important labels should be larger.
- No text shadow, outline, glow, blur, gradient, or faux 3D effect.
- Never use half-width/full-width spaces to create layout. Position text with coordinates, `dx`, or separate explicitly anchored elements.
- Avoid centred mixed-font implicit `<tspan>` runs. Give each segment an explicit anchor/coordinate when mixed typography is required.
- Keep multi-line text line height at least 1.20 times the font size.

## Text clearance

- Visible text-to-text separation: at least 1.0 mm.
- Text-to-line or text-to-boundary separation: at least 1.0 mm.
- Module internal horizontal padding: at least 1.2 mm; vertical padding: at least 0.8 mm.
- If a label cannot fit with these margins, change the layout. Never fix it by shrinking below the font floor, inserting spaces, or allowing the boundary to pass behind the text.
- Mark boundaries near text with `data-boundary-obstacle="true"` so rendered QA can measure the real font boxes.

## Arrow contract

Every structural arrow must specify source and target semantics:

```xml
<rect data-anchor-id="source" .../>
<rect data-anchor-id="target" .../>
<path data-source-id="source" data-source-side="right"
      data-target-id="target" data-target-side="left" .../>
```

- Arrow centreline error relative to the selected side centre: at most 0.5 mm.
- Independent arrows keep 0.8–2.0 mm visible gap at both source and target; 1.5 mm is a reliable default.
- A continuous/touch leader may use a −0.2–0.2 mm start gap only when explicitly marked as such.
- Labels bound to arrows sit 1.0–4.0 mm away.
- An arrowhead points to the target side centre, not merely somewhere on the right/left boundary.
- Same-role arrows form an isomorphic style group: line width and head-size dispersion no more than 0.1 px, length dispersion no more than 0.3 mm when equal length is intended, and parallel-angle error no more than 0.5 degrees.
- Do not delete a semantically required arrow to make QA pass.

### Non-circular markers

Triangles are easily misread as arrowheads. When a diagonal leader points to a triangle:

- preserve the intended diagonal direction;
- extend the leader ray through the marker's visual centre;
- terminate at the actual outline intersection, then leave a 0.8–1.2 mm radial gap;
- allow no more than 0.2 mm visual-centre deviation;
- match the line/head style used for the equivalent circle annotation.

## Axes and formulas

- The visible edge of an axis title must be 4–6 mm from the axis line.
- Chinese axis name and its mathematical symbol must appear as one optical group with 0.8–1.2 mm visible separation.
- Rotate the complete y-axis title group; do not place the Chinese label and symbol independently.
- Preserve real italic variables, upright operators/functions, and real superscripts/subscripts. Never fake formula spacing with spaces.

## Colour and paper style

- Default: white background, flat fills, thin grey structure, one restrained blue and one restrained orange for semantic contrast.
- A proven palette is: text `#26323B`, neutral `#52606B`, hot/reusable `#2C6E9B`, cold/low-reuse `#C96B2C`, light neutral `#EEF1F3`.
- Colour cannot be the sole carrier of meaning. Pair it with solid/dashed lines, hatching, position, or direct labels.
- Avoid presentation tropes: oversized title cards, decorative icons, gradients, saturated backgrounds, drop shadows, excessive rounded cards, and low-information whitespace.

## Architecture panoramas

- Keep the overview to innovation modules and the principal flow; move formulas, thresholds, numerical results, and request timelines to detail figures.
- For mixed time scales use upper request/data plane plus lower resource/control plane.
- Paired hot/cold or baseline/proposed pools must share the same size, start edge, internal Service/Deployment grid, and connector geometry.
- Allocate space by information density: a Router may stack algorithm modules vertically; parallel pools remain aligned for comparison.

## Metadata understood by `qa_svg.py`

- `data-boundary-obstacle="true"`: module outline that text must clear.
- `data-anchor-id="..."`: semantic anchor.
- `data-source-id`, `data-source-side`, `data-target-id`, `data-target-side`: arrow endpoint contract.
- `data-arrow-role="annotation"`: arrow intentionally excluded from source/target checks.
- `data-align-group` and direction metadata: optical centre-axis group.
- `data-stack-group`, `data-stack-order`: vertical information group.
- `data-arrow-style-group`: arrows that must share style/length/direction.
- `data-axis-title` and `data-axis-part`: axis-title clearance and name/symbol spacing.
