const test = require("node:test");
const assert = require("node:assert/strict");

const { fetchManageBacTasksPage } = require("../src/managebacClient");

test("fetchManageBacTasksPage uses the Electron session and its cookies", async () => {
  const expectedResponse = { ok: true };
  const calls = [];
  const manageBacSession = {
    fetch: async (...args) => {
      calls.push(args);
      return expectedResponse;
    }
  };

  const response = await fetchManageBacTasksPage(
    manageBacSession,
    "https://sdgj.managebac.cn/student/tasks_and_deadlines"
  );

  assert.equal(response, expectedResponse);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "https://sdgj.managebac.cn/student/tasks_and_deadlines");
  assert.equal(calls[0][1].credentials, "include");
  assert.equal(calls[0][1].redirect, "follow");
  assert.equal("cookie" in calls[0][1].headers, false);
  assert.equal("user-agent" in calls[0][1].headers, false);
});
