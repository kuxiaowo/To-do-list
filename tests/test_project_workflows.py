import base64
import json
import os
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

WEB_DIR = Path('web')
INDEX_HTML_PATH = WEB_DIR / 'index.html'
APP_JS_PATH = WEB_DIR / 'app.js'
STYLE_CSS_PATH = WEB_DIR / 'style.css'
API_DOC_PATH = Path('docs') / 'zh-CN' / 'API.md'


class ProjectWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.original_data_dir = server.DATA_DIR
        self.original_db_path = server.DB_PATH
        self.original_iterations = server.PASSWORD_ITERATIONS
        self.original_legacy_auth = server.LEGACY_AUTH_ENABLED
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        server.DATA_DIR = Path(self.temp_dir.name)
        server.DB_PATH = server.DATA_DIR / 'todo-list.db'
        server.PASSWORD_ITERATIONS = 1_000
        server.LEGACY_AUTH_ENABLED = True
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
        server.LEGACY_AUTH_ENABLED = self.original_legacy_auth
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

    def test_schedule_item_query_range_is_separate_from_habit_sync_range(self):
        token, user = self.register_user('schedule-range-user')
        today = server.today_key()
        past = server.add_days_key(today, -1)
        past_task = self.create_task(token, 'past-schedule-task', dueAt='')
        past_item_id, _ = self.create_schedule_item(token, past_task['id'], date_key=past, duration=1)

        weekday = server.weekday_for_date(today)
        slot = server.DEFAULT_WEEK_SLOTS[weekday][0]
        now = server.now_iso()
        with server.get_db() as conn:
            conn.execute(
                '''
                INSERT INTO tasks
                (id, user_id, title, subject, due_at, pool, priority, note, completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, '', 'habit', 'low', '', 0, ?, ?)
                ''',
                ('habit-range-task', user['id'], 'Range habit', 'Math', now, now),
            )
            conn.execute(
                '''
                INSERT INTO habits
                (id, user_id, task_id, weekdays_json, slot_key_base, slot_label, slot_start, slot_end,
                 duration_minutes, start_date, end_date, active, archived, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
                ''',
                (
                    'habit-range',
                    user['id'],
                    'habit-range-task',
                    json.dumps([weekday]),
                    slot['keyBase'],
                    slot['label'],
                    slot['start'],
                    slot['end'],
                    1,
                    today,
                    today,
                    now,
                    now,
                ),
            )
            conn.commit()

        status, payload = self.request(
            'GET',
            f'/api/schedule-items?from={past}&to={past}&syncFrom={today}&syncTo={today}',
            token=token,
        )
        self.assertEqual(status, HTTPStatus.OK, payload)
        self.assertEqual([item['id'] for item in payload['items']], [past_item_id])

        with server.get_db() as conn:
            generated_count = conn.execute(
                '''
                SELECT COUNT(*)
                FROM schedule_items
                WHERE user_id = ? AND habit_id = ? AND schedule_date = ?
                ''',
                (user['id'], 'habit-range', today),
            ).fetchone()[0]
        self.assertEqual(generated_count, 1)

    def test_habit_overlap_is_created_and_marked_for_cleanup(self):
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
        self.assertEqual(status, HTTPStatus.CREATED, payload)

        status, payload = self.request('GET', f'/api/schedule-items?from={date_key}&to={date_key}', token=token)
        self.assertEqual(status, HTTPStatus.OK)
        overlapping = [item for item in payload['items'] if item['habitId'] in {'habit-review', 'habit-conflict'}]
        self.assertEqual(len(overlapping), 2)
        self.assertTrue(all(item['hasConflict'] for item in overlapping))
        self.assertTrue(all(len(item['conflictIds']) == 1 for item in overlapping))

        status, payload = self.request('DELETE', '/api/habits/habit-review', token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('GET', f'/api/schedule-items?from={date_key}&to={date_key}', token=token)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertFalse(any(item['habitId'] == 'habit-review' for item in payload['items']))

    def test_delete_habit_removes_all_incomplete_instances_and_keeps_completed_history(self):
        token, user = self.register_user('habit-delete-all-user')
        today = server.today_key()
        past = server.add_days_key(today, -1)
        future = server.add_days_key(today, 1)
        weekday = server.weekday_for_date(today)
        status, payload = self.request('POST', '/api/habits', {
            'id': 'habit-delete-all',
            'title': 'Delete incomplete habit instances',
            'subject': 'Math',
            'weekdays': [weekday],
            'startTime': '08:00',
            'durationMinutes': 30,
            'startDate': today,
            'endDate': today,
            'priority': 'medium',
            'note': '',
            'active': True,
        }, token=token)
        self.assertEqual(status, HTTPStatus.CREATED, payload)
        task_id = payload['habit']['taskId']

        now = server.now_iso()
        with server.get_db() as conn:
            conn.execute(
                'DELETE FROM schedule_items WHERE user_id = ? AND habit_id = ?',
                (user['id'], 'habit-delete-all'),
            )
            for date_key in (past, today, future):
                for completed in (0, 1):
                    suffix = 'complete' if completed else 'incomplete'
                    conn.execute(
                        '''
                        INSERT INTO schedule_items
                        (id, user_id, task_id, habit_id, schedule_date, slot_key, slot_label,
                         slot_start, slot_end, item_start, item_end, duration_minutes, sort_order,
                         note, completed, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'Habit', '08:00', '08:30', '08:00', '08:30',
                                30, 1024, '', ?, ?, ?)
                        ''',
                        (
                            f'instance-{date_key}-{suffix}',
                            user['id'],
                            task_id,
                            'habit-delete-all',
                            date_key,
                            f'{date_key}-habit-0800',
                            completed,
                            now,
                            now,
                        ),
                    )
            conn.execute(
                '''
                INSERT INTO habit_instance_exclusions
                (user_id, habit_id, schedule_date, created_at)
                VALUES (?, ?, ?, ?)
                ''',
                (user['id'], 'habit-delete-all', today, now),
            )
            conn.commit()

        status, payload = self.request('DELETE', '/api/habits/habit-delete-all', token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        with server.get_db() as conn:
            remaining = conn.execute(
                '''
                SELECT id, completed
                FROM schedule_items
                WHERE user_id = ? AND habit_id = ?
                ORDER BY id
                ''',
                (user['id'], 'habit-delete-all'),
            ).fetchall()
            archived = conn.execute(
                'SELECT archived, active FROM habits WHERE user_id = ? AND id = ?',
                (user['id'], 'habit-delete-all'),
            ).fetchone()
            exclusion_count = conn.execute(
                'SELECT COUNT(*) FROM habit_instance_exclusions WHERE user_id = ? AND habit_id = ?',
                (user['id'], 'habit-delete-all'),
            ).fetchone()[0]
        self.assertEqual(len(remaining), 3)
        self.assertTrue(all(bool(row['completed']) for row in remaining))
        self.assertEqual((archived['archived'], archived['active']), (1, 0))
        self.assertEqual(exclusion_count, 0)

        status, payload = self.request(
            'GET',
            f'/api/schedule-items?from={past}&to={future}&syncFrom={today}&syncTo={future}',
            token=token,
        )
        self.assertEqual(status, HTTPStatus.OK, payload)
        retained = [item for item in payload['items'] if item['habitId'] == 'habit-delete-all']
        self.assertEqual(len(retained), 3)
        self.assertTrue(all(item['completed'] for item in retained))

    def test_delete_habit_instance_permanently_skips_only_that_date(self):
        token, user = self.register_user('habit-instance-delete-user')
        other_token, _ = self.register_user('habit-instance-delete-other')
        today = server.today_key()
        tomorrow = server.add_days_key(today, 1)
        habit_payload = {
            'id': 'habit-instance-delete',
            'title': 'Delete one habit instance',
            'subject': 'English',
            'weekdays': sorted({
                int(server.weekday_for_date(today)),
                int(server.weekday_for_date(tomorrow)),
            }),
            'startTime': '09:00',
            'durationMinutes': 20,
            'startDate': today,
            'endDate': tomorrow,
            'priority': 'low',
            'note': '',
            'active': True,
        }
        status, payload = self.request('POST', '/api/habits', habit_payload, token=token)
        self.assertEqual(status, HTTPStatus.CREATED, payload)

        schedule_path = (
            f'/api/schedule-items?from={today}&to={tomorrow}'
            f'&syncFrom={today}&syncTo={tomorrow}'
        )
        status, payload = self.request('GET', schedule_path, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)
        instances = {
            item['date']: item
            for item in payload['items']
            if item['habitId'] == 'habit-instance-delete'
        }
        self.assertEqual(set(instances), {today, tomorrow})

        today_id = instances[today]['id']
        status, payload = self.request(
            'DELETE',
            f'/api/schedule-items/{today_id}',
            token=other_token,
        )
        self.assertEqual(status, HTTPStatus.NOT_FOUND, payload)

        status, payload = self.request('DELETE', f'/api/schedule-items/{today_id}', token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)
        status, payload = self.request('DELETE', f'/api/schedule-items/{today_id}', token=token)
        self.assertEqual(status, HTTPStatus.NOT_FOUND, payload)

        status, payload = self.request('GET', schedule_path, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)
        instances = [
            item for item in payload['items']
            if item['habitId'] == 'habit-instance-delete'
        ]
        self.assertEqual([item['date'] for item in instances], [tomorrow])

        status, payload = self.request('PUT', '/api/habits/habit-instance-delete', {
            **habit_payload,
            'title': 'Updated habit after one skipped date',
        }, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)
        status, payload = self.request('GET', schedule_path, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)
        instances = [
            item for item in payload['items']
            if item['habitId'] == 'habit-instance-delete'
        ]
        self.assertEqual([item['date'] for item in instances], [tomorrow])

        tomorrow_id = instances[0]['id']
        status, payload = self.request(
            'PUT',
            f'/api/schedule-items/{tomorrow_id}',
            {'completed': True},
            token=token,
        )
        self.assertEqual(status, HTTPStatus.OK, payload)
        status, payload = self.request(
            'DELETE',
            f'/api/schedule-items/{tomorrow_id}',
            token=token,
        )
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('GET', schedule_path, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)
        self.assertFalse(any(
            item['habitId'] == 'habit-instance-delete'
            for item in payload['items']
        ))
        with server.get_db() as conn:
            excluded_dates = {
                row['schedule_date']
                for row in conn.execute(
                    '''
                    SELECT schedule_date
                    FROM habit_instance_exclusions
                    WHERE user_id = ? AND habit_id = ?
                    ''',
                    (user['id'], 'habit-instance-delete'),
                ).fetchall()
            }
        self.assertEqual(excluded_dates, {today, tomorrow})

    def test_habit_uses_exact_start_time_without_template_slot(self):
        token, _ = self.register_user('exact-habit-user')
        date_key = server.today_key()
        weekday = server.weekday_for_date(date_key)
        status, payload = self.request('POST', '/api/habits', {
            'id': 'habit-exact-time',
            'title': 'Exact habit',
            'subject': 'Math',
            'weekdays': [weekday],
            'startTime': '08:07',
            'durationMinutes': 26,
            'startDate': date_key,
            'endDate': date_key,
            'priority': 'medium',
            'note': '',
            'active': True,
        }, token=token)
        self.assertEqual(status, HTTPStatus.CREATED, payload)
        self.assertEqual(payload['habit']['startTime'], '08:07')
        self.assertEqual(payload['habit']['endTime'], '08:33')

        status, payload = self.request(
            'GET',
            f'/api/schedule-items?from={date_key}&to={date_key}',
            token=token,
        )
        self.assertEqual(status, HTTPStatus.OK, payload)
        item = next(entry for entry in payload['items'] if entry['habitId'] == 'habit-exact-time')
        self.assertEqual(item['startTime'], '08:07')
        self.assertEqual(item['endTime'], '08:33')

    def test_completed_schedule_item_does_not_conflict_with_active_item(self):
        token, _ = self.register_user('completed-conflict-user')
        date_key = '2026-06-22'
        completed_task = self.create_task(token, 'task-completed-conflict')
        active_task = self.create_task(token, 'task-active-conflict')
        completed_item_id, _ = self.create_schedule_item(token, completed_task['id'], date_key, duration=30)
        active_item_id, _ = self.create_schedule_item(token, active_task['id'], date_key, duration=30)

        status, payload = self.request(
            'GET',
            f'/api/schedule-items?from={date_key}&to={date_key}',
            token=token,
        )
        self.assertEqual(status, HTTPStatus.OK, payload)
        overlapping = {
            item['id']: item
            for item in payload['items']
            if item['id'] in {completed_item_id, active_item_id}
        }
        self.assertEqual(set(overlapping), {completed_item_id, active_item_id})
        self.assertTrue(all(item['hasConflict'] for item in overlapping.values()))

        status, payload = self.request('PUT', f"/api/tasks/{completed_task['id']}", {
            **completed_task,
            'completed': True,
        }, token=token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request(
            'GET',
            f'/api/schedule-items?from={date_key}&to={date_key}',
            token=token,
        )
        self.assertEqual(status, HTTPStatus.OK, payload)
        overlapping = {
            item['id']: item
            for item in payload['items']
            if item['id'] in {completed_item_id, active_item_id}
        }
        self.assertEqual(set(overlapping), {completed_item_id, active_item_id})
        self.assertTrue(overlapping[completed_item_id]['completed'])
        self.assertFalse(overlapping[active_item_id]['completed'])
        self.assertTrue(all(not item['hasConflict'] for item in overlapping.values()))
        self.assertTrue(all(item['conflictIds'] == [] for item in overlapping.values()))

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

        status, payload = self.request('POST', '/api/visits', {'page': 'home', 'path': '/'}, token=admin_token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('POST', '/api/visits', {'page': 'home', 'path': '/'})
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('POST', '/api/visits', {'page': 'admin', 'path': '/admin'}, token=admin_token)
        self.assertEqual(status, HTTPStatus.OK, payload)

        status, payload = self.request('GET', '/api/admin/traffic/summary?view=6h&page=1&pageSize=5', token=admin_token)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload['trafficView'], '6h')
        self.assertGreaterEqual(payload['totalVisits'], 1)
        self.assertTrue(payload['recentVisits'])

        status, payload = self.request(
            'GET',
            f"/api/admin/traffic/summary?view=6h&page=1&pageSize=5&userId={admin_user['id']}",
            token=admin_token,
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload['userFilter'], str(admin_user['id']))
        self.assertEqual(payload['totalVisits'], 2)
        self.assertTrue(all(row['userId'] == admin_user['id'] for row in payload['recentVisits']))

        status, payload = self.request(
            'GET',
            '/api/admin/traffic/summary?view=6h&page=1&pageSize=5&userId=anonymous',
            token=admin_token,
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload['userFilter'], 'anonymous')
        self.assertEqual(payload['totalVisits'], 1)
        self.assertTrue(all(row['user'] is None for row in payload['recentVisits']))

        status, payload = self.request(
            'GET',
            '/api/admin/traffic/summary?view=6h&page=1&pageSize=5&userId=bad',
            token=admin_token,
        )
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)

        app_js = APP_JS_PATH.read_text(encoding='utf-8')
        index_html = INDEX_HTML_PATH.read_text(encoding='utf-8')
        style_css = STYLE_CSS_PATH.read_text(encoding='utf-8')
        for marker in [
            'settingsDialogVisible',
            'aiApprovalVisible',
            'feedbackDialogVisible',
            'habitDialogVisible',
            'scheduleDialogVisible',
            "recordVisit('home')",
            'adminTrafficUserFilter',
            'handleAdminTrafficUserFilterChange',
            "adminSection === 'traffic'",
            "adminSection === 'aiUsage'",
        ]:
            self.assertIn(marker, index_html + app_js)
        self.assertIn('匿名访问', index_html)
        self.assertIn('traffic-filter-row', style_css)
        self.assertIn('@media (max-width: 720px)', style_css)
        self.assertIn('[data-theme="dark"]', style_css)

    def test_api_documentation_mentions_core_endpoints(self):
        api_doc = API_DOC_PATH.read_text(encoding='utf-8')
        user_guide = Path('docs/zh-CN/USER_GUIDE.md').read_text(encoding='utf-8')
        deploy_script = Path('deploy-first-run.sh').read_text(encoding='utf-8')

        for endpoint in [
            '/api/auth/register',
            '/api/auth/login',
            '/auth/login',
            '/auth/callback',
            '/auth/backchannel-logout',
            '/api/tasks',
            '/api/schedule-items',
            '/api/habits',
            '/api/schedule-config',
            '/api/feedback',
        ]:
            self.assertIn(endpoint, api_doc)

        english_api_doc = Path('docs/en/API.md').read_text(encoding='utf-8')
        self.assertIn('/api/tasks', english_api_doc)
        self.assertIn('[中文](../zh-CN/API.md)', english_api_doc)
        self.assertIn('[English](../en/API.md)', api_doc)

        self.assertIn('TODO_PORT', deploy_script)
        self.assertNotIn('TODO_ADMIN_NICKNAME', deploy_script)
        self.assertNotIn('TODO_ADMIN_PASSWORD', deploy_script)
        self.assertIn('TODO_CONDA_ENV', deploy_script)
        self.assertIn('TODO_PYTHON_VERSION', deploy_script)
        self.assertIn('conda create --yes --name', deploy_script)
        self.assertIn('"$PYTHON_BIN" -m pip install --upgrade -r', deploy_script)
        self.assertIn('MANAGEBAC_COOKIE_ENCRYPTION_KEY', deploy_script)
        self.assertIn('cp "$APP_DIR/.env.example" "$APP_DIR/.env"', deploy_script)
        self.assertIn('web/index.html', deploy_script)
        self.assertIn('ExecStart="$PYTHON_BIN"', deploy_script)
        self.assertNotIn('! -f index.html', deploy_script)
        self.assertIn('管理员', user_guide)

    def test_deploy_script_generates_managebac_key_once(self):
        deploy_script = Path('deploy-first-run.sh').read_text(encoding='utf-8')
        start_marker = 'TODO_ENV_PATH="$APP_DIR/.env" "$PYTHON_BIN" - <<\'PY\'\n'
        end_marker = '\nPY\n\nlog "在 Conda 环境中安装或更新 Python 依赖。"'
        self.assertIn(start_marker, deploy_script)
        bootstrap_code = deploy_script.split(start_marker, 1)[1].split(end_marker, 1)[0]

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            env_path = Path(temp_dir) / '.env'
            env_path.write_text('TODO_HOST=127.0.0.1\n', encoding='utf-8')
            previous_path = os.environ.get('TODO_ENV_PATH')
            os.environ['TODO_ENV_PATH'] = str(env_path)
            try:
                exec(compile(bootstrap_code, 'deploy-first-run-key-bootstrap', 'exec'), {})
                first_text = env_path.read_text(encoding='utf-8')
                first_key = next(
                    line.split('=', 1)[1]
                    for line in first_text.splitlines()
                    if line.startswith('MANAGEBAC_COOKIE_ENCRYPTION_KEY=')
                )
                self.assertEqual(len(base64.b64decode(first_key, altchars=b'-_', validate=True)), 32)

                exec(compile(bootstrap_code, 'deploy-first-run-key-bootstrap', 'exec'), {})
                self.assertEqual(env_path.read_text(encoding='utf-8'), first_text)
            finally:
                if previous_path is None:
                    os.environ.pop('TODO_ENV_PATH', None)
                else:
                    os.environ['TODO_ENV_PATH'] = previous_path


if __name__ == '__main__':
    unittest.main()
