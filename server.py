#!/usr/bin/env python3
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import ipaddress
import json
import math
import os
import posixpath
import secrets
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / 'web'
AI_PROMPTS_PATH = BASE_DIR / 'ai_prompts.json'
AI_PROMPT_KEYS = (
    'AI_CHAT_SYSTEM_PROMPT',
    'AI_STREAM_SYSTEM_PROMPT',
    'AI_REPAIR_SYSTEM_PROMPT',
)


def load_ai_prompts(path: Path | None = None) -> dict[str, str]:
    prompts_path = path or AI_PROMPTS_PATH
    with prompts_path.open(encoding='utf-8') as file:
        prompts = json.load(file)

    missing_or_invalid = [
        key for key in AI_PROMPT_KEYS
        if not isinstance(prompts.get(key), str) or not prompts[key].strip()
    ]
    if missing_or_invalid:
        names = ', '.join(missing_or_invalid)
        raise RuntimeError(f'Missing AI prompt(s) in {prompts_path.name}: {names}')

    return {key: prompts[key].strip() for key in AI_PROMPT_KEYS}


_AI_PROMPTS = load_ai_prompts()

AI_CHAT_SYSTEM_PROMPT = _AI_PROMPTS['AI_CHAT_SYSTEM_PROMPT']
AI_STREAM_SYSTEM_PROMPT = _AI_PROMPTS['AI_STREAM_SYSTEM_PROMPT']
AI_REPAIR_SYSTEM_PROMPT = _AI_PROMPTS['AI_REPAIR_SYSTEM_PROMPT']


def load_dotenv(path: Path | None = None, *, override: bool = False) -> None:
    dotenv_path = path or (BASE_DIR / '.env')
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip().lstrip('\ufeff')
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export '):].strip()
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value


load_dotenv()

DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'todo-list.db'
HOST = os.environ.get('TODO_HOST', '127.0.0.1')
PORT = int(os.environ.get('TODO_PORT', '8092'))
PASSWORD_ITERATIONS = 260_000
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_FEEDBACK_LIMIT_PER_USER = 10
FEEDBACK_LIMIT_SETTING_KEY = 'feedback_limit_per_user'
AI_TOKEN_LIMIT_SETTING_KEY = 'ai_token_limit_global'
INSTALLER_DOWNLOAD_LIMIT_SETTING_KEY = 'managebac_installer_download_limit_global'
DEFAULT_AI_TOKEN_WINDOW_HOURS = 24
DEFAULT_AI_INPUT_TOKEN_LIMIT = 200_000
DEFAULT_AI_OUTPUT_TOKEN_LIMIT = 50_000
DEFAULT_INSTALLER_DOWNLOAD_WINDOW_HOURS = 24
DEFAULT_INSTALLER_DOWNLOAD_LINK_LIMIT = 5
TRUSTED_PROXY_IPS = {'127.0.0.1', '::1'}
DEEPSEEK_API_URL = 'https://api.deepseek.com/chat/completions'
DEFAULT_DEEPSEEK_MODEL = 'deepseek-v4-flash'
DEFAULT_DEEPSEEK_TIMEOUT_SECONDS = 20
AI_ACTION_LIMIT = 10
AI_HISTORY_LIMIT = 20
AI_CONTEXT_TASK_LIMIT = 200
AI_TASK_FIELDS = {'title', 'subject', 'dueAt', 'priority', 'note'}
MAX_JSON_BODY_BYTES = 5 * 1024 * 1024
MAX_TASK_ID_LENGTH = 128
MAX_TASK_TITLE_LENGTH = 120
MAX_TASK_SUBJECT_LENGTH = 40
MAX_TASK_DUE_AT_LENGTH = 32
MAX_TASK_NOTE_LENGTH = 4000
HABIT_SYNC_FUTURE_DAYS = 90
MAX_HABIT_SYNC_FUTURE_DAYS = 365
MAX_AVATAR_BYTES = 2 * 1024 * 1024
AVATAR_CONTENT_TYPES = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/webp': 'webp',
}
AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
DEFAULT_AVATAR_COLOR = '#6366f1'
STATIC_FILE_PATHS = {'/index.html', '/app.js', '/style.css'}
STATIC_DIRECTORY_PREFIXES = ('/vendor/', '/assets/')
MANAGEBAC_HELPER_DIR = BASE_DIR / 'managebac-sync-helper'
DEFAULT_OSS_SIGN_EXPIRES_SECONDS = 10 * 60
MAX_OSS_SIGN_EXPIRES_SECONDS = 7 * 24 * 60 * 60
MANAGEBAC_OSS_INSTALLER_ENV_NAMES = [
    'ALIYUN_OSS_ACCESS_KEY_ID',
    'ALIYUN_OSS_ACCESS_KEY_SECRET',
    'ALIYUN_OSS_REGION',
    'ALIYUN_OSS_BUCKET',
    'ALIYUN_OSS_INSTALLER_KEY',
    'ALIYUN_OSS_ENDPOINT',
    'ALIYUN_OSS_INSTALLER_FILENAME',
    'ALIYUN_OSS_SIGN_EXPIRES_SECONDS',
]
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
AI_SUBJECT_ALIASES = {
    'Chinese': ['chinese', '中文', '语文', '汉语'],
    'Mathematics': ['mathematics', 'math', 'maths', '数学'],
    'English B': ['english b', 'english', '英语'],
    'IELTS': ['ielts', '雅思'],
    'Physics': ['physics', '物理'],
    'Economics': ['economics', 'econ', '经济', '经济学'],
    'Chemistry': ['chemistry', '化学'],
    'Psychology': ['psychology', '心理', '心理学'],
    'Biology': ['biology', '生物'],
    'Computer Science': ['computer science', 'computer', 'cs', '计算机', '计算机科学', '电脑'],
}


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


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def avatar_dir() -> Path:
    return DATA_DIR / 'uploads' / 'avatars'


def init_db() -> None:
    """Create the SQLite schema and apply small in-place migrations."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    avatar_dir().mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH, factory=ClosingConnection) as conn:
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA busy_timeout = 5000')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                nickname TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                avatar_file TEXT NOT NULL DEFAULT '',
                avatar_updated_at TEXT NOT NULL DEFAULT '',
                avatar_color TEXT NOT NULL DEFAULT '#6366f1',
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
                habit_id TEXT NOT NULL DEFAULT '',
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
        if 'habit_id' not in columns:
            conn.execute("ALTER TABLE schedule_items ADD COLUMN habit_id TEXT NOT NULL DEFAULT ''")
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS habits (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                weekdays_json TEXT NOT NULL,
                slot_key_base TEXT NOT NULL,
                slot_label TEXT NOT NULL,
                slot_start TEXT NOT NULL,
                slot_end TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
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
            CREATE TABLE IF NOT EXISTS ai_usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                model TEXT NOT NULL,
                call_type TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                prompt_cache_hit_tokens INTEGER NOT NULL DEFAULT 0,
                prompt_cache_miss_tokens INTEGER NOT NULL DEFAULT 0,
                reasoning_tokens INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_user_created ON ai_usage_logs(user_id, created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_created_at ON ai_usage_logs(created_at)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS ai_token_limits (
                user_id INTEGER PRIMARY KEY,
                window_hours INTEGER NOT NULL,
                input_token_limit INTEGER NOT NULL,
                output_token_limit INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS installer_download_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                object_key TEXT NOT NULL DEFAULT '',
                filename TEXT NOT NULL DEFAULT '',
                ip TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_installer_download_logs_user_created ON installer_download_logs(user_id, created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_installer_download_logs_created_at ON installer_download_logs(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_installer_download_logs_ip ON installer_download_logs(ip)')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS installer_download_limits (
                user_id INTEGER PRIMARY KEY,
                window_hours INTEGER NOT NULL,
                link_limit INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute(
            '''
            INSERT OR IGNORE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ''',
            (FEEDBACK_LIMIT_SETTING_KEY, str(DEFAULT_FEEDBACK_LIMIT_PER_USER), now_iso()),
        )
        conn.execute(
            '''
            INSERT OR IGNORE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ''',
            (
                AI_TOKEN_LIMIT_SETTING_KEY,
                json.dumps({
                    'windowHours': DEFAULT_AI_TOKEN_WINDOW_HOURS,
                    'inputTokenLimit': DEFAULT_AI_INPUT_TOKEN_LIMIT,
                    'outputTokenLimit': DEFAULT_AI_OUTPUT_TOKEN_LIMIT,
                }, ensure_ascii=False),
                now_iso(),
            ),
        )
        conn.execute(
            '''
            INSERT OR IGNORE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ''',
            (
                INSTALLER_DOWNLOAD_LIMIT_SETTING_KEY,
                json.dumps({
                    'windowHours': DEFAULT_INSTALLER_DOWNLOAD_WINDOW_HOURS,
                    'linkLimit': DEFAULT_INSTALLER_DOWNLOAD_LINK_LIMIT,
                }, ensure_ascii=False),
                now_iso(),
            ),
        )
        nickname_duplicates = conn.execute(
            '''
            SELECT lower(nickname) AS nickname_key, COUNT(*) AS duplicate_count
            FROM users
            GROUP BY lower(nickname)
            HAVING COUNT(*) > 1
            '''
        ).fetchall()
        if nickname_duplicates:
            duplicate_keys = ', '.join(str(row[0]) for row in nickname_duplicates[:5])
            raise RuntimeError(
                'Cannot create case-insensitive nickname index; duplicate nicknames exist: '
                f'{duplicate_keys}'
            )
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_users_nickname_nocase ON users(nickname COLLATE NOCASE)'
        )

        user_columns = {row[1] for row in conn.execute('PRAGMA table_info(users)').fetchall()}
        if 'avatar_file' not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN avatar_file TEXT NOT NULL DEFAULT ''")
        if 'avatar_updated_at' not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN avatar_updated_at TEXT NOT NULL DEFAULT ''")
        if 'avatar_color' not in user_columns:
            conn.execute(f"ALTER TABLE users ADD COLUMN avatar_color TEXT NOT NULL DEFAULT '{DEFAULT_AVATAR_COLOR}'")
        task_columns = {row[1] for row in conn.execute('PRAGMA table_info(tasks)').fetchall()}
        if 'subject' not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN subject TEXT NOT NULL DEFAULT ''")
        if 'user_id' not in task_columns:
            conn.execute('ALTER TABLE tasks ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1')
        if 'pool' not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN pool TEXT NOT NULL DEFAULT 'todo'")
        conn.execute('UPDATE tasks SET user_id = 1 WHERE user_id IS NULL OR user_id = 0')
        conn.execute("UPDATE tasks SET pool = 'todo' WHERE pool IS NULL OR pool = ''")
        conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user_due_priority ON tasks(user_id, due_at, priority)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user_pool_due ON tasks(user_id, pool, due_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user_pool_completed_due ON tasks(user_id, pool, completed, due_at)')
        conn.execute(
            '''
            CREATE INDEX IF NOT EXISTS idx_tasks_user_ai_context_order
            ON tasks(
                user_id,
                pool,
                completed,
                due_at,
                CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                title COLLATE NOCASE
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_schedule_items_user_date_slot ON schedule_items(user_id, schedule_date, slot_key)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_schedule_items_user_task ON schedule_items(user_id, task_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_schedule_items_user_habit_date ON schedule_items(user_id, habit_id, schedule_date)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_habits_user_active_archived ON habits(user_id, active, archived)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_operation_logs_target_created ON operation_logs(target_user_id, created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_feedback_user_created ON feedback(user_id, created_at)')
        conn.commit()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 5000')
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


def deepseek_api_key() -> str:
    return os.environ.get('DEEPSEEK_API_KEY', '').strip()


def deepseek_model() -> str:
    return os.environ.get('DEEPSEEK_MODEL', DEFAULT_DEEPSEEK_MODEL).strip() or DEFAULT_DEEPSEEK_MODEL


def deepseek_timeout_seconds() -> float:
    try:
        return max(1.0, float(os.environ.get('DEEPSEEK_TIMEOUT_SECONDS', str(DEFAULT_DEEPSEEK_TIMEOUT_SECONDS))))
    except (TypeError, ValueError):
        return float(DEFAULT_DEEPSEEK_TIMEOUT_SECONDS)


def compact_task_for_ai(task: dict) -> dict:
    return {
        'id': task.get('id', ''),
        'title': task.get('title', ''),
        'subject': task.get('subject', ''),
        'dueAt': task.get('dueAt', ''),
        'priority': task.get('priority', 'medium'),
        'note': task.get('note', ''),
        'completed': bool(task.get('completed', False)),
        'pool': task.get('pool', 'todo'),
    }


def ai_task_context_payload(included_tasks: list[dict], total_timeline_task_count: int) -> dict:
    omitted_count = max(0, int(total_timeline_task_count) - len(included_tasks))
    return {
        'taskSelection': {
            'status': 'incomplete_timeline_only',
            'pool': 'todo',
            'totalIncompleteTimelineTaskCount': int(total_timeline_task_count),
            'includedTaskCount': len(included_tasks),
            'omittedIncompleteTimelineTaskCount': omitted_count,
            'truncated': omitted_count > 0,
            'limit': AI_CONTEXT_TASK_LIMIT,
            'policy': 'Only included incomplete timeline tasks with pool=todo may be used as update targets. Daily schedule items, habits, arrangement-pool tasks, and completed tasks are not visible. If truncated and the target is not visible, ask the user to narrow the request.',
        },
        'taskPlacement': {
            'ddlTimeline': 'pool=todo 且 dueAt 非空的任务显示在 DDL 时间线/日历。',
            'unscheduledDdl': 'pool=todo 且 dueAt 为空字符串的任务显示在“待安排DDL”。如果用户要求没有截止日期、先待安排或放入待安排DDL，create_task 应把 dueAt 设为空字符串。',
            'dailyArrangementPool': 'pool=arrangement 是每日安排页的“临时任务池”，当前 AI 不可创建或修改。',
            'createTaskPoolPolicy': 'create_task 不接收 pool 字段；后端/前端会按普通 DDL 任务写入 pool=todo。',
        },
        'tasks': [compact_task_for_ai(task) for task in included_tasks],
    }


def ai_context_tasks(tasks: list[dict]) -> tuple[list[dict], dict]:
    timeline_tasks = [
        task for task in tasks
        if not bool(task.get('completed')) and task.get('pool', 'todo') == 'todo'
    ]
    included_tasks = timeline_tasks[:AI_CONTEXT_TASK_LIMIT]
    return included_tasks, ai_task_context_payload(included_tasks, len(timeline_tasks))


def is_valid_ai_due_at(value: str) -> bool:
    if value == '':
        return True
    if not value.endswith(':00'):
        return False
    try:
        datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        return True
    except ValueError:
        return False


def is_valid_task_due_at(value: str) -> bool:
    value = str(value or '').strip()
    if value == '':
        return True
    if len(value) > MAX_TASK_DUE_AT_LENGTH:
        return False
    try:
        datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        return True
    except ValueError:
        return False


def normalize_ai_task_fields(raw: object, *, partial: bool, subject_names: list[str] | None = None) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, 'task fields must be an object'
    unsupported = sorted(set(raw) - AI_TASK_FIELDS)
    if unsupported:
        return None, f'unsupported task fields: {", ".join(unsupported)}'

    fields: dict = {}
    if not partial or 'title' in raw:
        title = str(raw.get('title', '') or '').strip()
        if not title:
            return None, 'task title is required'
        if len(title) > 80:
            return None, 'task title is too long'
        fields['title'] = title

    if not partial or 'subject' in raw:
        subject = str(raw.get('subject', '') or '').strip()
        if not subject:
            return None, 'task subject is required'
        if len(subject) > 40:
            return None, 'task subject is too long'
        fields['subject'] = match_existing_subject(subject, subject_names or [])

    if not partial or 'dueAt' in raw:
        due_at = str(raw.get('dueAt', '') or '').strip()
        if not is_valid_ai_due_at(due_at):
            return None, 'task dueAt must be empty or YYYY-MM-DDTHH:mm:00'
        fields['dueAt'] = due_at

    if not partial or 'priority' in raw:
        priority = str(raw.get('priority', '') or '').strip()
        if not priority:
            return None, 'task priority is required'
        if priority not in {'high', 'medium', 'low'}:
            return None, 'invalid task priority'
        fields['priority'] = priority

    if not partial or 'note' in raw:
        note = str(raw.get('note', '') or '').strip()
        if len(note) > 4000:
            return None, 'task note is too long'
        fields['note'] = note

    if partial and not fields:
        return None, 'update patch is empty'
    return fields, None


def ai_priority_label(priority: str) -> str:
    return {'high': '高', 'medium': '中', 'low': '低'}.get(priority, priority or '中')


def ai_due_label(value: str) -> str:
    return value.replace('T', ' ')[:16] if value else '待安排DDL'


def ai_task_summary(task: dict) -> str:
    return f"{task.get('title', '')} / {task.get('subject', '')} / {ai_due_label(task.get('dueAt', ''))} / {ai_priority_label(task.get('priority', 'medium'))}"


def normalize_ai_actions(raw_actions: object, tasks: list[dict], subject_names: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    if raw_actions is None:
        return [], []
    if not isinstance(raw_actions, list):
        return [], [{'index': 0, 'reason': 'actions must be a list'}]

    tasks_by_id = {str(task.get('id', '')): task for task in tasks}
    actions: list[dict] = []
    rejected: list[dict] = []
    for index, raw_action in enumerate(raw_actions[:AI_ACTION_LIMIT]):
        if not isinstance(raw_action, dict):
            rejected.append({'index': index, 'reason': 'action must be an object'})
            continue
        action_type = str(raw_action.get('type', '') or '').strip()
        if action_type == 'create_task':
            fields, error = normalize_ai_task_fields(raw_action.get('task'), partial=False, subject_names=subject_names)
            if error:
                rejected.append({'index': index, 'reason': error})
                continue
            action = {
                'id': f'ai-action-{index + 1}',
                'type': 'create_task',
                'summary': f"创建任务：{ai_task_summary(fields)}",
                'task': fields,
            }
            actions.append(action)
            continue

        if action_type == 'update_task':
            target_task_id = str(raw_action.get('targetTaskId', '') or '').strip()
            existing = tasks_by_id.get(target_task_id)
            if not existing:
                rejected.append({'index': index, 'reason': 'target task not found'})
                continue
            if existing.get('pool') in {'habit', 'schedule'}:
                rejected.append({'index': index, 'reason': 'habit or schedule tasks cannot be updated by AI'})
                continue
            patch, error = normalize_ai_task_fields(raw_action.get('patch'), partial=True, subject_names=subject_names)
            if error:
                rejected.append({'index': index, 'reason': error})
                continue
            before = {key: existing.get(key, '') for key in AI_TASK_FIELDS}
            changed_patch = {key: value for key, value in patch.items() if before.get(key, '') != value}
            if not changed_patch:
                rejected.append({'index': index, 'reason': 'update has no actual changes'})
                continue
            after = {**before, **changed_patch}
            action = {
                'id': f'ai-action-{index + 1}',
                'type': 'update_task',
                'summary': f"修改任务：{existing.get('title', '')}",
                'targetTaskId': target_task_id,
                'targetTaskTitle': existing.get('title', ''),
                'patch': changed_patch,
                'before': before,
                'after': after,
            }
            actions.append(action)
            continue

        rejected.append({'index': index, 'reason': 'unsupported action type'})

    if isinstance(raw_actions, list) and len(raw_actions) > AI_ACTION_LIMIT:
        rejected.append({'index': AI_ACTION_LIMIT, 'reason': f'only first {AI_ACTION_LIMIT} actions are accepted'})
    return actions, rejected


def parse_ai_json_content(content: str) -> tuple[dict | None, str | None]:
    try:
        payload = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return None, 'AI returned invalid JSON'
    if not isinstance(payload, dict):
        return None, 'AI JSON response must be an object'
    return payload, None


def parse_ai_stream_content(content: str) -> tuple[str, object, str | None]:
    start_tag = '<AI_ACTIONS_JSON>'
    end_tag = '</AI_ACTIONS_JSON>'
    start = content.find(start_tag)
    end = content.find(end_tag, start + len(start_tag)) if start != -1 else -1
    if start == -1 or end == -1:
        payload, error = parse_ai_json_content(content)
        if error:
            return content.strip(), [], 'AI stream response missing actions JSON'
        return str(payload.get('reply', '') or '').strip(), payload.get('actions'), None
    reply = content[:start].strip()
    raw_json = content[start + len(start_tag):end].strip()
    try:
        payload = json.loads(raw_json)
    except (TypeError, json.JSONDecodeError):
        return reply, [], 'AI actions JSON is invalid'
    if not isinstance(payload, dict):
        return reply, [], 'AI actions JSON must be an object'
    return reply, payload.get('actions'), None


def public_user(row: sqlite3.Row | dict) -> dict:
    avatar_file = row_value(row, 'avatar_file', '')
    avatar_updated_at = row_value(row, 'avatar_updated_at', '')
    avatar_color = normalize_avatar_color(row_value(row, 'avatar_color', DEFAULT_AVATAR_COLOR))
    return {
        'id': row['id'],
        'name': row['name'],
        'nickname': row['nickname'],
        'role': row['role'],
        'avatarUrl': avatar_url(avatar_file, avatar_updated_at),
        'avatarColor': avatar_color,
    }


def row_value(row: sqlite3.Row | dict, key: str, default=''):
    if isinstance(row, sqlite3.Row):
        return row[key] if key in row.keys() else default
    return row.get(key, default)


def avatar_url(avatar_file: str, avatar_updated_at: str = '') -> str:
    avatar_file = str(avatar_file or '').strip()
    if not is_safe_avatar_filename(avatar_file):
        return ''
    version = str(avatar_updated_at or '').strip()
    suffix = f'?v={version}' if version else ''
    return f'/uploads/avatars/{avatar_file}{suffix}'


def normalize_avatar_color(value: str) -> str:
    color = str(value or '').strip().lower()
    return color if is_valid_avatar_color(color) else DEFAULT_AVATAR_COLOR


def is_valid_avatar_color(value: str) -> bool:
    color = str(value or '').strip().lower()
    if len(color) != 7 or not color.startswith('#'):
        return False
    return all(char in '0123456789abcdef' for char in color[1:])


def is_safe_avatar_filename(filename: str) -> bool:
    filename = str(filename or '')
    if not filename or '/' in filename or '\\' in filename or '\x00' in filename:
        return False
    if filename in {'.', '..'} or Path(filename).name != filename:
        return False
    stem, dot, ext = filename.rpartition('.')
    if not stem or dot != '.' or ext.lower() not in AVATAR_EXTENSIONS:
        return False
    allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.')
    return all(char in allowed for char in filename)


def avatar_magic_type(raw: bytes) -> str:
    if raw.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if raw.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if len(raw) >= 12 and raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
        return 'image/webp'
    return ''


def avatar_content_type(filename: str) -> str:
    ext = filename.rpartition('.')[2].lower()
    if ext == 'png':
        return 'image/png'
    if ext in {'jpg', 'jpeg'}:
        return 'image/jpeg'
    if ext == 'webp':
        return 'image/webp'
    return 'application/octet-stream'


def cleanup_avatar_file(filename: str) -> None:
    if not is_safe_avatar_filename(filename):
        return
    path = avatar_dir() / filename
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


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


def subject_match_key(value: str) -> str:
    return ''.join(ch for ch in str(value or '').casefold() if ch.isalnum())


def enabled_subject_names(subjects: list[dict]) -> list[str]:
    names: list[str] = []
    seen = set()
    for item in subjects:
        if not isinstance(item, dict) or not item.get('enabled', True):
            continue
        name = str(item.get('name', '')).strip()
        key = subject_match_key(name)
        if name and key not in seen:
            names.append(name)
            seen.add(key)
    return names


def get_subject_template_for_user(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    row = conn.execute(
        'SELECT subjects_json FROM subject_templates WHERE user_id = ?',
        (user_id,),
    ).fetchone()
    return parse_subject_template(row['subjects_json'] if row else None)


def ai_subject_context(subject_names: list[str]) -> dict:
    return {
        'subjectTemplate': {
            'availableSubjects': list(subject_names),
            'matchingPolicy': '用户明确提供科目后，先匹配 availableSubjects；匹配成功时使用已有科目的原始名称；没有匹配时保留用户原话；不要从任务内容自行推断科目。',
        },
    }


def match_existing_subject(subject: str, subject_names: list[str]) -> str:
    subject = str(subject or '').strip()
    key = subject_match_key(subject)
    if not key:
        return subject
    for name in subject_names:
        if subject_match_key(name) == key:
            return name
    for canonical, aliases in AI_SUBJECT_ALIASES.items():
        if key not in {subject_match_key(alias) for alias in aliases}:
            continue
        for name in subject_names:
            if subject_match_key(name) == subject_match_key(canonical):
                return name
    return subject


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


def is_valid_date_key(value: str) -> bool:
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True
    except Exception:
        return False


def add_days_key(date_key: str, days: int) -> str:
    base = datetime.strptime(date_key, '%Y-%m-%d')
    return (base + timedelta(days=days)).strftime('%Y-%m-%d')


def clamp_habit_sync_window(start: str | None, end: str | None) -> tuple[str, str]:
    today = today_key()
    default_end = add_days_key(today, HABIT_SYNC_FUTURE_DAYS)
    max_end = add_days_key(today, MAX_HABIT_SYNC_FUTURE_DAYS)
    start_key = str(start or '').strip()
    end_key = str(end or '').strip()
    if not is_valid_date_key(start_key):
        start_key = today
    if not is_valid_date_key(end_key):
        end_key = default_end
    start_key = max(today, min(start_key, max_end))
    end_key = min(max(end_key, start_key), max_end)
    return start_key, end_key


def today_key() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


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
        try:
            parsed = json.loads(override['slots_json'])
        except json.JSONDecodeError:
            parsed = []
        return parsed if isinstance(parsed, list) else []
    week_slots = week_slots_for_date(conn, user_id, date_key)
    weekday = weekday_for_date(date_key)
    return week_slots.get(weekday, [])


def matching_effective_slot(
    conn: sqlite3.Connection,
    user_id: int,
    date_key: str,
    slot_key_text: str,
    slot_start: str,
    slot_end: str,
) -> dict | None:
    for slot in effective_slots_for_date(conn, user_id, date_key):
        if (
            slot_key(date_key, slot) == slot_key_text
            and slot.get('start') == slot_start
            and slot.get('end') == slot_end
        ):
            return slot
    return None


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
        'habitId': row['habit_id'],
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


def public_habit(row: sqlite3.Row) -> dict:
    try:
        weekdays = json.loads(row['weekdays_json'] or '[]')
    except json.JSONDecodeError:
        weekdays = []
    return {
        'id': row['id'],
        'userId': row['user_id'],
        'taskId': row['task_id'],
        'title': row['task_title'],
        'subject': row['task_subject'],
        'priority': row['task_priority'],
        'note': row['task_note'],
        'weekdays': weekdays if isinstance(weekdays, list) else [],
        'slotKeyBase': row['slot_key_base'],
        'slotLabel': row['slot_label'],
        'slotStart': row['slot_start'],
        'slotEnd': row['slot_end'],
        'durationMinutes': row['duration_minutes'],
        'startDate': row['start_date'],
        'endDate': row['end_date'],
        'active': bool(row['active']),
        'archived': bool(row['archived']),
        'createdAt': row['created_at'],
        'updatedAt': row['updated_at'],
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


def default_ai_token_limit() -> dict:
    return {
        'windowHours': DEFAULT_AI_TOKEN_WINDOW_HOURS,
        'inputTokenLimit': DEFAULT_AI_INPUT_TOKEN_LIMIT,
        'outputTokenLimit': DEFAULT_AI_OUTPUT_TOKEN_LIMIT,
    }


def normalize_ai_token_limit(raw: object) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, 'limit must be an object'
    try:
        window_hours = int(raw.get('windowHours'))
        input_limit = int(raw.get('inputTokenLimit'))
        output_limit = int(raw.get('outputTokenLimit'))
    except (TypeError, ValueError):
        return None, 'windowHours, inputTokenLimit and outputTokenLimit must be integers'
    if window_hours < 1 or window_hours > 24 * 365:
        return None, 'windowHours must be between 1 and 8760'
    if input_limit < 1 or input_limit > 10_000_000_000:
        return None, 'inputTokenLimit must be between 1 and 10000000000'
    if output_limit < 1 or output_limit > 10_000_000_000:
        return None, 'outputTokenLimit must be between 1 and 10000000000'
    return {
        'windowHours': window_hours,
        'inputTokenLimit': input_limit,
        'outputTokenLimit': output_limit,
    }, None


def get_ai_global_token_limit(conn: sqlite3.Connection) -> dict:
    row = conn.execute('SELECT value FROM app_settings WHERE key = ?', (AI_TOKEN_LIMIT_SETTING_KEY,)).fetchone()
    if not row:
        return default_ai_token_limit()
    try:
        payload = json.loads(row['value'])
    except (TypeError, json.JSONDecodeError):
        return default_ai_token_limit()
    limit, error = normalize_ai_token_limit(payload)
    return default_ai_token_limit() if error else limit


def set_ai_global_token_limit(conn: sqlite3.Connection, limit: dict) -> None:
    conn.execute(
        '''
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        ''',
        (AI_TOKEN_LIMIT_SETTING_KEY, json.dumps(limit, ensure_ascii=False), now_iso()),
    )


def get_ai_user_token_limit(conn: sqlite3.Connection, user_id: int) -> dict | None:
    row = conn.execute(
        '''
        SELECT window_hours, input_token_limit, output_token_limit, updated_at
        FROM ai_token_limits
        WHERE user_id = ?
        ''',
        (user_id,),
    ).fetchone()
    if not row:
        return None
    return {
        'windowHours': int(row['window_hours']),
        'inputTokenLimit': int(row['input_token_limit']),
        'outputTokenLimit': int(row['output_token_limit']),
        'updatedAt': row['updated_at'],
    }


def set_ai_user_token_limit(conn: sqlite3.Connection, user_id: int, limit: dict) -> None:
    conn.execute(
        '''
        INSERT INTO ai_token_limits
        (user_id, window_hours, input_token_limit, output_token_limit, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            window_hours = excluded.window_hours,
            input_token_limit = excluded.input_token_limit,
            output_token_limit = excluded.output_token_limit,
            updated_at = excluded.updated_at
        ''',
        (
            user_id,
            limit['windowHours'],
            limit['inputTokenLimit'],
            limit['outputTokenLimit'],
            now_iso(),
        ),
    )


def effective_ai_token_limit(conn: sqlite3.Connection, user_id: int) -> dict:
    user_limit = get_ai_user_token_limit(conn, user_id)
    if user_limit:
        return {**user_limit, 'source': 'user', 'hasOverride': True}
    return {**get_ai_global_token_limit(conn), 'source': 'global', 'hasOverride': False}


def ai_token_window_start(window_hours: int) -> str:
    start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    return start.strftime('%Y-%m-%dT%H:%M:%SZ')


def ai_usage_totals_since(conn: sqlite3.Connection, user_id: int | None, start_key: str) -> dict:
    params: list[object] = [start_key]
    where = 'created_at >= ?'
    if user_id is not None:
        where += ' AND user_id = ?'
        params.append(user_id)
    row = conn.execute(
        f'''
        SELECT
            COUNT(*) AS calls,
            COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
            COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
            COALESCE(SUM(total_tokens), 0) AS total_tokens
        FROM ai_usage_logs
        WHERE {where}
        ''',
        tuple(params),
    ).fetchone()
    return {
        'calls': int(row['calls'] or 0),
        'promptTokens': int(row['prompt_tokens'] or 0),
        'completionTokens': int(row['completion_tokens'] or 0),
        'totalTokens': int(row['total_tokens'] or 0),
    }


def normalize_deepseek_usage(usage: object) -> dict:
    source = usage if isinstance(usage, dict) else {}
    details = source.get('completion_tokens_details') if isinstance(source.get('completion_tokens_details'), dict) else {}

    def safe_int(key: str, raw_source: dict = source) -> int:
        try:
            return max(0, int(raw_source.get(key, 0) or 0))
        except (TypeError, ValueError):
            return 0

    return {
        'promptTokens': safe_int('prompt_tokens'),
        'completionTokens': safe_int('completion_tokens'),
        'totalTokens': safe_int('total_tokens'),
        'promptCacheHitTokens': safe_int('prompt_cache_hit_tokens'),
        'promptCacheMissTokens': safe_int('prompt_cache_miss_tokens'),
        'reasoningTokens': safe_int('reasoning_tokens', details),
    }


def record_ai_usage(conn: sqlite3.Connection, user_id: int, model: str, call_type: str, usage: object) -> dict:
    normalized = normalize_deepseek_usage(usage)
    conn.execute(
        '''
        INSERT INTO ai_usage_logs
        (user_id, model, call_type, prompt_tokens, completion_tokens, total_tokens,
         prompt_cache_hit_tokens, prompt_cache_miss_tokens, reasoning_tokens, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            user_id,
            model,
            call_type,
            normalized['promptTokens'],
            normalized['completionTokens'],
            normalized['totalTokens'],
            normalized['promptCacheHitTokens'],
            normalized['promptCacheMissTokens'],
            normalized['reasoningTokens'],
            now_iso(),
        ),
    )
    return normalized


def ai_token_limit_status(conn: sqlite3.Connection, user_id: int) -> dict:
    limit = effective_ai_token_limit(conn, user_id)
    usage = ai_usage_totals_since(conn, user_id, ai_token_window_start(limit['windowHours']))
    exceeded_dimension = ''
    if usage['promptTokens'] >= limit['inputTokenLimit']:
        exceeded_dimension = 'input'
    elif usage['completionTokens'] >= limit['outputTokenLimit']:
        exceeded_dimension = 'output'
    return {
        'limit': limit,
        'usage': usage,
        'exceeded': bool(exceeded_dimension),
        'dimension': exceeded_dimension,
    }


def ai_token_limit_error(status: dict) -> dict:
    limit = status['limit']
    usage = status['usage']
    dimension = status.get('dimension') or 'input'
    if dimension == 'output':
        message = (
            f"AI 输出 token 额度已达到限制：最近 {limit['windowHours']} 小时已用 "
            f"{usage['completionTokens']} / {limit['outputTokenLimit']}。"
        )
    else:
        message = (
            f"AI 输入 token 额度已达到限制：最近 {limit['windowHours']} 小时已用 "
            f"{usage['promptTokens']} / {limit['inputTokenLimit']}。"
        )
    return {
        'error': 'AI token limit exceeded',
        'message': message,
        'dimension': dimension,
        'windowHours': limit['windowHours'],
        'inputTokenLimit': limit['inputTokenLimit'],
        'outputTokenLimit': limit['outputTokenLimit'],
        'currentInputTokens': usage['promptTokens'],
        'currentOutputTokens': usage['completionTokens'],
    }


class AiTokenLimitExceeded(Exception):
    def __init__(self, payload: dict):
        super().__init__(payload.get('message') or 'AI token limit exceeded')
        self.payload = payload


def default_installer_download_limit() -> dict:
    return {
        'windowHours': DEFAULT_INSTALLER_DOWNLOAD_WINDOW_HOURS,
        'linkLimit': DEFAULT_INSTALLER_DOWNLOAD_LINK_LIMIT,
    }


def normalize_installer_download_limit(raw: object) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, 'limit must be an object'
    try:
        window_hours = int(raw.get('windowHours'))
        link_limit = int(raw.get('linkLimit'))
    except (TypeError, ValueError):
        return None, 'windowHours and linkLimit must be integers'
    if window_hours < 1 or window_hours > 24 * 365:
        return None, 'windowHours must be between 1 and 8760'
    if link_limit < 1 or link_limit > 1_000_000:
        return None, 'linkLimit must be between 1 and 1000000'
    return {'windowHours': window_hours, 'linkLimit': link_limit}, None


def get_installer_global_download_limit(conn: sqlite3.Connection) -> dict:
    row = conn.execute('SELECT value FROM app_settings WHERE key = ?', (INSTALLER_DOWNLOAD_LIMIT_SETTING_KEY,)).fetchone()
    if not row:
        return default_installer_download_limit()
    try:
        payload = json.loads(row['value'])
    except (TypeError, json.JSONDecodeError):
        return default_installer_download_limit()
    limit, error = normalize_installer_download_limit(payload)
    return default_installer_download_limit() if error else limit


def set_installer_global_download_limit(conn: sqlite3.Connection, limit: dict) -> None:
    conn.execute(
        '''
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        ''',
        (INSTALLER_DOWNLOAD_LIMIT_SETTING_KEY, json.dumps(limit, ensure_ascii=False), now_iso()),
    )


def get_installer_user_download_limit(conn: sqlite3.Connection, user_id: int) -> dict | None:
    row = conn.execute(
        '''
        SELECT window_hours, link_limit, updated_at
        FROM installer_download_limits
        WHERE user_id = ?
        ''',
        (user_id,),
    ).fetchone()
    if not row:
        return None
    return {
        'windowHours': int(row['window_hours']),
        'linkLimit': int(row['link_limit']),
        'updatedAt': row['updated_at'],
    }


def set_installer_user_download_limit(conn: sqlite3.Connection, user_id: int, limit: dict) -> None:
    conn.execute(
        '''
        INSERT INTO installer_download_limits
        (user_id, window_hours, link_limit, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            window_hours = excluded.window_hours,
            link_limit = excluded.link_limit,
            updated_at = excluded.updated_at
        ''',
        (user_id, limit['windowHours'], limit['linkLimit'], now_iso()),
    )


def effective_installer_download_limit(conn: sqlite3.Connection, user_id: int) -> dict:
    user_limit = get_installer_user_download_limit(conn, user_id)
    if user_limit:
        return {**user_limit, 'source': 'user', 'hasOverride': True}
    return {**get_installer_global_download_limit(conn), 'source': 'global', 'hasOverride': False}


def installer_download_window_start(window_hours: int) -> str:
    start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    return start.strftime('%Y-%m-%dT%H:%M:%SZ')


def installer_download_totals_since(conn: sqlite3.Connection, user_id: int | None, start_key: str) -> dict:
    params: list[object] = [start_key]
    where = 'created_at >= ?'
    if user_id is not None:
        where += ' AND user_id = ?'
        params.append(user_id)
    row = conn.execute(
        f'''
        SELECT COUNT(*) AS link_count
        FROM installer_download_logs
        WHERE {where}
        ''',
        tuple(params),
    ).fetchone()
    return {'linkCount': int(row['link_count'] or 0)}


def installer_download_limit_status(conn: sqlite3.Connection, user_id: int) -> dict:
    limit = effective_installer_download_limit(conn, user_id)
    usage = installer_download_totals_since(conn, user_id, installer_download_window_start(limit['windowHours']))
    return {
        'limit': limit,
        'usage': usage,
        'exceeded': usage['linkCount'] >= limit['linkLimit'],
    }


def installer_download_limit_error(status: dict) -> dict:
    limit = status['limit']
    usage = status['usage']
    return {
        'error': 'installer download limit exceeded',
        'message': (
            f"安装包下载链接生成次数已达到限制：最近 {limit['windowHours']} 小时已用 "
            f"{usage['linkCount']} / {limit['linkLimit']} 次。"
        ),
        'windowHours': limit['windowHours'],
        'linkLimit': limit['linkLimit'],
        'currentLinkCount': usage['linkCount'],
    }


def record_installer_download(
    conn: sqlite3.Connection,
    user_id: int,
    source: str,
    object_key: str,
    filename: str,
    ip: str,
    user_agent: str,
) -> dict:
    conn.execute(
        '''
        INSERT INTO installer_download_logs
        (user_id, source, object_key, filename, ip, user_agent, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            user_id,
            str(source or '')[:20],
            str(object_key or '')[:1000],
            str(filename or '')[:500],
            str(ip or '')[:80],
            str(user_agent or '')[:1000],
            now_iso(),
        ),
    )
    return installer_download_limit_status(conn, user_id)


def normalize_ip(value: str) -> str:
    value = str(value).strip()
    if not value:
        return ''
    if value.startswith('[') and ']' in value:
        value = value[1:value.index(']')]
    elif value.count(':') == 1:
        host, port = value.rsplit(':', 1)
        if port.isdigit():
            value = host
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return ''


def normalize_static_request_path(path: str) -> str:
    decoded = unquote(str(path or ''))
    if '\x00' in decoded or '\\' in decoded:
        return ''
    normalized = posixpath.normpath(decoded)
    if not normalized.startswith('/'):
        normalized = f'/{normalized}'
    return normalized


def is_allowed_static_path(path: str) -> bool:
    normalized = normalize_static_request_path(path)
    if normalized == '/':
        return True
    if normalized in STATIC_FILE_PATHS:
        return True
    return any(
        normalized.startswith(prefix) and not normalized.endswith('/')
        for prefix in STATIC_DIRECTORY_PREFIXES
    )


def find_managebac_installer() -> Path | None:
    direct_exes = sorted(MANAGEBAC_HELPER_DIR.glob('*.exe'))
    if len(direct_exes) == 1:
        return direct_exes[0]

    dist_dir = MANAGEBAC_HELPER_DIR / 'dist'
    setup_exes = sorted(
        path
        for path in dist_dir.glob('*.exe')
        if 'setup' in path.name.lower()
    )
    if len(setup_exes) == 1:
        return setup_exes[0]

    dist_exes = sorted(dist_dir.glob('*.exe'))
    if len(dist_exes) == 1:
        return dist_exes[0]

    return None


@dataclass(frozen=True)
class ManageBacOssInstallerConfig:
    access_key_id: str
    access_key_secret: str
    region: str
    bucket: str
    key: str
    endpoint: str
    expires_seconds: int
    filename: str


class ManageBacOssConfigError(RuntimeError):
    pass


class ManageBacOssDependencyError(RuntimeError):
    pass


def read_env_value(name: str) -> str:
    return os.environ.get(name, '').strip()


def configured_managebac_oss_values() -> dict[str, str]:
    return {name: read_env_value(name) for name in MANAGEBAC_OSS_INSTALLER_ENV_NAMES}


def get_managebac_oss_installer_config() -> ManageBacOssInstallerConfig | None:
    values = configured_managebac_oss_values()
    required_names = [
        'ALIYUN_OSS_ACCESS_KEY_ID',
        'ALIYUN_OSS_ACCESS_KEY_SECRET',
        'ALIYUN_OSS_REGION',
        'ALIYUN_OSS_BUCKET',
        'ALIYUN_OSS_INSTALLER_KEY',
    ]
    if not any(values.values()):
        return None

    missing = [name for name in required_names if not values[name]]
    if missing:
        raise ManageBacOssConfigError(f'Missing OSS environment variables: {", ".join(missing)}')

    raw_key = values['ALIYUN_OSS_INSTALLER_KEY']
    key = raw_key.lstrip('/')
    if not key:
        raise ManageBacOssConfigError('ALIYUN_OSS_INSTALLER_KEY cannot be empty')
    filename = values['ALIYUN_OSS_INSTALLER_FILENAME'] or Path(key).name or 'managebac-sync-helper.exe'

    raw_expires = values['ALIYUN_OSS_SIGN_EXPIRES_SECONDS']
    if raw_expires:
        try:
            expires_seconds = int(raw_expires)
        except ValueError as exc:
            raise ManageBacOssConfigError('ALIYUN_OSS_SIGN_EXPIRES_SECONDS must be an integer') from exc
        if expires_seconds < 1 or expires_seconds > MAX_OSS_SIGN_EXPIRES_SECONDS:
            raise ManageBacOssConfigError(
                f'ALIYUN_OSS_SIGN_EXPIRES_SECONDS must be between 1 and {MAX_OSS_SIGN_EXPIRES_SECONDS}'
            )
    else:
        expires_seconds = DEFAULT_OSS_SIGN_EXPIRES_SECONDS

    return ManageBacOssInstallerConfig(
        access_key_id=values['ALIYUN_OSS_ACCESS_KEY_ID'],
        access_key_secret=values['ALIYUN_OSS_ACCESS_KEY_SECRET'],
        region=values['ALIYUN_OSS_REGION'],
        bucket=values['ALIYUN_OSS_BUCKET'],
        key=key,
        endpoint=values['ALIYUN_OSS_ENDPOINT'],
        expires_seconds=expires_seconds,
        filename=filename,
    )


def content_disposition_attachment(filename: str) -> str:
    ascii_name = ''.join(ch if 32 <= ord(ch) < 127 and ch not in {'"', '\\'} else '_' for ch in filename)
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def generate_managebac_oss_installer_url(config: ManageBacOssInstallerConfig) -> str:
    try:
        import alibabacloud_oss_v2 as oss
    except ImportError as exc:
        raise ManageBacOssDependencyError(
            'Missing Python dependency: alibabacloud-oss-v2. Run: pip install -r requirements.txt'
        ) from exc

    credentials_provider = oss.credentials.StaticCredentialsProvider(
        access_key_id=config.access_key_id,
        access_key_secret=config.access_key_secret,
    )
    oss_config = oss.config.load_default()
    oss_config.credentials_provider = credentials_provider
    oss_config.region = config.region
    if config.endpoint:
        oss_config.endpoint = config.endpoint

    client = oss.Client(oss_config)
    presigned = client.presign(
        oss.GetObjectRequest(
            bucket=config.bucket,
            key=config.key,
            response_content_disposition=content_disposition_attachment(config.filename),
        ),
        expires=timedelta(seconds=config.expires_seconds),
    )
    return presigned.url


class TodoHandler(SimpleHTTPRequestHandler):
    server_version = 'TodoListHTTP/1.0'
    sys_version = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/managebac-helper/installer':
            return self.handle_managebac_installer(send_body=True)
        if path.startswith('/uploads/avatars/'):
            return self.handle_avatar_file(path, send_body=True)
        if path.startswith('/api/admin/'):
            return self.handle_admin_get(path)
        if path == '/api/tasks':
            return self.handle_list_tasks()
        if path == '/api/schedule-items':
            return self.handle_list_schedule_items()
        if path == '/api/habits':
            return self.handle_list_habits()
        if path == '/api/schedule-config':
            return self.handle_get_schedule_config()
        if path == '/api/subject-template':
            return self.handle_get_subject_template()
        if path == '/api/feedback':
            return self.handle_list_feedback()
        if path == '/api/auth/me':
            return self.handle_auth_me()
        if path == '/api/health':
            return self.write_json({'ok': True})
        if path.startswith('/api/'):
            return self.write_json({'error': 'not found'}, status=HTTPStatus.NOT_FOUND)
        if path in {'/', '/index.html'}:
            self.record_visit('home', path)
        if not is_allowed_static_path(path):
            self.send_error(HTTPStatus.NOT_FOUND, 'Not found')
            return
        return super().do_GET()

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path == '/api/managebac-helper/installer':
            return self.handle_managebac_installer(send_body=False)
        if path.startswith('/uploads/avatars/'):
            return self.handle_avatar_file(path, send_body=False)
        if not is_allowed_static_path(path):
            self.send_error(HTTPStatus.NOT_FOUND, 'Not found')
            return
        return super().do_HEAD()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/visits':
            return self.handle_create_visit()
        if path == '/api/admin/ai-usage/clear-user-limits':
            return self.handle_admin_clear_all_ai_token_limits()
        if path == '/api/admin/installer-downloads/clear-user-limits':
            return self.handle_admin_clear_all_installer_download_limits()
        if path == '/api/auth/register':
            return self.handle_auth_register()
        if path == '/api/auth/login':
            return self.handle_auth_login()
        if path == '/api/auth/logout':
            return self.handle_auth_logout()
        if path == '/api/auth/avatar':
            return self.handle_auth_update_avatar()
        if path == '/api/ai/chat':
            return self.handle_ai_chat()
        if path == '/api/ai/chat-stream':
            return self.handle_ai_chat_stream()
        if path == '/api/tasks':
            return self.handle_create_task()
        if path == '/api/schedule-items':
            return self.handle_create_schedule_item()
        if path == '/api/habits':
            return self.handle_create_habit()
        if path == '/api/feedback':
            return self.handle_create_feedback()
        if path.startswith('/api/'):
            return self.write_json({'error': 'not found'}, status=HTTPStatus.NOT_FOUND)
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def do_PUT(self):
        path = urlparse(self.path).path
        if path == '/api/auth/nickname':
            return self.handle_auth_update_nickname()
        if path == '/api/auth/password':
            return self.handle_auth_update_password()
        if path == '/api/auth/avatar-color':
            return self.handle_auth_update_avatar_color()
        if path == '/api/admin/ai-usage/global-limit':
            return self.handle_admin_update_ai_global_limit()
        if path == '/api/admin/installer-downloads/global-limit':
            return self.handle_admin_update_installer_download_global_limit()
        parts = path.strip('/').split('/')
        if len(parts) == 5 and parts[:3] == ['api', 'admin', 'users'] and parts[4] == 'ai-token-limit':
            return self.handle_admin_update_user_ai_token_limit(parts[3])
        if len(parts) == 5 and parts[:3] == ['api', 'admin', 'users'] and parts[4] == 'installer-download-limit':
            return self.handle_admin_update_user_installer_download_limit(parts[3])
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
        if path.startswith('/api/habits/'):
            return self.handle_update_habit(path.rsplit('/', 1)[-1])
        if path == '/api/schedule-template':
            return self.handle_update_schedule_template()
        if path == '/api/subject-template':
            return self.handle_update_subject_template()
        if path.startswith('/api/schedule-day-slots/'):
            return self.handle_update_schedule_day_slots(path.rsplit('/', 1)[-1])
        if path.startswith('/api/'):
            return self.write_json({'error': 'not found'}, status=HTTPStatus.NOT_FOUND)
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith('/api/admin/feedback/'):
            return self.handle_admin_delete_feedback(path.rsplit('/', 1)[-1])
        parts = path.strip('/').split('/')
        if len(parts) == 5 and parts[:3] == ['api', 'admin', 'users'] and parts[4] == 'ai-token-limit':
            return self.handle_admin_clear_user_ai_token_limit(parts[3])
        if len(parts) == 5 and parts[:3] == ['api', 'admin', 'users'] and parts[4] == 'installer-download-limit':
            return self.handle_admin_clear_user_installer_download_limit(parts[3])
        if path.startswith('/api/feedback/'):
            return self.handle_delete_feedback(path.rsplit('/', 1)[-1])
        if path == '/api/auth/avatar':
            return self.handle_auth_delete_avatar()
        if path.startswith('/api/admin/users/'):
            return self.handle_admin_delete_user(path.rsplit('/', 1)[-1])
        if path.startswith('/api/tasks/'):
            return self.handle_delete_task(path.rsplit('/', 1)[-1])
        if path.startswith('/api/schedule-items/'):
            return self.handle_delete_schedule_item(path.rsplit('/', 1)[-1])
        if path.startswith('/api/habits/'):
            return self.handle_delete_habit(path.rsplit('/', 1)[-1])
        if path == '/api/schedule-config':
            return self.handle_reset_schedule_config()
        if path.startswith('/api/schedule-day-slots/'):
            return self.handle_reset_schedule_day(path.rsplit('/', 1)[-1])
        if path.startswith('/api/'):
            return self.write_json({'error': 'not found'}, status=HTTPStatus.NOT_FOUND)
        self.send_error(HTTPStatus.NOT_FOUND, 'Not found')

    def handle_avatar_file(self, path: str, send_body: bool = True):
        prefix = '/uploads/avatars/'
        filename = unquote(path[len(prefix):]) if path.startswith(prefix) else ''
        if not is_safe_avatar_filename(filename):
            self.send_error(HTTPStatus.NOT_FOUND, 'Not found')
            return
        file_path = avatar_dir() / filename
        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, 'Not found')
            return
        try:
            raw = file_path.read_bytes() if send_body else b''
            size = file_path.stat().st_size
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, 'Not found')
            return
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', avatar_content_type(filename))
        self.send_header('Content-Length', str(size))
        self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
        self.end_headers()
        if send_body:
            self.wfile.write(raw)

    def handle_managebac_installer(self, send_body: bool = True):
        if not send_body:
            user = self.current_user()
            self.send_response(HTTPStatus.NO_CONTENT if user else HTTPStatus.UNAUTHORIZED)
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            return

        user = self.require_user()
        if not user:
            return
        user_id = int(user['id'])
        with get_db() as conn:
            limit_status = installer_download_limit_status(conn, user_id)
        if limit_status['exceeded']:
            return self.write_json(installer_download_limit_error(limit_status), status=HTTPStatus.TOO_MANY_REQUESTS)

        try:
            oss_config = get_managebac_oss_installer_config()
        except ManageBacOssConfigError as error:
            return self.write_json({'error': 'oss config error', 'message': str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        if oss_config:
            try:
                signed_url = generate_managebac_oss_installer_url(oss_config)
            except ManageBacOssDependencyError as error:
                return self.write_json({'error': 'oss dependency missing', 'message': str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:
                return self.write_json(
                    {'error': 'oss presign failed', 'message': '安装包下载链接生成失败。'},
                    status=HTTPStatus.BAD_GATEWAY,
                )
            with get_db() as conn:
                conn.execute('BEGIN IMMEDIATE')
                limit_status = installer_download_limit_status(conn, user_id)
                if limit_status['exceeded']:
                    return self.write_json(installer_download_limit_error(limit_status), status=HTTPStatus.TOO_MANY_REQUESTS)
                next_status = record_installer_download(
                    conn,
                    user_id,
                    'oss',
                    oss_config.key,
                    oss_config.filename,
                    self.request_ip(),
                    str(self.headers.get('User-Agent', '')),
                )
                conn.commit()
            return self.write_json({
                'ok': True,
                'source': 'oss',
                'url': signed_url,
                'expiresSeconds': oss_config.expires_seconds,
                'limit': next_status['limit'],
                'usage': next_status['usage'],
            })

        file_path = find_managebac_installer()
        if not file_path or not file_path.is_file():
            return self.write_json(
                {'error': 'installer not found', 'message': 'ManageBac 安装包不存在。'},
                status=HTTPStatus.NOT_FOUND,
            )
        try:
            size = file_path.stat().st_size
            source = file_path.open('rb')
        except OSError:
            return self.write_json(
                {'error': 'installer not found', 'message': 'ManageBac 安装包不存在。'},
                status=HTTPStatus.NOT_FOUND,
            )
        filename = file_path.name
        with get_db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            limit_status = installer_download_limit_status(conn, user_id)
            if limit_status['exceeded']:
                source.close()
                return self.write_json(installer_download_limit_error(limit_status), status=HTTPStatus.TOO_MANY_REQUESTS)
            record_installer_download(
                conn,
                user_id,
                'local',
                str(file_path.relative_to(BASE_DIR)) if file_path.is_relative_to(BASE_DIR) else file_path.name,
                filename,
                self.request_ip(),
                str(self.headers.get('User-Agent', '')),
            )
            conn.commit()
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'application/vnd.microsoft.portable-executable')
        self.send_header('Content-Length', str(size))
        self.send_header('Content-Disposition', content_disposition_attachment(filename))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        with source:
            self.copyfile(source, self.wfile)

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
                SELECT users.id, users.name, users.nickname, users.role,
                       users.avatar_file, users.avatar_updated_at, users.avatar_color, sessions.expires_at
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
                self.request_ip(),
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

    def fetch_ai_context_tasks_for_user(self, conn: sqlite3.Connection, user_id: int) -> tuple[list[dict], dict]:
        total_row = conn.execute(
            '''
            SELECT COUNT(*) AS total
            FROM tasks
            WHERE user_id = ? AND pool = 'todo' AND completed = 0
            ''',
            (user_id,),
        ).fetchone()
        total_count = int(total_row['total'] or 0)
        rows = conn.execute(
            '''
            SELECT id, user_id, title, subject, due_at, pool, priority, note, completed, created_at, updated_at
            FROM tasks
            WHERE user_id = ? AND pool = 'todo' AND completed = 0
            ORDER BY due_at ASC, CASE priority
                WHEN 'high' THEN 0
                WHEN 'medium' THEN 1
                ELSE 2
            END ASC, title COLLATE NOCASE ASC
            LIMIT ?
            ''',
            (user_id, AI_CONTEXT_TASK_LIMIT),
        ).fetchall()
        included_tasks = [public_task(row) for row in rows]
        return included_tasks, ai_task_context_payload(included_tasks, total_count)

    def normalize_ai_history(self, raw_history: object) -> list[dict]:
        if not isinstance(raw_history, list):
            return []
        history = []
        for item in raw_history[-AI_HISTORY_LIMIT:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get('role', '') or '').strip()
            if role not in {'user', 'assistant'}:
                continue
            content = str(item.get('content', '') or '').strip()
            if not content:
                continue
            history.append({'role': role, 'content': content[:1000]})
        return history

    def ensure_ai_token_available(self, user_id: int) -> None:
        with get_db() as conn:
            status = ai_token_limit_status(conn, int(user_id))
        if status['exceeded']:
            raise AiTokenLimitExceeded(ai_token_limit_error(status))

    def record_ai_usage_for_user(self, user_id: int, call_type: str, usage: object) -> dict:
        with get_db() as conn:
            normalized = record_ai_usage(conn, int(user_id), deepseek_model(), call_type, usage)
            conn.commit()
            return normalized

    def call_deepseek_chat_recorded(self, messages: list[dict], user_id: int, call_type: str) -> str:
        self._last_deepseek_usage = None
        content = self.call_deepseek_chat(messages)
        self.record_ai_usage_for_user(user_id, call_type, getattr(self, '_last_deepseek_usage', None))
        return content

    def build_ai_messages(
        self,
        message: str,
        history: list[dict],
        tasks: list[dict],
        client_now: str,
        timezone_name: str,
        subject_names: list[str] | None = None,
        task_context: dict | None = None,
    ) -> list[dict]:
        if task_context is None:
            _, task_context = ai_context_tasks(tasks)
        context = {
            'clientNow': client_now,
            'timezone': timezone_name,
            'request': message,
            **ai_subject_context(subject_names or []),
            **task_context,
        }
        return [
            {'role': 'system', 'content': AI_CHAT_SYSTEM_PROMPT},
            *history,
            {
                'role': 'user',
                'content': '请根据下面 JSON 上下文处理用户请求，并按 system 中的 JSON schema 输出：\n'
                           + json.dumps(context, ensure_ascii=False),
            },
        ]

    def build_ai_stream_messages(
        self,
        message: str,
        history: list[dict],
        tasks: list[dict],
        client_now: str,
        timezone_name: str,
        subject_names: list[str] | None = None,
        task_context: dict | None = None,
    ) -> list[dict]:
        if task_context is None:
            _, task_context = ai_context_tasks(tasks)
        context = {
            'clientNow': client_now,
            'timezone': timezone_name,
            'request': message,
            **ai_subject_context(subject_names or []),
            **task_context,
        }
        return [
            {'role': 'system', 'content': AI_STREAM_SYSTEM_PROMPT},
            *history,
            {
                'role': 'user',
                'content': '请根据下面 JSON 上下文处理用户请求，先输出自然语言回复，最后输出动作 JSON 标签：\n'
                           + json.dumps(context, ensure_ascii=False),
            },
        ]

    def call_deepseek_chat(self, messages: list[dict]) -> str:
        api_key = deepseek_api_key()
        if not api_key:
            raise ValueError('missing api key')
        self._last_deepseek_usage = None
        body = json.dumps({
            'model': deepseek_model(),
            'messages': messages,
            'response_format': {'type': 'json_object'},
            'stream': False,
            'max_tokens': 2000,
        }, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(
            DEEPSEEK_API_URL,
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=deepseek_timeout_seconds()) as response:
                payload = json.loads(response.read().decode('utf-8') or '{}')
        except urllib.error.HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')[:500]
            raise RuntimeError(f'DeepSeek HTTP {error.code}: {detail}') from error
        except urllib.error.URLError as error:
            raise RuntimeError(f'DeepSeek request failed: {error.reason}') from error
        except (TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f'DeepSeek response failed: {error}') from error

        try:
            content = payload['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError('DeepSeek response missing message content') from error
        self._last_deepseek_usage = payload.get('usage') if isinstance(payload, dict) else None
        return str(content or '').strip()

    def build_ai_repair_messages(
        self,
        message: str,
        history: list[dict],
        tasks: list[dict],
        client_now: str,
        timezone_name: str,
        original_reply: str,
        raw_actions: object,
        rejected_actions: list[dict],
        subject_names: list[str] | None = None,
        task_context: dict | None = None,
    ) -> list[dict]:
        if task_context is None:
            _, task_context = ai_context_tasks(tasks)
        context = {
            'clientNow': client_now,
            'timezone': timezone_name,
            'request': message,
            **ai_subject_context(subject_names or []),
            **task_context,
            'originalReply': original_reply,
            'originalActions': raw_actions if isinstance(raw_actions, list) else [],
            'rejectedActions': rejected_actions,
            'backendSafetyValidation': {
                'blocked': True,
                'instruction': '这些 actions 已被后端安全校验拒绝。请根据 rejectedActions 的 reason 修正；如果缺少必需信息，就追问用户并返回空 actions。',
                'rejectedActions': rejected_actions,
            },
        }
        return [
            {'role': 'system', 'content': AI_REPAIR_SYSTEM_PROMPT},
            *history,
            {
                'role': 'user',
                'content': '请根据下面 JSON 上下文修正被拦截的 AI 指令。如果不能安全修正，就追问用户：\n'
                           + json.dumps(context, ensure_ascii=False),
            },
        ]

    def repair_ai_response(
        self,
        user_id: int,
        message: str,
        history: list[dict],
        tasks: list[dict],
        client_now: str,
        timezone_name: str,
        original_reply: str,
        raw_actions: object,
        rejected_actions: list[dict],
        subject_names: list[str] | None = None,
        task_context: dict | None = None,
    ) -> tuple[str, list[dict], list[dict]] | None:
        if not rejected_actions:
            return None
        repair_messages = self.build_ai_repair_messages(
            message,
            history,
            tasks,
            client_now,
            timezone_name,
            original_reply,
            raw_actions,
            rejected_actions,
            subject_names or [],
            task_context,
        )
        self.ensure_ai_token_available(user_id)
        content = self.call_deepseek_chat_recorded(repair_messages, user_id, 'repair')
        repair_payload, parse_error = parse_ai_json_content(content)
        if parse_error:
            return None
        visible_tasks = tasks
        repair_reply = str(repair_payload.get('reply', '') or '').strip()
        repair_actions, repair_rejected = normalize_ai_actions(repair_payload.get('actions'), visible_tasks, subject_names or [])
        if not repair_reply:
            repair_reply = '我还需要更明确的信息。' if not repair_actions else '我修正好了可审批的操作。'
        return repair_reply[:2000], repair_actions, repair_rejected

    def stream_deepseek_chat(self, messages: list[dict]):
        api_key = deepseek_api_key()
        if not api_key:
            raise ValueError('missing api key')
        self._last_deepseek_stream_usage = None
        body = json.dumps({
            'model': deepseek_model(),
            'messages': messages,
            'stream': True,
            'stream_options': {'include_usage': True},
            'max_tokens': 2000,
        }, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(
            DEEPSEEK_API_URL,
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=deepseek_timeout_seconds()) as response:
                for raw_line in response:
                    line = raw_line.decode('utf-8', errors='replace').strip()
                    if not line or line.startswith(':'):
                        continue
                    if not line.startswith('data:'):
                        continue
                    data = line[len('data:'):].strip()
                    if data == '[DONE]':
                        break
                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(payload, dict) and payload.get('usage') is not None:
                        self._last_deepseek_stream_usage = payload.get('usage')
                    try:
                        delta = payload['choices'][0].get('delta', {}).get('content', '')
                    except (KeyError, IndexError, TypeError):
                        delta = ''
                    if delta:
                        yield str(delta)
        except urllib.error.HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')[:500]
            raise RuntimeError(f'DeepSeek HTTP {error.code}: {detail}') from error
        except urllib.error.URLError as error:
            raise RuntimeError(f'DeepSeek request failed: {error.reason}') from error
        except TimeoutError as error:
            raise RuntimeError(f'DeepSeek response failed: {error}') from error

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

    def fetch_habits_for_user(self, conn: sqlite3.Connection, user_id: int, include_archived: bool = False) -> list[dict]:
        archived_filter = '' if include_archived else 'AND habits.archived = 0'
        rows = conn.execute(
            f"""
            SELECT habits.*, tasks.title AS task_title, tasks.subject AS task_subject,
                   tasks.priority AS task_priority, tasks.note AS task_note
            FROM habits
            JOIN tasks ON tasks.id = habits.task_id AND tasks.user_id = habits.user_id
            WHERE habits.user_id = ? {archived_filter}
            ORDER BY habits.archived ASC, habits.active DESC, habits.created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [public_habit(row) for row in rows]

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
        if parts == ['api', 'admin', 'ai-usage', 'summary']:
            return self.handle_admin_ai_usage_summary()
        if parts == ['api', 'admin', 'installer-downloads', 'summary']:
            return self.handle_admin_installer_downloads_summary()
        if len(parts) == 5 and parts[:3] == ['api', 'admin', 'users']:
            try:
                target_user_id = int(parts[3])
            except ValueError:
                return self.write_json({'error': 'invalid user id'}, status=HTTPStatus.BAD_REQUEST)
            if parts[4] == 'tasks':
                return self.handle_admin_user_tasks(target_user_id)
            if parts[4] == 'schedule-items':
                return self.handle_admin_user_schedule_items(target_user_id)
            if parts[4] == 'habits':
                return self.handle_admin_user_habits(target_user_id)
            if parts[4] == 'schedule-config':
                return self.handle_admin_user_schedule_config(target_user_id)
            if parts[4] == 'logs':
                return self.handle_admin_user_logs(target_user_id)
        return self.write_json({'error': 'not found'}, status=HTTPStatus.NOT_FOUND)

    def ensure_user_exists(self, conn: sqlite3.Connection, user_id: int):
        row = conn.execute(
            'SELECT id, name, nickname, role, created_at, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
            (user_id,),
        ).fetchone()
        return row

    def request_ip(self) -> str:
        peer_ip = normalize_ip(self.client_address[0] if self.client_address else '')
        if peer_ip in TRUSTED_PROXY_IPS:
            forwarded_for = str(self.headers.get('X-Forwarded-For', '')).strip()
            for forwarded_ip in forwarded_for.split(','):
                normalized_ip = normalize_ip(forwarded_ip)
                if normalized_ip:
                    return normalized_ip

            real_ip = normalize_ip(self.headers.get('X-Real-IP', ''))
            if real_ip:
                return real_ip

        return peer_ip

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

        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
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
                WHERE ip != '' AND created_at >= ?
                GROUP BY ip
                ORDER BY visits DESC, last_visit_at DESC
                LIMIT 10
                ''',
                (start_key,),
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

    def handle_admin_ai_usage_summary(self):
        query = parse_qs(urlparse(self.path).query)
        usage_view = str(query.get('view', ['7d'])[0]).strip()
        if usage_view not in {'30d', '7d', '1d', '6h'}:
            return self.write_json({'error': 'invalid usage view'}, status=HTTPStatus.BAD_REQUEST)
        try:
            page = max(1, int(query.get('page', ['1'])[0]))
            page_size = min(100, max(1, int(query.get('pageSize', ['50'])[0])))
        except ValueError:
            return self.write_json({'error': 'invalid pagination'}, status=HTTPStatus.BAD_REQUEST)
        offset = (page - 1) * page_size

        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
        today_key = now.date().isoformat()
        if usage_view == '30d':
            series_unit = 'day'
            bucket_count = 30
            start_dt = datetime.combine(now.date() - timedelta(days=bucket_count - 1), datetime.min.time())
        elif usage_view == '7d':
            series_unit = 'day'
            bucket_count = 7
            start_dt = datetime.combine(now.date() - timedelta(days=bucket_count - 1), datetime.min.time())
        elif usage_view == '1d':
            series_unit = 'hour'
            bucket_count = 24
            start_dt = now - timedelta(hours=bucket_count - 1)
        else:
            series_unit = 'hour'
            bucket_count = 6
            start_dt = now - timedelta(hours=bucket_count - 1)
        start_key = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        with get_db() as conn:
            global_limit = get_ai_global_token_limit(conn)
            total_row = conn.execute(
                '''
                SELECT
                    COUNT(*) AS calls,
                    COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) AS completion_tokens
                FROM ai_usage_logs
                '''
            ).fetchone()
            today_row = conn.execute(
                '''
                SELECT
                    COUNT(*) AS calls,
                    COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) AS completion_tokens
                FROM ai_usage_logs
                WHERE substr(created_at, 1, 10) = ?
                ''',
                (today_key,),
            ).fetchone()
            trend_rows = conn.execute(
                '''
                SELECT created_at, prompt_tokens, completion_tokens, total_tokens
                FROM ai_usage_logs
                WHERE created_at >= ?
                ORDER BY created_at ASC
                ''',
                (start_key,),
            ).fetchall()
            users_total = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            user_rows = conn.execute(
                '''
                SELECT users.id, users.name, users.nickname, users.role, MAX(ai_usage_logs.created_at) AS last_used_at
                FROM users
                LEFT JOIN ai_usage_logs ON ai_usage_logs.user_id = users.id
                GROUP BY users.id
                ORDER BY
                    CASE WHEN MAX(ai_usage_logs.created_at) IS NULL THEN 1 ELSE 0 END ASC,
                    MAX(ai_usage_logs.created_at) DESC,
                    users.id ASC
                LIMIT ? OFFSET ?
                ''',
                (page_size, offset),
            ).fetchall()

            user_payload = []
            for row in user_rows:
                limit = effective_ai_token_limit(conn, int(row['id']))
                usage = ai_usage_totals_since(conn, int(row['id']), ai_token_window_start(limit['windowHours']))
                user_payload.append({
                    'user': {
                        'id': row['id'],
                        'name': row['name'],
                        'nickname': row['nickname'],
                        'role': row['role'],
                    },
                    'effectiveLimit': limit,
                    'hasOverride': bool(limit.get('hasOverride')),
                    'source': limit.get('source', 'global'),
                    'windowUsage': usage,
                    'lastUsedAt': row['last_used_at'],
                })

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
            bucket = trend_by_bucket.setdefault(bucket_key, {
                'promptTokens': 0,
                'completionTokens': 0,
                'totalTokens': 0,
                'calls': 0,
            })
            bucket['promptTokens'] += int(row['prompt_tokens'] or 0)
            bucket['completionTokens'] += int(row['completion_tokens'] or 0)
            bucket['totalTokens'] += int(row['total_tokens'] or 0)
            bucket['calls'] += 1

        trend_series = []
        for bucket_offset in range(bucket_count):
            bucket_dt = start_dt + (timedelta(days=bucket_offset) if series_unit == 'day' else timedelta(hours=bucket_offset))
            if series_unit == 'day':
                bucket_key = bucket_dt.date().isoformat()
            else:
                bucket_key = bucket_dt.strftime('%Y-%m-%dT%H:00:00Z')
            item = trend_by_bucket.get(bucket_key, {
                'promptTokens': 0,
                'completionTokens': 0,
                'totalTokens': 0,
                'calls': 0,
            })
            trend_series.append({'date': bucket_key, **item})

        return self.write_json({
            'usageView': usage_view,
            'seriesUnit': series_unit,
            'globalLimit': global_limit,
            'totalPromptTokens': int(total_row['prompt_tokens'] or 0),
            'totalCompletionTokens': int(total_row['completion_tokens'] or 0),
            'totalCalls': int(total_row['calls'] or 0),
            'todayPromptTokens': int(today_row['prompt_tokens'] or 0),
            'todayCompletionTokens': int(today_row['completion_tokens'] or 0),
            'todayCalls': int(today_row['calls'] or 0),
            'trendSeries': trend_series,
            'users': user_payload,
            'usersTotal': users_total,
            'page': page,
            'pageSize': page_size,
        })

    def handle_admin_update_ai_global_limit(self):
        admin = self.require_admin()
        if not admin:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        limit, error = normalize_ai_token_limit(payload)
        if error:
            return self.write_json({'error': error}, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            set_ai_global_token_limit(conn, limit)
            self.log_operation(
                conn,
                int(admin['id']),
                int(admin['id']),
                'admin.ai_token.global_limit_update',
                'ai_token_limit',
                'global',
                {'limit': limit},
            )
            conn.commit()
        return self.write_json({'ok': True, 'globalLimit': limit})

    def handle_admin_update_user_ai_token_limit(self, user_id_text: str):
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
        limit, error = normalize_ai_token_limit(payload)
        if error:
            return self.write_json({'error': error}, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            user_row = self.ensure_user_exists(conn, user_id)
            if not user_row:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            set_ai_user_token_limit(conn, user_id, limit)
            effective_limit = effective_ai_token_limit(conn, user_id)
            self.log_operation(
                conn,
                int(admin['id']),
                user_id,
                'admin.ai_token.user_limit_update',
                'ai_token_limit',
                str(user_id),
                {'limit': limit},
            )
            conn.commit()
        return self.write_json({'ok': True, 'userId': user_id, 'effectiveLimit': effective_limit})

    def handle_admin_clear_user_ai_token_limit(self, user_id_text: str):
        admin = self.require_admin()
        if not admin:
            return
        try:
            user_id = int(user_id_text)
        except ValueError:
            return self.write_json({'error': 'invalid user id'}, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            user_row = self.ensure_user_exists(conn, user_id)
            if not user_row:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            conn.execute('DELETE FROM ai_token_limits WHERE user_id = ?', (user_id,))
            effective_limit = effective_ai_token_limit(conn, user_id)
            self.log_operation(
                conn,
                int(admin['id']),
                user_id,
                'admin.ai_token.user_limit_clear',
                'ai_token_limit',
                str(user_id),
                {},
            )
            conn.commit()
        return self.write_json({'ok': True, 'userId': user_id, 'effectiveLimit': effective_limit})

    def handle_admin_clear_all_ai_token_limits(self):
        admin = self.require_admin()
        if not admin:
            return
        with get_db() as conn:
            deleted = conn.execute('DELETE FROM ai_token_limits').rowcount
            self.log_operation(
                conn,
                int(admin['id']),
                int(admin['id']),
                'admin.ai_token.user_limits_clear_all',
                'ai_token_limit',
                'all',
                {'deleted': int(deleted or 0)},
            )
            conn.commit()
        return self.write_json({'ok': True, 'deleted': int(deleted or 0)})

    def handle_admin_installer_downloads_summary(self):
        query = parse_qs(urlparse(self.path).query)
        usage_view = str(query.get('view', ['7d'])[0]).strip()
        if usage_view not in {'30d', '7d', '1d', '6h'}:
            return self.write_json({'error': 'invalid usage view'}, status=HTTPStatus.BAD_REQUEST)
        try:
            page = max(1, int(query.get('page', ['1'])[0]))
            page_size = min(100, max(1, int(query.get('pageSize', ['50'])[0])))
        except ValueError:
            return self.write_json({'error': 'invalid pagination'}, status=HTTPStatus.BAD_REQUEST)
        offset = (page - 1) * page_size

        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
        today_key = now.date().isoformat()
        if usage_view == '30d':
            series_unit = 'day'
            bucket_count = 30
            start_dt = datetime.combine(now.date() - timedelta(days=bucket_count - 1), datetime.min.time())
        elif usage_view == '7d':
            series_unit = 'day'
            bucket_count = 7
            start_dt = datetime.combine(now.date() - timedelta(days=bucket_count - 1), datetime.min.time())
        elif usage_view == '1d':
            series_unit = 'hour'
            bucket_count = 24
            start_dt = now - timedelta(hours=bucket_count - 1)
        else:
            series_unit = 'hour'
            bucket_count = 6
            start_dt = now - timedelta(hours=bucket_count - 1)
        start_key = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        with get_db() as conn:
            global_limit = get_installer_global_download_limit(conn)
            total_row = conn.execute(
                '''
                SELECT COUNT(*) AS links, COUNT(DISTINCT user_id) AS users
                FROM installer_download_logs
                '''
            ).fetchone()
            today_row = conn.execute(
                '''
                SELECT COUNT(*) AS links, COUNT(DISTINCT user_id) AS users
                FROM installer_download_logs
                WHERE substr(created_at, 1, 10) = ?
                ''',
                (today_key,),
            ).fetchone()
            trend_rows = conn.execute(
                '''
                SELECT created_at
                FROM installer_download_logs
                WHERE created_at >= ?
                ORDER BY created_at ASC
                ''',
                (start_key,),
            ).fetchall()
            users_total = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            user_rows = conn.execute(
                '''
                SELECT users.id, users.name, users.nickname, users.role,
                       MAX(installer_download_logs.created_at) AS last_generated_at,
                       COUNT(installer_download_logs.id) AS total_links
                FROM users
                LEFT JOIN installer_download_logs ON installer_download_logs.user_id = users.id
                GROUP BY users.id
                ORDER BY
                    CASE WHEN MAX(installer_download_logs.created_at) IS NULL THEN 1 ELSE 0 END ASC,
                    MAX(installer_download_logs.created_at) DESC,
                    users.id ASC
                LIMIT ? OFFSET ?
                ''',
                (page_size, offset),
            ).fetchall()

            user_payload = []
            for row in user_rows:
                limit = effective_installer_download_limit(conn, int(row['id']))
                usage = installer_download_totals_since(conn, int(row['id']), installer_download_window_start(limit['windowHours']))
                user_payload.append({
                    'user': {
                        'id': row['id'],
                        'name': row['name'],
                        'nickname': row['nickname'],
                        'role': row['role'],
                    },
                    'effectiveLimit': limit,
                    'hasOverride': bool(limit.get('hasOverride')),
                    'source': limit.get('source', 'global'),
                    'windowUsage': usage,
                    'totalLinks': int(row['total_links'] or 0),
                    'lastGeneratedAt': row['last_generated_at'],
                })

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
            trend_by_bucket[bucket_key] = trend_by_bucket.get(bucket_key, 0) + 1

        trend_series = []
        for bucket_offset in range(bucket_count):
            bucket_dt = start_dt + (timedelta(days=bucket_offset) if series_unit == 'day' else timedelta(hours=bucket_offset))
            if series_unit == 'day':
                bucket_key = bucket_dt.date().isoformat()
            else:
                bucket_key = bucket_dt.strftime('%Y-%m-%dT%H:00:00Z')
            trend_series.append({'date': bucket_key, 'linkCount': trend_by_bucket.get(bucket_key, 0)})

        return self.write_json({
            'usageView': usage_view,
            'seriesUnit': series_unit,
            'globalLimit': global_limit,
            'totalLinks': int(total_row['links'] or 0),
            'totalUsers': int(total_row['users'] or 0),
            'todayLinks': int(today_row['links'] or 0),
            'todayUsers': int(today_row['users'] or 0),
            'trendSeries': trend_series,
            'users': user_payload,
            'usersTotal': users_total,
            'page': page,
            'pageSize': page_size,
        })

    def handle_admin_update_installer_download_global_limit(self):
        admin = self.require_admin()
        if not admin:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        limit, error = normalize_installer_download_limit(payload)
        if error:
            return self.write_json({'error': error}, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            set_installer_global_download_limit(conn, limit)
            self.log_operation(
                conn,
                int(admin['id']),
                int(admin['id']),
                'admin.installer_download.global_limit_update',
                'installer_download_limit',
                'global',
                {'limit': limit},
            )
            conn.commit()
        return self.write_json({'ok': True, 'globalLimit': limit})

    def handle_admin_update_user_installer_download_limit(self, user_id_text: str):
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
        limit, error = normalize_installer_download_limit(payload)
        if error:
            return self.write_json({'error': error}, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            user_row = self.ensure_user_exists(conn, user_id)
            if not user_row:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            set_installer_user_download_limit(conn, user_id, limit)
            effective_limit = effective_installer_download_limit(conn, user_id)
            self.log_operation(
                conn,
                int(admin['id']),
                user_id,
                'admin.installer_download.user_limit_update',
                'installer_download_limit',
                str(user_id),
                {'limit': limit},
            )
            conn.commit()
        return self.write_json({'ok': True, 'userId': user_id, 'effectiveLimit': effective_limit})

    def handle_admin_clear_user_installer_download_limit(self, user_id_text: str):
        admin = self.require_admin()
        if not admin:
            return
        try:
            user_id = int(user_id_text)
        except ValueError:
            return self.write_json({'error': 'invalid user id'}, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            user_row = self.ensure_user_exists(conn, user_id)
            if not user_row:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            conn.execute('DELETE FROM installer_download_limits WHERE user_id = ?', (user_id,))
            effective_limit = effective_installer_download_limit(conn, user_id)
            self.log_operation(
                conn,
                int(admin['id']),
                user_id,
                'admin.installer_download.user_limit_clear',
                'installer_download_limit',
                str(user_id),
                {},
            )
            conn.commit()
        return self.write_json({'ok': True, 'userId': user_id, 'effectiveLimit': effective_limit})

    def handle_admin_clear_all_installer_download_limits(self):
        admin = self.require_admin()
        if not admin:
            return
        with get_db() as conn:
            deleted = conn.execute('DELETE FROM installer_download_limits').rowcount
            self.log_operation(
                conn,
                int(admin['id']),
                int(admin['id']),
                'admin.installer_download.user_limits_clear_all',
                'installer_download_limit',
                'all',
                {'deleted': int(deleted or 0)},
            )
            conn.commit()
        return self.write_json({'ok': True, 'deleted': int(deleted or 0)})

    def handle_admin_users(self):
        with get_db() as conn:
            rows = conn.execute(
                '''
                SELECT users.id, users.name, users.nickname, users.role, users.created_at,
                       users.avatar_file, users.avatar_updated_at, users.avatar_color,
                       COUNT(DISTINCT tasks.id) AS task_count,
                       COUNT(DISTINCT schedule_items.id) AS schedule_item_count,
                       COUNT(DISTINCT habits.id) AS habit_count,
                       MAX(operation_logs.created_at) AS last_operation_at,
                       MAX(CASE WHEN operation_logs.action = 'auth.login' THEN operation_logs.created_at END) AS last_login_at
                FROM users
                LEFT JOIN tasks ON tasks.user_id = users.id
                LEFT JOIN schedule_items ON schedule_items.user_id = users.id
                LEFT JOIN habits ON habits.user_id = users.id AND habits.archived = 0
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
                    'avatarUrl': avatar_url(row['avatar_file'], row['avatar_updated_at']),
                    'avatarColor': normalize_avatar_color(row['avatar_color']),
                    'createdAt': row['created_at'],
                    'taskCount': row['task_count'],
                    'scheduleItemCount': row['schedule_item_count'],
                    'habitCount': row['habit_count'],
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
            habit_count = conn.execute('SELECT COUNT(*) FROM habits WHERE user_id = ?', (user_id,)).fetchone()[0]
            log_count = conn.execute('SELECT COUNT(*) FROM operation_logs WHERE target_user_id = ?', (user_id,)).fetchone()[0]
            feedback_count = conn.execute('SELECT COUNT(*) FROM feedback WHERE user_id = ?', (user_id,)).fetchone()[0]

            conn.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM schedule_items WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM habits WHERE user_id = ?', (user_id,))
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
                    'deletedHabitCount': int(habit_count),
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
        return self.write_json({'items': items, 'readOnly': True, 'user': public_user(user), 'habitSyncConflicts': []})

    def handle_admin_user_habits(self, user_id: int):
        with get_db() as conn:
            user = self.ensure_user_exists(conn, user_id)
            if not user:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            habits = self.fetch_habits_for_user(conn, user_id)
        return self.write_json({'habits': habits, 'readOnly': True, 'user': public_user(user)})

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

    def handle_ai_chat(self):
        user = self.require_user()
        if not user:
            return
        if not deepseek_api_key():
            return self.write_json(
                {'error': 'DeepSeek API key is not configured'},
                status=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        payload = self.read_json_body()
        if payload is None:
            return
        message = str(payload.get('message', '') or '').strip()
        if not message:
            return self.write_json({'error': 'message is required'}, status=HTTPStatus.BAD_REQUEST)
        if len(message) > 2000:
            return self.write_json({'error': 'message is too long'}, status=HTTPStatus.BAD_REQUEST)
        try:
            self.ensure_ai_token_available(int(user['id']))
        except AiTokenLimitExceeded as error:
            return self.write_json(error.payload, status=HTTPStatus.TOO_MANY_REQUESTS)

        client_now = str(payload.get('clientNow', '') or '').strip()[:40]
        timezone_name = str(payload.get('timezone', 'Asia/Shanghai') or 'Asia/Shanghai').strip()[:64]
        history = self.normalize_ai_history(payload.get('history'))
        with get_db() as conn:
            tasks, task_context = self.fetch_ai_context_tasks_for_user(conn, int(user['id']))
            subject_names = enabled_subject_names(get_subject_template_for_user(conn, int(user['id'])))

        messages = self.build_ai_messages(
            message,
            history,
            tasks,
            client_now,
            timezone_name,
            subject_names,
            task_context=task_context,
        )
        try:
            content = self.call_deepseek_chat_recorded(messages, int(user['id']), 'chat')
        except ValueError:
            return self.write_json(
                {'error': 'DeepSeek API key is not configured'},
                status=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except AiTokenLimitExceeded as error:
            return self.write_json(error.payload, status=HTTPStatus.TOO_MANY_REQUESTS)
        except RuntimeError as error:
            return self.write_json(
                {'error': 'DeepSeek request failed', 'message': str(error)},
                status=HTTPStatus.BAD_GATEWAY,
            )

        ai_payload, parse_error = parse_ai_json_content(content)
        if parse_error:
            return self.write_json({
                'ok': True,
                'reply': 'AI 返回的格式不是可执行 JSON，我没有生成任何操作。',
                'actions': [],
                'rejectedActions': [{'index': 0, 'reason': parse_error}],
            })

        reply = str(ai_payload.get('reply', '') or '').strip()
        visible_tasks, _ = ai_context_tasks(tasks)
        raw_actions = ai_payload.get('actions')
        actions, rejected = normalize_ai_actions(raw_actions, visible_tasks, subject_names)
        if not reply:
            reply = '我整理好了可审批的操作。' if actions else '我还需要更明确的信息。'
        if rejected:
            try:
                repaired = self.repair_ai_response(
                    int(user['id']),
                    message,
                    history,
                    tasks,
                    client_now,
                    timezone_name,
                    reply,
                    raw_actions,
                    rejected,
                    subject_names,
                    task_context=task_context,
                )
            except RuntimeError as error:
                repaired = None
                rejected.append({'index': 0, 'reason': f'AI correction failed: {error}'})
            except AiTokenLimitExceeded as error:
                return self.write_json(error.payload, status=HTTPStatus.TOO_MANY_REQUESTS)
            if repaired is not None:
                reply, actions, rejected = repaired
        return self.write_json({
            'ok': True,
            'reply': reply[:2000],
            'actions': actions,
            'rejectedActions': rejected,
        })

    def handle_ai_chat_stream(self):
        user = self.require_user()
        if not user:
            return
        if not deepseek_api_key():
            return self.write_json(
                {'error': 'DeepSeek API key is not configured'},
                status=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        payload = self.read_json_body()
        if payload is None:
            return
        message = str(payload.get('message', '') or '').strip()
        if not message:
            return self.write_json({'error': 'message is required'}, status=HTTPStatus.BAD_REQUEST)
        if len(message) > 2000:
            return self.write_json({'error': 'message is too long'}, status=HTTPStatus.BAD_REQUEST)
        try:
            self.ensure_ai_token_available(int(user['id']))
        except AiTokenLimitExceeded as error:
            return self.write_json(error.payload, status=HTTPStatus.TOO_MANY_REQUESTS)

        client_now = str(payload.get('clientNow', '') or '').strip()[:40]
        timezone_name = str(payload.get('timezone', 'Asia/Shanghai') or 'Asia/Shanghai').strip()[:64]
        history = self.normalize_ai_history(payload.get('history'))
        with get_db() as conn:
            tasks, task_context = self.fetch_ai_context_tasks_for_user(conn, int(user['id']))
            subject_names = enabled_subject_names(get_subject_template_for_user(conn, int(user['id'])))

        messages = self.build_ai_stream_messages(
            message,
            history,
            tasks,
            client_now,
            timezone_name,
            subject_names,
            task_context=task_context,
        )
        self.start_sse()
        full_content = ''
        visible_buffer = ''
        hidden_actions = False
        marker = '<AI_ACTIONS_JSON>'
        keep_tail = len(marker) - 1

        try:
            for chunk in self.stream_deepseek_chat(messages):
                full_content += chunk
                if hidden_actions:
                    continue
                visible_buffer += chunk
                marker_index = visible_buffer.find(marker)
                if marker_index != -1:
                    text = visible_buffer[:marker_index]
                    if text:
                        self.write_sse_event('delta', {'text': text})
                    visible_buffer = ''
                    hidden_actions = True
                    continue
                safe_length = max(0, len(visible_buffer) - keep_tail)
                if safe_length:
                    text = visible_buffer[:safe_length]
                    visible_buffer = visible_buffer[safe_length:]
                    self.write_sse_event('delta', {'text': text})

            if visible_buffer and not hidden_actions:
                self.write_sse_event('delta', {'text': visible_buffer})

            self.record_ai_usage_for_user(
                int(user['id']),
                'chat_stream',
                getattr(self, '_last_deepseek_stream_usage', None),
            )
            reply, raw_actions, parse_error = parse_ai_stream_content(full_content)
            visible_tasks = tasks
            actions, rejected = normalize_ai_actions(raw_actions, visible_tasks, subject_names)
            if parse_error:
                rejected.append({'index': 0, 'reason': parse_error})
            if not reply:
                reply = '我整理好了可审批的操作。' if actions else '我还需要更明确的信息。'
            if rejected:
                try:
                    repaired = self.repair_ai_response(
                        int(user['id']),
                        message,
                        history,
                        tasks,
                        client_now,
                        timezone_name,
                        reply,
                        raw_actions,
                        rejected,
                        subject_names,
                        task_context=task_context,
                    )
                except RuntimeError as error:
                    repaired = None
                    rejected.append({'index': 0, 'reason': f'AI correction failed: {error}'})
                except AiTokenLimitExceeded as error:
                    self.write_sse_event('error', error.payload)
                    return
                if repaired is not None:
                    reply, actions, rejected = repaired
            self.write_sse_event('done', {
                'reply': reply[:2000],
                'actions': actions,
                'rejectedActions': rejected,
            })
        except ValueError:
            self.write_sse_event('error', {'error': 'DeepSeek API key is not configured'})
        except RuntimeError as error:
            self.write_sse_event('error', {'error': 'DeepSeek request failed', 'message': str(error)})
        finally:
            self.close_connection = True

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
        if 'completed' in payload and not isinstance(payload.get('completed'), bool):
            return None, {'error': 'completed must be a boolean'}
        task = normalize_task({**payload, 'id': task_id or payload.get('id', '')}, user_id)
        if not task['id']:
            task['id'] = f"task-{int(time.time() * 1000)}-{secrets.token_hex(4)}"
        if len(task['id']) > MAX_TASK_ID_LENGTH:
            return None, {'error': 'task id is too long'}
        if not task['title']:
            return None, {'error': 'task title is required'}
        if len(task['title']) > MAX_TASK_TITLE_LENGTH:
            return None, {'error': 'task title is too long'}
        if not task['subject']:
            return None, {'error': 'subject is required'}
        if len(task['subject']) > MAX_TASK_SUBJECT_LENGTH:
            return None, {'error': 'subject is too long'}
        if not is_valid_task_due_at(task['dueAt']):
            return None, {'error': 'dueAt must be empty or YYYY-MM-DDTHH:mm:ss'}
        if len(task['note']) > MAX_TASK_NOTE_LENGTH:
            return None, {'error': 'note is too long'}
        if task['priority'] not in {'high', 'medium', 'low'}:
            return None, {'error': 'invalid priority'}
        if task['pool'] not in {'todo', 'arrangement', 'habit', 'schedule'}:
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

    def normalize_habit_payload(self, payload: dict, user_id: int, habit_id: str | None = None):
        if not isinstance(payload, dict):
            return None, {'error': 'habit must be an object'}
        if 'active' in payload and not isinstance(payload.get('active'), bool):
            return None, {'error': 'active must be a boolean'}
        title = str(payload.get('title', '')).strip()
        subject = str(payload.get('subject', '')).strip()
        priority = str(payload.get('priority', 'medium')).strip() or 'medium'
        note = str(payload.get('note', '') or '').strip()
        raw_weekdays = payload.get('weekdays', [])
        slot_key_base = str(payload.get('slotKeyBase', '')).strip()
        slot_label = str(payload.get('slotLabel', '')).strip()
        slot_start = normalize_time_text(str(payload.get('slotStart', '')).strip())
        slot_end = normalize_time_text(str(payload.get('slotEnd', '')).strip())
        start_date = str(payload.get('startDate', '')).strip()
        end_date = str(payload.get('endDate', '') or '').strip()
        active = bool(payload.get('active', True))
        try:
            duration_minutes = int(payload.get('durationMinutes'))
        except Exception:
            return None, {'error': 'durationMinutes must be an integer'}

        if not title:
            return None, {'error': 'habit title is required'}
        if len(title) > 120:
            return None, {'error': 'habit title is too long'}
        if len(subject) > 40:
            return None, {'error': 'subject is too long'}
        if priority not in {'high', 'medium', 'low'}:
            return None, {'error': 'invalid priority'}
        if len(note) > 500:
            return None, {'error': 'note is too long'}
        if not isinstance(raw_weekdays, list):
            return None, {'error': 'weekdays must be a list'}
        weekdays = []
        for raw in raw_weekdays:
            try:
                weekday = int(raw)
            except Exception:
                return None, {'error': 'invalid weekday'}
            if weekday < 0 or weekday > 6:
                return None, {'error': 'invalid weekday'}
            if weekday not in weekdays:
                weekdays.append(weekday)
        weekdays.sort()
        if not weekdays:
            return None, {'error': 'at least one weekday is required'}
        if not slot_key_base or not slot_label or not slot_start or not slot_end:
            return None, {'error': 'slotKeyBase, slotLabel, slotStart and slotEnd are required'}
        slot_capacity = minutes_between(slot_start, slot_end)
        if slot_capacity <= 0:
            return None, {'error': 'invalid slot time range'}
        if duration_minutes <= 0:
            return None, {'error': 'durationMinutes must be positive'}
        if duration_minutes > slot_capacity:
            return None, {'error': 'duration exceeds slot capacity'}
        if not is_valid_date_key(start_date):
            return None, {'error': 'startDate is required'}
        if end_date and (not is_valid_date_key(end_date) or end_date < start_date):
            return None, {'error': 'endDate must be empty or later than startDate'}

        return {
            'id': habit_id or str(payload.get('id', '')).strip() or f"habit-{int(time.time() * 1000)}-{secrets.token_hex(4)}",
            'userId': user_id,
            'title': title,
            'subject': subject,
            'priority': priority,
            'note': note,
            'weekdays': weekdays,
            'slotKeyBase': slot_key_base,
            'slotLabel': slot_label[:40],
            'slotStart': slot_start,
            'slotEnd': slot_end,
            'durationMinutes': duration_minutes,
            'startDate': start_date,
            'endDate': end_date,
            'active': active,
        }, None

    def create_habit_task(self, conn: sqlite3.Connection, habit: dict) -> str:
        task_id = f"habit-task-{int(time.time() * 1000)}-{secrets.token_hex(4)}"
        now = now_iso()
        conn.execute(
            '''
            INSERT INTO tasks (id, user_id, title, subject, due_at, pool, priority, note, completed, created_at, updated_at)
            VALUES (?, ?, ?, ?, '', 'habit', ?, ?, 0, ?, ?)
            ''',
            (
                task_id,
                habit['userId'],
                habit['title'],
                habit['subject'],
                habit['priority'],
                habit['note'],
                now,
                now,
            ),
        )
        return task_id

    def habit_date_keys(self, habit: sqlite3.Row, window_start: str, window_end: str) -> list[str]:
        start = max(str(habit['start_date']), window_start)
        end = str(habit['end_date'] or '') or window_end
        end = min(end, window_end)
        if end < start:
            return []
        try:
            weekdays = {str(int(value)) for value in json.loads(habit['weekdays_json'] or '[]')}
        except Exception:
            weekdays = set()
        dates = []
        current = start
        while current <= end:
            if weekday_for_date(current) in weekdays:
                dates.append(current)
            current = add_days_key(current, 1)
        return dates

    def sync_habit_instances(
        self,
        conn: sqlite3.Connection,
        user_id: int,
        habit_ids: list[str] | None = None,
        window_start: str | None = None,
        window_end: str | None = None,
        reset_future_uncompleted: bool = False,
        strict: bool = False,
    ) -> list[dict]:
        today = today_key()
        window_start, window_end = clamp_habit_sync_window(window_start or today, window_end)
        params: list = [user_id]
        id_filter = ''
        if habit_ids:
            placeholders = ','.join('?' for _ in habit_ids)
            id_filter = f'AND habits.id IN ({placeholders})'
            params.extend(habit_ids)
        habits = conn.execute(
            f'''
            SELECT habits.*
            FROM habits
            WHERE user_id = ? AND active = 1 AND archived = 0 {id_filter}
            ORDER BY created_at ASC
            ''',
            params,
        ).fetchall()

        conflicts = []
        inserts = []
        for habit in habits:
            for date_key in self.habit_date_keys(habit, window_start, window_end):
                existing = conn.execute(
                    '''
                    SELECT id, completed FROM schedule_items
                    WHERE user_id = ? AND habit_id = ? AND schedule_date = ?
                    LIMIT 1
                    ''',
                    (user_id, habit['id'], date_key),
                ).fetchone()
                if existing and not (reset_future_uncompleted and not bool(existing['completed']) and date_key >= today):
                    continue
                target_slot_key = f"{date_key}-{habit['slot_key_base']}"
                slots = effective_slots_for_date(conn, user_id, date_key)
                slot = next((item for item in slots if slot_key(date_key, item) == target_slot_key), None)
                if not slot or slot['start'] != habit['slot_start'] or slot['end'] != habit['slot_end']:
                    conflicts.append({'habitId': habit['id'], 'date': date_key, 'reason': 'slot missing'})
                    continue
                used = conn.execute(
                    '''
                    SELECT COALESCE(SUM(duration_minutes), 0)
                    FROM schedule_items
                    WHERE user_id = ? AND schedule_date = ? AND slot_key = ?
                      AND NOT (habit_id = ? AND completed = 0 AND schedule_date >= ?)
                    ''',
                    (user_id, date_key, target_slot_key, habit['id'], today),
                ).fetchone()[0]
                if int(used or 0) + int(habit['duration_minutes']) > minutes_between(habit['slot_start'], habit['slot_end']):
                    conflicts.append({'habitId': habit['id'], 'date': date_key, 'reason': 'capacity exceeded'})
                    continue
                inserts.append((habit, date_key, target_slot_key))

        if conflicts and strict:
            return conflicts

        if reset_future_uncompleted and habit_ids:
            placeholders = ','.join('?' for _ in habit_ids)
            conn.execute(
                f'''
                DELETE FROM schedule_items
                WHERE user_id = ? AND habit_id IN ({placeholders}) AND schedule_date >= ? AND completed = 0
                ''',
                [user_id, *habit_ids, today],
            )

        now = now_iso()
        for habit, date_key, target_slot_key in inserts:
            existing = conn.execute(
                '''
                SELECT id FROM schedule_items
                WHERE user_id = ? AND habit_id = ? AND schedule_date = ?
                LIMIT 1
                ''',
                (user_id, habit['id'], date_key),
            ).fetchone()
            if existing:
                continue
            sort_order = float(conn.execute(
                '''
                SELECT COALESCE(MAX(sort_order), 0) + 1024 FROM schedule_items
                WHERE user_id = ? AND schedule_date = ? AND slot_key = ?
                ''',
                (user_id, date_key, target_slot_key),
            ).fetchone()[0])
            item_id = f"schedule-{int(time.time() * 1000)}-{secrets.token_hex(4)}"
            conn.execute(
                '''
                INSERT INTO schedule_items
                (id, user_id, task_id, habit_id, schedule_date, slot_key, slot_label, slot_start, slot_end,
                 duration_minutes, sort_order, note, completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', 0, ?, ?)
                ''',
                (
                    item_id,
                    user_id,
                    habit['task_id'],
                    habit['id'],
                    date_key,
                    target_slot_key,
                    habit['slot_label'],
                    habit['slot_start'],
                    habit['slot_end'],
                    habit['duration_minutes'],
                    sort_order,
                    now,
                    now,
                ),
            )
        return conflicts

    def habit_sync_window_from_request(self) -> tuple[str, str]:
        query = parse_qs(urlparse(self.path).query)
        start = str((query.get('from') or [''])[0]).strip()
        end = str((query.get('to') or [''])[0]).strip()
        return clamp_habit_sync_window(start, end)

    def handle_list_habits(self):
        user = self.current_user()
        if not user:
            return self.write_json({'habits': [], 'readOnly': True})
        with get_db() as conn:
            habits = self.fetch_habits_for_user(conn, int(user['id']))
        return self.write_json({'habits': habits, 'readOnly': False})

    def handle_create_habit(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        habit, error = self.normalize_habit_payload(payload, int(user['id']))
        if error:
            return self.write_json(error, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            task_id = self.create_habit_task(conn, habit)
            now = now_iso()
            conn.execute(
                '''
                INSERT INTO habits
                (id, user_id, task_id, weekdays_json, slot_key_base, slot_label, slot_start, slot_end,
                 duration_minutes, start_date, end_date, active, archived, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                ''',
                (
                    habit['id'], user['id'], task_id, json.dumps(habit['weekdays']),
                    habit['slotKeyBase'], habit['slotLabel'], habit['slotStart'], habit['slotEnd'],
                    habit['durationMinutes'], habit['startDate'], habit['endDate'], 1 if habit['active'] else 0,
                    now, now,
                ),
            )
            sync_to = habit['endDate'] or add_days_key(today_key(), HABIT_SYNC_FUTURE_DAYS)
            conflicts = self.sync_habit_instances(
                conn,
                int(user['id']),
                [habit['id']],
                today_key(),
                sync_to,
                strict=True,
            )
            if conflicts:
                conn.rollback()
                return self.write_json({'error': 'habit schedule conflict', 'conflicts': conflicts}, status=HTTPStatus.CONFLICT)
            self.log_operation(conn, int(user['id']), int(user['id']), 'habit.create', 'habit', habit['id'], {'title': habit['title']})
            conn.commit()
            rows = self.fetch_habits_for_user(conn, int(user['id']))
        return self.write_json({'ok': True, 'habit': next(item for item in rows if item['id'] == habit['id'])}, status=HTTPStatus.CREATED)

    def handle_update_habit(self, habit_id: str):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        habit, error = self.normalize_habit_payload(payload, int(user['id']), habit_id=habit_id)
        if error:
            return self.write_json(error, status=HTTPStatus.BAD_REQUEST)
        with get_db() as conn:
            existing = conn.execute('SELECT * FROM habits WHERE id = ? AND user_id = ? AND archived = 0', (habit_id, user['id'])).fetchone()
            if not existing:
                return self.write_json({'error': 'habit not found'}, status=HTTPStatus.NOT_FOUND)
            task_id = self.create_habit_task(conn, habit)
            now = now_iso()
            conn.execute(
                '''
                UPDATE habits
                SET task_id = ?, weekdays_json = ?, slot_key_base = ?, slot_label = ?, slot_start = ?, slot_end = ?,
                    duration_minutes = ?, start_date = ?, end_date = ?, active = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                ''',
                (
                    task_id, json.dumps(habit['weekdays']), habit['slotKeyBase'], habit['slotLabel'],
                    habit['slotStart'], habit['slotEnd'], habit['durationMinutes'], habit['startDate'],
                    habit['endDate'], 1 if habit['active'] else 0, now, habit_id, user['id'],
                ),
            )
            sync_to = habit['endDate'] or add_days_key(today_key(), HABIT_SYNC_FUTURE_DAYS)
            conflicts = self.sync_habit_instances(
                conn,
                int(user['id']),
                [habit_id],
                today_key(),
                sync_to,
                reset_future_uncompleted=True,
                strict=True,
            )
            if conflicts:
                conn.rollback()
                return self.write_json({'error': 'habit schedule conflict', 'conflicts': conflicts}, status=HTTPStatus.CONFLICT)
            self.log_operation(conn, int(user['id']), int(user['id']), 'habit.update', 'habit', habit_id, {'title': habit['title']})
            conn.commit()
            rows = self.fetch_habits_for_user(conn, int(user['id']))
        return self.write_json({'ok': True, 'habit': next(item for item in rows if item['id'] == habit_id)})

    def handle_delete_habit(self, habit_id: str):
        user = self.require_user()
        if not user:
            return
        with get_db() as conn:
            existing = conn.execute('SELECT id FROM habits WHERE id = ? AND user_id = ? AND archived = 0', (habit_id, user['id'])).fetchone()
            if not existing:
                return self.write_json({'error': 'habit not found'}, status=HTTPStatus.NOT_FOUND)
            now = now_iso()
            conn.execute('UPDATE habits SET archived = 1, active = 0, updated_at = ? WHERE id = ? AND user_id = ?', (now, habit_id, user['id']))
            conn.execute('DELETE FROM schedule_items WHERE user_id = ? AND habit_id = ? AND schedule_date >= ?', (user['id'], habit_id, today_key()))
            self.log_operation(conn, int(user['id']), int(user['id']), 'habit.delete', 'habit', habit_id, {})
            conn.commit()
        return self.write_json({'ok': True})

    def handle_list_schedule_items(self):
        user = self.current_user()
        if not user:
            return self.write_json({'items': [], 'readOnly': True})

        with get_db() as conn:
            sync_start, sync_end = self.habit_sync_window_from_request()
            sync_conflicts = self.sync_habit_instances(conn, int(user['id']), window_start=sync_start, window_end=sync_end)
            conn.commit()
            items = self.fetch_schedule_items_for_user(conn, int(user['id']))
        return self.write_json({'items': items, 'readOnly': False, 'habitSyncConflicts': sync_conflicts})


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
        if error:
            return self.write_json({'error': error}, status=HTTPStatus.BAD_REQUEST)
        if not is_valid_date_key(effective_from):
            return self.write_json({'error': 'effectiveFrom must be a valid date'}, status=HTTPStatus.BAD_REQUEST)

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
        if not is_valid_date_key(date_key):
            return self.write_json({'error': 'invalid schedule date'}, status=HTTPStatus.BAD_REQUEST)
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
        if not is_valid_date_key(date_key):
            return self.write_json({'error': 'invalid schedule date'}, status=HTTPStatus.BAD_REQUEST)
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

    def validate_schedule_payload(
        self,
        conn: sqlite3.Connection,
        payload: dict,
        user_id: int,
        existing_id: str | None = None,
        enforce_slot_exists: bool = True,
    ):
        """Validate schedule item edits and enforce per-slot capacity."""
        task_id = str(payload.get('taskId', '')).strip()
        schedule_date = str(payload.get('date', '')).strip()
        slot_key = str(payload.get('slotKey', '')).strip()
        slot_label = str(payload.get('slotLabel', '')).strip()
        slot_start = normalize_time_text(str(payload.get('slotStart', '')).strip())
        slot_end = normalize_time_text(str(payload.get('slotEnd', '')).strip())
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
            if not math.isfinite(sort_order):
                return None, {'error': 'sortOrder must be a finite number'}

        if not task_id or not schedule_date or not slot_key or not slot_start or not slot_end:
            return None, {'error': 'taskId, date, slotKey, slotStart and slotEnd are required'}
        if not is_valid_date_key(schedule_date):
            return None, {'error': 'date must be a valid YYYY-MM-DD date'}
        if len(slot_label) > 40:
            return None, {'error': 'slotLabel must be at most 40 characters'}
        if duration_minutes <= 0:
            return None, {'error': 'durationMinutes must be positive'}
        slot_capacity = minutes_between(slot_start, slot_end)
        if slot_capacity <= 0:
            return None, {'error': 'invalid slot time range'}
        if duration_minutes > slot_capacity:
            return None, {'error': 'duration exceeds slot capacity'}
        if len(note) > 500:
            return None, {'error': 'note is too long'}
        if enforce_slot_exists and not matching_effective_slot(conn, user_id, schedule_date, slot_key, slot_start, slot_end):
            return None, {'error': 'time slot does not exist for this date'}

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
        item_id = f"schedule-{int(time.time() * 1000)}-{secrets.token_hex(4)}"
        with get_db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            item, error = self.validate_schedule_payload(conn, payload, int(user['id']))
            if error:
                return self.write_json(error, status=HTTPStatus.BAD_REQUEST)
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
            conn.execute('BEGIN IMMEDIATE')
            existing = conn.execute('SELECT * FROM schedule_items WHERE id = ? AND user_id = ?', (item_id, user['id'])).fetchone()
            if not existing:
                return self.write_json({'error': 'schedule item not found'}, status=HTTPStatus.NOT_FOUND)
            if existing['habit_id']:
                locked_fields = {
                    'date': existing['schedule_date'],
                    'slotKey': existing['slot_key'],
                    'slotLabel': existing['slot_label'],
                    'slotStart': existing['slot_start'],
                    'slotEnd': existing['slot_end'],
                    'durationMinutes': existing['duration_minutes'],
                }
                for key, current_value in locked_fields.items():
                    if key in payload and str(payload.get(key)) != str(current_value):
                        return self.write_json({'error': 'habit schedule items can only be completed from the daily board'}, status=HTTPStatus.BAD_REQUEST)

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

            schedule_changed = any(
                str(merged[key]) != str(current_value)
                for key, current_value in {
                    'date': existing['schedule_date'],
                    'slotKey': existing['slot_key'],
                    'slotStart': existing['slot_start'],
                    'slotEnd': existing['slot_end'],
                    'durationMinutes': existing['duration_minutes'],
                    'sortOrder': existing['sort_order'],
                }.items()
            )
            if schedule_changed:
                item, error = self.validate_schedule_payload(
                    conn,
                    merged,
                    int(user['id']),
                    existing_id=item_id,
                    enforce_slot_exists=True,
                )
                if error:
                    return self.write_json(error, status=HTTPStatus.BAD_REQUEST)
                if item['sortOrder'] is None:
                    item['sortOrder'] = existing['sort_order']
            else:
                note = str(merged.get('note', '') or '').strip()
                if len(note) > 500:
                    return self.write_json({'error': 'note is too long'}, status=HTTPStatus.BAD_REQUEST)
                item = {
                    'taskId': existing['task_id'],
                    'date': existing['schedule_date'],
                    'slotKey': existing['slot_key'],
                    'slotLabel': existing['slot_label'],
                    'slotStart': existing['slot_start'],
                    'slotEnd': existing['slot_end'],
                    'durationMinutes': existing['duration_minutes'],
                    'sortOrder': existing['sort_order'],
                    'note': note,
                }
            if 'completed' in payload and not isinstance(payload.get('completed'), bool):
                return self.write_json({'error': 'completed must be a boolean'}, status=HTTPStatus.BAD_REQUEST)
            completed = bool(payload.get('completed')) if 'completed' in payload else bool(existing['completed'])
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
                '''
                SELECT schedule_items.task_id, schedule_items.habit_id, schedule_items.schedule_date,
                       schedule_items.slot_label, tasks.pool AS task_pool
                FROM schedule_items
                JOIN tasks ON tasks.id = schedule_items.task_id AND tasks.user_id = schedule_items.user_id
                WHERE schedule_items.id = ? AND schedule_items.user_id = ?
                ''',
                (item_id, user['id']),
            ).fetchone()
            if not existing:
                return self.write_json({'error': 'schedule item not found'}, status=HTTPStatus.NOT_FOUND)
            if existing['habit_id']:
                return self.write_json({'error': 'habit schedule items must be deleted from the habit'}, status=HTTPStatus.BAD_REQUEST)
            cursor = conn.execute('DELETE FROM schedule_items WHERE id = ? AND user_id = ?', (item_id, user['id']))
            if existing['task_pool'] == 'schedule':
                remaining = conn.execute(
                    'SELECT 1 FROM schedule_items WHERE user_id = ? AND task_id = ? LIMIT 1',
                    (user['id'], existing['task_id']),
                ).fetchone()
                if not remaining:
                    conn.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (existing['task_id'], user['id']))
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
            existing = conn.execute('SELECT id FROM users WHERE nickname = ? COLLATE NOCASE', (nickname,)).fetchone()
            if existing:
                return self.write_json({'error': 'nickname already exists'}, status=HTTPStatus.CONFLICT)
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
            user = conn.execute(
                'SELECT id, name, nickname, role, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
                (user_id,),
            ).fetchone()
        return self.issue_session_response(user)

    def handle_auth_login(self):
        payload = self.read_json_body()
        if payload is None:
            return
        nickname = str(payload.get('nickname', '')).strip()
        password = str(payload.get('password', ''))
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE nickname = ? COLLATE NOCASE', (nickname,)).fetchone()
            if not user or not verify_password(password, user['password_hash']):
                return self.write_json({'error': 'invalid nickname or password'}, status=HTTPStatus.UNAUTHORIZED)
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

    def handle_auth_update_avatar(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        filename = str(payload.get('filename', '')).strip()
        content_type = str(payload.get('contentType', '')).strip().lower()
        data = str(payload.get('data', '')).strip()
        if not filename or not content_type or not data:
            return self.write_json({'error': 'filename, contentType and data are required'}, status=HTTPStatus.BAD_REQUEST)
        if content_type not in AVATAR_CONTENT_TYPES:
            return self.write_json({'error': 'avatar must be a PNG, JPEG or WebP image'}, status=HTTPStatus.BAD_REQUEST)
        ext = filename.rpartition('.')[2].lower()
        if ext not in AVATAR_EXTENSIONS:
            return self.write_json({'error': 'avatar filename must end with png, jpg, jpeg or webp'}, status=HTTPStatus.BAD_REQUEST)
        if content_type == 'image/png' and ext != 'png':
            return self.write_json({'error': 'avatar extension does not match content type'}, status=HTTPStatus.BAD_REQUEST)
        if content_type == 'image/jpeg' and ext not in {'jpg', 'jpeg'}:
            return self.write_json({'error': 'avatar extension does not match content type'}, status=HTTPStatus.BAD_REQUEST)
        if content_type == 'image/webp' and ext != 'webp':
            return self.write_json({'error': 'avatar extension does not match content type'}, status=HTTPStatus.BAD_REQUEST)
        if data.startswith('data:') and ',' in data:
            data = data.split(',', 1)[1]
        try:
            raw = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError):
            return self.write_json({'error': 'avatar data must be valid base64'}, status=HTTPStatus.BAD_REQUEST)
        if not raw:
            return self.write_json({'error': 'avatar data is empty'}, status=HTTPStatus.BAD_REQUEST)
        if len(raw) > MAX_AVATAR_BYTES:
            return self.write_json({'error': 'avatar must be at most 2MB'}, status=HTTPStatus.BAD_REQUEST)
        if avatar_magic_type(raw) != content_type:
            return self.write_json({'error': 'avatar content does not match image type'}, status=HTTPStatus.BAD_REQUEST)

        stored_ext = AVATAR_CONTENT_TYPES[content_type]
        new_filename = f'user-{user["id"]}-{secrets.token_urlsafe(12)}.{stored_ext}'
        target_dir = avatar_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / new_filename
        old_avatar = row_value(user, 'avatar_file', '')
        updated_at = now_iso()
        try:
            target_path.write_bytes(raw)
            with get_db() as conn:
                current = conn.execute(
                    'SELECT id, name, nickname, role, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
                    (user['id'],),
                ).fetchone()
                if not current:
                    cleanup_avatar_file(new_filename)
                    return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
                old_avatar = current['avatar_file']
                conn.execute(
                    'UPDATE users SET avatar_file = ?, avatar_updated_at = ? WHERE id = ?',
                    (new_filename, updated_at, user['id']),
                )
                self.log_operation(
                    conn,
                    int(user['id']),
                    int(user['id']),
                    'user.avatar.update',
                    'user',
                    str(user['id']),
                    {'filename': new_filename},
                )
                conn.commit()
                updated = conn.execute(
                    'SELECT id, name, nickname, role, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
                    (user['id'],),
                ).fetchone()
        except OSError:
            cleanup_avatar_file(new_filename)
            return self.write_json({'error': 'avatar could not be saved'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        cleanup_avatar_file(old_avatar)
        return self.write_json({'ok': True, 'user': public_user(updated)})

    def handle_auth_delete_avatar(self):
        user = self.require_user()
        if not user:
            return
        old_avatar = ''
        with get_db() as conn:
            current = conn.execute(
                'SELECT id, name, nickname, role, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
                (user['id'],),
            ).fetchone()
            if not current:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            old_avatar = current['avatar_file']
            conn.execute(
                "UPDATE users SET avatar_file = '', avatar_updated_at = '' WHERE id = ?",
                (user['id'],),
            )
            self.log_operation(
                conn,
                int(user['id']),
                int(user['id']),
                'user.avatar.delete',
                'user',
                str(user['id']),
                {'filename': old_avatar},
            )
            conn.commit()
            updated = conn.execute(
                'SELECT id, name, nickname, role, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
                (user['id'],),
            ).fetchone()
        cleanup_avatar_file(old_avatar)
        return self.write_json({'ok': True, 'user': public_user(updated)})

    def handle_auth_update_avatar_color(self):
        user = self.require_user()
        if not user:
            return
        payload = self.read_json_body()
        if payload is None:
            return
        raw_color = str(payload.get('color', '')).strip().lower()
        if not is_valid_avatar_color(raw_color):
            return self.write_json({'error': 'avatar color is not allowed'}, status=HTTPStatus.BAD_REQUEST)
        color = raw_color
        with get_db() as conn:
            current = conn.execute(
                'SELECT id, name, nickname, role, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
                (user['id'],),
            ).fetchone()
            if not current:
                return self.write_json({'error': 'user not found'}, status=HTTPStatus.NOT_FOUND)
            if normalize_avatar_color(current['avatar_color']) != color:
                conn.execute('UPDATE users SET avatar_color = ? WHERE id = ?', (color, user['id']))
                self.log_operation(
                    conn,
                    int(user['id']),
                    int(user['id']),
                    'user.avatar_color.update',
                    'user',
                    str(user['id']),
                    {'color': color},
                )
                conn.commit()
            updated = conn.execute(
                'SELECT id, name, nickname, role, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
                (user['id'],),
            ).fetchone()
        return self.write_json({'ok': True, 'user': public_user(updated)})

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
                'SELECT id FROM users WHERE nickname = ? COLLATE NOCASE AND id != ?',
                (nickname, user['id']),
            ).fetchone()
            if existing:
                return self.write_json({'error': 'nickname already exists', 'message': '这个昵称已被使用。'}, status=HTTPStatus.CONFLICT)
            current = conn.execute(
                'SELECT id, name, nickname, role, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
                (user['id'],),
            ).fetchone()
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
            updated = conn.execute(
                'SELECT id, name, nickname, role, avatar_file, avatar_updated_at, avatar_color FROM users WHERE id = ?',
                (user['id'],),
            ).fetchone()
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
        if length < 0:
            return self.write_json({'error': 'invalid content length'}, status=HTTPStatus.BAD_REQUEST)
        if length > MAX_JSON_BODY_BYTES:
            self.close_connection = True
            return self.write_json(
                {'error': 'request body too large', 'maxBytes': MAX_JSON_BODY_BYTES},
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
        raw = self.rfile.read(length) if length > 0 else b''
        try:
            payload = json.loads(raw.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            self.write_json({'error': 'invalid json'}, status=HTTPStatus.BAD_REQUEST)
            return None
        if not isinstance(payload, dict):
            self.write_json({'error': 'json body must be an object'}, status=HTTPStatus.BAD_REQUEST)
            return None
        return payload

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('X-Frame-Options', 'DENY')
        super().end_headers()

    def write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def start_sse(self):
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store')
        self.send_header('X-Accel-Buffering', 'no')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(b': connected\n\n')
        self.wfile.flush()

    def write_sse_event(self, event: str, payload: dict):
        body = (
            f'event: {event}\n'
            f'data: {json.dumps(payload, ensure_ascii=False)}\n\n'
        ).encode('utf-8')
        self.wfile.write(body)
        self.wfile.flush()

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
