# ManageBac 后端同步说明

[中文](./MANAGEBAC_SYNC.md) | [English](../en/MANAGEBAC_SYNC.md)

## 设计边界

ManageBac 同步由本站后端完成：

```text
用户输入 ManageBac 账号密码
  -> 后端完成一次登录并立即丢弃账号密码
  -> AES-GCM 加密 Cookie Jar 后按本站用户保存
  -> 后续使用 Cookie 抓取并解析任务页
  -> Cookie 失效时删除旧登录态并要求重新输入账号密码
```

后端不保存 ManageBac 账号或密码。Cookie 是有效登录凭证，虽然经过加密，仍应按密码级别保护。前端只接收连接状态和解析后的任务，不接收 Cookie。

## 必需配置

安装依赖：

```bash
python -m pip install -r requirements.txt
```

生成一枚 32 字节 URL-safe Base64 密钥：

```bash
python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

将结果放入部署环境：

```dotenv
MANAGEBAC_COOKIE_ENCRYPTION_KEY=生成的密钥
```

密钥必须独立备份并保持稳定。丢失或更换密钥后，已有 Cookie 无法解密，用户需要重新登录。不要把真实密钥提交到仓库。

生产环境必须通过 HTTPS 暴露站点。反向代理连接本机 Python 服务时，需要传递：

```text
X-Forwarded-Proto: https
```

本机 `localhost` 开发仍可使用 HTTP。

## 用户流程

1. 用户打开“同步 ManageBac”，网页调用 `GET /api/managebac/session`。
2. 没有 Cookie 时显示 ManageBac 账号密码表单。
3. 网页调用 `POST /api/managebac/session`；后端获取登录页 CSRF Token、提交登录并验证任务页。
4. 登录成功后，后端只保存加密 Cookie，同时返回任务预览。
5. 后续调用 `POST /api/managebac/tasks/preview` 使用 Cookie 抓取任务，并保存服务端返回的 Cookie 轮换。
6. 如果任务请求回到登录页，后端删除失效 Cookie 并返回 `managebac_reauth_required`，网页重新显示登录表单。
7. 用户可调用 `DELETE /api/managebac/session` 主动删除远端保存的 Cookie。

## 限制

- 当前固定连接 `https://sdgj.managebac.cn`。
- 当前支持 ManageBac 账号密码表单登录；验证码、MFA、Google/Microsoft SSO 不保证可用。
- 后端不保存密码，因此 Cookie 过期后不能无人值守地自动重新登录。
- 每个本站用户和来源 IP 在 15 分钟内最多产生 5 次失败登录，超过后暂时拒绝继续尝试。
- Cookie 只发送给固定 ManageBac 主机，跨域重定向会被拒绝。

## 导入策略

- 登录和抓取只返回预览，不直接创建本站任务。
- 用户确认后才调用现有任务接口导入。
- 网页从 `className/rawCourseName` 推断科目，无法识别时需要用户补全。
- 导入时保留 `ManageBac: core_task:<id>` 备注，用于识别重复任务。
