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
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'todo-list.db'
HOST = os.environ.get('TODO_HOST', '127.0.0.1')
PORT = int(os.environ.get('TODO_PORT', '8092'))
PASSWORD_ITERATIONS = 260_000
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_FEEDBACK_LIMIT_PER_USER = 10
FEEDBACK_LIMIT_SETTING_KEY = 'feedback_limit_per_user'
DEFAULT_SUBJECTS = [
    'Chinese',
    'Mathematics',
    'English B',
    'IELTS',
    'Physics',
    'Economics',
    'Chemistry',
    'Psychology',
    'Biology',
    'Computer Science',
]

# Weekday keys follow JavaScript Date.getDay(): 0 is Sunday, 1 is Monday.
# The frontend also keeps a fallback copy, but this server-side value is the
# canonical default returned by /api/schedule-config.
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
    """Create the SQLite schema and apply small in-place migrations."""
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
                pool TEXT NOT NULL DEFAULT 'todo',
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
                sort_order REAL NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            '''
        )
        columns = {row[1] for row in conn.execute('PRAGMA table_info(schedule_items)').fetchall()}
        if 'sort_order' not in columns:
            conn.execute('ALTER TABLE schedule_items ADD COLUMN sort_order REAL NOT NULL DEFAULT 0')
            rows = conn.execute(
                '''
                SELECT id, user_id, schedule_date, slot_key
                FROM schedule_items
                ORDER BY user_id ASC, schedule_date ASC, slot_start ASC, created_at ASC, id ASC
                '''
            ).fetchall()
            slot_counts = {}
            for row in rows:
                key = (row[1], row[2], row[3])
                slot_counts[key] = slot_counts.get(key, 0) + 1
                conn.execute(
                    'UPDATE schedule_items SET sort_order = ? WHERE id = ?',
                    (slot_counts[key] * 1024, row[0]),
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
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id INTEGER,
                target_user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                detail_json TEXT NOT NULL DEFAULT '{}',
                ip TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(actor_user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                admin_reply TEXT NOT NULL DEFAULT '',
                replied_by INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(replied_by) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS subject_templates (
                user_id INTEGER PRIMARY KEY,
                subjects_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS visit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL DEFAULT '',
                page TEXT NOT NULL,
                path TEXT NOT NULL DEFAULT '',
                user_id INTEGER,
                user_agent TEXT NOT NULL DEFAULT '',
                referer TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_visit_logs_created_at ON visit_logs(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_visit_logs_ip ON visit_logs(ip)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_visit_logs_page ON visit_logs(page)')
        conn.execute(
            '''
            INSERT OR IGNORE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ''',
            (FEEDBACK_LIMIT_SETTING_KEY, str(DEFAULT_FEEDBACK_LIMIT_PER_USER), now_iso()),
        )
        task_columns = {row[1] for row in conn.execute('PRAGMA table_info(tasks)').fetchall()}
        if 'subject' not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN subject TEXT NOT NULL DEFAULT ''")
        if 'user_id' not in task_columns:
            conn.execute('ALTER TABLE tasks ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1')
        if 'pool' not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN pool TEXT NOT NULL DEFAULT 'todo'")
        conn.execute('UPDATE tasks SET user_id = 1 WHERE user_id IS NULL OR user_id = 0')
        conn.execute("UPDATE tasks SET pool = 'todo' WHERE pool IS NULL OR pool = ''")
        conn.commit()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def hash_password(password: str) -> str:
    """Return a self-describing PBKDF2 hash string for password storage."""
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
    """Normalize external task JSON to the internal/public field names."""
    return {
        'id': str(task.get('id', '')).strip(),
        'userId': user_id,
        'title': str(task.get('title', '')).strip(),
        'subject': str(task.get('subject', '')).strip(),
        'dueAt': str(task.get('dueAt', '')).strip(),
        'pool': str(task.get('pool', 'todo')).strip() or 'todo',
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
        'pool': row['pool'],
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


def default_subject_template() -> list[dict]:
    return [{'name': name, 'preset': True, 'enabled': True} for name in DEFAULT_SUBJECTS]


def normalize_subject_template(raw_subjects) -> tuple[list[dict] | None, str | None]:
    if raw_subjects is None:
        return default_subject_template(), None
    if not isinstance(raw_subjects, list):
        return None, 'subjects must be a list'

    raw_by_name = {}
    for item in raw_subjects:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name', '')).strip()
        if not name:
            continue
        if len(name) > 40:
            return None, 'subject name is too long'
        raw_by_name[name.casefold()] = item

    subjects = []
    seen = set()
    for name in DEFAULT_SUBJECTS:
        key = name.casefold()
        raw = raw_by_name.get(key, {})
        subjects.append({'name': name, 'preset': True, 'enabled': bool(raw.get('enabled', True))})
        seen.add(key)

    for item in raw_subjects:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name', '')).strip()
        if not name:
            continue
        if len(name) > 40:
            return None, 'subject name is too long'
        key = name.casefold()
        if key in seen:
            continue
        subjects.append({'name': name, 'preset': False, 'enabled': bool(item.get('enabled', True))})
        seen.add(key)

    return subjects, None


def parse_subject_template(raw_json: str | None) -> list[dict]:
    if not raw_json:
        return default_subject_template()
    try:
        payload = json.loads(raw_json)
    except (TypeError, json.JSONDecodeError):
        return default_subject_template()
    subjects, error = normalize_subject_template(payload)
    return default_subject_template() if error else subjects


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
    return len(value.split(':', 1)[0]) in {1, 2} and len(value.split(':', 1)[1]) == 2 and 0 <= hour <= 23 and 0 <= minute <= 59


def normalize_time_text(value: str) -> str:
    value = str(value).strip()
    if not is_valid_time_text(value):
        return ''
    hour, minute = [int(part) for part in value.split(':', 1)]
    return f'{hour:02d}:{minute:02d}'


def weekday_for_date(date_key: str) -> str:
    """Convert an ISO date to the weekday key used by DEFAULT_WEEK_SLOTS."""
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
    """Validate and normalize one day's editable time slots."""
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
            return None, f'{path}[{index}] time must use H:mm or HH:mm'
        start = normalize_time_text(start)
        end = normalize_time_text(end)
        if minutes_between(start, end) <= 0:
            return None, f'{path}[{index}] end must be later than start'
        if key_base in seen_keys:
            return None, f'{path}[{index}] keyBase is duplicated'
        seen_keys.add(key_base)
        normalized.append({'keyBase': key_base, 'label': label[:40], 'start': start, 'end': end})
    normalized.sort(key=lambda slot: (slot['start'], slot['end']))
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
    """Return the latest weekly template version effective on date_key."""
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
    """Return the slots for a date, with single-day overrides taking priority."""
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
    """Reject slot config changes that would strand or shrink existing items."""
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
        'sortOrder': row['sort_order'],
        'note': row['note'],
        'completed': bool(row['completed']),
        'createdAt': row['created_at'],
        'updatedAt': row['updated_at'],
        'task': {
            'id': row['task_id'],
            'title': row['task_title'],
            'subject': row['task_subject'],
            'dueAt': row['task_due_at'],
            'pool': row['task_pool'],
            'priority': row['task_priority'],
        },
    }


def public_operation_log(row: sqlite3.Row) -> dict:
    try:
        detail = json.loads(row['detail_json'] or '{}')
    except json.JSONDecodeError:
        detail = {}
    return {
        'id': row['id'],
        'actorUserId': row['actor_user_id'],
        'targetUserId': row['target_user_id'],
        'action': row['action'],
        'entityType': row['entity_type'],
        'entityId': row['entity_id'],
        'detail': detail,
        'ip': row['ip'],
        'createdAt': row['created_at'],
    }


def public_feedback(row: sqlite3.Row, include_user: bool = False) -> dict:
    payload = {
        'id': row['id'],
        'userId': row['user_id'],
        'content': row['content'],
        'adminReply': row['admin_reply'],
        'repliedBy': row['replied_by'],
        'status': row['status'],
        'createdAt': row['created_at'],
        'updatedAt': row['updated_at'],
    }
    if include_user:
        payload['user'] = {
            'id': row['user_id'],
            'name': row['user_name'],
            'nickname': row['user_nickname'],
        }
    return payload


def get_feedback_limit(conn: sqlite3.Connection) -> int:
    row = conn.execute('SELECT value FROM app_settings WHERE key = ?', (FEEDBACK_LIMIT_SETTING_KEY,)).fetchone()
    if not row:
        return DEFAULT_FEEDBACK_LIMIT_PER_USER
    try:
        return max(1, int(row['value']))
    except (TypeError, ValueError):
        return DEFAULT_FEEDBACK_LIMIT_PER_USER


def set_feedback_limit(conn: sqlite3.Connection, limit: int) -> None:
    conn.execute(
        '''
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        ''',
        (FEEDBACK_LIMIT_SETTING_KEY, str(limit), now_iso()),
    )


class TodoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith('/api/admin/'):
            return self.handle_admin_get(path)
        if path == '/api/tasks':
            return self.handle_list_tasks()
        if path == '/api/schedule-items':
            return self.handle_list_schedule_items()
        if path == '/api/schedule-config':
            return self.handle_get_schedule_config()
        if path == '/api/subject-template':
            return self.handle_get_subject_template()
        if path == '/api/feedback':
            return self.handle_list_feedback()
        if path == '/api/auth/me':
            return self.handle_auth_me()
        if path == '/api/health':
            return self.write_json({'ok': True, 'database': str(DB_PATH)})
        if path in {'/', '/index.html'}:
            self.record_visit('home', path)
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/visits':
            return self.handle_create_visit()
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
        if path == '/api/feedback':
            return self.handle_create_feedback()
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def do_PUT(self):
        path = urlparse(self.path).path
        if path == '/api/auth/nickname':
            return self.handle_auth_update_nickname()
        if path == '/api/auth/password':
            return self.handle_auth_update_password()
        if path == '/api/admin/feedback-settings':
            return self.handle_admin_update_feedback_settings()
        if path.startswith('/api/admin/feedback/') and path.endswith('/reply'):
            parts = path.strip('/').split('/')
            if len(parts) == 5:
                return self.handle_admin_reply_feedback(parts[3])
        if path.startswith('/api/admin/users/'):
            return self.handle_admin_update_user(path.rsplit('/', 1)[-1])
        if path.startswith('/api/tasks/'):
            return self.handle_update_task(path.rsplit('/', 1)[-1])
        if path.startswith('/api/schedule-items/'):
            return self.handle_update_schedule_item(path.rsplit('/', 1)[-1])
        if path == '/api/schedule-template':
            return self.handle_update_schedule_template()
        if path == '/api/subject-template':
            return self.handle_update_subject_template()
        if path.startswith('/api/schedule-day-slots/'):
            return self.handle_update_schedule_day_slots(path.rsplit('/', 1)[-1])
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith('/api/admin/feedback/'):
            return self.handle_admin_delete_feedback(path.rsplit('/', 1)[-1])
        if path.startswith('/api/feedback/'):
            return self.handle_delete_feedback(path.rsplit('/', 1)[-1])
        if path.startswith('/api/admin/users/'):
            return self.handle_admin_delete_user(path.rsplit('/', 1)[-1])
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
        """Resolve the bearer token and slide the session expiration forward."""
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

    def require_admin(self):
        user = self.require_user()
        if not user:
            return None
        if user['role'] != 'admin':
            self.write_json({'error': 'admin required'}, status=HTTPStatus.FORBIDDEN)
            return None
        return user

    def log_operation(
        self,
        conn: sqlite3.Connection,
        actor_user_id: int | None,
        target_user_id: int,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        detail: dict | None = None,
    ) -> None:
        conn.execute(
            '''
            INSERT INTO operation_logs
            (actor_user_id, target_user_id, action, entity_type, entity_id, detail_json, ip, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                actor_user_id,
                target_user_id,
                action,
                entity_type,
                entity_id,
                json.dumps(detail or {}, ensure_ascii=False),
                self.client_address[0] if self.client_address else '',
                now_iso(),
            ),
        )

    def fetch_tasks_for_user(self, conn: sqlite3.Connection, user_id: int) -> list[dict]:
        rows = conn.execute(
            '''
            SELECT id, user_id, title, subject, due_at, pool, priority, note, completed, created_at, updated_at
            FROM tasks
            WHERE user_id = ?
            ORDER BY due_at ASC, CASE priority
                WHEN 'high' THEN 0
                WHEN 'medium' THEN 1
                ELSE 2
            END ASC, title COLLATE NOCASE ASC
            ''',
            (user_id,),
        ).fetchall()
        return [public_task(row) for row in rows]

    def fetch_schedule_items_for_user(self, conn: sqlite3.Connection, user_id: int) -> list[dict]:
        rows = conn.execute(
            """
            SELECT schedule_items.*, tasks.title AS task_title, tasks.subject AS task_subject,
                   tasks.due_at AS task_due_at, tasks.pool AS task_pool, tasks.priority AS task_priority
            FROM schedule_items
            JOIN tasks ON tasks.id = schedule_items.task_id AND tasks.user_id = schedule_items.user_id
            WHERE schedule_items.user_id = ?
            ORDER BY schedule_items.schedule_date ASC, schedule_items.slot_start ASC, schedule_items.sort_order ASC, schedule_items.created_at ASC
            """,
            (user_id,),
        ).fetchall()
        return [public_schedule_item(row) for row in rows]

    def fetch_schedule_config_for_user(self, conn: sqlite3.Connection, user_id: int) -> dict:
        versions = conn.execute(
            '''
            SELECT id, effective_from, slots_json, created_at, updated_at
            FROM schedule_template_versions
            WHERE user_id = ?
            ORDER BY effective_from ASC, id ASC
            ''',
            (user_id,),
        ).fetchall()
        overrides = conn.execute(
            '''
            SELECT schedule_date, slots_json
            FROM schedule_day_overrides
            WHERE user_id = ?
            ORDER BY schedule_date ASC
            ''',
            (user_id,),
        ).fetchall()
        return {
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
        }

    def handle_admin_get(self, path: str):
        admin = self.require_admin()
        if not admin:
            return
        parts = path.strip('/').split('/')
        if parts == ['api', 'admin', 'users']:
            return self.handle_admin_users()
        if parts == ['api', 'admin', 'feedback']:
            return self.handle_admin_feedback()
        if parts == ['api', 'admin', 'feedback-settings']:
            return self.handle_admin_feedback_settings()
        if parts == ['api', 'admin', 'traffic', 'summary']:
            return self.handle_admin_traffic_summary()
        if len(parts) == 5 and parts[:3] == ['api', 'admin', 'users']:
            try:
                target_user_id = int(parts[3])
            except ValueError:
                return self.write_json({'error': 'invalid user id'}, status=HTTPStatus.BAD_REQUEST)
            if parts[4] == 'tasks':
                return self.handle_admin_user_tasks(target_user_id)
            if parts[4] == 'schedule-items':
                return self.handle_admin_user_schedule_items(target_user_id)
            if parts[4] == 'schedule-config':
                return self.handle_admin_user_schedule_config(target_user_id)
            if parts[4] == 'logs':
                return self.handle_admin_user_logs(target_user_id)
        return self.write_json({'error': 'not found'}, status=HTTPStatus.NOT_FOUND)

    def ensure_user_exists(self, conn: sqlite3.Connection, user_id: int):
        row = conn.execute('SELECT id, name, nickname, role, created_at FROM users WHERE id = ?', (user_id,)).fetchone()
        return row

    def request_ip(self) -> str:
        return self.client_address[0] if self.client_address else ''

    def record_visit(self, page: str, path: str, user_id: int | None = None) -> None:
        with get_db() as conn:
            conn.execute(
                '''
                INSERT INTO visit_logs (ip, page, path, user_id, user_agent, referer, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    self.request_ip(),
                    page[:40],
                    path[:500],
                    user_id,
                    str(self.headers.get('User-Agent', ''))[:1000],
                    str(self.headers.get('Referer', ''))[:1000],
                    now_iso(),
                ),
            )
            conn.commit()

    def handle_create_visit(self):
        payload = self.read_json_body()
        if payload is None:
            return
        page = str(payload.get('page', '')).strip()
        if page not in {'admin'}:
            return self.write_json({'error': 'invalid page'}, status=HTTPStatus.BAD_REQUEST)
        user = self.current_user()
        visit_path = str(payload.get('path', '')).strip() or urlparse(self.path).path
        self.record_visit(page, visit_path, int(user['id']) if user else None)
        return self.write_json({'ok': True})

    def handle_admin_traffic_summary(self):
        query = parse_qs(urlparse(self.path).query)
        traffic_view = str(query.get('view', ['7d'])[0]).strip()
        if traffic_view not in {'30d', '7d', '1d', '6h'}:
            return self.write_json({'error': 'invalid traffic view'}, status=HTTPStatus.BAD_REQUEST)
        try:
            page = max(1, int(query.get('page', ['1'])[0]))
            page_size = min(100, max(1, int(query.get('pageSize', ['50'])[0])))
        except ValueError:
            return self.write_json({'error': 'invalid pagination'}, status=HTTPStatus.BAD_REQUEST)
        offset = (page - 1) * page_size

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        today = now.date()
        today_key = today.isoformat()
        if traffic_view == '30d':
            series_unit = 'day'
            bucket_count = 30
            start_dt = datetime.combine(today - timedelta(days=bucket_count - 1), datetime.min.time())
        elif traffic_view == '7d':
            series_unit = 'day'
            bucket_count = 7
            start_dt = datetime.combine(today - timedelta(days=bucket_count - 1), datetime.min.time())
        elif traffic_view == '1d':
            series_unit = 'hour'
            bucket_count = 24
            start_dt = now - timedelta(hours=bucket_count - 1)
        else:
            series_unit = 'hour'
            bucket_count = 6
            start_dt = now - timedelta(hours=bucket_count - 1)
        start_key = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        with get_db() as conn:
            total_visits = conn.execute('SELECT COUNT(*) FROM visit_logs').fetchone()[0]
            today_visits = conn.execute(
                "SELECT COUNT(*) FROM visit_logs WHERE substr(created_at, 1, 10) = ?",
                (today_key,),
            ).fetchone()[0]
            unique_ips = conn.execute("SELECT COUNT(DISTINCT NULLIF(ip, '')) FROM visit_logs").fetchone()[0]
            today_unique_ips = conn.execute(
                "SELECT COUNT(DISTINCT NULLIF(ip, '')) FROM visit_logs WHERE substr(created_at, 1, 10) = ?",
                (today_key,),
            ).fetchone()[0]
            trend_rows = conn.execute(
                '''
                SELECT ip, created_at
                FROM visit_logs
                WHERE created_at >= ?
                ORDER BY created_at ASC
                ''',
                (start_key,),
            ).fetchall()
            top_rows = conn.execute(
                '''
                SELECT ip, COUNT(*) AS visits, MAX(created_at) AS last_visit_at
                FROM visit_logs
                WHERE ip != ''
                GROUP BY ip
                ORDER BY visits DESC, last_visit_at DESC
                LIMIT 10
                '''
            ).fetchall()
            recent_total = conn.execute('SELECT COUNT(*) FROM visit_logs').fetchone()[0]
            recent_rows = conn.execute(
                '''
                SELECT visit_logs.id, visit_logs.ip, visit_logs.page, visit_logs.path,
                       visit_logs.user_id, visit_logs.user_agent, visit_logs.referer,
                       visit_logs.created_at, users.name AS user_name, users.nickname AS user_nickname
                FROM visit_logs
                LEFT JOIN users ON users.id = visit_logs.user_id
                ORDER BY visit_logs.created_at DESC, visit_logs.id DESC
                LIMIT ? OFFSET ?
                ''',
                (page_size, offset),
            ).fetchall()

        trend_by_bucket = {}
        for row in trend_rows:
            try:
                created_at = datetime.strptime(row['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            except (TypeError, ValueError):
                continue
            if series_unit == 'day':
                bucket_key = created_at.date().isoformat()
            else:
                bucket_key = created_at.replace(minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:00:00Z')
            bucket = trend_by_bucket.setdefault(bucket_key, {'visits': 0, 'ips': set()})
            bucket['visits'] += 1
            if row['ip']:
                bucket['ips'].add(row['ip'])

        trend_series = []
        for offset in range(bucket_count):
            bucket_dt = start_dt + (timedelta(days=offset) if series_unit == 'day' else timedelta(hours=offset))
            if series_unit == 'day':
                bucket_key = bucket_dt.date().isoformat()
            else:
                bucket_key = bucket_dt.strftime('%Y-%m-%dT%H:00:00Z')
            item = trend_by_bucket.get(bucket_key, {'visits': 0, 'ips': set()})
            trend_series.append({
                'date': bucket_key,
                'visits': item['visits'],
                'uniqueIps': len(item['ips']),
            })

        return self.write_json({
            'trafficView': traffic_view,
            'seriesUnit': series_unit,
            'totalVisits': total_visits,
            'todayVisits': today_visits,
            'uniqueIps': unique_ips,
            'todayUniqueIps': today_unique_ips,
            'dailySeries': trend_series,
            'trendSeries': trend_series,
            'recentTotal': recent_total,
            'page': page,
            'pageSize': page_size,
            'topIps': [
                {'ip': row['ip'], 'visits': row['visits'], 'lastVisitAt': row['last_visit_at']}
                for row in top_rows
            ],
            'recentVisits': [
                {
                    'id': row['id'],
                    'ip': row['ip'],
                    'page': row['page'],
                    'path': row['path'],
                    'userId': row['user_id'],
                    'user': (
                        {'id': row['user_id'], 'name': row['user_name'], 'nickname': row['user_nickname']}
                        if row['user_id'] else None
                    ),
                    'userAgent': row['user_agent'],
                    'referer': row['referer'],
                    'createdAt': row['created_at'],
                }
                for row in recent_rows
            ],
        })

    def handle_admin_users(self):
        with get_db() as conn:
            rows = conn.execute(
                '''
                SELECT users.id, users.name, users.nickname, users.role, users.created_at,
                       COUNT(DISTINCT tasks.id) AS task_count,
                       COUNT(DISTINCT schedule_items.id) AS schedule_item_count,
                       MAX(operation_logs.created_at) AS last_operation_at,
                       MAX(CASE WHEN operation_logs.action = 'auth.login' THEN operation_logs.created_at END) AS last_login_at
                FROM users
                LEFT JOIN tasks ON tasks.user_id = users.id
                LEFT JOIN schedule_items ON schedule_items.user_id = users.id
                LEFT JOIN operation_logs ON operation_logs.target_user_id = users.id
                GROUP BY users.id
                ORDER BY users.created_at DESC, users.id DESC
                '''
            ).fetchall()
        return self.write_json({
            'users': [
                {
                    'id': row['id'],
                    'name': row['name'],
                    'nickname': row['nickname'],
                    'role': row['role'],
                    'createdAt': row['created_at'],
                    'taskCount': row['task_count'],
                    'scheduleItemCount': row['schedule_item_count'],
                    'lastOperationAt': row['last_operation_at'],
                    'lastLoginAt': row['last_login_at'],
                }
                for row in rows
            ]
        })

    def handle_admin_feedback(self):
        query = parse_qs(urlparse(self.path).query)
        try:
            page = max(1, int(query.get('page', ['1'])[0]))
            page_size = min(100, max(1, int(query.get('pageSize', ['50'])[0])))
        except ValueError:
            return self.write_json({'error': 'invalid pagination'}, status=HTTPStatus.BAD_REQUEST)
        offset = (page - 1) * page_size
        with get_db() as conn:
            feedback_limit = get_feedback_limit(conn)
            total = conn.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]
            rows = conn.execute(
                '''
                SELECT feedback.id, feedback.user_id, feedback.content, feedback.admin_reply,
                       feedback.replied_by, feedback.status, feedback.created_at, feedback.updated_at,
                       users.name AS user_name, users.nickname AS user_nickname
                FROM feedback
                JOIN users ON users.id = feedback.user_id
                ORDER BY feedback.created_at DESC, feedback.id DESC
                LIMIT ? OFFSET ?
                ''',
                (page_size, offset),
            ).fetchall()
        return self.write_json({
            'feedback': [public_feedback(row, include_user=True) for row in rows],
            'total': total,
            'page': page,
            'pageSize': page_size,
            'feedbackLimitPerUser': feedback_limit,
        })

    def handle_admin_feedback_settings(self):
        with get_db() as conn:
            feedback_limit = get_feedback_limit(conn)
        return self.write_json({'feedbackLimitPerUser': feedback_limit})

    def handle_admin_update_feedback_settings(self):
        admin = self.require_admin()
        if not admin:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        try:
            feedback_limit = int(payload.get('feedbackLimitPerUser'))
        except (TypeError, ValueError):
            return self.write_json({'error': 'invalid feedback limit', 'message': '未回复反馈上限必须是数字。'}, status=HTTPStatus.BAD_REQUEST)
        if feedback_limit < 1 or feedback_limit > 1000:
            return self.write_json({'error': 'feedback limit out of range', 'message': '未回复反馈上限必须在 1 到 1000 之间。'}, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            old_limit = get_feedback_limit(conn)
            set_feedback_limit(conn, feedback_limit)
            if old_limit != feedback_limit:
                self.log_operation(
                    conn,
                    int(admin['id']),
                    int(admin['id']),
                    'admin.feedback.limit_update',
                    'setting',
                    FEEDBACK_LIMIT_SETTING_KEY,
                    {'oldPendingLimit': old_limit, 'newPendingLimit': feedback_limit},
                )
            conn.commit()
        return self.write_json({'ok': True, 'feedbackLimitPerUser': feedback_limit})

    def handle_admin_reply_feedback(self, feedback_id_text: str):
        admin = self.require_admin()
        if not admin:
            return
        try:
            feedback_id = int(feedback_id_text)
        except ValueError:
            return self.write_json({'error': 'invalid feedback id'}, status=HTTPStatus.BAD_REQUEST)
        payload = self.read_json_body()
        if payload is None:
            return
        reply = str(payload.get('reply', '')).strip()
        if not reply:
            return self.write_json({'error': 'reply is required', 'message': '回复内容不能为空。'}, status=HTTPStatus.BAD_REQUEST)
        if len(reply) > 1000:
            return self.write_json({'error': 'reply is too long', 'message': '回复内容不能超过 1000 个字符。'}, status=HTTPStatus.BAD_REQUEST)
        now = now_iso()
        with get_db() as conn:
            row = conn.execute('SELECT id, user_id, content FROM feedback WHERE id = ?', (feedback_id,)).fetchone()
            if not row:
                return self.write_json({'error': 'feedback not found'}, status=HTTPStatus.NOT_FOUND)
            conn.execute(
                '''
                UPDATE feedback
                SET admin_reply = ?, replied_by = ?, status = 'replied', updated_at = ?
                WHERE id = ?
                ''',
                (reply, admin['id'], now, feedback_id),
            )
            self.log_operation(
                conn,
                int(admin['id']),
                int(row['user_id']),
                'admin.feedback.reply',
                'feedback',
                str(feedback_id),
                {'reply': reply},
            )
            conn.commit()
            updated = conn.execute(
                '''
                SELECT feedback.id, feedback.user_id, feedback.content, feedback.admin_reply,
                       feedback.replied_by, feedback.status, feedback.created_at, feedback.updated_at,
                       users.name AS user_name, users.nickname AS user_nickname
                FROM feedback
                JOIN users ON users.id = feedback.user_id
                WHERE feedback.id = ?
                ''',
                (feedback_id,),
            ).fetchone()
        return self.write_json({'ok': True, 'feedback': public_feedback(updated, include_user=True)})

    def handle_admin_delete_feedback(self, feedback_id_text: str):
        admin = self.require_admin()
        if not admin:
            return
        try:
            feedback_id = int(feedback_id_text)
        except ValueError:
            return self.write_json({'error': 'invalid feedback id'}, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            row = conn.execute(
                '''
                SELECT feedback.id, feedback.user_id, feedback.content, feedback.admin_reply,
                       users.name AS user_name, users.nickname AS user_nickname
                FROM feedback
                JOIN users ON users.id = feedback.user_id
                WHERE feedback.id = ?
                ''',
                (feedback_id,),
            ).fetchone()
            if not row:
                return self.write_json({'error': 'feedback not found'}, status=HTTPStatus.NOT_FOUND)
            conn.execute('DELETE FROM feedback WHERE id = ?', (feedback_id,))
            self.log_operation(
                conn,
                int(admin['id']),
                int(row['user_id']),
                'admin.feedback.delete',
                'feedback',
                str(feedback_id),
                {
                    'user': f"{row['user_name']}({row['user_nickname']})",
                    'content': row['content'],
                    'hadReply': bool(row['admin_reply']),
                },
            )
            conn.commit()
        return self.write_json({'ok': True, 'id': feedback_id})

    def handle_admin_update_user(self, user_id_text: str):
        admin = self.require_admin()
        if not admin:
            return
        try:
            user_id = int(user_id_text)
        except ValueError:
            return self.write_json({'error': 'invalid user id'}, status=HTTPStatus.BAD_REQUEST)
        payload = self.read_json_body()
        if payload is None:
            return
        name = str(payload.get('name', '')).strip()
        if not name:
            return self.write_json({'error': 'name is required', 'message': '姓名不能为空。'}, status=HTTPStatus.BAD_REQUEST)
        if len(name) > 80:
            return self.write_json({'error': 'name is too long', 'message': '姓名不能超过 80 个字符。'}, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            user = self.ensure_user_exists(conn, user_id)
            if not user:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            if user['name'] == name:
                return self.write_json({'ok': True, 'user': public_user(user)})
            conn.execute('UPDATE users SET name = ? WHERE id = ?', (name, user_id))
            self.log_operation(
                conn,
                int(admin['id']),
                user_id,
                'admin.user.update',
                'user',
                str(user_id),
                {'oldName': user['name'], 'newName': name, 'nickname': user['nickname']},
            )
            conn.commit()
            updated = self.ensure_user_exists(conn, user_id)
        return self.write_json({'ok': True, 'user': public_user(updated)})

    def handle_admin_delete_user(self, user_id_text: str):
        admin = self.require_admin()
        if not admin:
            return
        try:
            user_id = int(user_id_text)
        except ValueError:
            return self.write_json({'error': 'invalid user id'}, status=HTTPStatus.BAD_REQUEST)
        if user_id == int(admin['id']):
            return self.write_json(
                {'error': 'cannot delete current admin', 'message': '不能删除当前登录的管理员账号。'},
                status=HTTPStatus.BAD_REQUEST,
            )
        with get_db() as conn:
            user = self.ensure_user_exists(conn, user_id)
            if not user:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            task_count = conn.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (user_id,)).fetchone()[0]
            schedule_count = conn.execute('SELECT COUNT(*) FROM schedule_items WHERE user_id = ?', (user_id,)).fetchone()[0]
            log_count = conn.execute('SELECT COUNT(*) FROM operation_logs WHERE target_user_id = ?', (user_id,)).fetchone()[0]
            feedback_count = conn.execute('SELECT COUNT(*) FROM feedback WHERE user_id = ?', (user_id,)).fetchone()[0]

            conn.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM schedule_items WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM tasks WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM schedule_template_versions WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM schedule_day_overrides WHERE user_id = ?', (user_id,))
            conn.execute('UPDATE feedback SET replied_by = NULL WHERE replied_by = ?', (user_id,))
            conn.execute('DELETE FROM feedback WHERE user_id = ?', (user_id,))
            conn.execute('UPDATE operation_logs SET actor_user_id = NULL WHERE actor_user_id = ?', (user_id,))
            conn.execute('DELETE FROM operation_logs WHERE target_user_id = ?', (user_id,))
            cursor = conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            if cursor.rowcount != 1:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            self.log_operation(
                conn,
                int(admin['id']),
                int(admin['id']),
                'admin.user.delete',
                'user',
                str(user_id),
                {
                    'deletedUser': {
                        'id': user['id'],
                        'name': user['name'],
                        'nickname': user['nickname'],
                        'role': user['role'],
                    },
                    'deletedTaskCount': int(task_count),
                    'deletedScheduleItemCount': int(schedule_count),
                    'deletedFeedbackCount': int(feedback_count),
                    'deletedLogCount': int(log_count),
                },
            )
            conn.commit()
        return self.write_json({'ok': True, 'id': user_id})

    def handle_admin_user_tasks(self, user_id: int):
        with get_db() as conn:
            user = self.ensure_user_exists(conn, user_id)
            if not user:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            tasks = self.fetch_tasks_for_user(conn, user_id)
        return self.write_json({'tasks': tasks, 'readOnly': True, 'user': public_user(user)})

    def handle_admin_user_schedule_items(self, user_id: int):
        with get_db() as conn:
            user = self.ensure_user_exists(conn, user_id)
            if not user:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            items = self.fetch_schedule_items_for_user(conn, user_id)
        return self.write_json({'items': items, 'readOnly': True, 'user': public_user(user)})

    def handle_admin_user_schedule_config(self, user_id: int):
        with get_db() as conn:
            user = self.ensure_user_exists(conn, user_id)
            if not user:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            config = self.fetch_schedule_config_for_user(conn, user_id)
        return self.write_json({**config, 'readOnly': True, 'user': public_user(user)})

    def handle_admin_user_logs(self, user_id: int):
        query = parse_qs(urlparse(self.path).query)
        try:
            page = max(1, int(query.get('page', ['1'])[0]))
            page_size = min(100, max(1, int(query.get('pageSize', ['50'])[0])))
        except ValueError:
            return self.write_json({'error': 'invalid pagination'}, status=HTTPStatus.BAD_REQUEST)
        offset = (page - 1) * page_size
        with get_db() as conn:
            user = self.ensure_user_exists(conn, user_id)
            if not user:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            total = conn.execute(
                'SELECT COUNT(*) FROM operation_logs WHERE target_user_id = ?',
                (user_id,),
            ).fetchone()[0]
            rows = conn.execute(
                '''
                SELECT id, actor_user_id, target_user_id, action, entity_type, entity_id, detail_json, ip, created_at
                FROM operation_logs
                WHERE target_user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                ''',
                (user_id, page_size, offset),
            ).fetchall()
        return self.write_json({
            'logs': [public_operation_log(row) for row in rows],
            'total': total,
            'page': page,
            'pageSize': page_size,
            'user': public_user(user),
        })

    def handle_list_feedback(self):
        user = self.require_user()
        if not user:
            return
        with get_db() as conn:
            feedback_limit = get_feedback_limit(conn)
            rows = conn.execute(
                '''
                SELECT id, user_id, content, admin_reply, replied_by, status, created_at, updated_at
                FROM feedback
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                ''',
                (user['id'],),
            ).fetchall()
        return self.write_json({
            'feedback': [public_feedback(row) for row in rows],
            'feedbackLimitPerUser': feedback_limit,
        })

    def handle_create_feedback(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        content = str(payload.get('content', '')).strip()
        if not content:
            return self.write_json({'error': 'content is required', 'message': '反馈内容不能为空。'}, status=HTTPStatus.BAD_REQUEST)
        if len(content) > 1000:
            return self.write_json({'error': 'content is too long', 'message': '反馈内容不能超过 1000 个字符。'}, status=HTTPStatus.BAD_REQUEST)
        now = now_iso()
        with get_db() as conn:
            feedback_limit = get_feedback_limit(conn)
            feedback_count = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE user_id = ? AND status != 'replied'",
                (user['id'],),
            ).fetchone()[0]
            if int(feedback_count) >= feedback_limit:
                return self.write_json(
                    {
                        'error': 'feedback limit reached',
                        'message': f'每个用户未回复的反馈不能超过 {feedback_limit} 条，请等待管理员回复或删除旧反馈。',
                    },
                    status=HTTPStatus.CONFLICT,
                )
            cursor = conn.execute(
                '''
                INSERT INTO feedback (user_id, content, admin_reply, replied_by, status, created_at, updated_at)
                VALUES (?, ?, '', NULL, 'pending', ?, ?)
                ''',
                (user['id'], content, now, now),
            )
            feedback_id = cursor.lastrowid
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'feedback.create',
                'feedback',
                str(feedback_id),
                {'content': content},
            )
            conn.commit()
            row = conn.execute(
                '''
                SELECT id, user_id, content, admin_reply, replied_by, status, created_at, updated_at
                FROM feedback
                WHERE id = ?
                ''',
                (feedback_id,),
            ).fetchone()
        return self.write_json({'ok': True, 'feedback': public_feedback(row)}, status=HTTPStatus.CREATED)

    def handle_delete_feedback(self, feedback_id_text: str):
        user = self.require_user()
        if not user:
            return
        try:
            feedback_id = int(feedback_id_text)
        except ValueError:
            return self.write_json({'error': 'invalid feedback id'}, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            row = conn.execute(
                'SELECT id, user_id, content, admin_reply FROM feedback WHERE id = ? AND user_id = ?',
                (feedback_id, user['id']),
            ).fetchone()
            if not row:
                return self.write_json({'error': 'feedback not found'}, status=HTTPStatus.NOT_FOUND)
            conn.execute('DELETE FROM feedback WHERE id = ? AND user_id = ?', (feedback_id, user['id']))
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'feedback.delete',
                'feedback',
                str(feedback_id),
                {'content': row['content'], 'hadReply': bool(row['admin_reply'])},
            )
            conn.commit()
        return self.write_json({'ok': True, 'id': feedback_id})

    def handle_list_tasks(self):
        user = self.current_user()
        if not user:
            return self.write_json({'tasks': [], 'readOnly': True})

        with get_db() as conn:
            tasks = self.fetch_tasks_for_user(conn, int(user['id']))
        return self.write_json({'tasks': tasks, 'readOnly': False, 'user': public_user(user)})

    def handle_get_subject_template(self):
        user = self.require_user()
        if not user:
            return
        with get_db() as conn:
            row = conn.execute(
                'SELECT subjects_json FROM subject_templates WHERE user_id = ?',
                (user['id'],),
            ).fetchone()
        subjects = parse_subject_template(row['subjects_json'] if row else None)
        return self.write_json({
            'subjects': subjects,
            'defaultSubjects': DEFAULT_SUBJECTS,
            'readOnly': False,
        })

    def handle_update_subject_template(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        subjects, error = normalize_subject_template(payload.get('subjects'))
        if error:
            return self.write_json({'error': error}, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            conn.execute(
                '''
                INSERT INTO subject_templates (user_id, subjects_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    subjects_json = excluded.subjects_json,
                    updated_at = excluded.updated_at
                ''',
                (user['id'], json.dumps(subjects, ensure_ascii=False), now_iso()),
            )
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'subject_template.update',
                'subject_template',
                str(user['id']),
                {'count': len(subjects), 'enabledCount': sum(1 for item in subjects if item.get('enabled'))},
            )
            conn.commit()
        return self.write_json({'ok': True, 'subjects': subjects, 'defaultSubjects': DEFAULT_SUBJECTS})

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
        if task['pool'] not in {'todo', 'arrangement'}:
            return None, {'error': 'invalid task pool'}
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
                    INSERT INTO tasks (id, user_id, title, subject, due_at, pool, priority, note, completed, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        task['id'], task['userId'], task['title'], task['subject'], task['dueAt'], task['pool'],
                        task['priority'], task['note'], 1 if task['completed'] else 0,
                        task['createdAt'], task['updatedAt'],
                    ),
                )
                self.log_operation(
                    conn,
                    int(user['id']),
                    int(user['id']),
                    'task.create',
                    'task',
                    task['id'],
                    {'title': task['title'], 'pool': task['pool'], 'dueAt': task['dueAt']},
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return self.write_json({'error': 'task id already exists'}, status=HTTPStatus.CONFLICT)
            row = conn.execute(
                'SELECT id, user_id, title, subject, due_at, pool, priority, note, completed, created_at, updated_at FROM tasks WHERE id = ? AND user_id = ?',
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
            existing = conn.execute(
                'SELECT id, title, completed FROM tasks WHERE id = ? AND user_id = ?',
                (task_id, user['id']),
            ).fetchone()
            if not existing:
                return self.write_json({'error': 'task not found'}, status=HTTPStatus.NOT_FOUND)
            conn.execute(
                '''
                UPDATE tasks
                SET title = ?, subject = ?, due_at = ?, pool = ?, priority = ?, note = ?, completed = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                ''',
                (
                    task['title'], task['subject'], task['dueAt'], task['pool'], task['priority'], task['note'],
                    1 if task['completed'] else 0, task['updatedAt'], task_id, user['id'],
                ),
            )
            action = 'task.update'
            if bool(existing['completed']) != bool(task['completed']):
                action = 'task.complete' if task['completed'] else 'task.reopen'
            if (
                not bool(existing['completed'])
                and bool(task['completed'])
            ):
                conn.execute(
                    '''
                    UPDATE schedule_items
                    SET completed = 1, updated_at = ?
                    WHERE task_id = ? AND user_id = ? AND completed = 0
                    ''',
                    (task['updatedAt'], task_id, user['id']),
                )
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                action,
                'task',
                task_id,
                {'title': task['title'], 'previousTitle': existing['title']},
            )
            conn.commit()
            row = conn.execute(
                'SELECT id, user_id, title, subject, due_at, pool, priority, note, completed, created_at, updated_at FROM tasks WHERE id = ? AND user_id = ?',
                (task_id, user['id']),
            ).fetchone()
        return self.write_json({'ok': True, 'task': public_task(row)})

    def handle_delete_task(self, task_id: str):
        user = self.require_user()
        if not user:
            return
        with get_db() as conn:
            existing = conn.execute('SELECT title FROM tasks WHERE id = ? AND user_id = ?', (task_id, user['id'])).fetchone()
            if not existing:
                return self.write_json({'error': 'task not found'}, status=HTTPStatus.NOT_FOUND)
            conn.execute('DELETE FROM schedule_items WHERE task_id = ? AND user_id = ?', (task_id, user['id']))
            cursor = conn.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user['id']))
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'task.delete',
                'task',
                task_id,
                {'title': existing['title']},
            )
            conn.commit()
        return self.write_json({'ok': True})

    def handle_list_schedule_items(self):
        user = self.current_user()
        if not user:
            return self.write_json({'items': [], 'readOnly': True})

        with get_db() as conn:
            items = self.fetch_schedule_items_for_user(conn, int(user['id']))
        return self.write_json({'items': items, 'readOnly': False})

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
            config = self.fetch_schedule_config_for_user(conn, int(user['id']))
        return self.write_json(config)

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
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'schedule_config.template_update',
                'schedule_config',
                effective_from,
                {'effectiveFrom': effective_from},
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
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'schedule_config.day_update',
                'schedule_config',
                date_key,
                {'date': date_key},
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
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'schedule_config.day_reset',
                'schedule_config',
                date_key,
                {'date': date_key},
            )
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
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'schedule_config.reset',
                'schedule_config',
                None,
                {},
            )
            conn.commit()
        return self.write_json({'ok': True})

    def validate_schedule_payload(self, payload: dict, user_id: int, existing_id: str | None = None):
        """Validate schedule item edits and enforce per-slot capacity."""
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
        raw_sort_order = payload.get('sortOrder', None)
        if raw_sort_order in (None, ''):
            sort_order = None
        else:
            try:
                sort_order = float(raw_sort_order)
            except Exception:
                return None, {'error': 'sortOrder must be a number'}

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
            'sortOrder': sort_order,
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
            sort_order = item['sortOrder']
            if sort_order is None:
                sort_order = float(conn.execute(
                    """
                    SELECT COALESCE(MAX(sort_order), 0) + 1024 FROM schedule_items
                    WHERE user_id = ? AND schedule_date = ? AND slot_key = ?
                    """,
                    (user['id'], item['date'], item['slotKey']),
                ).fetchone()[0])
            conn.execute(
                """
                INSERT INTO schedule_items
                (id, user_id, task_id, schedule_date, slot_key, slot_label, slot_start, slot_end,
                 duration_minutes, sort_order, note, completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id, user['id'], item['taskId'], item['date'], item['slotKey'], item['slotLabel'],
                    item['slotStart'], item['slotEnd'], item['durationMinutes'], sort_order, item['note'],
                    0, now_iso(), now_iso(),
                ),
            )
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'schedule_item.create',
                'schedule_item',
                item_id,
                {'taskId': item['taskId'], 'date': item['date'], 'slotLabel': item['slotLabel']},
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
            'date': payload.get('date', existing['schedule_date']),
            'slotKey': payload.get('slotKey', existing['slot_key']),
            'slotLabel': payload.get('slotLabel', existing['slot_label']),
            'slotStart': payload.get('slotStart', existing['slot_start']),
            'slotEnd': payload.get('slotEnd', existing['slot_end']),
            'durationMinutes': payload.get('durationMinutes', existing['duration_minutes']),
            'sortOrder': payload.get('sortOrder', existing['sort_order']),
            'note': payload.get('note', existing['note']),
        }
        item, error = self.validate_schedule_payload(merged, int(user['id']), existing_id=item_id)
        if error:
            return self.write_json(error, status=HTTPStatus.BAD_REQUEST)
        if item['sortOrder'] is None:
            item['sortOrder'] = existing['sort_order']
        completed = bool(payload.get('completed')) if 'completed' in payload else bool(existing['completed'])
        with get_db() as conn:
            conn.execute(
                """
                UPDATE schedule_items
                SET schedule_date = ?, slot_key = ?, slot_label = ?, slot_start = ?, slot_end = ?,
                    duration_minutes = ?, sort_order = ?, note = ?, completed = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    item['date'], item['slotKey'], item['slotLabel'], item['slotStart'], item['slotEnd'],
                    item['durationMinutes'], item['sortOrder'], item['note'], 1 if completed else 0,
                    now_iso(), item_id, user['id'],
                ),
            )
            action = 'schedule_item.update'
            if bool(existing['completed']) != completed:
                action = 'schedule_item.complete' if completed else 'schedule_item.reopen'
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                action,
                'schedule_item',
                item_id,
                {'taskId': item['taskId'], 'date': item['date'], 'slotLabel': item['slotLabel']},
            )
            conn.commit()
        return self.write_json({'ok': True, 'id': item_id})

    def handle_delete_schedule_item(self, item_id: str):
        user = self.require_user()
        if not user:
            return
        with get_db() as conn:
            existing = conn.execute(
                'SELECT task_id, schedule_date, slot_label FROM schedule_items WHERE id = ? AND user_id = ?',
                (item_id, user['id']),
            ).fetchone()
            if not existing:
                return self.write_json({'error': 'schedule item not found'}, status=HTTPStatus.NOT_FOUND)
            cursor = conn.execute('DELETE FROM schedule_items WHERE id = ? AND user_id = ?', (item_id, user['id']))
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'schedule_item.delete',
                'schedule_item',
                item_id,
                {'taskId': existing['task_id'], 'date': existing['schedule_date'], 'slotLabel': existing['slot_label']},
            )
            conn.commit()
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
                user_id = cursor.lastrowid
                self.log_operation(
                    conn,
                    user_id,
                    user_id,
                    'auth.register',
                    'user',
                    str(user_id),
                    {'nickname': nickname},
                )
                conn.commit()
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
            if user and verify_password(password, user['password_hash']):
                self.log_operation(
                    conn,
                    int(user['id']),
                    int(user['id']),
                    'auth.login',
                    'user',
                    str(user['id']),
                    {'nickname': user['nickname']},
                )
                conn.commit()
            else:
                user = None
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

    def handle_auth_update_nickname(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        nickname = str(payload.get('nickname', '')).strip()
        if not nickname:
            return self.write_json({'error': 'nickname is required', 'message': '昵称不能为空。'}, status=HTTPStatus.BAD_REQUEST)
        if len(nickname) > 32:
            return self.write_json({'error': 'nickname is too long', 'message': '昵称不能超过 32 个字符。'}, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            existing = conn.execute(
                'SELECT id FROM users WHERE lower(nickname) = lower(?) AND id != ?',
                (nickname, user['id']),
            ).fetchone()
            if existing:
                return self.write_json({'error': 'nickname already exists', 'message': '这个昵称已被使用。'}, status=HTTPStatus.CONFLICT)
            current = conn.execute('SELECT id, name, nickname, role FROM users WHERE id = ?', (user['id'],)).fetchone()
            if not current:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            if current['nickname'] == nickname:
                return self.write_json({'ok': True, 'user': public_user(current)})
            try:
                conn.execute('UPDATE users SET nickname = ? WHERE id = ?', (nickname, user['id']))
            except sqlite3.IntegrityError:
                return self.write_json({'error': 'nickname already exists', 'message': '这个昵称已被使用。'}, status=HTTPStatus.CONFLICT)
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'user.nickname.update',
                'user',
                str(user['id']),
                {'oldNickname': current['nickname'], 'newNickname': nickname},
            )
            conn.commit()
            updated = conn.execute('SELECT id, name, nickname, role FROM users WHERE id = ?', (user['id'],)).fetchone()
        return self.write_json({'ok': True, 'user': public_user(updated)})

    def handle_auth_update_password(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        current_password = str(payload.get('currentPassword', ''))
        new_password = str(payload.get('newPassword', ''))
        if not current_password or not new_password:
            return self.write_json({'error': 'passwords are required', 'message': '请填写原密码和新密码。'}, status=HTTPStatus.BAD_REQUEST)
        if len(new_password) < 6:
            return self.write_json({'error': 'password must be at least 6 characters', 'message': '新密码至少需要 6 位。'}, status=HTTPStatus.BAD_REQUEST)

        with get_db() as conn:
            current = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
            if not current:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            if not verify_password(current_password, current['password_hash']):
                return self.write_json({'error': 'current password is incorrect', 'message': '原密码不正确。'}, status=HTTPStatus.UNAUTHORIZED)
            conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hash_password(new_password), user['id']))
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'user.password.update',
                'user',
                str(user['id']),
                {'nickname': current['nickname']},
            )
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
        """Decode a JSON request body and write a 400 response on parse errors."""
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
