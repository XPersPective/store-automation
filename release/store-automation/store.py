"""Small deterministic companion. Native agents are controlled by their host."""
import argparse
import json
from pathlib import Path
import sys

# Keep installed skill directories free of generated Python bytecode.
sys.dont_write_bytecode = True

from runtime import receipts
from runtime.acceptance import validate_task
from runtime.gate import gate
from runtime.verification import run_check, release_readback, measured_usage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='.', help='Selected application root')
    parser.add_argument('command', choices=['doctor', 'task', 'snapshot', 'prepare',
        'finish', 'record', 'check', 'gate', 'handoff', 'release-readback', 'usage'])
    parser.add_argument('--request', help='Public JSON request relative to project root')
    args = parser.parse_args(argv)
    root = Path(args.project).resolve(strict=True)
    try:
        if args.command == 'doctor':
            result = dict(status='READY' if sys.version_info >= (3, 11) else 'BLOCKED',
                          python=sys.version.split()[0], project=str(root),
                          skill=str(Path(__file__).resolve().parent / 'SKILL.md'),
                          host='Use the current native host; no provider login or model scan required',
                          isolation='Scope instructions are not an OS sandbox')
        else:
            if not args.request:
                parser.error('--request is required')
            path = receipts.public_path(root, args.request)
            if path.stat().st_size > receipts.MAX_RECORD:
                raise ValueError('Request too large')
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict):
                raise ValueError('Request must be an object')
            if args.command == 'task':
                result = validate_task(data)
            elif args.command == 'snapshot':
                result = receipts.snapshot(root, data['files'])
            elif args.command == 'prepare':
                result = receipts.prepare(root, **data)
            elif args.command == 'finish':
                result = receipts.finish(root, **data)
            elif args.command == 'record':
                result = receipts.append_record(root, **data)
            elif args.command == 'check':
                result = run_check(root, **data)
            elif args.command == 'gate':
                result = gate(root, **data)
            elif args.command == 'handoff':
                result = receipts.handoff(root, **data)
            elif args.command == 'release-readback':
                result = release_readback(**data)
            else:
                result = measured_usage(**data)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 1 if result.get('status') in ('BLOCKED', 'UNVERIFIED') or result.get('state') == 'FAIL' else 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({'status': 'ERROR', 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
