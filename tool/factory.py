"""Small deterministic gaps around native OpenCode; no workflow state/database."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import secrets
import shutil
import subprocess
import sys
import time
import zipfile

try:
    from . import sessions
except ImportError:
    import sessions

BUNDLE = Path(__file__).resolve().parents[1]
ROOT = Path.cwd().resolve()
BRAIN = Path(os.environ['STORE_AUTOMATION_BRAIN']) if os.environ.get('STORE_AUTOMATION_BRAIN') else next(
    (path for path in (Path.home() / '.skills-manager/skills/project-brain/scripts/brain.py',
                       Path.home() / '.codex/skills/project-brain/scripts/brain.py',
                       Path.home() / '.config/opencode/skills/project-brain/scripts/brain.py') if path.is_file()),
    Path.home() / '.codex/skills/project-brain/scripts/brain.py')
STARTER = Path(os.environ.get('STORE_AUTOMATION_STARTER', 'D:/repositories/napp_app_template'))
KIT = Path(os.environ.get('STORE_AUTOMATION_KIT', 'D:/repositories/napp-core'))
FREE_MODELS = ('opencode/space-bunny-free', 'opencode/longcat-2.5-preview-free')
FIELDS = ('task_id objective persona context dependencies scope out_of_scope '
          'required_capabilities allowed_tools permissions quality_requirements '
          'acceptance_criteria required_evidence deliverables failure_policy handoff_format').split()
PERSONA = ('role expertise objective quality_standard tools permissions '
           'forbidden_actions common_failure_modes acceptance_criteria').split()


def sensitive_path(path):
    return bool(re.search(r'auth|credential|secret|service-account|\.env|\.jks$|\.p8$|\.p12$|\.pfx$|\.pem$|id_rsa|id_ed25519|key\.properties', str(path), re.I))


def snapshot_path(name):
    path = (ROOT / name).resolve()
    if ROOT not in path.parents or sensitive_path(name) or sensitive_path(path):
        raise ValueError('Unsafe source snapshot path')
    if not path.is_file() or path.stat().st_size > 100_000:
        raise ValueError('Source snapshot missing or exceeds context budget')
    return path


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def project_dir(name):
    path = (ROOT / name).resolve()
    if ROOT not in path.parents:
        raise ValueError('Project state directory escapes the selected project')
    return path


def trusted_input(path, suffix, directory='contracts'):
    path = Path(path).resolve()
    base = project_dir(directory)
    if base not in path.parents or path.suffix != suffix or not path.is_file():
        raise ValueError('Input must be an existing contracts file in the factory workspace')
    if sensitive_path(path.name):
        raise ValueError('Secret input refused')
    return path


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive writes keep old evidence and interrupted work intact.
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)


def validate_contract(data):
    if not isinstance(data, dict) or any(k not in data for k in FIELDS):
        raise ValueError('Incomplete task contract')
    if not re.fullmatch(r'PB-\d{3,}', data['task_id']):
        raise ValueError('task_id must refer to an existing Project Brain task')
    if not project_dir('.project-brain/tasks/' + data['task_id'] + '.md').is_file():
        raise ValueError('Canonical Project Brain task does not exist')
    if not re.search(r'^Status: (READY|IN_PROGRESS)$',
                     project_dir('.project-brain/tasks/' + data['task_id'] + '.md').read_text(encoding='utf-8'), re.M):
        raise ValueError('Task must be READY or IN_PROGRESS before dispatch/acceptance')
    if not isinstance(data['persona'], dict) or any(not data['persona'].get(k) for k in PERSONA):
        raise ValueError('Incomplete persona')
    lists = ('context scope out_of_scope required_capabilities allowed_tools '
             'quality_requirements acceptance_criteria required_evidence deliverables').split()
    if any(not isinstance(data[k], list) or not data[k] or
           any(not isinstance(v, str) or not v.strip() for v in data[k]) for k in lists):
        raise ValueError('Nonempty string lists required')
    if not isinstance(data['dependencies'], list):
        raise ValueError('dependencies must be a list')
    if any(not isinstance(dep, str) or not re.fullmatch(r'PB-\d{3,}', dep)
           for dep in data['dependencies']):
        raise ValueError('Invalid dependency ID')
    for dep in data['dependencies']:
        if not project_dir('.project-brain/tasks/' + dep + '.md').is_file():
            history = run(['git', 'log', '--format=%B', '--grep=PB-Task: ' + dep])
            if history['exit_code'] or not history['stdout'].strip():
                raise ValueError('Dependency has no canonical task or completed checkpoint')
    if any(not isinstance(data[k], str) or not data[k].strip()
           for k in ('objective', 'failure_policy', 'handoff_format')):
        raise ValueError('Missing objective/failure/handoff text')
    if not isinstance(data['permissions'], dict) or data['permissions'].get('paid_api') is not False:
        raise ValueError('paid_api must be explicitly false')
    if data['permissions'].get('deploy') is not False:
        raise ValueError('Production operations are outside the factory worker')
    persona = data['persona']
    if any(not isinstance(persona[k], str) for k in ('role', 'objective', 'quality_standard')) or any(
            not isinstance(persona[k], list) or not persona[k] or
            any(not isinstance(v, str) or not v.strip() for v in persona[k])
            for k in ('expertise', 'tools', 'forbidden_actions', 'common_failure_modes', 'acceptance_criteria')):
        raise ValueError('Persona strings and lists have invalid types')
    if not isinstance(persona['permissions'], dict) or persona['permissions'] != {
            k: data['permissions'][k] for k in persona['permissions'] if k in data['permissions']}:
        raise ValueError('Persona permissions conflict with task permissions')
    if not set(persona['tools']).issubset(data['allowed_tools']):
        raise ValueError('Persona tools exceed allowed tools')
    for scope in data['scope']:
        if PureWindowsPath(scope).anchor or Path(scope).anchor or '..' in PureWindowsPath(scope).parts:
            raise ValueError('scope must stay within the selected workspace')
    return data


def worker_permissions(task):
    edits = {'*': 'deny'}
    if task['permissions'].get('write') is True:
        for scope in task['scope']:
            if not re.match(r'^(?:\.factory/workspaces/[a-z0-9_-]+/)?(?:lib/|test/|assets/|android/app/src/|ios/Runner/|pubspec\.yaml$)', scope):
                raise ValueError('Worker writes restricted to selected application source paths')
            prefix = scope.split('*', 1)[0]
            candidate = ROOT / prefix
            if any(path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())
                   for path in (candidate, *candidate.parents) if path != ROOT and ROOT in path.parents):
                raise ValueError('Worker write scope may not traverse a link')
            if ROOT not in candidate.resolve().parents:
                raise ValueError('Worker write scope escapes the workspace')
            if '*' in scope and candidate.exists() and any(
                    p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in candidate.rglob('*')):
                raise ValueError('Wildcard write scope contains linked paths')
            # OpenCode v1.18 edit/write asks with worktree-relative native paths.
            edits[scope] = 'allow'
            edits[str(Path(scope))] = 'allow'
    return {'agent': {'factory': {'permission': {'bash': 'deny', 'edit': 'deny'}},
                      'factory-worker': {'permission': {'edit': edits, 'bash': 'deny', 'grep': 'deny'}}}}


def executable(name):
    # Native exe avoids Windows batch argument injection in model prompts.
    npm = Path(os.environ.get('APPDATA', '')) / 'npm/node_modules'
    if os.name == 'nt' and name == 'dart':
        shim = shutil.which('dart')
        native = Path(shim).parent / 'cache/dart-sdk/bin/dart.exe' if shim else Path('missing')
        if native.is_file():
            return str(native)
        raise RuntimeError('Native Dart executable required; refusing batch arguments')
    if os.name == 'nt' and name in ('opencode', 'codex'):
        if name == 'opencode':
            local = Path.home() / '.local/share/ai-app-factory/runtime-1.18.0/node_modules/opencode-ai/bin/opencode.exe'
            if local.is_file():
                return str(local)
        candidates = list((npm / ('opencode-ai' if name == 'opencode' else '@openai/codex')).rglob(name + '.exe'))
        if candidates:
            return str(candidates[0])
        raise RuntimeError(f'Native {name}.exe unavailable; refusing batch model shim')
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f'{name} unavailable')
    return path


def clean_ai_env(env):
    # Auth remains in each official CLI; never inspect or transfer its tokens.
    return {k: v for k, v in env.items() if not re.search(
        r'OPENAI|ANTHROPIC|AZURE|BEDROCK|VERTEX|OPENCODE_CONFIG|OPENCODE_MODEL|GEMINI|GOOGLE_API_KEY', k, re.I)}


def native_env(overlay=None):
    """Load installed roles while all work/state stays in the current project."""
    cfg = load(BUNDLE / 'opencode.json')
    cli = f'python "{Path(__file__).resolve().as_posix()}"'
    for agent in cfg['agent'].values():
        prompt = agent['prompt']
        if prompt.startswith('{file:'):
            agent['prompt'] = (BUNDLE / prompt[6:-1]).read_text(encoding='utf-8')
        agent['prompt'] = agent['prompt'].replace('python tool/factory.py', cli).replace('app-factory', 'store-automation')
        permission = agent['permission']
        if isinstance(permission.get('bash'), dict):
            permission['bash'].pop('python tool/factory.py *', None)
            permission['bash'][cli + ' *'] = 'allow'
        permission['skill'] = {'*': 'deny', 'store-automation': 'allow'}
    cfg['permission']['skill'] = {'*': 'deny', 'store-automation': 'allow', 'project-brain': 'allow'}
    cfg['agent']['factory']['permission']['skill']['project-brain'] = 'allow'
    cfg['permission']['external_directory'][BUNDLE.as_posix() + '/**'] = 'allow'
    for command in cfg['command'].values():
        command['template'] = command['template'].replace('python tool/factory.py', cli).replace('app-factory', 'store-automation')
    for name, agent in (overlay or {}).get('agent', {}).items():
        cfg['agent'][name]['permission'].update(agent['permission'])
    env = clean_ai_env(os.environ)
    env['OPENCODE_CONFIG_CONTENT'] = json.dumps(cfg)
    return env


def run(argv, cwd=None, timeout=300, env=None, input_text=None):
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=ROOT if cwd is None else cwd, input=input_text, capture_output=True,
                              text=True, encoding='utf-8', errors='replace',
                              timeout=timeout, env=env)
        return {'command': argv, 'exit_code': proc.returncode,
                'stdout': proc.stdout, 'stderr': proc.stderr,
                'duration_seconds': round(time.monotonic() - started, 2)}
    except subprocess.TimeoutExpired as error:
        def partial(value):
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')
        return {'command': argv, 'exit_code': 124, 'stdout': partial(error.stdout),
                'stderr': partial(error.stderr) + '\nTIMEOUT; inspect checkpoint before retry',
                'duration_seconds': round(time.monotonic() - started, 2)}


def brain_run(action, args=(), env=None):
    brain = project_dir('.project-brain')
    if any(ROOT not in path.resolve().parents for path in brain.rglob('*')):
        raise ValueError('Project Brain path escapes the selected project')
    return run([sys.executable, str(BRAIN), action, *args], env=env)


def adopt():
    """Select the caller's project, never copy the factory's history."""
    if not BRAIN.is_file():
        raise ValueError('Install project-brain before starting this workflow')
    for name in ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md', 'PROJECT_BRAIN.md', '.gitignore'):
        pointer = ROOT / name
        if pointer.is_symlink() or (hasattr(pointer, 'is_junction') and pointer.is_junction()) or (pointer.exists() and not pointer.is_file()):
            raise ValueError('Linked/non-file project instruction or ignore path refused: ' + name)
    brain = project_dir('.project-brain')
    if not brain.exists() and (ROOT / 'PROJECT_BRAIN.md').exists():
        return {'status': 'MIGRATION_REVIEW_REQUIRED', 'project_root': str(ROOT),
                'preview': brain_run('migrate'),
                'next': 'Supervisor follows Project Brain migration before implementation'}
    actions = []
    if not brain.exists():
        for action in ('map', 'init'):
            evidence = brain_run(action)
            actions.append(evidence)
            if evidence['exit_code']:
                return {'status': 'BLOCKED', 'actions': actions}
    ignore = ROOT / '.gitignore'
    if ignore.resolve() != ignore or (ignore.exists() and not ignore.is_file()):
        raise ValueError('Linked or non-file .gitignore refused')
    old = ignore.read_text(encoding='utf-8-sig') if ignore.exists() else ''
    entry = '.factory/'
    if entry not in old.splitlines():
        with ignore.open('a', encoding='utf-8') as stream:
            stream.write(('\n' if old and not old.endswith('\n') else '') + entry + '\n')
    boot = brain_run('boot')
    return {'status': 'PROJECT_LOADED' if not boot['exit_code'] else 'BLOCKED',
            'project_root': str(ROOT), 'actions': actions, 'boot': boot,
            'next': 'Supervisor reads map/manifests and records the actual goal; new target remains DRAFT'}


def validate_resume(session, contract):
    if not re.fullmatch(r'ses_[A-Za-z0-9]+', session):
        raise ValueError('Invalid native session ID')
    records = project_dir('.factory/runs')
    for path in records.glob('live-*.json'):
        if path.resolve().parent != records:
            raise ValueError('Linked execution evidence refused')
        data = load(path)
        if (data.get('project') == str(ROOT) and data.get('contract_sha256') == digest_file(contract)
                and session in data.get('native_sessions', []) and data.get('state') in ('FINISHED', 'FAILED', 'TIMEOUT', 'INTERRUPTED')):
            return
    raise ValueError('Resume requires this project and exact contract execution provenance; use a fresh Brain handoff')


def classify(result):
    if result['exit_code'] == 124:
        return 'TIMEOUT'
    output = result.get('stdout', '') + result.get('stderr', '')
    # OpenCode can emit an error event and still exit zero.
    error_event = any('"type":"error"' in line.replace(' ', '') for line in output.splitlines())
    if result['exit_code'] == 0 and not error_event:
        return 'SUCCESS'
    # ponytail: error-text matching is heuristic; use structured provider codes when CLI schemas stabilize.
    for label, pattern in [('QUOTA_EXHAUSTED', 'quota|usage limit'),
                           ('RATE_LIMIT', r'rate.?limit|(?:http|status|error)[^\n]{0,40}\b429\b'),
                           ('AUTH_ERROR', r'unauthorized|authentication|(?:http|status|error)[^\n]{0,40}\b401\b'),
                           ('MODEL_UNAVAILABLE', r'model.*not found|model.*unavailable|UpgradeRequired|(?:http|status|error)[^\n]{0,40}\b(?:426|404)\b')]:
        if re.search(pattern, output, re.I):
            return label
    return 'UNKNOWN_FAILURE'


def fallback_run(primary, alternative, invoke, checkpoint):
    """Availability fallback only; caller verifies a checkpoint before a fresh session."""
    if primary not in FREE_MODELS or alternative not in FREE_MODELS or primary == alternative:
        raise ValueError('Fallback requires two different verified free models')
    first = invoke(primary)
    status = classify(first)
    if status not in ('QUOTA_EXHAUSTED', 'RATE_LIMIT', 'MODEL_UNAVAILABLE', 'TIMEOUT'):
        return {'classification': status, 'attempts': [first], 'task_result': task_result(first)}
    try:
        checkpoint()
        second = invoke(alternative)
    except (ValueError, RuntimeError, OSError) as error:
        return {'classification': 'BLOCKED', 'attempts': [first], 'reason': str(error)}
    return {'classification': classify(second), 'attempts': [first, second],
            'task_result': task_result(second),
            'fallback_from': primary, 'fallback_to': alternative}


def task_result(result):
    """Transport exit success is separate from an agent's task verdict."""
    final = ''
    for line in result.get('stdout', '').splitlines():
        try:
            event = json.loads(line)
            if event.get('type') == 'text':
                final = event.get('part', {}).get('text', '')
            if event.get('type') == 'item.completed' and event.get('item', {}).get('type') == 'agent_message':
                final = event['item']['text']
        except (ValueError, TypeError):
            continue
    match = re.search(r'```json\s*([\s\S]*?)```', final)
    candidate = match.group(1) if match else final
    try:
        data = json.loads(candidate)
    except ValueError:
        try:
            data = json.loads(candidate.replace('\\n', '\n'))
        except ValueError:
            return {'status': 'UNVERIFIED', 'final_text': final}
    return data if isinstance(data, dict) else {'status': 'UNVERIFIED'}


def model_run(provider, prompt, contract, timeout=300, session=None, visible=False):
    lock = project_dir('.factory') / 'dispatch.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    # ponytail: one project lock serializes its tasks; cross-project scheduling remains supervisor-owned.
    try:
        stream = lock.open('x', encoding='utf-8')
    except FileExistsError:
        raise RuntimeError('Dispatch already active; after a crash inspect the recorded PID before removing its lock')
    release = True
    try:
        with stream:
            stream.write(str(os.getpid()))
            stream.flush()
            return _model_run(provider, prompt, contract, timeout, session, visible)
    except sessions.ContainmentError:
        release = False
        raise
    finally:
        if release and lock.exists() and lock.read_text(encoding='utf-8') == str(os.getpid()):
            lock.unlink()


def _model_run(provider, prompt, contract, timeout=300, session=None, visible=False):
    env = clean_ai_env(os.environ)
    contract = trusted_input(contract, '.json')
    task = validate_contract(load(contract))
    registry = load(BUNDLE / 'contracts/capabilities.json')['models']
    if provider not in registry or not set(task['required_capabilities']).issubset(registry[provider]['verified']):
        raise ValueError('Model unavailable or lacks required verified capability; do not guess vision support')
    if provider in FREE_MODELS and registry[provider].get('access') not in (
            'native_free', 'native_free_requires_OpenCode_1.18.0'):
        raise ValueError('Registry no longer approves this free model; revalidate access before dispatch')
    if provider == 'codex':
        binary = executable('codex')
        auth = run([binary, 'login', 'status'], env=env)
        if auth['exit_code'] or 'ChatGPT' not in auth['stdout'] + auth['stderr']:
            raise RuntimeError('BLOCKED: official Codex ChatGPT login required; API login refused')
        argv = [binary, 'exec', '--ignore-user-config', '--ignore-rules',
                '-c', 'forced_login_method="chatgpt"', '--sandbox', 'read-only', '--json', '-']
        if session:
            raise ValueError('Use a fresh official CLI Brain handoff, not incompatible session ID')
        snapshots = []
        for name in task['context']:
            path = snapshot_path(name)
            snapshots.append({'path': name, 'sha256': digest_file(path),
                              'content': path.read_text(encoding='utf-8-sig')})
        if visible:
            raise ValueError('Codex handoff streams activity; interactive panes require its native host, not OpenCode attach')
        result = sessions.stream_run(argv, ROOT, env, timeout=timeout,
                   metadata={'provider': provider, 'task_id': task['task_id'], 'role': task['persona']['role']},
                   emit=lambda event: print(json.dumps(event), file=sys.stderr, flush=True),
                   input_text=prompt + '\nValidated task contract:\n' + json.dumps(task) +
                   '\nExact read-only source snapshots captured by the runner. Verify these; '
                   'do not execute shell or reimplement. Parent rechecks hashes before acceptance.\n' +
                   json.dumps(snapshots, ensure_ascii=False))
        result['source_snapshots'] = [{'path': item['path'], 'sha256': item['sha256']} for item in snapshots]
        return result
    if provider not in FREE_MODELS:
        raise ValueError('Paid/unverified model refused; choose an explicit free allowlisted model')
    env = native_env(worker_permissions(task))
    boot = brain_run('boot', env=env)
    if boot['exit_code']:
        raise RuntimeError('Project Brain boot failed before native dispatch')
    prompt = ('Runner already executed this session Project Brain boot; use this '
              'exact startup evidence. Do not call any shell tools during this dispatch; '
              'they are denied. Delegate only via native task.\n' + boot['stdout'] + '\n' + prompt)
    argv = [executable('opencode'), '--pure', 'run', '--model', provider,
            '--agent', 'factory', '--format', 'json', '--file', str(Path(contract).resolve())]
    if session:
        validate_resume(session, contract)
        argv += ['--session', session]
    metadata = {'provider': 'opencode', 'model': provider, 'task_id': task['task_id'],
                'role': task['persona']['role'], 'contract_sha256': digest_file(contract)}
    server = None
    def activity(event):
        print(json.dumps(event), file=sys.stderr, flush=True)
    try:
        if visible:
            env['OPENCODE_SERVER_PASSWORD'] = secrets.token_urlsafe(32)
            server = sessions.start(ROOT, executable('opencode'), env)
            sessions.validate_config(server, env)
            if session:
                server['resume_sessions'] = [session]
                sessions.store(ROOT, server)
            argv += ['--attach', server['url']]
            watcher = [sys.executable, str(BUNDLE / 'tool/sessions.py'), 'watch', '--project', str(ROOT), '--auto-panes']
            subprocess.run(sessions.terminal_command(ROOT, watcher), env=env, check=True)
        argv += ['--', prompt]
        return sessions.stream_run(argv, ROOT, env, timeout=timeout, metadata=metadata, emit=activity)
    finally:
        if server:
            try:
                sessions.stop(ROOT)
            except Exception as error:
                raise sessions.ContainmentError('Visible server cleanup is unverified; reconcile before dispatch') from error


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_digest(root):
    root = Path(root).resolve()
    top = run(['git', 'rev-parse', '--show-toplevel'], cwd=root)
    if top['exit_code'] or Path(top['stdout'].strip()).resolve() != root:
        raise ValueError('Evidence source must have its own Git workspace root')
    result = run(['git', 'ls-files', '-co', '--exclude-standard', '-z'], cwd=root)
    if result['exit_code']:
        raise ValueError('Evidence source must be a Git workspace')
    # ponytail: full tracked source scan is O(bytes); use Git tree + dirty delta for large repos.
    digest = hashlib.sha256()
    for name in sorted(set(result['stdout'].split('\0')) - {''}):
        if name.startswith(('.factory/', 'docs/evidence/')):
            continue
        if not name.endswith('.example') and re.search(
                r'(^|/)(?:\.env(?:\.[^/]+)?|auth\.json|credentials?\.json|service-account[^/]*\.json|key\.properties|id_rsa|id_ed25519)$|\.(?:jks|p8|p12|pfx|pem)$|(^|/)credentials?/', name, re.I):
            raise ValueError('Credential path must be outside tracked/unignored source before verification: ' + name)
        path = root / name
        if path.resolve() != path.absolute():
            raise ValueError('Linked source must be replaced by regular project files before verification: ' + name)
        if path.is_file():
            digest.update(name.encode())
            digest.update(bytes.fromhex(digest_file(path)))
    return digest.hexdigest()


def verification_commands(profile, build=False):
    if profile == 'factory':
        if ROOT != BUNDLE:
            raise ValueError('Factory verification is only for the tool source; application tasks use flutter')
        if build:
            raise ValueError('Factory profile has no mobile build')
        return {'unit': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                'syntax': [sys.executable, '-m', 'py_compile', 'tool/factory.py'],
                'discovery': [executable('opencode'), '--pure', 'debug', 'agent', 'factory']}
    if profile == 'flutter':
        return {'format': [executable('dart'), 'format', '--output=none', '--set-exit-if-changed', 'lib', 'test'],
                'analyze': [executable('flutter'), 'analyze', '--fatal-infos'],
                'test': [executable('flutter'), 'test'],
                **({'build': [executable('flutter'), 'build', 'apk', '--release']} if build else {})}
    raise ValueError('Unknown verification profile')


def check(root, contract, worker_session, output):
    contract = trusted_input(contract, '.json')
    task = validate_contract(load(contract))
    policy = task.get('verification', {})
    profile, build = policy.get('profile'), policy.get('build')
    if not isinstance(build, bool):
        raise ValueError('Contract verification requires a profile and boolean build')
    task_id = task['task_id']
    root = Path(root).resolve()
    if root != ROOT and project_dir('.factory/workspaces') not in root.parents:
        raise ValueError('Checks must target the factory or its generated workspaces')
    if not worker_session or not project_dir('.project-brain/tasks/' + task_id + '.md').is_file():
        raise ValueError('Existing task and worker session required')
    output = Path(output).resolve()
    if project_dir('.factory/runs') not in output.parents or output.exists():
        raise ValueError('Use a NEW evidence path inside .factory/runs')
    before = source_digest(root)
    checks = []
    for name, argv in verification_commands(profile, build).items():
        result = run(argv, cwd=root, timeout=1800 if name == 'build' else 600, env=clean_ai_env(os.environ))
        result.update({'cwd': str(root), 'source_digest': before})
        log = output.parent / (output.stem + '-' + name + '.json')
        save(log, result)
        checks.append({'name': name, 'command': argv, 'exit_code': result['exit_code'],
                       'log': str(log), 'sha256': digest_file(log)})
        if result['exit_code']:
            break
    artifacts = []
    if build:
        artifact = root / 'build/app/outputs/flutter-apk/app-release.apk'
        if artifact.is_file():
            artifacts.append({'path': str(artifact), 'sha256': digest_file(artifact)})
    evidence = {'task_id': task_id, 'worker_session': worker_session, 'profile': profile,
                'contract_sha256': digest_file(contract),
                'source_digest': before, 'checks': checks, 'artifacts': artifacts,
                'status': 'PASS' if source_digest(root) == before and
                len(checks) == len(verification_commands(profile, build)) and
                all(c['exit_code'] == 0 for c in checks) else 'REWORK_REQUIRED'}
    save(output, evidence)
    return evidence


def evidence_gate(root, evidence, review, contract):
    root = Path(root).resolve()
    if root != ROOT and project_dir('.factory/workspaces') not in root.parents:
        raise ValueError('Evidence must target the factory or its generated workspaces')
    contract = trusted_input(contract, '.json')
    task = validate_contract(load(contract))
    required = task.get('verification', {})
    require_build = required.get('build')
    if not isinstance(require_build, bool) or required.get('profile') != evidence.get('profile'):
        raise ValueError('Missing or mismatched contract verification policy')
    if evidence.get('contract_sha256') != digest_file(contract) or evidence.get('task_id') != task['task_id']:
        raise ValueError('Evidence belongs to another task contract')
    if evidence.get('source_digest') != source_digest(root):
        raise ValueError('Stale source evidence')
    if not evidence.get('checks') or any(c.get('exit_code') != 0 for c in evidence['checks']):
        raise ValueError('Missing or failed machine checks')
    expected = verification_commands(evidence.get('profile'), require_build)
    if {c.get('name') for c in evidence['checks']} != set(expected):
        raise ValueError('Missing mandatory verification commands')
    for checked in evidence['checks']:
        log = trusted_input(checked.get('log', ''), '.json', '.factory/runs')
        if not log.is_file() or digest_file(log) != checked.get('sha256'):
            raise ValueError('Missing or changed machine log')
        recorded = load(log)
        if checked.get('command') != expected[checked['name']] or recorded.get('command') != checked['command'] or recorded.get('exit_code') != 0:
            raise ValueError('Machine log does not prove the required check')
        if recorded.get('cwd') != str(Path(root).resolve()) or recorded.get('source_digest') != evidence['source_digest']:
            raise ValueError('Machine log belongs to another source/workspace')
    for artifact in evidence.get('artifacts', []):
        path = Path(artifact['path']).resolve()
        if root not in path.parents:
            raise ValueError('Artifact escapes the verified workspace')
        if not path.is_file() or digest_file(path) != artifact['sha256']:
            raise ValueError('Missing or changed artifact')
    if require_build and not evidence.get('artifacts'):
        raise ValueError('Build artifact required')
    if require_build and {Path(a['path']).resolve() for a in evidence['artifacts']} != {
            Path(root).resolve() / 'build/app/outputs/flutter-apk/app-release.apk'}:
        raise ValueError('Expected verified Flutter release APK required')
    if review.get('verdict') != 'PASS' or review.get('findings') != []:
        raise ValueError('Independent review is not PASS')
    for field in ('task_id', 'source_digest', 'contract_sha256', 'worker_session'):
        if not evidence.get(field) or review.get(field) != evidence[field]:
            raise ValueError('Review must refer to this task/source/worker')
    if not review.get('reviewer_session') or review['reviewer_session'] == evidence['worker_session']:
        raise ValueError('Review must use a fresh independent session')
    if not re.fullmatch(r'ses_[A-Za-z0-9]+', review['reviewer_session']):
        raise ValueError('Review requires a native reviewer session')
    exported = run([executable('opencode'), '--pure', 'export', review['reviewer_session']],
                   env=clean_ai_env(os.environ))
    if exported['exit_code']:
        raise ValueError('Native reviewer session unavailable')
    session = json.loads(exported['stdout'])
    info = session.get('info', {})
    if info.get('id') != review['reviewer_session'] or info.get('agent') != 'factory-reviewer' or not info.get('parentID'):
        raise ValueError('Review does not belong to an independent native reviewer')
    parts = [p for m in session.get('messages', []) if m.get('info', {}).get('role') == 'assistant'
             for p in m.get('parts', [])]
    if any(p.get('type') == 'tool' and p.get('tool') not in ('read', 'glob', 'list', 'skill') for p in parts):
        raise ValueError('Reviewer used a forbidden tool')
    verdict = task_result({'stdout': '\n'.join(json.dumps({'type': 'text', 'part': p})
                          for p in parts if p.get('type') == 'text')})
    if any(verdict.get(k) != review.get(k) for k in (
            'task_id', 'source_digest', 'contract_sha256', 'worker_session', 'verdict', 'findings')):
        raise ValueError('Review JSON is not the recorded native reviewer verdict')
    return {'status': 'ACCEPTABLE', 'task_id': evidence['task_id'],
            'source_digest': evidence['source_digest'], 'reviewer_session': review['reviewer_session']}


def bootstrap(destination, name, package, ads, pro):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Bootstrap only into a NEW explicitly selected project directory')
    if any(p.isspace() for p in package) or not re.fullmatch(r'[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+', package):
        raise ValueError('Invalid Android/iOS package')
    destination.mkdir(parents=True)
    archive = run(['git', 'archive', '--format=zip', 'HEAD', '-o', str(destination / 'starter.zip')], cwd=STARTER)
    if archive['exit_code']:
        raise RuntimeError('Starter archive failed')
    with zipfile.ZipFile(destination / 'starter.zip') as source:
        # A starter's plan/history is not the new product's Project Brain.
        source.extractall(destination, [name for name in source.namelist()
                                       if not name.startswith('.project-brain/') and name != 'PROJECT_BRAIN.md'])
    (destination / 'starter.zip').unlink()
    subprocess.run(['git', 'init'], cwd=destination, check=True, capture_output=True)
    brain = run([sys.executable, str(BRAIN), 'init'], cwd=destination)
    if brain['exit_code']:
        raise RuntimeError('New project Brain initialization failed; preserve workspace for inspection')
    argv = [executable('dart'), 'run', 'tool/new_app.dart', '--name', name,
            '--package', package, '--ads', ads, '--pro', pro, '--data', 'local',
            '--kit-path', KIT.as_posix(), '--force']
    result = run(argv, cwd=destination, timeout=1800)
    legacy = destination / 'PROJECT_BRAIN.md'
    provenance = {'starter_commit': run(['git', 'rev-parse', 'HEAD'], cwd=STARTER)['stdout'].strip(),
                  'kit_commit': run(['git', 'rev-parse', 'HEAD'], cwd=KIT)['stdout'].strip(),
                  'project_root': str(destination), 'brain_init': brain,
                  'generated_legacy_brain': legacy.read_text(encoding='utf-8') if legacy.is_file() else None,
                  'kit_local_development': True, 'result': result,
                  'status': 'VERIFIED_LOCAL' if not result['exit_code'] else 'BLOCKED'}
    save(destination / '.factory-bootstrap.json', provenance)
    if not result['exit_code']:
        # Owned new skeleton: preserve generator notes above, keep only canonical Brain.
        if legacy.is_file():
            legacy.unlink()
        config = destination / '.project-brain/config.yaml'
        text = config.read_text(encoding='utf-8')
        text = re.sub(r"(?m)^  (test|lint|build):.*$", lambda m: '  ' + m[1] + ': ' + {
            'test': 'flutter test', 'lint': 'flutter analyze --fatal-infos',
            'build': 'flutter build apk --release'}[m[1]], text)
        config.write_text(text, encoding='utf-8')
    return provenance


def audit():
    cfg = load(BUNDLE / 'opencode.json')
    registry = load(BUNDLE / 'contracts/capabilities.json')['models']
    paid = cfg.get('enabled_providers') != ['opencode'] or set(
        cfg.get('provider', {}).get('opencode', {}).get('whitelist', [])) != {
            model.split('/', 1)[1] for model in FREE_MODELS} or any(
                cfg.get(key) not in FREE_MODELS for key in ('model', 'small_model')) or any(
                    registry.get(model, {}).get('access') not in ('native_free', 'native_free_requires_OpenCode_1.18.0')
                    for model in FREE_MODELS)
    return {'status': 'REWORK_REQUIRED' if paid else 'PASS', 'model': cfg['model'], 'free_allowlist': FREE_MODELS,
            'agents': list(cfg['agent']), 'enabled_providers': cfg['enabled_providers'],
            'project_root': str(ROOT), 'runtime_root': str(BUNDLE),
            'brain_exists': (ROOT / '.project-brain').is_dir(), 'brain_skill_exists': BRAIN.is_file(),
            'publishing_protocol_exists': Path('D:/AppPublishing/README.md').is_file(),
            'skills_scoped': {name: agent.get('permission', {}).get('skill', cfg['permission']['skill'])
                              for name, agent in cfg['agent'].items()},
            'global_skills_deleted': 'not measured by config audit', 'paid_api_enabled': paid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('audit')
    commands.add_parser('open')
    starter = commands.add_parser('start')
    starter.add_argument('--host', choices=['opencode', 'codex'], default='opencode')
    starter.add_argument('goal', nargs='*')
    commands.add_parser('adopt')
    commands.add_parser('activity')
    commands.add_parser('providers')
    native = commands.add_parser('sessions')
    native.add_argument('action', choices=['start', 'status', 'watch', 'attach', 'stop'])
    native.add_argument('--session')
    native.add_argument('--pane', action='store_true')
    native.add_argument('--contract')
    router = commands.add_parser('route')
    router.add_argument('--contract', required=True)
    router.add_argument('--complexity', choices=['SIMPLE', 'STANDARD', 'COMPLEX', 'SPECIALIZED'], default='STANDARD')
    for name in ('contract', 'digest'):
        commands.add_parser(name).add_argument('path')
    release = commands.add_parser('release-preflight')
    release.add_argument('path')
    release.add_argument('--publishing-root', default='D:/AppPublishing')
    release.add_argument('--app-id', required=True)
    release.add_argument('--platform', choices=['android', 'ios'], action='append', required=True)
    release.add_argument('--locale', action='append', required=True)
    brain = commands.add_parser('brain')
    brain.add_argument('action', choices=['boot', 'validate', 'map', 'new'])
    brain.add_argument('args', nargs='*')
    runner = commands.add_parser('run')
    runner.add_argument('--provider', choices=[*FREE_MODELS, 'codex'], required=True)
    runner.add_argument('--contract', required=True)
    runner.add_argument('--prompt-file', required=True)
    runner.add_argument('--output', required=True)
    runner.add_argument('--timeout', type=int, default=300)
    runner.add_argument('--session')
    runner.add_argument('--visible', action='store_true', help='Actual OpenCode session panes; Windows Terminal required')
    runner.add_argument('--fallback', choices=FREE_MODELS)
    gate = commands.add_parser('gate')
    gate.add_argument('--root', default=str(ROOT))
    gate.add_argument('--evidence', required=True)
    gate.add_argument('--review', required=True)
    gate.add_argument('--contract', required=True)
    checker = commands.add_parser('check')
    checker.add_argument('--root', default=str(ROOT))
    checker.add_argument('--contract', required=True)
    checker.add_argument('--worker-session', required=True)
    checker.add_argument('--output', required=True)
    boot = commands.add_parser('bootstrap')
    boot.add_argument('destination')
    boot.add_argument('--name', required=True)
    boot.add_argument('--package', required=True)
    boot.add_argument('--ads', choices=['yes', 'no'], default='no')
    boot.add_argument('--pro', choices=['yes', 'no'], default='no')
    args = parser.parse_args(sys.argv[1:] or ['start'])
    if args.command == 'audit':
        result = audit()
    elif args.command in ('open', 'start'):
        prompt = None
        if args.command == 'start':
            adopted = adopt()
            print(json.dumps(adopted, ensure_ascii=False, indent=2), flush=True)
            if adopted['status'] == 'BLOCKED':
                return 1
            prompt = ('Use $store-automation and canonical project-brain in this selected project. '
                      'Inspect current state and existing callers before planning. Resume the recorded '
                      'goal if confirmed; otherwise adopt/map the existing project and record only the '
                      'actual user goal. Never import another project history. Give each task a detailed '
                      'persona and least sufficient verified model, with quality gates and fresh review. '
                      'Expose real agent sessions/status for user intervention. '
                      + ('User goal: ' + ' '.join(args.goal) if args.goal else
                         'No new product goal supplied: inspect and report verified state, then resume only confirmed work.'))
            if args.host == 'codex':
                return subprocess.call([executable('codex'), '-c', 'forced_login_method="chatgpt"',
                                        '-C', str(ROOT), prompt], cwd=ROOT, env=clean_ai_env(os.environ))
        argv = [executable('opencode'), '--pure', '--agent', 'factory', str(ROOT)]
        if prompt:
            argv += ['--prompt', prompt]
        return subprocess.call(argv,
                               cwd=ROOT, env=native_env())
    elif args.command == 'adopt':
        result = adopt()
    elif args.command == 'activity':
        records = []
        for path in sorted(project_dir('.factory/runs').glob('live-*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            if path.resolve().parent != project_dir('.factory/runs'):
                raise ValueError('Linked execution evidence refused')
            data = load(path)
            if data.get('project') != str(ROOT):
                raise ValueError('Execution evidence belongs to another project')
            records.append(data)
        result = {'project_root': str(ROOT), 'runs': records, 'quota_remaining': None}
    elif args.command == 'providers':
        login = {'codex': 'codex login', 'claude': 'claude auth login', 'gemini': 'gemini (Login with Google)',
                 'mcode': 'mcode login --region global', 'qwen': 'Verify current Coding Plan route',
                 'agy': 'Use official Antigravity account setup', 'opencode': 'opencode providers',
                 'gh': 'gh auth login --web'}
        result = {'providers': [{'cli': name, 'installed': shutil.which(name) is not None,
                                 'access': 'NOT_PROBED', 'login': command} for name, command in login.items()],
                  'measured_routes': load(BUNDLE / 'contracts/capabilities.json'),
                  'policy': 'Presence is not authentication/entitlement/inference proof; official subscription login only',
                  'glm': 'Official ZCode account route; no verified headless adapter', 'quota_remaining': None}
    elif args.command == 'sessions':
        overlay = worker_permissions(validate_contract(load(trusted_input(args.contract, '.json')))) if args.contract else None
        result = sessions.handle(args.action, ROOT, executable('opencode'), native_env(overlay), args.session, args.pane)
    elif args.command == 'route':
        task = validate_contract(load(trusted_input(args.contract, '.json')))
        registry = load(BUNDLE / 'contracts/capabilities.json')
        candidates = [model for model in registry['routing'][args.complexity]
                      if set(task['required_capabilities']).issubset(registry['models'][model]['verified'])]
        result = {'status': 'CANDIDATES_REQUIRE_GATES' if candidates else 'BLOCKED',
                  'candidates': candidates, 'complexity': args.complexity,
                  'required_capabilities': task['required_capabilities'],
                  'first_action': 'Use deterministic tools if acceptance needs no judgment' if args.complexity == 'SIMPLE' else
                                  'Select lowest sufficient verified capability; do not lower quality floor',
                  'quality_gates': ['contract', 'machine verification', 'fresh independent review'],
                  'subscription_quota_remaining': None}
    elif args.command == 'contract':
        result = {'status': 'VALID', 'task_id': validate_contract(load(trusted_input(args.path, '.json')))['task_id']}
    elif args.command == 'digest':
        result = {'source_digest': source_digest(args.path)}
    elif args.command == 'brain':
        if args.action == 'new':
            if len(args.args) < 2 or args.args[0] != '.' or any(v == '--root' for v in args.args):
                raise ValueError('Brain new must target this workspace using . and a title')
        elif args.args:
            raise ValueError('Brain read/validation commands target this workspace only')
        result = brain_run(args.action, args.args)
    elif args.command == 'run':
        output = Path(args.output).resolve()
        if project_dir('.factory/runs') not in output.parents or output.suffix != '.json':
            raise ValueError('Run outputs must stay under .factory/runs and use .json')
        if output.exists():
            raise ValueError('Existing run evidence will not be overwritten')
        prompt = trusted_input(args.prompt_file, '.txt').read_text(encoding='utf-8')
        if args.fallback:
            task = validate_contract(load(trusted_input(args.contract, '.json')))
            roots = {ROOT, *(ROOT.joinpath(*Path(scope).parts[:3]) for scope in task['scope']
                             if scope.startswith('.factory/workspaces/'))}
            initial = {str(root): source_digest(root) for root in roots}
            def checkpoint():
                boot = brain_run('boot')
                if boot['exit_code'] or {str(root): source_digest(root) for root in roots} != initial:
                    raise RuntimeError('BLOCKED: reconcile changed source before model fallback')
            result = fallback_run(args.provider, args.fallback,
                                  lambda provider: model_run(provider, prompt, args.contract, args.timeout, visible=args.visible),
                                  checkpoint)
        else:
            result = model_run(args.provider, prompt, args.contract, args.timeout, args.session, visible=args.visible)
            result['classification'] = classify(result)
            result['task_result'] = task_result(result)
        save(args.output, result)
    elif args.command == 'gate':
        result = evidence_gate(args.root,
                               load(trusted_input(args.evidence, '.json', '.factory/runs')),
                               load(trusted_input(args.review, '.json', '.factory/runs')), args.contract)
    elif args.command == 'check':
        result = check(args.root, args.contract, args.worker_session, args.output)
    elif args.command == 'bootstrap':
        result = bootstrap(args.destination, args.name, args.package, args.ads, args.pro)
    else:
        try:
            from .release import preflight
        except ImportError:
            from release import preflight
        result = preflight(args.path, args.publishing_root, args.app_id, args.platform, args.locale)
    printed = result
    if args.command == 'run':
        printed = {k: v for k, v in result.items() if k not in ('stdout', 'stderr', 'attempts')}
        printed['evidence_path'] = str(Path(args.output).resolve())
    print(json.dumps(printed, ensure_ascii=False, indent=2))
    if result.get('exit_code', 0) or result.get('classification', 'SUCCESS') != 'SUCCESS' or result.get('status') in ('BLOCKED', 'REWORK_REQUIRED') or result.get('task_result', {}).get('status') in ('BLOCKED', 'REWORK_REQUIRED', 'FAILED', 'FAIL', 'UNVERIFIED') or result.get('task_result', {}).get('verdict') in ('FAIL', 'REWORK_REQUIRED', 'BLOCKED'):
        return 1
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(error)}, ensure_ascii=False))
        sys.exit(1)
