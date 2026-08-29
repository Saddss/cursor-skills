# /// script
# requires-python = ">=3.11"
# dependencies = ["lxml>=5.3.0"]
# ///
"""Verify one embedded DOCX figure without rebuilding the document."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from lxml import etree


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}
DOCUMENT = "word/document.xml"
RELS = "word/_rels/document.xml.rels"
EMU_PER_MM = 36_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--rel-id", required=True, help="drawing relationship, for example rId7")
    parser.add_argument("--width-mm", type=float, required=True)
    parser.add_argument("--height-mm", type=float, required=True)
    parser.add_argument("--expected-image", type=Path, help="compare exact embedded image bytes")
    args = parser.parse_args()

    issues: list[dict[str, object]] = []
    with zipfile.ZipFile(args.docx) as archive:
        bad_member = archive.testzip()
        if bad_member:
            issues.append({"type": "zip-corruption", "member": bad_member})

        root = etree.fromstring(archive.read(DOCUMENT))
        rel_root = etree.fromstring(archive.read(RELS))
        rels = rel_root.xpath(
            './/pr:Relationship[@Id=$rid]', namespaces=NS, rid=args.rel_id
        )
        if len(rels) != 1:
            issues.append({"type": "relationship-count", "count": len(rels)})
            media_member = None
        else:
            target = rels[0].get("Target", "")
            media_member = f"word/{target.lstrip('/')}"
            if media_member not in archive.namelist():
                issues.append({"type": "missing-media-member", "member": media_member})

        drawings = root.xpath(
            './/w:drawing[.//a:blip[@r:embed=$rid]]', namespaces=NS, rid=args.rel_id
        )
        if len(drawings) != 1:
            issues.append({"type": "drawing-count", "count": len(drawings)})
        else:
            drawing = drawings[0]
            inline_count = len(drawing.xpath("./wp:inline", namespaces=NS))
            anchor_count = len(drawing.xpath("./wp:anchor", namespaces=NS))
            if inline_count != 1 or anchor_count:
                issues.append(
                    {
                        "type": "drawing-not-inline",
                        "inline": inline_count,
                        "anchor": anchor_count,
                    }
                )

            expected = (
                round(args.width_mm * EMU_PER_MM),
                round(args.height_mm * EMU_PER_MM),
            )
            wp_extents = [
                (int(node.get("cx")), int(node.get("cy")))
                for node in drawing.xpath(".//wp:extent", namespaces=NS)
            ]
            xfrm_extents = [
                (int(node.get("cx")), int(node.get("cy")))
                for node in drawing.xpath(".//a:xfrm/a:ext", namespaces=NS)
            ]
            for kind, values in (("wp:extent", wp_extents), ("a:xfrm/a:ext", xfrm_extents)):
                if not values or any(value != expected for value in values):
                    issues.append(
                        {"type": "extent-mismatch", "kind": kind, "expected": expected, "actual": values}
                    )

        if args.expected_image and media_member and media_member in archive.namelist():
            if archive.read(media_member) != args.expected_image.read_bytes():
                issues.append({"type": "embedded-image-bytes-differ", "member": media_member})

    report = {
        "status": "PASS" if not issues else "FAIL",
        "docx": str(args.docx),
        "relationship": args.rel_id,
        "target_mm": [args.width_mm, args.height_mm],
        "issues": issues,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
