import os
from pathlib import Path
import sys
import tempfile
import unittest

from runtime.verification import release_readback, run_command


class VerificationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'source.txt').write_text('input')

    def execute(self, argv, timeout=60):
        return run_command(self.root, argv, self.root / 'runs/x.log', timeout)

    def test_actual_command_success_and_failure_with_full_log(self):
        result = self.execute([sys.executable, '-c', 'print("real execution")'])
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('real execution', (self.root / 'runs/x.log').read_text())
        self.assertEqual(self.execute([sys.executable, '-c', 'raise SystemExit(2)'])['exit_code'], 2)

    @unittest.skipUnless(os.name == 'nt', 'Windows batch resolution')
    def test_batch_tools_and_project_scripts_resolve_like_a_shell(self):
        tools = self.root / 'tools'
        tools.mkdir()
        (tools / 'probe.cmd').write_text('@exit /b 0')
        self.assertEqual(self.execute(['tools/probe.cmd'])['exit_code'], 0)
        old = os.environ['PATH']
        os.environ['PATH'] = str(tools) + os.pathsep + old
        try:
            self.assertEqual(self.execute(['probe'])['exit_code'], 0)
        finally:
            os.environ['PATH'] = old

    @unittest.skipUnless(os.name == 'nt', 'cmd.exe argument parsing')
    def test_batch_arguments_cannot_inject_commands(self):
        """B05: argv safety ends at a .cmd/.bat boundary unless metacharacters are refused."""
        (self.root / 'probe.cmd').write_text('@exit /b 0')
        for arg in ('x&echo hit>injected.txt', 'a|b', '%COMSPEC%', 'x"&calc'):
            with self.assertRaises(ValueError, msg=arg):
                self.execute(['./probe.cmd', arg])
        self.assertFalse((self.root / 'injected.txt').exists())
        self.assertEqual(self.execute(['./probe.cmd', 'plain-arg'])['exit_code'], 0)

    def test_stale_bytecode_cannot_answer_for_edited_source(self):
        """B09: same size, same mtime, different source: the run must see the new source."""
        mod = self.root / 'greet.py'
        mod.write_text('WORD = "selam"\n')
        stamp = mod.stat().st_mtime_ns
        import py_compile
        py_compile.compile(str(mod), cfile=str(self.root / '__pycache__' / f'greet.{sys.implementation.cache_tag}.pyc'))
        mod.write_text('WORD = "wrong"\n')
        os.utime(mod, ns=(stamp, stamp))
        result = self.execute([sys.executable, '-c', 'import greet; raise SystemExit(greet.WORD != "wrong")'])
        self.assertEqual(result['exit_code'], 0)

    def test_real_timeout_kills_owned_descendant_before_delayed_write(self):
        marker = self.root / 'orphan.txt'
        child = 'import time; from pathlib import Path; time.sleep(1.5); Path("orphan.txt").write_text("bad")'
        parent = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",' + repr(child) + ']); time.sleep(20)'
        result = self.execute([sys.executable, '-c', parent], timeout=.15)
        self.assertEqual(result['exit_code'], 124)
        import time
        time.sleep(1.7)
        self.assertFalse(marker.exists())

    def test_release_exit_success_cannot_replace_exact_remote_readback(self):
        expected = dict(platform='android', account='selected', app='com.example.test',
                        channel='internal', version='3', artifact_sha256='digest', state='AVAILABLE')
        observed = dict(expected, state='UPLOADED', readback_reference='tool:1',
                        observed_at='2026-10-13T12:00:00Z', provenance='verified')
        self.assertEqual(release_readback(expected, observed)['status'], 'UNVERIFIED')
        observed.update(state='AVAILABLE', availability_reference='tool:public-url')
        self.assertEqual(release_readback(expected, observed)['status'], 'MATCHED')
        for key in ('account', 'app', 'channel', 'version', 'artifact_sha256'):
            self.assertEqual(release_readback(expected, dict(observed, **{key:'wrong'}))['status'], 'BLOCKED')
        for key in ('readback_reference', 'observed_at', 'availability_reference'):
            with self.assertRaises(ValueError):
                release_readback(expected, dict(observed, **{key: True}))
        with self.assertRaises(ValueError):
            release_readback(expected, dict(observed, observed_at='2026-10-13T12:00:00'))
        for junk in ('line\nbreak', 'x' * 501):
            with self.assertRaises(ValueError):
                release_readback(expected, dict(observed, readback_reference=junk))


if __name__ == '__main__':
    unittest.main()
