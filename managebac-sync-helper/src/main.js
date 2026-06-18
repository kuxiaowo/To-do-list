const { app, BrowserWindow, dialog, session, shell } = require("electron");
const http = require("node:http");
const crypto = require("node:crypto");
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

const clientSessions = new Map();
let server;
let loginWindow;
let protocolRegistered = false;

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

function registerProtocol() {
  if (!app.isPackaged) return false;
  return app.setAsDefaultProtocolClient(PROTOCOL);
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

function createLoginWindow() {
  if (loginWindow && !loginWindow.isDestroyed()) {
    loginWindow.focus();
    return;
  }

  loginWindow = new BrowserWindow({
    width: 1160,
    height: 840,
    title: "ManageBac Login",
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
      dialog.showErrorBox("ManageBac Sync Helper", `127.0.0.1:${PORT} 已被占用，Helper 无法启动。`);
      app.quit();
      return;
    }
    dialog.showErrorBox("ManageBac Sync Helper", error.message || String(error));
    app.quit();
  });
  server.listen(PORT, HOST, () => {
    console.log(`ManageBac Sync Helper is running at http://${HOST}:${PORT}`);
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
    startLocalServer();
    handleProtocolUrl(findProtocolUrl(process.argv));
  });
}

app.on("before-quit", () => {
  if (server) {
    server.close();
    server = null;
  }
});

app.on("window-all-closed", (event) => {
  event.preventDefault();
});
