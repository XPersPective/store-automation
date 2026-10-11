"""Read official CLI metadata, select a sufficient model, and account for reported usage."""
from datetime import datetime, timezone
import math
import re
import shutil


LOGIN = {'agy': 'agy (official account setup)', 'claude': 'claude auth login',
         'codex': 'codex login', 'gemini': 'gemini (Login with Google)',
         'mcode': 'mcode login --region global', 'opencode': 'opencode auth login'}
RESERVE = 0.10


def number(value, maximum=None):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 and (maximum is None or value <= maximum) else None


def agy_groups(payload):
    if not isinstance(payload, dict):
        return []
    command = payload.get('command', {}) if isinstance(payload, dict) else {}
    if not isinstance(command, dict) or not isinstance(command.get('data'), dict) or not isinstance(command['data'].get('groups'), list):
        return []
    if payload.get('status') != 'SUCCESS' or command.get('name') != 'usage':
        return []
    groups = []
    for group in command.get('data', {}).get('groups', []):
        if not isinstance(group, dict):
            continue
        if not isinstance(group.get('buckets'), list):
            continue
        buckets = [dict(id=b.get('id'), window=b.get('window'),
                        remaining_fraction=number(b.get('remaining_fraction'), 1),
                        reset_time=b.get('reset_time'))
                   if isinstance(b, dict) else {'remaining_fraction': None}
                   for b in group.get('buckets', [])]
        groups.append({'name': group.get('name'), 'buckets': buckets})
    return groups


def model_group(model, groups):
    # ponytail: measured AGY group names; unfamiliar families stay unavailable until mapped.
    name = 'Gemini Models' if model.startswith('gemini-') else 'Claude and GPT models' if model.startswith(('claude-', 'gpt-oss-')) else None
    return next((g for g in groups if g['name'] == name), None)


def remaining(group):
    buckets = group.get('buckets', []) if group else []
    values = [number(b.get('remaining_fraction'), 1) for b in buckets]
    return min(values) if values and all(v is not None for v in values) else None


def inventory(run, executable, env, excluded=('qwen',)):
    """No inference, token files, arbitrary shell, account names or raw auth output."""
    import json
    providers = []
    for cli, login in LOGIN.items():
        row = {'cli': cli, 'installed': shutil.which(cli) is not None,
               'auth': 'UNKNOWN', 'access': 'NOT_PROBED', 'models': [],
               'quota_groups': [], 'login_action': login, 'quota_remaining': None}
        providers.append(row)
        if not row['installed'] or cli in excluded:
            continue
        def probe(args):
            try:
                return run([executable(cli), *args], timeout=30, env=env)
            except (OSError, RuntimeError):
                return {'exit_code': 1, 'stdout': ''}
        def decoded(result):
            try:
                data = json.loads(result.get('stdout', ''))
                return data if result['exit_code'] == 0 and isinstance(data, dict) else {}
            except (ValueError, TypeError):
                return {}
        if cli == 'agy':
            models = probe(['models'])
            if models['exit_code'] == 0:
                for line in models['stdout'].splitlines():
                    parts = line.split('\t')
                    if len(parts) == 2 and re.fullmatch(r'[a-z][a-z0-9.-]{1,100}', parts[0]):
                        row['models'].append({'id': parts[0], 'label': parts[1][:150]})
            quota = decoded(probe(['--output-format', 'json', '-p', '/usage']))
            row['quota_groups'] = agy_groups(quota)
            if row['quota_groups']:
                row.update(auth='AUTHENTICATED_METADATA', access='METADATA_VERIFIED')
            credits = decoded(probe(['--output-format', 'json', '-p', '/credits']))
            command = credits.get('command') or {}
            if not isinstance(command, dict) or not isinstance(command.get('data'), dict):
                command = {'data': {}}
            row['credits_remaining'] = number(command.get('data', {}).get('remaining_credits')) if credits.get('status') == 'SUCCESS' and command.get('name') == 'credits' else None
            row['billing'] = 'NO_CREDITS_AVAILABLE' if row['credits_remaining'] == 0 else 'OVERAGE_POLICY_REQUIRED'
        elif cli == 'claude':
            status = decoded(probe(['auth', 'status']))
            row['auth'] = 'SUBSCRIPTION_LOGIN' if status.get('loggedIn') is True and status.get('authMethod') in ('oauth_token', 'oauth') and status.get('apiProvider') == 'firstParty' else 'LOGIN_OR_PLAN_REQUIRED'
            row['billing'] = 'EXTRA_USAGE_POLICY_REQUIRED'
            row['quota_action'] = 'Official interactive /usage; do not send it as an inference prompt'
        elif cli == 'codex':
            status = probe(['login', 'status'])
            output = status.get('stdout', '') + status.get('stderr', '')
            row['auth'] = 'SUBSCRIPTION_LOGIN' if status['exit_code'] == 0 and 'ChatGPT' in output else 'LOGIN_OR_PLAN_REQUIRED'
            row['quota_action'] = 'Current Codex host usage tool or official interactive /status'
        else:
            row['quota_action'] = 'Inspect current official CLI status; authentication/remaining quota not inferred from presence'
    return {'schema_version': 1, 'captured_at': datetime.now(timezone.utc).isoformat(),
            'providers': providers, 'excluded': list(excluded), 'excluded_model_prefixes': ['claude-'],
            'policy': 'Quota fractions are shared windows, not token counts. Unknown is null. No paid API/credit fallback.'}


def route(snapshot, complexity, reserve=RESERVE, now=None):
    if complexity not in ('SIMPLE', 'STANDARD', 'COMPLEX', 'SPECIALIZED'):
        raise ValueError('Unknown complexity')
    if number(reserve, 1) is None or reserve >= 1:
        raise ValueError('Invalid reserve fraction')
    captured = datetime.fromisoformat(snapshot['captured_at'])
    if captured.tzinfo is None:
        raise ValueError('Inventory timestamp requires timezone')
    age = ((now or datetime.now(timezone.utc)) - captured).total_seconds()
    if not 0 <= age <= 300:
        raise ValueError('Refresh CLI inventory; quota snapshot is stale')
    candidates = []
    for provider in snapshot['providers']:
        if provider['cli'] != 'agy' or provider['cli'] in snapshot.get('excluded', []) or provider.get('access') != 'METADATA_VERIFIED' or provider.get('billing') != 'NO_CREDITS_AVAILABLE':
            continue
        for entry in provider['models']:
            model = entry['id']
            if any(model.startswith(prefix) for prefix in snapshot.get('excluded_model_prefixes', [])):
                continue
            group = model_group(model, provider['quota_groups'])
            left = remaining(group)
            if left is None or left <= reserve:
                continue
            effort = model.rsplit('-', 1)[-1]
            family = 0 if re.match(r'gemini-[\d.]+-flash-', model) else 1 if model.startswith('claude-sonnet-') else 2 if re.match(r'gemini-[\d.]+-pro-', model) else 3 if model.startswith('claude-opus-') else None
            minimum = {'SIMPLE': 'low', 'STANDARD': 'medium', 'COMPLEX': 'high', 'SPECIALIZED': 'high'}[complexity]
            if family is None or effort not in ('low', 'medium', 'high') or ('low', 'medium', 'high').index(effort) < ('low', 'medium', 'high').index(minimum) or (complexity in ('COMPLEX', 'SPECIALIZED') and family < 2):
                continue
            candidates.append({'provider': 'agy', 'model': model, 'effort': effort,
                               'quota_group': group['name'], 'remaining_fraction': left,
                               'quality_tier': family})
    # Family/effort before quota: abundant quota does not justify a weaker quality floor.
    candidates.sort(key=lambda c: (c['quality_tier'], ('low', 'medium', 'high').index(c['effort']), -c['remaining_fraction'], tuple(-int(x) for x in re.findall(r'\d+', c['model']))))
    return {'status': 'CANDIDATES_REQUIRE_GATES' if candidates else 'BLOCKED',
            'selected': candidates[0] if candidates else None, 'candidates': candidates,
            'reserve_fraction': reserve, 'captured_at': snapshot['captured_at'],
            'next': 'Validate expert contract and task capability; open native interactive session, checkpoint before changing route. Refresh quota before each dispatch.' if candidates else 'Use an approved equally qualified route with fresh quota/overage evidence, log in via official CLI, or wait for reset. Do not lower quality.'}


def probe_model(selected, run, executable, env):
    """One bounded tool-free inference verifies selected model access, never catalogue alone."""
    import json
    import tempfile
    scratch = tempfile.mkdtemp(prefix='store-model-probe-')
    from pathlib import Path
    if Path(scratch).resolve().parent != Path(tempfile.gettempdir()).resolve():
        raise ValueError('Probe scratch directory escaped its owned temporary root')
    try:
        result = run([executable('agy'), '--model', selected['model'], '--effort', 'low',
                      '--mode', 'plan', '--disable-slash-commands', '--output-format', 'json',
                      '--print-timeout', '30s', '--print',
                      'No tools, files, MCP, skills or agents. Return only READY. This is an account/model access probe.'],
                     cwd=scratch, timeout=40, env=env, contained=True)
    except BaseException:
        # Preserve the owned scratch if containment/cleanup was not verified.
        raise
    else:
        if Path(scratch).resolve().parent != Path(tempfile.gettempdir()).resolve():
            raise ValueError('Probe cleanup escaped its owned temporary root')
        shutil.rmtree(scratch)
    try:
        payload = json.loads(result.get('stdout', ''))
        if not isinstance(payload, dict):
            payload = {}
    except (ValueError, TypeError):
        payload = {}
    response = payload.get('response')
    usage = payload.get('usage') if isinstance(payload.get('usage'), dict) else {}
    available = result['exit_code'] == 0 and payload.get('status') == 'SUCCESS' and isinstance(response, str) and response.strip() == 'READY' and not payload.get('denied_actions')
    # Never return raw auth/errors/prompt content; quota or permission failure is not a successful probe.
    return {'provider': 'agy', 'model': selected['model'], 'effort': 'low',
            'state': 'AVAILABLE' if available else 'UNVERIFIED',
            'usage': {key: number(usage.get(key)) for key in
                      ('input_tokens', 'output_tokens', 'thinking_tokens', 'cache_read_tokens')},
            'next_action': 'Dispatch bounded task with its selected effort' if available else
                           'Inspect official native status/login/quota and checkpoint; do not assume model entitlement'}


def usage_summary(records, expected_attempts=None):
    """Aggregate distinct agent/attempt records, excluding provider inclusive totals."""
    unique = {}
    for record in records:
        if (not isinstance(record, dict) or
                any(not isinstance(record.get(field), str) or not record[field].strip() for field in ('provider', 'session')) or
                not isinstance(record.get('attempt'), int) or isinstance(record['attempt'], bool) or record['attempt'] < 1 or
                ('includes_children' in record and not isinstance(record['includes_children'], bool))):
            raise ValueError('Invalid usage attempt identity or child coverage')
        key = (record['provider'], record['session'], record['attempt'])
        if key in unique and unique[key] != record:
            raise ValueError('Conflicting usage for the same attempt')
        unique[key] = record
    leaves = [r for r in unique.values() if not r.get('includes_children')]
    fields = ('input_tokens', 'output_tokens', 'thinking_tokens', 'cache_read_tokens')
    totals = {field: sum(values) if values and all(v is not None for v in values) else None
              for field in fields for values in [[number(r['usage'].get(field)) if isinstance(r.get('usage'), dict) else None for r in leaves]]}
    return {'attempts': len(unique), 'totals': totals,
            'complete': bool(leaves) and expected_attempts is not None and set(expected_attempts) == set(unique) and len(leaves) == len(unique) and all(v is not None for v in totals.values()),
            'inclusive_records_excluded': len(unique) - len(leaves),
            'quota_remaining': None}


def native_launch(project, request_path, terminal, python, module):
    """Keep the prompt out of Windows Terminal's command parser; use a real native TUI."""
    from pathlib import Path
    if not terminal:
        raise RuntimeError('Native visible terminal unavailable; do not silently dispatch headless')
    args = [terminal, '-w', 'store-automation', 'new-tab', '--title',
            'Uygulayıcı — Store Automation', '-d', str(Path(project).resolve()),
            python, str(module), '--interactive', str(request_path)]
    if any(';' in arg or '\n' in arg or '\r' in arg for arg in args):
        raise ValueError('Unsafe terminal argument')
    return args


if __name__ == '__main__':
    import json
    from pathlib import Path
    import subprocess
    import sys
    import factory
    if len(sys.argv) != 3 or sys.argv[1] != '--interactive':
        raise SystemExit('Use store-automation native with a validated project contract')
    path = factory.trusted_input(sys.argv[2], '.json', '.factory/runs')
    request = factory.load(path)
    if request['project'] != str(factory.ROOT):
        raise ValueError('Native handoff belongs to another project')
    contract = factory.validate_contract(factory.load(factory.trusted_input(request['contract'], '.json')))
    if contract['permissions'].get('write') or not set(contract['required_capabilities']).issubset({'reasoning', 'source_read'}):
        raise ValueError('Native write/specialized capability permission is not verified')
    prompt_path = factory.trusted_input(request['prompt_file'], '.txt')
    if factory.digest_file(Path(request['contract'])) != request['contract_sha256'] or factory.digest_file(prompt_path) != request['prompt_sha256']:
        raise ValueError('Native contract/prompt changed after dispatch; replan before launch')
    prompt = prompt_path.read_text(encoding='utf-8')
    selected = request['selected']
    if selected['provider'] != 'agy':
        raise ValueError('Unsupported native adapter; use the verified official host directly')
    # Refresh quota at actual launch, not only when the terminal request was created.
    current = inventory(factory.run, factory.executable, factory.clean_ai_env(factory.os.environ))
    candidates = route(current, request['complexity'])['candidates']
    if not any((c['model'], c['effort']) == (selected['model'], selected['effort']) for c in candidates):
        raise SystemExit('Selected model no longer meets quota/quality gates; checkpoint and reroute')
    probe = probe_model(selected, factory.run, factory.executable, factory.clean_ai_env(factory.os.environ))
    factory.save(path.with_name(path.stem + '-model-probe.json'), probe)
    if probe['state'] != 'AVAILABLE':
        raise SystemExit('Model-specific access unverified; task not dispatched. See native model probe.')
    prompt = (json.dumps(contract, ensure_ascii=False) + '\n' + prompt +
              '\nSupervisor handoff: ' + json.dumps(selected) +
              '\nUse native tools only within the contract scope. No Brain/git/account/policy writes or nested delegation. '
              'Publish progress and return task, role, provider_model, effort, state, changed_files, evidence, usage '
              '(only authoritative counters or null), blockers, next_action as a final JSON response in this terminal. '
              'No writes, including report files. After reporting completion, answer questions without source changes. '
              'The supervisor performs machine verification and fresh independent review; you cannot accept your own work.')
    if len(prompt) > contract['delegation']['context_budget_chars']:
        raise SystemExit('Final native prompt exceeds contract context budget; task not dispatched')
    print(f"{contract['task_id']} | {contract['persona']['role']} | {selected['model']} | effort {selected['effort']}", flush=True)
    # argv + inherited terminal: the user can ask/interrupt the actual agent, no fabricated viewer.
    raise SystemExit(subprocess.call([factory.executable('agy'), '--model', selected['model'],
                                     '--effort', selected['effort'], '--mode', 'plan',
                                     '--prompt-interactive', prompt],
                                    cwd=factory.ROOT, env=factory.clean_ai_env(factory.os.environ)))
