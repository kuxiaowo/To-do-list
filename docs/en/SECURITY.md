# Security Guide

[中文](../zh-CN/SECURITY.md) | [English](./SECURITY.md)

This document records the security boundaries, deployment recommendations, and remaining considerations for the current project.

## Service exposure

- Default listener is `127.0.0.1:8092`. In the production environment, it is recommended to continue to bind the local address and provide HTTPS to the outside world through Caddy or Nginx reverse proxy.
- It is not recommended to expose Python's built-in HTTP service directly to the public network.
- `.env` has been ignored in `.gitignore`, do not submit the real `DEEPSEEK_API_KEY`, OSS AccessKey or administrator initialization password.

## Authentication and session

- Login state uses `Authorization: Bearer <token>` request header.
- The default validity period of the server session is 7 days; when accessing the protected interface, the expiration time will be slidingly refreshed.
- Passwords are stored using PBKDF2-SHA256 salted hashes.
- The front end currently stores the token in `localStorage`. This is convenient for static front-end use, but if XSS occurs on the page, the token will be exposed together; therefore, the introduction of untrusted scripts is prohibited, and the source must be confirmed when upgrading `web/vendor/` dependencies.

## Input and files

- The JSON API only accepts top-level objects, with a maximum request body of 5 MiB.
- Task title, account, notes, date and Boolean fields are all verified by the backend, not just the frontend.
- Avatar upload is limited to PNG/JPEG/WebP and checks the extension, declared Content-Type, and file signature; the frontend compresses avatars to WebP at up to 256×256, and each avatar is limited to 64 KiB.
- Static file service only allows `index.html`, `app.js`, `i18n.js`, `style.css`, `vendor/`, and `assets/`; avatar file names use allow-list validation to reject directory traversal.

## Administrator function

- Administrator interface requires `role=admin`.
- Deleting a user will cascade clean up the user's tasks, arrangements, habits, conversations, feedback and related logs.
- Download statistics, AI token quota and installation package download quota are only available in the administrator background.

## ManageBac backend synchronization

- ManageBac credentials are used for one sign-in only and are not written to the database or operation log; production rejects credential submission without HTTPS.
- The backend persists only an AES-GCM-encrypted cookie jar. `MANAGEBAC_COOKIE_ENCRYPTION_KEY` must be stored separately from the database.
- Cookies are never returned to the frontend or sent outside `sdgj.managebac.cn`; cross-origin redirects are rejected.
- Expired cookies are deleted and users must enter their credentials again.
- Failed sign-ins are rate-limited per site user and source IP to reduce credential-stuffing risk.
- Do not log the `/api/managebac/session` request body in a reverse proxy, APM, or debug middleware; doing so would bypass the backend's no-persistence boundary for passwords.
- An active cookie is still a sign-in credential. An attacker who compromises both the application server and encryption key may decrypt it.

## Still needs manual attention

- `server.py` is based on the standard library HTTP service and is suitable for small-scale self-use or post-generation use; in high-concurrency scenarios, it is recommended to migrate to mature web frameworks and WSGI/ASGI services.
- AI and OSS are external services. The production environment needs to configure minimum permissions and quota monitoring for the corresponding keys.
- There is currently no automated dependency vulnerability scanning process. When upgrading Electron, Element Plus, Vue or OSS SDK, it is recommended to run the corresponding ecological audit command.
