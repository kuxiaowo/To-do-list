# API 接口文档

本文档描述 `server.py` 提供的 HTTP API。所有接口返回 JSON，除特别说明外，请求体也使用 JSON。

## 通用约定

基础地址：

```text
http://localhost:8092
```

请求头：

```http
Content-Type: application/json
Authorization: Bearer <token>
```

未登录访问部分读取接口时会返回只读空数据；写入、更新和删除接口必须登录。

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

- `priority` 可选值：`high`、`medium`、`low`。
- `dueAt` 为空字符串时表示未排期任务。
- `subject` 当前前端要求必填，后端保存为空字符串也兼容。

### ScheduleItem

```json
{
  "id": "schedule-1710000000000-abcd1234",
  "userId": 1,
  "taskId": "task-1710000000000-abcd1234",
  "date": "2026-05-18",
  "slotKey": "2026-05-18-1-18:00",
  "slotLabel": "晚饭后",
  "slotStart": "18:00",
  "slotEnd": "18:40",
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

### Slot

```json
{
  "keyBase": "1-18:00",
  "label": "晚饭后",
  "start": "18:00",
  "end": "18:40"
}
```

说明：

- `keyBase` 是同一天内的时间格子稳定标识。
- 前端生成每日安排时会把日期和 `keyBase` 合成 `slotKey`。
- `start` 和 `end` 使用 `HH:mm`。

## 认证接口

### 注册

```http
POST /api/auth/register
```

请求：

```json
{
  "name": "张三",
  "nickname": "zhangsan",
  "password": "123456"
}
```

响应：

```json
{
  "token": "session-token",
  "user": {
    "id": 1,
    "name": "张三",
    "nickname": "zhangsan",
    "role": "student"
  }
}
```

状态码：

- `200 OK`：注册成功并自动登录。
- `400 Bad Request`：缺少字段、字段过长或密码不足 6 位。
- `409 Conflict`：昵称已存在。

### 登录

```http
POST /api/auth/login
```

请求：

```json
{
  "nickname": "zhangsan",
  "password": "123456"
}
```

响应同注册接口。

状态码：

- `200 OK`：登录成功。
- `401 Unauthorized`：昵称或密码错误。

### 获取当前用户

```http
GET /api/auth/me
```

响应：

```json
{
  "user": {
    "id": 1,
    "name": "张三",
    "nickname": "zhangsan",
    "role": "student"
  }
}
```

状态码：

- `200 OK`：token 有效。
- `401 Unauthorized`：未登录或 token 过期。

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
- `400 Bad Request`：标题缺失或优先级非法。
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
- `400 Bad Request`：标题缺失或优先级非法。
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
  "slotKey": "2026-05-18-1-18:00",
  "slotLabel": "晚饭后",
  "slotStart": "18:00",
  "slotEnd": "18:40",
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
- `400 Bad Request`：任务不存在、时间字段缺失、时长非法或超过当前格子容量。
- `401 Unauthorized`：未登录。

### 更新每日安排

```http
PUT /api/schedule-items/{id}
```

当前实现只更新以下字段：

```json
{
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
- `400 Bad Request`：时长非法或超过格子容量。
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

## 健康检查

```http
GET /api/health
```

响应：

```json
{
  "ok": true,
  "database": "D:\\Python\\programs\\GitHub\\To-do-list\\data\\todo-list.db"
}
```
