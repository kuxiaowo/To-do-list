# 待办清单时间线

一个面向学习任务管理的待办清单 Web 应用。项目使用静态前端、Python 标准库 HTTP 服务和 SQLite 数据库存储，不需要 Node.js 构建流程；如启用 OSS 安装包下载，需要安装 `requirements.txt` 中的 Python 依赖。

## 功能

- 账号注册、登录、退出登录。
- 按用户隔离任务、每日安排和时间格子配置。
- 新增、编辑、删除、完成或取消完成 DDL 任务。
- 支持任务标题、科目、截止日期时间、优先级和备注。
- 支持未排期待办池，按高、中、低优先级分组。
- DDL 日期时间线，按日期横向浏览任务。
- 每日安排视图，可把任务拖入时间格子生成学习安排。
- 支持一周时间格子模板和单日时间格子覆盖。
- 时间段容量校验，避免安排时长超过可用时间。
- 浅色/深色主题切换。
- 支持通过本地 ManageBac Helper 预览导入 ManageBac DDL 任务。

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
│   ├── vendor/          # Vue 和 Element Plus 本地依赖
│   └── assets/          # 图标等静态资源
├── server.py            # 静态文件服务、API 服务和 SQLite 初始化
├── managebac-sync-helper/ # ManageBac 本地 Helper
├── deploy-first-run.sh  # Linux 首次部署脚本
├── requirements.txt     # 可选 OSS 下载依赖
├── .env.example         # 环境变量示例
├── docs/                # API、用户手册和安全说明
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

确保已安装 Python 3，然后在项目根目录运行：

```bash
python server.py
```

如果需要启用 ManageBac Helper 安装包的 OSS 预签名下载，先安装可选依赖：

```bash
pip install -r requirements.txt
```

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
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=20
```

本机访问通常使用：

```text
http://localhost:8092
```

服务启动时会自动创建 `data/todo-list.db`，并补齐所需 SQLite 表和默认设置。旧数据库可以直接随新版启动，新增表会自动创建；历史 AI token 用量不会回填。

## 首次使用

1. 打开 `http://localhost:8092`。
2. 点击右上角账号入口。
3. 注册新账号。
4. 登录后即可新增、编辑、删除和安排任务。

未登录时页面可以打开，但任务列表和每日安排是只读空数据状态，不能保存修改。

## Linux 部署

建议先在项目根目录创建 `.env`：

```bash
cd /root/To-do-list
cp .env.example .env
nano .env
```

示例内容：

```env
TODO_HOST=127.0.0.1
TODO_PORT=8092
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=20
```

如果已经用 Caddy 或 Nginx 反代，`TODO_HOST` 建议保持 `127.0.0.1`，不要开放 Python 服务到公网。

项目提供首次部署脚本：

```bash
chmod +x deploy-first-run.sh
./deploy-first-run.sh
```

脚本会：

- 检查 `python3`。
- 创建 `data/` 目录。
- 初始化 SQLite 数据库。
- 默认创建并启动 systemd 用户服务 `todo-list.service`。
- 不会创建 `.env`，也不会向 systemd service 写入 `TODO_PORT`、`DEEPSEEK_API_KEY` 等运行环境变量。

只初始化数据库、不创建 systemd 服务：

```bash
./deploy-first-run.sh --no-systemd
```

创建 systemd 服务但不立即启动：

```bash
./deploy-first-run.sh --no-start
```

可选环境变量：

```bash
TODO_ADMIN_NICKNAME=admin \
TODO_ADMIN_NAME=管理员 \
TODO_ADMIN_PASSWORD='change-this-password' \
./deploy-first-run.sh
```

也可以把管理员初始化配置写进 `.env`：

```env
TODO_ADMIN_NICKNAME=admin
TODO_ADMIN_NAME=管理员
TODO_ADMIN_PASSWORD=change-this-password
```

`deploy-first-run.sh` 初始化数据库时会导入 `server.py`，而 `server.py` 会读取 `.env`，所以这些管理员变量可以从 `.env` 生效。再次运行脚本时，如果昵称已存在，会把该账号更新为管理员并重设密码。

如果只设置了 `TODO_ADMIN_NICKNAME` 或只设置了 `TODO_ADMIN_PASSWORD`，脚本会报错退出；两者需要同时设置。部署完成后建议从 `.env` 中移除明文管理员密码，别把钥匙挂门口，风一吹大家都知道。

其他环境变量：

- `TODO_SERVICE_NAME`：systemd 用户服务名，默认 `todo-list.service`。
- `TODO_PORT`：只用于脚本最后输出访问地址提示；实际监听端口由 `.env`、外部环境变量或程序默认值决定。

注意：`TODO_SERVICE_NAME` 是 shell 脚本开头读取的变量，不会通过 `.env` 生效。如需自定义服务名，请在运行脚本时直接传入：

```bash
TODO_SERVICE_NAME=my-todo-list.service ./deploy-first-run.sh
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
ExecStart=/usr/bin/env python3 /root/To-do-list/server.py
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

完整接口说明见 [API.md](./docs/API.md)。

面向普通用户和管理员的功能说明见 [用户功能手册](./docs/USER_GUIDE.md)。

ManageBac 本地 Helper 的唤起和本地 API 说明见 [ManageBac 同步接入说明](./docs/MANAGEBAC_SYNC.md)。

安全边界、部署注意事项和已知剩余风险见 [安全说明](./docs/SECURITY.md)。

需要登录的接口通过请求头传入 token：

```http
Authorization: Bearer <token>
```

## 数据说明

SQLite 数据库默认位置：

```text
data/todo-list.db
```

该目录已被 `.gitignore` 忽略，避免提交本地运行数据。生产环境建议定期备份该文件。

密码使用 PBKDF2-SHA256 加盐哈希存储；会话 token 默认有效期为 7 天。每次访问受保护资源时，服务端会刷新 token 过期时间。

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
