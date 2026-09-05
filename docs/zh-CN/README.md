# 待办清单时间线

[中文](./README.md) | [English](../en/README.md)

一个面向学习任务管理的待办清单 Web 应用。项目使用静态前端、Python 标准库 HTTP 服务和 SQLite 数据库存储，不需要 Node.js 构建流程；`requirements.txt` 包含头像迁移、ManageBac Cookie 加密和可选 OSS 下载所需的依赖。

## 功能

- 通过 NetHub Accounts 统一登录；TodoList 退出只结束本站会话。
- 按用户隔离任务、每日安排和时间格子配置。
- 新增、编辑、删除、完成或取消完成 DDL 任务。
- 支持任务标题、科目、截止日期时间、优先级和备注。
- 支持未排期待办池，按高、中、低优先级分组。
- DDL 日期时间线，按日期横向浏览任务。
- 每日安排视图，可把任务拖入时间格子生成学习安排。
- 支持一周时间格子模板和单日时间格子覆盖。
- 时间段容量校验，避免安排时长超过可用时间。
- 浅色/深色主题切换。
- 支持由后端使用加密 Cookie 预览导入 ManageBac DDL 任务。

## 技术栈

- 前端：Vue 3、Element Plus，本地静态文件加载。
- 后端：Python 标准库 `http.server` + `sqlite3`；OSS 预签名下载使用 `alibabacloud-oss-v2`。
- 数据库：SQLite，默认写入 `data/todo-list.db`。
- 部署：可直接运行 `server.py`，也可使用 `deploy-first-run.sh` 创建 systemd 用户服务。

## 项目结构

```text
.
├── web/                 # 前端静态文件根目录
│   ├── index.html       # 前端页面结构
│   ├── style.css        # 页面样式
│   ├── app.js           # Vue 应用逻辑
│   ├── i18n.js          # 中英文界面翻译与语言偏好
│   ├── vendor/          # Vue 和 Element Plus 本地依赖
│   └── assets/          # 图标等静态资源
├── server.py            # 静态文件服务、API 服务和 SQLite 初始化
├── managebac_backend.py   # ManageBac 后端登录、Cookie 加密和任务解析
├── managebac-sync-helper/ # 旧版 ManageBac 本地 Helper
├── deploy-first-run.sh  # Linux 首次部署脚本
├── requirements.txt     # 头像压缩、Cookie 加密与可选 OSS 下载依赖
├── .env.example         # 环境变量示例
├── docs/                # 按 zh-CN 和 en 分开的项目文档
├── LICENSE              # MIT 许可证
├── .gitignore           # 忽略 data/ 运行时数据目录
└── README.md
```

运行后会自动生成：

```text
data/
└── todo-list.db
```

## 本地运行

确保已安装 Python 3，然后在项目根目录运行（推荐使用 Conda Python 3.12 环境）：

```bash
pip install -r requirements.txt
python server.py
```

Pillow 用于自动压缩和迁移旧头像，`cryptography` 用于加密 ManageBac Cookie；阿里云 SDK 用于旧版 Helper 的可选 OSS 预签名下载。

安装包下载接口需要用户登录。管理员后台的“下载统计”页可以查看生成次数，并配置全局或单用户的滚动窗口限制。

默认监听：

```text
http://127.0.0.1:8092
```

可通过 `.env` 或环境变量修改监听地址、端口和 AI 配置。项目启动时会自动读取根目录下的 `.env`，且不会覆盖已经存在的系统环境变量。

可以从示例文件复制一份本地配置：

```bash
cp .env.example .env
```

然后按需修改 `.env`。示例内容：

```env
TODO_HOST=127.0.0.1
TODO_PORT=8092
TODO_PUBLIC_URL=https://todolist.nethub.wiki
ACCOUNTS_ISSUER=https://auth.nethub.wiki
TODO_OIDC_CLIENT_ID=todo
TODO_OIDC_CLIENT_SECRET=replace-with-registered-client-secret
TODO_OIDC_REDIRECT_URI=https://todolist.nethub.wiki/auth/callback
TODO_SESSION_COOKIE_SECURE=true
TODO_LEGACY_AUTH_ENABLED=false
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=20
MANAGEBAC_COOKIE_ENCRYPTION_KEY=replace-with-generated-key
```

本机访问通常使用：

```text
http://localhost:8092
```

服务启动时会自动创建 `data/todo-list.db`，并补齐所需 SQLite 表和默认设置。旧数据库可以直接随新版启动，新增表会自动创建；历史 AI token 用量不会回填。

## 首次使用

1. 在 Accounts 注册 TodoList 客户端，回调地址必须精确设置为 TodoList 的 `/auth/callback`，Back-Channel Logout 地址设置为 `/auth/backchannel-logout`。
2. 把客户端密钥及 Issuer 写入 `.env`。
3. 打开 TodoList，点击右上角登录入口并在 Accounts 完成登录。
4. 首次回调会创建本站成员，之后即可新增、编辑、删除和安排任务。

未登录时页面可以打开，但任务列表和每日安排是只读空数据状态，不能保存修改。

## Linux 部署

需要预先安装 Miniconda 或 Anaconda，并确保当前 shell 可以运行 `conda`。项目提供首次部署脚本：

```bash
cd /root/To-do-list
chmod +x deploy-first-run.sh
./deploy-first-run.sh
```

脚本会：

- 检查 `conda` 和项目必需文件。
- 当 `.env` 不存在时，从 `.env.example` 创建，并将权限设置为 `600`；已有 `.env` 不会被覆盖。
- 检查 `MANAGEBAC_COOKIE_ENCRYPTION_KEY`：有效密钥保持不变，缺失或无效时生成新的 32 字节随机密钥，且不会把密钥打印到终端。
- 创建 Conda 环境 `todo-list`（Python 3.12），已存在时直接复用。
- 在该环境中升级 pip，并安装或更新 `requirements.txt`。
- 创建权限为 `700` 的 `data/`，初始化或迁移 SQLite 数据库。
- 默认创建、启用并启动 systemd 用户服务 `todo-list.service`，服务固定使用该 Conda 环境中的 Python。

如需提前设置端口、OIDC 或 AI 配置，可以在首次运行前手动创建 `.env`；否则脚本会自动复制模板，之后再编辑即可。如果使用 Caddy 或 Nginx 反代，`TODO_HOST` 建议保持 `127.0.0.1`，不要开放 Python 服务到公网。

初始化 `.env`、Conda 环境、依赖和数据库，但不创建 systemd 服务：

```bash
./deploy-first-run.sh --no-systemd
```

创建 systemd 服务但不立即启动：

```bash
./deploy-first-run.sh --no-start
```

TodoList 不再创建本地密码管理员。完成 Accounts 客户端配置后，先用中央账号登录一次，再使用不可变的中央 `sub` 授予本地管理员角色：

```bash
conda run -n todo-list python scripts/grant_admin.py \
  --database data/todo-list.db \
  --auth-sub 00000000-0000-0000-0000-000000000000
```

这个命令只修改 TodoList 的本地角色，不会授予 Accounts 或其他网站的管理员权限。迁移的旧管理员会由映射工具保留原有本地角色。

其他环境变量：

- `TODO_CONDA_ENV`：Conda 环境名，默认 `todo-list`。
- `TODO_PYTHON_VERSION`：新建 Conda 环境时使用的 Python 版本，默认 `3.12`；复用已有环境时不会改版本。
- `TODO_SERVICE_NAME`：systemd 用户服务名，默认 `todo-list.service`。
- `TODO_PORT`：覆盖实际监听端口；未通过 shell 设置时读取 `.env` 或程序默认值。脚本最后会打印后端实际读取到的端口。

注意：`TODO_CONDA_ENV`、`TODO_PYTHON_VERSION` 和 `TODO_SERVICE_NAME` 是 shell 脚本读取的初始化参数，不会通过 `.env` 生效。如需自定义，请在运行脚本时直接传入：

```bash
TODO_CONDA_ENV=my-todo-list \
TODO_PYTHON_VERSION=3.12 \
TODO_SERVICE_NAME=my-todo-list.service \
./deploy-first-run.sh
```

脚本生成的用户服务默认位置：

```bash
~/.config/systemd/user/todo-list.service
```

生成后的 service 大致如下：

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

修改 `.env` 或 service 后，重载并重启：

```bash
systemctl --user daemon-reload
systemctl --user restart todo-list.service
systemctl --user status todo-list.service
```

本机检查：

```bash
curl http://127.0.0.1:8092/api/health
```

如果使用 Caddy 反代，示例配置：

```caddyfile
your-domain.com {
    reverse_proxy 127.0.0.1:8092
}
```

## API 文档

完整接口说明见 [API.md](./API.md)。

面向普通用户和管理员的功能说明见 [用户功能手册](./USER_GUIDE.md)。

后端登录、Cookie 加密配置和过期重登流程见 [ManageBac 同步接入说明](./MANAGEBAC_SYNC.md)。

安全边界、部署注意事项和已知剩余风险见 [安全说明](./SECURITY.md)。

浏览器登录使用服务端保存的不透明会话 Cookie；修改数据的请求还必须携带 `/api/auth/me` 返回的 CSRF token：

```http
Cookie: todo_session=<opaque-token>
X-CSRF-Token: <csrf-token>
```

生产硬切换前，先在 Accounts 中导入旧账号并导出映射，然后离线备份 TodoList 数据库并执行：

```bash
conda run -n todo-list python scripts/apply_accounts_mapping.py \
  --database data/todo-list.db \
  --mapping /secure/path/accounts-mapping.json
```

映射必须覆盖全部本站用户。脚本事务化保留本地用户 ID、角色和业务数据，把旧密码移入归档表，清空旧会话，并可用同一映射重复执行。

## 数据说明

SQLite 数据库默认位置：

```text
data/todo-list.db
```

该目录已被 `.gitignore` 忽略，避免提交本地运行数据。服务启动时会启用 SQLite WAL 模式，因此数据库必须放在本机文件系统，不能直接放在 NFS/SMB 等网络文件系统。在线备份请使用 SQLite backup API；也可以先停止服务，再完整备份 `data/` 目录。服务运行时不要只复制 `.db` 文件，以免遗漏 WAL 中尚未 checkpoint 的事务。

切换后本站不再验证或保存可登录的密码。历史 PBKDF2 哈希仅在迁移时进入不可登录的归档表；中央账号负责密码验证。本站会话 token 只以哈希形式存入 SQLite，默认有效期为 7 天。活跃会话会自动延期，但服务端最多每小时刷新一次过期时间。

## 开发说明

项目没有打包步骤。修改前端文件后刷新浏览器即可查看效果；修改后端文件后通常需要重启 `server.py`。

前端依赖已放在 `web/vendor/` 目录：

- `web/vendor/vue.global.prod.js`
- `web/vendor/element-plus.full.min.js`
- `web/vendor/element-plus.css`

因此部署环境不需要访问外部 CDN。以后升级 Vue 或 Element Plus 时，替换 `web/vendor/` 中对应文件即可。

运行测试：

```powershell
python -m pytest -q
cd managebac-sync-helper
npm test
```

后端测试会使用随机端口，不占用默认 `8092`。ManageBac Helper 的 `npm test` 只运行解析器单元测试，不启动本地 `27654` API。

## 许可证

本项目使用 MIT License，详见 `LICENSE`。
