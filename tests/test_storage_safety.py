#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVER = ROOT / "storage-analyzer" / "scripts" / "server.py"
BUILD_REPORT = ROOT / "storage-analyzer" / "scripts" / "build_report.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def post(module, payload, content_length=None):
    handler = object.__new__(module.Handler)
    handler.path = "/action"
    raw = json.dumps(payload).encode()
    handler.headers = {
        "Host": "127.0.0.1",
        "Content-Length": str(len(raw)) if content_length is None else content_length,
    }
    handler.rfile = io.BytesIO(raw)
    responses = []
    handler._send = lambda code, body, ctype="application/json": responses.append((code, body))
    handler.do_POST()
    return responses


class StorageSafetyTests(unittest.TestCase):
    def test_script_json_escapes_closing_tags(self):
        payload = {"value": "</script><script id=pwn>&\u2028"}
        for path, name in ((SERVER, "server_json"), (BUILD_REPORT, "build_json")):
            with self.subTest(module=name):
                encoded = load(path, name).json_for_script(payload)
                self.assertNotIn("</script>", encoded)
                self.assertIn("\\u003c/script\\u003e", encoded)
                self.assertIn("\\u0026", encoded)
                self.assertIn("\\u2028", encoded)

    def test_mixed_batch_performs_no_mutation(self):
        module = load(SERVER, "server_batch")
        with tempfile.TemporaryDirectory() as tmp:
            valid = pathlib.Path(tmp) / "cache"
            valid.mkdir()
            module.HOME = tmp
            module.TOKEN = "token"
            module.RM_ALLOW = {str(valid)}
            module.TRASH_ALLOW = set()
            module.OPEN_ALLOW = set()
            deleted = []
            module.hard_delete = lambda path: deleted.append(path)
            responses = post(module, {"token": "token", "mode": "rm", "paths": [str(valid), str(valid) + "-bad"]})
            self.assertEqual(responses[-1][0], 403)
            self.assertEqual(deleted, [])

    def test_request_shape_and_size_are_bounded(self):
        module = load(SERVER, "server_body")
        module.TOKEN = "token"
        self.assertEqual(post(module, {}, content_length="bad")[-1][0], 400)
        too_large = str(module.MAX_BODY_BYTES + 1)
        self.assertEqual(post(module, {}, content_length=too_large)[-1][0], 413)
        self.assertEqual(post(module, {"token": "token", "mode": "rm", "paths": "not-a-list"})[-1][0], 400)

    def test_destructive_actions_reject_home_and_trash_roots(self):
        module = load(SERVER, "server_roots")
        with tempfile.TemporaryDirectory() as tmp:
            trash = pathlib.Path(tmp) / ".Trash"
            trash.mkdir()
            module.HOME = tmp
            module.TOKEN = "token"
            module.RM_ALLOW = {tmp, str(trash)}
            module.TRASH_ALLOW = set()
            module.OPEN_ALLOW = set()
            deleted = []
            module.hard_delete = lambda path: deleted.append(path)
            for target in (tmp, str(trash)):
                with self.subTest(target=target):
                    responses = post(module, {"token": "token", "mode": "rm", "paths": [target]})
                    self.assertEqual(responses[-1][0], 403)
            self.assertEqual(deleted, [])


if __name__ == "__main__":
    unittest.main()
