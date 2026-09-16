#!/usr/bin/env python3
"""Lock README install names to first-level skill folders."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README_ZH = ROOT / "README.md"
README_EN = ROOT / "README.en.md"
SKILL_DIRS = frozenset(path.parent.name for path in ROOT.glob("*/SKILL.md"))


def section_after(text: str, heading_token: str) -> str:
    match = re.search(
        rf"^## [^\n]*{re.escape(heading_token)}[^\n]*\n(.*?)(?=^## |\Z)",
        text,
        flags=re.M | re.S,
    )
    if not match:
        raise AssertionError(f"missing section containing {heading_token!r}")
    return match.group(1)


def table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(r":?-{3,}:?", cells[0]):
            continue
        rows.append(cells)
    return rows


def fenced_names(text: str) -> set[str]:
    return set(re.findall(r"`([a-z0-9-]+)`", text))


class ReadmeInstallNameTests(unittest.TestCase):
    def test_zh_catalog_exposes_folder_install_names(self) -> None:
        section = section_after(README_ZH.read_text(encoding="utf-8"), "目录")
        rows = table_rows(section)
        self.assertGreaterEqual(len(rows), 2, "catalog table is missing")
        header = rows[0]
        self.assertIn("安装名", header)
        install_idx = header.index("安装名")
        names: list[str] = []
        for row in rows[1:]:
            self.assertGreater(len(row), install_idx, row)
            cell = row[install_idx]
            match = re.fullmatch(r"`([a-z0-9-]+)`", cell)
            self.assertIsNotNone(match, f"install name is not a scannable folder: {cell}")
            names.append(match.group(1))
        self.assertEqual(set(names), set(SKILL_DIRS))
        self.assertEqual(len(names), len(SKILL_DIRS))

    def test_install_sections_list_every_skill_folder(self) -> None:
        zh_install = section_after(README_ZH.read_text(encoding="utf-8"), "安装方式")
        en_install = section_after(README_EN.read_text(encoding="utf-8"), "Install")
        for label, section in (("zh", zh_install), ("en", en_install)):
            with self.subTest(readme=label):
                self.assertIn("<skill-name>", section)
                self.assertTrue(SKILL_DIRS.issubset(fenced_names(section)), section)


if __name__ == "__main__":
    unittest.main()
