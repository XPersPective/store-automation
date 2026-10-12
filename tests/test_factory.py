import copy
from datetime import datetime, timezone
from contextlib import redirect_stdout
import io
import json
import os
import runpy
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tool import factory


class FactoryChecks(unittest.TestCase):
    def setUp(self):
        original = factory.BUNDLE
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name in ('contracts/delegation-smoke.json', 'contracts/capabilities.json', 'opencode.json'):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original / name, root / name)
        for directory in ('prompts', 'skills'):
            shutil.copytree(original / '.opencode' / directory, root / '.opencode' / directory)
        task = root / '.project-brain/tasks/PB-001.md'
        task.parent.mkdir(parents=True)
        task.write_text('Status: READY\n')
        patched = patch.object(factory, 'ROOT', root)
        patched.start()
        self.addCleanup(patched.stop)
        bundled = patch.object(factory, 'BUNDLE', root)
        bundled.start()
        self.addCleanup(bundled.stop)
        self.contract = factory.load(factory.ROOT / 'contracts/delegation-smoke.json')
        boot = patch.object(factory, 'brain_run', return_value={'exit_code': 0, 'stdout': 'synthetic verified boot'})
        boot.start()
        self.addCleanup(boot.stop)
        admit = factory.authority.admit
        isolated = patch.object(factory.authority, 'admit',
            side_effect=lambda selected, project, attempt: admit(selected, project, attempt, root / 'admission'))
        isolated.start()
        self.addCleanup(isolated.stop)

    def test_sensitive_inputs_refused(self):
        for name in ('service-account-prod.json', 'keys/signing.PEM', 'id_ed25519', 'app-ids.env', 'key.properties', 'upload.p12'):
            self.assertTrue(factory.sensitive_path(name))
        self.assertFalse(factory.sensitive_path('lib/feature.dart'))

    def test_failed_brain_boot_blocks_inference_before_catalogue(self):
        with patch.object(factory, 'brain_run', return_value={'exit_code': 1}), \
             patch.object(factory, 'startup_inventory') as catalogue, patch.object(factory, 'run') as inference:
            with self.assertRaisesRegex(RuntimeError, 'Brain boot failed'):
                factory._model_run('codex', 'Read only', factory.ROOT / 'contracts/delegation-smoke.json')
        catalogue.assert_not_called()
        inference.assert_not_called()

    def test_context_ranges_and_actual_snapshot_budget_before_inference(self):
        self.contract['complexity'] = 'SIMPLE'
        self.contract['delegation'].update(provider='codex', model='auto', effort='auto', context_budget_chars=9000)
        self.contract['context'] = ['lib/demo.txt']
        self.contract['context_ranges'] = {'lib/demo.txt': [1, 1]}
        source = factory.ROOT / 'lib/demo.txt'
        source.parent.mkdir()
        source.write_text('included\n' + 'omitted' * 9000)
        contract = factory.ROOT / 'contracts/ranged.json'
        contract.write_text(json.dumps(self.contract))
        snapshot = {'captured_at': datetime.now(timezone.utc).isoformat(), 'providers': [{
            'cli': 'codex', 'auth': 'SUBSCRIPTION_LOGIN', 'access': 'METADATA_VERIFIED',
            'billing': 'SUBSCRIPTION_ONLY_REQUIRED',
            'models': [{'id': 'gpt-5.6-luna', 'supported_efforts': ['low']}],
            'quota_groups': [{'name': 'Codex Models', 'buckets': [{'remaining_fraction': .8}]}]}]}
        with patch.object(factory, 'executable', return_value='codex'), \
             patch.object(factory, 'run', return_value={'exit_code': 0, 'stdout': 'ChatGPT', 'stderr': ''}), \
             patch.object(factory, 'startup_inventory', return_value=(snapshot, Path('inventory.json'))), \
             patch.object(factory.sessions, 'stream_run', return_value={}) as inference:
            factory._model_run('codex', 'Read snapshot', contract)
            payload = inference.call_args.kwargs['input_text']
            self.assertIn('included', payload)
            self.assertNotIn('omitted', payload)
            self.assertLessEqual(len(payload), 9000)
            inference.reset_mock()
            del self.contract['context_ranges']
            contract.write_text(json.dumps(self.contract))
            with self.assertRaisesRegex(ValueError, 'Actual snapshot input exceeds'):
                factory._model_run('codex', 'Read snapshot', contract)
            inference.assert_not_called()
        for bounds in ([0, 1], [True, 1], [2, 1], [1], '1:2'):
            self.contract['context_ranges'] = {'lib/demo.txt': bounds}
            with self.assertRaisesRegex(ValueError, 'Context ranges'):
                factory.validate_contract(self.contract)

    def test_windows_platform_reaches_bootstrap_instead_of_android_default(self):
        argv = ['factory', 'bootstrap', 'new-app', '--name', 'Example', '--package', 'com.example.app', '--platform', 'windows']
        with patch.object(sys, 'argv', argv), patch.object(factory, 'bootstrap', return_value={'status': 'VERIFIED_LOCAL'}) as bootstrap, redirect_stdout(io.StringIO()):
            self.assertEqual(factory.main(), 0)
        self.assertEqual(bootstrap.call_args.args[-1], ('windows',))

    def test_retired_agent_ui_commands_are_not_available(self):
        for command in ('console', 'native'):
            with patch.object(sys, 'argv', ['factory', command]), patch.object(factory.subprocess, 'call') as launch:
                with self.assertRaises(SystemExit) as result:
                    factory.main()
                self.assertEqual(result.exception.code, 2)
                launch.assert_not_called()

    def test_containment_failure_preserves_dispatch_lock(self):
        with patch.object(factory, '_model_run', side_effect=factory.sessions.ContainmentError('synthetic failure')):
            with self.assertRaises(factory.sessions.ContainmentError):
                factory.model_run(factory.FREE_MODELS[0], 'test', 'unused')
        self.assertTrue((factory.ROOT / '.factory/dispatch.lock').is_file())
        with self.assertRaisesRegex(RuntimeError, 'Dispatch already active'):
            factory.model_run(factory.FREE_MODELS[0], 'test', 'unused')

    def test_source_digest_refuses_credentials_before_hashing_contents(self):
        subprocess.run(['git', 'init', '-q', str(factory.ROOT)], check=True)
        private = factory.ROOT / 'service-account-prod.json'
        private.write_text('synthetic fixture only')
        real_digest = factory.digest_file
        def digest(path):
            self.assertNotEqual(Path(path), private, 'Credential contents must never be hashed/read')
            return real_digest(path)
        with patch.object(factory, 'digest_file', side_effect=digest):
            with self.assertRaisesRegex(ValueError, 'Credential path'):
                factory.source_digest(factory.ROOT)

    def test_source_digest_rejects_resolved_links_before_reading(self):
        subprocess.run(['git', 'init', '-q', str(factory.ROOT)], check=True)
        harmless = factory.ROOT / 'public.txt'
        harmless.write_text('synthetic fixture')
        resolve = Path.resolve
        def resolved(path, *args, **kwargs):
            return factory.ROOT / 'credentials.json' if path == harmless else resolve(path, *args, **kwargs)
        digest = factory.digest_file
        def checked_digest(path):
            self.assertNotEqual(path, harmless)
            return digest(path)
        with patch.object(Path, 'resolve', resolved), patch.object(factory, 'digest_file', side_effect=checked_digest):
            with self.assertRaisesRegex(ValueError, 'Linked source'):
                factory.source_digest(factory.ROOT)

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
        for field in factory.subscriptions.REPORT_FIELDS:
            bad = copy.deepcopy(self.contract)
            bad['delegation']['report_fields'].remove(field)
            with self.assertRaisesRegex(ValueError, 'Mandatory worker return report'):
                factory.validate_contract(bad)
        bad = copy.deepcopy(self.contract)
        bad['delegation']['report_fields'].append({})
        with self.assertRaisesRegex(ValueError, 'Mandatory worker return report'):
            factory.validate_contract(bad)
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
        for field in ('role', 'objective', 'quality_standard'):
            bad = copy.deepcopy(self.contract)
            bad['persona'][field] = '   '
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
        model['verified'] = list(model['capabilities'])  # Synthetic capability fixture, independent of live availability.
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

    def test_actual_report_requires_identity_and_projects_only_public_fields(self):
        report = dict(task=self.contract['task_id'], role='auditor', provider='codex', model='gpt-5.6-luna',
                      effort='low', state='COMPLETED', changed_files=[], evidence=['source read'],
                      usage=None, blockers=[], next_action='Supervisor checks', private_extra='discard')
        def result(value):
            return {'stdout': json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps(value)}})}
        checked = factory.task_result(result(report), self.contract)
        self.assertEqual(checked['state'], 'COMPLETED')
        self.assertNotIn('private_extra', checked)
        for invalid in ({'status': 'PASS'}, dict(report, task='PB-999'), dict(report, usage={'input': True})):
            self.assertEqual(factory.task_result(result(invalid), self.contract)['status'], 'UNVERIFIED')
        self.assertEqual(factory.task_result(result({'verdict': 'PASS'}))['verdict'], 'PASS')

    def test_startup_scans_before_inference_and_reserve_prevents_launch(self):
        snapshot = {'schema_version': 1, 'captured_at': datetime.now(timezone.utc).isoformat(), 'providers': [{
            'cli': 'codex', 'auth': 'SUBSCRIPTION_LOGIN', 'access': 'METADATA_VERIFIED',
            'billing': 'SUBSCRIPTION_ONLY_REQUIRED', 'models': [{'id': 'gpt-5.6-sol', 'supported_efforts': ['high']}],
            'quota_groups': [{'name': 'Codex Models', 'buckets': [{'remaining_fraction': .8}]}]}]}
        seen = []
        def scan(*args, **kwargs):
            seen.append('scan')
            return snapshot
        def launch(argv, **kwargs):
            seen.append('launch')
            self.assertEqual(seen, ['scan', 'launch'])
            self.assertEqual(argv[argv.index('--model') + 1], 'gpt-5.6-sol')
            self.assertIn('model_reasoning_effort="high"', argv)
            self.assertTrue(list((factory.ROOT / '.factory/runs').glob('inventory-*.json')))
            return 0
        argv = ['factory', 'start', '--host', 'codex', 'Audit']
        with patch.object(sys, 'argv', argv), patch.object(factory, 'adopt', return_value={'status': 'PROJECT_LOADED'}), \
                patch.object(factory.subscriptions, 'inventory', side_effect=scan), \
                patch.object(factory, 'executable', return_value='codex'), \
                patch.object(factory.subprocess, 'call', side_effect=launch) as launched, redirect_stdout(io.StringIO()):
            self.assertEqual(factory.main(), 0)
            snapshot['providers'][0]['quota_groups'][0]['buckets'][0]['remaining_fraction'] = .10
            self.assertEqual(factory.main(), 1)
            self.assertEqual(launched.call_count, 1)

    def test_blocked_report_state_fails_even_with_successful_transport(self):
        contract = factory.ROOT / 'contracts/delegation-smoke.json'
        prompt = factory.ROOT / 'contracts/report.txt'
        prompt.write_text('Report only')
        report = dict(task=self.contract['task_id'], role='auditor', provider='codex', model='gpt-5.6-sol',
                      effort='high', state='BLOCKED', changed_files=[], evidence=[], usage=None,
                      blockers=['Missing evidence'], next_action='Wait')
        output = factory.ROOT / '.factory/runs/report.json'
        native = {'exit_code': 0, 'stdout': json.dumps({'type': 'text', 'part': {'text': json.dumps(report)}})}
        argv = ['factory', 'run', '--provider', 'codex', '--contract', str(contract),
                '--prompt-file', str(prompt), '--output', str(output), '--json']
        with patch.object(sys, 'argv', argv), patch.object(factory, 'model_run', return_value=native), redirect_stdout(io.StringIO()):
            self.assertEqual(factory.main(), 1)
        self.assertEqual(json.loads(output.read_text())['task_result']['state'], 'BLOCKED')
        report['state'] = 'COMPLETED'
        native['stdout'] = json.dumps({'type': 'text', 'part': {'text': json.dumps(report)}})
        native['selected'] = {'provider': 'codex', 'model': 'gpt-5.6-luna', 'effort': 'low'}
        output = factory.ROOT / '.factory/runs/wrong-route.json'
        argv[argv.index('--output') + 1] = str(output)
        argv.extend(['--fallback', factory.FREE_MODELS[1]])
        with patch.object(sys, 'argv', argv), patch.object(factory, 'source_digest', return_value='unchanged'), patch.object(factory, 'fallback_run', return_value={
                'classification': 'SUCCESS', 'attempts': [native]}), redirect_stdout(io.StringIO()):
            self.assertEqual(factory.main(), 1)
        self.assertEqual(json.loads(output.read_text())['task_result']['status'], 'UNVERIFIED')

    def test_free_dispatch_preserves_explicit_model_and_effort(self):
        contract = factory.ROOT / 'contracts/delegation-smoke.json'
        for field, value in (('model', 'different-model'), ('effort', 'high')):
            task = factory.load(contract)
            task['delegation'][field] = value
            registry = {'models': {factory.FREE_MODELS[0]: {'verified': task['required_capabilities'], 'access': 'native_free'}}}
            with patch.object(factory, 'load', side_effect=lambda path: task if path == contract else registry), \
                    patch.object(factory, 'brain_run') as boot:
                with self.assertRaisesRegex(ValueError, 'conflicts with delegation'):
                    factory._model_run(factory.FREE_MODELS[0], 'test', contract)
                boot.assert_not_called()

    def test_fallback_error_classification_controlled_not_live(self):
        self.assertEqual(factory.classify({'exit_code': 1, 'stderr': 'quota exhausted'}), 'QUOTA_EXHAUSTED')
        self.assertEqual(factory.classify({'exit_code': 124}), 'TIMEOUT')
        self.assertEqual(factory.classify({'exit_code': 0, 'stdout': '{"type":"error","error":"401 authentication"}'}), 'AUTH_ERROR')
        self.assertEqual(factory.classify({'exit_code': 0}), 'SUCCESS')
        self.assertEqual(factory.classify({'exit_code': 1, 'stderr': 'build failed at line 404, fixture 401'}), 'UNKNOWN_FAILURE')
        self.assertEqual(factory.classify({'exit_code': 1, 'stderr': 'HTTP status 429'}), 'RATE_LIMIT')
        restricted = {'exit_code': 0, 'stdout': json.dumps({
            'type': 'error', 'error': {'message': 'The free tier can only be used from within OpenCode. HTTP status 429'}})}
        self.assertEqual(factory.classify(restricted), 'ACCESS_RESTRICTED')
        calls = []
        def invoke(model):
            calls.append(model)
            return restricted
        result = factory.fallback_run(*factory.FREE_MODELS, invoke,
                                      lambda: self.fail('Access restriction must not trigger a checkpoint or fallback'))
        self.assertEqual(result['classification'], 'ACCESS_RESTRICTED')
        self.assertEqual(calls, [factory.FREE_MODELS[0]])
        for language, expected in [('tr', 'Sağlayıcı erişimi kısıtlı'), ('en', 'Provider access restricted')]:
            text = factory.sessions.format_public(result, language)
            self.assertIn(expected, text)
            self.assertNotIn('free tier can only', text)

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

    def test_bootstrap_never_overwrites_existing_directory(self):
        for destination in (factory.ROOT, factory.ROOT / 'contracts'):
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
        def invoke(provider, *args, **kwargs):
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


class PortableSkillChecks(unittest.TestCase):
    def test_rebaseline_preview_archive_and_failed_initialization_preserve_plan(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(factory, 'ROOT', Path(tmp).resolve()):
            root = factory.ROOT
            self.assertEqual(factory.adopt()['status'], 'PROJECT_LOADED')
            marker = root / '.project-brain/tasks/PB-901.md'
            marker.write_text('Status: READY\nOld project task\n')
            (root / 'app.txt').write_text('preserve user source')
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(factory.rebaseline()['status'], 'REBASELINE_PREVIEW')
            self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()})
            with patch('pathlib.Path.rename', side_effect=OSError('transient archive failure')) as rename:
                with self.assertRaisesRegex(OSError, 'transient archive'):
                    factory.rebaseline(True)
                self.assertEqual(rename.call_count, 1, 'Rollback must not attempt to rename the original Brain')
            self.assertTrue(marker.exists(), 'A failed initial archive must not move the original Brain during rollback')
            with patch.object(factory, 'adopt', return_value={'status': 'BLOCKED'}):
                with self.assertRaisesRegex(RuntimeError, 'initialization failed'):
                    factory.rebaseline(True)
            self.assertEqual(marker.read_text(), 'Status: READY\nOld project task\n')
            result = factory.rebaseline(True)
            self.assertEqual(result['status'], 'REBASELINE_AUDIT_REQUIRED')
            self.assertEqual((Path(result['archive']) / '.project-brain/tasks/PB-901.md').read_bytes(), before['.project-brain/tasks/PB-901.md'])
            self.assertFalse(marker.exists())
            self.assertIn('Status: DRAFT', (root / '.project-brain/target.md').read_text())
            self.assertEqual((root / 'app.txt').read_text(), 'preserve user source')

    def test_rebaseline_refuses_linked_archive_directory(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(factory, 'ROOT', Path(tmp).resolve()):
            root = factory.ROOT
            factory.adopt()
            outside = root / 'outside'
            outside.mkdir()
            (root / '.factory').mkdir()
            try:
                (root / '.factory/brain-backups').symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('Host does not allow symlink creation')
            with self.assertRaisesRegex(ValueError, 'destination'):
                factory.rebaseline(True)
            self.assertTrue((root / '.project-brain/target.md').is_file())
            self.assertEqual(list(outside.iterdir()), [])

    def test_linked_manifest_and_adoption_pointer_preserve_external_files(self):
        installer = runpy.run_path(str(factory.BUNDLE / 'tool/install-skill.py'))
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            outside = base / 'outside.json'
            outside.write_text('{}')
            skill, app, binary = base / 'skill', base / 'app', base / 'bin'
            for path in (skill, app, binary):
                path.mkdir()
            links = [skill / '.install-manifest.json', app / 'AGENTS.md', binary / '.store-automation-launcher.json']
            try:
                for link in links:
                    link.symlink_to(outside)
            except OSError:
                self.skipTest('Host does not allow symlink creation')
            with self.assertRaisesRegex(ValueError, 'manifest'):
                installer['install']([skill])
            with patch.object(factory, 'ROOT', app):
                with self.assertRaisesRegex(ValueError, 'instruction'):
                    factory.adopt()
            with self.assertRaisesRegex(ValueError, 'manifest'):
                installer['install_launcher'](skill, binary)
            self.assertEqual(outside.read_text(), '{}')
            self.assertFalse((app / '.project-brain').exists())

    def test_resume_requires_exact_project_contract_and_finished_provenance(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(factory, 'ROOT', Path(tmp).resolve()):
            root = factory.ROOT
            contract = root / 'contracts/task.json'
            contract.parent.mkdir()
            contract.write_text('{}')
            record = root / '.factory/runs/live-test.json'
            record.parent.mkdir(parents=True)
            data = {'project': str(root), 'contract_sha256': factory.digest_file(contract),
                    'native_sessions': ['ses_owned'], 'state': 'FINISHED'}
            record.write_text(json.dumps(data))
            factory.validate_resume('ses_owned', contract)
            for key, value in [('project', str(root.parent)), ('contract_sha256', 'wrong'),
                               ('native_sessions', ['ses_elsewhere']), ('state', 'RUNNING')]:
                record.write_text(json.dumps(dict(data, **{key: value})))
                with self.assertRaisesRegex(ValueError, 'provenance'):
                    factory.validate_resume('ses_owned', contract)

    def test_adoption_preserves_existing_project_and_does_not_import_tasks(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(factory, 'ROOT', Path(tmp).resolve()):
            root = factory.ROOT
            (root / 'README.md').write_text('Existing user project goal\n')
            result = factory.adopt()
            self.assertEqual(result['status'], 'PROJECT_LOADED', result)
            self.assertEqual((root / 'README.md').read_text(), 'Existing user project goal\n')
            self.assertTrue((root / '.project-brain/target.md').is_file())
            self.assertIn('Status: DRAFT', (root / '.project-brain/target.md').read_text())
            self.assertEqual(list((root / '.project-brain/tasks').glob('PB-*.md')), [])
            self.assertFalse((root / '.git').exists())
            factory.adopt()
            self.assertEqual((root / '.gitignore').read_text().count('.factory/'), 1)

    def test_legacy_adoption_preserves_plan_and_hands_migration_to_supervisor(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(factory, 'ROOT', Path(tmp).resolve()):
            legacy = factory.ROOT / 'PROJECT_BRAIN.md'
            original = '# Project Brain\n\n## Goal\nPreserve the existing product.\n'
            legacy.write_text(original)
            result = factory.adopt()
            self.assertEqual(result['status'], 'MIGRATION_REVIEW_REQUIRED')
            self.assertEqual(result['preview']['exit_code'], 0, result)
            self.assertEqual(legacy.read_text(), original)
            self.assertFalse((factory.ROOT / '.project-brain').exists())

    def test_launcher_preserves_cwd_and_rejects_local_modification(self):
        installer = runpy.run_path(str(factory.BUNDLE / 'tool/install-skill.py'))
        with tempfile.TemporaryDirectory(prefix='launcher space ') as tmp:
            base = Path(tmp)
            skill = base / 'installed skill'
            installer['install']([skill])
            launcher = Path(installer['install_launcher'](skill, base / 'bin'))
            app = base / 'existing app'
            app.mkdir()
            # Windows cmd quoting is exercised by an actual launcher, not a string assertion.
            command = [str(launcher), 'adopt']
            result = subprocess.run(command, cwd=app, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['project_root'], str(app.resolve()))
            self.assertFalse((skill / '.project-brain').exists())
            launcher.write_text('user change')
            with self.assertRaisesRegex(ValueError, 'modified/unowned launcher'):
                installer['install_launcher'](skill, base / 'bin')

    def test_installed_cli_uses_each_projects_brain_without_checkout(self):
        installer = runpy.run_path(str(factory.BUNDLE / 'tool/install-skill.py'))
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skill = base / 'skill'
            installer['install']([skill])
            cli = skill / 'runtime/tool/factory.py'
            for name, task_id in [('first', 'PB-101'), ('second', 'PB-202')]:
                app = base / name
                task = app / '.project-brain/tasks' / (task_id + '.md')
                task.parent.mkdir(parents=True)
                task.write_text('Status: READY\n')
                (app / 'contracts').mkdir()
                contract = factory.load(factory.BUNDLE / 'contracts/delegation-smoke.json')
                contract['task_id'] = task_id
                path = app / 'contracts/task.json'
                path.write_text(json.dumps(contract))
                result = subprocess.run([sys.executable, str(cli), 'contract', str(path)], cwd=app, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                audit = subprocess.run([sys.executable, str(cli), 'audit'], cwd=app, capture_output=True, text=True)
                self.assertEqual(json.loads(audit.stdout)['project_root'], str(app.resolve()))
            cross = subprocess.run([sys.executable, str(cli), 'contract', str(base / 'first/contracts/task.json')],
                                   cwd=base / 'second', capture_output=True)
            self.assertNotEqual(cross.returncode, 0)
            contract['task_id'] = 'PB-101'
            path.write_text(json.dumps(contract))
            wrong_id = subprocess.run([sys.executable, str(cli), 'contract', str(path)], cwd=path.parents[1], capture_output=True)
            self.assertNotEqual(wrong_id.returncode, 0)
            # No source-checkout paths are present in the installed execution arguments.
            self.assertNotIn(str(factory.BUNDLE), str(cli))
            (skill / 'runtime/tool/factory.py').write_text('user edit')
            with self.assertRaisesRegex(ValueError, 'Preserve modified'):
                installer['install']([skill])

    def test_bootstrap_separate_project_gets_fresh_brain(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            starter = base / 'starter'
            inherited = starter / '.project-brain/tasks/PB-999.md'
            inherited.parent.mkdir(parents=True)
            inherited.write_text('template task must not leak')
            (starter / 'PROJECT_BRAIN.md').write_text('template legacy plan')
            (starter / 'source.txt').write_text('preserved template source')
            subprocess.run(['git', 'init', '-q', str(starter)], check=True)
            subprocess.run(['git', 'add', '.'], cwd=starter, check=True)
            subprocess.run(['git', '-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
                            'commit', '-qm', 'synthetic starter'], cwd=starter, check=True)
            app = base / 'independent-app'
            real_run = factory.run
            def runner(argv, **kw):
                if 'tool/new_app.dart' in argv:
                    self.assertEqual(argv[argv.index('--platforms') + 1], 'windows')
                    self.assertEqual(argv[argv.index('--pro') + 1], 'monthly')
                    self.assertEqual(argv[argv.index('--data') + 1], 'cloud')
                    self.assertEqual(argv[argv.index('--banner') + 1], 'no')
                    self.assertEqual(argv[argv.index('--rewarded') + 1], 'yes')
                    (app / 'PROJECT_BRAIN.md').write_text('newly generated app notes')
                    return {'exit_code': 0, 'stdout': 'synthetic generator success'}
                return real_run(argv, **kw)
            with patch.object(factory, 'STARTER', starter), patch.object(factory, 'KIT', starter), \
                    patch.object(factory, 'executable', return_value=sys.executable), patch.object(factory, 'run', side_effect=runner):
                result = factory.bootstrap(app, 'Demo', 'com.example.demo', 'yes', 'monthly', ('windows',),
                                           data='cloud', banner='no', rewarded='yes', app_open='no')
            self.assertEqual(result['status'], 'VERIFIED_LOCAL')
            self.assertTrue((app / '.git').is_dir())
            self.assertTrue((app / '.project-brain/target.md').is_file())
            self.assertIn('Status: DRAFT', (app / '.project-brain/target.md').read_text())
            self.assertFalse((app / '.project-brain/tasks/PB-999.md').exists())
            self.assertFalse((app / 'PROJECT_BRAIN.md').exists())
            self.assertEqual(result['generated_legacy_brain'], 'newly generated app notes')
            self.assertIn('flutter test', (app / '.project-brain/config.yaml').read_text())
            self.assertIn('flutter build windows --release', (app / '.project-brain/config.yaml').read_text())
            self.assertEqual((app / 'source.txt').read_text(), 'preserved template source')
            with self.assertRaises(ValueError):
                factory.bootstrap(app, 'Demo', 'com.example.demo', 'no', 'no')

    def test_native_config_and_subprocess_cwd_are_project_scoped(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(factory, 'ROOT', Path(tmp)):
            result = factory.run([sys.executable, '-c', 'import os; print(os.getcwd())'])
            self.assertEqual(Path(result['stdout'].strip()).resolve(), Path(tmp).resolve())
            cfg = json.loads(factory.native_env()['OPENCODE_CONFIG_CONTENT'])
            self.assertIn('store-automation', cfg['permission']['skill'])
            self.assertNotIn('{file:', cfg['agent']['factory']['prompt'])
            cfg = json.loads(factory.native_env({'agent': {'factory': {'permission': {'bash': 'deny'}}}})['OPENCODE_CONFIG_CONTENT'])
            self.assertEqual(cfg['agent']['factory']['permission']['bash'], 'deny')
            self.assertEqual(cfg['agent']['factory-reviewer']['permission']['*'], 'deny')
            with self.assertRaisesRegex(ValueError, 'only for the tool source'):
                factory.verification_commands('factory')

    def test_linked_project_state_cannot_borrow_another_projects_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            other = base / 'other'
            other.mkdir()
            (other / 'task.json').write_text('{}')
            (other / 'PB-001.md').write_text('Status: READY\n')
            for index, relative in enumerate(('contracts', '.factory', '.project-brain', '.project-brain/tasks')):
                app = base / str(index)
                app.mkdir()
                link = app / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                if os.name == 'nt':
                    subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(other)],
                                   check=True, capture_output=True)
                else:
                    link.symlink_to(other, target_is_directory=True)
                with patch.object(factory, 'ROOT', app):
                    with self.assertRaisesRegex(ValueError, 'escapes the selected project'):
                        factory.project_dir(relative)
                    if relative == 'contracts':
                        with self.assertRaises(ValueError):
                            factory.trusted_input(link / 'task.json', '.json')
                    if relative.startswith('.project-brain'):
                        with patch('sys.argv', ['factory', 'brain', 'new', '.', 'Synthetic task']):
                            with self.assertRaises(ValueError):
                                factory.main()
                        self.assertEqual(sorted(p.name for p in other.iterdir()), ['PB-001.md', 'task.json'])


if __name__ == '__main__':
    unittest.main()
