"""Build a new standalone directory; never overwrite an installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from runtime.paths import public_path


def build(source, destination):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination must not exist; preserve the current installation')
    if destination.resolve() != Path(os.path.abspath(destination)):  # `..` is fine, a linked parent is not
        raise ValueError('Linked destination refused')
    names = ['SKILL.md', 'store.py']
    names += [p.relative_to(source).as_posix() for folder, pattern in
              [('runtime', '*.py'), ('references', '*.md')] for p in sorted((source / folder).glob(pattern))]
    for name in names:
        if not public_path(source, name).is_file():
            raise ValueError('Package source missing or linked')
    destination.mkdir(parents=True)
    manifest = {}
    for name in names:
        output = destination / name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, output)
        manifest[name] = hashlib.sha256(output.read_bytes()).hexdigest()
    (destination / 'package-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(Path(__file__).resolve().parent, args.destination), indent=2))
