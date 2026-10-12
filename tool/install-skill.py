"""Install the self-contained skill for detected native hosts without editing configs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parents[1]


def discover(home=None):
    """Presence only: never open host settings, sessions or authentication files."""
    home = Path.home() if home is None else Path(home)
    roots = {
        'codex': Path(os.environ.get('CODEX_HOME', str(home / '.codex'))) / 'skills',
        'claude': home / '.claude/skills',
        'gemini': home / '.gemini/skills',
        'qwen': home / '.qwen/skills',
        'opencode': home / '.config/opencode/skills',
        'mcode': Path(os.environ.get('MINIMAX_DATA_DIR') or os.environ.get('MAVIS_DATA_DIR') or str(home / '.minimax')) / 'skills',
        'mimo': home / '.config/mimocode/skills',
        # Google Codelab documents CLI separately from the current IDE.
        'agy': home / '.gemini/antigravity-cli/skills',
        'cursor': home / '.cursor/skills',
        'windsurf': home / '.codeium/windsurf/skills',
        'cline': home / '.cline/skills',
        'codebuff': home / '.agents/skills',
        'freebuff': home / '.agents/skills',
        'zed': home / '.agents/skills',
    }
    found = {name: root / 'store-automation' for name, root in roots.items()
             if shutil.which(name)}
    programs = home / 'AppData/Local/Programs'
    for name, executable, root in [
        ('antigravity-ide', 'Antigravity IDE/Antigravity IDE.exe', '.gemini/config/skills'),
        ('antigravity', 'antigravity/Antigravity.exe', '.gemini/config/skills'),
        ('freebuff', '@codebufffreebuff-desktop/Freebuff.exe', '.agents/skills'),
        ('cursor', 'cursor/Cursor.exe', '.cursor/skills'),
        ('windsurf', 'Windsurf/Windsurf.exe', '.codeium/windsurf/skills'),
    ]:
        if (programs / executable).is_file():
            found[name] = home / root / 'store-automation'
    extensions = home / '.vscode/extensions'
    if extensions.is_dir() and any(p.is_dir() and p.name.startswith('saoudrizwan.claude-dev-')
                                   for p in extensions.iterdir()):
        found['cline'] = home / '.cline/skills/store-automation'
    # Official user discovery root shared by Codex, Gemini, OpenCode and MiMo.
    found['agents'] = home / '.agents/skills/store-automation'
    return found


def plain_path(path):
    if path.resolve() != path.absolute():
        raise ValueError(f'Linked or non-canonical install path refused: {path}')
    if any(p.exists() and not p.is_dir() for p in path.parents):
        raise ValueError(f'Non-directory install ancestor refused: {path}')


def files():
    result = {p.relative_to(SOURCE / 'skills/store-automation').as_posix(): p
              for p in (SOURCE / 'skills/store-automation').rglob('*') if p.is_file()}
    names = ['tool/factory.py', 'tool/release.py', 'tool/sessions.py', 'tool/subscriptions.py', 'tool/dispatch.py',
             'tool/native_agents.py', 'tool/console.py', 'tool/console.html', 'tool/team.py', 'tool/ios-evidence.py', 'opencode.json', 'contracts/capabilities.json',
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
    if target.is_symlink() or (target.exists() and (not target.is_file() or
                            digest(target) != previous.get('sha256'))):
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
    targets = [Path(target).absolute() for target in targets]
    resources = files()
    for source in resources.values():
        plain_path(source)
    hashes = {name: digest(path) for name, path in resources.items()}
    # Preflight every destination before writing either host's installation.
    for target in targets:
        plain_path(target)
        if target.exists() and not target.is_dir():
            raise ValueError(f'Non-directory skill target refused: {target}')
        if target.is_symlink() or (hasattr(target, 'is_junction') and target.is_junction()):
            raise ValueError(f'Existing linked skill is not owned by this installer: {target}')
        manifest = target / '.install-manifest.json'
        if manifest.is_symlink() or (hasattr(manifest, 'is_junction') and manifest.is_junction()) or (manifest.exists() and not manifest.is_file()):
            raise ValueError(f'Linked/non-file install manifest refused: {manifest}')
        previous = json.loads(manifest.read_text()) if manifest.is_file() else {}
        for name in resources:
            path = target / name
            plain_path(path)
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
    parser.add_argument('--list', action='store_true', help='Report detected destinations without writing files')
    args = parser.parse_args()
    hosts = {'explicit': args.target.absolute()} if args.target else discover()
    if args.list:
        print(json.dumps({'detected': {name: str(path) for name, path in hosts.items()}}, indent=2))
        sys.exit(0)
    targets = list(dict.fromkeys(hosts.values()))
    managed = Path.home() / '.skills-manager/skills/store-automation'
    linked = [p for p in targets if p.resolve() != p.absolute()]
    if not args.target and linked:
        expected = {name: digest(source) for name, source in files().items()}
        if any(p.resolve() != managed.resolve() for p in linked) or any(
                not (managed / name).is_file() or digest(managed / name) != value for name, value in expected.items()):
            raise ValueError('Update managed library through Skills Manager first; linked targets are never overwritten')
        targets = [p for p in targets if p not in linked]
    result = install(targets)
    result['managed_verified'] = [str(p) for p in linked] if not args.target else []
    result['hosts'] = list(hosts)
    if not args.target:
        result['launcher'] = install_launcher((targets or [managed])[0], Path.home() / '.local/bin')
        result['path_note'] = 'User .local/bin must be on PATH; reopen existing terminals after PATH changes'
    print(json.dumps(result, indent=2))
