# ManageBac Sync Helper

Local Windows helper for the To-Do List website.

The website wakes this app with:

```text
managebac-sync://wake
```

After startup, the helper listens only on:

```text
http://127.0.0.1:27654
```

The custom protocol is only a wake signal. Cookies, account credentials, website tokens, and task data are not passed through the protocol URL.

## Development

```powershell
npm.cmd install
npm.cmd run dev
```

The development run starts the local API, but production protocol registration happens only in packaged builds. Use the website button to call the local API.

## Local API

- `GET /v1/health`
- `POST /v1/session/start`
- `GET /v1/session`
- `POST /v1/login/open`
- `POST /v1/tasks/preview`
- `POST /v1/session/clear`

Set allowed browser origins with:

```powershell
$env:MANAGEBAC_ALLOWED_ORIGINS="https://example.com,http://localhost:8092"
```

Local development origins for `localhost:8092` and `127.0.0.1:8092` are allowed by default.

## Security Boundary

- Reads cookies only from this app's Electron profile.
- Does not read Chrome cookies.
- Does not store raw cookie values in files.
- Binds the API to `127.0.0.1` only.
- Requires a short-lived local client token for session, login, and preview endpoints.
