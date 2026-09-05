import http.client
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from joserfc import jwt
from joserfc.jwk import import_key

import server
from oidc_client import (
    OIDCError,
    OIDCIdentity,
    _validate_id_token,
    validate_logout_token,
)
from scripts.apply_accounts_mapping import apply_mapping
from scripts.grant_admin import grant_admin


def signing_material():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    key = import_key(pem, 'RSA', {'kid': 'test-key'})
    return key, {'keys': [key.as_dict(private=False)]}


class OIDCAuthTests(unittest.TestCase):
    def setUp(self):
        self.originals = {
            'data_dir': server.DATA_DIR,
            'db_path': server.DB_PATH,
            'legacy': server.LEGACY_AUTH_ENABLED,
            'secret': server.OIDC_CLIENT_SECRET,
            'secure': server.SESSION_COOKIE_SECURE,
        }
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        server.DATA_DIR = Path(self.temp_dir.name)
        server.DB_PATH = server.DATA_DIR / 'todo-list.db'
        server.LEGACY_AUTH_ENABLED = False
        server.OIDC_CLIENT_SECRET = 'test-client-secret'
        server.SESSION_COOKIE_SECURE = False
        server.init_db()
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.TodoHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        server.DATA_DIR = self.originals['data_dir']
        server.DB_PATH = self.originals['db_path']
        server.LEGACY_AUTH_ENABLED = self.originals['legacy']
        server.OIDC_CLIENT_SECRET = self.originals['secret']
        server.SESSION_COOKIE_SECURE = self.originals['secure']
        self.temp_dir.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.httpd.server_address[1], timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        result = (response.status, response.getheaders(), payload)
        connection.close()
        return result

    @staticmethod
    def cookie_from(headers, name):
        for header, value in headers:
            if header.lower() == 'set-cookie' and value.startswith(name + '='):
                return value.split(';', 1)[0]
        return ''

    def test_oidc_login_callback_creates_local_member_and_cookie_session(self):
        status, headers, _ = self.request('GET', '/auth/login')
        self.assertEqual(status, HTTPStatus.FOUND)
        location = dict(headers)['Location']
        query = parse_qs(urlparse(location).query)
        self.assertEqual(query['client_id'], ['todo'])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertEqual(query['nonce'][0] != '', True)
        flow_cookie = self.cookie_from(headers, server.OIDC_FLOW_COOKIE_NAME)
        self.assertTrue(flow_cookie)

        identity = OIDCIdentity(
            sub='11111111-1111-4111-8111-111111111111',
            username='Alice',
            display_name='Alice Example',
            sid='22222222-2222-4222-8222-222222222222',
        )
        callback = f"/auth/callback?code=test-code&state={query['state'][0]}"
        with mock.patch.object(server, 'exchange_authorization_code', return_value=identity):
            status, callback_headers, _ = self.request(
                'GET', callback, headers={'Cookie': flow_cookie}
            )
        self.assertEqual(status, HTTPStatus.FOUND)
        session_cookie = self.cookie_from(callback_headers, server.SESSION_COOKIE_NAME)
        self.assertTrue(session_cookie)

        status, _, body = self.request(
            'GET', '/api/auth/me', headers={'Cookie': session_cookie}
        )
        self.assertEqual(status, HTTPStatus.OK)
        payload = json.loads(body)
        self.assertEqual(payload['user']['nickname'], 'Alice')
        self.assertTrue(payload['csrfToken'])
        with server.get_db() as connection:
            user = connection.execute('SELECT * FROM users').fetchone()
            self.assertEqual(user['auth_sub'], identity.sub)
            self.assertEqual(user['role'], 'student')
            stored = connection.execute('SELECT token FROM sessions').fetchone()[0]
            self.assertNotIn(session_cookie.split('=', 1)[1], stored)

        status, _, _ = self.request(
            'PUT',
            '/api/auth/avatar-color',
            body=json.dumps({'color': '#123abc'}),
            headers={'Cookie': session_cookie, 'Content-Type': 'application/json'},
        )
        self.assertEqual(status, HTTPStatus.FORBIDDEN)
        status, _, _ = self.request(
            'PUT',
            '/api/auth/avatar-color',
            body=json.dumps({'color': '#123abc'}),
            headers={
                'Cookie': session_cookie,
                'Content-Type': 'application/json',
                'X-CSRF-Token': payload['csrfToken'],
            },
        )
        self.assertEqual(status, HTTPStatus.GONE)

    def test_callback_state_is_one_time_even_when_exchange_fails(self):
        status, headers, _ = self.request('GET', '/auth/login')
        self.assertEqual(status, HTTPStatus.FOUND)
        query = parse_qs(urlparse(dict(headers)['Location']).query)
        flow_cookie = self.cookie_from(headers, server.OIDC_FLOW_COOKIE_NAME)
        callback = f"/auth/callback?code=test-code&state={query['state'][0]}"
        with mock.patch.object(server, 'exchange_authorization_code', side_effect=server.OIDCError('no')):
            first, _, _ = self.request('GET', callback, headers={'Cookie': flow_cookie})
        self.assertEqual(first, HTTPStatus.BAD_GATEWAY)
        second, _, _ = self.request('GET', callback, headers={'Cookie': flow_cookie})
        self.assertEqual(second, HTTPStatus.BAD_REQUEST)

    def test_backchannel_logout_revokes_sid_and_rejects_replay_side_effects(self):
        with server.get_db() as connection:
            cursor = connection.execute(
                '''
                INSERT INTO users (name, nickname, password_hash, role, auth_sub, created_at)
                VALUES ('Alice', 'alice', '', 'student', 'central-sub', ?)
                ''',
                (server.now_iso(),),
            )
            user_id = cursor.lastrowid
            connection.execute(
                '''
                INSERT INTO sessions
                (token, user_id, auth_sub, sid, csrf_token, expires_at, created_at)
                VALUES ('digest', ?, 'central-sub', 'central-sid', 'csrf', ?, ?)
                ''',
                (user_id, 9999999999, server.now_iso()),
            )
            connection.commit()
        fake_response = mock.Mock()
        fake_response.json.return_value = {'keys': []}
        fake_response.raise_for_status.return_value = None
        claims = {'jti': 'logout-jti', 'sid': 'central-sid', 'sub': 'central-sub'}
        encoded = 'logout_token=opaque'
        with (
            mock.patch.object(server.requests, 'get', return_value=fake_response),
            mock.patch.object(server, 'validate_logout_token', return_value=claims),
        ):
            for _ in range(2):
                status, _, _ = self.request(
                    'POST',
                    '/auth/backchannel-logout',
                    body=encoded,
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Content-Length': str(len(encoded)),
                    },
                )
                self.assertEqual(status, HTTPStatus.OK)
        with server.get_db() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 0)
            self.assertEqual(
                connection.execute('SELECT COUNT(*) FROM backchannel_logout_jtis').fetchone()[0], 1
            )

    def test_local_password_endpoints_are_closed_after_cutover(self):
        for endpoint in ('/api/auth/register', '/api/auth/login'):
            status, _, body = self.request(
                'POST',
                endpoint,
                body=b'{}',
                headers={'Content-Type': 'application/json', 'Content-Length': '2'},
            )
            self.assertEqual(status, HTTPStatus.GONE)
            self.assertEqual(json.loads(body)['loginUrl'], '/auth/login')


class AccountsMappingTests(unittest.TestCase):
    def test_mapping_preserves_local_id_and_business_rows(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = Path(directory) / 'todo.sqlite3'
            mapping_path = Path(directory) / 'mapping.json'
            connection = sqlite3.connect(database)
            connection.executescript(
                '''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, nickname TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE sessions (
                    token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE tasks (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT);
                INSERT INTO users VALUES (7, 'Alice', 'alice', 'legacy-hash', 'admin', 'now');
                INSERT INTO sessions VALUES ('legacy-session', 7, 9999999999, 'now');
                INSERT INTO tasks VALUES ('task-1', 7, 'Keep me');
                '''
            )
            connection.commit()
            connection.close()
            mapping_path.write_text(
                json.dumps(
                    {
                        'version': 1,
                        'mappings': [
                            {
                                'source_app': 'todo',
                                'source_user_id': '7',
                                'central_sub': '33333333-3333-4333-8333-333333333333',
                            }
                        ],
                    }
                ),
                encoding='utf-8',
            )
            first = apply_mapping(database, mapping_path)
            second = apply_mapping(database, mapping_path)
            self.assertEqual(first['mapped'], 1)
            self.assertEqual(second['mapped'], 1)
            connection = sqlite3.connect(database)
            user = connection.execute(
                'SELECT id, role, password_hash, auth_sub FROM users'
            ).fetchone()
            self.assertEqual(user, (7, 'admin', '', '33333333-3333-4333-8333-333333333333'))
            self.assertEqual(connection.execute('SELECT user_id FROM tasks').fetchone()[0], 7)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 0)
            self.assertEqual(
                connection.execute(
                    'SELECT password_hash FROM archived_password_credentials WHERE user_id = 7'
                ).fetchone()[0],
                'legacy-hash',
            )
            connection.close()

    def test_grant_admin_uses_central_sub_and_requires_existing_member(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = Path(directory) / 'todo.sqlite3'
            with sqlite3.connect(database) as connection:
                connection.execute(
                    '''
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY, nickname TEXT NOT NULL, role TEXT NOT NULL,
                        auth_sub TEXT UNIQUE
                    )
                    '''
                )
                connection.execute(
                    "INSERT INTO users VALUES (5, 'alice', 'student', 'central-sub')"
                )
            self.assertEqual(grant_admin(database, 'central-sub'), 'alice')
            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    connection.execute('SELECT id, role FROM users').fetchone(), (5, 'admin')
                )
            with self.assertRaisesRegex(ValueError, 'no local member'):
                grant_admin(database, 'unknown-sub')


class TokenValidationTests(unittest.TestCase):
    def test_id_token_requires_signature_audience_and_nonce(self):
        key, jwks = signing_material()
        now = int(time.time())
        claims = {
            'iss': 'https://accounts.test',
            'aud': ['todo'],
            'sub': 'central-sub',
            'exp': now + 300,
            'iat': now,
            'nonce': 'expected-nonce',
            'sid': 'central-sid',
        }
        token = jwt.encode({'alg': 'RS256', 'kid': 'test-key'}, claims, key)
        decoded = _validate_id_token(
            token,
            jwks,
            issuer='https://accounts.test',
            client_id='todo',
            nonce='expected-nonce',
        )
        self.assertEqual(decoded['sub'], 'central-sub')
        with self.assertRaises(OIDCError):
            _validate_id_token(
                token,
                jwks,
                issuer='https://accounts.test',
                client_id='todo',
                nonce='wrong-nonce',
            )

    def test_logout_token_requires_backchannel_event_and_current_iat(self):
        key, jwks = signing_material()
        now = int(time.time())
        claims = {
            'iss': 'https://accounts.test',
            'aud': ['todo'],
            'iat': now,
            'jti': 'logout-jti',
            'sid': 'central-sid',
            'events': {'http://schemas.openid.net/event/backchannel-logout': {}},
        }
        token = jwt.encode({'alg': 'RS256', 'kid': 'test-key'}, claims, key)
        decoded = validate_logout_token(
            token, jwks, issuer='https://accounts.test', client_id='todo'
        )
        self.assertEqual(decoded['sid'], 'central-sid')
        claims['iat'] = now - 301
        stale = jwt.encode({'alg': 'RS256', 'kid': 'test-key'}, claims, key)
        with self.assertRaisesRegex(OIDCError, 'too old'):
            validate_logout_token(
                stale, jwks, issuer='https://accounts.test', client_id='todo'
            )


if __name__ == '__main__':
    unittest.main()
