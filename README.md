<div align="center">

<br>

<img src="./web/assets/favicon.png" alt="To-Do List Timeline logo" width="144" height="144">

<h1>To-Do List Timeline</h1>

<p><strong>A self-hosted study planner that turns deadlines into a practical daily schedule.</strong></p>

<p>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10+"></a>
  <a href="https://vuejs.org/"><img src="https://img.shields.io/badge/Frontend-Vue%203-42b883?logo=vuedotjs&amp;logoColor=white" alt="Vue 3"></a>
  <a href="https://www.sqlite.org/"><img src="https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&amp;logoColor=white" alt="SQLite"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-8A2BE2" alt="MIT License"></a>
</p>

<p>
  <a href="https://github.com/kuxiaowo/To-do-list/actions/workflows/tests.yml"><img src="https://github.com/kuxiaowo/To-do-list/actions/workflows/tests.yml/badge.svg?branch=main" alt="Tests"></a>
  <a href="https://github.com/kuxiaowo/To-do-list/stargazers"><img src="https://img.shields.io/github/stars/kuxiaowo/To-do-list?style=flat&amp;logo=github&amp;label=Stars" alt="GitHub stars"></a>
  <a href="https://github.com/kuxiaowo/To-do-list/commits/main"><img src="https://img.shields.io/github/last-commit/kuxiaowo/To-do-list?logo=git&amp;label=Last%20commit" alt="Last commit"></a>
</p>

<p><strong>English</strong> | <a href="./README.zh-CN.md">简体中文</a></p>

<p>
  <a href="./docs/en/README.md"><img src="https://img.shields.io/badge/Docs-Setup%20guide-0969DA?logo=readthedocs&amp;logoColor=white" alt="Setup guide"></a>
  <a href="./docs/en/API.md"><img src="https://img.shields.io/badge/API-Reference-00897B?logo=bookstack&amp;logoColor=white" alt="API reference"></a>
  <a href="./docs/en/USER_GUIDE.md"><img src="https://img.shields.io/badge/Guide-User%20manual-F57C00?logo=gitbook&amp;logoColor=white" alt="User guide"></a>
</p>

</div>

---

## Overview

To-Do List Timeline is a bilingual web application for managing study
deadlines, unscheduled work, habits, and daily plans. It combines a Vue 3
static front end with a lightweight Python HTTP service and SQLite storage.
There is no Node.js build step for the main web application.

## Highlights

- Manage deadline tasks with subjects, priorities, notes, and completion states.
- Keep unscheduled tasks in a priority-grouped planning pool.
- Browse deadlines on a horizontal timeline or calendar.
- Drag tasks into configurable time slots to create daily study plans.
- Maintain recurring habits and detect schedule conflicts.
- Keep accounts, tasks, schedules, and settings isolated by user.
- Use the optional AI assistant to review or propose task changes before applying them.
- Preview and import ManageBac deadlines through backend-stored encrypted cookies.
- Switch between English and Simplified Chinese, as well as light and dark themes.
- Deploy with Python alone or install a systemd user service with the included script.

## Technology

| Layer | Technology |
| --- | --- |
| Front end | Vue 3, Element Plus, vanilla JavaScript |
| Back end | Python standard library `http.server` |
| Database | SQLite |
| Optional integration | DeepSeek API, ManageBac, Alibaba Cloud OSS |

The front-end libraries are stored in `web/vendor`, so production deployment
does not depend on an external CDN.

## Quick start

Python 3.10 or newer is required.

```bash
git clone https://github.com/kuxiaowo/To-do-list.git
cd To-do-list
python -m pip install -r requirements.txt
python server.py
```

Then open <http://localhost:8092>.

The application creates `data/todo-list.db` automatically on first launch.
To customize the listening address, port, or optional AI integration, copy the
environment example first:

```bash
cp .env.example .env
```

Pillow compresses and migrates avatars, `cryptography` encrypts ManageBac cookies,
and the Alibaba Cloud SDK supports the optional legacy Helper OSS download.

See the [English documentation](./docs/en/README.md) or
[中文文档](./docs/zh-CN/README.md) for complete configuration and deployment
instructions.

## Project layout

```text
.
├── web/                       # Static Vue front end
├── server.py                  # HTTP service, API, and database initialization
├── managebac_backend.py       # ManageBac sign-in, cookie encryption, and task parsing
├── ai_prompts.json            # AI assistant prompts
├── managebac-sync-helper/     # Legacy Electron Helper (no longer required by the site)
├── tests/                     # Backend and workflow regression tests
├── docs/
│   ├── en/                    # English documentation
│   └── zh-CN/                 # Simplified Chinese documentation
├── deploy-first-run.sh        # First-run Linux deployment helper
├── requirements.txt           # Avatar, cookie encryption, and optional OSS dependencies
└── LICENSE
```

## Documentation

| Document | English | 简体中文 |
| --- | --- | --- |
| Full setup and deployment | [Read](./docs/en/README.md) | [阅读](./docs/zh-CN/README.md) |
| API reference | [Read](./docs/en/API.md) | [阅读](./docs/zh-CN/API.md) |
| User guide | [Read](./docs/en/USER_GUIDE.md) | [阅读](./docs/zh-CN/USER_GUIDE.md) |
| ManageBac integration | [Read](./docs/en/MANAGEBAC_SYNC.md) | [阅读](./docs/zh-CN/MANAGEBAC_SYNC.md) |
| Security notes | [Read](./docs/en/SECURITY.md) | [阅读](./docs/zh-CN/SECURITY.md) |

## Development

The main application has no packaging step. Refresh the browser after changing
front-end files, and restart `server.py` after changing the back end.

Run the backend test suite:

```bash
python -m unittest discover -s tests -v
```

Run the ManageBac Helper parser tests:

```bash
cd managebac-sync-helper
npm test
```

Both suites are also run by GitHub Actions on pushes and pull requests.

## License

Released under the [MIT License](./LICENSE).
