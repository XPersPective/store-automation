"""Store Automation companion: git-native plan, evidence-bound acceptance, legacy cleanup.

Plan commands print short text lines for agents; doctor, legacy and
release-readback print JSON. Exit: 0 ok, 1 warnings/unverified, 2 errors, 3 no plan.
"""
import argparse
import json
from pathlib import Path
import sys

# Keep installed skill directories free of generated Python bytecode.
sys.dont_write_bytecode = True
# Agents read output as UTF-8 even when a Windows pipe defaults to the ANSI code page.
sys.stdout.reconfigure(encoding='utf-8')

from runtime import accept, models, plan
from runtime.legacy import found as legacy_found, legacy
from runtime.paths import public_path
from runtime.verification import release_readback

VERSION = '4.2.0'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--version', action='version', version='store-automation ' + VERSION)
    ap.add_argument('--project', default='.', help='Application root (default: current directory)')
    ap.add_argument('--models-file', type=Path, default=models.DEFAULT, help='User model registry (outside the skill)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('doctor', 'boot', 'map', 'init', 'changed', 'validate'):
        sub.add_parser(name)
    p = sub.add_parser('new', help='Create the next task (PLANNED scaffold)')
    p.add_argument('title')
    p.add_argument('--depends', default='')
    p.add_argument('--risk', choices=plan.RISK_VALUES, type=str.upper)
    p.add_argument('--priority', choices=plan.PRIORITY_VALUES, type=str.upper)
    p.add_argument('--tier', choices=plan.TIER_VALUES, type=str.upper)
    p.add_argument('--milestone', default='')
    p = sub.add_parser('start', help='READY -> IN_PROGRESS and record Owner')
    p.add_argument('task')
    p.add_argument('--owner', required=True, help='Your model/agent id')
    p.add_argument('--takeover', default='', help="Reason for taking over another owner's task")
    p = sub.add_parser('check', help='Run the task Verify commands; write machine evidence')
    p.add_argument('task')
    p.add_argument('--as', dest='actor', default='', help='Your model id (must be the Owner)')
    p.add_argument('--timeout', type=float)
    p = sub.add_parser('evidence', help='Record a non-machine observation bound to current source')
    p.add_argument('task')
    p.add_argument('--kind', required=True)
    p.add_argument('--as', dest='actor', required=True, help='Your model id (must be the Owner)')
    p.add_argument('--note', required=True)
    p.add_argument('--criterion', action='append', default=[],
                   help='Acceptance item id this observation proves (shown by `boot`/`accept`), repeatable')
    p.add_argument('--file', action='append', default=[], help='Observed artifact (e.g. screenshot), repeatable')
    p = sub.add_parser('review', help='Independent review by an agent other than Owner')
    p.add_argument('task')
    p.add_argument('--reviewer', required=True)
    p.add_argument('--verdict', required=True, choices=('PASS', 'BLOCKED'), type=str.upper)
    p.add_argument('--finding', action='append', default=[])
    p = sub.add_parser('accept', help='Evaluate acceptance; DONE, REVIEW_PENDING, WAITING_USER, UNVERIFIED or BLOCKED')
    p.add_argument('task')
    p.add_argument('--as', dest='actor', required=True, help='Owner, or the reviewer on a REVIEW task')
    p = sub.add_parser('legacy', help='Retire foreign planning/state systems after extraction (preview unless --apply)')
    p.add_argument('--apply', action='store_true')
    p.add_argument('--path', action='append', default=[], help='Extra foreign state path found by judgment')
    p.add_argument('--drop-archive', action='store_true', help='Delete this project archive after the adoption commit')
    p.add_argument('--confirm-untracked', action='store_true',
                   help='With --drop-archive: also delete archived files that were never in Git')
    p = sub.add_parser('release-readback', help='Compare expected/observed release JSON')
    p.add_argument('--request', required=True, help='JSON {expected, observed} relative to the project')
    p = sub.add_parser('models', help='Offline model pool, evidence refresh queue and selection')
    ms = p.add_subparsers(dest='model_cmd', required=True)
    p = ms.add_parser('list')
    p.add_argument('--details', action='store_true', help='Include full schema for editing retained entries')
    p = ms.add_parser('merge', help='Merge researched entries; preserve unrelated models and pools')
    p.add_argument('--file', required=True, help='Project-relative public JSON patch')
    p.add_argument('--revision', required=True, help='Revision returned by models list (prevents lost updates)')
    p = ms.add_parser('select', help='Recommend authorized models meeting the task quality floor')
    p.add_argument('--role', choices=models.ROLES, required=True)
    p.add_argument('--tier', choices=plan.TIER_VALUES, required=True)
    p.add_argument('--kind', choices=models.KINDS)
    p.add_argument('--task-class', default='')
    p.add_argument('--metric', choices=('tokens', 'usd'), default='tokens')
    p.add_argument('--context', type=int, default=0)
    p.add_argument('--tool', action='append', default=[])
    args = ap.parse_args(argv)
    try:
        root = Path(args.project).resolve(strict=True)
        if not root.is_dir():
            raise ValueError('Project is not a directory: ' + str(root))
        c = args.cmd
        if c == 'models':
            data, revision = models.load(args.models_file)
            if args.model_cmd == 'merge':
                path = public_path(root, args.file)
                if path.stat().st_size > 4_000_000:
                    raise ValueError('Model patch exceeds 4 MB')
                patch = models.parse(path.read_text(encoding='utf-8-sig'))
                data, revision = models.merge(args.models_file, patch, args.revision)
            if args.model_cmd == 'select':
                models.number(args.context)
                result = models.select(data, args.role, args.tier, args.task_class,
                                       args.metric, args.kind, args.context, args.tool)
                return emit_json(result, 0 if result['recommended'] else 1)
            result = models.report(data, revision)
            if args.model_cmd == 'list' and not args.details:
                result = models.summary(data, result)
            return emit_json(result, 0)
        if c == 'doctor':
            data = dict(status='READY' if sys.version_info >= (3, 11) else 'BLOCKED', version=VERSION,
                        python=sys.version.split()[0], interpreter=sys.executable, git=plan.git(root, '--version') or 'missing',
                        project=str(root), plan=plan.plan_exists(root), legacy=legacy_found(root) or None,
                        skill=str(Path(__file__).resolve().parent / 'SKILL.md'),
                        isolation='Scope instructions are not an OS sandbox')
            return emit_json(data, 0 if data['status'] == 'READY' else 1)
        if c == 'legacy':
            return emit_json(legacy(root, apply=args.apply, extra=args.path, drop_archive=args.drop_archive,
                                    confirm_untracked=args.confirm_untracked), 0)
        if c == 'release-readback':
            path = public_path(root, args.request)
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            result = release_readback(data.get('expected'), data.get('observed'))
            return emit_json(result, 0 if result['status'] == 'MATCHED' else 1)
        code, lines = {
            'boot': lambda: plan.boot(root), 'map': lambda: plan.map_repo(root), 'init': lambda: plan.init(root),
            'changed': lambda: plan.changed(root), 'validate': lambda: plan.validate(root),
            'new': lambda: plan.new_task(root, args.title, args.depends, args.risk, args.priority, args.tier,
                                         args.milestone),
            'start': lambda: plan.start(root, args.task, args.owner, args.takeover, args.models_file),
            'check': lambda: accept.check(root, args.task, args.timeout, args.actor),
            'evidence': lambda: accept.evidence(root, args.task, args.kind, args.note, args.file,
                                                args.actor, args.criterion),
            'review': lambda: accept.review(root, args.task, args.reviewer, args.verdict, args.finding, args.models_file),
            'accept': lambda: accept.accept(root, args.task, args.actor, args.models_file),
        }[c]()
        if c == 'boot':
            try:
                data, revision = models.load(args.models_file)
                status = models.report(data, revision)
                lines.append(f"MODELS: {len(data['models'])} registered; "
                             f"{'enforced' if data['enforce'] else 'advisory'}; "
                             f"{len(status['research_due'])} research due, {len(status['research_deferred'])} deferred")
                if status['research_due']:
                    lines.append('MODELS RESEARCH: ' + ', '.join(status['research_due'][:25]) +
                                 ' (see `models list`; refresh only missing/stale entries)')
            except (ValueError, TypeError, KeyError, OSError) as exc:
                lines.append('MODELS ERROR: ' + str(exc) + '; repair registry before model selection')
        print('\n'.join(lines))
        return code
    except (ValueError, TypeError, KeyError, OSError) as exc:
        if args.cmd in ('doctor', 'legacy', 'release-readback', 'models'):
            return emit_json({'status': 'ERROR', 'error': str(exc)}, 2)
        print('FAIL ' + str(exc))
        return 2


def emit_json(data, code):
    print(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
