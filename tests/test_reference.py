import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid


spec = importlib.util.spec_from_file_location('reference_app', Path(__file__).resolve().parents[1] / 'examples/reference/app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / 'notes.db'
        self.start()

    def start(self):
        self.server = app.create_server(self.db, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.addCleanup(self.stop)

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(2)
            self.server = None

    def request(self, value=None, headers=None):
        data = None if value is None else json.dumps(value).encode()
        request = Request(self.base + '/api/notes', data=data,
                          headers=headers if headers is not None else {'Origin':self.base, 'Content-Type':'application/json'})
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_real_http_persistence_retry_and_conflict(self):
        note = {'id':str(uuid.uuid4()), 'title':'İlk fikir', 'body':'Türkçe kalıcı not <script> metin olarak.'}
        self.assertEqual(self.request(), (200, []))
        status, saved = self.request(note)
        self.assertEqual(status, 201)
        self.assertEqual(self.request(note), (200, saved))
        self.assertEqual(self.request({**note, 'title':'Farklı içerik'})[0], 409)
        self.stop()
        self.start()
        self.assertEqual(self.request(), (200, [saved]))

    def test_validation_and_request_boundaries(self):
        note = {'id':str(uuid.uuid4()), 'title':'   ', 'body':''}
        self.assertEqual(self.request(note)[0], 400)
        note['title'] = 'Valid'
        self.assertEqual(self.request(note, {'Content-Type':'application/json'})[0], 403)
        self.assertEqual(self.request(note, {'Origin':'https://untrusted.example', 'Content-Type':'application/json'})[0], 403)
        self.assertEqual(self.request(note, {'Origin':self.base, 'Content-Type':'application/json', 'Host':'untrusted.example'})[0], 403)
        self.assertEqual(self.request({**note, 'body':4})[0], 400)
        self.assertEqual(self.request({**note, 'title':'x'*121})[0], 400)
        self.assertEqual(self.request(), (200, []))

    def test_storage_failure_then_retry_preserves_one_note(self):
        note = {'id':str(uuid.uuid4()), 'title':'Tekrar deneme', 'body':'Kaybolmaması gereken metin'}
        connection = sqlite3.connect(self.db)
        try:
            connection.execute('BEGIN EXCLUSIVE')
            self.assertEqual(self.request(note)[0], 503)
        finally:
            connection.rollback()
            connection.close()
        self.assertEqual(self.request(note)[0], 201)
        self.assertEqual(len(self.request()[1]), 1)


if __name__ == '__main__':
    unittest.main()
