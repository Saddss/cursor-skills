# Failure modes and mandatory corrections

This list captures defects that repeatedly survive casual visual inspection. Treat them as design failures, not cosmetic preferences.

| Symptom | Root cause | Required correction | Acceptance gate |
|---|---|---|---|
| Text overlaps a module or another label | Layout was drawn before final font metrics | Wait for fonts, measure rendered bounding boxes, then enlarge/reflow the region | Zero `text-text` and `text-boundary-collision` issues |
| Chinese looks blurry, shadowed, or malformed | Raster/image generation, font fallback, synthetic weight, or text effect | Use editable SVG `<text>`, installed fonts, 400/700 weight, no shadow/stroke | Font-role/glyph/effect QA passes and PNG inspection is crisp |
| Arrow touches a box or stops too far away | Endpoint chosen by eye or marker width ignored | Bind source/target sides and use a 0.8–2.0 mm visible terminal gap | Endpoint and gap metrics pass |
| Arrow points to an offset edge location | Coordinates target the box but not its side centre | Compute the selected side centre and align the shaft, including marker geometry | Centreline error at most 0.5 mm |
| Equivalent arrows differ in thickness, direction, or length | Paths and markers were created independently | Reuse one class/marker and register a style group | Width/head/angle/length dispersion passes |
| Label is visually detached from its arrow | Text and connector were positioned separately | Treat both as one optical group; keep label 1–4 mm from its arrow | Arrow-label distance passes |
| A diagonal line meets a triangle awkwardly | Connector was aimed at the bounding-box edge | Route through the triangle's visual centre and intersect its real outline, leaving radial gap | Deviation at most 0.2 mm; gap 0.8–1.2 mm |
| Y-axis title is far from the axis, or name and symbol are far apart | Separate objects or space characters used for layout | Rotate one complete title group and set explicit coordinates | Axis gap 4–6 mm; token gap 0.8–1.2 mm |
| Figure resembles a slide | Too many cards, saturated colour, decoration, or low information density | Remove decoration, tighten hierarchy, use flat restrained styling, split into overview/detail figures if necessary | Manual paper-style review passes |
| Large accidental blank areas coexist with crowded text | Local patches instead of a global grid | Rebuild the grid and allocate space by information density | Repeated modules align; whitespace has grouping purpose |
| Control logic is squeezed between two data paths | Different time scales were mixed in one row | Put the fast data plane above and slow control plane below | No control bar interrupts business-lane comparison |
| Hot/cold panels are visually incomparable | Different dimensions/internal coordinates | Use equal boxes and an isomorphic internal grid | Shared edges/centres and equivalent connectors align |
| Problem is “fixed” by deleting an arrow or shortening the claim | QA was treated as the goal instead of semantics | Restore the required meaning, then solve geometry | Figure contract and diagram remain equivalent |
| Figure looks correct alone but overlaps正文 in WPS | Floating wrapping, wrong extent, or page reflow | Use inline drawing, lock ratio, update both OOXML extents, render the page | DOCX/WPS page preview passes |
| PNG is fuzzy in Word | Low-resolution preview was embedded or resized repeatedly | Export once at final physical size and at least 600 dpi | Embedded pixels match intended size; no resampling chain |
| Approved cover/template changes while replacing a figure | Whole-document reconstruction or style rewrite | Replace the target media/drawing only and compare protected XML/visual baseline | Cover/template comparison is identical |
| A second iteration overwrites the only good version | No version boundary | Create a new version and retain the approved baseline | Previous file remains present and unchanged |

## Review sequence

Always inspect in this order:

1. claim and evidence;
2. global layout and reading order;
3. repeated-module alignment;
4. text clearance and glyph shape;
5. arrow endpoints, gaps, and style groups;
6. grayscale/non-colour semantics;
7. final-size PNG pixels;
8. rendered DOCX/WPS page.

Fixing isolated coordinates without repeating this sequence often moves the defect elsewhere.
