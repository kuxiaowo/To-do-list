# 安全说明

本文档记录当前项目的安全边界、部署建议和剩余注意事项。

## 服务暴露

- 默认监听 `127.0.0.1:8092`。生产环境建议继续绑定本机地址，通过 Caddy 或 Nginx 反向代理对外提供 HTTPS。
- 不建议把 Python 内置 HTTP 服务直接暴露到公网。
- `.env` 已在 `.gitignore` 中忽略，不要提交真实 `DEEPSEEK_API_KEY`、OSS AccessKey 或管理员初始化密码。

## 认证和会话

- 登录态使用 `Authorization: Bearer <token>` 请求头。
- 服务端 session 默认有效期为 7 天；访问受保护接口时会滑动刷新过期时间。
- 密码使用 PBKDF2-SHA256 加盐哈希存储。
- 前端当前把 token 存在 `localStorage`。这便于静态前端使用，但如果页面出现 XSS，token 会一起暴露；因此禁止引入不可信脚本，升级 `web/vendor/` 依赖时要确认来源。

## 输入和文件

- JSON API 只接受顶层对象，请求体最大 5 MiB。
- 任务标题、科目、备注、日期和布尔字段都由后端校验，不只依赖前端。
- 头像上传限制为 PNG/JPEG/WebP，检查扩展名、声明的 Content-Type 和文件魔数，单个头像最大 2 MiB。
- 静态文件服务只允许 `index.html`、`app.js`、`style.css`、`vendor/` 和 `assets/`；头像文件名使用白名单校验，拒绝目录穿越。

## 管理员功能

- 管理员接口需要 `role=admin`。
- 删除用户会级联清理该用户任务、安排、习惯、会话、反馈和相关日志。
- 下载统计、AI token 限额和安装包下载限额都只在管理员后台开放。

## ManageBac Helper

- Helper 只监听 `127.0.0.1:27654`。
- Helper 默认只允许 `http://localhost:8092`、`http://127.0.0.1:8092`、`https://nethub.wiki` 和 `https://www.nethub.wiki` 访问本地 API。
- Helper 只读取自己 Electron profile 中的 ManageBac cookie，不读取 Chrome/Edge cookie，也不把 cookie 返回给网站。
- 受保护的 Helper 接口需要短期 `X-ManageBac-Client-Token`。

## 仍需人工关注

- `server.py` 基于标准库 HTTP 服务，适合小规模自用或反代后使用；高并发场景建议迁移到成熟 Web 框架和 WSGI/ASGI 服务。
- AI 和 OSS 是外部服务，生产环境需要给对应密钥配置最小权限和额度监控。
- 当前没有自动依赖漏洞扫描流程。升级 Electron、Element Plus、Vue 或 OSS SDK 时建议运行对应生态的审计命令。
