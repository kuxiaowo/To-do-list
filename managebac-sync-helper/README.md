# ManageBac 同步 Helper

这是给待办清单网站使用的本地 Windows Helper。它负责在本机打开 ManageBac 登录窗口、保存 Helper 自己的登录 cookie，并向网站返回已经解析好的任务预览数据。

网站通过下面的自定义协议唤起这个应用：

```text
managebac-sync://wake
```

启动后，Helper 只监听本机地址：

```text
http://127.0.0.1:27654
```

自定义协议只负责唤起应用，不传递 cookie、账号密码、网站 token 或任务数据。实际状态检查、登录窗口打开和任务抓取都通过 `127.0.0.1` 本地 HTTP API 完成。

## 开发运行

```powershell
npm.cmd install
npm.cmd run dev
```

开发模式会启动本地 API，但不会注册 `managebac-sync://` 自定义协议。自定义协议注册只在打包后的生产版本中执行。开发测试时可以先手动运行 Helper，再从网站按钮调用本地 API。

## 本地 API

- `GET /v1/health`
- `POST /v1/session/start`
- `GET /v1/session`
- `POST /v1/login/open`
- `POST /v1/tasks/preview`
- `POST /v1/session/clear`

如需允许额外的网站来源访问本地 API，可以设置：

```powershell
$env:MANAGEBAC_ALLOWED_ORIGINS="https://example.com,http://localhost:8092"
```

默认允许本地开发来源 `localhost:8092` 和 `127.0.0.1:8092`。

## 安全边界

- 只读取这个 Electron 应用自己 profile 里的 cookie。
- 不读取 Chrome 浏览器 cookie。
- 不把原始 cookie 值写入项目文件。
- API 只绑定到 `127.0.0.1`。
- 会话、登录和预览接口需要短期本地 client token。
