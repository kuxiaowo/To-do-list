import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path

import server


class ProjectWorkflowTests(unittest.TestCase):
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
                raw = response.read().decode('utf-8')
                return response.status, json.loads(raw or '{}')
        except urllib.error.HTTPError as error:
            try:
                raw = error.read().decode('utf-8') or '{}'
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = {'raw': raw}
                return error.code, payload
            finally:
                error.close()

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

    def register_user(self, nickname='student', name='Student', password='secret123'):
        status, payload = self.request('POST', '/api/auth/register', {
            'name': name,
            'nickname': nickname,
            'password': password,
        })
        self.assertEqual(status, HTTPStatus.OK, payload)
        return payload['token'], payload['user']

    def make_admin(self, user_id):
        with server.get_db() as conn:
            conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
            conn.commit()

    def create_task(self, token, task_id='task-test', **overrides):
        task = {
            'id': task_id,
            'title': 'Test task',
            'subject': 'Math',
            'dueAt': '2026-06-20T23:59:00',
            'pool': 'todo',
            'priority': 'medium',
            'note': '',
            'completed': False,
        }
        task.update(overrides)
        status, payload = self.request('POST', '/api/tasks', task, token=token)
        self.assertEqual(status, HTTPStatus.CREATED, payload)
        return payload['task']

    def first_slot_for_date(self, date_key):
        weekday = server.weekday_for_date(date_key)
        slot = server.DEFAULT_WEEK_SLOTS[weekday][0]
        return {
            **slot,
            'key': server.slot_key(date_key, slot),
            'duration': server.minutes_between(slot['start'], slot['end']),
        }

    def create_schedule_item(self, token, task_id, date_key='2026-06-22', duration=30):
        slot = self.first_slot_for_date(date_key)
        status, payload = self.request('POST', '/api/schedule-items', {
            'taskId': task_id,
            'date': date_key,
            'slotKey': slot['key'],
            'slotLabel': slot['label'],
            'slotStart': slot['start'],
            'slotEnd': slot['end'],
            'durationMinutes': duration,
            'note': 'schedule note',
        }, token=token)
        self.assertEqual(status, HTTPStatus.CREATED, payload)
        return payload['id'], slot

    def test_runtime_static_and_guest_readonly_contracts(self):
        status, payload = self.request('GET', '/api/health')
        self.assertEqual(status, HTTPStatus.OK)
        self.assertTrue(payload['ok'])

        for path, collection in [
            ('/api/tasks', 'tasks'),
            ('/api/schedule-items', 'items'),
            ('/api/habits', 'habits'),
        ]:
            status, payload = self.request('GET', path)
            self.assertEqual(status, HTTPStatus.OK, path)
            self.assertEqual(payload[collection], [])
            self.assertTrue(payload['readOnly'])

        status, payload = self.request('GET', '/api/schedule-config')
        self.assertEqual(status, HTTPStatus.OK)
        self.assertTrue(payload['readOnly'])
        self.assertIn('defaultWeekSlots', payload)

        status, headers, body = self.raw_request('HEAD', '/index.html')
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(body, b'')
        self.assertIn('text/html', headers.get('Content-Type', ''))

        status, _, _ = self.raw_request('GET', '/server.py')
        self.assertEqual(status, HTTPStatus.NOT_FOUND)

    def test_auth_profile_and_session_lifecycle(self):
        status, payload = self.request('POST', '/api/auth/register', {
            'name': 'Short Password',
            'nickname': 'short-password',
            'password': '123',
        })
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload['error'], 'password must be at least 6 characters')

        token, user = self.register_user('student')

        status, payload = self.request('POST', '/api/auth/register', {
            'name': 'Duplicate',
            'nickname': 'STUDENT',
            'password': 'secret123',
        })
        self.assertEqual(status, HTTPStatus.CONFLICT)

        status, payload = self.request('GET', '/api/auth/me', token=token)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload['user']['id'], user['id'])

        status, payload = self.request('PUT', '/api/auth/nickname', {'nickname': 'renamed'}, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)
        self.assertEqual(payload['user']['nickname'], 'renamed')

        status, payload = self.request('PUT', '/api/auth/password', {
            'currentPassword': 'wrong',
            'newPassword': 'newsecret123',
        }, token=token)
        self.assertEqual(status, HTTPStatus.UNAUTHORIZED)

        status, payload = self.request('PUT', '/api/auth/password', {
            'currentPassword': 'secret123',
            'newPassword': 'newsecret123',
        }, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('POST', '/api/auth/login', {
            'nickname': 'renamed',
            'password': 'secret123',
        })
        self.assertEqual(status, HTTPStatus.UNAUTHORIZED)

        status, payload = self.request('POST', '/api/auth/login', {
            'nickname': 'renamed',
            'password': 'newsecret123',
        })
        self.assertEqual(status, HTTPStatus.OK, payload)
        refreshed_token = payload['token']

        status, payload = self.request('POST', '/api/auth/logout', token=refreshed_token)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertTrue(payload['ok'])

        status, payload = self.request('GET', '/api/auth/me', token=refreshed_token)
        self.assertEqual(status, HTTPStatus.UNAUTHORIZED)

    def test_task_crud_user_isolation_and_schedule_cascade(self):
        token_a, _ = self.register_user('alice')
        token_b, _ = self.register_user('bob')
        task = self.create_task(token_a, 'task-owned-by-alice')
        item_id, _ = self.create_schedule_item(token_a, task['id'])

        status, payload = self.request('GET', '/api/tasks', token=token_b)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload['tasks'], [])

        status, payload = self.request('PUT', f"/api/tasks/{task['id']}", {
            **task,
            'title': 'Bob edit',
        }, token=token_b)
        self.assertEqual(status, HTTPStatus.NOT_FOUND)

        status, payload = self.request('PUT', f"/api/tasks/{task['id']}", {
            **task,
            'completed': True,
        }, token=token_a)
        self.assertEqual(status, HTTPStatus.OK, payload)
        self.assertTrue(payload['task']['completed'])

        status, payload = self.request('GET', '/api/schedule-items', token=token_a)
        self.assertEqual(status, HTTPStatus.OK)
        scheduled = next(item for item in payload['items'] if item['id'] == item_id)
        self.assertTrue(scheduled['completed'])

        status, payload = self.request('DELETE', f"/api/tasks/{task['id']}", token=token_a)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('GET', '/api/schedule-items', token=token_a)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertFalse(any(item['id'] == item_id for item in payload['items']))

    def test_schedule_template_day_override_and_item_lifecycle(self):
        token, _ = self.register_user('scheduler')
        task = self.create_task(token, 'task-for-schedule', dueAt='')
        item_id, slot = self.create_schedule_item(token, task['id'], duration=20)

        status, payload = self.request('PUT', f'/api/schedule-items/{item_id}', {
            'note': 'updated note',
            'completed': True,
            'sortOrder': -10,
        }, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('GET', '/api/schedule-items', token=token)
        self.assertEqual(status, HTTPStatus.OK)
        item = next(entry for entry in payload['items'] if entry['id'] == item_id)
        self.assertEqual(item['note'], 'updated note')
        self.assertTrue(item['completed'])

        status, payload = self.request('PUT', '/api/schedule-day-slots/2026-06-22', {
            'slots': [{
                'keyBase': slot['keyBase'],
                'label': slot['label'],
                'start': slot['start'],
                'end': slot['start'],
            }],
        }, token=token)
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)

        status, payload = self.request('PUT', '/api/schedule-day-slots/2026-06-22', {
            'slots': [{
                'keyBase': slot['keyBase'],
                'label': slot['label'],
                'start': slot['start'],
                'end': slot['end'],
            }],
        }, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('GET', '/api/schedule-config', token=token)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn('2026-06-22', payload['dayOverrides'])

        status, payload = self.request('DELETE', '/api/schedule-day-slots/2026-06-22', token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('DELETE', f'/api/schedule-items/{item_id}', token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)

    def test_habit_sync_conflict_and_delete_cleanup(self):
        token, _ = self.register_user('habit-user')
        date_key = server.today_key()
        weekday = server.weekday_for_date(date_key)
        slot = server.DEFAULT_WEEK_SLOTS[weekday][0]

        habit_payload = {
            'id': 'habit-review',
            'title': 'Review vocabulary',
            'subject': 'English B',
            'weekdays': [weekday],
            'slotKeyBase': slot['keyBase'],
            'slotLabel': slot['label'],
            'slotStart': slot['start'],
            'slotEnd': slot['end'],
            'durationMinutes': 15,
            'startDate': date_key,
            'endDate': date_key,
            'priority': 'low',
            'note': '',
            'active': True,
        }
        status, payload = self.request('POST', '/api/habits', habit_payload, token=token)
        self.assertEqual(status, HTTPStatus.CREATED, payload)
        self.assertEqual(payload['habit']['id'], 'habit-review')

        status, payload = self.request('GET', f'/api/schedule-items?from={date_key}&to={date_key}', token=token)
        self.assertEqual(status, HTTPStatus.OK)
        habit_items = [item for item in payload['items'] if item['habitId'] == 'habit-review']
        self.assertEqual(len(habit_items), 1)

        status, payload = self.request('POST', '/api/habits', {
            **habit_payload,
            'id': 'habit-conflict',
            'title': 'Conflicting habit',
            'durationMinutes': server.minutes_between(slot['start'], slot['end']),
        }, token=token)
        self.assertEqual(status, HTTPStatus.CONFLICT)
        self.assertEqual(payload['error'], 'habit schedule conflict')
        self.assertTrue(payload['conflicts'])

        status, payload = self.request('DELETE', '/api/habits/habit-review', token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('GET', f'/api/schedule-items?from={date_key}&to={date_key}', token=token)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertFalse(any(item['habitId'] == 'habit-review' for item in payload['items']))

    def test_feedback_limits_admin_reply_and_permissions(self):
        admin_token, admin_user = self.register_user('admin', name='Admin')
        self.make_admin(admin_user['id'])
        user_token, user = self.register_user('feedback-user')

        status, payload = self.request('GET', '/api/admin/users', token=user_token)
        self.assertEqual(status, HTTPStatus.FORBIDDEN)

        status, payload = self.request('PUT', '/api/admin/feedback-settings', {
            'feedbackLimitPerUser': 1,
        }, token=admin_token)
        self.assertEqual(status, HTTPStatus.OK, payload)
        self.assertEqual(payload['feedbackLimitPerUser'], 1)

        status, payload = self.request('POST', '/api/feedback', {'content': 'First feedback'}, token=user_token)
        self.assertEqual(status, HTTPStatus.CREATED, payload)
        feedback_id = payload['feedback']['id']

        status, payload = self.request('POST', '/api/feedback', {'content': 'Second feedback'}, token=user_token)
        self.assertEqual(status, HTTPStatus.CONFLICT)
        self.assertEqual(payload['error'], 'feedback limit reached')

        status, payload = self.request('PUT', f'/api/admin/feedback/{feedback_id}/reply', {
            'reply': 'Received',
        }, token=admin_token)
        self.assertEqual(status, HTTPStatus.OK, payload)
        self.assertEqual(payload['feedback']['status'], 'replied')

        status, payload = self.request('POST', '/api/feedback', {'content': 'Second feedback'}, token=user_token)
        self.assertEqual(status, HTTPStatus.CREATED, payload)

        status, payload = self.request('GET', '/api/admin/users', token=admin_token)
        self.assertEqual(status, HTTPStatus.OK)
        listed = {entry['id']: entry for entry in payload['users']}
        self.assertIn(user['id'], listed)

        status, payload = self.request('GET', f"/api/admin/users/{user['id']}/logs?page=1&pageSize=10", token=admin_token)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertGreaterEqual(payload['total'], 1)

    def test_admin_readonly_timeline_and_user_delete_cascade(self):
        admin_token, admin_user = self.register_user('admin2', name='Admin')
        self.make_admin(admin_user['id'])
        user_token, user = self.register_user('target-user')
        task = self.create_task(user_token, 'task-before-delete')
        self.create_schedule_item(user_token, task['id'])

        for suffix, key in [
            ('tasks', 'tasks'),
            ('schedule-items', 'items'),
            ('habits', 'habits'),
            ('schedule-config', 'defaultWeekSlots'),
        ]:
            status, payload = self.request('GET', f"/api/admin/users/{user['id']}/{suffix}", token=admin_token)
            self.assertEqual(status, HTTPStatus.OK, suffix)
            self.assertTrue(payload['readOnly'])
            self.assertIn(key, payload)

        status, payload = self.request('DELETE', f"/api/admin/users/{admin_user['id']}", token=admin_token)
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload['error'], 'cannot delete current admin')

        status, payload = self.request('DELETE', f"/api/admin/users/{user['id']}", token=admin_token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        with server.get_db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM users WHERE id = ?', (user['id'],)).fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (user['id'],)).fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM schedule_items WHERE user_id = ?', (user['id'],)).fetchone()[0], 0)

    def test_visit_tracking_admin_traffic_and_frontend_scaffolding(self):
        admin_token, admin_user = self.register_user('traffic-admin', name='Admin')
        self.make_admin(admin_user['id'])

        status, payload = self.request('POST', '/api/visits', {'page': 'home'}, token=admin_token)
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)

        status, payload = self.request('POST', '/api/visits', {'page': 'admin', 'path': '/admin'}, token=admin_token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('GET', '/api/admin/traffic/summary?view=6h&page=1&pageSize=5', token=admin_token)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload['trafficView'], '6h')
        self.assertGreaterEqual(payload['totalVisits'], 1)
        self.assertTrue(payload['recentVisits'])

        app_js = Path('app.js').read_text(encoding='utf-8')
        index_html = Path('index.html').read_text(encoding='utf-8')
        style_css = Path('style.css').read_text(encoding='utf-8')
        for marker in [
            'settingsDialogVisible',
            'aiApprovalVisible',
            'feedbackDialogVisible',
            'habitDialogVisible',
            'scheduleDialogVisible',
            "adminSection === 'traffic'",
            "adminSection === 'aiUsage'",
        ]:
            self.assertIn(marker, index_html + app_js)
        self.assertIn('@media (max-width: 720px)', style_css)
        self.assertIn('[data-theme="dark"]', style_css)

    def test_api_documentation_mentions_core_endpoints(self):
        api_doc = Path('API.md').read_text(encoding='utf-8')
        user_guide = Path('docs/USER_GUIDE.md').read_text(encoding='utf-8')
        deploy_script = Path('deploy-first-run.sh').read_text(encoding='utf-8')

        for endpoint in [
            '/api/auth/register',
            '/api/auth/login',
            '/api/tasks',
            '/api/schedule-items',
            '/api/habits',
            '/api/schedule-config',
            '/api/feedback',
        ]:
            self.assertIn(endpoint, api_doc)

        self.assertIn('TODO_PORT', deploy_script)
        self.assertIn('TODO_ADMIN_NICKNAME', deploy_script)
        self.assertIn('管理员', user_guide)


if __name__ == '__main__':
    unittest.main()
