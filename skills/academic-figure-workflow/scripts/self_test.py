# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "cairosvg>=2.7.1",
#   "fonttools>=4.59.0",
#   "lxml>=5.3.0",
#   "pillow>=10.4.0",
#   "pyppeteer>=2.0.0",
# ]
# ///
"""Regression tests for the DOCX minimal-mutation gate."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

import docx_change_guard as guard


DOCUMENT_XML = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <w:body><w:p><w:r><w:drawing><wp:inline>
  <wp:extent cx="7200000" cy="3600000"/>
  <a:graphic><a:graphicData><pic:pic><pic:blipFill><a:blip r:embed="rId5"/></pic:blipFill>
  <pic:spPr><a:xfrm><a:ext cx="7200000" cy="3600000"/></a:xfrm></pic:spPr>
  </pic:pic></a:graphicData></a:graphic>
 </wp:inline></w:drawing></w:r></w:p></w:body>
</w:document>'''

RELS_XML = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/figure1.png"/>
</Relationships>'''

SVG_PASS = '''<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="40mm" viewBox="0 0 1600 400">
<title>QA invariant fixture</title>
<style>.t{font-family:"Noto Sans CJK SC",sans-serif;font-size:22px;font-weight:400;fill:#26323b}.arrow{stroke:#2c6e9b;stroke-width:3;fill:none}</style>
<rect width="1600" height="400" fill="#fff"/>
<text x="100" y="80" class="t" data-typography-group="peer-title">模块甲</text>
<text x="500" y="80" class="t" data-typography-group="peer-title">模块乙</text>
<path d="M100 200H400" class="arrow" data-arrow-role="annotation" data-legend-key="flow"/>
<path d="M800 200H950" class="arrow" data-arrow-role="annotation" data-legend-for="flow"/>
<text x="980" y="208" class="t">数据流</text>
</svg>'''


def png_bytes(width: int, height: int, colour: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="PNG")
    return buffer.getvalue()


def write_fixture(path: Path, image: bytes, document: bytes = DOCUMENT_XML) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", RELS_XML)
        archive.writestr("word/media/figure1.png", image)


def run_svg_audit(directory: Path, filename: str) -> tuple[int, dict[str, object]]:
    command = [
        sys.executable,
        str(Path(__file__).with_name("qa_svg.py")),
        str(directory),
        "--audit-only",
        "--pattern",
        filename,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="academic-figure-self-test-") as raw:
        root = Path(raw)
        baseline = root / "baseline.docx"
        replacement = root / "replacement.png"
        revised = root / "revised.docx"
        bad = root / "bad.docx"
        square = root / "square.png"
        mismatch = root / "mismatch.docx"
        svg_pass = root / "legend-pass.svg"
        svg_fail = root / "legend-fail.svg"

        write_fixture(baseline, png_bytes(100, 50, "white"))
        replacement.write_bytes(png_bytes(200, 100, "blue"))
        square.write_bytes(png_bytes(100, 100, "orange"))

        assert guard.replace_media(baseline, revised, "rId5", replacement, 0.005) == 0
        diff = guard.package_diff(baseline, revised)
        assert diff["changed"] == ["word/media/figure1.png"]

        write_fixture(
            bad,
            replacement.read_bytes(),
            document=DOCUMENT_XML.replace(b"</w:document>", b"<!--unwanted rewrite--></w:document>"),
        )
        assert guard.check_revision(baseline, bad, ["word/media/figure1.png"]) == 1

        try:
            guard.replace_media(baseline, mismatch, "rId5", square, 0.005)
        except ValueError as exc:
            assert "aspect ratio" in str(exc)
        else:
            raise AssertionError("aspect-ratio mismatch was not rejected")

        svg_pass.write_text(SVG_PASS, encoding="utf-8")
        pass_status, pass_report = run_svg_audit(root, svg_pass.name)
        assert pass_status == 0 and pass_report["issue_count"] == 0

        svg_fail.write_text(
            SVG_PASS.replace(' data-legend-for="flow"', "").replace(
                'x="500" y="80" class="t"',
                'x="500" y="80" class="t" style="font-size:19px"',
            ),
            encoding="utf-8",
        )
        fail_status, fail_report = run_svg_audit(root, svg_fail.name)
        issue_types = {
            issue["type"]
            for figure in fail_report["figures"]
            for issue in figure["issues"]
        }
        assert fail_status == 1
        assert "arrow-legend-coverage-mismatch" in issue_types
        assert "typography-group-mismatch" in issue_types

    print("self_test=PASS")
    print("media_only_change_scope=PASS")
    print("unwanted_document_xml_change=REJECTED")
    print("aspect_ratio_mismatch=REJECTED")
    print("complete_legend_and_peer_typography=PASS")
    print("missing_legend_and_peer_size_mismatch=REJECTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
