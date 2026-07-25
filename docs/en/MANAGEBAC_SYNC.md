# ManageBac synchronization access instructions

[中文](../zh-CN/MANAGEBAC_SYNC.md) | [English](./MANAGEBAC_SYNC.md)

## Design boundaries

ManageBac synchronization consists of three parts:

```text
managebac-sync://wake evoke local Helper
http://127.0.0.1:27654 local API Responsible for logging in, crawling and parsing
The web page is responsible for preview, confirmation and import
```

The custom protocol is only responsible for waking up local programs and does not pass cookies, accounts, passwords, website tokens or task data.

## Helper run

The official Helper is located at:

```text
managebac-sync-helper/
```

Development starts:

```powershell
cd managebac-sync-helper
npm.cmd install
npm.cmd run dev
```

After production packaging, the Helper will be registered for the first time:

```text
managebac-sync://
```

Development mode does not automatically register protocols to avoid polluting the native protocol configuration.

## Allowed website sources

Helper local API only listens to:

```text
127.0.0.1:27654
```

Allows local development sites and official sites by default:

```text
http://localhost:8092
http://127.0.0.1:8092
https://nethub.wiki
https://www.nethub.wiki
```

When the remote website goes online, it needs to be configured in the Helper running environment:

```powershell
$env:MANAGEBAC_ALLOWED_ORIGINS="https://your-site.example"
```

Multiple sources separated by commas.

## Web page process

After the user clicks "Sync ManageBac":

1. Web page request `GET /v1/health`.
2. If the Helper does not respond, the web page opens `managebac-sync://wake?nonce=...`.
3. The web page polls the local Helper.
4. Web page call `POST /v1/session/start` to establish a short-term local session.
5. Call `GET /v1/session` on the web page to check the ManageBac login status.
6. When you are not logged in or your login has expired, the web page displays the "Open login window" button.
7. After the user clicks, the web page calls `POST /v1/login/open`, and the Helper pops up or focuses on the ManageBac login window.
8. After logging in, the web page calls `POST /v1/tasks/preview` to obtain the parsing results; the Helper only returns the ManageBac class/course name and is not responsible for identifying the website subjects.
9. The webpage pre-fills the subjects according to its own subject template and displays the preview list. After the user confirms, it is imported through the existing `/api/tasks`.

## Local API

### `GET /v1/health`

Returns Helper status, version, port and protocol registration status.

### `POST /v1/session/start`

Request:

```json
{
  "nonce": "browser-generated-random-value"
}
```

Response:

```json
{
  "ok": true,
  "clientToken": "short-lived-token",
  "expiresInSeconds": 600
}
```

Subsequent protected interfaces require request headers:

```http
X-ManageBac-Client-Token: <clientToken>
```

### `GET /v1/session`

Returns the ManageBac login status in the Helper's own Electron profile.

### `POST /v1/login/open`

Opens or focuses the ManageBac login window.

### `POST /v1/tasks/preview`

Fetch the `Tasks & Deadlines` page, parse the task and return the preview list.

Task item example:

```json
{
  "source": "managebac",
  "sourceId": "core_task:27421385",
  "sourceUrl": "https://sdgj.managebac.cn/student/classes/11465612/core_tasks/27421385",
  "title": "Final Group Project",
  "subject": "",
  "className": "HS Computer（25level elective） (Grade 10)",
  "rawCourseName": "HS Computer（25level elective） (Grade 10)",
  "dueAt": "2026-06-21T23:55:00",
  "priority": "medium",
  "note": "ManageBac: core_task:27421385"
}
```

### `POST /v1/session/clear`

Clear Helper's own ManageBac login status.

## Import strategy

- By default, it only previews and does not automatically write to the task library.
- The existing `/api/tasks` creation task is called only after the user checks it.
- Helper does not recognize the account; the website prefills it from `className/rawCourseName` according to the account template. If the task is still unrecognized, the account must be filled in the preview first.
- Existing tasks cannot be checked by default; the current basis is `ManageBac: core_task:<id>` remarks or title, subject, and deadline matching.
