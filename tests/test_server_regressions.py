import concurrent.futures
import base64
import json
import os
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

    def stream_request(self, path, payload, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(f'{self.base_url}{path}', data=data, method='POST', headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, response.headers, response.read().decode('utf-8')
        except urllib.error.HTTPError as error:
            try:
                body = error.read().decode('utf-8') or '{}'
                return error.code, error.headers, body
            finally:
                error.close()

    def parse_sse(self, raw):
        events = []
        for block in raw.strip().split('\n\n'):
            event = 'message'
            data_lines = []
            for line in block.splitlines():
                if line.startswith('event:'):
                    event = line.split(':', 1)[1].strip()
                elif line.startswith('data:'):
                    data_lines.append(line.split(':', 1)[1].strip())
            if data_lines:
                events.append((event, json.loads('\n'.join(data_lines))))
        return events

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

    def test_ai_context_uses_incomplete_timeline_tasks_and_reports_truncation(self):
        limit = server.AI_CONTEXT_TASK_LIMIT
        tasks = [
            {
                'id': 'task-completed',
                'title': 'Completed task',
                'subject': 'Math',
                'dueAt': '',
                'priority': 'medium',
                'note': '',
                'completed': True,
                'pool': 'todo',
            },
            {
                'id': 'task-schedule',
                'title': 'Schedule task',
                'subject': 'Math',
                'dueAt': '',
                'priority': 'medium',
                'note': '',
                'completed': False,
                'pool': 'schedule',
            },
            {
                'id': 'task-habit',
                'title': 'Habit task',
                'subject': 'Math',
                'dueAt': '',
                'priority': 'medium',
                'note': '',
                'completed': False,
                'pool': 'habit',
            },
            {
                'id': 'task-arrangement',
                'title': 'Arrangement task',
                'subject': 'Math',
                'dueAt': '',
                'priority': 'medium',
                'note': '',
                'completed': False,
                'pool': 'arrangement',
            },
        ]
        tasks.extend({
            'id': f'task-{index}',
            'title': f'Task {index}',
            'subject': 'Math',
            'dueAt': '',
            'priority': 'medium',
            'note': '',
            'completed': False,
            'pool': 'todo',
        } for index in range(limit + 2))

        included, context = server.ai_context_tasks(tasks)

        self.assertEqual(len(included), limit)
        self.assertTrue(all(not task['completed'] and task['pool'] == 'todo' for task in included))
        self.assertEqual(context['taskSelection']['status'], 'incomplete_timeline_only')
        self.assertEqual(context['taskSelection']['pool'], 'todo')
        self.assertEqual(context['taskSelection']['totalIncompleteTimelineTaskCount'], limit + 2)
        self.assertEqual(context['taskSelection']['includedTaskCount'], limit)
        self.assertEqual(context['taskSelection']['omittedIncompleteTimelineTaskCount'], 2)
        self.assertTrue(context['taskSelection']['truncated'])
        context_json = json.dumps(context, ensure_ascii=False)
        self.assertNotIn('task-completed', context_json)
        self.assertNotIn('task-schedule', context_json)
        self.assertNotIn('task-habit', context_json)
        self.assertNotIn('task-arrangement', context_json)

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

    def test_ai_chat_requires_login_and_configured_key(self):
        original_key = os.environ.pop('DEEPSEEK_API_KEY', None)
        try:
            status, body = self.request('POST', '/api/ai/chat', {'message': '创建一个任务'})
            self.assertEqual(status, 401, body)

            token, _ = self.register_user('ai-no-key')
            status, body = self.request('POST', '/api/ai/chat', {'message': '创建一个任务'}, token=token)
            self.assertEqual(status, 503, body)
            self.assertEqual(body.get('error'), 'DeepSeek API key is not configured')
        finally:
            if original_key is not None:
                os.environ['DEEPSEEK_API_KEY'] = original_key

    def test_ai_chat_returns_actions_without_writing_tasks(self):
        token, _ = self.register_user('ai-actions')
        self.create_task(token, 'task-ai-existing')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_call = server.TodoHandler.call_deepseek_chat
        captured = {}

        def fake_call(handler, messages):
            captured['messages'] = messages
            return json.dumps({
                'reply': '我整理了两条待审批指令。',
                'actions': [
                    {
                        'type': 'create_task',
                        'task': {
                            'title': 'Read chapter 3',
                            'subject': 'English B',
                            'dueAt': '2026-06-18T23:00:00',
                            'priority': 'medium',
                            'note': 'Annotate key paragraphs',
                        },
                    },
                    {
                        'type': 'update_task',
                        'targetTaskId': 'task-ai-existing',
                        'patch': {'note': 'Review mistakes'},
                    },
                ],
            })

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.call_deepseek_chat = fake_call
            status, body = self.request('POST', '/api/ai/chat', {
                'message': '创建阅读任务，并修改已有任务备注',
                'clientNow': '2026-06-17T12:00:00.000Z',
                'timezone': 'Asia/Shanghai',
            }, token=token)
        finally:
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 200, body)
        self.assertEqual(body.get('reply'), '我整理了两条待审批指令。')
        self.assertEqual([action['type'] for action in body['actions']], ['create_task', 'update_task'])
        self.assertIn('task-ai-existing', captured['messages'][-1]['content'])

        status, tasks_body = self.request('GET', '/api/tasks', token=token)
        self.assertEqual(status, 200, tasks_body)
        tasks = tasks_body['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['id'], 'task-ai-existing')
        self.assertEqual(tasks[0]['note'], '')

    def test_ai_chat_rejects_unsafe_or_invalid_actions(self):
        token, _ = self.register_user('ai-rejects')
        self.create_task(token, 'task-ai-reject')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_call = server.TodoHandler.call_deepseek_chat

        def fake_call(handler, messages):
            return json.dumps({
                'reply': '我找到了一些候选操作。',
                'actions': [
                    {'type': 'delete_task', 'targetTaskId': 'task-ai-reject'},
                    {'type': 'update_task', 'targetTaskId': 'task-ai-reject', 'patch': {'completed': True}},
                    {
                        'type': 'create_task',
                        'task': {
                            'title': 'Bad task',
                            'subject': 'x' * 41,
                            'dueAt': '',
                            'priority': 'medium',
                            'note': '',
                        },
                    },
                ],
            })

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.call_deepseek_chat = fake_call
            status, body = self.request('POST', '/api/ai/chat', {'message': '做点危险操作'}, token=token)
        finally:
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 200, body)
        self.assertEqual(body['actions'], [])
        self.assertEqual(len(body['rejectedActions']), 3)

    def test_ai_chat_stream_sends_deltas_then_done_actions(self):
        token, _ = self.register_user('ai-stream')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_stream = server.TodoHandler.stream_deepseek_chat

        def fake_stream(handler, messages):
            yield '我会创建一个待审批任务。'
            yield '\n<AI_ACTIONS_'
            yield 'JSON>{"actions":[{"type":"create_task","task":{"title":"Stream task","subject":"Math","dueAt":"","priority":"low","note":"From stream"}}]}</AI_ACTIONS_JSON>'

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.stream_deepseek_chat = fake_stream
            status, headers, raw = self.stream_request('/api/ai/chat-stream', {
                'message': '创建一个流式任务',
                'clientNow': '2026-06-18T12:00:00.000Z',
                'timezone': 'Asia/Shanghai',
            }, token=token)
        finally:
            server.TodoHandler.stream_deepseek_chat = original_stream
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 200, raw)
        self.assertEqual(headers.get_content_type(), 'text/event-stream')
        events = self.parse_sse(raw)
        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[0][0], 'delta')
        delta_text = ''.join(event[1].get('text', '') for event in events if event[0] == 'delta')
        self.assertIn('我会创建一个待审批任务。', delta_text)
        self.assertEqual(events[-1][0], 'done')
        self.assertEqual(events[-1][1]['reply'], '我会创建一个待审批任务。')
        self.assertEqual(events[-1][1]['actions'][0]['type'], 'create_task')
        self.assertNotIn('AI_ACTIONS_JSON', delta_text)

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

    def test_admin_users_include_avatar_fields(self):
        admin_token, admin_user = self.register_user('admin-avatar-list')
        student_token, student = self.register_user('student-avatar-list')
        conn = server.get_db()
        try:
            conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (admin_user['id'],))
            conn.commit()
        finally:
            conn.close()

        status, body = self.request('PUT', '/api/auth/avatar-color', {'color': '#123abc'}, token=student_token)
        self.assertEqual(status, 200, body)
        status, body = self.request('POST', '/api/auth/avatar', self.avatar_payload(), token=student_token)
        self.assertEqual(status, 200, body)
        avatar_url = body['user']['avatarUrl']

        status, body = self.request('GET', '/api/admin/users', token=admin_token)
        self.assertEqual(status, 200, body)
        users_by_id = {user['id']: user for user in body['users']}
        self.assertIn(student['id'], users_by_id)
        self.assertEqual(users_by_id[student['id']]['avatarUrl'], avatar_url)
        self.assertEqual(users_by_id[student['id']]['avatarColor'], '#123abc')

    def test_frontend_uses_due_date_task_grouping(self):
        app_js = Path('app.js').read_text(encoding='utf-8')
        self.assertIn('todoTasksByDueDate()', app_js)
        self.assertIn('const tasks = this.todoTasksByDueDate[key] || []', app_js)
        self.assertIn('return this.todoTasksByDueDate[key] || []', app_js)
        self.assertNotIn(
            "this.filteredTasks.filter(task => task.dueAt && this.taskPool(task) === 'todo' && task.dueAt.startsWith(key))",
            app_js,
        )

    def test_admin_user_list_renders_avatar_column(self):
        index_html = Path('index.html').read_text(encoding='utf-8')
        app_js = Path('app.js').read_text(encoding='utf-8')
        style_css = Path('style.css').read_text(encoding='utf-8')

        self.assertIn('label="头像"', index_html)
        self.assertIn(':data="paginatedAdminUsers"', index_html)
        self.assertIn('class="admin-user-avatar"', index_html)
        self.assertLess(
            index_html.index('prop="id" label="ID"'),
            index_html.index('class="admin-user-avatar"'),
        )
        self.assertIn('adminUserAvatarText(row)', index_html)
        self.assertIn('adminUserAvatarStyle(row)', index_html)
        self.assertIn(':page-size="adminUsersPageSize"', index_html)
        self.assertIn('adminUserAvatarText(user)', app_js)
        self.assertIn('adminUserAvatarStyle(user)', app_js)
        self.assertIn('adminUsersPageSize: 20', app_js)
        self.assertIn('paginatedAdminUsers()', app_js)
        self.assertIn('.admin-user-avatar', style_css)
        self.assertIn('border-radius: 50%;', style_css)


if __name__ == '__main__':
    unittest.main()
