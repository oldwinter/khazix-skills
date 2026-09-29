#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "hv-analysis" / "scripts" / "md_to_pdf.py"
SPEC = importlib.util.spec_from_file_location("hv_md_to_pdf", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class HvOutputTests(unittest.TestCase):
    def test_debug_html_path_is_always_distinct(self):
        self.assertEqual(MODULE.debug_html_path("report.pdf"), "report.html")
        self.assertEqual(MODULE.debug_html_path("report.PDF"), "report.html")
        self.assertEqual(MODULE.debug_html_path("report"), "report.html")

    def test_metadata_escapes_html_and_style_contexts(self):
        self.assertEqual(MODULE.html_text("<b>&\""), "&lt;b&gt;&amp;&quot;")
        escaped = MODULE.css_escape('</style><script id="pwn">')
        self.assertNotIn("</style>", escaped)
        self.assertNotIn("<script", escaped)
        self.assertIn("\\3c ", escaped)


if __name__ == "__main__":
    unittest.main()
