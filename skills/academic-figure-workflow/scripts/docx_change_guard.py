# /// script
# requires-python = ">=3.11"
# dependencies = ["lxml>=5.3.0", "pillow>=10.4.0"]
# ///
"""Guard surgical DOCX figure revisions with ZIP-member allowlists.

Use ``replace`` when the drawing size and aspect ratio stay unchanged.  It
copies every package member byte-for-byte except the resolved media member.
Use ``check`` to audit any externally produced revision against an allowlist.
"""

from __future__ import annotations

import argparse
import copy
import io
import json
import posixpath
import re
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image


DOCUMENT = "word/document.xml"
RELS = "word/_rels/document.xml.rels"
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def clone_info(info: zipfile.ZipInfo) -> zipfile.ZipInfo:
    cloned = copy.copy(info)
    cloned.CRC = 0
    cloned.compress_size = 0
    cloned.file_size = 0
    return cloned


def package_diff(baseline: Path, candidate: Path) -> dict[str, object]:
    with zipfile.ZipFile(baseline) as before, zipfile.ZipFile(candidate) as after:
        before_names = set(before.namelist())
        after_names = set(after.namelist())
        changed = sorted(
            name
            for name in before_names & after_names
            if before.read(name) != after.read(name)
        )
        return {
            "changed": changed,
            "missing": sorted(before_names - after_names),
            "added": sorted(after_names - before_names),
            "corrupt_member": after.testzip(),
        }


def parse_svg_length(value: str) -> float:
    match = re.fullmatch(r"\s*([0-9.]+)\s*(mm|cm|in|pt|px)?\s*", value)
    if not match:
        raise ValueError(f"unsupported SVG length: {value!r}")
    number = float(match.group(1))
    unit = match.group(2) or "px"
    to_px = {"px": 1.0, "pt": 96.0 / 72.0, "in": 96.0, "mm": 96.0 / 25.4, "cm": 96.0 / 2.54}
    return number * to_px[unit]


def replacement_ratio(path: Path) -> float:
    if path.suffix.lower() == ".svg":
        root = etree.fromstring(path.read_bytes())
        width = root.get("width")
        height = root.get("height")
        if width and height:
            return parse_svg_length(width) / parse_svg_length(height)
        view_box = root.get("viewBox")
        if view_box:
            _, _, width_value, height_value = map(float, view_box.split())
            return width_value / height_value
        raise ValueError("SVG replacement needs width/height or viewBox")
    with Image.open(io.BytesIO(path.read_bytes())) as image:
        return image.width / image.height


def resolve_figure(archive: zipfile.ZipFile, rel_id: str) -> tuple[str, float]:
    rel_root = etree.fromstring(archive.read(RELS))
    relationships = rel_root.xpath(
        './/pr:Relationship[@Id=$rid]', namespaces=NS, rid=rel_id
    )
    if len(relationships) != 1:
        raise ValueError(f"{rel_id}: relationship count is {len(relationships)}, expected 1")
    target = relationships[0].get("Target", "")
    member = posixpath.normpath(posixpath.join("word", target.lstrip("/")))
    if member not in archive.namelist():
        raise ValueError(f"{rel_id}: media member does not exist: {member}")

    document = etree.fromstring(archive.read(DOCUMENT))
    drawings = document.xpath(
        './/wp:inline[.//a:blip[@r:embed=$rid]]', namespaces=NS, rid=rel_id
    )
    if len(drawings) != 1:
        raise ValueError(f"{rel_id}: inline drawing count is {len(drawings)}, expected 1")
    extents = [
        (int(node.get("cx")), int(node.get("cy")))
        for node in drawings[0].xpath(".//wp:extent", namespaces=NS)
    ]
    transform_extents = [
        (int(node.get("cx")), int(node.get("cy")))
        for node in drawings[0].xpath(".//a:xfrm/a:ext", namespaces=NS)
    ]
    if len(extents) != 1 or not transform_extents or any(item != extents[0] for item in transform_extents):
        raise ValueError(f"{rel_id}: drawing extents are missing or inconsistent")
    cx, cy = extents[0]
    return member, cx / cy


def check_revision(baseline: Path, candidate: Path, allowed: list[str]) -> int:
    result = package_diff(baseline, candidate)
    expected = sorted(set(allowed))
    passed = (
        result["changed"] == expected
        and not result["missing"]
        and not result["added"]
        and result["corrupt_member"] is None
    )
    report = {
        "status": "PASS" if passed else "FAIL",
        **result,
        "allowed": expected,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


def replace_media(
    baseline: Path,
    output: Path,
    rel_id: str,
    replacement: Path,
    ratio_tolerance: float,
) -> int:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing file: {output}")
    with zipfile.ZipFile(baseline, "r") as source:
        media_member, drawing_ratio = resolve_figure(source, rel_id)
        replacement_suffix = replacement.suffix.lower()
        member_suffix = Path(media_member).suffix.lower()
        if replacement_suffix != member_suffix:
            raise ValueError(
                f"replacement extension {replacement_suffix} does not match package member {member_suffix}"
            )
        image_ratio = replacement_ratio(replacement)
        relative_error = abs(image_ratio - drawing_ratio) / drawing_ratio
        if relative_error > ratio_tolerance:
            raise ValueError(
                f"replacement aspect ratio differs from drawing extent: "
                f"image={image_ratio:.6f}, drawing={drawing_ratio:.6f}, "
                f"relative_error={relative_error:.6f}"
            )
        with zipfile.ZipFile(output, "w") as target:
            for info in source.infolist():
                data = replacement.read_bytes() if info.filename == media_member else source.read(info.filename)
                target.writestr(clone_info(info), data)

    status = check_revision(baseline, output, [media_member])
    if status:
        raise RuntimeError("post-write DOCX change-scope check failed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="compare package members against an allowlist")
    check.add_argument("baseline", type=Path)
    check.add_argument("candidate", type=Path)
    check.add_argument("--allow", action="append", required=True)

    replace = subparsers.add_parser("replace", help="replace exactly one figure media member")
    replace.add_argument("baseline", type=Path)
    replace.add_argument("output", type=Path)
    replace.add_argument("--rel-id", required=True)
    replace.add_argument("--replacement", required=True, type=Path)
    replace.add_argument("--ratio-tolerance", type=float, default=0.005)

    args = parser.parse_args()
    if args.command == "check":
        return check_revision(args.baseline, args.candidate, args.allow)
    return replace_media(
        args.baseline,
        args.output,
        args.rel_id,
        args.replacement,
        args.ratio_tolerance,
    )


if __name__ == "__main__":
    raise SystemExit(main())
