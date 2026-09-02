const TARGET_ORIGIN = "https://sdgj.managebac.cn";
const MANAGEBAC_ASSETS_ORIGIN = "https://assets.managebac.cn";
const DEFAULT_CLIENT_ORIGINS = Object.freeze([
  "http://localhost:8092",
  "http://127.0.0.1:8092",
  "https://nethub.wiki",
  "https://www.nethub.wiki",
  "https://todolist.nethub.wiki"
]);

function configuredClientOrigins(rawConfigured = process.env.MANAGEBAC_ALLOWED_ORIGINS || "") {
  const configured = String(rawConfigured)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return new Set([...DEFAULT_CLIENT_ORIGINS, ...configured]);
}

function isAllowedClientOrigin(origin, rawConfigured) {
  if (!origin) return true;
  if (origin === "null") return false;
  return configuredClientOrigins(rawConfigured).has(origin);
}

function isAllowedManageBacWindowUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    return parsed.origin === TARGET_ORIGIN || parsed.origin === MANAGEBAC_ASSETS_ORIGIN;
  } catch (_error) {
    return false;
  }
}

module.exports = {
  TARGET_ORIGIN,
  MANAGEBAC_ASSETS_ORIGIN,
  DEFAULT_CLIENT_ORIGINS,
  configuredClientOrigins,
  isAllowedClientOrigin,
  isAllowedManageBacWindowUrl
};
