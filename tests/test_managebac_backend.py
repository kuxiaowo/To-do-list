import base64
import http.cookiejar
import os
import secrets
import unittest

import managebac_backend


TASKS_HTML = '''
<html class="controller-student-tasks_and_deadlines">
<head><title>ManageBac | Tasks &amp; Deadlines</title></head>
<body>
<div class="f-tile__body"><p class="f-tile__title h5"><a class="f-tile__title-link link-dark f-truncate-item" href="/student/classes/11465612/core_tasks/27421385"><span class="f-truncate-item">Final Group Project</span></a></p><div class="f-tile__description color-secondary"><div class="hstack gap-2 flex-wrap f-truncate"><span><svg></svg> Jun 21, 11:55 PM</span><span class="vr"></span><a class="f-truncate-item link-dark" href="/student/classes/11465612">HS Computer（25级选修） (Grade 10)</a></div></div></div>
</body>
</html>
'''


def sample_cookie_jar(value='server-session-secret'):
    jar = http.cookiejar.CookieJar()
    jar.set_cookie(http.cookiejar.Cookie(
        version=0,
        name='_managebac_session',
        value=value,
        port=None,
        port_specified=False,
        domain='sdgj.managebac.cn',
        domain_specified=True,
        domain_initial_dot=False,
        path='/',
        path_specified=True,
        secure=True,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={'HttpOnly': None, 'SameSite': 'None'},
        rfc2109=False,
    ))
    return jar


class ManageBacBackendTests(unittest.TestCase):
    def setUp(self):
        self.original_key = os.environ.get(managebac_backend.MANAGEBAC_COOKIE_KEY_ENV)
        os.environ[managebac_backend.MANAGEBAC_COOKIE_KEY_ENV] = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('ascii')

    def tearDown(self):
        if self.original_key is None:
            os.environ.pop(managebac_backend.MANAGEBAC_COOKIE_KEY_ENV, None)
        else:
            os.environ[managebac_backend.MANAGEBAC_COOKIE_KEY_ENV] = self.original_key

    def test_parser_matches_existing_helper_contract(self):
        tasks = managebac_backend.parse_managebac_tasks(TASKS_HTML, '2026-06-18T10:50:26.270Z')
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0], {
            'source': 'managebac',
            'sourceId': 'core_task:27421385',
            'sourceUrl': 'https://sdgj.managebac.cn/student/classes/11465612/core_tasks/27421385',
            'title': 'Final Group Project',
            'subject': '',
            'className': 'HS Computer（25级选修） (Grade 10)',
            'rawCourseName': 'HS Computer（25级选修） (Grade 10)',
            'dueAt': '2026-06-21T23:55:00',
            'priority': 'medium',
            'note': 'ManageBac: core_task:27421385',
        })
        self.assertEqual(
            managebac_backend.parse_managebac_due_text('Jan 2, 12:05 AM', '2026-12-30T00:00:00Z'),
            '2027-01-02T00:05:00',
        )
        self.assertEqual(
            managebac_backend.parse_managebac_due_text('Feb 31, 11:55 PM', '2026-02-01T00:00:00Z'),
            '',
        )

    def test_cookie_jar_round_trip_and_authenticated_encryption(self):
        plaintext = managebac_backend.serialize_cookie_jar(sample_cookie_jar())
        restored = managebac_backend.deserialize_cookie_jar(plaintext)
        self.assertEqual([(cookie.name, cookie.value) for cookie in restored], [
            ('_managebac_session', 'server-session-secret')
        ])

        encrypted = managebac_backend.encrypt_cookie_jar(plaintext, 7)
        self.assertNotIn('server-session-secret', encrypted)
        self.assertEqual(managebac_backend.decrypt_cookie_jar(encrypted, 7), plaintext)
        with self.assertRaises(managebac_backend.ManageBacConfigurationError):
            managebac_backend.decrypt_cookie_jar(encrypted, 8)

    def test_login_page_and_csrf_detection(self):
        login_html = '''
        <html><head><title>ManageBac | Login</title></head><body>
        <form action="/sessions"><input value="csrf&amp;value" name="authenticity_token">
        <input id="session_password" name="password" type="password"></form></body></html>
        '''
        self.assertEqual(managebac_backend.extract_authenticity_token(login_html), 'csrf&value')
        self.assertTrue(managebac_backend.is_login_page(login_html, managebac_backend.MANAGEBAC_LOGIN_URL))
        self.assertTrue(managebac_backend.is_tasks_page(TASKS_HTML))


if __name__ == '__main__':
    unittest.main()
