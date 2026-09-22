import concurrent.futures
import gzip
import io
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import server


class ResourceLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.original_web_dir = server.WEB_DIR
        self.original_data_dir = server.DATA_DIR
        server.WEB_DIR = self.root / 'web'
        server.DATA_DIR = self.root / 'data'
        server.WEB_DIR.mkdir(parents=True)
        server.avatar_dir().mkdir(parents=True)
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.TodoHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f'http://127.0.0.1:{self.httpd.server_address[1]}'

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        server.WEB_DIR = self.original_web_dir
        server.DATA_DIR = self.original_data_dir
        with server.STATIC_GZIP_CACHE_LOCK:
            server.STATIC_GZIP_CACHE.clear()
        self.temp_dir.cleanup()

    def request(self, method, path, headers=None):
        request = urllib.request.Request(
            f'{self.base_url}{path}', method=method, headers=headers or {}
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.headers, response.read()

    def test_large_static_file_is_streamed_without_read_bytes_or_gzip(self):
        content = b'const value = 1;\n' * 4096
        (server.WEB_DIR / 'app.js').write_bytes(content)
        original_max_source = server.STATIC_GZIP_MAX_SOURCE_BYTES
        server.STATIC_GZIP_MAX_SOURCE_BYTES = 1024
        try:
            status, headers, body = self.request(
                'GET', '/app.js?v=large', {'Accept-Encoding': 'gzip'}
            )
        finally:
            server.STATIC_GZIP_MAX_SOURCE_BYTES = original_max_source

        self.assertEqual(status, 200)
        self.assertEqual(body, content)
        self.assertIsNone(headers.get('Content-Encoding'))
        self.assertEqual(int(headers['Content-Length']), len(content))

    def test_stream_file_uses_bounded_reads(self):
        content = b'x' * (server.STATIC_STREAM_CHUNK_BYTES * 2 + 17)

        class GuardedReader(io.BytesIO):
            def __init__(self, value):
                super().__init__(value)
                self.read_sizes = []

            def read(self, size=-1):
                if size <= 0 or size > server.STATIC_STREAM_CHUNK_BYTES:
                    raise AssertionError(f'unbounded file read: {size}')
                self.read_sizes.append(size)
                return super().read(size)

        reader = GuardedReader(content)
        handler = server.TodoHandler.__new__(server.TodoHandler)
        handler.wfile = io.BytesIO()

        handler.stream_file(reader)

        self.assertEqual(handler.wfile.getvalue(), content)
        self.assertGreaterEqual(len(reader.read_sizes), 4)

    def test_avatar_get_is_streamed_and_head_has_no_body(self):
        content = b'RIFF' + b'x' * 4096
        avatar = server.avatar_dir() / 'user.webp'
        avatar.write_bytes(content)

        with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('not streamed')):
            status, headers, body = self.request('GET', '/uploads/avatars/user.webp')
            head_status, head_headers, head_body = self.request(
                'HEAD', '/uploads/avatars/user.webp'
            )

        self.assertEqual(status, 200)
        self.assertEqual(body, content)
        self.assertEqual(head_status, 200)
        self.assertEqual(head_body, b'')
        self.assertEqual(headers['Content-Length'], head_headers['Content-Length'])

    def test_binary_static_file_is_not_gzipped(self):
        content = b'\x89PNG\r\n\x1a\n' + (b'x' * 4096)
        (server.WEB_DIR / 'assets' / 'sample.png').parent.mkdir(parents=True)
        (server.WEB_DIR / 'assets' / 'sample.png').write_bytes(content)

        status, headers, body = self.request(
            'GET', '/assets/sample.png', {'Accept-Encoding': 'gzip'}
        )

        self.assertEqual(status, 200)
        self.assertEqual(body, content)
        self.assertIsNone(headers.get('Content-Encoding'))

    def test_gzip_cache_enforces_entry_and_total_byte_limits_concurrently(self):
        original_entries = server.STATIC_GZIP_CACHE_MAX_ENTRIES
        original_bytes = server.STATIC_GZIP_CACHE_MAX_BYTES
        server.STATIC_GZIP_CACHE_MAX_ENTRIES = 3
        server.STATIC_GZIP_CACHE_MAX_BYTES = 180
        expected = {}
        try:
            assets_dir = server.WEB_DIR / 'assets'
            assets_dir.mkdir(parents=True)
            for index in range(12):
                raw = (f'const value{index} = "{index}";\n'.encode() * 100)
                (assets_dir / f'{index}.js').write_bytes(raw)
                expected[index] = raw

            def fetch(index):
                status, headers, body = self.request(
                    'GET', f'/assets/{index}.js', {'Accept-Encoding': 'gzip'}
                )
                self.assertEqual(status, 200)
                self.assertEqual(headers.get('Content-Encoding'), 'gzip')
                return index, gzip.decompress(body)

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(fetch, list(range(12)) * 3))

            self.assertTrue(all(body == expected[index] for index, body in results))
            with server.STATIC_GZIP_CACHE_LOCK:
                self.assertLessEqual(len(server.STATIC_GZIP_CACHE), 3)
                cache_bytes = sum(
                    len(entry[1]) for entry in server.STATIC_GZIP_CACHE.values()
                )
                self.assertLessEqual(cache_bytes, 180)
        finally:
            server.STATIC_GZIP_CACHE_MAX_ENTRIES = original_entries
            server.STATIC_GZIP_CACHE_MAX_BYTES = original_bytes


class _BlockingHandler(BaseHTTPRequestHandler):
    entered = threading.Event()
    release = threading.Event()

    def do_GET(self):
        self.entered.set()
        self.release.wait(timeout=5)
        body = b'ok'
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class BoundedServerTests(unittest.TestCase):
    def test_overload_returns_503_without_starting_an_extra_worker(self):
        _BlockingHandler.entered.clear()
        _BlockingHandler.release.clear()
        httpd = server.BoundedThreadingHTTPServer(
            ('127.0.0.1', 0), _BlockingHandler, max_workers=1
        )
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        url = f'http://127.0.0.1:{httpd.server_address[1]}/'

        def first_request():
            with urllib.request.urlopen(url, timeout=5) as response:
                return response.status, response.read()

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                first = executor.submit(first_request)
                self.assertTrue(_BlockingHandler.entered.wait(timeout=2))
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(url, timeout=2)
                self.assertEqual(raised.exception.code, 503)
                self.assertEqual(raised.exception.headers.get('Retry-After'), '1')
                raised.exception.close()
                _BlockingHandler.release.set()
                self.assertEqual(first.result(timeout=5), (200, b'ok'))
                with urllib.request.urlopen(url, timeout=2) as response:
                    self.assertEqual((response.status, response.read()), (200, b'ok'))
        finally:
            _BlockingHandler.release.set()
            httpd.shutdown()
            httpd.server_close()
            server_thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
