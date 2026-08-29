# DOCX/WPS insertion and verification

Use this procedure when a figure must be inserted into or replaced inside an approved Word/WPS document.

## Preserve the document

- Start from the latest approved DOCX and write a new versioned file.
- Do not rebuild the cover, section layout, styles, tables, or captions just to replace an image.
- Identify the exact drawing relationship (`r:embed`) and media member inside the DOCX ZIP.
- Replace only the target media bytes and the target drawing metadata needed for the new aspect ratio.
- If the cover is protected, compare its XML boundary or rendered page against the approved baseline after editing.

## Drawing geometry

- Prefer `wp:inline`; floating `wp:anchor` objects can move behind or over正文 in WPS.
- Lock aspect ratio.
- Update both representations of the size:
  - `wp:extent/@cx,@cy`;
  - `a:xfrm/a:ext/@cx,@cy`.
- Conversion: `1 mm = 36,000 EMU`.
- Keep the caption in a normal paragraph below the figure; do not bake the figure number/caption into the image.
- Follow the document's existing chapter-based numbering and cross-reference fields; never type a competing manual number when the template uses fields.

## Format choice

- Use SVG when the actual WPS version renders fonts and markers correctly.
- Otherwise embed the verified 600 dpi PNG at its designed physical size and keep the SVG as the editable source.
- Do not copy a screenshot from a browser or chat window.
- Do not repeatedly resize/recompress a raster file.

## Required validation

1. Test the DOCX ZIP integrity.
2. Verify the embedded media bytes equal the approved export.
3. Verify exactly one intended drawing uses the relationship.
4. Verify both drawing extents equal the intended millimetre size.
5. Verify caption text and cross-reference target remain intact.
6. Compare protected cover/template content with the baseline.
7. Render the DOCX to a temporary PDF/image using LibreOffice or Word automation and inspect:
   - the cover;
   - the page before the figure;
   - the figure page;
   - the following page if pagination changed.
8. Keep temporary PDF/render artifacts outside the deliverable directory when the user requested Word only.

Do not report success from XML checks alone: WPS pagination and font substitution are rendered behaviours.
