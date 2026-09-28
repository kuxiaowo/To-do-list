import io
import json
import unittest
from unittest.mock import patch
import urllib.error

import server


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class TurnstileTest(unittest.TestCase):
    def test_siteverify_checks_hostname_and_action(self):
        def fake_open(_request, timeout):
            self.assertEqual(timeout, 4)
            return Response(json.dumps({
                'success': True,
                'hostname': 'todolist.nethub.wiki',
                'action': 'feedback',
            }).encode())

        with patch.object(server, 'TURNSTILE_SECRET_KEY', 'test-secret'), patch.object(
            server.urllib.request, 'urlopen', fake_open
        ):
            self.assertTrue(server.verify_turnstile('token', 'feedback'))
            self.assertFalse(server.verify_turnstile('token', 'login'))

    def test_missing_token_and_outage_fail_closed(self):
        self.assertFalse(server.verify_turnstile('', 'feedback'))

        def offline(_request, timeout):
            raise urllib.error.URLError('offline')

        with patch.object(server, 'TURNSTILE_SECRET_KEY', 'test-secret'), patch.object(
            server.urllib.request, 'urlopen', offline
        ):
            with self.assertRaises(server.TurnstileUnavailable):
                server.verify_turnstile('token', 'feedback')
