#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def grant_admin(database: Path, auth_sub: str) -> str:
    normalized_sub = auth_sub.strip()
    if not normalized_sub:
        raise ValueError('auth sub must not be empty')

    with sqlite3.connect(database) as connection:
        connection.execute('BEGIN IMMEDIATE')
        row = connection.execute(
            'SELECT id, nickname, role FROM users WHERE auth_sub = ?', (normalized_sub,)
        ).fetchone()
        if row is None:
            raise ValueError(
                'no local member has this auth sub; sign in once or apply the migration mapping first'
            )
        connection.execute('UPDATE users SET role = ? WHERE id = ?', ('admin', row[0]))
        connection.commit()
        return str(row[1])


def main() -> None:
    parser = argparse.ArgumentParser(description='Grant TodoList admin role by central auth sub')
    parser.add_argument('--database', type=Path, default=Path('data/todo-list.db'))
    parser.add_argument('--auth-sub', required=True)
    args = parser.parse_args()
    nickname = grant_admin(args.database, args.auth_sub)
    print(f'admin granted: {nickname}')


if __name__ == '__main__':
    main()
