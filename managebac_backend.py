from __future__ import annotations

import base64
import binascii
import html as html_module
import http.cookiejar
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


MANAGEBAC_ORIGIN = 'https://sdgj.managebac.cn'
MANAGEBAC_LOGIN_URL = f'{MANAGEBAC_ORIGIN}/login'
MANAGEBAC_SESSIONS_URL = f'{MANAGEBAC_ORIGIN}/sessions'
MANAGEBAC_TASKS_URL = f'{MANAGEBAC_ORIGIN}/student/tasks_and_deadlines'
MANAGEBAC_ALLOWED_HOST = 'sdgj.managebac.cn'
MANAGEBAC_COOKIE_KEY_ENV = 'MANAGEBAC_COOKIE_ENCRYPTION_KEY'
MANAGEBAC_RESPONSE_LIMIT_BYTES = 5 * 1024 * 1024
MANAGEBAC_REQUEST_TIMEOUT_SECONDS = 20
MANAGEBAC_TIMEZONE = timezone(timedelta(hours=8))
MANAGEBAC_COOKIE_FORMAT_VERSION = 1
MANAGEBAC_COOKIE_CIPHER_VERSION = 'v1'

PAGE_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'User-Agent': 'nethub.wiki ManageBac Sync/1.0',
}

MONTHS = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12,
}


class ManageBacError(Exception):
    """Base class for safe, user-facing ManageBac integration failures."""


class ManageBacConfigurationError(ManageBacError):
    pass


class ManageBacAuthenticationError(ManageBacError):
    pass


class ManageBacSessionExpired(ManageBacError):
    pass


class ManageBacRemoteError(ManageBacError):
    pass


class ManageBacProtocolError(ManageBacError):
    pass


@dataclass(frozen=True)
class ManageBacPage:
    html: str
    url: str
    status: int
    content_type: str
    byte_length: int


@dataclass(frozen=True)
class ManageBacPreview:
    cookie_jar_json: str
    tasks: list[dict]
    meta: dict


class _ManageBacRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        target_host = (parsed.hostname or '').lower()
        if parsed.scheme != 'https' or target_host != MANAGEBAC_ALLOWED_HOST:
            print(
                f'[ManageBac] error_type=untrusted_redirect '
                f'target_host={json.dumps(target_host or None)}',
                flush=True,
            )
            raise ManageBacProtocolError('ManageBac 返回了不受信任的跳转地址。')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class ManageBacClient:
    def __init__(self, cookie_jar: http.cookiejar.CookieJar | None = None):
        self.cookie_jar = cookie_jar or http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            _ManageBacRedirectHandler(),
        )

    def request(self, url: str, *, data: bytes | None = None, method: str = 'GET') -> ManageBacPage:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or (parsed.hostname or '').lower() != MANAGEBAC_ALLOWED_HOST:
            raise ManageBacProtocolError('拒绝向非 ManageBac 地址发送请求。')
        headers = dict(PAGE_REQUEST_HEADERS)
        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            headers['Origin'] = MANAGEBAC_ORIGIN
            headers['Referer'] = MANAGEBAC_LOGIN_URL
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self.opener.open(request, timeout=MANAGEBAC_REQUEST_TIMEOUT_SECONDS) as response:
                raw = response.read(MANAGEBAC_RESPONSE_LIMIT_BYTES + 1)
                if len(raw) > MANAGEBAC_RESPONSE_LIMIT_BYTES:
                    raise ManageBacRemoteError('ManageBac 返回的页面过大。')
                charset = response.headers.get_content_charset() or 'utf-8'
                return ManageBacPage(
                    html=raw.decode(charset, errors='replace'),
                    url=response.geturl(),
                    status=int(getattr(response, 'status', 200)),
                    content_type=str(response.headers.get('Content-Type', '')),
                    byte_length=len(raw),
                )
        except ManageBacError:
            raise
        except urllib.error.HTTPError as error:
            error.close()
            raise ManageBacRemoteError(f'ManageBac 请求失败（HTTP {error.code}）。') from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ManageBacRemoteError('暂时无法连接 ManageBac，请稍后重试。') from None

    def login(self, account: str, password: str) -> ManageBacPage:
        login_page = self.request(MANAGEBAC_LOGIN_URL)
        authenticity_token = extract_authenticity_token(login_page.html)
        if not authenticity_token:
            raise ManageBacProtocolError('无法读取 ManageBac 登录校验信息。')
        form = urllib.parse.urlencode({
            'authenticity_token': authenticity_token,
            'login': account,
            'password': password,
            'remember_me': '1',
            'commit': 'Sign in',
        }).encode('utf-8')
        self.request(MANAGEBAC_SESSIONS_URL, data=form, method='POST')
        tasks_page = self.request(MANAGEBAC_TASKS_URL)
        if is_login_page(tasks_page.html, tasks_page.url):
            raise ManageBacAuthenticationError('ManageBac 账号或密码不正确，或当前登录方式不受支持。')
        if not is_tasks_page(tasks_page.html):
            raise ManageBacProtocolError('ManageBac 登录成功，但任务页面格式无法识别。')
        return tasks_page

    def fetch_tasks(self) -> ManageBacPage:
        tasks_page = self.request(MANAGEBAC_TASKS_URL)
        if is_login_page(tasks_page.html, tasks_page.url):
            raise ManageBacSessionExpired('ManageBac 登录已失效，需要重新登录。')
        if not is_tasks_page(tasks_page.html):
            raise ManageBacProtocolError('ManageBac 任务页面格式无法识别。')
        return tasks_page


def extract_authenticity_token(html: str) -> str:
    tag_match = re.search(
        r'<input\b(?=[^>]*\bname\s*=\s*["\']authenticity_token["\'])[^>]*>',
        str(html or ''),
        flags=re.IGNORECASE,
    )
    if not tag_match:
        return ''
    value_match = re.search(r'\bvalue\s*=\s*["\']([^"\']*)["\']', tag_match.group(0), flags=re.IGNORECASE)
    return html_module.unescape(value_match.group(1)) if value_match else ''


def extract_title(html: str) -> str:
    match = re.search(r'<title[^>]*>([\s\S]*?)</title>', str(html or ''), flags=re.IGNORECASE)
    return normalize_whitespace(strip_tags(match.group(1))) if match else ''


def is_login_page(html: str, final_url: str = '') -> bool:
    path = urllib.parse.urlparse(final_url).path.rstrip('/')
    return (
        path in {'/login', '/sessions'}
        or re.search(r'<title[^>]*>\s*ManageBac\s*\|\s*Login\s*</title>', html, flags=re.IGNORECASE) is not None
        or re.search(r'id=["\']session_login["\']', html, flags=re.IGNORECASE) is not None
        or re.search(r'id=["\']session_password["\']', html, flags=re.IGNORECASE) is not None
        or re.search(r'name=["\']password["\']', html, flags=re.IGNORECASE) is not None
    )


def is_tasks_page(html: str) -> bool:
    return (
        'controller-student-tasks_and_deadlines' in str(html or '')
        or re.search(
            r'<title[^>]*>\s*ManageBac\s*\|\s*Tasks\s*&amp;\s*Deadlines\s*</title>',
            str(html or ''),
            flags=re.IGNORECASE,
        ) is not None
    )


def normalize_whitespace(value: str) -> str:
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def strip_tags(value: str) -> str:
    return html_module.unescape(re.sub(r'<[^>]*>', ' ', str(value or '')))


def _read_attribute(attrs: str, name: str) -> str:
    match = re.search(rf'{re.escape(name)}\s*=\s*["\']([^"\']+)["\']', str(attrs or ''), flags=re.IGNORECASE)
    return html_module.unescape(match.group(1)) if match else ''


def _find_anchors(fragment: str) -> list[dict]:
    anchors = []
    for match in re.finditer(r'<a\b([^>]*)>([\s\S]*?)</a>', fragment, flags=re.IGNORECASE):
        anchors.append({
            'href': _read_attribute(match.group(1), 'href'),
            'className': _read_attribute(match.group(1), 'class'),
            'text': normalize_whitespace(strip_tags(match.group(2))),
        })
    return anchors


def parse_managebac_due_text(raw_text: str, fetched_at: datetime | str | None = None) -> str:
    text = normalize_whitespace(raw_text)
    match = re.search(
        r'\b([A-Za-z]{3,9})\s+(\d{1,2})(?:,\s*(\d{4}))?,\s*(\d{1,2}):(\d{2})\s*(AM|PM)\b',
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ''
    month = MONTHS.get(match.group(1).lower())
    if month is None:
        return ''
    try:
        if isinstance(fetched_at, str):
            fetched = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
        elif isinstance(fetched_at, datetime):
            fetched = fetched_at
        else:
            fetched = datetime.now(MANAGEBAC_TIMEZONE)
        if fetched.tzinfo is not None:
            fetched = fetched.astimezone(MANAGEBAC_TIMEZONE).replace(tzinfo=None)
        year = int(match.group(3)) if match.group(3) else fetched.year
        hour = int(match.group(4))
        if match.group(6).upper() == 'PM' and hour < 12:
            hour += 12
        if match.group(6).upper() == 'AM' and hour == 12:
            hour = 0
        due = datetime(year, month, int(match.group(2)), hour, int(match.group(5)))
        if not match.group(3) and due < fetched - timedelta(days=30):
            due = due.replace(year=year + 1)
        return due.strftime('%Y-%m-%dT%H:%M:00')
    except (TypeError, ValueError, OverflowError):
        return ''


def parse_managebac_tasks(html: str, fetched_at: datetime | str | None = None) -> list[dict]:
    rows = [
        line for line in str(html or '').splitlines()
        if 'f-tile__body' in line and 'f-tile__title-link' in line and '/core_tasks/' in line
    ]
    seen: set[str] = set()
    tasks: list[dict] = []
    for row in rows:
        anchors = _find_anchors(row)
        task_anchor = next((
            anchor for anchor in anchors
            if 'f-tile__title-link' in anchor['className']
            and re.search(r'/core_tasks/\d+', anchor['href'])
        ), None)
        if not task_anchor:
            continue
        class_anchor = next((
            anchor for anchor in anchors
            if re.search(r'/student/classes/\d+$', anchor['href']) and '/core_tasks/' not in anchor['href']
        ), None)
        id_match = re.search(r'/core_tasks/(\d+)', task_anchor['href'])
        source_id = f'core_task:{id_match.group(1)}' if id_match else task_anchor['href']
        if source_id in seen:
            continue
        seen.add(source_id)
        due_match = re.search(r'<span[^>]*>\s*<svg[\s\S]*?</svg>\s*([^<]+)</span>', row, flags=re.IGNORECASE)
        due_text = html_module.unescape(due_match.group(1)) if due_match else ''
        title = task_anchor['text']
        if not title or not due_text:
            continue
        raw_course_name = class_anchor['text'] if class_anchor else ''
        source_url = urllib.parse.urljoin(MANAGEBAC_ORIGIN, task_anchor['href'])
        tasks.append({
            'source': 'managebac',
            'sourceId': source_id,
            'sourceUrl': source_url,
            'title': title,
            'subject': '',
            'className': raw_course_name,
            'rawCourseName': raw_course_name,
            'dueAt': parse_managebac_due_text(due_text, fetched_at),
            'priority': 'medium',
            'note': f'ManageBac: {source_id}',
        })
    return tasks


def serialize_cookie_jar(cookie_jar: http.cookiejar.CookieJar) -> str:
    cookies = []
    for cookie in cookie_jar:
        cookies.append({
            'version': cookie.version,
            'name': cookie.name,
            'value': cookie.value,
            'port': cookie.port,
            'portSpecified': cookie.port_specified,
            'domain': cookie.domain,
            'domainSpecified': cookie.domain_specified,
            'domainInitialDot': cookie.domain_initial_dot,
            'path': cookie.path,
            'pathSpecified': cookie.path_specified,
            'secure': cookie.secure,
            'expires': cookie.expires,
            'discard': cookie.discard,
            'comment': cookie.comment,
            'commentUrl': cookie.comment_url,
            'rest': dict(cookie._rest),
            'rfc2109': cookie.rfc2109,
        })
    return json.dumps(
        {'version': MANAGEBAC_COOKIE_FORMAT_VERSION, 'cookies': cookies},
        ensure_ascii=False,
        separators=(',', ':'),
    )


def deserialize_cookie_jar(payload: str) -> http.cookiejar.CookieJar:
    try:
        source = json.loads(payload)
        if source.get('version') != MANAGEBAC_COOKIE_FORMAT_VERSION or not isinstance(source.get('cookies'), list):
            raise ValueError
        cookie_jar = http.cookiejar.CookieJar()
        for item in source['cookies']:
            cookie_jar.set_cookie(http.cookiejar.Cookie(
                version=int(item.get('version', 0)),
                name=str(item['name']),
                value=str(item['value']),
                port=item.get('port'),
                port_specified=bool(item.get('portSpecified', False)),
                domain=str(item['domain']),
                domain_specified=bool(item.get('domainSpecified', False)),
                domain_initial_dot=bool(item.get('domainInitialDot', False)),
                path=str(item.get('path') or '/'),
                path_specified=bool(item.get('pathSpecified', True)),
                secure=bool(item.get('secure', True)),
                expires=item.get('expires'),
                discard=bool(item.get('discard', False)),
                comment=item.get('comment'),
                comment_url=item.get('commentUrl'),
                rest=dict(item.get('rest') or {}),
                rfc2109=bool(item.get('rfc2109', False)),
            ))
        return cookie_jar
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise ManageBacProtocolError('保存的 ManageBac Cookie 数据无法读取。') from None


def _cookie_encryption_key() -> bytes:
    raw = os.environ.get(MANAGEBAC_COOKIE_KEY_ENV, '').strip()
    if not raw:
        raise ManageBacConfigurationError(f'服务器未配置 {MANAGEBAC_COOKIE_KEY_ENV}。')
    try:
        key = base64.b64decode(raw.encode('ascii'), altchars=b'-_', validate=True)
    except (UnicodeEncodeError, binascii.Error):
        raise ManageBacConfigurationError(f'{MANAGEBAC_COOKIE_KEY_ENV} 格式无效。') from None
    if len(key) != 32:
        raise ManageBacConfigurationError(f'{MANAGEBAC_COOKIE_KEY_ENV} 必须是 32 字节 URL-safe Base64 密钥。')
    return key


def validate_cookie_encryption_configuration() -> None:
    _cookie_encryption_key()


def encrypt_cookie_jar(cookie_jar_json: str, user_id: int) -> str:
    nonce = secrets.token_bytes(12)
    aad = f'managebac-cookie:user:{int(user_id)}:{MANAGEBAC_COOKIE_CIPHER_VERSION}'.encode('ascii')
    ciphertext = AESGCM(_cookie_encryption_key()).encrypt(nonce, cookie_jar_json.encode('utf-8'), aad)
    encoded = base64.urlsafe_b64encode(nonce + ciphertext).decode('ascii').rstrip('=')
    return f'{MANAGEBAC_COOKIE_CIPHER_VERSION}.{encoded}'


def decrypt_cookie_jar(encrypted: str, user_id: int) -> str:
    prefix = f'{MANAGEBAC_COOKIE_CIPHER_VERSION}.'
    if not str(encrypted or '').startswith(prefix):
        raise ManageBacConfigurationError('保存的 ManageBac Cookie 加密版本不受支持。')
    encoded = encrypted[len(prefix):]
    try:
        raw = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
        nonce, ciphertext = raw[:12], raw[12:]
        if len(nonce) != 12 or not ciphertext:
            raise ValueError
        aad = f'managebac-cookie:user:{int(user_id)}:{MANAGEBAC_COOKIE_CIPHER_VERSION}'.encode('ascii')
        return AESGCM(_cookie_encryption_key()).decrypt(nonce, ciphertext, aad).decode('utf-8')
    except (InvalidTag, UnicodeDecodeError, ValueError, binascii.Error):
        raise ManageBacConfigurationError('保存的 ManageBac Cookie 无法解密，请检查服务器密钥。') from None


def _preview(page: ManageBacPage, cookie_jar: http.cookiejar.CookieJar) -> ManageBacPreview:
    fetched_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    return ManageBacPreview(
        cookie_jar_json=serialize_cookie_jar(cookie_jar),
        tasks=parse_managebac_tasks(page.html, fetched_at),
        meta={
            'fetchedAt': fetched_at,
            'url': MANAGEBAC_TASKS_URL,
            'status': page.status,
            'contentType': page.content_type,
            'byteLength': page.byte_length,
            'title': extract_title(page.html),
            'detectedLoginPage': False,
            'detectedTasksPage': True,
            'cookieCount': len(list(cookie_jar)),
        },
    )


def authenticate_managebac(account: str, password: str) -> ManageBacPreview:
    client = ManageBacClient()
    page = client.login(account, password)
    return _preview(page, client.cookie_jar)


def fetch_managebac_preview(cookie_jar_json: str) -> ManageBacPreview:
    client = ManageBacClient(deserialize_cookie_jar(cookie_jar_json))
    page = client.fetch_tasks()
    return _preview(page, client.cookie_jar)
