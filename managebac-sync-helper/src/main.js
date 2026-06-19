const { app, BrowserWindow, dialog, session, shell, Tray, Menu, nativeImage } = require("electron");
const http = require("node:http");
const crypto = require("node:crypto");
const path = require("node:path");
const { URL } = require("node:url");

const { parseManageBacTasks } = require("./managebacParser");

const PROTOCOL = "managebac-sync";
const HOST = "127.0.0.1";
const PORT = 27654;
const TARGET_ORIGIN = "https://sdgj.managebac.cn";
const TASKS_URL = `${TARGET_ORIGIN}/student/tasks_and_deadlines`;
const PARTITION = "persist:managebac-sync-helper";
const TOKEN_TTL_MS = 10 * 60 * 1000;
const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36";
const APP_DISPLAY_NAME = "nethub.wiki ManageBac 同步辅助程序";

const clientSessions = new Map();
let server;
let loginWindow;
let tray;
let trayStatusTimer;
let manageBacStatusText = "ManageBac：正在检查";
let isQuitting = false;
let protocolRegistered = false;
let protocolRegistration = {
  status: "checking",
  repaired: false,
  error: ""
};

app.setAppUserModelId("cn.managebac.sync.helper");

function configuredOrigins() {
  const configured = String(process.env.MANAGEBAC_ALLOWED_ORIGINS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return new Set([
    "http://localhost:8092",
    "http://127.0.0.1:8092",
    ...configured
  ]);
}

function isAllowedOrigin(origin) {
  if (!origin) return true;
  if (origin === "null") return false;
  return configuredOrigins().has(origin);
}

function getManageBacSession() {
  return session.fromPartition(PARTITION);
}

async function getCookies() {
  return getManageBacSession().cookies.get({ url: TARGET_ORIGIN });
}

async function getCookieStatus() {
  const cookies = await getCookies();
  return {
    loggedIn: cookies.some((cookie) => cookie.name === "_managebac_session"),
    cookieCount: cookies.length,
    hasManageBacSession: cookies.some((cookie) => cookie.name === "_managebac_session")
  };
}

function buildCookieHeader(cookies) {
  return cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join("; ");
}

function extractTitle(html) {
  const match = String(html || "").match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  return match ? match[1].replace(/\s+/g, " ").trim() : "";
}

function isLoginPage(html) {
  return /<title[^>]*>\s*ManageBac\s*\|\s*Login\s*<\/title>/i.test(html) ||
    /id=["']session_login["']/.test(html) ||
    /id=["']session_password["']/.test(html);
}

function isTasksPage(html) {
  return /controller-student-tasks_and_deadlines/.test(html) ||
    /<title[^>]*>\s*ManageBac\s*\|\s*Tasks\s*&amp;\s*Deadlines\s*<\/title>/i.test(html);
}

function getErrorMessage(error) {
  return error && error.message ? error.message : String(error || "");
}

function registerProtocol() {
  if (!app.isPackaged) {
    protocolRegistration = {
      status: "development",
      repaired: false,
      error: ""
    };
    return false;
  }

  let wasDefault = false;
  try {
    wasDefault = app.isDefaultProtocolClient(PROTOCOL);
  } catch (_error) {
    wasDefault = false;
  }

  let setResult = false;
  let error = "";
  try {
    setResult = app.setAsDefaultProtocolClient(PROTOCOL);
  } catch (registrationError) {
    error = getErrorMessage(registrationError);
  }

  let isDefault = false;
  try {
    isDefault = app.isDefaultProtocolClient(PROTOCOL);
  } catch (statusError) {
    if (!error) error = getErrorMessage(statusError);
  }

  const registered = Boolean(isDefault || setResult);
  protocolRegistration = {
    status: registered ? (wasDefault ? "registered" : "updated") : "failed",
    repaired: registered && !wasDefault,
    error
  };
  return registered;
}

function findProtocolUrl(argv) {
  return argv.find((arg) => String(arg || "").startsWith(`${PROTOCOL}://`)) || "";
}

function handleProtocolUrl(rawUrl) {
  if (!rawUrl) return;
  try {
    const parsed = new URL(rawUrl);
    if (parsed.hostname === "login") {
      createLoginWindow();
    }
  } catch (_error) {
    // Ignore malformed protocol input. The protocol is only a wake signal.
  }
}

function getAssetPath(fileName) {
  const assetDir = app.isPackaged
    ? path.join(process.resourcesPath, "assets")
    : path.join(__dirname, "..", "assets");
  return path.join(assetDir, fileName);
}

function protocolStatusText() {
  if (!app.isPackaged) return "协议：开发模式未注册";
  if (protocolRegistered) {
    return protocolRegistration.repaired
      ? "协议：managebac-sync:// 已覆盖注册"
      : "协议：managebac-sync:// 已注册";
  }
  return protocolRegistration.error ? "协议：注册失败" : "协议：未注册";
}

function setTrayMenu() {
  if (!tray) return;
  tray.setToolTip([
    APP_DISPLAY_NAME,
    manageBacStatusText,
    `本地接口：http://${HOST}:${PORT}`
  ].join("\n"));
  tray.setContextMenu(Menu.buildFromTemplate([
    {
      label: APP_DISPLAY_NAME,
      enabled: false
    },
    {
      label: "状态：Helper 已运行",
      enabled: false
    },
    {
      label: manageBacStatusText,
      enabled: false
    },
    {
      label: `本地接口：${HOST}:${PORT}`,
      enabled: false
    },
    {
      label: protocolStatusText(),
      enabled: false
    },
    { type: "separator" },
    {
      label: "刷新状态",
      click: () => refreshTrayStatus()
    },
    {
      label: "打开登录窗口",
      click: () => createLoginWindow()
    },
    {
      label: "应用说明与安全性",
      click: () => showSecurityInfo()
    },
    { type: "separator" },
    {
      label: "退出",
      click: () => quitApp()
    }
  ]));
}

async function refreshTrayStatus() {
  try {
    const status = await getCookieStatus();
    manageBacStatusText = status.hasManageBacSession
      ? `ManageBac：已检测到登录 cookie（${status.cookieCount || 0} 个）`
      : "ManageBac：未登录";
  } catch (_error) {
    manageBacStatusText = "ManageBac：状态检查失败";
  }
  setTrayMenu();
}

function showSecurityInfo() {
  dialog.showMessageBox({
    type: "info",
    title: `关于 ${APP_DISPLAY_NAME}`,
    message: APP_DISPLAY_NAME,
    detail: [
      "这是 nethub.wiki 的 ManageBac 本地同步辅助程序，用于打开 ManageBac 登录窗口并解析任务预览。",
      "",
      "安全说明：",
      "- 不读取、不保存 ManageBac 账号密码。",
      "- 登录窗口直接访问 ManageBac，账号密码提交给 ManageBac。",
      "- 只在本机保存 Helper 自己的 ManageBac 登录 cookie，用于维持登录状态。",
      "- 不读取 Chrome 或 Edge 浏览器 cookie。",
      "- 不把 cookie 发送给网站；网站只接收解析后的任务预览数据。",
      "- 本地接口只监听 127.0.0.1，并使用短期访问令牌。",
      "",
      "实现说明：",
      "- 网页通过 managebac-sync://wake 唤起本程序；程序启动后在系统托盘常驻。",
      "- 本程序只在本机开启 127.0.0.1 HTTP API，供网页检查状态、打开登录窗口、获取任务预览。",
      "- 登录窗口由本程序内置浏览器打开 ManageBac 页面，登录 cookie 存在本程序独立的 Electron 存储分区。",
      "- 抓取任务时，本程序使用自己的 cookie 请求 ManageBac 任务页，并在本机解析为任务列表。",
      "- 网页只负责展示预览和确认导入；科目识别、导入规则和最终写入由网页端处理。",
      "- 安装时会注册 managebac-sync:// 协议；启动时会校验并覆盖旧路径；卸载时会清理该协议注册。",
      "",
      `本地接口：http://${HOST}:${PORT}`,
      protocolStatusText()
    ].join("\n"),
    buttons: ["知道了"]
  }).catch(() => {});
}

function createTray() {
  if (tray) return;
  const iconPath = getAssetPath("icon.ico");
  const icon = nativeImage.createFromPath(iconPath);
  tray = new Tray(icon.isEmpty() ? iconPath : icon.resize({ width: 16, height: 16 }));
  setTrayMenu();
  refreshTrayStatus();
  trayStatusTimer = setInterval(refreshTrayStatus, 30 * 1000);
  tray.on("double-click", () => createLoginWindow());
}

function quitApp() {
  isQuitting = true;
  if (trayStatusTimer) {
    clearInterval(trayStatusTimer);
    trayStatusTimer = null;
  }
  if (tray) {
    tray.destroy();
    tray = null;
  }
  if (loginWindow && !loginWindow.isDestroyed()) {
    loginWindow.destroy();
    loginWindow = null;
  }
  if (server) {
    server.close();
    server = null;
  }
  app.quit();
}

function createLoginWindow() {
  if (loginWindow && !loginWindow.isDestroyed()) {
    loginWindow.focus();
    return;
  }

  loginWindow = new BrowserWindow({
    width: 1160,
    height: 840,
    title: `ManageBac 登录 - ${APP_DISPLAY_NAME}`,
    icon: getAssetPath("icon.ico"),
    webPreferences: {
      partition: PARTITION,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  loginWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(TARGET_ORIGIN) || url.startsWith("https://assets.managebac.cn")) {
      return { action: "allow" };
    }
    shell.openExternal(url);
    return { action: "deny" };
  });

  loginWindow.on("closed", () => {
    loginWindow = null;
  });

  loginWindow.loadURL(TASKS_URL);
}

function cleanupClientSessions() {
  const now = Date.now();
  for (const [token, value] of clientSessions.entries()) {
    if (now - value.createdAt > TOKEN_TTL_MS) {
      clientSessions.delete(token);
    }
  }
}

function createClientSession(origin, nonce) {
  cleanupClientSessions();
  const token = crypto.randomBytes(24).toString("hex");
  clientSessions.set(token, {
    origin,
    nonce,
    createdAt: Date.now()
  });
  return token;
}

function requireClient(req) {
  cleanupClientSessions();
  const token = String(req.headers["x-managebac-client-token"] || "");
  const client = clientSessions.get(token);
  if (!client) return null;
  return { token, ...client };
}

function corsHeaders(origin) {
  const headers = {
    "Cache-Control": "no-store",
    "Vary": "Origin"
  };
  if (origin && isAllowedOrigin(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Headers"] = "Content-Type, X-ManageBac-Client-Token";
    headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS";
    headers["Access-Control-Allow-Private-Network"] = "true";
  }
  return headers;
}

function writeJson(req, res, status, payload) {
  const origin = req.headers.origin || "";
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    ...corsHeaders(origin)
  });
  res.end(`${JSON.stringify(payload)}\n`);
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 8192) {
        reject(new Error("request body too large"));
        req.destroy();
      }
    });
    req.on("end", () => {
      if (!body) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch (_error) {
        reject(new Error("invalid json"));
      }
    });
    req.on("error", reject);
  });
}

function rejectBadOrigin(req, res) {
  const origin = req.headers.origin || "";
  if (origin && !isAllowedOrigin(origin)) {
    writeJson(req, res, 403, { error: "origin_not_allowed" });
    return true;
  }
  return false;
}

function rejectUnauthorized(req, res) {
  const client = requireClient(req);
  if (!client) {
    writeJson(req, res, 401, { error: "unauthorized" });
    return null;
  }
  return client;
}

async function fetchTasksPreview() {
  const cookies = await getCookies();
  const sessionCookie = cookies.find((cookie) => cookie.name === "_managebac_session");
  if (!sessionCookie) {
    const error = new Error("ManageBac login is required.");
    error.code = "login_required";
    throw error;
  }

  const response = await fetch(TASKS_URL, {
    redirect: "follow",
    headers: {
      accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
      "accept-language": "zh-CN,zh;q=0.9,en-GB;q=0.8,en-US;q=0.7,en;q=0.6",
      "cache-control": "no-cache",
      cookie: buildCookieHeader(cookies),
      pragma: "no-cache",
      "upgrade-insecure-requests": "1",
      "user-agent": USER_AGENT
    }
  });
  const html = await response.text();
  const meta = {
    fetchedAt: new Date().toISOString(),
    url: TASKS_URL,
    status: response.status,
    statusText: response.statusText,
    contentType: response.headers.get("content-type"),
    byteLength: Buffer.byteLength(html, "utf8"),
    title: extractTitle(html),
    detectedLoginPage: isLoginPage(html),
    detectedTasksPage: isTasksPage(html),
    cookieCount: cookies.length,
    hasManageBacSession: true
  };

  if (meta.detectedLoginPage || !meta.detectedTasksPage) {
    const error = new Error("ManageBac login has expired.");
    error.code = "login_required";
    error.meta = meta;
    throw error;
  }

  return {
    tasks: parseManageBacTasks(html, { fetchedAt: meta.fetchedAt }),
    meta
  };
}

async function clearManageBacSession() {
  const ses = getManageBacSession();
  await ses.clearStorageData({
    origin: TARGET_ORIGIN,
    storages: ["cookies", "localstorage", "indexdb", "cachestorage"]
  });
  return getCookieStatus();
}

async function handleRequest(req, res) {
  const origin = req.headers.origin || "";
  if (req.method === "OPTIONS") {
    res.writeHead(isAllowedOrigin(origin) ? 204 : 403, corsHeaders(origin));
    res.end();
    return;
  }
  if (rejectBadOrigin(req, res)) return;

  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  try {
    if (req.method === "GET" && url.pathname === "/v1/health") {
      writeJson(req, res, 200, {
        ok: true,
        version: app.getVersion(),
        protocol: PROTOCOL,
        protocolRegistered,
        protocolStatus: protocolRegistration.status,
        protocolRepaired: protocolRegistration.repaired,
        protocolError: protocolRegistration.error || null,
        port: PORT
      });
      return;
    }

    if (req.method === "POST" && url.pathname === "/v1/session/start") {
      const payload = await readJsonBody(req);
      const nonce = String(payload.nonce || "").slice(0, 128);
      if (!nonce) {
        writeJson(req, res, 400, { error: "nonce_required" });
        return;
      }
      const clientToken = createClientSession(origin, nonce);
      writeJson(req, res, 200, { ok: true, clientToken, expiresInSeconds: TOKEN_TTL_MS / 1000 });
      return;
    }

    const client = rejectUnauthorized(req, res);
    if (!client) return;

    if (req.method === "GET" && url.pathname === "/v1/session") {
      writeJson(req, res, 200, await getCookieStatus());
      return;
    }

    if (req.method === "POST" && url.pathname === "/v1/login/open") {
      createLoginWindow();
      writeJson(req, res, 200, { opened: true });
      return;
    }

    if (req.method === "POST" && url.pathname === "/v1/tasks/preview") {
      const preview = await fetchTasksPreview();
      writeJson(req, res, 200, preview);
      return;
    }

    if (req.method === "POST" && url.pathname === "/v1/session/clear") {
      writeJson(req, res, 200, await clearManageBacSession());
      return;
    }

    writeJson(req, res, 404, { error: "not_found" });
  } catch (error) {
    if (error.code === "login_required") {
      writeJson(req, res, 401, { error: "login_required", message: error.message, meta: error.meta || null });
      return;
    }
    writeJson(req, res, 500, { error: "helper_error", message: error.message || String(error) });
  }
}

function startLocalServer() {
  if (server) return;
  server = http.createServer((req, res) => {
    handleRequest(req, res).catch((error) => {
      writeJson(req, res, 500, { error: "helper_error", message: error.message || String(error) });
    });
  });
  server.on("error", (error) => {
    if (error.code === "EADDRINUSE") {
      dialog.showErrorBox(APP_DISPLAY_NAME, `127.0.0.1:${PORT} 已被占用，Helper 无法启动。`);
      app.quit();
      return;
    }
    dialog.showErrorBox(APP_DISPLAY_NAME, error.message || String(error));
    app.quit();
  });
  server.listen(PORT, HOST, () => {
    console.log(`${APP_DISPLAY_NAME} is running at http://${HOST}:${PORT}`);
    console.log("Keep this process open while testing the website sync flow.");
    if (!app.isPackaged) {
      console.log("Development mode does not register managebac-sync://wake. Start this helper manually before testing.");
    }
  });
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", (_event, argv) => {
    handleProtocolUrl(findProtocolUrl(argv));
  });

  app.whenReady().then(() => {
    protocolRegistered = registerProtocol();
    createTray();
    startLocalServer();
    handleProtocolUrl(findProtocolUrl(process.argv));
  });
}

app.on("before-quit", () => {
  isQuitting = true;
  if (trayStatusTimer) {
    clearInterval(trayStatusTimer);
    trayStatusTimer = null;
  }
  if (server) {
    server.close();
    server = null;
  }
});

app.on("window-all-closed", (event) => {
  if (!isQuitting) event.preventDefault();
});
