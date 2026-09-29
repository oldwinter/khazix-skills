#!/usr/bin/env python3
"""Regression test for unsupported storage-scan platforms."""

import json
import pathlib
import subprocess
import sys
import unittest


SCAN = pathlib.Path(__file__).with_name("scan.py")


class UnsupportedPlatformTests(unittest.TestCase):
    @unittest.skipIf(
        sys.platform == "darwin" or sys.platform.startswith("win"),
        "this regression exercises the unsupported-platform branch",
    )
    def test_error_payload_uses_failure_exit_code(self):
        result = subprocess.run(
            [sys.executable, str(SCAN)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["error"], "unsupported_platform")
        self.assertEqual(payload["platform"], sys.platform)


if __name__ == "__main__":
    unittest.main()
