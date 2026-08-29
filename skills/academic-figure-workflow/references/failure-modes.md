# Failure modes and mandatory corrections

This list captures defects that repeatedly survive casual visual inspection. Treat them as design failures, not cosmetic preferences.

| Symptom | Root cause | Required correction | Acceptance gate |
|---|---|---|---|
| Text overlaps a module or another label | Layout was drawn before final font metrics | Wait for fonts, measure rendered bounding boxes, then enlarge/reflow the region | Zero `text-text` and `text-boundary-collision` issues |
| Chinese looks blurry, shadowed, or malformed | Raster/image generation, font fallback, synthetic weight, or text effect | Use editable SVG `<text>`, installed fonts, 400/700 weight, no shadow/stroke | Font-role/glyph/effect QA passes and PNG inspection is crisp |
| Peer labels use different font sizes | Text was sized locally to fit instead of assigned a semantic role | Put peer labels in one typography group and reflow the layout so all use identical family, size, and weight | `typography-group-mismatch` count is zero; size spread is 0 px |
| Arrow touches a box or stops too far away | Endpoint chosen by eye or marker width ignored | Bind source/target sides and use a 0.8–2.0 mm visible terminal gap | Endpoint and gap metrics pass |
| Arrow points to an offset edge location | Coordinates target the box but not its side centre | Compute the selected side centre and align the shaft, including marker geometry | Centreline error at most 0.5 mm |
| Arrow is so short that its direction is hard to read | Adjacent modules consume the connector channel | Widen the channel or narrow/reflow modules; preserve at least 5 mm visible shaft at 160 mm final width | Manual review confirms a readable shaft; no oversized head workaround |
| It is unclear where an arrow originates or terminates | The diagram was drawn as lines before its semantic graph was defined | Create an edge ledger and bind both endpoints to named anchors and sides | Every structural edge can be read as `source — relation — target` |
| Multiple inputs merge into an unexplained stub | An implicit line intersection was used as a logical operator | If a real aggregation exists, add its semantic node; otherwise connect independent flows to separate named ports on the common container | No anonymous merge, fake “merge” node, or source-less output arrow |
| A “merge” circle appears although the system has no merge operation | A geometry rule was mistaken for a system component | Delete the invented node and route each independent flow to its own container port | Every visible node maps to a real operation or state |
| Paired candidates have labels at different heights or arrows aimed at unrelated locations | Candidate cards were positioned independently | Rebuild them as one mirrored component with shared dimensions, baselines, and equal-length mirrored/parallel arrows | Visual symmetry and target-port symmetry pass manual review |
| Arrow makes a tight turn against a module corner | Local coordinates were patched without reserving a routing channel | Reflow modules for a straight connector or use one broad curve with clearance | No corner-grazing or consecutive short bends |
| Container border has an artificial gap under an arrow | Border was erased to hide a collision | Keep the container intact; target it externally and express the internal relation with a second arrow | Continuous border and two explicit relations |
| Feedback path snakes through titles and modules | Fast and slow paths were laid out in the same direction without a return band | Reverse or reorder the slow path and reserve one dedicated feedback band with a broad curve | Feedback line crosses no text/module and uses at most one broad return curve |
| Equivalent arrows differ in thickness, direction, or length | Paths and markers were created independently | Reuse one class/marker and register a style group | Width/head/angle/length dispersion passes |
| Several semantic arrow styles appear but the legend explains only some of them | Legend was written as decoration rather than checked against the diagram's visual vocabulary | Give each meaning-bearing arrow style a semantic key and provide one matching legend sample; directly labelled local process arrows may remain outside the legend | `arrow-legend-coverage-mismatch` count is zero |
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
| Cover looks unchanged in LibreOffice but breaks in WPS after a figure replacement | A media-only edit also reserialized `document.xml`; prefix comparison and one renderer hid the broader mutation | Rebuild from the last approved DOCX and change only the resolved media member; keep the entire `document.xml` byte-identical | Package diff reports exactly one changed `word/media/...` member; protected cover pixel diff is zero |
| A user-reported defect is fixed in one screenshot but reappears in another/new figure | Coordinates were patched without promoting the failure into a semantic contract and deterministic gate | Audit the whole figure set, add metadata plus a checker/regression fixture, then update the maintained reference/template | Old artifact fails the new check; corrected set passes with zero issues |
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
