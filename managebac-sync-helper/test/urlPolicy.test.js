const test = require("node:test");
const assert = require("node:assert/strict");

const {
  isAllowedClientOrigin,
  isAllowedManageBacWindowUrl
} = require("../src/urlPolicy");

test("isAllowedClientOrigin allows the production sites and exact configured origins", () => {
  assert.equal(isAllowedClientOrigin("https://nethub.wiki"), true);
  assert.equal(isAllowedClientOrigin("https://www.nethub.wiki"), true);
  assert.equal(isAllowedClientOrigin("https://todolist.nethub.wiki"), true);
  assert.equal(isAllowedClientOrigin("http://localhost:8092"), true);
  assert.equal(isAllowedClientOrigin("http://127.0.0.1:8092"), true);
  assert.equal(isAllowedClientOrigin("https://example.com", "https://example.com"), true);

  assert.equal(isAllowedClientOrigin("https://todolist.nethub.wiki.evil.test"), false);
  assert.equal(isAllowedClientOrigin("http://todolist.nethub.wiki"), false);
  assert.equal(isAllowedClientOrigin("null"), false);
});

test("isAllowedManageBacWindowUrl only allows exact ManageBac origins", () => {
  assert.equal(isAllowedManageBacWindowUrl("https://sdgj.managebac.cn/student/tasks"), true);
  assert.equal(isAllowedManageBacWindowUrl("https://assets.managebac.cn/app.css"), true);

  assert.equal(isAllowedManageBacWindowUrl("https://sdgj.managebac.cn.evil.test/phish"), false);
  assert.equal(isAllowedManageBacWindowUrl("https://assets.managebac.cn.evil.test/app.css"), false);
  assert.equal(isAllowedManageBacWindowUrl("not a url"), false);
});
