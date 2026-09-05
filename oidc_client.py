from __future__ import annotations

import time
from dataclasses import dataclass

import requests
from authlib.integrations.requests_client import OAuth2Session
from joserfc import jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry


class OIDCError(RuntimeError):
    pass


@dataclass(frozen=True)
class OIDCIdentity:
    sub: str
    username: str
    display_name: str
    sid: str


def _endpoint(issuer: str, path: str) -> str:
    return issuer.rstrip('/') + path


def authorization_url(
    *,
    issuer: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    nonce: str,
    verifier: str,
    prompt: str | None = None,
    screen_hint: str | None = None,
) -> str:
    client = OAuth2Session(
        client_id=client_id,
        scope='openid profile',
        redirect_uri=redirect_uri,
        code_challenge_method='S256',
    )
    extra = {}
    if prompt:
        extra['prompt'] = prompt
    if screen_hint:
        extra['screen_hint'] = screen_hint
    url, _ = client.create_authorization_url(
        _endpoint(issuer, '/oauth/authorize'),
        state=state,
        nonce=nonce,
        code_verifier=verifier,
        **extra,
    )
    return url


def _validate_id_token(
    raw_token: str, jwks: dict, *, issuer: str, client_id: str, nonce: str
) -> dict:
    try:
        token = jwt.decode(raw_token, KeySet.import_key_set(jwks), algorithms=['RS256'])
        JWTClaimsRegistry(
            iss={'essential': True, 'value': issuer.rstrip('/')},
            aud={'essential': True, 'value': client_id},
            sub={'essential': True},
            exp={'essential': True},
            iat={'essential': True},
            nonce={'essential': True, 'value': nonce},
            sid={'essential': True},
        ).validate(token.claims)
    except Exception as exc:
        raise OIDCError('ID Token validation failed') from exc
    return token.claims


def exchange_authorization_code(
    *,
    issuer: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    verifier: str,
    nonce: str,
    timeout: float = 5,
) -> OIDCIdentity:
    client = OAuth2Session(
        client_id=client_id,
        client_secret=client_secret,
        token_endpoint_auth_method='client_secret_basic',
        scope='openid profile',
        redirect_uri=redirect_uri,
        code_challenge_method='S256',
        default_timeout=timeout,
    )
    try:
        token = client.fetch_token(
            _endpoint(issuer, '/oauth/token'),
            grant_type='authorization_code',
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=verifier,
        )
        if not token.get('id_token') or not token.get('access_token'):
            raise OIDCError('token response is incomplete')
        jwks_response = requests.get(_endpoint(issuer, '/.well-known/jwks.json'), timeout=timeout)
        jwks_response.raise_for_status()
        claims = _validate_id_token(
            token['id_token'],
            jwks_response.json(),
            issuer=issuer,
            client_id=client_id,
            nonce=nonce,
        )
        userinfo_response = client.get(_endpoint(issuer, '/oauth/userinfo'), timeout=timeout)
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
    except OIDCError:
        raise
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise OIDCError('central account service is unavailable or returned invalid data') from exc
    if userinfo.get('sub') != claims.get('sub'):
        raise OIDCError('UserInfo subject does not match ID Token')
    username = str(userinfo.get('preferred_username') or '').strip()
    display_name = str(userinfo.get('name') or username).strip()
    if not username or not display_name:
        raise OIDCError('central account profile is incomplete')
    return OIDCIdentity(
        sub=str(claims['sub']),
        username=username,
        display_name=display_name,
        sid=str(claims['sid']),
    )


def validate_logout_token(
    raw_token: str, jwks: dict, *, issuer: str, client_id: str, max_age_seconds: int = 300
) -> dict:
    try:
        token = jwt.decode(raw_token, KeySet.import_key_set(jwks), algorithms=['RS256'])
        JWTClaimsRegistry(
            iss={'essential': True, 'value': issuer.rstrip('/')},
            aud={'essential': True, 'value': client_id},
            iat={'essential': True},
            jti={'essential': True},
            events={'essential': True},
        ).validate(token.claims)
    except Exception as exc:
        raise OIDCError('logout token validation failed') from exc
    claims = token.claims
    event = 'http://schemas.openid.net/event/backchannel-logout'
    if event not in claims.get('events', {}):
        raise OIDCError('logout token event is missing')
    if not claims.get('sub') and not claims.get('sid'):
        raise OIDCError('logout token must contain sub or sid')
    if abs(int(time.time()) - int(claims['iat'])) > max_age_seconds:
        raise OIDCError('logout token is too old')
    return claims
