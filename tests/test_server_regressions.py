import concurrent.futures
import base64
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import server


class ServerRegressionTests(unittest.TestCase):
    def setUp(self):
        self.original_data_dir = server.DATA_DIR
        self.original_db_path = server.DB_PATH
        self.original_iterations = server.PASSWORD_ITERATIONS
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        server.DATA_DIR = Path(self.temp_dir.name)
        server.DB_PATH = server.DATA_DIR / 'todo-list.db'
        server.PASSWORD_ITERATIONS = 1_000
        server.init_db()

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.TodoHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f'http://127.0.0.1:{self.httpd.server_address[1]}'

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        server.DATA_DIR = self.original_data_dir
        server.DB_PATH = self.original_db_path
        server.PASSWORD_ITERATIONS = self.original_iterations
        self.temp_dir.cleanup()

    def request(self, method, path, payload=None, token=None, extra_headers=None):
        data = None
        headers = dict(extra_headers or {})
        if payload is not None:
            data = json.dumps(payload).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        if token:
            headers['Authorization'] = f'Bearer {token}'
        req = urllib.request.Request(f'{self.base_url}{path}', data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read().decode('utf-8') or '{}')
        except urllib.error.HTTPError as error:
            try:
                body = error.read().decode('utf-8') or '{}'
            finally:
                error.close()
            return error.code, json.loads(body)

    def raw_request(self, method, path, token=None):
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        req = urllib.request.Request(f'{self.base_url}{path}', method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            try:
                return error.code, error.headers, error.read()
            finally:
                error.close()

    def register_user(self, nickname='student'):
        status, payload = self.request('POST', '/api/auth/register', {
            'name': 'Student',
            'nickname': nickname,
            'password': 'secret123',
        })
        self.assertEqual(status, 200, payload)
        return payload['token'], payload['user']

    def create_task(self, token, task_id='task-test'):
        status, payload = self.request('POST', '/api/tasks', {
            'id': task_id,
            'title': 'Test task',
            'subject': 'Math',
            'dueAt': '',
            'pool': 'todo',
            'priority': 'medium',
            'note': '',
            'completed': False,
        }, token=token)
        self.assertEqual(status, 201, payload)
        return task_id

    def avatar_payload(self, raw=None, filename='avatar.png', content_type='image/png'):
        png = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
        )
        return {
            'filename': filename,
            'contentType': content_type,
            'data': base64.b64encode(raw if raw is not None else png).decode('ascii'),
        }

    def first_slot_for(self, user_id, date_key):
        conn = server.get_db()
        try:
            slots = server.effective_slots_for_date(conn, user_id, date_key)
        finally:
            conn.close()
        self.assertTrue(slots)
        return slots[0]

    def schedule_payload(self, user_id, task_id='task-test', **overrides):
        date_key = overrides.pop('date', server.today_key())
        slot_date_key = date_key if server.is_valid_date_key(date_key) else server.today_key()
        slot = self.first_slot_for(user_id, slot_date_key)
        payload = {
            'taskId': task_id,
            'date': date_key,
            'slotKey': server.slot_key(date_key, slot),
            'slotLabel': slot['label'],
            'slotStart': slot['start'],
            'slotEnd': slot['end'],
            'durationMinutes': 1,
            'note': '',
        }
        payload.update(overrides)
        return payload

    def test_schedule_payload_rejects_dirty_values(self):
        token, user = self.register_user()
        self.create_task(token)

        cases = [
            ({'date': '2026-99-99'}, 'date must be a valid YYYY-MM-DD date'),
            ({'slotStart': '25:00'}, 'taskId, date, slotKey, slotStart and slotEnd are required'),
            ({'slotKey': f'{server.today_key()}-missing'}, 'time slot does not exist for this date'),
            ({'sortOrder': float('nan')}, 'sortOrder must be a finite number'),
            ({'sortOrder': float('inf')}, 'sortOrder must be a finite number'),
            ({'slotLabel': 'x' * 41}, 'slotLabel must be at most 40 characters'),
        ]

        for overrides, expected_error in cases:
            with self.subTest(overrides=overrides):
                payload = self.schedule_payload(user['id'], **overrides)
                status, body = self.request('POST', '/api/schedule-items', payload, token=token)
                self.assertEqual(status, 400, body)
                self.assertEqual(body.get('error'), expected_error)

    def test_valid_schedule_create_still_succeeds(self):
        token, user = self.register_user()
        self.create_task(token)
        status, body = self.request('POST', '/api/schedule-items', self.schedule_payload(user['id']), token=token)
        self.assertEqual(status, 201, body)

    def test_foreign_keys_are_enforced_on_new_connections(self):
        token, user = self.register_user()
        date_key = server.today_key()
        slot = self.first_slot_for(user['id'], date_key)
        conn = server.get_db()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    '''
                    INSERT INTO schedule_items
                    (id, user_id, task_id, schedule_date, slot_key, slot_label, slot_start, slot_end,
                     duration_minutes, sort_order, note, completed, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        'schedule-orphan',
                        user['id'],
                        'missing-task',
                        date_key,
                        server.slot_key(date_key, slot),
                        slot['label'],
                        slot['start'],
                        slot['end'],
                        1,
                        1024,
                        '',
                        0,
                        server.now_iso(),
                        server.now_iso(),
                    ),
                )
        finally:
            conn.close()

    def test_concurrent_capacity_check_cannot_overfill_slot(self):
        token, user = self.register_user()
        self.create_task(token)
        payload = self.schedule_payload(user['id'])
        payload['durationMinutes'] = server.minutes_between(payload['slotStart'], payload['slotEnd'])

        def post_schedule():
            return self.request('POST', '/api/schedule-items', payload, token=token)[0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            statuses = sorted(executor.map(lambda _: post_schedule(), range(2)))

        self.assertEqual(statuses, [201, 400])
        conn = server.get_db()
        try:
            used = conn.execute(
                '''
                SELECT COALESCE(SUM(duration_minutes), 0)
                FROM schedule_items
                WHERE user_id = ? AND schedule_date = ? AND slot_key = ?
                ''',
                (user['id'], payload['date'], payload['slotKey']),
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(int(used), payload['durationMinutes'])

    def test_successful_login_verifies_password_once(self):
        self.register_user('login-user')
        original_verify = server.verify_password
        calls = []

        def counting_verify(password, stored_hash):
            calls.append(password)
            return original_verify(password, stored_hash)

        server.verify_password = counting_verify
        try:
            status, body = self.request('POST', '/api/auth/login', {
                'nickname': 'LOGIN-USER',
                'password': 'secret123',
            })
        finally:
            server.verify_password = original_verify

        self.assertEqual(status, 200, body)
        self.assertEqual(calls, ['secret123'])

    def test_operation_logs_use_forwarded_ip_from_trusted_proxy(self):
        self.register_user('proxy-user')

        status, body = self.request(
            'POST',
            '/api/auth/login',
            {
                'nickname': 'proxy-user',
                'password': 'secret123',
            },
            extra_headers={'X-Forwarded-For': '203.0.113.9, 10.0.0.5'},
        )

        self.assertEqual(status, 200, body)
        conn = server.get_db()
        try:
            row = conn.execute(
                '''
                SELECT ip
                FROM operation_logs
                WHERE action = 'auth.login'
                ORDER BY id DESC
                LIMIT 1
                '''
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row['ip'], '203.0.113.9')

    def test_avatar_upload_static_access_replacement_and_delete(self):
        token, user = self.register_user('avatar-user')
        self.assertEqual(user.get('avatarUrl'), '')

        status, body = self.request('POST', '/api/auth/avatar', self.avatar_payload(), token=token)
        self.assertEqual(status, 200, body)
        avatar_url = body['user']['avatarUrl']
        self.assertTrue(avatar_url.startswith('/uploads/avatars/user-'))
        first_filename = avatar_url.split('/uploads/avatars/', 1)[1].split('?', 1)[0]
        first_path = server.avatar_dir() / first_filename
        self.assertTrue(first_path.is_file())

        status, headers, raw = self.raw_request('GET', avatar_url)
        self.assertEqual(status, 200)
        self.assertEqual(headers.get_content_type(), 'image/png')
        self.assertTrue(raw.startswith(b'\x89PNG\r\n\x1a\n'))

        status, body = self.request('POST', '/api/auth/avatar', self.avatar_payload(), token=token)
        self.assertEqual(status, 200, body)
        second_url = body['user']['avatarUrl']
        second_filename = second_url.split('/uploads/avatars/', 1)[1].split('?', 1)[0]
        self.assertNotEqual(first_filename, second_filename)
        self.assertFalse(first_path.exists())
        self.assertTrue((server.avatar_dir() / second_filename).is_file())

        status, body = self.request('DELETE', '/api/auth/avatar', token=token)
        self.assertEqual(status, 200, body)
        self.assertEqual(body['user']['avatarUrl'], '')
        self.assertFalse((server.avatar_dir() / second_filename).exists())

    def test_avatar_upload_rejects_unauthorized_and_invalid_images(self):
        status, body = self.request('POST', '/api/auth/avatar', self.avatar_payload())
        self.assertEqual(status, 401, body)

        token, _ = self.register_user('avatar-invalid')
        cases = [
            self.avatar_payload(filename='avatar.jpg', content_type='image/png'),
            self.avatar_payload(raw=b'not an image'),
            self.avatar_payload(raw=b'\x89PNG\r\n\x1a\n' + (b'x' * server.MAX_AVATAR_BYTES)),
        ]
        for payload in cases:
            with self.subTest(payload={key: payload[key] for key in ('filename', 'contentType')}):
                status, body = self.request('POST', '/api/auth/avatar', payload, token=token)
                self.assertEqual(status, 400, body)

    def test_avatar_color_updates_for_text_avatar(self):
        token, user = self.register_user('avatar-color')
        self.assertEqual(user.get('avatarColor'), server.DEFAULT_AVATAR_COLOR)

        status, body = self.request('PUT', '/api/auth/avatar-color', {'color': '#123abc'}, token=token)
        self.assertEqual(status, 200, body)
        self.assertEqual(body['user']['avatarColor'], '#123abc')
        self.assertEqual(body['user']['avatarUrl'], '')

        status, body = self.request('GET', '/api/auth/me', token=token)
        self.assertEqual(status, 200, body)
        self.assertEqual(body['user']['avatarColor'], '#123abc')

        status, body = self.request('PUT', '/api/auth/avatar-color', {'color': 'javascript:bad'}, token=token)
        self.assertEqual(status, 400, body)

    def test_avatar_static_path_rejects_traversal(self):
        status, _, _ = self.raw_request('GET', '/uploads/avatars/../todo-list.db')
        self.assertEqual(status, 404)

    def test_frontend_uses_due_date_task_grouping(self):
        app_js = Path('app.js').read_text(encoding='utf-8')
        self.assertIn('todoTasksByDueDate()', app_js)
        self.assertIn('const tasks = this.todoTasksByDueDate[key] || []', app_js)
        self.assertIn('return this.todoTasksByDueDate[key] || []', app_js)
        self.assertNotIn(
            "this.filteredTasks.filter(task => task.dueAt && this.taskPool(task) === 'todo' && task.dueAt.startsWith(key))",
            app_js,
        )


if __name__ == '__main__':
    unittest.main()
