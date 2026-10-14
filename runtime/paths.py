"""Project-relative path checks shared by packaging, digests and evidence files."""
import ntpath
from pathlib import Path, PureWindowsPath
import re

PRIVATE = re.compile(r'(^|/)(?:\.env(?:\.[^/]+)?|auth\.json|credentials?|secrets?|'
                     r'service-account[^/]*|key\.properties|id_rsa|id_ed25519)(/|$)|'
                     r'\.(?:jks|keystore|p8|p12|pfx|pem)$', re.I)


def public_path(root, name):
    """Refuse private, escaping or linked paths before anything is opened, including on Windows."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError('relative path must be nonempty text')
    root = Path(root).absolute()
    parts = PureWindowsPath(name)
    if (parts.anchor or '\\' in name or '..' in parts.parts or ':' in name or
            any(part.endswith(('.', ' ')) or _reserved(part) for part in parts.parts) or
            PRIVATE.search(name) or any(ord(c) < 32 for c in name)):
        raise ValueError('Private or escaping path refused: ' + name)
    path = root / name
    for entry in (path, *path.parents):
        if entry.is_symlink() or (hasattr(entry, 'is_junction') and entry.is_junction()):
            raise ValueError('Linked path refused: ' + name)
    if root.resolve() not in path.resolve().parents:
        raise ValueError('Path escapes project: ' + name)
    return path


def _reserved(part):
    """Windows device names (CON, NUL, COM1...); PurePath.is_reserved is deprecated from Python 3.13."""
    return ntpath.isreserved(part) if hasattr(ntpath, 'isreserved') else PureWindowsPath(part).is_reserved()
