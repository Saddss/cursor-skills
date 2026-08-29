"""Verify that each SVG text role is covered by its declared font file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

from fontTools.ttLib import TTCollection, TTFont


FONT_FILES = {
    "cjk": Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    "math": Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    "symbol": Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
}


@lru_cache(maxsize=None)
def _cmap(role: str) -> set[int]:
    path = FONT_FILES[role]
    if path.suffix == ".ttc":
        collection = TTCollection(path)
        fonts = collection.fonts
    else:
        fonts = [TTFont(path)]
    points: set[int] = set()
    for font in fonts:
        for table in font["cmap"].tables:
            points.update(table.cmap)
    return points


def _classes(element: ET.Element) -> set[str]:
    return set(element.attrib.get("class", "").split())


def _role_for(element: ET.Element, inherited: str | None) -> str | None:
    classes = _classes(element)
    if "sym" in classes:
        return "symbol"
    if "math" in classes or "mathb" in classes or "mi" in classes:
        return "math"
    if "t" in classes:
        return "cjk"
    return inherited


def _check_text(text: str | None, role: str | None, label: str, issues: list[dict[str, object]]) -> None:
    if not text or not role:
        return
    missing = sorted({char for char in text if not char.isspace() and ord(char) not in _cmap(role)})
    if missing:
        issues.append({
            "type": "font-glyph-missing",
            "label": label,
            "role": role,
            "characters": "".join(missing),
            "codepoints": [f"U+{ord(char):04X}" for char in missing],
        })


def audit_svg_fonts(path: Path) -> list[dict[str, object]]:
    root = ET.parse(path).getroot()
    namespace = "{http://www.w3.org/2000/svg}"
    issues: list[dict[str, object]] = []
    for text in root.iter(f"{namespace}text"):
        label = "".join(text.itertext()).strip()
        base_role = _role_for(text, None)
        _check_text(text.text, base_role, label, issues)
        for child in text:
            child_role = _role_for(child, base_role)
            _check_text(child.text, child_role, label, issues)
            _check_text(child.tail, base_role, label, issues)
    return issues
