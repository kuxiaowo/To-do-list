# To-Do List Timeline

一个面向学习任务管理的待办清单 Web 应用。项目使用单文件前端、Python 标准库 HTTP 服务和 SQLite 数据库实现，不需要 Node.js 构建流程，也不依赖第三方 Python 包。

## 功能特性

- 账号注册、登录、退出登录
- 按用户隔离待办任务数据
- 新增、编辑、删除、完成/取消完成 DDL 任务
- 支持任务标题、科目、截止日期时间、优先级和备注
- 未排期任务池，按高/中/低优先级分组
- DDL 时间线视图，按日期横向浏览任务
- 每日安排视图，可将 DDL 拖拽到时间段中生成学习安排
- 时间段容量校验，避免安排时长超过可用时间
- 浅色/深色主题切换
- 首次从旧版浏览器 localStorage 数据迁移到服务器

## 技术栈

- 前端：Vue 3、Element Plus，通过 CDN 在 `index.html` 中直接加载
- 后端：Python 标准库 `http.server` + `sqlite3`
- 数据库：SQLite，默认写入 `data/todo-list.db`
- 部署：可直接运行 `server.py`，也可使用 `deploy-first-run.sh` 创建 systemd 用户服务

## 项目结构

```text
.
├── index.html           # 前端页面、样式和 Vue 应用逻辑
├── server.py            # 静态文件服务、API 服务和 SQLite 初始化
├── deploy-first-run.sh  # Linux 首次部署脚本，可初始化数据库和 systemd 用户服务
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

本机访问通常使用：

```text
http://localhost:8092
```

服务启动时会自动创建 `data/todo-list.db`，并初始化 `users`、`sessions`、`tasks`、`schedule_items` 表。

## 首次使用

1. 打开 `http://localhost:8092`
2. 点击右上角账号入口
3. 注册新账号
4. 登录后即可新增、编辑、删除和安排任务

未登录时页面可以打开，但任务列表和每日安排处于只读/空数据状态，不能保存修改。

## Linux 部署

项目提供首次部署脚本：

```bash
chmod +x deploy-first-run.sh
./deploy-first-run.sh
```

脚本会：

- 检查 `python3`
- 创建 `data/` 目录
- 初始化 SQLite 数据库
- 默认创建并启动 systemd 用户服务 `todo-list.service`

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

- `TODO_SERVICE_NAME`：systemd 用户服务名，默认 `todo-list.service`
- `TODO_PORT`：部署脚本提示用端口，默认 `8092`

注意：当前 `server.py` 中监听端口是常量 `PORT = 8092`。如果要更改实际端口，需要修改 `server.py`。

## API 概览

认证接口：

- `POST /api/auth/register`：注册账号，成功后返回 token
- `POST /api/auth/login`：登录账号，成功后返回 token
- `GET /api/auth/me`：获取当前登录用户
- `POST /api/auth/logout`：退出登录

任务接口：

- `GET /api/tasks`：获取当前用户任务
- `PUT /api/tasks/bulk`：批量替换当前用户任务

每日安排接口：

- `GET /api/schedule-items`：获取当前用户每日安排
- `POST /api/schedule-items`：创建每日安排
- `PUT /api/schedule-items/{id}`：更新安排时长、备注或完成状态
- `DELETE /api/schedule-items/{id}`：删除每日安排

健康检查：

- `GET /api/health`：返回服务状态和数据库路径

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

密码使用 PBKDF2-SHA256 加盐哈希存储，会话 token 默认有效期为 7 天；每次访问受保护资源时会刷新过期时间。

## 开发说明

该项目没有打包步骤，修改后端或前端文件后刷新浏览器即可查看效果。后端修改通常需要重启 `server.py`。

前端依赖通过 CDN 加载：

- `https://unpkg.com/vue@3/dist/vue.global.prod.js`
- `https://unpkg.com/element-plus/dist/index.full.min.js`
- `https://unpkg.com/element-plus/dist/index.css`

如果部署环境无法访问外网 CDN，需要将这些资源改为本地静态文件。

## 许可证

本项目使用 MIT License，详见 `LICENSE`。
