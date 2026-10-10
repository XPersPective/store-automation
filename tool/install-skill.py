"""Install the self-contained skill for Codex/OpenCode without editing global configs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parents[1]


def files():
    result = {p.relative_to(SOURCE / 'skills/store-automation').as_posix(): p
              for p in (SOURCE / 'skills/store-automation').rglob('*') if p.is_file()}
    names = ['tool/factory.py', 'tool/release.py', 'tool/sessions.py', 'opencode.json', 'contracts/capabilities.json',
             'contracts/delegation-smoke.json', 'docs/services.md', 'docs/roadmap.md']
    names += [p.relative_to(SOURCE).as_posix() for directory in ('prompts', 'skills')
              for p in (SOURCE / '.opencode' / directory).rglob('*') if p.is_file()]
    result.update({'runtime/' + name: SOURCE / name for name in names})
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_launcher(skill, directory):
    """Owned launcher in the existing user bin; never change the working directory."""
    directory = Path(directory)
    if directory.resolve() != directory.absolute():
        raise ValueError('Linked launcher directory refused')
    target = directory / ('store-automation.cmd' if os.name == 'nt' else 'store-automation')
    marker = 'store-automation owned launcher v1'
    cli = skill / 'runtime/tool/factory.py'
    if os.name == 'nt':
        paths = [str(Path(sys.executable).resolve()), str(cli.resolve())]
        if any(any(c in p for c in '\r\n"') for p in paths):
            raise ValueError('Unsafe launcher path')
        python, script = (p.replace('%', '%%') for p in paths)
        content = f'@echo off\nrem {marker}\n"{python}" "{script}" %*\nexit /b %errorlevel%\n'
    else:
        import shlex
        content = f'#!/bin/sh\n# {marker}\nexec {shlex.quote(sys.executable)} {shlex.quote(str(cli.resolve()))} "$@"\n'
    # Refuse altered or unrelated launchers, including aliases through links.
    manifest = directory / '.store-automation-launcher.json'
    if manifest.is_symlink() or (hasattr(manifest, 'is_junction') and manifest.is_junction()) or (manifest.exists() and not manifest.is_file()):
        raise ValueError('Linked/non-file launcher manifest refused')
    previous = json.loads(manifest.read_text()) if manifest.is_file() else {}
    if target.exists() and (target.is_symlink() or not target.is_file() or
                            digest(target) != previous.get('sha256')):
        raise ValueError(f'Preserve modified/unowned launcher: {target}')
    if manifest.is_symlink():
        raise ValueError('Linked launcher manifest refused')
    directory.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    if os.name != 'nt':
        target.chmod(0o755)
    manifest.write_text(json.dumps({'sha256': digest(target)}) + '\n')
    return str(target)


def install(targets):
    resources = files()
    hashes = {name: digest(path) for name, path in resources.items()}
    # Preflight every destination before writing either host's installation.
    for target in targets:
        if target.is_symlink() or (hasattr(target, 'is_junction') and target.is_junction()):
            raise ValueError(f'Existing linked skill is not owned by this installer: {target}')
        manifest = target / '.install-manifest.json'
        if manifest.is_symlink() or (hasattr(manifest, 'is_junction') and manifest.is_junction()) or (manifest.exists() and not manifest.is_file()):
            raise ValueError(f'Linked/non-file install manifest refused: {manifest}')
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
    result = install(targets)
    if not args.target:
        result['launcher'] = install_launcher(targets[0], Path.home() / '.local/bin')
        result['path_note'] = 'User .local/bin must be on PATH; reopen existing terminals after PATH changes'
    print(json.dumps(result, indent=2))
