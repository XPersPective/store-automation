"""Authenticated loopback UI over callbacks owned by the selected project's supervisor."""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import mimetypes
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from pathlib import PureWindowsPath
from urllib.parse import urlsplit

MAX_BODY = 16_384
MAX_IMAGE = 12 * 1024 * 1024
MAX_TRANSCRIPT = 100
SENSITIVE = re.compile(r"auth|credential|secret|service-account|\.env|\.jks$|\.p8$|\.p12$|\.pfx$|\.pem$|key\.properties|id_rsa|id_ed25519", re.I)
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


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


def _public_snapshot(raw):
    """Project only declared public card fields; never forward provider payloads."""
    if not isinstance(raw, dict) or not isinstance(raw.get("agents"), list):
        raise ValueError("snapshot callback must return an agents list")
    cards = []
    text_fields = ("id", "task", "role", "model", "effort", "state", "provider", "question")
    for agent in raw["agents"][:100]:
        if not isinstance(agent, dict) or not isinstance(agent.get("id"), str):
            continue
        card = {key: agent[key][:500] for key in text_fields
                if isinstance(agent.get(key), str)}
        card["id"] = agent["id"][:100]
        card["control"] = {k: bool(v) for k, v in agent.get("control", {}).items()
                           if k in ("message", "abort")} if isinstance(agent.get("control"), dict) else {}
        usage = agent.get("usage")
        if isinstance(usage, dict):
            # These are measured counters only; provider-specific payloads are not relayed.
            card["usage"] = {k: v for k, v in usage.items()
                             if k in ("input", "output", "reasoning", "cache_read", "cache_write", "reported_cost")
                             and isinstance(v, (int, float)) and not isinstance(v, bool)
                             and math.isfinite(v) and v >= 0}
        cards.append(card)
    native = raw.get("native_ui")
    native = {"available": bool(native.get("available")),
              "reason": str(native.get("reason", ""))[:240]} if isinstance(native, dict) else {
                  "available": False, "reason": "No native UI binding is exposed by this adapter."}
    quota = raw.get("quota") if isinstance(raw.get("quota"), dict) else {}
    fraction = quota.get("remaining_fraction")
    public_quota = {
        "captured_at": quota.get("captured_at")[:64] if isinstance(quota.get("captured_at"), str) else None,
        "remaining_fraction": fraction if isinstance(fraction, (int, float)) and not isinstance(fraction, bool)
        and math.isfinite(fraction) and 0 <= fraction <= 1 else None,
        "observer": quota.get("observer")[:80] if isinstance(quota.get("observer"), str) else None,
        "windows": [{key: row.get(key) for key in ('window', 'remaining_fraction', 'reset_time', 'window_duration_mins')
                     if isinstance(row.get(key), (str, int, float)) and not isinstance(row.get(key), bool)}
                    for row in quota.get('windows', [])[:10] if isinstance(row, dict)] if isinstance(quota.get('windows'), list) else [],
    }
    receipts = []
    for row in raw.get("receipts", [])[-30:] if isinstance(raw.get("receipts"), list) else []:
        if not isinstance(row, dict):
            continue
        receipt = {key: row[key][:100] for key in ("id", "agent", "state", "director")
                   if isinstance(row.get(key), str)}
        when = row.get("time")
        if isinstance(when, (int, float)) and not isinstance(when, bool) and math.isfinite(when):
            receipt["time"] = when
        receipts.append(receipt)
    director = raw.get("director")
    return {"agents": cards, "selected": raw.get("selected")[:100] if isinstance(raw.get("selected"), str) else None,
            "updated_at": raw.get("updated_at")[:64] if isinstance(raw.get("updated_at"), str) else None,
            "stale": bool(raw.get("stale", False)), "native_ui": native,
            "quota": public_quota, "director": director[:160] if isinstance(director, str) else "Bilinmiyor",
            "receipts": receipts}


def _public_transcript(rows):
    if not isinstance(rows, list):
        return []
    result = []
    for row in rows[-MAX_TRANSCRIPT:]:
        if isinstance(row, dict) and row.get("role") in ("user", "assistant") and isinstance(row.get("text"), str):
            result.append({"role": row["role"], "text": row["text"][:16_000],
                           "time": str(row.get("time", ""))[:64]})
    return result


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


def make_server(project, callbacks, host="127.0.0.1", port=0, token=None):
    """Create (but do not start) server. Caller starts/stops it with selected-project lifetime."""
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise ValueError("console may bind only to loopback")
    token = token or os.environ.get("FACTORY_CONSOLE_TOKEN")
    if not isinstance(token, str) or not 24 <= len(token) <= 256:
        raise ValueError("set an ephemeral FACTORY_CONSOLE_TOKEN before starting the console")
    for key in ("snapshot", "message", "abort"):
        if not callable(callbacks.get(key)):
            raise ValueError(f"missing owned-session callback: {key}")
    project = Path(project).resolve(strict=True)

    class Handler(BaseHTTPRequestHandler):
        server_version = "FactoryConsole"
        def log_message(self, *_):  # Never log headers, URLs, user text or the pasted token.
            return

        def _fail(self, code, message):
            self._json(code, {"error": message})

        def _json(self, code, value):
            body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            expected_host = f"{self.server.server_address[0]}:{self.server.server_address[1]}"
            host_header = self.headers.get("Host", "")
            if host_header.lower() != expected_host.lower():
                self._fail(400, "invalid Host")
                return False
            origin = self.headers.get("Origin")
            if origin and (urlsplit(origin).scheme != "http" or urlsplit(origin).netloc.lower() != expected_host.lower()):
                self._fail(403, "cross-origin request refused")
                return False
            if not hmac.compare_digest(self.headers.get("X-Console-Token", ""), token):
                self._fail(401, "paste the local console token")
                return False
            return True

        def do_GET(self):
            route = urlsplit(self.path)
            if route.path == '/favicon.ico' and not route.query:
                self.send_response(204); self.end_headers(); return
            if route.path == "/" and route.query == "":
                page = (Path(__file__).with_name("console.html")).read_bytes()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page))); self.send_header("Cache-Control", "no-store")
                self.end_headers(); self.wfile.write(page); return
            if not self._authorized(): return
            try:
                if route.path == "/api/state" and not route.query:
                    snap = _public_snapshot(callbacks["snapshot"]())
                    requested = self.headers.get('X-Selected-Agent')
                    selected = requested if requested in {a['id'] for a in snap['agents']} else snap['selected']
                    snap['selected'] = selected
                    transcript = _public_transcript(callbacks.get("messages", lambda _sid: [])(selected)) if selected else []
                    self._json(200, {**snap, "transcript": transcript, "artifacts": _artifacts(project) if (project / ".factory/runs/artifact-manifest.json").exists() else []})
                elif route.path.startswith("/api/image/") and not route.query:
                    artifact = next((a for a in _artifacts(project) if a["id"] == route.path.rsplit("/", 1)[-1]), None)
                    if not artifact: self._fail(404, "image is not in the approved manifest"); return
                    path = project / artifact["path"]
                    body = path.read_bytes()
                    if len(body) > MAX_IMAGE or hashlib.sha256(body).hexdigest() != artifact['sha256']:
                        self._fail(409, 'artifact changed before serving'); return
                    self.send_response(200); self.send_header("Content-Type", artifact["media_type"])
                    self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(body)
                else: self._fail(404, "route not found")
            except (OSError, ValueError, TypeError) as exc: self._fail(400, 'owned snapshot or artifact unavailable')

        def do_POST(self):
            if not self._authorized(): return
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= length <= MAX_BODY: self._fail(413, "request too large"); return
                raw = json.loads(self.rfile.read(length))
                if not isinstance(raw, dict) or not SAFE_ID.fullmatch(str(raw.get("session", ""))):
                    self._fail(400, "invalid request"); return
                parsed = urlsplit(self.path)
                if parsed.query: self._fail(400, 'query not allowed'); return
                route = parsed.path
                if route == "/api/message":
                    message = raw.get("text")
                    if not isinstance(message, str) or not message.strip() or len(message) > 8000:
                        self._fail(400, "message must contain 1 to 8000 characters"); return
                    if callbacks["message"](raw["session"], message) is False: self._fail(409, "message not acknowledged"); return
                    self._json(200, {"state": "pending"})
                elif route == "/api/abort":
                    if callbacks["abort"](raw["session"]) is False: self._fail(409, "abort not acknowledged"); return
                    self._json(200, {"state": "interrupted"})
                else: self._fail(404, "route not found")
            except (ValueError, TypeError, OSError, RuntimeError) as exc: self._fail(400, 'owned control request rejected')

    return ThreadingHTTPServer((host, port), Handler)

