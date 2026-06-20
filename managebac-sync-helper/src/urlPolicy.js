const TARGET_ORIGIN = "https://sdgj.managebac.cn";
const MANAGEBAC_ASSETS_ORIGIN = "https://assets.managebac.cn";

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
  isAllowedManageBacWindowUrl
};
