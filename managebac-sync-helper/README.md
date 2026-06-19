# nethub.wiki ManageBac 同步辅助程序

这是给 nethub.wiki 使用的本地 Windows 同步辅助程序。它负责在本机打开 ManageBac 登录窗口、保存 Helper 自己的登录 cookie，并向网站返回已经解析好的任务预览数据。

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

本目录包含项目级 `.npmrc`，默认使用 npmmirror 加速 npm 包、Electron 和 electron-builder 辅助二进制下载。

```powershell
npm.cmd install
npm.cmd run dev
```

开发模式会启动本地 API，但不会注册 `managebac-sync://` 自定义协议。自定义协议注册只在打包后的生产版本中执行。开发测试时可以先手动运行 Helper，再从网站按钮调用本地 API。

启动后会显示系统托盘图标。右键托盘图标可以查看当前状态、打开登录窗口、查看应用说明与安全性，或退出 Helper。

## 打包

```powershell
npm.cmd run dist
```

安装包会生成到：

```text
dist/
```

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

- 这是 `nethub.wiki` 的 ManageBac 本地同步辅助程序。
- 只读取这个 Electron 应用自己 profile 里的 cookie。
- 不读取 Chrome 浏览器 cookie。
- 不读取、不保存 ManageBac 账号密码。
- 不把 cookie 发送给网站；网站只接收解析后的任务预览数据。
- 不把原始 cookie 值写入项目文件。
- API 只绑定到 `127.0.0.1`。
- 会话、登录和预览接口需要短期本地 client token。
