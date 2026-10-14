"""Offline model evidence and user access registry. Agents fetch sources; this module never calls APIs."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

from . import plan
from .paths import public_path

ROLES = ('implement', 'plan', 'review')
KINDS = ('subscription', 'free_api', 'paid_api')
RANK = {'UNKNOWN': -1, 'L': 0, 'M': 1, 'H': 2}
DEFAULT = Path.home() / '.store-automation' / 'models.json'


def now():
    return datetime.now(timezone.utc)


def stamp(value):
    text(value)
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None or date > now() + timedelta(minutes=5):
        raise ValueError('Dates need a timezone and must not be in the future')
    return date


def fresh(value, seconds):
    return bool(value) and (now() - stamp(value)).total_seconds() < seconds


def number(value, ceiling=None):
    if type(value) not in (int, float) or not 0 <= value <= 1e18 or not math.isfinite(value) or (
            ceiling is not None and value > ceiling):
        raise ValueError('Expected a finite nonnegative number within bounds')


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 1000 or any(
            ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Expected nonempty printable text (at most 1000 characters)')


def source(value):
    text(value)
    url = urlsplit(value)
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('Source must be a public HTTPS URL without credentials')


def shape(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError('Invalid fields; expected ' + ', '.join(required))


def boolean(value):
    if type(value) is not bool:
        raise ValueError('Expected a boolean')


def identity(value):
    text(value)
    if plan.agent_id(value, 'registry id') != value:
        raise ValueError('Registry ids must not have leading/trailing whitespace')


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except RecursionError as exc:
        raise ValueError('Model JSON nesting is too deep') from exc


def validate(data):
    shape(data, ('schema', 'enforce', 'benchmarks', 'pools', 'models'))
    if type(data['schema']) is not int or data['schema'] != 1:
        raise ValueError('Unsupported model registry schema')
    boolean(data['enforce'])
    for key in ('benchmarks', 'pools', 'models'):
        if not isinstance(data[key], dict) or len(data[key]) > 2000:
            raise ValueError(key + ' must be a mapping with at most 2000 entries')
        for name in data[key]:
            identity(name)
    for b in data['benchmarks'].values():
        shape(b, ('name', 'version', 'harness', 'effort', 'dimension', 'source', 'checked_at',
                  'observed_at', 'reference_model', 'reference_score', 'h_min', 'm_min', 'rationale', 'independent'))
        for k in ('name', 'version', 'harness', 'effort', 'reference_model', 'rationale'):
            text(b[k])
        source(b['source'])
        if b['dimension'] not in ('coding', 'reasoning'):
            raise ValueError('Benchmark dimension must be coding or reasoning')
        boolean(b['independent'])
        if stamp(b['observed_at']) > stamp(b['checked_at']):
            raise ValueError('Benchmark observation is newer than its check')
        for k in ('reference_score', 'h_min', 'm_min'):
            number(b[k])
        if not 0 < b['m_min'] < b['h_min'] <= b['reference_score']:
            raise ValueError('Thresholds need 0 < M < H <= external reference score')
    for p in data['pools'].values():
        shape(p, ('kind', 'allowed', 'checked_at', 'source', 'windows'))
        if p['kind'] not in KINDS:
            raise ValueError('Unknown access kind')
        boolean(p['allowed'])
        stamp(p['checked_at'])
        text(p['source'])  # Native host tools may be the source, not a website.
        if not isinstance(p['windows'], list):
            raise ValueError('Quota windows must be a list; [] means unknown')
        for w in p['windows']:
            shape(w, ('remaining', 'resets_at'))
            number(w['remaining'], 100)
            text(w['resets_at'])
            stamp_reset = datetime.fromisoformat(w['resets_at'].replace('Z', '+00:00'))
            if stamp_reset.tzinfo is None:
                raise ValueError('Quota reset needs a timezone')
    aliases = set()
    access_ids = set()
    for name, m in data['models'].items():
        shape(m, ('effort', 'aliases', 'results', 'accesses'), ('overrides', 'research', 'usage_estimate'))
        text(m['effort'])
        if not isinstance(m['aliases'], list):
            raise ValueError('Aliases must be a list')
        for alias in [name, *m['aliases']]:
            identity(alias)
            if alias.casefold() in aliases:
                raise ValueError('Duplicate model id or alias: ' + alias)
            aliases.add(alias.casefold())
        if not isinstance(m['results'], dict):
            raise ValueError('Results must be a mapping')
        for key, r in m['results'].items():
            if key not in data['benchmarks']:
                raise ValueError('Unknown benchmark: ' + key)
            shape(r, ('score', 'source', 'checked_at'))
            number(r['score'])
            source(r['source'])
            stamp(r['checked_at'])
        if not isinstance(m.get('overrides', {}), dict):
            raise ValueError('Overrides must be a mapping')
        for role, o in m.get('overrides', {}).items():
            shape(o, ('tier', 'reason', 'checked_at'))
            if role not in ROLES or o['tier'] not in ('L', 'M', 'H'):
                raise ValueError('Invalid user override')
            text(o['reason'])
            stamp(o['checked_at'])
        if 'research' in m:
            shape(m['research'], ('retry_after', 'error'))
            text(m['research']['error'])
            text(m['research']['retry_after'])
            retry = datetime.fromisoformat(m['research']['retry_after'].replace('Z', '+00:00'))
            if retry.tzinfo is None:
                raise ValueError('Research retry needs a timezone')
        if 'usage_estimate' in m:
            estimate = m['usage_estimate']
            shape(estimate, ('workload', 'output_tokens_per_task', 'usd_per_task', 'source', 'checked_at'))
            text(estimate['workload'])
            source(estimate['source'])
            stamp(estimate['checked_at'])
            for k in ('output_tokens_per_task', 'usd_per_task'):
                if estimate[k] is not None:
                    number(estimate[k])
        if not isinstance(m['accesses'], list):
            raise ValueError('Accesses must be a list')
        for a in m['accesses']:
            shape(a, ('id', 'pool', 'host', 'effort', 'allowed', 'available', 'checked_at', 'source',
                      'context', 'tools', 'input_price', 'output_price'), ('metrics',))
            identity(a['id'])
            if a['id'].casefold() in access_ids or a['pool'] not in data['pools']:
                raise ValueError('Duplicate access id or unknown pool')
            access_ids.add(a['id'].casefold())
            for k in ('host', 'effort', 'source'):
                text(a[k])
            if a['effort'] != m['effort']:
                raise ValueError('Access effort must match its model profile')
            for k in ('allowed', 'available'):
                boolean(a[k])
            stamp(a['checked_at'])
            if a['context'] is not None:
                number(a['context'])
            if not isinstance(a['tools'], list) or any(not isinstance(t, str) or not t for t in a['tools']):
                raise ValueError('Tools must be a list of names')
            for k in ('input_price', 'output_price'):
                if a[k] is not None:
                    number(a[k])
            if 'metrics' in a:
                v = a['metrics']
                shape(v, ('task_class', 'samples', 'complete', 'checked_at', 'source',
                          'tokens_per_accepted', 'usd_per_accepted'))
                text(v['task_class'])
                text(v['source'])
                boolean(v['complete'])
                stamp(v['checked_at'])
                if type(v['samples']) is not int or v['samples'] < 1:
                    raise ValueError('Metrics need a positive integer sample count')
                for k in ('tokens_per_accepted', 'usd_per_accepted'):
                    if v[k] is not None:
                        number(v[k])
    return data


def registry_path(path=None):
    path = Path(path or DEFAULT).absolute()
    # Reuse the project path boundary: reject junctions/symlinks, private filenames and Windows aliases.
    return public_path(path.parent, path.name)


def load(path=None):
    path = registry_path(path)
    exists = path.exists()
    raw = b''
    if exists:
        with path.open('rb') as stream:
            raw = stream.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError('Model registry exceeds 4 MB')
    data = parse(raw.decode('utf-8-sig')) if exists else {
        'schema': 1, 'enforce': False, 'benchmarks': {}, 'pools': {}, 'models': {}}
    return validate(data), hashlib.sha256(raw).hexdigest()


def merge(path, patch, revision):
    shape(patch, (), ('benchmarks', 'pools', 'models', 'enforce'))
    path = registry_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with plan.checkout_lock(path.parent):
        data, current = load(path)
        if current != revision:
            raise ValueError('Registry changed: list again and merge against its new revision')
        for key in ('benchmarks', 'pools', 'models'):
            if key in patch:
                if not isinstance(patch[key], dict):
                    raise ValueError(key + ' must be a mapping')
                data[key].update(patch[key])
        if 'enforce' in patch:
            data['enforce'] = patch['enforce']
        validate(data)
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + '\n'
        if len(encoded.encode('utf-8')) > 4_000_000:
            raise ValueError('Model registry exceeds 4 MB')
        public_path(path.parent, path.name + '.tmp')
        plan.write_atomic(path, encoded)
    return load(path)


def assessment(data, name, role):
    model = data['models'][name]
    override = model.get('overrides', {}).get(role)
    if override and fresh(override['checked_at'], 30 * 86400):
        return {'tier': override['tier'], 'basis': 'user_override', 'reason': override['reason']}
    dimensions = {}
    evidence = []
    for key, result in model['results'].items():
        b = data['benchmarks'][key]
        if not (b['independent'] and b['effort'] == model['effort'] and model['effort'] != 'unknown' and
                all(fresh(d, 30 * 86400) for d in (
                b['checked_at'], b['observed_at'], result['checked_at']))):
            continue
        tier = 'H' if result['score'] >= b['h_min'] else 'M' if result['score'] >= b['m_min'] else 'L'
        dimensions.setdefault(b['dimension'], []).append(tier)
        evidence.append(key)
    required = ('coding',) if role == 'implement' else ('coding', 'reasoning')
    tier = min((t for dim in required for t in dimensions.get(dim, [])), key=RANK.get, default='UNKNOWN')
    if any(dim not in dimensions for dim in required):
        tier = 'UNKNOWN'
    return {'tier': tier, 'basis': 'benchmark' if tier != 'UNKNOWN' else 'missing_or_stale_evidence',
            'benchmarks': evidence}


def report(data, revision):
    due, deferred = [], []
    for name, model in data['models'].items():
        if model['accesses'] and not any(a['allowed'] and data['pools'][a['pool']]['allowed']
                                         for a in model['accesses']):
            continue
        if any(assessment(data, name, role)['tier'] == 'UNKNOWN' for role in ROLES):
            retry = model.get('research', {}).get('retry_after')
            if retry and datetime.fromisoformat(retry.replace('Z', '+00:00')) > now():
                deferred.append(name)
            else:
                due.append(name)
    return {'schema': 1, 'revision': revision, 'enforce': data['enforce'], 'models': data['models'],
            'pools': data['pools'], 'benchmarks': data['benchmarks'],
            'assessments': {n: {r: assessment(data, n, r) for r in ROLES} for n in data['models']},
            'research_due': due, 'research_deferred': deferred}


def summary(data, status):
    return {k: status[k] for k in ('revision', 'enforce', 'research_due', 'research_deferred')} | {
        'total_models': len(data['models']), 'pools': data['pools'],
        'models': {n: {'effort': m['effort'], 'roles': status['assessments'][n],
                      'usage_estimate': m.get('usage_estimate'),
                      'accesses': [{k: a[k] for k in ('id', 'pool', 'host', 'allowed', 'available', 'checked_at')}
                                   for a in m['accesses']]}
                   for n, m in data['models'].items() if not m['accesses'] or any(
                       a['allowed'] and data['pools'][a['pool']]['allowed'] for a in m['accesses'])},
        'note': 'Unauthorized catalog entries omitted; list --details includes every retained field.'}


def select(data, role, tier, task_class='', metric='tokens', kind=None, context=0, tools=()):
    candidates, excluded = [], []
    for name, model in data['models'].items():
        quality = assessment(data, name, role)
        for a in model['accesses']:
            p = data['pools'][a['pool']]
            reasons = []
            if RANK[quality['tier']] < RANK[tier]:
                reasons.append('quality_unknown_or_below_required')
            if not (p['allowed'] and a['allowed'] and a['available']):
                reasons.append('access_not_authorized_or_available')
            if kind and p['kind'] != kind:
                reasons.append('access_kind')
            if not fresh(a['checked_at'], 86400):
                reasons.append('catalog_or_price_stale')
            if not fresh(p['checked_at'], 300) or not p['windows'] or any(
                    w['remaining'] < 10 or datetime.fromisoformat(w['resets_at'].replace('Z', '+00:00')) <= now()
                    for w in p['windows']):
                reasons.append('quota_unknown_stale_or_below_10_percent')
            if p['kind'] == 'free_api' and (a['input_price'] != 0 or a['output_price'] != 0):
                reasons.append('free_price_not_verified')
            if context and (a['context'] is None or a['context'] < context):
                reasons.append('context_unknown_or_insufficient')
            if set(tools) - set(a['tools']):
                reasons.append('missing_tools')
            usage = a.get('metrics', {})
            cost = usage.get('tokens_per_accepted' if metric == 'tokens' else 'usd_per_accepted')
            if not (task_class and usage.get('task_class') == task_class and usage.get('complete') and
                    usage.get('samples', 0) >= 3 and fresh(usage.get('checked_at'), 30 * 86400)):
                cost = None
            item = {'model': name, 'access': a['id'], 'pool': a['pool'], 'kind': p['kind'],
                    'quality': quality, 'cost_per_accepted': cost, 'metric': metric,
                    'benchmark_prior': model.get('usage_estimate'),
                    'quota_remaining': min((w['remaining'] for w in p['windows']), default=None)}
            if reasons:
                excluded.append(dict(item, reasons=reasons))
            else:
                candidates.append(item)
    # ponytail: one comparable observed metric, no invented exchange rate across subscription quotas.
    # Unknown cost stays null; more workload classes can be added when real observations justify them.
    candidates.sort(key=lambda c: (c['cost_per_accepted'] is None,
                                   c['cost_per_accepted'] or 0, c['model'], c['access']))
    return {'status': 'AVAILABLE' if candidates else 'BLOCKED', 'recommended': candidates[0] if candidates else None,
            'candidates': candidates, 'excluded': excluded,
            'limits': 'Recommendation only; unknown cost is not zero. No automatic model switch or API call.'}


def require(data, actor, role, tier='H'):
    if not data['enforce']:
        return
    name = canonical(data, actor)
    if name not in data['models'] or RANK[assessment(data, name, role)['tier']] < RANK[tier]:
        raise ValueError(f'Model {actor} needs current {tier} evidence for {role}; refresh models first')


def canonical(data, actor):
    return next((n for n, m in data['models'].items() if actor.casefold() in
                 {s.casefold() for s in [n, *m['aliases']]}), actor.casefold())


def gate(task, actor, command, path=None):
    data, _ = load(path)
    if command == 'start' and data['enforce']:
        require(data, actor, 'plan' if task['tier'] == 'H' else 'implement', task['tier'])
        if task['risk'] != 'LOW' or any(i['kind'] in plan.SECURE_KINDS for i in task['items']):
            if not task['ready_by']:
                raise ValueError('Strong READY approval missing')
            require(data, task['ready_by'], 'plan')
    elif command == 'review':
        require(data, actor, 'review')
        from .accept import implementers
        if canonical(data, actor) in {canonical(data, a) for a in implementers(task)}:
            raise ValueError('Reviewer alias belongs to an implementer; independent review required')
    elif command == 'accept':
        # Recheck the current reviewer too: a past review cannot bypass an enabled/stale registry.
        from .accept import _latest_review, effective_risk
        if effective_risk(task) != 'LOW':
            latest = _latest_review(task['review'])
            if latest:
                require(data, latest['reviewer'], 'review')
                from .accept import implementers
                if canonical(data, latest['reviewer']) in {canonical(data, a) for a in implementers(task)}:
                    raise ValueError('Review is by an implementer alias; independent review required')
