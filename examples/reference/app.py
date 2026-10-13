"""Loopback-only reference product; synthetic notes, no accounts or production claims."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit
import uuid


ASSETS = Path(__file__).parent


def create_server(db, port=8765):
    db = Path(db).resolve()
    with closing(sqlite3.connect(db, timeout=.2)) as connection, connection:
        connection.execute('CREATE TABLE IF NOT EXISTS notes '
                           '(id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL)')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Local demo: never log note content or request headers.

        def respond(self, status, payload, content_type='application/json; charset=utf-8'):
            body = json.dumps(payload, ensure_ascii=False).encode() if isinstance(payload, (dict, list)) else payload
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def reject(self, status, payload):
            # Drain a small unread body first: closing with unread bytes makes Windows reset the
            # connection before the client can read this response.
            try:
                length = int(self.headers.get('Content-Length', 0))
                if 0 < length <= 8192:
                    self.connection.settimeout(5)
                    self.rfile.read(length)
            except (ValueError, OSError):
                pass
            return self.respond(status, payload)

        def valid_host(self):
            return self.headers.get_all('Host', []) == [f'127.0.0.1:{self.server.server_port}']

        def do_GET(self):
            if not self.valid_host():
                return self.respond(403, {'error': 'Bu demo yalnız kendi yerel adresinden açılabilir.'})
            path = urlsplit(self.path).path
            if path in ('/', '/app.js'):
                name = 'index.html' if path == '/' else 'app.js'
                mime = 'text/html; charset=utf-8' if path == '/' else 'text/javascript; charset=utf-8'
                return self.respond(200, (ASSETS / name).read_bytes(), mime)
            if path == '/api/notes':
                try:
                    with closing(sqlite3.connect(db, timeout=2)) as connection:
                        # ponytail: bounded reference usage only; add pagination before a large note collection.
                        rows = connection.execute('SELECT id,title,body,created FROM notes ORDER BY created DESC, id DESC').fetchall()
                    return self.respond(200, [dict(zip(('id', 'title', 'body', 'created'), row)) for row in rows])
                except sqlite3.Error:
                    return self.respond(503, {'error': 'Notlar okunamadı. Tekrar deneyin.'})
            self.respond(404, {'error': 'Sayfa bulunamadı.'})

        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid_host() or self.headers.get_all('Origin', []) != [origin]:
                return self.reject(403, {'error': 'İstek kaynağı doğrulanamadı.'})
            if self.path != '/api/notes':
                return self.reject(404, {'error': 'İşlem bulunamadı.'})
            if self.headers.get('Content-Type') != 'application/json' or self.headers.get('Transfer-Encoding'):
                return self.reject(415, {'error': 'JSON isteği gerekli.'})
            try:
                lengths = self.headers.get_all('Content-Length', [])
                if len(lengths) != 1 or not 0 < int(lengths[0]) <= 8192:
                    raise ValueError()
                self.connection.settimeout(5)
                value = json.loads(self.rfile.read(int(lengths[0])))
                if not isinstance(value, dict) or set(value) != {'id', 'title', 'body'}:
                    raise ValueError()
                if any(not isinstance(value[key], str) for key in value):
                    raise ValueError()
                if str(uuid.UUID(value['id'])) != value['id']:
                    raise ValueError()
                title, body = value['title'].strip(), value['body'].strip()
                if not 1 <= len(title) <= 120 or len(body) > 1000:
                    raise ValueError()
            except (ValueError, OSError):
                return self.respond(400, {'error': 'Başlık 1–120, açıklama en fazla 1000 karakter olmalı.'})
            created = datetime.now(timezone.utc).isoformat()
            try:
                with closing(sqlite3.connect(db, timeout=.2)) as connection, connection:
                    cursor = connection.execute('INSERT OR IGNORE INTO notes VALUES (?,?,?,?)',
                                                (value['id'], title, body, created))
                    inserted = cursor.rowcount == 1
                    row = connection.execute('SELECT title,body,created FROM notes WHERE id=?', (value['id'],)).fetchone()
                    if row[:2] != (title, body):
                        return self.respond(409, {'error': 'Bu isteğin önceki kaydı farklı. Sayfayı yenileyip kontrol edin.'})
                # Success is sent only after the transaction has committed.
                return self.respond(201 if inserted else 200,
                                    {'id': value['id'], 'title': title, 'body': body, 'created': row[2]})
            except sqlite3.Error:
                return self.respond(503, {'error': 'Not kaydedilemedi. Metniniz korunuyor; tekrar deneyin.'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--db', type=Path, required=True, help='Explicit SQLite file for synthetic demo data')
    args = parser.parse_args()
    server = create_server(args.db, args.port)
    print(f'Reference demo: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
