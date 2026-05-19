# To-Do List Timeline

一个面向学习任务管理的待办清单 Web 应用。项目使用静态前端、Python 标准库 HTTP 服务和 SQLite 数据库存储，不需要 Node.js 构建流程，也不依赖第三方 Python 包。

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

## 技术栈

- 前端：Vue 3、Element Plus，本地静态文件加载。
- 后端：Python 标准库 `http.server` + `sqlite3`。
- 数据库：SQLite，默认写入 `data/todo-list.db`。
- 部署：可直接运行 `server.py`，也可使用 `deploy-first-run.sh` 创建 systemd 用户服务。

## 项目结构

```text
.
├── index.html           # 前端页面结构
├── style.css            # 页面样式
├── app.js               # Vue 应用逻辑
├── vendor/              # Vue 和 Element Plus 本地依赖
├── server.py            # 静态文件服务、API 服务和 SQLite 初始化
├── deploy-first-run.sh  # Linux 首次部署脚本
├── API.md               # API 接口文档
├── LICENSE              # MIT License
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

默认监听：

```text
http://0.0.0.0:8092
```

可通过环境变量修改监听地址和端口：

```bash
TODO_HOST=127.0.0.1 TODO_PORT=9000 python server.py
```

本机访问通常使用：

```text
http://localhost:8092
```

服务启动时会自动创建 `data/todo-list.db`，并初始化 `users`、`sessions`、`tasks`、`schedule_items`、`schedule_template_versions`、`schedule_day_overrides` 表。

## 首次使用

1. 打开 `http://localhost:8092`。
2. 点击右上角账号入口。
3. 注册新账号。
4. 登录后即可新增、编辑、删除和安排任务。

未登录时页面可以打开，但任务列表和每日安排是只读空数据状态，不能保存修改。

## Linux 部署

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

其他环境变量：

- `TODO_SERVICE_NAME`：systemd 用户服务名，默认 `todo-list.service`。
- `TODO_PORT`：服务监听端口，默认 `8092`。

## API 文档

完整接口说明见 [API.md](./API.md)。

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

前端依赖已放在 `vendor/` 目录：

- `vendor/vue.global.prod.js`
- `vendor/element-plus.full.min.js`
- `vendor/element-plus.css`

因此部署环境不需要访问外部 CDN。以后升级 Vue 或 Element Plus 时，替换 `vendor/` 中对应文件即可。

## 许可证

本项目使用 MIT License，详见 `LICENSE`。
