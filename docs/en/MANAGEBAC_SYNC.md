# ManageBac backend synchronization

[中文](../zh-CN/MANAGEBAC_SYNC.md) | [English](./MANAGEBAC_SYNC.md)

## Security boundary

ManageBac synchronization runs on this site's backend:

```text
User enters ManageBac credentials
  -> backend signs in once and immediately discards the credentials
  -> AES-GCM encrypts the cookie jar and stores it per site user
  -> later requests fetch and parse the tasks page with the cookie
  -> an expired cookie is deleted and the user must enter credentials again
```

The backend does not persist the ManageBac account or password. A cookie is an active sign-in credential and must still be protected like a password. The frontend receives only connection state and parsed tasks, never the cookie.

## Required configuration

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Generate a 32-byte URL-safe Base64 key:

```bash
python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Set it in the deployment environment:

```dotenv
MANAGEBAC_COOKIE_ENCRYPTION_KEY=generated-key
```

Back up the key separately and keep it stable. Existing cookies cannot be decrypted after the key is lost or replaced, so users must sign in again. Never commit the real key.

Production must expose the site over HTTPS. A reverse proxy connected to the local Python service must forward:

```text
X-Forwarded-Proto: https
```

Plain HTTP remains allowed for local `localhost` development.

## User flow

1. Opening “Sync ManageBac” calls `GET /api/managebac/session`.
2. If no cookie exists, the UI displays the ManageBac credential form.
3. `POST /api/managebac/session` fetches the login CSRF token, submits the credentials, and verifies the tasks page.
4. On success, only the encrypted cookie is stored and a task preview is returned.
5. `POST /api/managebac/tasks/preview` uses the cookie and persists any cookie rotation returned by ManageBac.
6. If the task request returns to the login page, the backend deletes the expired cookie and returns `managebac_reauth_required`; the UI displays the credential form again.
7. `DELETE /api/managebac/session` deletes the remotely stored cookie on request.

## Limitations

- The integration is currently fixed to `https://sdgj.managebac.cn`.
- Password-form sign-in is supported; CAPTCHA, MFA, and Google/Microsoft SSO are not guaranteed to work.
- Because the password is not stored, an expired cookie cannot be renewed without user interaction.
- Each site user and source IP may produce at most five failed sign-ins within 15 minutes.
- Cookies are sent only to the fixed ManageBac host; cross-origin redirects are rejected.

## Import policy

- Sign-in and fetching return a preview and do not create site tasks directly.
- Tasks are imported only after user confirmation through the existing task API.
- The frontend infers subjects from `className/rawCourseName`; users must complete unresolved subjects.
- Imports preserve the `ManageBac: core_task:<id>` note for duplicate detection.
