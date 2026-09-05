#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def apply_mapping(database: Path, mapping_file: Path) -> dict[str, int]:
    payload = json.loads(mapping_file.read_text(encoding='utf-8'))
    todo_mappings = [
        item for item in payload.get('mappings', []) if item.get('source_app') == 'todo'
    ]
    mapping_by_id: dict[int, str] = {}
    for item in todo_mappings:
        user_id = int(item['source_user_id'])
        sub = str(item['central_sub']).strip()
        if not sub or user_id in mapping_by_id:
            raise ValueError('TodoList mapping contains an empty sub or duplicate local user ID')
        mapping_by_id[user_id] = sub
    if len(set(mapping_by_id.values())) != len(mapping_by_id):
        raise ValueError(
            'Multiple TodoList users map to one central sub; merge their local business data first'
        )

    connection = sqlite3.connect(database)
    try:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('BEGIN IMMEDIATE')
        columns = {row[1] for row in connection.execute('PRAGMA table_info(users)')}
        if 'auth_sub' not in columns:
            connection.execute('ALTER TABLE users ADD COLUMN auth_sub TEXT')
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS archived_password_credentials (
                user_id INTEGER PRIMARY KEY,
                password_hash TEXT NOT NULL,
                archived_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        local_ids = {int(row[0]) for row in connection.execute('SELECT id FROM users')}
        if set(mapping_by_id) != local_ids:
            missing = sorted(local_ids - set(mapping_by_id))
            unknown = sorted(set(mapping_by_id) - local_ids)
            raise ValueError(f'mapping must cover every local user; missing={missing}, unknown={unknown}')
        timestamp = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        archived = 0
        for user_id, sub in mapping_by_id.items():
            row = connection.execute(
                'SELECT password_hash, auth_sub FROM users WHERE id = ?', (user_id,)
            ).fetchone()
            if row[0]:
                connection.execute(
                    '''
                    INSERT OR IGNORE INTO archived_password_credentials
                    (user_id, password_hash, archived_at) VALUES (?, ?, ?)
                    ''',
                    (user_id, row[0], timestamp),
                )
                archived += 1
            if row[1] and row[1] != sub:
                raise ValueError(f'user {user_id} is already linked to a different central sub')
            connection.execute(
                "UPDATE users SET auth_sub = ?, password_hash = '' WHERE id = ?", (sub, user_id)
            )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_auth_sub ON users(auth_sub) "
            "WHERE auth_sub IS NOT NULL AND auth_sub != ''"
        )
        connection.execute('DELETE FROM sessions')
        connection.commit()
        return {'mapped': len(mapping_by_id), 'passwords_archived': archived}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description='Apply a NetHub Accounts mapping to TodoList')
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    args = parser.parse_args()
    result = apply_mapping(args.database, args.mapping)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
