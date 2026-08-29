# DOCX/WPS insertion and verification

Use this procedure when a figure must be inserted into or replaced inside an approved Word/WPS document.

## Preserve the document

- Start from the latest approved DOCX and write a new versioned file.
- Do not rebuild the cover, section layout, styles, tables, or captions just to replace an image.
- Identify the exact drawing relationship (`r:embed`) and media member inside the DOCX ZIP.
- Declare the permitted ZIP-member change set before editing.
- For a same-size/aspect replacement, replace only the target media bytes. Do not parse/serialize `document.xml`, update alt text, normalize namespaces, or touch metadata opportunistically.
- For a same-size/aspect replacement, compare the whole package against the baseline: the changed-member set must contain exactly the resolved media member. A cover-prefix XML comparison is not sufficient.
- If the cover is protected, compare its rendered pixels against the approved baseline in addition to the package check.

Use the guarded replacement command:

```bash
uv run scripts/docx_change_guard.py replace baseline.docx revised.docx \
  --rel-id rId5 --replacement figure.png
```

To audit a revision created elsewhere:

```bash
uv run scripts/docx_change_guard.py check baseline.docx revised.docx \
  --allow word/media/figure31.png
```

## Drawing geometry

- Prefer `wp:inline`; floating `wp:anchor` objects can move behind or over正文 in WPS.
- Lock aspect ratio.
- Update both representations of the size:
  - `wp:extent/@cx,@cy`;
  - `a:xfrm/a:ext/@cx,@cy`.
- Conversion: `1 mm = 36,000 EMU`.
- Keep the caption in a normal paragraph below the figure; do not bake the figure number/caption into the image.
- Follow the document's existing chapter-based numbering and cross-reference fields; never type a competing manual number when the template uses fields.

Changing extents or alt text is not a media-only revision. If it is genuinely required, allow `word/document.xml` explicitly, modify only the targeted drawing subtree, and prove that protected pages still render identically. Prefer regenerating the figure at the existing aspect ratio when that avoids an unnecessary XML mutation.

## Format choice

- Use SVG when the actual WPS version renders fonts and markers correctly.
- Otherwise embed the verified 600 dpi PNG at its designed physical size and keep the SVG as the editable source.
- Do not copy a screenshot from a browser or chat window.
- Do not repeatedly resize/recompress a raster file.

## Required validation

1. Test the DOCX ZIP integrity.
2. Compare package-member names and bytes against the declared change allowlist.
3. For media-only replacement, assert the changed-member set is exactly one `word/media/...` member and the entire `document.xml` is byte-identical.
4. Verify the embedded media bytes equal the approved export.
5. Verify exactly one intended drawing uses the relationship.
6. Verify both drawing extents equal the intended millimetre size and the replacement aspect ratio matches them.
7. Verify caption text and cross-reference target remain intact.
8. Compare protected cover/template pixels with the approved baseline.
9. Render the DOCX to a temporary PDF/image using LibreOffice or Word automation and inspect:
   - the cover;
   - the page before the figure;
   - the figure page;
   - the following page if pagination changed.
10. Keep temporary PDF/render artifacts outside the deliverable directory when the user requested Word only.

Do not report WPS success from LibreOffice rendering alone. When WPS itself is unavailable, say so and rely on the strongest portable guarantees: minimal package mutation, exact XML preservation, relationship/extent validation, and protected-page pixel comparison. Withdraw rejected revisions so that a broken file cannot be mistaken for the latest version.
