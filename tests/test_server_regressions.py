import concurrent.futures
import base64
import json
import os
import sqlite3
import sys
import tempfile
import threading
import types
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import server

WEB_DIR = Path('web')
INDEX_HTML_PATH = WEB_DIR / 'index.html'
APP_JS_PATH = WEB_DIR / 'app.js'
STYLE_CSS_PATH = WEB_DIR / 'style.css'


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

    def test_static_files_are_served_from_web_directory(self):
        status, headers, body = self.raw_request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'app.js', body)
        self.assertIn(b'style.css', body)
        self.assertEqual(headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(headers.get('X-Frame-Options'), 'DENY')

        status, headers, body = self.raw_request('GET', '/app.js')
        self.assertEqual(status, 200)
        self.assertIn(b'MANAGEBAC_INSTALLER_DOWNLOAD_URL', body)

    def test_json_body_validation_and_api_not_found_contract(self):
        status, payload = self.request('POST', '/api/auth/register', [])
        self.assertEqual(status, 400, payload)
        self.assertEqual(payload['error'], 'json body must be an object')

        original_limit = server.MAX_JSON_BODY_BYTES
        server.MAX_JSON_BODY_BYTES = 64
        try:
            status, payload = self.request('POST', '/api/auth/register', {
                'name': 'Body Limit',
                'nickname': 'body-limit',
                'password': 'secret123',
                'padding': 'x' * 100,
            })
        finally:
            server.MAX_JSON_BODY_BYTES = original_limit
        self.assertEqual(status, 413, payload)
        self.assertEqual(payload['error'], 'request body too large')

        status, payload = self.request('POST', '/api/no-such-endpoint', {})
        self.assertEqual(status, 404, payload)
        self.assertEqual(payload['error'], 'not found')

    def test_task_payload_rejects_invalid_backend_only_values(self):
        token, _ = self.register_user('task-validation')
        valid_task = {
            'id': 'task-validation-1',
            'title': 'Valid task',
            'subject': 'Math',
            'dueAt': '2026-06-20T23:59:00',
            'pool': 'todo',
            'priority': 'medium',
            'note': '',
            'completed': False,
        }

        cases = [
            ({**valid_task, 'id': 'task-title-too-long', 'title': 'x' * (server.MAX_TASK_TITLE_LENGTH + 1)}, 'task title is too long'),
            ({**valid_task, 'id': 'task-subject-required', 'subject': ''}, 'subject is required'),
            ({**valid_task, 'id': 'task-subject-too-long', 'subject': 'x' * (server.MAX_TASK_SUBJECT_LENGTH + 1)}, 'subject is too long'),
            ({**valid_task, 'id': 'task-invalid-due', 'dueAt': 'not-a-date'}, 'dueAt must be empty or YYYY-MM-DDTHH:mm:ss'),
            ({**valid_task, 'id': 'task-string-completed', 'completed': 'false'}, 'completed must be a boolean'),
        ]
        for payload, error in cases:
            with self.subTest(error=error):
                status, body = self.request('POST', '/api/tasks', payload, token=token)
                self.assertEqual(status, 400, body)
                self.assertEqual(body['error'], error)

    def make_admin(self, user_id):
        conn = server.get_db()
        try:
            conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()

    def ai_usage_rows(self):
        conn = server.get_db()
        try:
            return conn.execute(
                '''
                SELECT user_id, model, call_type, prompt_tokens, completion_tokens,
                       total_tokens, prompt_cache_hit_tokens, prompt_cache_miss_tokens,
                       reasoning_tokens, created_at
                FROM ai_usage_logs
                ORDER BY id ASC
                '''
            ).fetchall()
        finally:
            conn.close()

    def installer_download_rows(self):
        conn = server.get_db()
        try:
            return conn.execute(
                '''
                SELECT user_id, source, object_key, filename, ip, created_at
                FROM installer_download_logs
                ORDER BY id ASC
                '''
            ).fetchall()
        finally:
            conn.close()

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

    def ai_request_context(self, messages):
        content = messages[-1]['content']
        return json.loads(content.split('\n', 1)[1])

    def insert_task_direct(
        self,
        user_id,
        task_id,
        title,
        *,
        subject='Math',
        due_at='',
        pool='todo',
        priority='medium',
        note='',
        completed=False,
    ):
        now = server.now_iso()
        with server.get_db() as conn:
            conn.execute(
                '''
                INSERT INTO tasks
                (id, user_id, title, subject, due_at, pool, priority, note, completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    task_id,
                    user_id,
                    title,
                    subject,
                    due_at,
                    pool,
                    priority,
                    note,
                    1 if completed else 0,
                    now,
                    now,
                ),
            )
            conn.commit()

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
        self.assertIn('taskPlacement', context)
        self.assertIn('待安排DDL', context_json)
        self.assertIn('dueAt 为空字符串', context_json)

    def test_fetch_ai_context_tasks_uses_database_limit_and_truncation(self):
        token, user = self.register_user('ai-context-query')
        limit = server.AI_CONTEXT_TASK_LIMIT
        for index in range(limit + 3):
            self.insert_task_direct(user['id'], f'ai-visible-{index:03d}', f'Visible {index:03d}')
        self.insert_task_direct(user['id'], 'ai-completed', 'Completed', completed=True)
        self.insert_task_direct(user['id'], 'ai-arrangement', 'Arrangement', pool='arrangement')

        with server.get_db() as conn:
            tasks, context = server.TodoHandler.fetch_ai_context_tasks_for_user(None, conn, user['id'])

        self.assertEqual(len(tasks), limit)
        self.assertTrue(all(task['pool'] == 'todo' and not task['completed'] for task in tasks))
        self.assertEqual(context['taskSelection']['totalIncompleteTimelineTaskCount'], limit + 3)
        self.assertEqual(context['taskSelection']['includedTaskCount'], limit)
        self.assertEqual(context['taskSelection']['omittedIncompleteTimelineTaskCount'], 3)
        self.assertTrue(context['taskSelection']['truncated'])
        context_json = json.dumps(context, ensure_ascii=False)
        self.assertNotIn('ai-completed', context_json)
        self.assertNotIn('ai-arrangement', context_json)

    def test_ai_prompts_explain_unscheduled_ddl_placement(self):
        prompts = [
            server.AI_CHAT_SYSTEM_PROMPT,
            server.AI_STREAM_SYSTEM_PROMPT,
            server.AI_REPAIR_SYSTEM_PROMPT,
        ]
        for prompt in prompts:
            self.assertIn('待安排DDL', prompt)
            self.assertIn('dueAt', prompt)
            self.assertIn('空字符串', prompt)

    def test_ai_subject_template_context_and_matching(self):
        subject_names = ['Physics', 'Mathematics']
        messages = server.TodoHandler.build_ai_messages(None, '物理作业明天交', [], [], '2026-06-18T12:00:00Z', 'Asia/Shanghai', subject_names)
        context = self.ai_request_context(messages)
        self.assertEqual(context['subjectTemplate']['availableSubjects'], subject_names)
        self.assertIn('不要从任务内容自行推断科目', context['subjectTemplate']['matchingPolicy'])
        self.assertEqual(server.match_existing_subject('物理', subject_names), 'Physics')
        self.assertEqual(server.match_existing_subject('physics', subject_names), 'Physics')
        self.assertEqual(server.match_existing_subject('天文学', subject_names), '天文学')

        actions, rejected = server.normalize_ai_actions([
            {
                'type': 'create_task',
                'task': {
                    'title': '做实验报告',
                    'subject': '物理',
                    'dueAt': '',
                    'priority': 'medium',
                    'note': '',
                },
            },
            {
                'type': 'create_task',
                'task': {
                    'title': '观星记录',
                    'subject': '天文学',
                    'dueAt': '',
                    'priority': 'low',
                    'note': '',
                },
            },
        ], [], subject_names)

        self.assertEqual(rejected, [])
        self.assertEqual(actions[0]['task']['subject'], 'Physics')
        self.assertEqual(actions[1]['task']['subject'], '天文学')

    def test_ai_prompts_explain_subject_template_matching(self):
        prompts = [
            server.AI_CHAT_SYSTEM_PROMPT,
            server.AI_STREAM_SYSTEM_PROMPT,
            server.AI_REPAIR_SYSTEM_PROMPT,
        ]
        for prompt in prompts:
            self.assertIn('科目匹配规则', prompt)
            self.assertIn('subjectTemplate.availableSubjects', prompt)
            self.assertIn('不要因为任务内容或标题自行推断科目', prompt)

    def test_ai_create_task_requires_explicit_priority(self):
        actions, rejected = server.normalize_ai_actions([
            {
                'type': 'create_task',
                'task': {
                    'title': 'No priority task',
                    'subject': 'Math',
                    'dueAt': '',
                    'note': '',
                },
            },
        ], [], ['Math'])

        self.assertEqual(actions, [])
        self.assertEqual(rejected, [{'index': 0, 'reason': 'task priority is required'}])

        actions, rejected = server.normalize_ai_actions([
            {
                'type': 'create_task',
                'task': {
                    'title': 'Blank priority task',
                    'subject': 'Math',
                    'dueAt': '',
                    'priority': '',
                    'note': '',
                },
            },
        ], [], ['Math'])

        self.assertEqual(actions, [])
        self.assertEqual(rejected, [{'index': 0, 'reason': 'task priority is required'}])

    def test_ai_prompts_require_explicit_priority(self):
        for prompt in [server.AI_CHAT_SYSTEM_PROMPT, server.AI_STREAM_SYSTEM_PROMPT]:
            self.assertIn('创建任务时，如果用户没有明确提供优先级', prompt)
            self.assertIn('不要猜测或默认 medium', prompt)
            self.assertIn('这个任务的优先级是高、中还是低？', prompt)
        self.assertIn('task priority is required', server.AI_REPAIR_SYSTEM_PROMPT)
        self.assertIn('不要补默认 medium', server.AI_REPAIR_SYSTEM_PROMPT)


    def test_ai_prompts_are_loaded_from_json_file(self):
        prompts = json.loads((server.BASE_DIR / 'ai_prompts.json').read_text(encoding='utf-8'))
        self.assertEqual(prompts['AI_CHAT_SYSTEM_PROMPT'].strip(), server.AI_CHAT_SYSTEM_PROMPT)
        self.assertEqual(prompts['AI_STREAM_SYSTEM_PROMPT'].strip(), server.AI_STREAM_SYSTEM_PROMPT)
        self.assertEqual(prompts['AI_REPAIR_SYSTEM_PROMPT'].strip(), server.AI_REPAIR_SYSTEM_PROMPT)

    def test_dotenv_loader_sets_missing_values_without_overriding_existing_env(self):
        keys = ['DOTENV_TEST_KEY', 'DOTENV_EXISTING_KEY', 'DOTENV_QUOTED_KEY']
        original = {key: os.environ.get(key) for key in keys}
        dotenv_path = Path(self.temp_dir.name) / '.env'
        dotenv_path.write_text(
            '\n'.join([
                '\ufeff# comment',
                'DOTENV_TEST_KEY=loaded',
                'DOTENV_EXISTING_KEY=from-file',
                'DOTENV_QUOTED_KEY="quoted value"',
                '',
            ]),
            encoding='utf-8',
        )
        try:
            os.environ.pop('DOTENV_TEST_KEY', None)
            os.environ['DOTENV_EXISTING_KEY'] = 'from-env'
            os.environ.pop('DOTENV_QUOTED_KEY', None)

            server.load_dotenv(dotenv_path)

            self.assertEqual(os.environ['DOTENV_TEST_KEY'], 'loaded')
            self.assertEqual(os.environ['DOTENV_EXISTING_KEY'], 'from-env')
            self.assertEqual(os.environ['DOTENV_QUOTED_KEY'], 'quoted value')
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_managebac_oss_installer_config_reads_minimal_download_settings(self):
        keys = server.MANAGEBAC_OSS_INSTALLER_ENV_NAMES
        original = {key: os.environ.get(key) for key in keys}
        try:
            for key in keys:
                os.environ.pop(key, None)
            self.assertIsNone(server.get_managebac_oss_installer_config())

            os.environ['ALIYUN_OSS_BUCKET'] = 'todolis-oss'
            with self.assertRaises(server.ManageBacOssConfigError):
                server.get_managebac_oss_installer_config()

            os.environ['ALIYUN_OSS_ACCESS_KEY_ID'] = 'ak'
            os.environ['ALIYUN_OSS_ACCESS_KEY_SECRET'] = 'secret'
            os.environ['ALIYUN_OSS_REGION'] = 'cn-hangzhou'
            os.environ['ALIYUN_OSS_INSTALLER_KEY'] = '/managebac-sync-helper/latest.exe'
            os.environ['ALIYUN_OSS_ENDPOINT'] = 'https://oss-cn-hangzhou.aliyuncs.com'
            os.environ['ALIYUN_OSS_SIGN_EXPIRES_SECONDS'] = '300'

            config = server.get_managebac_oss_installer_config()

            self.assertIsNotNone(config)
            self.assertEqual(config.bucket, 'todolis-oss')
            self.assertEqual(config.key, 'managebac-sync-helper/latest.exe')
            self.assertEqual(config.filename, 'latest.exe')
            self.assertEqual(config.expires_seconds, 300)
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_managebac_oss_installer_url_uses_get_object_presign(self):
        captured = {}

        class FakeStaticCredentialsProvider:
            def __init__(self, access_key_id, access_key_secret):
                captured['access_key_id'] = access_key_id
                captured['access_key_secret'] = access_key_secret

        class FakeGetObjectRequest:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        class FakeClient:
            def __init__(self, config):
                captured['config'] = config

            def presign(self, request, expires):
                captured['request'] = request
                captured['expires'] = expires
                return types.SimpleNamespace(url='https://signed.example/download')

        fake_oss = types.SimpleNamespace(
            credentials=types.SimpleNamespace(StaticCredentialsProvider=FakeStaticCredentialsProvider),
            config=types.SimpleNamespace(load_default=lambda: types.SimpleNamespace()),
            Client=FakeClient,
            GetObjectRequest=FakeGetObjectRequest,
        )
        original_module = sys.modules.get('alibabacloud_oss_v2')
        sys.modules['alibabacloud_oss_v2'] = fake_oss
        try:
            config = server.ManageBacOssInstallerConfig(
                access_key_id='ak',
                access_key_secret='secret',
                region='cn-hangzhou',
                bucket='todolis-oss',
                key='managebac-sync-helper/latest.exe',
                endpoint='https://oss-cn-hangzhou.aliyuncs.com',
                expires_seconds=600,
                filename='ManageBac Helper.exe',
            )

            url = server.generate_managebac_oss_installer_url(config)

            self.assertEqual(url, 'https://signed.example/download')
            self.assertEqual(captured['access_key_id'], 'ak')
            self.assertEqual(captured['config'].region, 'cn-hangzhou')
            self.assertEqual(captured['config'].endpoint, 'https://oss-cn-hangzhou.aliyuncs.com')
            self.assertEqual(captured['request'].bucket, 'todolis-oss')
            self.assertEqual(captured['request'].key, 'managebac-sync-helper/latest.exe')
            self.assertIn('attachment', captured['request'].response_content_disposition)
            self.assertEqual(captured['expires'].total_seconds(), 600)
        finally:
            if original_module is None:
                sys.modules.pop('alibabacloud_oss_v2', None)
            else:
                sys.modules['alibabacloud_oss_v2'] = original_module

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
        calls = []

        def fake_call(handler, messages):
            calls.append(messages)
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
        self.assertEqual(len(calls), 2)
        self.assertIn('backendSafetyValidation', calls[1][-1]['content'])
        self.assertIn('unsupported action type', calls[1][-1]['content'])
        self.assertEqual(body['actions'], [])
        self.assertEqual(len(body['rejectedActions']), 3)

    def test_ai_chat_repairs_rejected_actions_with_followup_prompt(self):
        token, _ = self.register_user('ai-repair')
        self.create_task(token, 'task-ai-visible')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_call = server.TodoHandler.call_deepseek_chat
        calls = []

        def fake_call(handler, messages):
            calls.append(messages)
            content = messages[-1]['content']
            if 'rejectedActions' in content:
                return json.dumps({
                    'reply': 'Please clarify which visible timeline task should be updated.',
                    'actions': [],
                })
            return json.dumps({
                'reply': 'I will update it.',
                'actions': [
                    {'type': 'update_task', 'targetTaskId': 'missing-task', 'patch': {'note': 'New note'}},
                ],
            })

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.call_deepseek_chat = fake_call
            status, body = self.request('POST', '/api/ai/chat', {'message': 'Update that task'}, token=token)
        finally:
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 200, body)
        self.assertEqual(len(calls), 2)
        self.assertIn('backendSafetyValidation', calls[1][-1]['content'])
        self.assertIn('target task not found', calls[1][-1]['content'])
        self.assertEqual(body['reply'], 'Please clarify which visible timeline task should be updated.')
        self.assertEqual(body['actions'], [])
        self.assertEqual(body['rejectedActions'], [])

    def test_ai_chat_repairs_missing_subject_with_validation_feedback(self):
        token, _ = self.register_user('ai-repair-subject')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_call = server.TodoHandler.call_deepseek_chat
        calls = []

        def fake_call(handler, messages):
            calls.append(messages)
            content = messages[-1]['content']
            if 'backendSafetyValidation' in content:
                context = self.ai_request_context(messages)
                self.assertTrue(context['backendSafetyValidation']['blocked'])
                self.assertEqual(context['rejectedActions'][0]['reason'], 'task subject is required')
                return json.dumps({
                    'reply': '这个任务属于哪个科目？',
                    'actions': [],
                })
            return json.dumps({
                'reply': '我会创建这个任务。',
                'actions': [
                    {
                        'type': 'create_task',
                        'task': {
                            'title': 'No subject task',
                            'subject': '',
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
            status, body = self.request('POST', '/api/ai/chat', {'message': '帮我创建一个任务：写练习册'}, token=token)
        finally:
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 200, body)
        self.assertEqual(len(calls), 2)
        self.assertEqual(body['reply'], '这个任务属于哪个科目？')
        self.assertEqual(body['actions'], [])
        self.assertEqual(body['rejectedActions'], [])

    def test_ai_chat_repair_context_handles_more_than_two_hundred_tasks(self):
        token, user = self.register_user('ai-repair-truncated')
        for index in range(server.AI_CONTEXT_TASK_LIMIT + 5):
            self.insert_task_direct(
                user['id'],
                f'bulk-{index:03d}',
                f'Bulk {index:03d}',
            )
        self.insert_task_direct(user['id'], 'completed-extra', 'Completed extra', completed=True)
        self.insert_task_direct(user['id'], 'schedule-extra', 'Schedule extra', pool='schedule')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_call = server.TodoHandler.call_deepseek_chat
        contexts = []

        def fake_call(handler, messages):
            context = self.ai_request_context(messages)
            contexts.append(context)
            if 'backendSafetyValidation' in context:
                self.assertTrue(context['taskSelection']['truncated'])
                self.assertEqual(context['taskSelection']['includedTaskCount'], server.AI_CONTEXT_TASK_LIMIT)
                self.assertEqual(context['taskSelection']['omittedIncompleteTimelineTaskCount'], 5)
                self.assertEqual(context['rejectedActions'][0]['reason'], 'target task not found')
                self.assertNotIn('completed-extra', json.dumps(context, ensure_ascii=False))
                self.assertNotIn('schedule-extra', json.dumps(context, ensure_ascii=False))
                return json.dumps({
                    'reply': '当前未完成时间线任务超过 200 条，请告诉我更精确的任务标题或先缩小范围。',
                    'actions': [],
                })
            self.assertTrue(context['taskSelection']['truncated'])
            self.assertEqual(context['taskSelection']['totalIncompleteTimelineTaskCount'], server.AI_CONTEXT_TASK_LIMIT + 5)
            self.assertEqual(len(context['tasks']), server.AI_CONTEXT_TASK_LIMIT)
            self.assertNotIn('completed-extra', json.dumps(context, ensure_ascii=False))
            self.assertNotIn('schedule-extra', json.dumps(context, ensure_ascii=False))
            return json.dumps({
                'reply': '我会修改这个任务。',
                'actions': [
                    {
                        'type': 'update_task',
                        'targetTaskId': 'bulk-204',
                        'patch': {'note': 'This task was outside the visible context'},
                    },
                ],
            })

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.call_deepseek_chat = fake_call
            status, body = self.request('POST', '/api/ai/chat', {'message': '把最后那个任务备注改一下'}, token=token)
        finally:
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 200, body)
        self.assertEqual(len(contexts), 2)
        self.assertEqual(body['reply'], '当前未完成时间线任务超过 200 条，请告诉我更精确的任务标题或先缩小范围。')
        self.assertEqual(body['actions'], [])
        self.assertEqual(body['rejectedActions'], [])

    def test_ai_chat_stream_repairs_missing_subject_with_validation_feedback(self):
        token, _ = self.register_user('ai-stream-repair-subject')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_stream = server.TodoHandler.stream_deepseek_chat
        original_call = server.TodoHandler.call_deepseek_chat
        repair_contents = []

        def fake_stream(handler, messages):
            yield '我会创建这个任务。'
            yield '\n<AI_ACTIONS_JSON>'
            yield json.dumps({
                'actions': [
                    {
                        'type': 'create_task',
                        'task': {
                            'title': 'No subject task',
                            'subject': '',
                            'dueAt': '',
                            'priority': 'medium',
                            'note': '',
                        },
                    },
                ],
            })
            yield '</AI_ACTIONS_JSON>'

        def fake_call(handler, messages):
            repair_contents.append(messages[-1]['content'])
            return json.dumps({
                'reply': '这个任务属于哪个科目？',
                'actions': [],
            })

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.stream_deepseek_chat = fake_stream
            server.TodoHandler.call_deepseek_chat = fake_call
            status, headers, raw = self.stream_request('/api/ai/chat-stream', {
                'message': '帮我创建一个任务：写练习册',
                'clientNow': '2026-06-18T12:00:00.000Z',
                'timezone': 'Asia/Shanghai',
            }, token=token)
        finally:
            server.TodoHandler.stream_deepseek_chat = original_stream
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 200, raw)
        self.assertEqual(headers.get_content_type(), 'text/event-stream')
        self.assertEqual(len(repair_contents), 1)
        self.assertIn('backendSafetyValidation', repair_contents[0])
        self.assertIn('task subject is required', repair_contents[0])
        events = self.parse_sse(raw)
        self.assertEqual(events[-1][0], 'done')
        self.assertEqual(events[-1][1]['reply'], '这个任务属于哪个科目？')
        self.assertEqual(events[-1][1]['actions'], [])
        self.assertEqual(events[-1][1]['rejectedActions'], [])

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

    def test_ai_chat_records_non_stream_usage(self):
        token, user = self.register_user('ai-usage-non-stream')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_call = server.TodoHandler.call_deepseek_chat

        def fake_call(handler, messages):
            handler._last_deepseek_usage = {
                'prompt_tokens': 11,
                'completion_tokens': 7,
                'total_tokens': 18,
                'prompt_cache_hit_tokens': 3,
                'prompt_cache_miss_tokens': 8,
                'completion_tokens_details': {'reasoning_tokens': 2},
            }
            return json.dumps({'reply': 'ok', 'actions': []})

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.call_deepseek_chat = fake_call
            status, body = self.request('POST', '/api/ai/chat', {'message': 'hello'}, token=token)
        finally:
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 200, body)
        rows = self.ai_usage_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['user_id'], user['id'])
        self.assertEqual(rows[0]['call_type'], 'chat')
        self.assertEqual(rows[0]['prompt_tokens'], 11)
        self.assertEqual(rows[0]['completion_tokens'], 7)
        self.assertEqual(rows[0]['total_tokens'], 18)
        self.assertEqual(rows[0]['prompt_cache_hit_tokens'], 3)
        self.assertEqual(rows[0]['prompt_cache_miss_tokens'], 8)
        self.assertEqual(rows[0]['reasoning_tokens'], 2)

    def test_ai_chat_stream_records_usage(self):
        token, user = self.register_user('ai-usage-stream')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_stream = server.TodoHandler.stream_deepseek_chat

        def fake_stream(handler, messages):
            handler._last_deepseek_stream_usage = {
                'prompt_tokens': 13,
                'completion_tokens': 5,
                'total_tokens': 18,
            }
            yield 'stream ok'
            yield '\n<AI_ACTIONS_JSON>{"actions":[]}</AI_ACTIONS_JSON>'

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.stream_deepseek_chat = fake_stream
            status, headers, raw = self.stream_request('/api/ai/chat-stream', {
                'message': 'hello stream',
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
        rows = self.ai_usage_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['user_id'], user['id'])
        self.assertEqual(rows[0]['call_type'], 'chat_stream')
        self.assertEqual(rows[0]['prompt_tokens'], 13)
        self.assertEqual(rows[0]['completion_tokens'], 5)

    def test_stream_deepseek_chat_requests_usage_chunk(self):
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_urlopen = urllib.request.urlopen
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def __iter__(self):
                return iter([
                    b'data: {"choices":[{"delta":{"content":"hi"}}]}\n',
                    b'data: {"usage":{"prompt_tokens":17,"completion_tokens":4,"total_tokens":21},"choices":[]}\n',
                    b'data: [DONE]\n',
                ])

        def fake_urlopen(request, timeout=60):
            captured['body'] = json.loads(request.data.decode('utf-8'))
            return FakeResponse()

        class DummyHandler:
            pass

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            urllib.request.urlopen = fake_urlopen
            dummy = DummyHandler()
            chunks = list(server.TodoHandler.stream_deepseek_chat(dummy, [{'role': 'user', 'content': 'hi'}]))
        finally:
            urllib.request.urlopen = original_urlopen
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(chunks, ['hi'])
        self.assertEqual(captured['body']['stream_options'], {'include_usage': True})
        self.assertEqual(dummy._last_deepseek_stream_usage['prompt_tokens'], 17)
        self.assertEqual(dummy._last_deepseek_stream_usage['completion_tokens'], 4)

    def test_ai_chat_records_repair_usage(self):
        token, user = self.register_user('ai-usage-repair')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_call = server.TodoHandler.call_deepseek_chat
        calls = []

        def fake_call(handler, messages):
            calls.append(messages)
            if 'backendSafetyValidation' in messages[-1]['content']:
                handler._last_deepseek_usage = {
                    'prompt_tokens': 19,
                    'completion_tokens': 6,
                    'total_tokens': 25,
                }
                return json.dumps({'reply': 'need subject', 'actions': []})
            handler._last_deepseek_usage = {
                'prompt_tokens': 9,
                'completion_tokens': 4,
                'total_tokens': 13,
            }
            return json.dumps({
                'reply': 'creating',
                'actions': [
                    {
                        'type': 'create_task',
                        'task': {
                            'title': 'Missing subject',
                            'subject': '',
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
            status, body = self.request('POST', '/api/ai/chat', {'message': 'create'}, token=token)
        finally:
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 200, body)
        self.assertEqual(len(calls), 2)
        rows = self.ai_usage_rows()
        self.assertEqual([row['call_type'] for row in rows], ['chat', 'repair'])
        self.assertEqual([row['prompt_tokens'] for row in rows], [9, 19])
        self.assertEqual([row['completion_tokens'] for row in rows], [4, 6])
        self.assertTrue(all(row['user_id'] == user['id'] for row in rows))

    def test_ai_token_limits_global_override_and_clear(self):
        student_token, student = self.register_user('ai-limit-student')
        admin_token, admin = self.register_user('ai-limit-admin')
        self.make_admin(admin['id'])
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_call = server.TodoHandler.call_deepseek_chat
        calls = []

        def fake_call(handler, messages):
            calls.append(messages)
            handler._last_deepseek_usage = {
                'prompt_tokens': 2,
                'completion_tokens': 1,
                'total_tokens': 3,
            }
            return json.dumps({'reply': 'ok', 'actions': []})

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.call_deepseek_chat = fake_call
            status, body = self.request('PUT', '/api/admin/ai-usage/global-limit', {
                'windowHours': 24,
                'inputTokenLimit': 5,
                'outputTokenLimit': 100,
            }, token=admin_token)
            self.assertEqual(status, 200, body)

            conn = server.get_db()
            try:
                server.record_ai_usage(conn, student['id'], 'deepseek-test', 'seed', {
                    'prompt_tokens': 5,
                    'completion_tokens': 0,
                    'total_tokens': 5,
                })
                conn.commit()
            finally:
                conn.close()

            status, body = self.request('POST', '/api/ai/chat', {'message': 'blocked'}, token=student_token)
            self.assertEqual(status, 429, body)
            self.assertEqual(body.get('dimension'), 'input')
            self.assertEqual(len(calls), 0)

            status, body = self.request('PUT', f"/api/admin/users/{student['id']}/ai-token-limit", {
                'windowHours': 24,
                'inputTokenLimit': 100,
                'outputTokenLimit': 100,
            }, token=admin_token)
            self.assertEqual(status, 200, body)

            status, body = self.request('POST', '/api/ai/chat', {'message': 'allowed'}, token=student_token)
            self.assertEqual(status, 200, body)
            self.assertEqual(len(calls), 1)

            status, body = self.request('GET', '/api/admin/ai-usage/summary?view=7d&page=1&pageSize=50', token=admin_token)
            self.assertEqual(status, 200, body)
            rows_by_id = {row['user']['id']: row for row in body['users']}
            self.assertTrue(rows_by_id[student['id']]['hasOverride'])
            self.assertEqual(rows_by_id[student['id']]['windowUsage']['promptTokens'], 7)

            status, body = self.request('DELETE', f"/api/admin/users/{student['id']}/ai-token-limit", token=admin_token)
            self.assertEqual(status, 200, body)
            status, body = self.request('POST', '/api/ai/chat', {'message': 'blocked again'}, token=student_token)
            self.assertEqual(status, 429, body)

            status, body = self.request('PUT', f"/api/admin/users/{student['id']}/ai-token-limit", {
                'windowHours': 24,
                'inputTokenLimit': 100,
                'outputTokenLimit': 100,
            }, token=admin_token)
            self.assertEqual(status, 200, body)
            status, body = self.request('POST', '/api/admin/ai-usage/clear-user-limits', token=admin_token)
            self.assertEqual(status, 200, body)
            status, body = self.request('GET', '/api/admin/ai-usage/summary?view=7d&page=1&pageSize=50', token=admin_token)
            self.assertEqual(status, 200, body)
            rows_by_id = {row['user']['id']: row for row in body['users']}
            self.assertFalse(rows_by_id[student['id']]['hasOverride'])

            conn = server.get_db()
            try:
                server.record_ai_usage(conn, admin['id'], 'deepseek-test', 'seed', {
                    'prompt_tokens': 5,
                    'completion_tokens': 0,
                    'total_tokens': 5,
                })
                conn.commit()
            finally:
                conn.close()
            status, body = self.request('POST', '/api/ai/chat', {'message': 'admin is limited too'}, token=admin_token)
            self.assertEqual(status, 429, body)
        finally:
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

    def test_ai_token_output_limit_blocks_requests(self):
        token, user = self.register_user('ai-output-limit')
        original_key = os.environ.get('DEEPSEEK_API_KEY')
        original_call = server.TodoHandler.call_deepseek_chat
        calls = []

        def fake_call(handler, messages):
            calls.append(messages)
            return json.dumps({'reply': 'should not run', 'actions': []})

        conn = server.get_db()
        try:
            server.set_ai_global_token_limit(conn, {
                'windowHours': 24,
                'inputTokenLimit': 100,
                'outputTokenLimit': 5,
            })
            server.record_ai_usage(conn, user['id'], 'deepseek-test', 'seed', {
                'prompt_tokens': 0,
                'completion_tokens': 5,
                'total_tokens': 5,
            })
            conn.commit()
        finally:
            conn.close()

        try:
            os.environ['DEEPSEEK_API_KEY'] = 'test-key'
            server.TodoHandler.call_deepseek_chat = fake_call
            status, body = self.request('POST', '/api/ai/chat', {'message': 'blocked'}, token=token)
        finally:
            server.TodoHandler.call_deepseek_chat = original_call
            if original_key is None:
                os.environ.pop('DEEPSEEK_API_KEY', None)
            else:
                os.environ['DEEPSEEK_API_KEY'] = original_key

        self.assertEqual(status, 429, body)
        self.assertEqual(body.get('dimension'), 'output')
        self.assertEqual(len(calls), 0)

    def test_installer_download_limits_global_override_and_summary(self):
        student_token, student = self.register_user('installer-limit-student')
        admin_token, admin = self.register_user('installer-limit-admin')
        self.make_admin(admin['id'])
        original_env = {key: os.environ.get(key) for key in server.MANAGEBAC_OSS_INSTALLER_ENV_NAMES}
        original_module = sys.modules.get('alibabacloud_oss_v2')

        class FakeStaticCredentialsProvider:
            def __init__(self, access_key_id, access_key_secret):
                self.access_key_id = access_key_id
                self.access_key_secret = access_key_secret

        class FakeGetObjectRequest:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        class FakeClient:
            def __init__(self, config):
                self.config = config

            def presign(self, request, expires):
                return types.SimpleNamespace(url=f'https://signed.example/{request.key}?expires={int(expires.total_seconds())}')

        fake_oss = types.SimpleNamespace(
            credentials=types.SimpleNamespace(StaticCredentialsProvider=FakeStaticCredentialsProvider),
            config=types.SimpleNamespace(load_default=lambda: types.SimpleNamespace()),
            Client=FakeClient,
            GetObjectRequest=FakeGetObjectRequest,
        )
        try:
            sys.modules['alibabacloud_oss_v2'] = fake_oss
            for key in server.MANAGEBAC_OSS_INSTALLER_ENV_NAMES:
                os.environ.pop(key, None)
            os.environ['ALIYUN_OSS_ACCESS_KEY_ID'] = 'ak'
            os.environ['ALIYUN_OSS_ACCESS_KEY_SECRET'] = 'secret'
            os.environ['ALIYUN_OSS_REGION'] = 'cn-chengdu'
            os.environ['ALIYUN_OSS_ENDPOINT'] = 'https://oss-cn-chengdu.aliyuncs.com'
            os.environ['ALIYUN_OSS_BUCKET'] = 'todolis-oss'
            os.environ['ALIYUN_OSS_INSTALLER_KEY'] = 'managebac-sync-helper/latest.exe'
            os.environ['ALIYUN_OSS_INSTALLER_FILENAME'] = 'ManageBac Helper.exe'
            os.environ['ALIYUN_OSS_SIGN_EXPIRES_SECONDS'] = '60'

            status, body = self.request('GET', '/api/managebac-helper/installer')
            self.assertEqual(status, 401, body)

            status, body = self.request('PUT', '/api/admin/installer-downloads/global-limit', {
                'windowHours': 24,
                'linkLimit': 1,
            }, token=admin_token)
            self.assertEqual(status, 200, body)

            status, body = self.request('GET', '/api/managebac-helper/installer', token=student_token)
            self.assertEqual(status, 200, body)
            self.assertEqual(body['source'], 'oss')
            self.assertIn('https://signed.example/managebac-sync-helper/latest.exe', body['url'])
            self.assertEqual(body['usage']['linkCount'], 1)

            rows = self.installer_download_rows()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['user_id'], student['id'])
            self.assertEqual(rows[0]['source'], 'oss')
            self.assertEqual(rows[0]['object_key'], 'managebac-sync-helper/latest.exe')

            status, body = self.request('GET', '/api/managebac-helper/installer', token=student_token)
            self.assertEqual(status, 429, body)
            self.assertEqual(body['currentLinkCount'], 1)

            status, body = self.request('PUT', f"/api/admin/users/{student['id']}/installer-download-limit", {
                'windowHours': 24,
                'linkLimit': 2,
            }, token=admin_token)
            self.assertEqual(status, 200, body)

            status, body = self.request('GET', '/api/managebac-helper/installer', token=student_token)
            self.assertEqual(status, 200, body)
            self.assertEqual(body['usage']['linkCount'], 2)

            status, body = self.request('GET', '/api/admin/installer-downloads/summary?view=7d&page=1&pageSize=50', token=admin_token)
            self.assertEqual(status, 200, body)
            self.assertEqual(body['totalLinks'], 2)
            rows_by_id = {row['user']['id']: row for row in body['users']}
            self.assertTrue(rows_by_id[student['id']]['hasOverride'])
            self.assertEqual(rows_by_id[student['id']]['windowUsage']['linkCount'], 2)

            status, body = self.request('DELETE', f"/api/admin/users/{student['id']}/installer-download-limit", token=admin_token)
            self.assertEqual(status, 200, body)
            status, body = self.request('GET', '/api/managebac-helper/installer', token=student_token)
            self.assertEqual(status, 429, body)

            status, body = self.request('PUT', f"/api/admin/users/{student['id']}/installer-download-limit", {
                'windowHours': 24,
                'linkLimit': 3,
            }, token=admin_token)
            self.assertEqual(status, 200, body)
            status, body = self.request('POST', '/api/admin/installer-downloads/clear-user-limits', token=admin_token)
            self.assertEqual(status, 200, body)
            status, body = self.request('GET', '/api/admin/installer-downloads/summary?view=7d&page=1&pageSize=50', token=admin_token)
            self.assertEqual(status, 200, body)
            rows_by_id = {row['user']['id']: row for row in body['users']}
            self.assertFalse(rows_by_id[student['id']]['hasOverride'])
        finally:
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            if original_module is None:
                sys.modules.pop('alibabacloud_oss_v2', None)
            else:
                sys.modules['alibabacloud_oss_v2'] = original_module

    def test_installer_download_limit_is_atomic_for_concurrent_oss_requests(self):
        student_token, student = self.register_user('installer-race-student')
        admin_token, admin = self.register_user('installer-race-admin')
        self.make_admin(admin['id'])

        status, body = self.request('PUT', '/api/admin/installer-downloads/global-limit', {
            'windowHours': 24,
            'linkLimit': 1,
        }, token=admin_token)
        self.assertEqual(status, 200, body)

        config = server.ManageBacOssInstallerConfig(
            access_key_id='ak',
            access_key_secret='secret',
            region='cn-test',
            bucket='todolis-oss',
            key='managebac-sync-helper/latest.exe',
            endpoint='',
            expires_seconds=60,
            filename='ManageBac Helper.exe',
        )
        original_get_config = server.get_managebac_oss_installer_config
        original_generate = server.generate_managebac_oss_installer_url
        generate_barrier = threading.Barrier(2)

        def fake_generate(_config):
            try:
                generate_barrier.wait(timeout=3)
            except threading.BrokenBarrierError:
                pass
            return 'https://signed.example/managebac-sync-helper/latest.exe'

        try:
            server.get_managebac_oss_installer_config = lambda: config
            server.generate_managebac_oss_installer_url = fake_generate
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(self.request, 'GET', '/api/managebac-helper/installer', token=student_token),
                    executor.submit(self.request, 'GET', '/api/managebac-helper/installer', token=student_token),
                ]
                results = [future.result(timeout=10) for future in futures]
        finally:
            server.get_managebac_oss_installer_config = original_get_config
            server.generate_managebac_oss_installer_url = original_generate

        self.assertEqual(sorted(status for status, _body in results), [200, 429], results)
        rows = self.installer_download_rows()
        self.assertEqual(len(rows), 1, results)
        self.assertEqual(rows[0]['user_id'], student['id'])
        self.assertEqual(rows[0]['source'], 'oss')

    def test_ai_usage_admin_endpoints_require_admin(self):
        token, _ = self.register_user('ai-usage-normal-user')

        status, body = self.request('GET', '/api/admin/ai-usage/summary', token=token)
        self.assertEqual(status, 403, body)
        status, body = self.request('PUT', '/api/admin/ai-usage/global-limit', {
            'windowHours': 24,
            'inputTokenLimit': 100,
            'outputTokenLimit': 100,
        }, token=token)
        self.assertEqual(status, 403, body)
        status, body = self.request('POST', '/api/admin/ai-usage/clear-user-limits', token=token)
        self.assertEqual(status, 403, body)
        status, body = self.request('GET', '/api/admin/installer-downloads/summary', token=token)
        self.assertEqual(status, 403, body)
        status, body = self.request('PUT', '/api/admin/installer-downloads/global-limit', {
            'windowHours': 24,
            'linkLimit': 5,
        }, token=token)
        self.assertEqual(status, 403, body)
        status, body = self.request('POST', '/api/admin/installer-downloads/clear-user-limits', token=token)
        self.assertEqual(status, 403, body)

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
        app_js = APP_JS_PATH.read_text(encoding='utf-8')
        self.assertIn('todoTasksByDueDate()', app_js)
        self.assertIn('const tasks = this.todoTasksByDueDate[key] || []', app_js)
        self.assertIn('return this.todoTasksByDueDate[key] || []', app_js)
        self.assertNotIn(
            "this.filteredTasks.filter(task => task.dueAt && this.taskPool(task) === 'todo' && task.dueAt.startsWith(key))",
            app_js,
        )

    def test_ai_frontend_explains_unscheduled_ddl_placement(self):
        index_html = INDEX_HTML_PATH.read_text(encoding='utf-8')
        app_js = APP_JS_PATH.read_text(encoding='utf-8')

        self.assertIn('没有截止时间时会显示在“待安排DDL”', index_html)
        self.assertIn('留空则放入待安排DDL', index_html)
        self.assertIn(": '待安排DDL'", app_js)

    def test_ai_frontend_entry_only_renders_on_ddl_page(self):
        index_html = INDEX_HTML_PATH.read_text(encoding='utf-8')
        app_js = APP_JS_PATH.read_text(encoding='utf-8')

        self.assertIn('v-if="showAiAssistant"', index_html)
        self.assertIn("return !this.adminMode && this.activePage === 'ddl' && this.appSettings.aiEnabled;", app_js)
        self.assertIn("if (this.activePage !== 'ddl' || !this.appSettings.aiEnabled) return;", app_js)
        self.assertIn("if (page !== 'ddl') this.aiChatOpen = false;", app_js)

    def test_ai_approval_subject_uses_template_select(self):
        index_html = INDEX_HTML_PATH.read_text(encoding='utf-8')

        self.assertIn("field.field === 'subject'", index_html)
        self.assertIn('v-model="action.draft.subject"', index_html)
        self.assertIn('allow-create', index_html)
        self.assertIn('v-for="subject in enabledSubjectOptions"', index_html)
        self.assertIn('placeholder="选择或输入科目"', index_html)

    def test_ai_approval_does_not_show_pending_status_text(self):
        index_html = INDEX_HTML_PATH.read_text(encoding='utf-8')
        app_js = APP_JS_PATH.read_text(encoding='utf-8')

        self.assertIn('aiActionStatus(action) !== \'pending\'', index_html)
        self.assertIn('>取消</el-button>', index_html)
        self.assertIn('>执行</el-button>', index_html)
        self.assertNotIn('待处理', app_js)
        self.assertNotIn('未处理', app_js)

    def test_frontend_settings_control_ai_and_pool_visibility(self):
        index_html = INDEX_HTML_PATH.read_text(encoding='utf-8')
        app_js = APP_JS_PATH.read_text(encoding='utf-8')
        style_css = STYLE_CSS_PATH.read_text(encoding='utf-8')

        self.assertIn('APP_SETTINGS_STORAGE_KEY', app_js)
        self.assertIn('todo-list-app-settings-v1', app_js)
        self.assertIn('appSettings: loadAppSettings()', app_js)
        self.assertIn('settingsDialogVisible', app_js)
        self.assertIn('saveAppSettings()', app_js)
        self.assertIn('showTaskPoolSection()', app_js)
        self.assertIn('showHabitPoolSection()', app_js)
        self.assertIn('@click="openSettingsDialog"', index_html)
        self.assertIn('v-if="showTaskPoolSection"', index_html)
        self.assertIn('v-if="showHabitPoolSection"', index_html)
        self.assertIn('v-model="appSettings.showUnscheduledDdl"', index_html)
        self.assertIn('v-model="appSettings.showArrangementPool"', index_html)
        self.assertIn('v-model="appSettings.showHabitPool"', index_html)
        self.assertIn('v-model="appSettings.aiEnabled"', index_html)
        self.assertIn('.settings-row', style_css)

    def test_admin_user_list_renders_avatar_column(self):
        index_html = INDEX_HTML_PATH.read_text(encoding='utf-8')
        app_js = APP_JS_PATH.read_text(encoding='utf-8')
        style_css = STYLE_CSS_PATH.read_text(encoding='utf-8')

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

    def test_admin_ai_usage_frontend_scaffold(self):
        index_html = INDEX_HTML_PATH.read_text(encoding='utf-8')
        app_js = APP_JS_PATH.read_text(encoding='utf-8')
        style_css = STYLE_CSS_PATH.read_text(encoding='utf-8')

        self.assertIn("adminSection === 'aiUsage'", index_html)
        self.assertIn('Token 使用情况', index_html)
        self.assertIn('saveAdminAiGlobalLimit', index_html)
        self.assertIn('saveAdminAiUserLimit(row)', index_html)
        self.assertIn('clearAllAdminAiUserLimits', index_html)
        self.assertIn('loadAdminAiUsage', app_js)
        self.assertIn("`${ADMIN_API}/ai-usage/summary", app_js)
        self.assertIn("`${ADMIN_API}/ai-usage/global-limit`", app_js)
        self.assertIn("`${ADMIN_API}/ai-usage/clear-user-limits`", app_js)
        self.assertIn('.ai-usage-output-line', style_css)
        self.assertIn('.ai-user-limit-editor', style_css)

    def test_admin_installer_download_frontend_scaffold(self):
        index_html = INDEX_HTML_PATH.read_text(encoding='utf-8')
        app_js = APP_JS_PATH.read_text(encoding='utf-8')
        style_css = STYLE_CSS_PATH.read_text(encoding='utf-8')

        self.assertIn("adminSection === 'installerDownloads'", index_html)
        self.assertIn('下载统计', index_html)
        self.assertIn('saveAdminInstallerDownloadGlobalLimit', index_html)
        self.assertIn('saveAdminInstallerDownloadUserLimit(row)', index_html)
        self.assertIn('clearAllAdminInstallerDownloadUserLimits', index_html)
        self.assertIn('loadAdminInstallerDownloads', app_js)
        self.assertIn("`${ADMIN_API}/installer-downloads/summary", app_js)
        self.assertIn("`${ADMIN_API}/installer-downloads/global-limit`", app_js)
        self.assertIn("`${ADMIN_API}/installer-downloads/clear-user-limits`", app_js)
        self.assertIn('contentDispositionFilename', app_js)
        self.assertIn('.installer-download-line', style_css)
        self.assertIn('.installer-download-limit-fields', style_css)


if __name__ == '__main__':
    unittest.main()
