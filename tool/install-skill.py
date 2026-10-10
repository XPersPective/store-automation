"""Install the self-contained skill for Codex/OpenCode without editing global configs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

SOURCE = Path(__file__).resolve().parents[1]


def files():
    result = {p.relative_to(SOURCE / 'skills/store-automation').as_posix(): p
              for p in (SOURCE / 'skills/store-automation').rglob('*') if p.is_file()}
    names = ['tool/factory.py', 'opencode.json', 'contracts/capabilities.json',
             'contracts/delegation-smoke.json', 'docs/services.md', 'docs/roadmap.md']
    names += [p.relative_to(SOURCE).as_posix() for directory in ('prompts', 'skills')
              for p in (SOURCE / '.opencode' / directory).rglob('*') if p.is_file()]
    result.update({'runtime/' + name: SOURCE / name for name in names})
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(targets):
    resources = files()
    hashes = {name: digest(path) for name, path in resources.items()}
    # Preflight every destination before writing either host's installation.
    for target in targets:
        if target.is_symlink() or (hasattr(target, 'is_junction') and target.is_junction()):
            raise ValueError(f'Existing linked skill is not owned by this installer: {target}')
        manifest = target / '.install-manifest.json'
        previous = json.loads(manifest.read_text()) if manifest.is_file() else {}
        for name in resources:
            path = target / name
            if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
                   for p in (path, *path.parents) if p != target and target in p.parents):
                raise ValueError(f'Linked skill resource refused: {path}')
            if path.exists() and (not path.is_file() or digest(path) not in (previous.get(name), hashes[name])):
                raise ValueError(f'Preserve modified/unowned installed resource: {path}')
    for target in targets:
        for name, source in resources.items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, path)
        (target / '.install-manifest.json').write_text(json.dumps(hashes, indent=2) + '\n')
    return {'installed': [str(p) for p in targets], 'files_per_host': len(resources)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, help='Single explicit skill directory for isolated verification')
    args = parser.parse_args()
    targets = [args.target.resolve()] if args.target else [
        Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills/store-automation',
        Path.home() / '.config/opencode/skills/store-automation']
    print(json.dumps(install(targets), indent=2))
