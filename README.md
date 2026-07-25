<div align="center">

# To-Do List Timeline

**A self-hosted study planner that turns deadlines into a practical daily schedule.**

[![Tests](https://github.com/kuxiaowo/To-do-list/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/kuxiaowo/To-do-list/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/Vue-3-42b883?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-97CA00)](./LICENSE)

[![GitHub stars](https://img.shields.io/github/stars/kuxiaowo/To-do-list?style=flat&logo=github&label=Stars)](https://github.com/kuxiaowo/To-do-list/stargazers)
[![Last commit](https://img.shields.io/github/last-commit/kuxiaowo/To-do-list?logo=git&label=Last%20commit)](https://github.com/kuxiaowo/To-do-list/commits/main)
[![No build step](https://img.shields.io/badge/Frontend-No%20build%20step-6E40C9)](./docs/en/README.md#development-instructions)

[**English**](./README.md) | [**简体中文**](./docs/zh-CN/README.md)

[![Read the docs](https://img.shields.io/badge/Docs-Read%20the%20guide-0969DA?logo=readthedocs&logoColor=white)](./docs/en/README.md)
[![API reference](https://img.shields.io/badge/API-Reference-00897B?logo=bookstack&logoColor=white)](./docs/en/API.md)
[![User guide](https://img.shields.io/badge/Guide-User%20manual-F57C00?logo=gitbook&logoColor=white)](./docs/en/USER_GUIDE.md)
[![Security](https://img.shields.io/badge/Security-Notes-C62828?logo=securityscorecard&logoColor=white)](./docs/en/SECURITY.md)

</div>

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
- Preview and import ManageBac deadlines through the local desktop Helper.
- Switch between English and Simplified Chinese, as well as light and dark themes.
- Deploy with Python alone or install a systemd user service with the included script.

## Technology

| Layer | Technology |
| --- | --- |
| Front end | Vue 3, Element Plus, vanilla JavaScript |
| Back end | Python standard library `http.server` |
| Database | SQLite |
| Optional integration | DeepSeek API, Alibaba Cloud OSS |
| Desktop Helper | Electron |

The front-end libraries are stored in `web/vendor`, so production deployment
does not depend on an external CDN.

## Quick start

Python 3.10 or newer is required.

```bash
git clone https://github.com/kuxiaowo/To-do-list.git
cd To-do-list
python server.py
```

Then open <http://localhost:8092>.

The application creates `data/todo-list.db` automatically on first launch.
To customize the listening address, port, or optional AI integration, copy the
environment example first:

```bash
cp .env.example .env
```

If you enable Alibaba Cloud OSS downloads for the ManageBac Helper installer,
install the optional dependency:

```bash
python -m pip install -r requirements.txt
```

See the [English documentation](./docs/en/README.md) or
[中文文档](./docs/zh-CN/README.md) for complete configuration and deployment
instructions.

## Project layout

```text
.
├── web/                       # Static Vue front end
├── server.py                  # HTTP service, API, and database initialization
├── ai_prompts.json            # AI assistant prompts
├── managebac-sync-helper/     # Optional Electron desktop Helper
├── tests/                     # Backend and workflow regression tests
├── docs/
│   ├── en/                    # English documentation
│   └── zh-CN/                 # Simplified Chinese documentation
├── deploy-first-run.sh        # First-run Linux deployment helper
├── requirements.txt           # Optional OSS dependency
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
| ManageBac Helper | [Read](./managebac-sync-helper/docs/en/README.md) | [阅读](./managebac-sync-helper/docs/zh-CN/README.md) |

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
