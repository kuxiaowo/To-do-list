# 安全说明

[中文](./SECURITY.md) | [English](../en/SECURITY.md)

本文档记录当前项目的安全边界、部署建议和剩余注意事项。

## 服务暴露

- 默认监听 `127.0.0.1:8092`。生产环境建议继续绑定本机地址，通过 Caddy 或 Nginx 反向代理对外提供 HTTPS。
- 不建议把 Python 内置 HTTP 服务直接暴露到公网。
- `.env` 已在 `.gitignore` 中忽略，不要提交真实 OIDC 客户端密钥、`DEEPSEEK_API_KEY` 或 OSS AccessKey。

## 认证和会话

- 登录采用 Accounts 的 OIDC Authorization Code + PKCE S256；客户端密钥只保存在后端。
- 本站使用随机、不透明、`HttpOnly + SameSite=Lax` Cookie；生产环境同时启用 `Secure`。数据库只保存会话 token 哈希，不把凭证写入 `localStorage`。
- 修改数据的 Cookie 会话请求必须通过 `X-CSRF-Token` 校验。服务端 session 默认有效期为 7 天，访问受保护接口时滑动刷新。
- 本地密码注册、登录和修改密码在硬切换后关闭；旧 PBKDF2 哈希只允许迁入不可登录归档表。
- 回调严格校验 RS256 签名、issuer、audience、nonce、过期时间和 UserInfo 的 `sub`；state 与授权码流程记录只能使用一次。
- Back-Channel Logout 校验签名、事件、受众、时间和 `jti`，并按中央 `sid` 或 `sub` 撤销本站会话。

## 输入和文件

- JSON API 只接受顶层对象，请求体最大 5 MiB。
- 任务标题、科目、备注、日期和布尔字段都由后端校验，不只依赖前端。
- 头像上传限制为 PNG/JPEG/WebP，检查扩展名、声明的 Content-Type 和文件魔数；前端会将头像压缩为最高 256×256 的 WebP，单个头像最大 64 KiB。
- 静态文件服务只允许 `index.html`、`app.js`、`i18n.js`、`style.css`、`vendor/` 和 `assets/`；头像文件名使用白名单校验，拒绝目录穿越。

## 管理员功能

- 管理员接口需要 `role=admin`。
- 删除用户会级联清理该用户任务、安排、习惯、会话、反馈和相关日志。
- 下载统计、AI token 限额和安装包下载限额都只在管理员后台开放。

## ManageBac 后端同步

- ManageBac 账号密码仅用于一次登录，不写入数据库或操作日志；生产环境拒绝通过非 HTTPS 请求提交凭据。
- 后端只持久化 AES-GCM 加密的 Cookie Jar，密钥来自 `MANAGEBAC_COOKIE_ENCRYPTION_KEY`，不得与数据库一起保存。
- Cookie 不返回前端，也不会发送给 `sdgj.managebac.cn` 之外的主机；跨域重定向会被拒绝。
- Cookie 失效后立即删除远端登录态，要求用户重新输入账号密码。
- 每个本站用户和来源 IP 的失败登录次数受短期限制，以降低密码撞库风险。
- 不要在反向代理、APM 或调试中记录 `/api/managebac/session` 的请求体，否则“后端不持久化密码”的边界会被日志绕过。
- Cookie 在有效期内仍等同登录凭证；应用服务器与加密密钥同时失陷时，攻击者仍可能解密 Cookie。

## 仍需人工关注

- `server.py` 基于标准库 HTTP 服务，适合小规模自用或反代后使用；高并发场景建议迁移到成熟 Web 框架和 WSGI/ASGI 服务。
- AI 和 OSS 是外部服务，生产环境需要给对应密钥配置最小权限和额度监控。
- 当前没有自动依赖漏洞扫描流程。升级 Electron、Element Plus、Vue 或 OSS SDK 时建议运行对应生态的审计命令。
