import copy
from contextlib import redirect_stdout
import io
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tool import factory


class FactoryChecks(unittest.TestCase):
    def setUp(self):
        original = factory.ROOT
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name in ('contracts/delegation-smoke.json', 'contracts/capabilities.json', 'opencode.json'):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original / name, root / name)
        task = root / '.project-brain/tasks/PB-001.md'
        task.parent.mkdir(parents=True)
        task.write_text('Status: READY\n')
        patched = patch.object(factory, 'ROOT', root)
        patched.start()
        self.addCleanup(patched.stop)
        self.contract = factory.load(factory.ROOT / 'contracts/delegation-smoke.json')

    def test_sensitive_inputs_refused(self):
        for name in ('service-account-prod.json', 'keys/signing.PEM', 'id_ed25519', 'app-ids.env', 'key.properties', 'upload.p12'):
            self.assertTrue(factory.sensitive_path(name))
        self.assertFalse(factory.sensitive_path('lib/feature.dart'))

    def test_snapshot_rejects_resolved_sensitive_target(self):
        target = factory.ROOT / 'service-account-prod.json'
        target.write_text('{"synthetic":true}')
        harmless = factory.ROOT / 'lib/review-source.txt'
        harmless.parent.mkdir()
        # Check the resolved target even on hosts that do not permit symlink creation.
        with patch.object(Path, 'resolve', return_value=target):
            with self.assertRaises(ValueError):
                factory.snapshot_path('lib/review-source.txt')

    def test_contract_complete_and_fail_closed(self):
        factory.validate_contract(self.contract)
        for field in factory.FIELDS:
            bad = copy.deepcopy(self.contract)
            del bad[field]
            with self.assertRaises(ValueError):
                factory.validate_contract(bad)
        for name, value in [('paid_api', True), ('deploy', True)]:
            bad = copy.deepcopy(self.contract)
            bad['permissions'][name] = value
            with self.assertRaises(ValueError):
                factory.validate_contract(bad)
        self.contract['scope'] = ['../credentials']
        with self.assertRaises(ValueError):
            factory.validate_contract(self.contract)
        for field, value in [('task_id', 'PB-999999'), ('dependencies', ['bad']), ('scope', ['C:outside'])]:
            bad = factory.load(factory.ROOT / 'contracts/delegation-smoke.json')
            bad[field] = value
            with self.assertRaises(ValueError):
                factory.validate_contract(bad)

    def test_wrapper_paths_and_worker_permissions_are_fail_closed(self):
        for name in ('../auth.json', 'C:/Users/rubicon/.codex/auth.json', 'contracts/../opencode.json'):
            with self.assertRaises(ValueError):
                factory.trusted_input(name, '.json')
        self.assertEqual(factory.worker_permissions(self.contract)['agent']['factory-worker']['permission']['edit'], {'*': 'deny'})
        self.contract['permissions']['write'] = True
        self.contract['scope'] = ['tool/factory.py']
        with self.assertRaises(ValueError):
            factory.worker_permissions(self.contract)
        self.contract['scope'] = ['lib/feature.dart']
        edits = factory.worker_permissions(self.contract)['agent']['factory-worker']['permission']['edit']
        self.assertEqual(edits['*'], 'deny')
        self.assertEqual(edits['lib/feature.dart'], 'allow')
        self.assertEqual(edits[str(Path('lib/feature.dart'))], 'allow')

    def test_model_router_refuses_paid_before_execution(self):
        with patch.object(factory, 'run') as run:
            with self.assertRaises(ValueError):
                factory.model_run('qwen-paytopay/qwen3.8-max', 'test',
                                  factory.ROOT / 'contracts/delegation-smoke.json')
            run.assert_not_called()

    def test_dispatch_lock_rejects_concurrent_run_and_releases_after_failure(self):
        lock = factory.ROOT / '.factory/dispatch.lock'
        lock.parent.mkdir()
        lock.write_text('synthetic running process')
        with self.assertRaisesRegex(RuntimeError, 'already active'):
            factory.model_run(factory.FREE_MODELS[0], 'test', 'unused')
        lock.unlink()
        with patch.object(factory, '_model_run', side_effect=ValueError('bad input')):
            with self.assertRaises(ValueError):
                factory.model_run(factory.FREE_MODELS[0], 'test', 'unused')
        self.assertFalse(lock.exists())

    def test_inactive_task_and_paid_config_are_rejected(self):
        (factory.ROOT / '.project-brain/tasks/PB-001.md').write_text('Status: DONE\n')
        with self.assertRaisesRegex(ValueError, 'READY or IN_PROGRESS'):
            factory.validate_contract(self.contract)
        cfg = factory.load(factory.ROOT / 'opencode.json')
        cfg['provider']['opencode']['whitelist'].append('paid-model')
        (factory.ROOT / 'opencode.json').write_text(json.dumps(cfg))
        self.assertEqual(factory.audit()['status'], 'REWORK_REQUIRED')

    def test_registry_can_revoke_free_access_or_verified_capability(self):
        path = factory.ROOT / 'contracts/capabilities.json'
        registry = factory.load(path)
        model = registry['models'][factory.FREE_MODELS[0]]
        model['access'] = 'paid'
        path.write_text(json.dumps(registry))
        self.assertEqual(factory.audit()['status'], 'REWORK_REQUIRED')
        with patch.object(factory, 'run') as runner:
            with self.assertRaisesRegex(ValueError, 'no longer approves'):
                factory.model_run(factory.FREE_MODELS[0], 'test', factory.ROOT / 'contracts/delegation-smoke.json')
            runner.assert_not_called()
        model['access'] = 'native_free'
        model['verified'] = []
        path.write_text(json.dumps(registry))
        with patch.object(factory, 'run') as runner:
            with self.assertRaisesRegex(ValueError, 'verified capability'):
                factory.model_run(factory.FREE_MODELS[0], 'test', factory.ROOT / 'contracts/delegation-smoke.json')
            runner.assert_not_called()

    def test_subscription_env_does_not_inherit_api_gateway(self):
        env = factory.clean_ai_env({'PATH': 'ok', 'OPENAI_API_KEY': 'secret',
                                   'ANTHROPIC_BASE_URL': 'paid', 'OPENCODE_CONFIG_CONTENT': '{}'})
        self.assertEqual(env, {'PATH': 'ok'})

    def test_exit_zero_is_not_task_pass(self):
        result = {'exit_code': 0, 'stdout': json.dumps({'type': 'item.completed',
                  'item': {'type': 'agent_message', 'text': '{"status":"BLOCKED"}'}})}
        self.assertEqual(factory.classify(result), 'SUCCESS')
        self.assertEqual(factory.task_result(result)['status'], 'BLOCKED')

    def test_fallback_error_classification_controlled_not_live(self):
        self.assertEqual(factory.classify({'exit_code': 1, 'stderr': 'quota exhausted'}), 'QUOTA_EXHAUSTED')
        self.assertEqual(factory.classify({'exit_code': 124}), 'TIMEOUT')
        self.assertEqual(factory.classify({'exit_code': 0, 'stdout': '{"type":"error","error":"401 authentication"}'}), 'AUTH_ERROR')
        self.assertEqual(factory.classify({'exit_code': 0}), 'SUCCESS')
        self.assertEqual(factory.classify({'exit_code': 1, 'stderr': 'build failed at line 404, fixture 401'}), 'UNKNOWN_FAILURE')
        self.assertEqual(factory.classify({'exit_code': 1, 'stderr': 'HTTP status 429'}), 'RATE_LIMIT')

    def test_controlled_quota_fallback_checkpoints_and_never_uses_paid(self):
        calls = []
        def invoke(model):
            calls.append(model)
            return {'exit_code': 1, 'stderr': 'quota exhausted'} if len(calls) == 1 else {'exit_code': 0}
        result = factory.fallback_run(*factory.FREE_MODELS, invoke, lambda: calls.append('checkpoint'))
        self.assertEqual(result['classification'], 'SUCCESS')
        self.assertEqual(calls, [factory.FREE_MODELS[0], 'checkpoint', factory.FREE_MODELS[1]])
        with self.assertRaises(ValueError):
            factory.fallback_run(factory.FREE_MODELS[0], 'paid/model', invoke, lambda: None)
        def blocked():
            raise RuntimeError('source changed')
        calls.clear()
        result = factory.fallback_run(*factory.FREE_MODELS, invoke, blocked)
        self.assertEqual(len(result['attempts']), 1)
        self.assertEqual(result['classification'], 'BLOCKED')
        with patch.object(factory, 'classify', return_value='AUTH_ERROR'):
            calls.clear()
            result = factory.fallback_run(*factory.FREE_MODELS, invoke, lambda: calls.append('checkpoint'))
            self.assertEqual(len(calls), 1)
        blocked = {'exit_code': 0, 'stdout': json.dumps({'type': 'text', 'part': {'text': '{"status":"BLOCKED"}'}})}
        result = factory.fallback_run(*factory.FREE_MODELS,
                                     lambda _: {'exit_code': 1, 'stderr': 'quota exhausted'} if _ == factory.FREE_MODELS[0] else blocked,
                                     lambda: None)
        self.assertEqual(result['task_result']['status'], 'BLOCKED')

    def test_bootstrap_never_overwrites_existing_or_external_directory(self):
        for destination in (factory.ROOT, factory.ROOT / '../another-app'):
            with self.assertRaises(ValueError):
                factory.bootstrap(destination, 'Demo', 'com.demo.app', 'no', 'no')

    def test_cli_fallback_stops_after_generated_app_source_changes(self):
        subprocess.run(['git', 'init', '-q', str(factory.ROOT)], check=True)
        app = factory.ROOT / '.factory/workspaces/app'
        source = app / 'lib/main.dart'
        source.parent.mkdir(parents=True)
        source.write_text('before')
        subprocess.run(['git', 'init', '-q', str(app)], check=True)
        self.contract['scope'] = ['.factory/workspaces/app/lib/main.dart']
        contract = factory.ROOT / 'contracts/delegation-smoke.json'
        contract.write_text(json.dumps(self.contract))
        prompt = factory.ROOT / 'contracts/prompt.txt'
        prompt.write_text('Synthetic fallback check')
        output = factory.ROOT / '.factory/runs/fallback.json'
        calls = []
        def invoke(provider, *args):
            calls.append(provider)
            source.write_text('partial implementation')
            return {'exit_code': 1, 'stderr': 'quota exhausted'}
        real_run = factory.run
        def runner(argv, **kw):
            return {'exit_code': 0, 'stdout': 'synthetic boot'} if str(factory.BRAIN) in argv else real_run(argv, **kw)
        argv = ['factory', 'run', '--provider', factory.FREE_MODELS[0], '--fallback', factory.FREE_MODELS[1],
                '--contract', str(contract), '--prompt-file', str(prompt), '--output', str(output)]
        with patch('sys.argv', argv), patch.object(factory, 'model_run', side_effect=invoke), \
                patch.object(factory, 'run', side_effect=runner), redirect_stdout(io.StringIO()):
            self.assertEqual(factory.main(), 1)
        self.assertEqual(calls, [factory.FREE_MODELS[0]])
        self.assertEqual(factory.load(output)['classification'], 'BLOCKED')

    def test_evidence_rejects_stale_failed_missing_artifact_and_same_reviewer(self):
        workspaces = factory.ROOT / '.factory/workspaces'
        workspaces.mkdir(parents=True)
        with tempfile.TemporaryDirectory(dir=workspaces) as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', tmp], check=True)
            (root / 'source.txt').write_text('implementation')
            artifact = root / 'build.bin'
            (root / '.gitignore').write_text('build.bin\n.factory/\n')
            artifact.write_bytes(b'real build evidence')
            checks = []
            for name, argv in factory.verification_commands('factory').items():
                log = factory.ROOT / '.factory/runs' / (name + '.json')
                factory.save(log, {'command': argv, 'exit_code': 0, 'stdout': 'test fixture',
                                  'cwd': str(root.resolve()), 'source_digest': factory.source_digest(root)})
                checks.append({'name': name, 'command': argv, 'exit_code': 0,
                               'log': str(log), 'sha256': factory.digest_file(log)})
            evidence = {'task_id': 'PB-001', 'worker_session': 'worker',
                        'profile': 'factory',
                        'contract_sha256': factory.digest_file(factory.ROOT / 'contracts/delegation-smoke.json'),
                        'source_digest': factory.source_digest(root),
                        'checks': checks,
                        'artifacts': [{'path': str(artifact), 'sha256': factory.digest_file(artifact)}]}
            review = {'task_id': 'PB-001', 'worker_session': 'worker', 'reviewer_session': 'ses_reviewer',
                      'contract_sha256': evidence['contract_sha256'],
                      'source_digest': evidence['source_digest'], 'verdict': 'PASS', 'findings': []}
            contract = factory.ROOT / 'contracts/delegation-smoke.json'
            with self.assertRaisesRegex(ValueError, 'must target'):
                factory.evidence_gate(root.parent.parent.parent.parent, evidence, review, contract)
            native = {'info': {'id': 'ses_reviewer', 'agent': 'factory-reviewer', 'parentID': 'ses_supervisor'},
                      'messages': [{'info': {'role': 'assistant'}, 'parts': [{'type': 'text', 'text': json.dumps(review)}]}]}
            real_run = factory.run
            with patch.object(factory, 'run') as native_run:
                native_run.side_effect = lambda argv, **kw: {'exit_code': 0, 'stdout': json.dumps(native)} if 'export' in argv else real_run(argv, **kw)
                self.assertEqual(factory.evidence_gate(root, evidence, review, contract)['status'], 'ACCEPTABLE')
                native['info']['agent'] = 'factory-worker'
                with self.assertRaisesRegex(ValueError, 'independent native reviewer'):
                    factory.evidence_gate(root, evidence, review, contract)
                native['info']['agent'] = 'factory-reviewer'
                native['messages'][0]['parts'][0]['text'] = '{"verdict":"PASS"}'
                with self.assertRaisesRegex(ValueError, 'recorded native reviewer verdict'):
                    factory.evidence_gate(root, evidence, review, contract)
            for field, value in [('reviewer_session', 'worker'), ('verdict', 'REWORK_REQUIRED'), ('task_id', 'PB-002')]:
                bad = dict(review, **{field: value})
                with self.assertRaises(ValueError):
                    factory.evidence_gate(root, evidence, bad, contract)
            failed = dict(evidence, checks=[{'exit_code': 1}])
            with self.assertRaises(ValueError):
                factory.evidence_gate(root, failed, review, contract)
            with self.assertRaises(ValueError):
                factory.evidence_gate(root, dict(evidence, checks=checks[:1]), review, contract)
            artifact.write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                factory.evidence_gate(root, evidence, review, contract)
            (root / 'source.txt').write_text('changed')
            with self.assertRaises(ValueError):
                factory.evidence_gate(root, evidence, review, contract)
            artifact.write_bytes(b'real build evidence')
            evidence['source_digest'] = factory.source_digest(root)
            review['source_digest'] = evidence['source_digest']
            with self.assertRaisesRegex(ValueError, 'another source/workspace'):
                factory.evidence_gate(root, evidence, review, contract)

    def test_check_rejects_source_mutation_even_when_commands_succeed(self):
        subprocess.run(['git', 'init', '-q', str(factory.ROOT)], check=True)
        source = factory.ROOT / 'source.txt'
        source.write_text('before')
        self.contract['verification'] = {'profile': 'factory', 'build': False}
        contract = factory.ROOT / 'contracts/delegation-smoke.json'
        contract.write_text(json.dumps(self.contract))
        real_run = factory.run
        def mutate(argv, **kw):
            if argv[0] == 'git':
                return real_run(argv, **kw)
            source.write_text('after')
            return {'command': argv, 'exit_code': 0, 'stdout': 'synthetic success', 'stderr': ''}
        with patch.object(factory, 'run', side_effect=mutate):
            result = factory.check(factory.ROOT, contract, 'worker', factory.ROOT / '.factory/runs/check.json')
        self.assertEqual(result['status'], 'REWORK_REQUIRED')
        self.assertTrue(all(c['exit_code'] == 0 for c in result['checks']))

    def test_review_cannot_mutate_or_spawn_and_skills_are_scoped(self):
        cfg = factory.load(factory.ROOT / 'opencode.json')
        reviewer = cfg['agent']['factory-reviewer']['permission']
        self.assertEqual(reviewer['*'], 'deny')
        self.assertNotIn('bash', reviewer)
        self.assertNotIn('edit', reviewer)
        self.assertNotIn('task', reviewer)
        self.assertEqual(cfg['enabled_providers'], ['opencode'])
        self.assertEqual(cfg['permission']['skill']['*'], 'deny')


if __name__ == '__main__':
    unittest.main()
