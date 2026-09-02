#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="${TODO_SERVICE_NAME:-todo-list.service}"
CONDA_ENV_NAME="${TODO_CONDA_ENV:-todo-list}"
CONDA_PYTHON_VERSION="${TODO_PYTHON_VERSION:-3.12}"
INSTALL_SYSTEMD=1
START_SERVICE=1

usage() {
  cat <<'EOF'
Todo List 第一次部署脚本

用法：
  ./deploy-first-run.sh [选项]

选项：
  --no-systemd   初始化环境、依赖和数据库，但不创建/启动 systemd 用户服务
  --no-start     创建 systemd 用户服务，但不立即启动
  -h, --help     显示帮助

可选环境变量：
  TODO_ADMIN_NICKNAME   预创建管理员昵称
  TODO_ADMIN_NAME       预创建管理员姓名，默认同昵称
  TODO_ADMIN_PASSWORD   预创建管理员密码；为空则不创建管理员
  TODO_CONDA_ENV        Conda 环境名，默认 todo-list
  TODO_PYTHON_VERSION   Conda Python 版本，默认 3.12
  TODO_SERVICE_NAME     systemd 服务名，默认 todo-list.service
  TODO_PORT             覆盖实际监听端口；未设置时读取 .env 或程序默认值

示例：
  chmod +x deploy-first-run.sh
  TODO_ADMIN_NICKNAME=kuxiaowo TODO_ADMIN_PASSWORD='换成强密码' ./deploy-first-run.sh

说明：
  - 需要预先安装 Conda，并确保 conda 命令可用
  - .env 不存在时会从 .env.example 创建
  - ManageBac Cookie 加密密钥缺失或无效时会随机生成，不会覆盖有效密钥
  - 数据库使用 SQLite，文件位于 ./data/todo-list.db
  - 不需要安装 MySQL/PostgreSQL
  - Python 依赖安装在独立 Conda 环境中
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-systemd)
      INSTALL_SYSTEMD=0
      ;;
    --no-start)
      START_SERVICE=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

log() {
  printf '[todo-list deploy] %s\n' "$*"
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令: $1" >&2
    echo "请先安装 Miniconda/Anaconda，并确保 conda 命令可在当前 shell 中使用。" >&2
    exit 1
  fi
}

need_cmd conda

log "应用目录: $APP_DIR"
cd "$APP_DIR"

if [[ ! -f server.py || ! -f web/index.html || ! -f requirements.txt || ! -f .env.example ]]; then
  echo "当前目录缺少 server.py、web/index.html、requirements.txt 或 .env.example，请在完整的 todo-list 目录内运行。" >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
  log "从 .env.example 创建 .env。"
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
else
  log "检测到已有 .env，保留现有配置。"
fi
chmod 600 "$APP_DIR/.env"

if conda run -n "$CONDA_ENV_NAME" python -c 'import sys' >/dev/null 2>&1; then
  log "复用 Conda 环境: $CONDA_ENV_NAME"
else
  log "创建 Conda 环境: $CONDA_ENV_NAME (Python $CONDA_PYTHON_VERSION)"
  conda create --yes --name "$CONDA_ENV_NAME" "python=$CONDA_PYTHON_VERSION"
fi

PYTHON_BIN="$(conda run -n "$CONDA_ENV_NAME" python -c 'import sys; print(sys.executable)')"
PYTHON_BIN="${PYTHON_BIN//$'\r'/}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "无法确定 Conda 环境 $CONDA_ENV_NAME 的 Python 路径。" >&2
  exit 1
fi

log "检查 ManageBac Cookie 加密密钥。"
TODO_ENV_PATH="$APP_DIR/.env" "$PYTHON_BIN" - <<'PY'
import base64
import binascii
import os
import re
import secrets
from pathlib import Path

key_name = 'MANAGEBAC_COOKIE_ENCRYPTION_KEY'
env_path = Path(os.environ['TODO_ENV_PATH'])
lines = env_path.read_text(encoding='utf-8').splitlines()
assignment = re.compile(rf'^\s*{re.escape(key_name)}\s*=')
active_indexes = [index for index, line in enumerate(lines) if assignment.match(line)]


def valid_key(value: str) -> bool:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    try:
        decoded = base64.b64decode(value.encode('ascii'), altchars=b'-_', validate=True)
    except (UnicodeEncodeError, binascii.Error):
        return False
    return len(decoded) == 32


current_value = lines[active_indexes[0]].split('=', 1)[1] if active_indexes else ''
if active_indexes and valid_key(current_value):
    print('ManageBac Cookie encryption key: kept existing value')
else:
    generated = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii')
    new_assignment = f'{key_name}={generated}'
    if active_indexes:
        lines[active_indexes[0]] = new_assignment
    else:
        if lines and lines[-1].strip():
            lines.append('')
        lines.append(new_assignment)
    temporary_path = env_path.with_name(f'{env_path.name}.tmp.{os.getpid()}')
    temporary_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    os.chmod(temporary_path, 0o600)
    os.replace(temporary_path, env_path)
    print('ManageBac Cookie encryption key: generated')
PY

log "在 Conda 环境中安装或更新 Python 依赖。"
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install --upgrade -r "$APP_DIR/requirements.txt"

log "创建数据目录并初始化 SQLite 数据库。"
mkdir -p "$APP_DIR/data"
chmod 700 "$APP_DIR/data"

"$PYTHON_BIN" - <<'PY'
import importlib.util
import os
import sqlite3
from pathlib import Path

app_dir = Path.cwd()
spec = importlib.util.spec_from_file_location('todo_server', app_dir / 'server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
server.init_db()

nickname = os.environ.get('TODO_ADMIN_NICKNAME', '').strip()
password = os.environ.get('TODO_ADMIN_PASSWORD', '')
name = os.environ.get('TODO_ADMIN_NAME', '').strip() or nickname

if nickname and password:
    with sqlite3.connect(server.DB_PATH) as conn:
        row = conn.execute('SELECT id FROM users WHERE lower(nickname) = lower(?)', (nickname,)).fetchone()
        password_hash = server.hash_password(password)
        if row:
            conn.execute(
                'UPDATE users SET name = ?, password_hash = ?, role = ? WHERE id = ?',
                (name, password_hash, 'admin', row[0]),
            )
            action = 'updated'
        else:
            conn.execute(
                'INSERT INTO users (name, nickname, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
                (name, nickname, password_hash, 'admin', server.now_iso()),
            )
            action = 'created'
        conn.commit()
    print(f'admin {action}: {nickname}')
elif nickname or password:
    raise SystemExit('TODO_ADMIN_NICKNAME 和 TODO_ADMIN_PASSWORD 需要同时设置。')
else:
    print('admin skipped: 可在网页里注册第一个账号。')

print(f'database ready: {server.DB_PATH}')
PY

if [[ "$INSTALL_SYSTEMD" == "1" ]]; then
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "未找到 systemctl，已完成环境、依赖和数据库初始化。" >&2
    echo "可手动运行: $PYTHON_BIN $APP_DIR/server.py" >&2
  else
    SERVICE_DIR="$HOME/.config/systemd/user"
    SERVICE_FILE="$SERVICE_DIR/$SERVICE_NAME"
    mkdir -p "$SERVICE_DIR"

    log "写入 systemd 用户服务: $SERVICE_FILE"
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Todo List Web App
After=network.target

[Service]
WorkingDirectory=$APP_DIR
ExecStart="$PYTHON_BIN" "$APP_DIR/server.py"
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"

    if [[ "$START_SERVICE" == "1" ]]; then
      systemctl --user restart "$SERVICE_NAME"
      log "服务状态: $(systemctl --user is-active "$SERVICE_NAME")"
    else
      log "已创建服务，但按 --no-start 要求未启动。"
    fi

    if command -v loginctl >/dev/null 2>&1; then
      log "提示：如需退出 SSH 后服务继续运行，可执行：loginctl enable-linger $USER"
    fi
  fi
else
  log "已按 --no-systemd 要求跳过 systemd 服务创建。"
fi

PORT="$("$PYTHON_BIN" -c 'import server; print(server.PORT)')"
log "部署完成。访问地址通常是: http://服务器IP:${PORT}"
log "如启用防火墙，请放行: sudo ufw allow ${PORT}/tcp"
