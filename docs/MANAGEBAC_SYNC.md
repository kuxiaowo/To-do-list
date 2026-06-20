# ManageBac 同步接入说明

## 设计边界

ManageBac 同步由三个部分组成：

```text
managebac-sync://wake 唤起本地 Helper
http://127.0.0.1:27654 本地 API 负责登录、抓取和解析
网页负责预览、确认和导入
```

自定义协议只负责唤醒本地程序，不传 Cookie、账号、密码、网站 token 或任务数据。

## Helper 运行

正式 Helper 位于：

```text
managebac-sync-helper/
```

开发启动：

```powershell
cd managebac-sync-helper
npm.cmd install
npm.cmd run dev
```

生产打包后，Helper 首次启动会注册：

```text
managebac-sync://
```

开发模式不会自动注册协议，避免污染本机协议配置。

## 允许的网站来源

Helper 本地 API 只监听：

```text
127.0.0.1:27654
```

默认允许本地开发网站和正式站点：

```text
http://localhost:8092
http://127.0.0.1:8092
https://nethub.wiki
https://www.nethub.wiki
```

远程网站上线时，需要在 Helper 运行环境中配置：

```powershell
$env:MANAGEBAC_ALLOWED_ORIGINS="https://your-site.example"
```

多个来源用英文逗号分隔。

## 网页流程

用户点击“同步 ManageBac”后：

1. 网页请求 `GET /v1/health`。
2. 如果 Helper 未响应，网页打开 `managebac-sync://wake?nonce=...`。
3. 网页轮询本地 Helper。
4. 网页调用 `POST /v1/session/start` 建立短期本地会话。
5. 网页调用 `GET /v1/session` 检查 ManageBac 登录态。
6. 未登录或登录过期时，网页显示“打开登录窗口”按钮。
7. 用户点击后，网页调用 `POST /v1/login/open`，Helper 弹出或聚焦 ManageBac 登录窗口。
8. 登录后，网页调用 `POST /v1/tasks/preview` 获取解析结果；Helper 只返回 ManageBac 班级/课程名，不负责识别网站科目。
9. 网页根据自己的科目模板预填科目并展示预览列表，用户确认后通过现有 `/api/tasks` 导入。

## 本地 API

### `GET /v1/health`

返回 Helper 状态、版本、端口和协议注册状态。

### `POST /v1/session/start`

请求：

```json
{
  "nonce": "browser-generated-random-value"
}
```

响应：

```json
{
  "ok": true,
  "clientToken": "short-lived-token",
  "expiresInSeconds": 600
}
```

后续受保护接口需要请求头：

```http
X-ManageBac-Client-Token: <clientToken>
```

### `GET /v1/session`

返回 Helper 自己 Electron profile 中的 ManageBac 登录状态。

### `POST /v1/login/open`

打开或聚焦 ManageBac 登录窗口。

### `POST /v1/tasks/preview`

抓取 `Tasks & Deadlines` 页面，解析任务并返回预览列表。

任务项示例：

```json
{
  "source": "managebac",
  "sourceId": "core_task:27421385",
  "sourceUrl": "https://sdgj.managebac.cn/student/classes/11465612/core_tasks/27421385",
  "title": "Final Group Project",
  "subject": "",
  "className": "HS Computer（25级选修） (Grade 10)",
  "rawCourseName": "HS Computer（25级选修） (Grade 10)",
  "dueAt": "2026-06-21T23:55:00",
  "priority": "medium",
  "note": "ManageBac: core_task:27421385"
}
```

### `POST /v1/session/clear`

清除 Helper 自己的 ManageBac 登录态。

## 导入策略

- 默认只预览，不自动写入任务库。
- 用户勾选后才调用现有 `/api/tasks` 创建任务。
- Helper 不识别科目；网站端按科目模板从 `className/rawCourseName` 预填，仍无法识别的任务必须先在预览里补全科目。
- 已存在的任务默认不可勾选；当前依据 `ManageBac: core_task:<id>` 备注或标题、科目、截止时间匹配。
