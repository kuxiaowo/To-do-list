const test = require("node:test");
const assert = require("node:assert/strict");

const {
  isAllowedManageBacWindowUrl
} = require("../src/urlPolicy");

test("isAllowedManageBacWindowUrl only allows exact ManageBac origins", () => {
  assert.equal(isAllowedManageBacWindowUrl("https://sdgj.managebac.cn/student/tasks"), true);
  assert.equal(isAllowedManageBacWindowUrl("https://assets.managebac.cn/app.css"), true);

  assert.equal(isAllowedManageBacWindowUrl("https://sdgj.managebac.cn.evil.test/phish"), false);
  assert.equal(isAllowedManageBacWindowUrl("https://assets.managebac.cn.evil.test/app.css"), false);
  assert.equal(isAllowedManageBacWindowUrl("not a url"), false);
});
