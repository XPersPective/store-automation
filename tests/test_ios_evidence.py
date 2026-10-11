import base64
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('ios_evidence', Path(__file__).parents[1] / 'tool/ios-evidence.py')
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class IosEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.logs, self.output = self.root / 'run.log', self.root / 'screenshot.png'
        self.png = b'\x89PNG\r\n\x1a\n' + b'public fixture' * 30

    def block(self, png=None):
        png = self.png if png is None else png
        encoded = base64.b64encode(png).decode()
        prefix = 'simulator\tCapture\t2026-10-11T12:00:00Z '
        lines = [f'STORE_AUTOMATION_PNG_BEGIN launch {len(png)} {hashlib.sha256(png).hexdigest()}']
        lines += ['STORE_AUTOMATION_PNG_DATA ' + encoded[i:i + 120] for i in range(0, len(encoded), 120)]
        lines += ['STORE_AUTOMATION_PNG_END launch']
        return '\n'.join(prefix + line for line in lines) + '\n'

    def run_extract(self, text):
        self.logs.write_text(text)
        return evidence.extract(self.logs, self.output)

    def assert_rejected(self, text):
        with self.assertRaises(ValueError):
            self.run_extract(text)
        self.assertFalse(self.output.exists())

    def test_good_prefixed_chunked_log_is_verified_before_write(self):
        echoed = "simulator\tCapture\t2026-10-11T12:00:00Z print('STORE_AUTOMATION_PNG_BEGIN launch', size)\n"
        result = self.run_extract('ordinary build output\n' + echoed + self.block() + 'cleanup\n')
        self.assertEqual(self.output.read_bytes(), self.png)
        self.assertEqual(result['sha256'], hashlib.sha256(self.png).hexdigest())
        self.assertFalse(result['remote_provenance_verified'])

    def test_missing_truncated_nested_duplicate_and_bad_marker_are_rejected(self):
        block = self.block()
        for text in ('ordinary log', block.rsplit('STORE_AUTOMATION_PNG_END', 1)[0],
                     block + block, block.splitlines()[0] + '\n' + block,
                     block.replace('END launch', 'END wrong'),
                     block.replace('STORE_AUTOMATION_PNG_DATA ', 'STORE_AUTOMATION_PNG_DATA !', 1),
                     block.replace('STORE_AUTOMATION_PNG_DATA ', 'unexpected\nSTORE_AUTOMATION_PNG_DATA ', 1)):
            with self.subTest(text=text[:60]):
                self.assert_rejected(text)

    def test_size_hash_and_signature_mismatch_preserve_absent_output(self):
        block = self.block()
        for text in (block.replace(f'launch {len(self.png)} ', f'launch {len(self.png) + 1} ', 1),
                     block.replace(hashlib.sha256(self.png).hexdigest(), '0' * 64),
                     self.block(b'not a PNG image'),
                     block.replace(f'launch {len(self.png)} ', f'launch {evidence.MAX_PNG + 1} ', 1),
                     block.replace(f'launch {len(self.png)} ', 'launch 0 ', 1)):
            with self.subTest(text=text[:60]):
                self.assert_rejected(text)

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b'user file')
        with self.assertRaises(FileExistsError):
            self.run_extract(self.block())
        self.assertEqual(self.output.read_bytes(), b'user file')

    def test_line_and_file_bounds_are_enforced(self):
        self.assert_rejected('x' * (evidence.MAX_LINE + 1))
        from unittest.mock import patch
        with patch.object(evidence, 'MAX_LOG', 10):
            self.assert_rejected(self.block())

    def test_data_after_padding_and_outside_block_are_rejected(self):
        self.assert_rejected('STORE_AUTOMATION_PNG_BEGIN launch 2 ' + '0' * 64 + '\n'
                             'STORE_AUTOMATION_PNG_DATA YQ==\nSTORE_AUTOMATION_PNG_DATA YQ==\n'
                             'STORE_AUTOMATION_PNG_END launch\n')
        self.assert_rejected('STORE_AUTOMATION_PNG_DATA YQ==\n' + self.block())


if __name__ == '__main__':
    unittest.main()
