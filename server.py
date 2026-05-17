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
        if path == '/api/schedule-items':
            return self.handle_create_schedule_item()
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def do_PUT(self):
        path = urlparse(self.path).path
        if path == '/api/tasks/bulk':
            return self.handle_bulk_replace()
        if path.startswith('/api/schedule-items/'):
            return self.handle_update_schedule_item(path.rsplit('/', 1)[-1])
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith('/api/schedule-items/'):
            return self.handle_delete_schedule_item(path.rsplit('/', 1)[-1])
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
        tasks = [
            {
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
            for row in rows
        ]
        return self.write_json({'tasks': tasks, 'readOnly': False, 'user': public_user(user)})

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
