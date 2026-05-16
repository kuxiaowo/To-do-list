#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="${TODO_SERVICE_NAME:-todo-list.service}"
PORT="${TODO_PORT:-8092}"
INSTALL_SYSTEMD=1
START_SERVICE=1

usage() {
  cat <<'EOF'
Todo List 第一次部署脚本

用法：
  ./deploy-first-run.sh [选项]

选项：
  --no-systemd   只初始化数据库，不创建/启动 systemd 用户服务
  --no-start     创建 systemd 用户服务，但不立即启动
  -h, --help     显示帮助

可选环境变量：
  TODO_ADMIN_NICKNAME   预创建管理员昵称
  TODO_ADMIN_NAME       预创建管理员姓名，默认同昵称
  TODO_ADMIN_PASSWORD   预创建管理员密码；为空则不创建管理员
  TODO_SERVICE_NAME     systemd 服务名，默认 todo-list.service
  TODO_PORT             仅写入提示信息；当前 server.py 默认监听 8092

示例：
  chmod +x deploy-first-run.sh
  TODO_ADMIN_NICKNAME=kuxiaowo TODO_ADMIN_PASSWORD='换成强密码' ./deploy-first-run.sh

说明：
  - 数据库使用 SQLite，文件位于 ./data/todo-list.db
  - 不需要安装 MySQL/PostgreSQL
  - Python 的 sqlite3 模块随 Python 标准库提供
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
    echo "Ubuntu/Debian 可执行: sudo apt update && sudo apt install -y python3" >&2
    exit 1
  fi
}

need_cmd python3

log "应用目录: $APP_DIR"
cd "$APP_DIR"

if [[ ! -f server.py || ! -f index.html ]]; then
  echo "当前目录缺少 server.py 或 index.html，请在解压后的 todo-list 目录内运行。" >&2
  exit 1
fi

log "创建数据目录并初始化 SQLite 数据库。"
mkdir -p "$APP_DIR/data"
chmod 700 "$APP_DIR/data"

python3 - <<'PY'
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
    echo "未找到 systemctl，已完成数据库初始化；请用 python3 server.py 手动运行。" >&2
    exit 0
  fi

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
ExecStart=/usr/bin/env python3 $APP_DIR/server.py
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
else
  log "已按 --no-systemd 要求跳过 systemd 服务创建。"
fi

log "部署完成。访问地址通常是: http://服务器IP:${PORT}"
log "如启用防火墙，请放行: sudo ufw allow ${PORT}/tcp"
