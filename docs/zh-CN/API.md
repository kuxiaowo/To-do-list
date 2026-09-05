# API 接口文档

[中文](./API.md) | [English](../en/API.md)

本文档描述 `server.py` 提供的 HTTP API。所有接口返回 JSON，除特别说明外，请求体也使用 JSON。

## 通用约定

基础地址：

```text
http://localhost:8092
```

请求头：

```http
Content-Type: application/json
Cookie: todo_session=<opaque-token>
X-CSRF-Token: <csrf-token>  # 仅修改数据的请求需要
```

未登录访问部分读取接口时会返回只读空数据；写入、更新和删除接口必须登录。

请求体约束：

- JSON 请求体顶层必须是对象。
- 单个 JSON 请求体最大 5 MiB；头像上传的 base64 内容也包含在这个限制内。
- 未匹配的 `/api/...` 路径会返回 JSON 404，而不是 HTML 错误页。

通用错误响应：

```json
{
  "error": "error message"
}
```

部分业务错误会额外返回 `message`、`usedMinutes`、`capacityMinutes` 等字段，前端会优先展示 `message`。

## 数据模型

### User

```json
{
  "id": 1,
  "name": "张三",
  "nickname": "zhangsan",
  "role": "student"
}
```

### Task

```json
{
  "id": "task-1710000000000-abcd1234",
  "userId": 1,
  "title": "完成物理作业",
  "subject": "物理",
  "dueAt": "2026-05-18T23:59:00",
  "priority": "medium",
  "note": "第 3 章练习",
  "completed": false,
  "createdAt": "2026-05-18T13:00:00Z",
  "updatedAt": "2026-05-18T13:00:00Z"
}
```

说明：

- `id` 最长 128 个字符；创建任务时不传则由后端生成。
- `title` 必填，最长 120 个字符。
- `subject` 必填，最长 40 个字符；值可以来自科目模板，也可以是用户自定义文本。
- `priority` 可选值：`high`、`medium`、`low`。
- `dueAt` 为空字符串时表示未排期任务；非空时必须使用 `YYYY-MM-DDTHH:mm:ss`。
- `note` 最长 4000 个字符。
- `completed` 必须是 JSON 布尔值。

### ScheduleItem

```json
{
  "id": "schedule-1710000000000-abcd1234",
  "userId": 1,
  "taskId": "task-1710000000000-abcd1234",
  "date": "2026-05-18",
  "slotKey": "2026-05-18-dynamic",
  "slotLabel": "每日安排",
  "slotStart": "00:00",
  "slotEnd": "23:59",
  "startTime": "18:05",
  "endTime": "18:35",
  "durationMinutes": 30,
  "note": "复习错题",
  "completed": false,
  "createdAt": "2026-05-18T13:00:00Z",
  "updatedAt": "2026-05-18T13:00:00Z",
  "task": {
    "id": "task-1710000000000-abcd1234",
    "title": "完成物理作业",
    "subject": "物理",
    "dueAt": "2026-05-18T23:59:00",
    "priority": "medium"
  }
}
```

### Slot（旧版兼容）

```json
{
  "keyBase": "1-18:00",
  "label": "晚饭后",
  "start": "18:00",
  "end": "18:40"
}
```

说明：

- 新版每日安排不再依赖时间格子；`slotKey`、`slotLabel`、`slotStart`、`slotEnd` 仅作为旧数据兼容字段返回。
- `keyBase` 是同一天内的时间格子稳定标识。
- `start` 和 `end` 使用 `HH:mm`。

## 认证接口

### 发起中央登录

```http
GET /auth/login
```

创建一次性 OIDC state、nonce 和 PKCE verifier，把流程哈希保存在 SQLite，并重定向到 Accounts。浏览器同时收到短期 `HttpOnly` 流程 Cookie。

### OIDC 回调

```http
GET /auth/callback?code=<code>&state=<state>
```

后端兑换授权码并校验 ID Token 和 UserInfo。若 `auth_sub` 尚无本站成员，则复制中央用户名和显示名称创建默认 `student`；以后资料独立，不持续同步。成功后设置本站会话 Cookie 并重定向到 `/`。

旧接口 `POST /api/auth/register`、`POST /api/auth/login` 和 `PUT /api/auth/password` 在生产默认返回 `410 Gone`。

### 获取当前用户

```http
GET /api/auth/me
```

响应：

```json
{
  "csrfToken": "request-csrf-token",
  "user": {
    "id": 1,
    "name": "张三",
    "nickname": "zhangsan",
    "role": "student"
  }
}
```

状态码：

- `200 OK`：Cookie 会话有效。
- `401 Unauthorized`：未登录或会话过期。

### 退出登录

```http
POST /api/auth/logout
```

响应：

```json
{
  "ok": true
}
```

只删除 TodoList 本地会话，不退出 Accounts 或其他网站。

### Back-Channel Logout

```http
POST /auth/backchannel-logout
Content-Type: application/x-www-form-urlencoded

logout_token=<signed-jwt>
```

供 Accounts 调用。签名和声明通过后，按中央 `sid` 或 `sub` 删除本站会话；重复 `jti` 不会重复产生副作用。

## ManageBac 后端同步

以下接口都需要本站 Cookie 会话，修改请求还需要 CSRF token，响应均禁止缓存。ManageBac 账号密码只允许通过 HTTPS 提交；本机 `localhost` 开发除外。

### 查询登录状态

```http
GET /api/managebac/session
```

返回是否保存了可解密的 Cookie、连接时间和上次验证时间。此接口不访问 ManageBac，不保证 Cookie 尚未过期。

### 登录并获取预览

```http
POST /api/managebac/session
Content-Type: application/json

{
  "account": "student@example.com",
  "password": "ManageBac password"
}
```

后端完成一次 ManageBac 登录，只持久化 AES-GCM 加密的 Cookie Jar，并立即返回解析后的 `tasks` 和 `meta`。账号和密码不会写入数据库或操作日志。

可能状态：

- `200 OK`：登录成功并返回任务预览。
- `401 Unauthorized`：ManageBac 拒绝账号密码。
- `426 Upgrade Required`：生产请求未使用 HTTPS。
- `429 Too Many Requests`：短时间内登录失败次数过多。
- `502 Bad Gateway`：ManageBac 不可用或页面协议无法识别。
- `503 Service Unavailable`：Cookie 加密密钥缺失或无效。

### 使用 Cookie 获取预览

```http
POST /api/managebac/tasks/preview
```

成功时返回 `tasks` 和 `meta`，并保存 ManageBac 响应产生的 Cookie 轮换。Cookie 失效时返回：

```json
{
  "error": "managebac_reauth_required",
  "message": "ManageBac 登录已失效，需要重新登录。",
  "requiresLogin": true
}
```

### 清除登录状态

```http
DELETE /api/managebac/session
```

删除当前本站用户保存的 ManageBac Cookie。

## 旧版 ManageBac Helper 安装包下载

### 获取安装包下载

```http
GET /api/managebac-helper/installer
Cookie: todo_session=<opaque-token>
```

行为：

- 必须登录。
- 配置 OSS 时，返回一次短期预签名下载 URL。
- 未配置 OSS 时，返回本地安装包文件流。
- 每次成功生成 OSS URL 或发送本地安装包都会计入下载统计。

OSS 响应：

```json
{
  "ok": true,
  "source": "oss",
  "url": "https://...",
  "expiresSeconds": 600,
  "limit": {
    "windowHours": 24,
    "linkLimit": 5,
    "source": "global",
    "hasOverride": false
  },
  "usage": {
    "linkCount": 1
  }
}
```

状态码：

- `200 OK`：返回 OSS URL 或本地文件流。
- `401 Unauthorized`：未登录。
- `429 Too Many Requests`：下载链接生成次数达到当前用户限制。

### 管理员查看下载统计

```http
GET /api/admin/installer-downloads/summary?view=7d&page=1&pageSize=10
```

`view` 可选：`6h`、`1d`、`7d`、`30d`。

### 管理员更新全局下载限制

```http
PUT /api/admin/installer-downloads/global-limit
```

请求：

```json
{
  "windowHours": 24,
  "linkLimit": 5
}
```

### 管理员更新单用户下载限制

```http
PUT /api/admin/users/{userId}/installer-download-limit
```

请求：

```json
{
  "windowHours": 24,
  "linkLimit": 10
}
```

### 管理员清除单用户下载限制

```http
DELETE /api/admin/users/{userId}/installer-download-limit
```

### 管理员清除全部单用户下载限制

```http
POST /api/admin/installer-downloads/clear-user-limits
```

## 任务接口

### 获取任务列表

```http
GET /api/tasks
```

未登录响应：

```json
{
  "tasks": [],
  "readOnly": true
}
```

已登录响应：

```json
{
  "tasks": [],
  "readOnly": false,
  "user": {
    "id": 1,
    "name": "张三",
    "nickname": "zhangsan",
    "role": "student"
  }
}
```

### 创建任务

```http
POST /api/tasks
```

请求：

```json
{
  "id": "task-1710000000000-abcd1234",
  "title": "完成物理作业",
  "subject": "物理",
  "dueAt": "2026-05-18T23:59:00",
  "priority": "medium",
  "note": "第 3 章练习",
  "completed": false,
  "createdAt": "2026-05-18T13:00:00Z"
}
```

响应：

```json
{
  "ok": true,
  "task": {}
}
```

状态码：

- `201 Created`：创建成功。
- `400 Bad Request`：标题或科目缺失、字段超长、`dueAt` 格式非法、`priority` / `pool` 非法，或 `completed` 不是布尔值。
- `401 Unauthorized`：未登录。
- `409 Conflict`：任务 id 已存在。

### 更新任务

```http
PUT /api/tasks/{id}
```

请求体同创建任务。路径中的 `{id}` 是要更新的任务 id。

响应：

```json
{
  "ok": true,
  "task": {}
}
```

状态码：

- `200 OK`：更新成功。
- `400 Bad Request`：标题或科目缺失、字段超长、`dueAt` 格式非法、`priority` / `pool` 非法，或 `completed` 不是布尔值。
- `401 Unauthorized`：未登录。
- `404 Not Found`：任务不存在或不属于当前用户。

### 删除任务

```http
DELETE /api/tasks/{id}
```

响应：

```json
{
  "ok": true
}
```

说明：删除单个任务时会同步删除该任务对应的每日安排。

## 每日安排接口

### 获取每日安排

```http
GET /api/schedule-items
```

响应：

```json
{
  "items": [],
  "readOnly": false
}
```

未登录时返回：

```json
{
  "items": [],
  "readOnly": true
}
```

### 创建每日安排

```http
POST /api/schedule-items
```

请求：

```json
{
  "taskId": "task-1710000000000-abcd1234",
  "date": "2026-05-18",
  "startTime": "18:05",
  "durationMinutes": 30,
  "note": "复习错题",
  "completed": false
}
```

响应：

```json
{
  "ok": true,
  "id": "schedule-1710000000000-abcd1234"
}
```

状态码：

- `201 Created`：创建成功。
- `400 Bad Request`：任务不存在、日期或开始时间缺失、时长非法，或安排跨越到次日。
- `401 Unauthorized`：未登录。

每日安排不再依赖时间段模板。结束时间由 `startTime + durationMinutes` 自动计算；同一日期的安排允许时间重叠。查询安排时，每个实例会返回：

```json
{
  "startTime": "18:05",
  "endTime": "18:35",
  "hasConflict": true,
  "conflictIds": ["schedule-overlapping-id"]
}
```

相邻但不重叠的区间不会标记冲突；已完成的安排不再参与冲突计算。

### 更新每日安排

```http
PUT /api/schedule-items/{id}
```

当前实现只更新以下字段：

```json
{
  "startTime": "18:10",
  "durationMinutes": 20,
  "note": "改做选择题",
  "completed": true
}
```

响应：

```json
{
  "ok": true,
  "id": "schedule-1710000000000-abcd1234"
}
```

状态码：

- `200 OK`：更新成功。
- `400 Bad Request`：开始时间或时长非法，或安排跨越到次日。
- `401 Unauthorized`：未登录。
- `404 Not Found`：安排不存在或不属于当前用户。

### 删除每日安排

```http
DELETE /api/schedule-items/{id}
```

响应：

```json
{
  "ok": true
}
```

说明：删除普通每日安排不会删除原任务。删除习惯实例时，只会永久跳过该习惯的对应日期，不影响习惯定义及其他日期的实例；后续同步不会重新生成该日期。

## 时间格子配置接口

### 获取时间格子配置

```http
GET /api/schedule-config
```

响应：

```json
{
  "defaultWeekSlots": {
    "0": [],
    "1": []
  },
  "templateVersions": [
    {
      "id": 1,
      "effectiveFrom": "2026-05-18",
      "slots": {
        "0": [],
        "1": []
      },
      "createdAt": "2026-05-18T13:00:00Z",
      "updatedAt": "2026-05-18T13:00:00Z"
    }
  ],
  "dayOverrides": {
    "2026-05-18": []
  },
  "readOnly": false
}
```

说明：

- `defaultWeekSlots` 是系统默认一周模板。
- `templateVersions` 是用户保存过的一周模板版本，按 `effectiveFrom` 生效。
- `dayOverrides` 是单日自定义时间格子，优先级高于一周模板。

### 保存一周模板

```http
PUT /api/schedule-template
```

请求：

```json
{
  "effectiveFrom": "2026-05-18",
  "slots": {
    "0": [
      {
        "keyBase": "0-09:00",
        "label": "上午",
        "start": "09:00",
        "end": "10:00"
      }
    ],
    "1": [],
    "2": [],
    "3": [],
    "4": [],
    "5": [],
    "6": []
  }
}
```

响应：

```json
{
  "ok": true
}
```

说明：模板从 `effectiveFrom` 起对未来未单独自定义的日期生效。如果修改会破坏已有安排所在时间段，接口返回 `409 Conflict`。

### 保存单日时间格子

```http
PUT /api/schedule-day-slots/{date}
```

请求：

```json
{
  "slots": [
    {
      "keyBase": "0-13:00",
      "label": "午休",
      "start": "13:00",
      "end": "13:45"
    }
  ]
}
```

响应：

```json
{
  "ok": true
}
```

说明：只影响路径中的 `{date}`，例如 `2026-05-18`。

### 重置单日时间格子

```http
DELETE /api/schedule-day-slots/{date}
```

响应：

```json
{
  "ok": true
}
```

说明：删除该日期的单日覆盖，使它重新使用一周模板。

### 重置全部时间格子配置

```http
DELETE /api/schedule-config
```

响应：

```json
{
  "ok": true
}
```

说明：删除当前用户的一周模板版本和全部单日覆盖，恢复系统默认模板。如果恢复默认模板会破坏已有安排所在时间段，接口返回 `409 Conflict`。

## 习惯接口

### 获取习惯列表

```http
GET /api/habits
```

未登录响应：

```json
{
  "habits": [],
  "readOnly": true
}
```

已登录响应：

```json
{
  "habits": [],
  "readOnly": false
}
```

### 创建习惯

```http
POST /api/habits
```

请求：

```json
{
  "id": "habit-1710000000000-abcd1234",
  "title": "背单词",
  "subject": "English B",
  "weekdays": ["1", "3", "5"],
  "startTime": "18:00",
  "durationMinutes": 15,
  "startDate": "2026-05-18",
  "endDate": "",
  "priority": "medium",
  "note": "复习错题本",
  "active": true
}
```

响应：

```json
{
  "ok": true,
  "habit": {}
}
```

状态码：

- `201 Created`：创建成功，并同步生成符合日期范围的每日安排。
- `400 Bad Request`：字段缺失、星期非法、开始时间或时长非法，或习惯会跨越午夜。
- `401 Unauthorized`：未登录。

习惯不再依赖一周时间格模板。结束时间由 `startTime + durationMinutes` 自动计算；即使与其他安排重叠也会正常创建，并在每日安排查询结果中通过 `hasConflict` 与 `conflictIds` 标记。

### 更新习惯

```http
PUT /api/habits/{id}
```

请求体同创建习惯。更新会重建今天及未来未完成的习惯安排；历史记录保留。

### 删除习惯

```http
DELETE /api/habits/{id}
```

响应：

```json
{
  "ok": true
}
```

说明：删除习惯会归档该习惯，并删除跨全部日期的所有未完成实例；已完成实例会作为历史记录保留。

## 用户反馈接口

### 获取我的反馈

```http
GET /api/feedback
```

响应：

```json
{
  "feedback": [],
  "feedbackLimitPerUser": 10
}
```

状态码：

- `200 OK`：获取成功。
- `401 Unauthorized`：未登录。

### 提交反馈

```http
POST /api/feedback
```

请求：

```json
{
  "content": "希望增加导出功能"
}
```

响应：

```json
{
  "ok": true,
  "feedback": {}
}
```

状态码：

- `201 Created`：提交成功。
- `400 Bad Request`：内容为空或超过 1000 个字符。
- `401 Unauthorized`：未登录。
- `409 Conflict`：未回复反馈数量达到管理员设置的上限。

### 删除我的反馈

```http
DELETE /api/feedback/{id}
```

响应：

```json
{
  "ok": true,
  "id": 1
}
```

说明：只能删除当前登录用户自己的反馈。

## AI 助手接口

AI 助手只生成待审批指令，不会在 `/api/ai/...` 接口中直接写入任务。客户端审批执行时仍调用普通任务接口，因此任务接口的后端校验是最终兜底。

AI 上下文只包含当前用户未完成的 `pool=todo` 任务，最多返回给模型 200 条；如果实际数量超过 200，响应上下文中的 `taskSelection.truncated` 会提示模型追问用户缩小范围。

### 非流式聊天

```http
POST /api/ai/chat
Cookie: todo_session=<opaque-token>
X-CSRF-Token: <csrf-token>
Content-Type: application/json
```

请求：

```json
{
  "message": "帮我创建一个数学任务，低优先级，先放到待安排",
  "history": [
    { "role": "user", "content": "上一轮用户消息" },
    { "role": "assistant", "content": "上一轮助手回复" }
  ],
  "locale": "zh-CN",
  "clientNow": "2026-06-20T12:00:00.000Z",
  "timezone": "Asia/Shanghai"
}
```

`locale` 可选值为 `zh-CN` 或 `en`；传入 `en` 时，AI 助手的用户可见回复使用英语。未传时默认使用中文。

响应：

```json
{
  "ok": true,
  "reply": "给用户看的回复",
  "actions": [
    {
      "id": "ai-action-1",
      "type": "create_task",
      "summary": "创建任务：完成练习 / Mathematics / 待安排 / 低",
      "task": {
        "title": "完成练习",
        "subject": "Mathematics",
        "dueAt": "",
        "priority": "low",
        "note": ""
      }
    }
  ],
  "rejectedActions": []
}
```

状态码：

- `200 OK`：AI 返回已处理；`actions` 仍需客户端审批后再执行。
- `400 Bad Request`：请求体非法、`message` 缺失或超过 2000 字符。
- `401 Unauthorized`：未登录。
- `429 Too Many Requests`：达到当前用户 AI token 限制。
- `502 Bad Gateway`：DeepSeek 请求失败。
- `503 Service Unavailable`：未配置 `DEEPSEEK_API_KEY`。

### 流式聊天

```http
POST /api/ai/chat-stream
Cookie: todo_session=<opaque-token>
X-CSRF-Token: <csrf-token>
Content-Type: application/json
```

请求体同 `/api/ai/chat`。响应使用 Server-Sent Events：

```text
event: delta
data: {"text":"我先整理一下..."}

event: done
data: {"reply":"完整回复","actions":[],"rejectedActions":[]}
```

错误会以 SSE `error` 事件返回：

```text
event: error
data: {"error":"DeepSeek request failed","message":"..."}
```

### AI 动作格式

服务端只接受两类动作：

- `create_task`：只能包含 `title`、`subject`、`dueAt`、`priority`、`note`，且最终创建为 `pool=todo`。
- `update_task`：只能修改上下文中已有任务的 `title`、`subject`、`dueAt`、`priority`、`note`。

服务端会拒绝删除任务、标记完成、修改每日安排、修改习惯、写入未知字段、使用上下文外任务 id、超长字段或非法日期。被拒绝的动作会出现在 `rejectedActions` 中；后端会尝试用修复提示让模型重新生成安全动作。

## 管理员 AI Token 统计与限制

以下接口都要求管理员登录。

### 获取 AI 用量统计

```http
GET /api/admin/ai-usage/summary?view=7d&page=1&pageSize=10
Cookie: todo_session=<opaque-token>
```

`view` 可选：`6h`、`1d`、`7d`、`30d`。响应包含全局限制、趋势数据、当前页用户的有效限制和滚动窗口用量。

### 更新全局限制

```http
PUT /api/admin/ai-usage/global-limit
Cookie: todo_session=<opaque-token>
X-CSRF-Token: <csrf-token>
Content-Type: application/json
```

请求：

```json
{
  "windowHours": 24,
  "inputTokenLimit": 200000,
  "outputTokenLimit": 50000
}
```

### 更新或清除用户限制

```http
PUT /api/admin/users/{userId}/ai-token-limit
DELETE /api/admin/users/{userId}/ai-token-limit
```

`PUT` 请求体同全局限制；`DELETE` 会让该用户重新使用全局限制。

### 清除全部用户覆盖

```http
POST /api/admin/ai-usage/clear-user-limits
```

响应：

```json
{
  "ok": true,
  "deleted": 3
}
```

## 健康检查

```http
GET /api/health
```

响应：

```json
{
  "ok": true
}
```

## Subject Template API

Subject templates are per-user presets for the task `subject` field. Tasks still store `subject` as plain text and do not require the value to come from the template.

### Get subject template

```http
GET /api/subject-template
```

Response:
```json
{
  "subjects": [
    { "name": "Chinese", "preset": true, "enabled": true },
    { "name": "Mathematics", "preset": true, "enabled": true },
    { "name": "Computer Science", "preset": true, "enabled": true },
    { "name": "History", "preset": false, "enabled": true }
  ],
  "defaultSubjects": ["Chinese", "Mathematics", "English B", "IELTS", "Physics", "Economics", "Chemistry", "Psychology", "Biology", "Computer Science"],
  "readOnly": false
}
```

Status:
- `200 OK`: success.
- `401 Unauthorized`: login required.

### Update subject template

```http
PUT /api/subject-template
```

Request:
```json
{
  "subjects": [
    { "name": "Chinese", "preset": true, "enabled": false },
    { "name": "History", "preset": false, "enabled": true }
  ]
}
```

Notes:
- Preset subjects are always kept by the server; clients can only enable or disable them.
- Custom subjects can be added or removed by including or omitting them from `subjects`.
- Subject names are trimmed, case-insensitively deduplicated, and limited to 40 characters.

Status:
- `200 OK`: saved.
- `400 Bad Request`: invalid payload.
- `401 Unauthorized`: login required.
