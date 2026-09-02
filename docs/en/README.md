# To-Do List Timeline

[中文](../zh-CN/README.md) | [English](./README.md)

A to-do list web application for learning task management. The project uses a static front end, Python standard library HTTP service and SQLite database storage, and does not require a Node.js build process; `requirements.txt` includes dependencies for avatar migration, ManageBac cookie encryption, and optional OSS downloads.

## Function

- Account registration, login, and logout.
- Isolate tasks, daily schedules and time grid configurations by user.
- Add, edit, delete, complete or cancel DDL tasks.
- Supports task title, account, deadline time, priority and notes.
- Supports unqueued to-do pools, grouped by high, medium, and low priority.
- DDL date timeline, browse tasks horizontally by date.
- Daily schedule view, you can drag tasks into the time grid to generate learning schedules.
- Supports one-week time grid template and single-day time grid overlay.
- Time period capacity verification to avoid scheduling longer than available time.
- Light/dark theme switching.
- Supports importing ManageBac deadlines through backend-stored encrypted cookies.

## Technology stack

- Front-end: Vue 3, Element Plus, local static file loading.
- Backend: Python standard library `http.server` + `sqlite3`; OSS pre-signed download uses `alibabacloud-oss-v2`.
- Database: SQLite, default writes `data/todo-list.db`.
- Deployment: You can run `server.py` directly, or use `deploy-first-run.sh` to create a systemd user service.

## Project structure

```text
.
├── web/                 # Front-end static file root directory
│   ├── index.html       # Front-end page structure
│   ├── style.css        # Page style
│   ├── app.js           # Vue application logic
│   ├── i18n.js          # Chinese/English UI translations and language preference
│   ├── vendor/          # Vue and Element Plus Local dependencies
│   └── assets/          # Static resources such as icons
├── server.py            # Static file service、API Services and SQLite initialization
├── managebac_backend.py   # ManageBac backend sign-in, cookie encryption, and task parsing
├── managebac-sync-helper/ # Legacy ManageBac local Helper
├── deploy-first-run.sh  # Linux First deployment script
├── requirements.txt     # Avatar, cookie encryption, and optional OSS dependencies
├── .env.example         # Environment variable example
├── docs/                # Project documentation separated into zh-CN and en
├── LICENSE              # MIT License
├── .gitignore           # ignore data/ Runtime data directory
└── README.md
```

will be automatically generated after running:

```text
data/
└── todo-list.db
```

## Run locally

Make sure Python 3 is installed, then run:

```bash
pip install -r requirements.txt
python server.py
```

Pillow compresses and migrates old avatars, `cryptography` encrypts ManageBac cookies, and the Alibaba Cloud SDK supports optional legacy Helper OSS downloads.

The installation package download interface requires user login. The "Download Statistics" page in the administrator's backend allows you to view the number of generations and configure global or single-user rolling window limits.

Default listening:

```text
http://127.0.0.1:8092
```

The listening address, port and AI configuration can be modified through `.env` or environment variables. When the project starts, it will automatically read `.env` in the root directory and will not overwrite existing system environment variables.

You can copy a local configuration from the example file:

```bash
cp .env.example .env
```

Then modify `.env` as needed. Example content:

```env
TODO_HOST=127.0.0.1
TODO_PORT=8092
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=20
MANAGEBAC_COOKIE_ENCRYPTION_KEY=replace-with-generated-key
```

Native access typically uses:

```text
http://localhost:8092
```

`data/todo-list.db` will be automatically created when the service starts, and the required SQLite tables and default settings will be completed. The old database can be started directly with the new version, and new tables will be automatically created; historical AI token usage will not be backfilled.

## First time use

1. Open `http://localhost:8092`.
2. Click the account entry in the upper right corner.
3. Register a new account.
4. After logging in, you can add, edit, delete and schedule tasks.

The page can be opened when not logged in, but the task list and daily schedule are in a read-only empty data state and modifications cannot be saved.

## Linux deployment

Install Miniconda or Anaconda first and make sure `conda` is available in the current shell. The project provides a first-run deployment script:

```bash
cd /root/To-do-list
chmod +x deploy-first-run.sh
./deploy-first-run.sh
```

The script will:

- Check `conda` and the required project files.
- Create `.env` from `.env.example` when it is missing and set mode `600`; an existing `.env` is never overwritten.
- Validate `MANAGEBAC_COOKIE_ENCRYPTION_KEY`: keep a valid value, or generate a new random 32-byte key when it is missing or invalid, without printing the key.
- Create the `todo-list` Conda environment with Python 3.12, or reuse it when it already exists.
- Upgrade pip and install or update `requirements.txt` in that environment.
- Create `data/` with mode `700` and initialize or migrate the SQLite database.
- Create, enable, and start the `todo-list.service` systemd user service by default, using the exact Python executable from the Conda environment.

To set the port, AI, or administrator options before the first run, create `.env` manually; otherwise the script copies the template and you can edit it afterward. With a Caddy or Nginx reverse proxy, keep `TODO_HOST=127.0.0.1` instead of exposing the Python service publicly.

Initialize `.env`, the Conda environment, dependencies, and the database without creating a systemd service:

```bash
./deploy-first-run.sh --no-systemd
```

Create the systemd service but do not start it immediately:

```bash
./deploy-first-run.sh --no-start
```

Optional environment variables:

```bash
TODO_ADMIN_NICKNAME=admin \
TODO_ADMIN_NAME=Administrator \
TODO_ADMIN_PASSWORD='change-this-password' \
./deploy-first-run.sh
```

You can also write the administrator initialization configuration into `.env`:

```env
TODO_ADMIN_NICKNAME=admin
TODO_ADMIN_NAME=Administrator
TODO_ADMIN_PASSWORD=change-this-password
```

`deploy-first-run.sh` will import `server.py` when initializing the database, and `server.py` will read `.env`, so these administrator variables can take effect from `.env`. When you run the script again, if the nickname already exists, the account will be updated to administrator and the password will be reset.

If only `TODO_ADMIN_NICKNAME` or only `TODO_ADMIN_PASSWORD` is set, the script will report an error and exit; both need to be set at the same time. After the deployment is completed, it is recommended to remove the clear text administrator password from `.env`. Don’t hang the key at the door. Everyone will know it when the wind blows.

Other environment variables:

- `TODO_CONDA_ENV`: Conda environment name, default `todo-list`.
- `TODO_PYTHON_VERSION`: Python version used only when creating a new environment, default `3.12`; an existing environment is not changed.
- `TODO_SERVICE_NAME`: systemd user service name, default `todo-list.service`.
- `TODO_PORT`: overrides the actual listener port; otherwise the value comes from `.env` or the program default. The script prints the port read by the backend at the end.

`TODO_CONDA_ENV`, `TODO_PYTHON_VERSION`, and `TODO_SERVICE_NAME` are initialization parameters read by the shell script and do not take effect through `.env`. Pass them directly when running the script:

```bash
TODO_CONDA_ENV=my-todo-list \
TODO_PYTHON_VERSION=3.12 \
TODO_SERVICE_NAME=my-todo-list.service \
./deploy-first-run.sh
```

Default location of user service generated by script:

```bash
~/.config/systemd/user/todo-list.service
```

The generated service is roughly as follows:

```ini
[Unit]
Description=Todo List Web App
After=network.target

[Service]
WorkingDirectory=/root/To-do-list
ExecStart="/root/miniconda3/envs/todo-list/bin/python" "/root/To-do-list/server.py"
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
```

After modifying `.env` or service, reload and restart:

```bash
systemctl --user daemon-reload
systemctl --user restart todo-list.service
systemctl --user status todo-list.service
```

Native check:

```bash
curl http://127.0.0.1:8092/api/health
```

If using Caddy anti-generation, example configuration:

```caddyfile
your-domain.com {
    reverse_proxy 127.0.0.1:8092
}
```

## API documentation

For complete interface description, see [API.md](./API.md).

For function descriptions for ordinary users and administrators, see [User Function Manual](./USER_GUIDE.md).

For backend sign-in, cookie encryption, and reauthentication details, see the [ManageBac Sync Integration Guide](./MANAGEBAC_SYNC.md).

See [Security Notes](./SECURITY.md) for security boundaries, deployment considerations, and known residual risks.

The interface that needs to log in passes the token through the request header:

```http
Authorization: Bearer <token>
```

## Data description

SQLite database default location:

```text
data/todo-list.db
```

This directory has been ignored by `.gitignore` to avoid submitting local running data. SQLite WAL mode is enabled when the service starts, so the database must be placed in the local file system and cannot be placed directly in network file systems such as NFS/SMB. Please use the SQLite backup API for online backup; you can also stop the service first and then fully back up the `data/` directory. Do not just copy the `.db` file when the service is running to avoid missing transactions that have not been checkpointed in the WAL.

The password is stored using PBKDF2-SHA256 salted hash; the default validity period of the session token is 7 days. Active sessions are automatically extended, but the server refreshes the expiration time at most every hour to reduce database write lock competition caused by read-only requests.

## Development instructions

There is no packaging step for the project. After modifying the front-end file, refresh the browser to see the effect; after modifying the back-end file, you usually need to restart `server.py`.

The front-end dependencies have been placed in the `web/vendor/` directory:

- `web/vendor/vue.global.prod.js`
- `web/vendor/element-plus.full.min.js`
- `web/vendor/element-plus.css`

Therefore the deployment environment does not require access to an external CDN. When upgrading Vue or Element Plus in the future, just replace the corresponding files in `web/vendor/`.

Run the test:

```powershell
python -m pytest -q
cd managebac-sync-helper
npm test
```

The backend test will use a random port and does not occupy the default `8092`. ManageBac Helper's `npm test` only runs the parser unit tests and does not start the local `27654` API.

## License

This project uses the MIT License, see `LICENSE` for details.
