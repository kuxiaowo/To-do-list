"""Database backends used by the To-do service.

The D1 backend deliberately exposes a small sqlite3-like facade so existing
handlers can be migrated incrementally.  It never opens a local database.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Sequence


class D1Error(RuntimeError):
    """An error returned by the D1 gateway."""


class D1Row(dict):
    """Mapping row compatible with the sqlite3.Row operations used by views."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class D1Cursor:
    def __init__(self, result: dict):
        self._rows = [D1Row(row) if isinstance(row, dict) else row for row in result.get('rows', [])]
        meta = result.get('meta') or {}
        self.rowcount = int(meta.get('changes', result.get('changes', -1)) or 0)
        self.lastrowid = meta.get('last_row_id', result.get('last_row_id'))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def __iter__(self):
        return iter(self._rows)


class D1GatewayConnection:
    """sqlite3.Connection-shaped client for a private D1 gateway."""

    def __init__(self, url: str, secret: str, *, timeout: float = 15.0, clock=time.time):
        self.url = url.rstrip('/') + '/internal/db'
        self.secret = secret.encode('utf-8')
        self.timeout = timeout
        self.clock = clock
        self.row_factory = None
        self._closed = False

    def _request(self, statements: list[dict], mode: str = 'single') -> list[dict]:
        if self._closed:
            raise D1Error('database connection is closed')
        request_id = str(uuid.uuid4())
        timestamp = str(int(self.clock()))
        payload = json.dumps({
            'requestId': request_id,
            'timestamp': int(timestamp),
            'mode': mode,
            'statements': statements,
        }, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        digest = hashlib.sha256(payload).hexdigest()
        message = f'v1\nPOST\n/internal/db\n{request_id}\n{timestamp}\n{digest}'.encode()
        signature = hmac.new(self.secret, message, hashlib.sha256).hexdigest()
        request = urllib.request.Request(self.url, data=payload, method='POST', headers={
            'Content-Type': 'application/json',
            'User-Agent': 'NetHub-D1-Client/1.0',
            'X-DB-Request-ID': request_id,
            'X-DB-Timestamp': timestamp,
            'X-DB-Signature': signature,
        })
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            try:
                error_body = json.loads(exc.read().decode('utf-8'))
            except (OSError, UnicodeDecodeError, ValueError):
                error_body = {}
            message = str(error_body.get('message') or error_body.get('error') or exc.reason)
            if exc.code == 409 or error_body.get('error') == 'database_integrity_error':
                raise sqlite3.IntegrityError(message) from exc
            raise D1Error(f'D1 gateway request failed ({exc.code}): {message}') from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise D1Error(f'D1 gateway request failed: {exc}') from exc
        if not isinstance(body, dict) or body.get('error'):
            raise D1Error(str(body.get('error', 'invalid D1 gateway response')))
        results = body.get('results')
        if not isinstance(results, list) or len(results) != len(statements) or not all(isinstance(item, dict) for item in results):
            raise D1Error('invalid D1 gateway response: results must be a list')
        return results

    def execute(self, sql: str, params: Sequence = ()) -> D1Cursor:
        normalized = sql.strip().upper()
        # Never pretend a D1 request opened a connection-level transaction.
        if normalized in {'BEGIN', 'BEGIN IMMEDIATE', 'COMMIT', 'ROLLBACK'}:
            raise D1Error('D1 transaction controls are unsupported; use batch() for atomic writes')
        result = self._request([{'sql': sql, 'params': list(params)}])[0]
        return D1Cursor(result)

    def batch(self, statements: Sequence[tuple[str, Sequence] | dict]) -> list[D1Cursor]:
        payload = []
        for statement in statements:
            if isinstance(statement, dict):
                payload.append(statement)
            else:
                sql, params = statement
                payload.append({'sql': sql, 'params': list(params)})
        return [D1Cursor(item) for item in self._request(payload, mode='batch')]

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence]):
        return self.batch([(sql, params) for params in seq_of_params])[-1] if seq_of_params else D1Cursor({})

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


def create_d1_connection(url: str | None, secret: str | None, *, timeout: float = 15.0):
    if not url or not secret:
        raise RuntimeError('TODO_DB_BACKEND=d1 requires TODO_D1_GATEWAY_URL and TODO_D1_GATEWAY_SECRET')
    return D1GatewayConnection(url, secret, timeout=timeout)
