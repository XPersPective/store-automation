"""Public screenshot provenance regressions after retiring custom UI."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tool import artifacts


class ArtifactChecks(unittest.TestCase):
    def test_hidden_artifacts_and_wrong_image_signature_are_refused(self):
        path = self.root / '.factory/private.png'
        path.write_bytes(self.good_image.read_bytes())
        with self.assertRaises(ValueError):
            artifacts.register_artifact(self.root, '.factory/private.png', 'capture', 'PB-001')
        self.good_image.write_bytes(b'not an image')
        with self.assertRaises(ValueError):
            artifacts.register_artifact(self.root, 'shot.png', 'capture', 'PB-001')
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
    def tearDown(self):
        self.temp.cleanup()
        self.outside_temp.cleanup()

    def test_manifest_accepts_only_current_public_image_hash(self):
        approved = artifacts._artifacts(self.root)
        self.assertEqual([row['id'] for row in approved], [self.digest])
        self.good_image.write_bytes(b'changed')
        self.assertEqual(artifacts._artifacts(self.root), [])


if __name__ == '__main__':
    unittest.main()
