"""Offline regressions: no provider calls, credentials or real user registry."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime import models, plan, accept
from test_plan import READY_TASK


def fixture():
    checked = models.now().isoformat()
    b = dict(name='coding check', version='1', harness='same-agent', effort='high', dimension='coding',
             source='https://benchmark.example/results', checked_at=checked, observed_at=checked,
             reference_model='external-frontier', reference_score=100, h_min=90, m_min=70,
             rationale='Policy: H at 90, M at 70 on this exact cohort; not a quality guarantee', independent=True)
    p = dict(kind='subscription', allowed=True, checked_at=checked, source='native quota tool',
             windows=[dict(remaining=50, resets_at=(models.now() + timedelta(hours=1)).isoformat())])
    a = dict(id='host-a', pool='account', host='test-host', effort='high', allowed=True, available=True,
             checked_at=checked, source='native model catalog', context=200000, tools=['shell'],
             input_price=None, output_price=None)
    r = dict(score=95, source='https://benchmark.example/model-a', checked_at=checked)
    return dict(schema=1, enforce=False, benchmarks={'code': b, 'reason': dict(b, dimension='reasoning')},
                pools={'account': p}, models={'a@high': dict(effort='high', aliases=['a'],
                results={'code': r, 'reason': deepcopy(r)}, accesses=[a])})


class ModelTests(unittest.TestCase):
    def test_quality_floor_external_reference_and_separate_roles(self):
        d = models.validate(fixture())
        self.assertEqual(models.assessment(d, 'a@high', 'plan')['tier'], 'H')
        d['models']['a@high']['results']['code']['score'] = 20
        self.assertEqual(models.assessment(d, 'a@high', 'plan')['tier'], 'L')
        del d['models']['a@high']['results']['reason']
        self.assertEqual(models.assessment(d, 'a@high', 'review')['tier'], 'UNKNOWN')
        self.assertEqual(models.assessment(d, 'a@high', 'implement')['tier'], 'L')

    def test_stale_sources_unknown_effort_and_manufacturer_claims_never_make_h(self):
        for mutate in (lambda d: d['benchmarks']['code'].update(independent=False),
                       lambda d: d['benchmarks']['code'].update(effort='max'),
                       lambda d: d['benchmarks']['code'].update(observed_at=(models.now()-timedelta(days=31)).isoformat()),
                       lambda d: d['models']['a@high']['results']['code'].update(
                           checked_at=(models.now()-timedelta(days=31)).isoformat())):
            d = fixture()
            mutate(d)
            self.assertEqual(models.assessment(d, 'a@high', 'implement')['tier'], 'UNKNOWN')

    def test_select_checks_authority_tools_context_shared_quota_and_price(self):
        d = fixture()
        self.assertIsNotNone(models.select(d, 'plan', 'H', tools=['shell'])['recommended'])
        for mutate in (lambda d: d['pools']['account'].update(allowed=False),
                       lambda d: d['pools']['account'].update(windows=[]),
                       lambda d: d['pools']['account']['windows'].append(dict(remaining=9,
                           resets_at=(models.now()+timedelta(hours=1)).isoformat())),
                       lambda d: d['pools']['account'].update(checked_at=(models.now()-timedelta(minutes=6)).isoformat()),
                       lambda d: d['models']['a@high']['accesses'][0].update(available=False),
                       lambda d: d['pools']['account'].update(kind='free_api')):
            sample = deepcopy(d)
            mutate(sample)
            self.assertEqual(models.select(sample, 'plan', 'H')['status'], 'BLOCKED')
        self.assertEqual(models.select(d, 'plan', 'H', context=200001)['status'], 'BLOCKED')
        self.assertEqual(models.select(d, 'plan', 'H', tools=['browser'])['status'], 'BLOCKED')
        d['pools']['account']['kind'] = 'free_api'
        d['models']['a@high']['accesses'][0].update(input_price=0, output_price=0)
        self.assertEqual(models.select(d, 'plan', 'H')['status'], 'AVAILABLE')

    def test_only_complete_comparable_observations_rank_cost_and_unknown_stays_null(self):
        d = fixture()
        a = d['models']['a@high']['accesses'][0]
        a['metrics'] = dict(task_class='bugfix', samples=3, complete=True, checked_at=models.now().isoformat(),
                            source='native complete task counters including retries',
                            tokens_per_accepted=2000, usd_per_accepted=None)
        self.assertEqual(models.select(d, 'implement', 'M', 'bugfix')['recommended']['cost_per_accepted'], 2000)
        self.assertIsNone(models.select(d, 'implement', 'M', 'other')['recommended']['cost_per_accepted'])
        a['metrics']['complete'] = False
        self.assertIsNone(models.select(d, 'implement', 'M', 'bugfix')['recommended']['cost_per_accepted'])

    def test_corrupt_input_refused_and_failed_merge_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'models.json'
            _, rev = models.load(path)
            d = fixture()
            patch = {k: v for k, v in d.items() if k != 'schema'}
            _, rev = models.merge(path, patch, rev)
            before = path.read_bytes()
            for patch in ({'models': {'bad': {}}}, {'enforce': 'yes'}, {'pools': []},
                          {'benchmarks': {'bad': dict(d['benchmarks']['code'], h_min=float('nan'))}}):
                with self.assertRaises(ValueError):
                    models.merge(path, patch, rev)
                self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(ValueError):
                models.merge(path, {'enforce': True}, 'old-revision')
            changed, _ = models.merge(path, {'enforce': True}, rev)
            self.assertIn('a@high', changed['models'])
            self.assertTrue(changed['enforce'])

    def test_aliases_future_dates_credentials_and_effort_mismatch_are_refused(self):
        for mutate in (lambda d: d['models']['a@high'].update(aliases=['A@HIGH']),
                       lambda d: d['benchmarks']['code'].update(checked_at='2999-01-01T00:00:00Z'),
                       lambda d: d['benchmarks']['code'].update(source='https://secret@example.com'),
                       lambda d: d['models']['a@high']['accesses'][0].update(effort='low'),
                       lambda d: d['models']['a@high'].update(overrides=[]),
                       lambda d: d['models']['a@high'].update(aliases=[123]),
                       lambda d: d['models']['a@high'].update(aliases=[' a ']),
                       lambda d: d['pools']['account']['windows'][0].update(resets_at=None),
                       lambda d: d['benchmarks']['code'].update(h_min=10**1000)):
            d = fixture()
            mutate(d)
            with self.assertRaises(ValueError):
                models.validate(d)

    def test_empty_existing_registry_duplicate_keys_and_linked_temp_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'models.json'
            path.touch()
            with self.assertRaises(ValueError):
                models.load(path)
            with self.assertRaises(ValueError):
                models.parse('{"enforce":true,"enforce":false}')
            with self.assertRaises(ValueError):
                models.validate(models.parse('[' * 1100 + '0' + ']' * 1100))
            path.unlink()
            target = Path(tmp)/'preserve.txt'
            target.write_text('user data')
            try:
                path.with_name(path.name+'.tmp').symlink_to(target)
            except OSError:
                return  # Windows without symlink privilege: linked project paths have their own test.
            with self.assertRaises(ValueError):
                models.merge(path, {'enforce': True}, models.load(path)[1])
            self.assertEqual(target.read_text(), 'user data')

    def test_failure_backoff_and_user_override_are_visible(self):
        d = fixture()
        d['models']['a@high']['results'] = {}
        model = d['models']['a@high']
        model['research'] = dict(error='source unavailable', retry_after=(models.now()+timedelta(days=1)).isoformat())
        self.assertEqual(models.report(d, 'rev')['research_deferred'], ['a@high'])
        model['overrides'] = dict(plan=dict(tier='H', reason='explicit user decision', checked_at=models.now().isoformat()))
        self.assertEqual(models.assessment(d, 'a@high', 'plan')['basis'], 'user_override')
        d['enforce'] = True
        models.require(d, 'A', 'plan')
        with self.assertRaises(ValueError):
            models.require(d, 'a', 'review')

    def test_shared_runtime_gates_start_review_and_accept_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan.init(root)
            path = root / '.store-automation/tasks/SA-001.md'
            path.write_text(READY_TASK.format(id='SA-001').replace('Risk: LOW', 'Risk: MEDIUM') +
                            '- ready by a:high: contract and risk checked\n', encoding='utf-8')
            registry = root / 'models.json'
            d = fixture()
            d['enforce'] = True
            d['models']['a@high']['aliases'].append('a:high')
            registry.write_text(json.dumps(d), encoding='utf-8')
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                plan.start(root, 'SA-001', 'unlisted', models_path=registry)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(plan.start(root, 'SA-001', 'a:high', models_path=registry)[0], 0)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                accept.review(root, 'SA-001', 'a', 'PASS', models_path=registry)
            with self.assertRaises(ValueError):
                accept.review(root, 'SA-001', 'unlisted', 'PASS', models_path=registry)
            self.assertEqual(path.read_bytes(), before)
            task = plan.find_task(root, 'SA-001')
            task['review'] = ['- review by unlisted | PASS | digest='+'0'*16+' | contract='+'0'*16]
            with self.assertRaises(ValueError):
                models.gate(task, 'a', 'accept', registry)

    def test_cli_offline_first_use_merge_select_and_boot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / 'user/models.json'
            cmd = [sys.executable, str(Path(__file__).resolve().parents[1]/'store.py'),
                   '--project', str(root), '--models-file', str(registry)]
            def call(*args):
                return subprocess.run([*cmd, *args], capture_output=True, encoding='utf-8')
            result = json.loads(call('models', 'list').stdout)
            self.assertFalse(registry.exists())
            d = fixture()
            (root/'patch.json').write_text(json.dumps({k:v for k,v in d.items() if k != 'schema'}))
            self.assertEqual(call('models', 'merge', '--file', 'patch.json', '--revision', result['revision']).returncode, 0)
            selected = call('models', 'select', '--role', 'plan', '--tier', 'H')
            self.assertEqual(json.loads(selected.stdout)['status'], 'AVAILABLE')
            self.assertIn('MODELS: 1 registered', call('boot').stdout)
            self.assertEqual(call('models', 'merge', '--file', '../private.json', '--revision', 'old').returncode, 2)
            registry.write_text('{bad')
            self.assertIn('MODELS ERROR:', call('boot').stdout)
            self.assertEqual(call('models', 'list').returncode, 2)


if __name__ == '__main__':
    unittest.main()
