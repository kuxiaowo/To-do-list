#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'todo-list.db'
HOST = os.environ.get('TODO_HOST', '0.0.0.0')
PORT = int(os.environ.get('TODO_PORT', '8092'))
PASSWORD_ITERATIONS = 260_000
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60

DEFAULT_WEEK_SLOTS = {
    '0': [
        {'keyBase': '0-09:00', 'label': '上午', 'start': '09:00', 'end': '10:00'},
        {'keyBase': '1-10:00', 'label': '上午', 'start': '10:00', 'end': '11:00'},
        {'keyBase': '2-11:00', 'label': '上午', 'start': '11:00', 'end': '12:00'},
        {'keyBase': '3-14:00', 'label': '下午', 'start': '14:00', 'end': '15:00'},
        {'keyBase': '4-15:00', 'label': '下午', 'start': '15:00', 'end': '16:00'},
        {'keyBase': '5-17:00', 'label': '下午', 'start': '17:00', 'end': '18:00'},
        {'keyBase': '6-18:00', 'label': '晚饭后', 'start': '18:00', 'end': '18:40'},
        {'keyBase': '7-18:40', 'label': '第一节晚自习', 'start': '18:40', 'end': '19:40'},
        {'keyBase': '8-19:50', 'label': '第二节晚自习', 'start': '19:50', 'end': '20:40'},
        {'keyBase': '9-20:50', 'label': '第三节晚自习', 'start': '20:50', 'end': '21:30'},
    ],
    '1': [
        {'keyBase': '0-13:00', 'label': '午休', 'start': '13:00', 'end': '13:45'},
        {'keyBase': '1-18:00', 'label': '晚饭后', 'start': '18:00', 'end': '18:40'},
        {'keyBase': '2-18:40', 'label': '第一节晚自习', 'start': '18:40', 'end': '19:40'},
        {'keyBase': '3-19:50', 'label': '第二节晚自习', 'start': '19:50', 'end': '20:40'},
        {'keyBase': '4-20:50', 'label': '第三节晚自习', 'start': '20:50', 'end': '21:30'},
    ],
    '2': [
        {'keyBase': '0-13:00', 'label': '午休', 'start': '13:00', 'end': '13:45'},
        {'keyBase': '1-18:00', 'label': '晚饭后', 'start': '18:00', 'end': '18:40'},
        {'keyBase': '2-18:40', 'label': '第一节晚自习', 'start': '18:40', 'end': '19:40'},
        {'keyBase': '3-19:50', 'label': '第二节晚自习', 'start': '19:50', 'end': '20:40'},
        {'keyBase': '4-20:50', 'label': '第三节晚自习', 'start': '20:50', 'end': '21:30'},
    ],
    '3': [
        {'keyBase': '0-13:00', 'label': '午休', 'start': '13:00', 'end': '13:45'},
        {'keyBase': '1-18:00', 'label': '晚饭后', 'start': '18:00', 'end': '18:40'},
        {'keyBase': '2-18:40', 'label': '第一节晚自习', 'start': '18:40', 'end': '19:40'},
        {'keyBase': '3-19:50', 'label': '第二节晚自习', 'start': '19:50', 'end': '20:40'},
        {'keyBase': '4-20:50', 'label': '第三节晚自习', 'start': '20:50', 'end': '21:30'},
    ],
    '4': [
        {'keyBase': '0-13:00', 'label': '午休', 'start': '13:00', 'end': '13:45'},
        {'keyBase': '1-18:00', 'label': '晚饭后', 'start': '18:00', 'end': '18:40'},
        {'keyBase': '2-18:40', 'label': '第一节晚自习', 'start': '18:40', 'end': '19:40'},
        {'keyBase': '3-19:50', 'label': '第二节晚自习', 'start': '19:50', 'end': '20:40'},
        {'keyBase': '4-20:50', 'label': '第三节晚自习', 'start': '20:50', 'end': '21:30'},
    ],
    '5': [
        {'keyBase': '0-13:00', 'label': '午休', 'start': '13:00', 'end': '13:45'},
    ],
    '6': [
        {'keyBase': '0-09:00', 'label': '上午', 'start': '09:00', 'end': '10:00'},
        {'keyBase': '1-10:00', 'label': '上午', 'start': '10:00', 'end': '11:00'},
        {'keyBase': '2-11:00', 'label': '上午', 'start': '11:00', 'end': '12:00'},
        {'keyBase': '3-14:00', 'label': '下午', 'start': '14:00', 'end': '15:00'},
        {'keyBase': '4-15:00', 'label': '下午', 'start': '15:00', 'end': '16:00'},
        {'keyBase': '5-17:00', 'label': '下午', 'start': '17:00', 'end': '18:00'},
        {'keyBase': '6-19:00', 'label': '晚上', 'start': '19:00', 'end': '20:00'},
    ],
}


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                nickname TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                created_at TEXT NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                due_at TEXT NOT NULL,
                priority TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS schedule_items (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                schedule_date TEXT NOT NULL,
                slot_key TEXT NOT NULL,
                slot_label TEXT NOT NULL,
                slot_start TEXT NOT NULL,
                slot_end TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS schedule_template_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                effective_from TEXT NOT NULL,
                slots_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS schedule_day_overrides (
                user_id INTEGER NOT NULL,
                schedule_date TEXT NOT NULL,
                slots_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(user_id, schedule_date),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        task_columns = {row[1] for row in conn.execute('PRAGMA table_info(tasks)').fetchall()}
        if 'subject' not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN subject TEXT NOT NULL DEFAULT ''")
        if 'user_id' not in task_columns:
            conn.execute('ALTER TABLE tasks ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1')
        conn.execute('UPDATE tasks SET user_id = 1 WHERE user_id IS NULL OR user_id = 0')
        conn.commit()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PASSWORD_ITERATIONS)
    return 'pbkdf2_sha256${}${}${}'.format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode('ascii'),
        base64.b64encode(digest).decode('ascii'),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored_hash.split('$', 3)
        if algorithm != 'pbkdf2_sha256':
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def normalize_task(task: dict, user_id: int) -> dict:
    return {
        'id': str(task.get('id', '')).strip(),
        'userId': user_id,
        'title': str(task.get('title', '')).strip(),
        'subject': str(task.get('subject', '')).strip(),
        'dueAt': str(task.get('dueAt', '')).strip(),
        'priority': str(task.get('priority', 'medium')).strip() or 'medium',
        'note': str(task.get('note', '') or ''),
        'completed': bool(task.get('completed', False)),
        'createdAt': str(task.get('createdAt', '') or ''),
        'updatedAt': str(task.get('updatedAt', '') or ''),
    }


def public_task(row: sqlite3.Row) -> dict:
    return {
        'id': row['id'],
        'userId': row['user_id'],
        'title': row['title'],
        'subject': row['subject'],
        'dueAt': row['due_at'],
        'priority': row['priority'],
        'note': row['note'],
        'completed': bool(row['completed']),
        'createdAt': row['created_at'],
        'updatedAt': row['updated_at'],
    }


def public_user(row: sqlite3.Row | dict) -> dict:
    return {
        'id': row['id'],
        'name': row['name'],
        'nickname': row['nickname'],
        'role': row['role'],
    }


def minutes_between(start: str, end: str) -> int:
    try:
        sh, sm = [int(part) for part in start.split(':', 1)]
        eh, em = [int(part) for part in end.split(':', 1)]
    except Exception:
        return 0
    return (eh * 60 + em) - (sh * 60 + sm)


def is_valid_time_text(value: str) -> bool:
    try:
        hour, minute = [int(part) for part in value.split(':', 1)]
    except Exception:
        return False
    return len(value) == 5 and value[2] == ':' and 0 <= hour <= 23 and 0 <= minute <= 59


def weekday_for_date(date_key: str) -> str:
    try:
        import datetime as _datetime

        return str((_datetime.date.fromisoformat(date_key).weekday() + 1) % 7)
    except Exception:
        return ''


def parse_slots_json(raw: str | None):
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def normalize_slot_list(slots, path: str = 'slots'):
    if not isinstance(slots, list):
        return None, f'{path} must be a list'
    normalized = []
    seen_keys = set()
    for index, slot in enumerate(slots):
        if not isinstance(slot, dict):
            return None, f'{path}[{index}] must be an object'
        label = str(slot.get('label', '')).strip()
        start = str(slot.get('start', '')).strip()
        end = str(slot.get('end', '')).strip()
        key_base = str(slot.get('keyBase', '')).strip() or f'custom-{int(time.time() * 1000)}-{secrets.token_hex(3)}-{index}'
        if not label or not start or not end:
            return None, f'{path}[{index}] label, start and end are required'
        if not is_valid_time_text(start) or not is_valid_time_text(end):
            return None, f'{path}[{index}] time must use HH:mm'
        if minutes_between(start, end) <= 0:
            return None, f'{path}[{index}] end must be later than start'
        if key_base in seen_keys:
            return None, f'{path}[{index}] keyBase is duplicated'
        seen_keys.add(key_base)
        normalized.append({'keyBase': key_base, 'label': label[:40], 'start': start, 'end': end})
    return normalized, None


def normalize_week_slots(value):
    if not isinstance(value, dict):
        return None, 'slots must be an object keyed by weekday'
    normalized = {}
    for weekday in [str(index) for index in range(7)]:
        slots, error = normalize_slot_list(value.get(weekday, []), f'slots[{weekday}]')
        if error:
            return None, error
        normalized[weekday] = slots
    return normalized, None


def slot_key(date_key: str, slot: dict) -> str:
    return f"{date_key}-{slot['keyBase']}"


def week_slots_for_date(conn: sqlite3.Connection, user_id: int, date_key: str) -> dict:
    row = conn.execute(
        '''
        SELECT slots_json FROM schedule_template_versions
        WHERE user_id = ? AND effective_from <= ?
        ORDER BY effective_from DESC, id DESC
        LIMIT 1
        ''',
        (user_id, date_key),
    ).fetchone()
    return (parse_slots_json(row['slots_json']) or DEFAULT_WEEK_SLOTS) if row else DEFAULT_WEEK_SLOTS


def effective_slots_for_date(conn: sqlite3.Connection, user_id: int, date_key: str) -> list[dict]:
    override = conn.execute(
        'SELECT slots_json FROM schedule_day_overrides WHERE user_id = ? AND schedule_date = ?',
        (user_id, date_key),
    ).fetchone()
    if override:
        parsed = json.loads(override['slots_json'])
        return parsed if isinstance(parsed, list) else []
    week_slots = week_slots_for_date(conn, user_id, date_key)
    weekday = weekday_for_date(date_key)
    return week_slots.get(weekday, [])


def conflict_with_existing_items(
    conn: sqlite3.Connection,
    user_id: int,
    dates: list[str],
    new_slots_by_date: dict[str, list[dict]],
):
    for date_key in dates:
        rows = conn.execute(
            '''
            SELECT slot_key, slot_start, slot_end, SUM(duration_minutes) AS used_minutes
            FROM schedule_items
            WHERE user_id = ? AND schedule_date = ?
            GROUP BY slot_key, slot_start, slot_end
            ''',
            (user_id, date_key),
        ).fetchall()
        if not rows:
            continue
        new_by_key = {slot_key(date_key, slot): slot for slot in new_slots_by_date.get(date_key, [])}
        for row in rows:
            slot = new_by_key.get(row['slot_key'])
            if not slot:
                return {
                    'error': 'time slot has existing schedule items',
                    'message': f"{date_key} 的时间段 {row['slot_start']}-{row['slot_end']} 已有安排，请先删除或调整安排。",
                }
            if slot['start'] != row['slot_start'] or slot['end'] != row['slot_end']:
                return {
                    'error': 'time slot has existing schedule items',
                    'message': f"{date_key} 的时间段 {row['slot_start']}-{row['slot_end']} 已有安排，不能修改开始或结束时间。",
                }
            if int(row['used_minutes'] or 0) > minutes_between(slot['start'], slot['end']):
                return {
                    'error': 'time slot capacity would be too small',
                    'message': f"{date_key} 的时间段容量不足以容纳已有安排。",
                }
    return None


def public_schedule_item(row: sqlite3.Row) -> dict:
    return {
        'id': row['id'],
        'userId': row['user_id'],
        'taskId': row['task_id'],
        'date': row['schedule_date'],
        'slotKey': row['slot_key'],
        'slotLabel': row['slot_label'],
        'slotStart': row['slot_start'],
        'slotEnd': row['slot_end'],
        'durationMinutes': row['duration_minutes'],
        'note': row['note'],
        'completed': bool(row['completed']),
        'createdAt': row['created_at'],
        'updatedAt': row['updated_at'],
        'task': {
            'id': row['task_id'],
            'title': row['task_title'],
            'subject': row['task_subject'],
            'dueAt': row['task_due_at'],
            'priority': row['task_priority'],
        },
    }


class TodoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/tasks':
            return self.handle_list_tasks()
        if path == '/api/schedule-items':
            return self.handle_list_schedule_items()
        if path == '/api/schedule-config':
            return self.handle_get_schedule_config()
        if path == '/api/auth/me':
            return self.handle_auth_me()
        if path == '/api/health':
            return self.write_json({'ok': True, 'database': str(DB_PATH)})
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/auth/register':
            return self.handle_auth_register()
        if path == '/api/auth/login':
            return self.handle_auth_login()
        if path == '/api/auth/logout':
            return self.handle_auth_logout()
        if path == '/api/tasks':
            return self.handle_create_task()
        if path == '/api/schedule-items':
            return self.handle_create_schedule_item()
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def do_PUT(self):
        path = urlparse(self.path).path
        if path == '/api/tasks/bulk':
            return self.handle_bulk_replace()
        if path.startswith('/api/tasks/'):
            return self.handle_update_task(path.rsplit('/', 1)[-1])
        if path.startswith('/api/schedule-items/'):
            return self.handle_update_schedule_item(path.rsplit('/', 1)[-1])
        if path == '/api/schedule-template':
            return self.handle_update_schedule_template()
        if path.startswith('/api/schedule-day-slots/'):
            return self.handle_update_schedule_day_slots(path.rsplit('/', 1)[-1])
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith('/api/tasks/'):
            return self.handle_delete_task(path.rsplit('/', 1)[-1])
        if path.startswith('/api/schedule-items/'):
            return self.handle_delete_schedule_item(path.rsplit('/', 1)[-1])
        if path == '/api/schedule-config':
            return self.handle_reset_schedule_config()
        if path.startswith('/api/schedule-day-slots/'):
            return self.handle_reset_schedule_day(path.rsplit('/', 1)[-1])
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def current_user(self):
        auth = self.headers.get('Authorization', '')
        if not auth.lower().startswith('bearer '):
            return None
        token = auth.split(' ', 1)[1].strip()
        if not token:
            return None
        now = int(time.time())
        with get_db() as conn:
            row = conn.execute(
                '''
                SELECT users.id, users.name, users.nickname, users.role, sessions.expires_at
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ?
                ''',
                (token,),
            ).fetchone()
            if not row:
                return None
            if int(row['expires_at']) < now:
                conn.execute('DELETE FROM sessions WHERE token = ?', (token,))
                conn.commit()
                return None
            conn.execute('UPDATE sessions SET expires_at = ? WHERE token = ?', (now + SESSION_TTL_SECONDS, token))
            conn.commit()
            return row

    def require_user(self):
        user = self.current_user()
        if not user:
            self.write_json({'error': 'login required'}, status=HTTPStatus.UNAUTHORIZED)
            return None
        return user

    def handle_list_tasks(self):
        user = self.current_user()
        if not user:
            return self.write_json({'tasks': [], 'readOnly': True})

        with get_db() as conn:
            rows = conn.execute(
                '''
                SELECT id, user_id, title, subject, due_at, priority, note, completed, created_at, updated_at
                FROM tasks
                WHERE user_id = ?
                ORDER BY due_at ASC, CASE priority
                    WHEN 'high' THEN 0
                    WHEN 'medium' THEN 1
                    ELSE 2
                END ASC, title COLLATE NOCASE ASC
                ''',
                (user['id'],),
            ).fetchall()
        tasks = [public_task(row) for row in rows]
        return self.write_json({'tasks': tasks, 'readOnly': False, 'user': public_user(user)})

    def validate_task_payload(self, payload: dict, user_id: int, task_id: str | None = None):
        if not isinstance(payload, dict):
            return None, {'error': 'task must be an object'}
        task = normalize_task({**payload, 'id': task_id or payload.get('id', '')}, user_id)
        if not task['id']:
            task['id'] = f"task-{int(time.time() * 1000)}-{secrets.token_hex(4)}"
        if not task['title']:
            return None, {'error': 'task title is required'}
        if task['priority'] not in {'high', 'medium', 'low'}:
            return None, {'error': 'invalid priority'}
        now = now_iso()
        if not task['createdAt']:
            task['createdAt'] = now
        task['updatedAt'] = now
        return task, None

    def handle_create_task(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        task, error = self.validate_task_payload(payload, int(user['id']))
        if error:
            return self.write_json(error, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            try:
                conn.execute(
                    '''
                    INSERT INTO tasks (id, user_id, title, subject, due_at, priority, note, completed, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        task['id'], task['userId'], task['title'], task['subject'], task['dueAt'],
                        task['priority'], task['note'], 1 if task['completed'] else 0,
                        task['createdAt'], task['updatedAt'],
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return self.write_json({'error': 'task id already exists'}, status=HTTPStatus.CONFLICT)
            row = conn.execute(
                'SELECT id, user_id, title, subject, due_at, priority, note, completed, created_at, updated_at FROM tasks WHERE id = ? AND user_id = ?',
                (task['id'], user['id']),
            ).fetchone()
        return self.write_json({'ok': True, 'task': public_task(row)}, status=HTTPStatus.CREATED)

    def handle_update_task(self, task_id: str):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        task, error = self.validate_task_payload(payload, int(user['id']), task_id=task_id)
        if error:
            return self.write_json(error, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            existing = conn.execute('SELECT created_at FROM tasks WHERE id = ? AND user_id = ?', (task_id, user['id'])).fetchone()
            if not existing:
                return self.write_json({'error': 'task not found'}, status=HTTPStatus.NOT_FOUND)
            conn.execute(
                '''
                UPDATE tasks
                SET title = ?, subject = ?, due_at = ?, priority = ?, note = ?, completed = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                ''',
                (
                    task['title'], task['subject'], task['dueAt'], task['priority'], task['note'],
                    1 if task['completed'] else 0, task['updatedAt'], task_id, user['id'],
                ),
            )
            conn.commit()
            row = conn.execute(
                'SELECT id, user_id, title, subject, due_at, priority, note, completed, created_at, updated_at FROM tasks WHERE id = ? AND user_id = ?',
                (task_id, user['id']),
            ).fetchone()
        return self.write_json({'ok': True, 'task': public_task(row)})

    def handle_delete_task(self, task_id: str):
        user = self.require_user()
        if not user:
            return
        with get_db() as conn:
            conn.execute('DELETE FROM schedule_items WHERE task_id = ? AND user_id = ?', (task_id, user['id']))
            cursor = conn.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user['id']))
            conn.commit()
        if cursor.rowcount == 0:
            return self.write_json({'error': 'task not found'}, status=HTTPStatus.NOT_FOUND)
        return self.write_json({'ok': True})

    def handle_bulk_replace(self):
        user = self.require_user()
        if not user:
            return

        payload = self.read_json_body()
        if payload is None:
            return

        tasks = payload.get('tasks')
        if not isinstance(tasks, list):
            return self.write_json({'error': 'tasks must be a list'}, status=HTTPStatus.BAD_REQUEST)

        normalized = []
        for task in tasks:
            if not isinstance(task, dict):
                return self.write_json({'error': 'each task must be an object'}, status=HTTPStatus.BAD_REQUEST)
            item = normalize_task(task, int(user['id']))
            if not item['id'] or not item['title']:
                return self.write_json({'error': 'task id/title are required'}, status=HTTPStatus.BAD_REQUEST)
            normalized.append(item)

        with get_db() as conn:
            conn.execute('BEGIN')
            conn.execute('DELETE FROM tasks WHERE user_id = ?', (user['id'],))
            conn.executemany(
                '''
                INSERT INTO tasks (id, user_id, title, subject, due_at, priority, note, completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                [
                    (
                        item['id'],
                        item['userId'],
                        item['title'],
                        item['subject'],
                        item['dueAt'],
                        item['priority'],
                        item['note'],
                        1 if item['completed'] else 0,
                        item['createdAt'],
                        item['updatedAt'],
                    )
                    for item in normalized
                ],
            )
            conn.commit()

        return self.write_json({'ok': True, 'count': len(normalized), 'user': public_user(user)})

    def handle_list_schedule_items(self):
        user = self.current_user()
        if not user:
            return self.write_json({'items': [], 'readOnly': True})

        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT schedule_items.*, tasks.title AS task_title, tasks.subject AS task_subject,
                       tasks.due_at AS task_due_at, tasks.priority AS task_priority
                FROM schedule_items
                JOIN tasks ON tasks.id = schedule_items.task_id AND tasks.user_id = schedule_items.user_id
                WHERE schedule_items.user_id = ?
                ORDER BY schedule_items.schedule_date ASC, schedule_items.slot_start ASC, schedule_items.created_at ASC
                """,
                (user['id'],),
            ).fetchall()
        return self.write_json({'items': [public_schedule_item(row) for row in rows], 'readOnly': False})

    def handle_get_schedule_config(self):
        user = self.current_user()
        if not user:
            return self.write_json({
                'defaultWeekSlots': DEFAULT_WEEK_SLOTS,
                'templateVersions': [],
                'dayOverrides': {},
                'readOnly': True,
            })

        with get_db() as conn:
            versions = conn.execute(
                '''
                SELECT id, effective_from, slots_json, created_at, updated_at
                FROM schedule_template_versions
                WHERE user_id = ?
                ORDER BY effective_from ASC, id ASC
                ''',
                (user['id'],),
            ).fetchall()
            overrides = conn.execute(
                '''
                SELECT schedule_date, slots_json
                FROM schedule_day_overrides
                WHERE user_id = ?
                ORDER BY schedule_date ASC
                ''',
                (user['id'],),
            ).fetchall()

        return self.write_json({
            'defaultWeekSlots': DEFAULT_WEEK_SLOTS,
            'templateVersions': [
                {
                    'id': row['id'],
                    'effectiveFrom': row['effective_from'],
                    'slots': parse_slots_json(row['slots_json']) or DEFAULT_WEEK_SLOTS,
                    'createdAt': row['created_at'],
                    'updatedAt': row['updated_at'],
                }
                for row in versions
            ],
            'dayOverrides': {
                row['schedule_date']: json.loads(row['slots_json'])
                for row in overrides
            },
            'readOnly': False,
        })

    def handle_update_schedule_template(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        effective_from = str(payload.get('effectiveFrom', '')).strip()
        week_slots, error = normalize_week_slots(payload.get('slots'))
        if not effective_from or error:
            return self.write_json({'error': error or 'effectiveFrom is required'}, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            rows = conn.execute(
                '''
                SELECT DISTINCT schedule_date
                FROM schedule_items
                WHERE user_id = ? AND schedule_date >= ?
                ORDER BY schedule_date ASC
                ''',
                (user['id'], effective_from),
            ).fetchall()
            dates = []
            next_slots = {}
            for row in rows:
                date_key = row['schedule_date']
                override = conn.execute(
                    'SELECT 1 FROM schedule_day_overrides WHERE user_id = ? AND schedule_date = ?',
                    (user['id'], date_key),
                ).fetchone()
                if override:
                    continue
                later_version = conn.execute(
                    '''
                    SELECT 1 FROM schedule_template_versions
                    WHERE user_id = ? AND effective_from > ? AND effective_from <= ?
                    LIMIT 1
                    ''',
                    (user['id'], effective_from, date_key),
                ).fetchone()
                if later_version:
                    continue
                dates.append(date_key)
                next_slots[date_key] = week_slots.get(weekday_for_date(date_key), [])
            conflict = conflict_with_existing_items(conn, int(user['id']), dates, next_slots)
            if conflict:
                return self.write_json(conflict, status=HTTPStatus.CONFLICT)

            now = now_iso()
            conn.execute(
                '''
                INSERT INTO schedule_template_versions (user_id, effective_from, slots_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (user['id'], effective_from, json.dumps(week_slots, ensure_ascii=False), now, now),
            )
            conn.commit()
        return self.write_json({'ok': True})

    def handle_update_schedule_day_slots(self, date_key: str):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        slots, error = normalize_slot_list(payload.get('slots'), 'slots')
        if error:
            return self.write_json({'error': error}, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            conflict = conflict_with_existing_items(conn, int(user['id']), [date_key], {date_key: slots})
            if conflict:
                return self.write_json(conflict, status=HTTPStatus.CONFLICT)
            now = now_iso()
            conn.execute(
                '''
                INSERT INTO schedule_day_overrides (user_id, schedule_date, slots_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, schedule_date)
                DO UPDATE SET slots_json = excluded.slots_json, updated_at = excluded.updated_at
                ''',
                (user['id'], date_key, json.dumps(slots, ensure_ascii=False), now, now),
            )
            conn.commit()
        return self.write_json({'ok': True})

    def handle_reset_schedule_day(self, date_key: str):
        user = self.require_user()
        if not user:
            return
        with get_db() as conn:
            template_slots = week_slots_for_date(conn, int(user['id']), date_key).get(weekday_for_date(date_key), [])
            conflict = conflict_with_existing_items(conn, int(user['id']), [date_key], {date_key: template_slots})
            if conflict:
                return self.write_json(conflict, status=HTTPStatus.CONFLICT)
            conn.execute('DELETE FROM schedule_day_overrides WHERE user_id = ? AND schedule_date = ?', (user['id'], date_key))
            conn.commit()
        return self.write_json({'ok': True})

    def handle_reset_schedule_config(self):
        user = self.require_user()
        if not user:
            return
        with get_db() as conn:
            rows = conn.execute(
                '''
                SELECT DISTINCT schedule_date
                FROM schedule_items
                WHERE user_id = ?
                ORDER BY schedule_date ASC
                ''',
                (user['id'],),
            ).fetchall()
            dates = [row['schedule_date'] for row in rows]
            next_slots = {
                date_key: DEFAULT_WEEK_SLOTS.get(weekday_for_date(date_key), [])
                for date_key in dates
            }
            conflict = conflict_with_existing_items(conn, int(user['id']), dates, next_slots)
            if conflict:
                return self.write_json(conflict, status=HTTPStatus.CONFLICT)
            conn.execute('DELETE FROM schedule_day_overrides WHERE user_id = ?', (user['id'],))
            conn.execute('DELETE FROM schedule_template_versions WHERE user_id = ?', (user['id'],))
            conn.commit()
        return self.write_json({'ok': True})

    def validate_schedule_payload(self, payload: dict, user_id: int, existing_id: str | None = None):
        task_id = str(payload.get('taskId', '')).strip()
        schedule_date = str(payload.get('date', '')).strip()
        slot_key = str(payload.get('slotKey', '')).strip()
        slot_label = str(payload.get('slotLabel', '')).strip()
        slot_start = str(payload.get('slotStart', '')).strip()
        slot_end = str(payload.get('slotEnd', '')).strip()
        note = str(payload.get('note', '') or '').strip()
        try:
            duration_minutes = int(payload.get('durationMinutes'))
        except Exception:
            return None, {'error': 'durationMinutes must be an integer'}

        if not task_id or not schedule_date or not slot_key or not slot_start or not slot_end:
            return None, {'error': 'taskId, date, slotKey, slotStart and slotEnd are required'}
        if duration_minutes <= 0:
            return None, {'error': 'durationMinutes must be positive'}
        slot_capacity = minutes_between(slot_start, slot_end)
        if slot_capacity <= 0:
            return None, {'error': 'invalid slot time range'}
        if duration_minutes > slot_capacity:
            return None, {'error': 'duration exceeds slot capacity'}
        if len(note) > 500:
            return None, {'error': 'note is too long'}

        with get_db() as conn:
            task = conn.execute('SELECT id FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id)).fetchone()
            if not task:
                return None, {'error': 'task not found'}
            if existing_id:
                used = conn.execute(
                    """
                    SELECT COALESCE(SUM(duration_minutes), 0) FROM schedule_items
                    WHERE user_id = ? AND schedule_date = ? AND slot_key = ? AND id != ?
                    """,
                    (user_id, schedule_date, slot_key, existing_id),
                ).fetchone()[0]
            else:
                used = conn.execute(
                    """
                    SELECT COALESCE(SUM(duration_minutes), 0) FROM schedule_items
                    WHERE user_id = ? AND schedule_date = ? AND slot_key = ?
                    """,
                    (user_id, schedule_date, slot_key),
                ).fetchone()[0]
        if int(used) + duration_minutes > slot_capacity:
            return None, {'error': 'time slot capacity exceeded', 'usedMinutes': int(used), 'capacityMinutes': slot_capacity}

        return {
            'taskId': task_id,
            'date': schedule_date,
            'slotKey': slot_key,
            'slotLabel': slot_label or slot_key,
            'slotStart': slot_start,
            'slotEnd': slot_end,
            'durationMinutes': duration_minutes,
            'note': note,
        }, None

    def handle_create_schedule_item(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        item, error = self.validate_schedule_payload(payload, int(user['id']))
        if error:
            return self.write_json(error, status=HTTPStatus.BAD_REQUEST)
        item_id = f"schedule-{int(time.time() * 1000)}-{secrets.token_hex(4)}"
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO schedule_items
                (id, user_id, task_id, schedule_date, slot_key, slot_label, slot_start, slot_end,
                 duration_minutes, note, completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id, user['id'], item['taskId'], item['date'], item['slotKey'], item['slotLabel'],
                    item['slotStart'], item['slotEnd'], item['durationMinutes'], item['note'],
                    0, now_iso(), now_iso(),
                ),
            )
            conn.commit()
        return self.write_json({'ok': True, 'id': item_id}, status=HTTPStatus.CREATED)

    def handle_update_schedule_item(self, item_id: str):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        with get_db() as conn:
            existing = conn.execute('SELECT * FROM schedule_items WHERE id = ? AND user_id = ?', (item_id, user['id'])).fetchone()
        if not existing:
            return self.write_json({'error': 'schedule item not found'}, status=HTTPStatus.NOT_FOUND)

        merged = {
            'taskId': existing['task_id'],
            'date': existing['schedule_date'],
            'slotKey': existing['slot_key'],
            'slotLabel': existing['slot_label'],
            'slotStart': existing['slot_start'],
            'slotEnd': existing['slot_end'],
            'durationMinutes': payload.get('durationMinutes', existing['duration_minutes']),
            'note': payload.get('note', existing['note']),
        }
        item, error = self.validate_schedule_payload(merged, int(user['id']), existing_id=item_id)
        if error:
            return self.write_json(error, status=HTTPStatus.BAD_REQUEST)
        completed = bool(payload.get('completed')) if 'completed' in payload else bool(existing['completed'])
        with get_db() as conn:
            conn.execute(
                """
                UPDATE schedule_items
                SET duration_minutes = ?, note = ?, completed = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (item['durationMinutes'], item['note'], 1 if completed else 0, now_iso(), item_id, user['id']),
            )
            conn.commit()
        return self.write_json({'ok': True, 'id': item_id})

    def handle_delete_schedule_item(self, item_id: str):
        user = self.require_user()
        if not user:
            return
        with get_db() as conn:
            cursor = conn.execute('DELETE FROM schedule_items WHERE id = ? AND user_id = ?', (item_id, user['id']))
            conn.commit()
        if cursor.rowcount == 0:
            return self.write_json({'error': 'schedule item not found'}, status=HTTPStatus.NOT_FOUND)
        return self.write_json({'ok': True})

    def handle_auth_register(self):
        payload = self.read_json_body()
        if payload is None:
            return
        name = str(payload.get('name', '')).strip()
        nickname = str(payload.get('nickname', '')).strip()
        password = str(payload.get('password', ''))
        if not name or not nickname or not password:
            return self.write_json({'error': 'name, nickname and password are required'}, status=HTTPStatus.BAD_REQUEST)
        if len(name) > 64 or len(nickname) > 32:
            return self.write_json({'error': 'name or nickname is too long'}, status=HTTPStatus.BAD_REQUEST)
        if len(password) < 6:
            return self.write_json({'error': 'password must be at least 6 characters'}, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            try:
                cursor = conn.execute(
                    'INSERT INTO users (name, nickname, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
                    (name, nickname, hash_password(password), 'student', now_iso()),
                )
                conn.commit()
                user_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                return self.write_json({'error': 'nickname already exists'}, status=HTTPStatus.CONFLICT)
            user = conn.execute('SELECT id, name, nickname, role FROM users WHERE id = ?', (user_id,)).fetchone()
        return self.issue_session_response(user)

    def handle_auth_login(self):
        payload = self.read_json_body()
        if payload is None:
            return
        nickname = str(payload.get('nickname', '')).strip()
        password = str(payload.get('password', ''))
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE lower(nickname) = lower(?)', (nickname,)).fetchone()
        if not user or not verify_password(password, user['password_hash']):
            return self.write_json({'error': 'invalid nickname or password'}, status=HTTPStatus.UNAUTHORIZED)
        return self.issue_session_response(user)

    def handle_auth_me(self):
        user = self.current_user()
        if not user:
            return self.write_json({'error': 'login required'}, status=HTTPStatus.UNAUTHORIZED)
        return self.write_json({'user': public_user(user)})

    def handle_auth_logout(self):
        auth = self.headers.get('Authorization', '')
        if auth.lower().startswith('bearer '):
            token = auth.split(' ', 1)[1].strip()
            with get_db() as conn:
                conn.execute('DELETE FROM sessions WHERE token = ?', (token,))
                conn.commit()
        return self.write_json({'ok': True})

    def issue_session_response(self, user):
        token = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + SESSION_TTL_SECONDS
        with get_db() as conn:
            conn.execute(
                'INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)',
                (token, user['id'], expires_at, now_iso()),
            )
            conn.commit()
        return self.write_json({'token': token, 'user': public_user(user)})

    def read_json_body(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.write_json({'error': 'invalid content length'}, status=HTTPStatus.BAD_REQUEST)
        raw = self.rfile.read(length) if length > 0 else b''
        try:
            return json.loads(raw.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            self.write_json({'error': 'invalid json'}, status=HTTPStatus.BAD_REQUEST)
            return None

    def write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args):
        super().log_message(format, *args)


if __name__ == '__main__':
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), TodoHandler)
    print(f'Serving To-Do List on http://{HOST}:{PORT} (db: {DB_PATH})')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
