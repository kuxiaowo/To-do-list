# nethub.wiki ManageBac sync helper

[中文](../zh-CN/README.md) | [English](./README.md)

This is the native Windows synchronization helper for nethub.wiki. It is responsible for opening the ManageBac login window on the local machine, saving the Helper's own login cookie, and returning the parsed task preview data to the website.

The website invokes this application via the following custom protocol:

```text
managebac-sync://wake
```

After starting, the Helper only listens to the local address:

```text
http://127.0.0.1:27654
```

The custom protocol only launches the application; it does not pass cookies, account passwords, website tokens, or task data. Status checks, opening the login window, and task fetching all use the local HTTP API at `127.0.0.1`.

## Development and running

This directory contains project-level `.npmrc`, which uses npmmirror by default to accelerate npm packages, Electron and electron-builder to assist binary downloads.

```powershell
npm.cmd install
npm.cmd run dev
```

Development mode starts the local API but does not register the `managebac-sync://` custom protocol. Custom protocol registration is only performed in the packaged production version. When developing and testing, you can manually run the Helper first, and then call the local API from the website button.

The system tray icon will be displayed after startup. Right-click the tray icon to view the current status, open the login window, view application instructions and security, or exit the Helper.

## Packaging

```powershell
npm.cmd run dist
```

The installation package will be generated to:

```text
dist/
```

## Local API

- `GET /v1/health`
- `POST /v1/session/start`
- `GET /v1/session`
- `POST /v1/login/open`
- `POST /v1/tasks/preview`
- `POST /v1/session/clear`

To allow additional website sources to access the local API, you can set:

```powershell
$env:MANAGEBAC_ALLOWED_ORIGINS="https://example.com,http://localhost:8092"
```

Local development sources `localhost:8092` and `127.0.0.1:8092` are allowed by default.

## Security boundary

- This is the ManageBac local sync helper for `nethub.wiki`.
- Only reads cookies from this Electron application's own profile.
- Do not read Chrome browser cookies.
- Do not read or save the ManageBac account password.
- Do not send cookies to the website; the website only receives the parsed task preview data.
- Do not write the original cookie value to the project file.
- API only binds to `127.0.0.1`.
- Session, login, and preview interfaces require short-lived local client tokens.
