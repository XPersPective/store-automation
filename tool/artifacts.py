"""Public screenshot manifest with source and byte provenance."""
from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import re
from pathlib import Path
from pathlib import PureWindowsPath

MAX_IMAGE = 12 * 1024 * 1024
SENSITIVE = re.compile(r"auth|credential|secret|service-account|\.env|\.jks$|\.p8$|\.p12$|\.pfx$|\.pem$|key\.properties|id_rsa|id_ed25519", re.I)


def _image_type(body):
    if body.startswith(b'\x89PNG\r\n\x1a\n'): return 'image/png'
    if body.startswith(b'\xff\xd8\xff'): return 'image/jpeg'
    if body[:4] == b'RIFF' and body[8:12] == b'WEBP': return 'image/webp'
    return None


def register_artifact(project, name, source, task):
    """Explicit capture registration; hashes bind the bytes, provenance remains declared."""
    try:
        from . import dispatch as authority
    except ImportError:
        import dispatch as authority
    if not all(isinstance(x, str) and 0 < len(x) <= 160 for x in (source, task)):
        raise ValueError('Bounded source and task provenance required')
    if PureWindowsPath(name).anchor or any(part.startswith('.') for part in PureWindowsPath(name).parts) or SENSITIVE.search(name):
        raise ValueError('Artifact must be a public project-relative image')
    path = authority.owned_path(project, name)
    if not path.is_file() or path.stat().st_size > MAX_IMAGE:
        raise ValueError('Bounded regular image required')
    body = path.read_bytes()
    if _image_type(body) != mimetypes.guess_type(path.name)[0]:
        raise ValueError('Image header/extension mismatch')
    manifest = authority.owned_path(project, '.factory/runs/artifact-manifest.json')
    rows = _artifacts(project) if manifest.exists() else []
    if len(rows) >= 200: raise ValueError('Artifact manifest full')
    row = {'path': path.relative_to(Path(project).resolve()).as_posix(),
           'sha256': hashlib.sha256(body).hexdigest(), 'source': source, 'task': task}
    rows = [r for r in rows if r['path'] != row['path']]
    authority.atomic(manifest, {'artifacts': [*rows, row]})
    return row


def _artifacts(project):
    """Read only the explicit project manifest; reject links, escapes and stale hashes."""
    root = Path(project).resolve(strict=True)
    manifest = root / ".factory" / "runs" / "artifact-manifest.json"
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in (manifest, *manifest.parents) if p != root and root in p.parents) or root not in manifest.resolve(strict=True).parents:
        raise ValueError("artifact manifest must be a regular file inside the project")
    if manifest.stat().st_size > 1_000_000:
        raise ValueError("artifact manifest too large")
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    rows = raw.get("artifacts", raw) if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise ValueError("artifact manifest must contain an artifacts list")
    result = []
    for row in rows[:200]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            continue
        rel = Path(row["path"])
        if rel.is_absolute() or PureWindowsPath(row['path']).anchor or any(part.startswith('.') for part in PureWindowsPath(row['path']).parts) or SENSITIVE.search(row["path"]):
            continue
        path = root / rel
        if any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()) for p in (path, *path.parents) if p != root):
            continue
        try:
            resolved = path.resolve(strict=True)
            if root not in resolved.parents or not resolved.is_file() or resolved.stat().st_size > MAX_IMAGE:
                continue
            if mimetypes.guess_type(resolved.name)[0] not in ("image/png", "image/jpeg", "image/webp"):
                continue
            body = resolved.read_bytes()
            if _image_type(body) != mimetypes.guess_type(resolved.name)[0]:
                continue
            digest = hashlib.sha256(body).hexdigest()
            if not hmac.compare_digest(digest, str(row.get("sha256", ""))):
                continue
        except (OSError, ValueError):
            continue
        result.append({"id": digest, "path": rel.as_posix(), "sha256": digest,
                       "source": str(row.get("source", "unspecified"))[:160],
                       "task": str(row.get("task", ""))[:160], "media_type": mimetypes.guess_type(resolved.name)[0]})
    return result


