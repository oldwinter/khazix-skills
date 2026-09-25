#!/usr/bin/env python3
"""Lock PDF chrome secondary text to #5d6d7e on white (WCAG AA)."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "md_to_pdf.py"
SECONDARY = "#5d6d7e"
BANNED = "#95a5a6"
WHITE = "#ffffff"
HEADER_SELECTORS = ("@top-center", "@bottom-center", ".cover .subtitle", ".cover .meta")


def load_css_template() -> str:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "CSS_TEMPLATE" in names and isinstance(node.value, ast.Constant):
                return node.value.value
    raise AssertionError("CSS_TEMPLATE string not found in md_to_pdf.py")


def hex_to_srgb(color: str) -> tuple[float, float, float]:
    raw = color.removeprefix("#")
    return tuple(int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))


def relative_luminance(color: str) -> float:
    channels = []
    for channel in hex_to_srgb(color):
        if channel <= 0.04045:
            channels.append(channel / 12.92)
        else:
            channels.append(((channel + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(fg: str, bg: str) -> float:
    lighter, darker = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def rule_color(css: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]+)\}", css)
    if not match:
        raise AssertionError(f"missing CSS rule for {selector}")
    color = re.search(r"color:\s*(#[0-9a-fA-F]{6})", match.group(1))
    if not color:
        raise AssertionError(f"{selector} has no hex color")
    return color.group(1).lower()


class PdfSecondaryContrastTests(unittest.TestCase):
    def test_secondary_chrome_uses_blockquote_ink(self) -> None:
        css = load_css_template()
        self.assertNotIn(BANNED, css.lower())
        self.assertGreaterEqual(contrast_ratio(SECONDARY, WHITE), 4.5)
        for selector in HEADER_SELECTORS:
            self.assertEqual(rule_color(css, selector), SECONDARY)
        self.assertEqual(rule_color(css, "blockquote"), SECONDARY)


if __name__ == "__main__":
    unittest.main()
