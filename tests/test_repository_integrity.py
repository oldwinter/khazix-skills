#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class RepositoryIntegrityTests(unittest.TestCase):
    def run_script(self, relative, *extra):
        return subprocess.run(
            [sys.executable, *extra, str(ROOT / relative)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_existing_regression_scripts_pass(self):
        for relative in (
            "scripts/test_readme_install_names.py",
            "hv-analysis/scripts/test_pdf_secondary_contrast.py",
            "storage-analyzer/scripts/test_scan_unsupported_platform.py",
            "neat-freak/evals/validate.py",
            "scripts/validate_repository.py",
        ):
            with self.subTest(script=relative):
                result = self.run_script(relative)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_neat_validator_rejects_optimized_mode(self):
        result = self.run_script("neat-freak/evals/validate.py", "-O")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("must run without Python -O", result.stdout + result.stderr)

    def test_python_bytecode_is_ignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("__pycache__/", text)
        self.assertIn("*.py[cod]", text)


if __name__ == "__main__":
    unittest.main()
