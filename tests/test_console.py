"""Runnable proposal checks: python .factory/runs/proposals/test_console.py"""
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest

from tool import console


class ConsoleProposalChecks(unittest.TestCase):
    def test_hidden_artifacts_and_wrong_image_signature_are_refused(self):
        path = self.root / '.factory/private.png'
        path.write_bytes(self.good_image.read_bytes())
        with self.assertRaises(ValueError):
            console.register_artifact(self.root, '.factory/private.png', 'capture', 'PB-001')
        self.good_image.write_bytes(b'not an image')
        with self.assertRaises(ValueError):
            console.register_artifact(self.root, 'shot.png', 'capture', 'PB-001')
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.outside_temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        runs = self.root / ".factory" / "runs"
        runs.mkdir(parents=True)
        self.good_image = self.root / "shot.png"
        self.good_image.write_bytes(b'\x89PNG\r\n\x1a\napproved image bytes')
        self.digest = hashlib.sha256(self.good_image.read_bytes()).hexdigest()
        outside = Path(self.outside_temp.name) / "outside.png"
        outside.write_bytes(b"outside")
        rows = [
            {"path": "shot.png", "sha256": self.digest, "source": "emulator", "task": "ui-check"},
            {"path": "../" + outside.name, "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(), "source": "escape"},
            {"path": "shot.png", "sha256": "0" * 64, "source": "stale-hash"},
        ]
        self.link_created = False
        try:
            (self.root / "linked.png").symlink_to(outside)
            self.link_created = True
            rows.append({"path": "linked.png", "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(), "source": "link"})
        except (OSError, NotImplementedError):
            pass
        (runs / "artifact-manifest.json").write_text(json.dumps({"artifacts": rows}), encoding="utf-8")
        self.token = "test-token-" + ("x" * 28)
        self.server = console.make_server(self.root, {
            "snapshot": lambda: {"agents": [{"id": "agent1", "task": "A task", "control": {"message": True}}],
                                 "selected": "agent1", "quota": {"remaining_fraction": 0.5,
                                 "captured_at": "2026-10-12", "observer": "official"},
                                 "director": "existing conversation", "receipts": [{"id": "r1", "agent": "agent1",
                                 "state": "NATIVE_ACK", "director": "PENDING_RECONCILIATION", "time": 1}]},
            "messages": lambda _identity: [{"role": "assistant", "text": "Public reply"},
                                           {"role": "tool", "text": "must not appear"}],
            "message": lambda *_: True, "abort": lambda *_: True,
        }, token=self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address[:2]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()
        self.outside_temp.cleanup()

    def request(self, path, headers=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=3)
        conn.request("GET", path, headers=headers or {})
        response = conn.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        conn.close()
        return result

    def auth(self, **extra):
        return {"X-Console-Token": self.token, **extra}

    def test_http_auth_host_origin_and_public_projection(self):
        status, _, _ = self.request("/api/state")
        self.assertEqual(status, 401)
        status, _, _ = self.request("/api/state", self.auth(Host="attacker.invalid"))
        self.assertEqual(status, 400)
        status, _, _ = self.request("/api/state", self.auth(Origin="http://attacker.invalid"))
        self.assertEqual(status, 403)
        status, body, _ = self.request("/api/state", self.auth(Origin=f"http://{self.host}:{self.port}"))
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["quota"]["remaining_fraction"], 0.5)
        self.assertEqual(payload["director"], "existing conversation")
        self.assertEqual(payload["receipts"][0]["state"], "NATIVE_ACK")
        self.assertEqual([m["text"] for m in payload["transcript"]], ["Public reply"])

    def test_image_endpoint_accepts_only_manifest_hash(self):
        approved = console._artifacts(self.root)
        self.assertEqual([row["id"] for row in approved], [self.digest])
        status, body, headers = self.request("/api/image/" + self.digest, self.auth())
        self.assertEqual(status, 200)
        self.assertEqual(body, self.good_image.read_bytes())
        self.assertEqual(headers["Content-Type"], "image/png")
        status, _, _ = self.request("/api/image/" + "0" * 64, self.auth())
        self.assertEqual(status, 404)

    def test_snapshot_does_not_forward_arbitrary_provider_fields(self):
        result = console._public_snapshot({"agents": [{"id": "a1", "hidden_prompt": "secret",
            "usage": {"input": 4, "secret": 99}}], "selected": "a1"})
        self.assertNotIn("hidden_prompt", result["agents"][0])
        self.assertEqual(result["agents"][0]["usage"], {"input": 4})


if __name__ == "__main__":
    unittest.main()
