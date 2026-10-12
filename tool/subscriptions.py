"""Read official CLI metadata, select a sufficient model, and account for reported usage."""
from datetime import datetime, timezone
import math
import re
import shutil
import threading


LOGIN = {'agy': 'agy (official account setup)', 'claude': 'claude auth login',
         'codex': 'codex login', 'gemini': 'gemini (Login with Google)',
         'mcode': 'mcode login --region global', 'opencode': 'opencode auth login',
         **dict.fromkeys(('mimo', 'cursor', 'windsurf', 'cline', 'codebuff',
                          'freebuff', 'zed', 'ollama', 'qwen', 'minimax', 'zcode', 'antigravity',
                          'kimi', 'hermes', 'lms', 'omniroute'),
                         'Verify the installed official client and its documented account/model/status controls')}
RESERVE = 0.10
# Task suitability assessed from the host's documented model roles; new IDs need reassessment.
CODEX_TIERS = {'gpt-5.6-luna': 0, 'gpt-6-luna': 0, 'gpt-5.6-terra': 1,
               'gpt-5.6-sol': 2, 'gpt-6-sol': 2, 'gpt-6.1-sol': 2, 'gpt-6-astra': 3}
# Public documentation only; metadata cannot grant billing or tool permissions.
CLI_DOCS = {'codex': 'https://developers.openai.com/codex/cli/',
            'mcode': 'https://github.com/MiniMax-AI/minimax-code',
            'minimax': 'https://agent.minimax.io/',
            'mimo': 'https://github.com/XiaomiMiMo/MiMo-Code',
            'opencode': 'https://opencode.ai/docs/',
            'gemini': 'https://geminicli.com/docs/',
            'claude': 'https://code.claude.com/docs/',
            'kimi': 'https://moonshotai.github.io/kimi-cli/en/reference/slash-commands.html'}
OPENROUTER_MODELS_URL = 'https://openrouter.ai/api/v1/models'
CATALOGUE_MAX_BYTES = 8 * 1024 * 1024
REPORT_FIELDS = ('task', 'role', 'provider', 'model', 'effort', 'state',
                 'changed_files', 'evidence', 'usage', 'blockers', 'next_action')


def number(value, maximum=None):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 and (maximum is None or value <= maximum) else None


def report_valid(report, task_id=None):
    """Validate public report shape; a complete report is not task acceptance."""
    if not isinstance(report, dict) or not set(REPORT_FIELDS).issubset(report):
        return False
    if any(not isinstance(report[key], str) or not report[key].strip() for key in
           ('task', 'role', 'provider', 'model', 'effort', 'state', 'next_action')):
        return False
    if task_id is not None and report['task'] != task_id:
        return False
    if any(not isinstance(report[key], list) or any(not isinstance(item, str) or not item.strip()
           for item in report[key]) for key in ('changed_files', 'evidence', 'blockers')):
        return False
    usage = report['usage']
    return usage is None or (isinstance(usage, dict) and all(isinstance(key, str) and
           (value is None or number(value) is not None) for key, value in usage.items()))


def codex_metadata(executable, env, timeout=30):
    """Bounded official stdio metadata RPC; no turn, credential or account reads."""
    import json
    import queue
    import subprocess
    import threading
    import time
    try:
        from . import sessions
    except ImportError:
        import sessions
    result = {'models': [], 'quota_groups': [], 'catalogue': 'UNAVAILABLE',
              'access': 'NOT_PROBED'}
    tree = sessions.ProcessTree()
    proc = None
    messages = queue.Queue(maxsize=128)
    deadline = time.monotonic() + timeout
    def read():
        try:
            while True:
                line = proc.stdout.readline(1_000_001)
                if not line or len(line) > 1_000_000:
                    break
                try:
                    messages.put(json.loads(line), timeout=.1)
                except (ValueError, queue.Full):
                    break
        finally:
            try:
                messages.put(None, timeout=.1)
            except queue.Full:
                pass
    def rpc(identity, method, params):
        proc.stdin.write(json.dumps({'id': identity, 'method': method, 'params': params}) + '\n')
        proc.stdin.flush()
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError('Metadata deadline reached')
            message = messages.get(timeout=left)
            if message is None:
                raise RuntimeError('Metadata stream ended')
            if isinstance(message, dict) and message.get('id') == identity:
                if not isinstance(message.get('result'), dict):
                    raise ValueError('Metadata response unavailable')
                return message['result']
    try:
        proc = tree.spawn([executable('codex'), 'app-server', '--stdio', '-c', 'forced_login_method="chatgpt"'],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          text=True, encoding='utf-8', env=env)
        threading.Thread(target=read, daemon=True).start()
        rpc(1, 'initialize', {'clientInfo': {'name': 'store-automation-metadata', 'version': '1.0'},
                              'capabilities': {'experimentalApi': True}})
        proc.stdin.write('{"method":"initialized","params":{}}\n')
        proc.stdin.flush()
        models, cursor = [], None
        for page in range(10):
            payload = rpc(page + 2, 'model/list', {'limit': 100, 'includeHidden': False, 'cursor': cursor})
            if not isinstance(payload.get('data'), list):
                raise ValueError('Invalid model catalogue')
            for model in payload['data']:
                if not isinstance(model, dict) or not isinstance(model.get('id'), str) or not re.fullmatch(
                        r'[a-z][a-z0-9.-]{1,100}', model['id']):
                    raise ValueError('Invalid model identity')
                efforts = model.get('supportedReasoningEfforts')
                if not isinstance(efforts, list) or not efforts or any(
                        not isinstance(item, dict) or item.get('reasoningEffort') not in
                        ('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra') for item in efforts):
                    raise ValueError('Invalid supported model effort')
                entry = {'id': model['id'], 'supported_efforts': [item['reasoningEffort'] for item in efforts],
                         'access': 'CATALOGUE_ONLY'}
                for key in ('description', 'displayName'):
                    if isinstance(model.get(key), str) and len(model[key]) <= 600:
                        entry[key] = model[key]
                models.append(entry)
            cursor = payload.get('nextCursor')
            if cursor is None:
                break
            if not isinstance(cursor, str) or not cursor or len(cursor) > 1000:
                raise ValueError('Invalid catalogue cursor')
        else:
            raise ValueError('Catalogue pagination exceeds bound')
        quota = rpc(20, 'account/rateLimits/read', {})
        buckets = quota.get('rateLimitsByLimitId')
        if not isinstance(buckets, dict):
            buckets = {'codex': quota.get('rateLimits')}
        bucket = buckets.get('codex')
        if not isinstance(bucket, dict):
            raise ValueError('Codex shared quota unavailable')
        windows = []
        for window in ('primary', 'secondary'):
            value = bucket.get(window)
            if not isinstance(value, dict) or number(value.get('usedPercent'), 100) is None:
                raise ValueError('Codex shared window unknown')
            windows.append({'id': 'codex-' + window, 'window': window,
                            'remaining_fraction': (100 - value['usedPercent']) / 100,
                            'reset_time': number(value.get('resetsAt')),
                            'window_duration_mins': number(value.get('windowDurationMins'))})
        if quota.get('ordinaryUsageAllowed') is False or bucket.get('rateLimitReachedType') is not None:
            raise ValueError('Included ordinary usage disallowed')
        result.update(models=models, quota_groups=[{'name': 'Codex Models', 'buckets': windows}],
                      catalogue='CLI_METADATA_VERIFIED', access='METADATA_VERIFIED')
    except (OSError, RuntimeError, ValueError, queue.Empty):
        pass
    finally:
        tree.close()
        if proc is not None:
            proc.wait(timeout=5)
            for pipe in (proc.stdin, proc.stdout):
                if pipe:
                    pipe.close()
    return result


ACP_MAX_SECONDS = 20


def _acp_argv(cli, executable):
    """Resolve official entry points without invoking a shell or a CLI prompt."""
    import os
    from pathlib import Path
    if cli == 'mcode':
        launcher = executable('mcode')
        if not launcher:
            raise OSError('Official mcode launcher unavailable')
        script = Path(launcher).resolve().parent / 'node_modules' / '@minimax-ai' / 'code' / 'cli.js'
        if not script.is_file():
            raise OSError('Official @minimax-ai/code entry point unavailable beside launcher')
        return [executable('node'), str(script), 'acp']
    if cli in ('kimi', 'mimo'):
        return [executable(cli), 'acp']
    raise ValueError('Unsupported ACP client')


def _acp_catalogue(cli, executable, env, project=None, timeout=ACP_MAX_SECONDS):
    """Read bounded ACP report metadata only; no prompts, auth claims, or quota claims."""
    import os
    from pathlib import Path
    try:
        from . import sessions, native_agents
    except ImportError:
        try:
            import sessions
            import native_agents
        except ImportError:
            from tool import sessions, native_agents
    tree = None
    proc = None
    timed_out = threading.Event()
    close_errors = []
    try:
        tree = sessions.ProcessTree()
        def stop_on_deadline():
            timed_out.set()
            try:
                tree.close()
            except Exception as error:
                close_errors.append(error)
        timer = threading.Timer(timeout, stop_on_deadline)
        timer.daemon = True
        timer.start()
        try:
            client = native_agents.AcpMetadata(_acp_argv(cli, executable), project or os.getcwd(), env,
                                               tree=tree)
            report = client.report()
        except Exception:
            if timed_out.is_set():
                raise TimeoutError('ACP metadata deadline reached') from None
            raise
        finally:
            timer.cancel()
        if timed_out.is_set():
            raise TimeoutError('ACP metadata deadline reached')
        if close_errors:
            raise close_errors[0]
        if not isinstance(report, dict) or report.get('inference') is not False:
            raise ValueError('ACP metadata report is invalid')
        raw_models = report.get('models', [])
        raw_efforts = report.get('efforts', [])
        raw_modes = report.get('modes', [])
        if not all(isinstance(items, list) and len(items) <= 500
                   for items in (raw_models, raw_efforts, raw_modes)):
            raise ValueError('ACP metadata groups exceed bounds')
        models = []
        for item in raw_models:
            if not isinstance(item, dict):
                continue
            identity, label = item.get('id'), item.get('name')
            if isinstance(identity, str) and 0 < len(identity) <= 200 and '..' not in identity and re.fullmatch(
                    r'[A-Za-z0-9_][A-Za-z0-9_.:/+-]*', identity):
                models.append({'id': identity, 'name': label[:160] if isinstance(label, str) else identity})
        def safe_values(items):
            return [{'id': value} for value in items if isinstance(value, str) and
                    0 < len(value) <= 100 and re.fullmatch(r'[A-Za-z0-9_.+-]+', value)]
        return {'models': models, 'efforts': safe_values(raw_efforts), 'mode_options': safe_values(raw_modes),
                'model_selector': bool(models),
                'catalogue': 'CLI_METADATA_VERIFIED' if models else 'UNAVAILABLE'}
    except Exception as error:
        # Native ACP errors may contain private paths or data; publish only the class.
        return {'models': [], 'efforts': [], 'mode_options': [], 'catalogue': 'UNAVAILABLE',
                'model_selector': False, 'error': type(error).__name__}
    finally:
        proc = getattr(tree, 'proc', None) if tree is not None else None
        if tree is not None:
            tree.close()
        if proc is not None:
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
            for pipe in (proc.stdin, proc.stdout, proc.stderr):
                if pipe:
                    try:
                        pipe.close()
                    except OSError:
                        pass


def reserve_decision(actor, remaining_fraction, handoff_saved=False,
                     equivalent_verified=False, reserve=RESERVE):
    """Caller confirms a durable handoff and a fresh, equally capable approved route.

    Unknown limits never authorize dispatch. The coordinator waits rather than
    transferring its authority; only a checkpointed worker may change routes.
    """
    if actor not in ('coordinator', 'worker') or number(reserve, 1) is None or reserve >= 1:
        raise ValueError('Invalid reserve actor or fraction')
    if not isinstance(handoff_saved, bool) or not isinstance(equivalent_verified, bool):
        raise ValueError('Checkpoint and equivalent-route evidence must be explicit booleans')
    left = number(remaining_fraction, 1)
    if left is None:
        return 'QUOTA_UNKNOWN'
    if left > reserve:
        return 'READY'
    if not handoff_saved:
        return 'CHECKPOINT_REQUIRED'
    return 'REROUTE_APPROVED' if actor == 'worker' and equivalent_verified else 'WAIT_FOR_RESET'


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


def openrouter_free_models(payload):
    """Public price metadata only; neither account access nor coding quality."""
    from decimal import Decimal, InvalidOperation
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        return []
    models = []
    for entry in payload['data']:
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not re.fullmatch(
                r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.:-]{1,160}:free', entry['id']):
            continue
        pricing = entry.get('pricing')
        if not isinstance(pricing, dict) or not {'prompt', 'completion'}.issubset(pricing):
            continue
        try:
            if any(not isinstance(key, str) or not re.fullmatch(r'[a-z_]{1,64}', key) or
                   isinstance(value, bool) or not isinstance(value, (str, int, float)) or
                   not Decimal(str(value)).is_finite() or Decimal(str(value)) != 0
                   for key, value in pricing.items()):
                continue
        except (InvalidOperation, ValueError):
            continue
        architecture = entry.get('architecture') if isinstance(entry.get('architecture'), dict) else {}
        def observed_strings(value):
            return value if isinstance(value, list) and len(value) <= 64 and all(
                isinstance(item, str) and re.fullmatch(r'[a-z][a-z0-9_/-]{0,63}', item) for item in value) else None
        models.append({'id': entry['id'], 'pricing': {key: '0' for key in pricing},
                       'context_length': number(entry.get('context_length')),
                       'supported_parameters': observed_strings(entry.get('supported_parameters')),
                       'input_modalities': observed_strings(architecture.get('input_modalities')),
                       'output_modalities': observed_strings(architecture.get('output_modalities')),
                       'quality_tier': 'UNASSESSED', 'effort': 'UNKNOWN', 'access': 'NOT_PROBED'})
    return models


def openrouter_catalogue():
    """Fixed public GET, no credential/header/inference or arbitrary URL input."""
    import json
    from urllib.request import urlopen
    row = {'cli': 'openrouter', 'installed': False, 'adapter': 'UNVERIFIED',
           'auth': 'UNKNOWN', 'access': 'NOT_PROBED', 'quota_remaining': None,
           'source': OPENROUTER_MODELS_URL, 'models': [], 'catalogue': 'UNAVAILABLE',
           'billing': 'PUBLIC_PRICE_METADATA_ONLY'}
    try:
        with urlopen(OPENROUTER_MODELS_URL, timeout=15) as response:
            if response.geturl() != OPENROUTER_MODELS_URL:
                return row
            payload = response.read(CATALOGUE_MAX_BYTES + 1)
        if len(payload) > CATALOGUE_MAX_BYTES:
            return row
        data = json.loads(payload)
        if not isinstance(data, dict) or not isinstance(data.get('data'), list):
            return row
        row.update(models=openrouter_free_models(data), catalogue='PUBLIC_METADATA_VERIFIED')
    except (OSError, ValueError):
        pass
    return row


def host_registry(run, executable, env):
    """Dynamic manager detection hints, never executable/auth/model entitlement."""
    import json
    result = {'source': 'skills-manager-cli agents list --json',
              'status': 'NOT_INSTALLED', 'clients': []}
    if not shutil.which('skills-manager-cli'):
        return result
    result['status'] = 'UNAVAILABLE'
    try:
        response = run([executable('skills-manager-cli'), 'agents', 'list', '--json'],
                       timeout=30, env=env)
        output = response.get('stdout')
        if response.get('exit_code') != 0 or not isinstance(output, str) or len(output) > 2_000_000:
            return result
        rows = json.loads(output)
    except (OSError, RuntimeError, ValueError):
        return result
    if not isinstance(rows, list) or len(rows) > 5000:
        return result
    clients = []
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('key'), str) or
                not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', row['key']) or
                not isinstance(row.get('display_name'), str) or
                not re.fullmatch(r'[\w .()+/-]{1,100}', row['display_name']) or
                any(not isinstance(row.get(field), bool) for field in ('installed', 'enabled', 'is_custom'))):
            return result
        clients.append({'key': row['key'], 'name': row['display_name'],
                        'host_reported_installed': row['installed'],
                        'enabled': row['enabled'], 'custom': row['is_custom'],
                        'access': 'UNKNOWN', 'adapter': 'UNKNOWN', 'quota_remaining': None})
    result.update(status='REGISTRY_METADATA', clients=clients)
    return result


def inventory(run, executable, env, excluded=('qwen',), include_openrouter=False):
    """No inference, token files, arbitrary shell, account names or raw auth output."""
    import json
    providers = []
    for cli, login in LOGIN.items():
        row = {'cli': cli, 'installed': shutil.which(cli) is not None,
               'auth': 'UNKNOWN', 'access': 'NOT_PROBED', 'models': [],
               'quota_groups': [], 'login_action': login, 'quota_remaining': None,
               'adapter': 'METADATA_ONLY' if cli in ('agy', 'claude', 'codex', 'opencode') else 'UNVERIFIED'}
        providers.append(row)
        row['documentation'] = CLI_DOCS.get(cli)
        row['executable'] = None
        if row['installed']:
            try:
                row['executable'] = executable(cli)
            except (OSError, RuntimeError):
                row['executable'] = shutil.which(cli)
        row['controls'] = {'models': 'UNKNOWN', 'effort': 'UNKNOWN', 'quota': 'UNKNOWN',
                           'session': 'UNKNOWN', 'intervention': 'UNKNOWN', 'permissions': 'UNVERIFIED'}
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
            row['controls'].update(models='agy models', effort='--effort', quota='/usage metadata',
                                   session='--conversation', intervention='native TUI', permissions='--mode plan; sandbox unverified')
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
            row['controls'].update(models='app-server model/list', effort='model_reasoning_effort',
                                   quota='app-server account/rateLimits/read', session='native thread',
                                   intervention='exec snapshot: unavailable; app-server turn/steer', permissions='read-only snapshot wrapper')
            status = probe(['login', 'status'])
            output = status.get('stdout', '') + status.get('stderr', '')
            row['auth'] = 'SUBSCRIPTION_LOGIN' if status['exit_code'] == 0 and 'ChatGPT' in output else 'LOGIN_OR_PLAN_REQUIRED'
            if row['auth'] == 'SUBSCRIPTION_LOGIN':
                row.update(codex_metadata(executable, env))
                row['billing'] = 'SUBSCRIPTION_ONLY_REQUIRED'
            row['quota_action'] = 'Current Codex host usage tool or official interactive /status'
        elif cli in ('opencode', 'mimo'):
            result = probe(['--pure', 'models'])
            if result['exit_code'] == 0:
                row['models'] = [{'id': model, 'quality_tier': 'UNASSESSED', 'effort': 'UNKNOWN'}
                                 for model in result.get('stdout', '').splitlines()
                                 if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.:/-]{1,180}', model)]
                row['catalogue'] = 'CLI_METADATA_VERIFIED'
            row['quota_action'] = 'Provider-specific official status required; catalogue is not account access'
            row['controls'].update(models=cli + ' --pure models', session=cli + ' attach / session',
                                   intervention='native HTTP requires owned config verification')
        elif cli in ('mcode', 'kimi'):
            row['controls'].update(models=cli + ' ACP session/new configOptions',
                                   effort='ACP configOptions (only when explicitly returned)',
                                   session=cli + ' native ACP', intervention='native TUI / ACP',
                                   permissions='ACP configOptions only; execution permissions unverified')
            metadata = _acp_catalogue(cli, executable, env)
            row.update(catalogue=metadata['catalogue'], efforts=metadata['efforts'],
                       mode_options=metadata['mode_options'], model_selector=metadata['model_selector'],
                       billing='UNVERIFIED', quota_remaining=None,
                       quota_action=('Official interactive /status; inspect Token Plan credits and permissions' if cli == 'mcode'
                                     else 'Official interactive /usage (alias /status); supported only on Kimi Code platform'))
            row['models'] = [dict(model, effort='UNKNOWN', quality_tier='UNASSESSED', access='NOT_PROBED')
                             for model in metadata['models']]
            row['adapter'] = 'CATALOGUE_ONLY'
            if metadata.get('error'):
                row['metadata_error'] = metadata['error']
        else:
            row['quota_action'] = 'Inspect current official CLI status; authentication/remaining quota not inferred from presence'
    if include_openrouter:
        providers.append(openrouter_catalogue())
    return {'schema_version': 1, 'captured_at': datetime.now(timezone.utc).isoformat(),
            'host_clients': host_registry(run, executable, env),
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
        cli = provider['cli']
        billing = provider.get('billing')
        if (cli not in ('agy', 'codex') or cli in snapshot.get('excluded', []) or
                provider.get('access') != 'METADATA_VERIFIED' or
                (cli == 'agy' and billing != 'NO_CREDITS_AVAILABLE') or
                (cli == 'codex' and (provider.get('auth') != 'SUBSCRIPTION_LOGIN' or billing != 'SUBSCRIPTION_ONLY_REQUIRED'))):
            continue
        for entry in provider['models']:
            model = entry['id']
            if any(model.startswith(prefix) for prefix in snapshot.get('excluded_model_prefixes', [])):
                continue
            group = model_group(model, provider['quota_groups']) if cli == 'agy' else next(
                (item for item in provider['quota_groups'] if item.get('name') == 'Codex Models'), None)
            left = remaining(group)
            if reserve_decision('worker', left, reserve=reserve) != 'READY':
                continue
            effort = model.rsplit('-', 1)[-1]
            if cli == 'codex':
                family = CODEX_TIERS.get(model)
                available = entry.get('supported_efforts', [])
                if not isinstance(available, list):
                    continue
                minimum = {'SIMPLE': 'low', 'STANDARD': 'medium', 'COMPLEX': 'high', 'SPECIALIZED': 'high'}[complexity]
                effort = next((value for value in ('low', 'medium', 'high')
                               if value in available and ('low', 'medium', 'high').index(value) >= ('low', 'medium', 'high').index(minimum)), None)
                if complexity == 'STANDARD' and family == 0:
                    continue
            else:
                family = 0 if re.match(r'gemini-[\d.]+-flash-', model) else 1 if model.startswith('claude-sonnet-') else 2 if re.match(r'gemini-[\d.]+-pro-', model) else 3 if model.startswith('claude-opus-') else None
            minimum = {'SIMPLE': 'low', 'STANDARD': 'medium', 'COMPLEX': 'high', 'SPECIALIZED': 'high'}[complexity]
            if family is None or effort not in ('low', 'medium', 'high') or ('low', 'medium', 'high').index(effort) < ('low', 'medium', 'high').index(minimum) or (complexity in ('COMPLEX', 'SPECIALIZED') and family < 2):
                continue
            candidates.append({'provider': cli, 'model': model, 'effort': effort,
                               'quota_group': group['name'], 'remaining_fraction': left,
                               'quality_tier': family})
    # Family/effort before quota: abundant quota does not justify a weaker quality floor.
    candidates.sort(key=lambda c: (c['quality_tier'], ('low', 'medium', 'high').index(c['effort']), -c['remaining_fraction'],
                                   tuple(-int(x) for x in (re.findall(r'\d+', c['model']) + ['0'] * 4)[:4])))
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
              'Publish progress and return task, role, provider, model, effort, state, changed_files, evidence, usage '
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
