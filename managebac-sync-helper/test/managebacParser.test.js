const test = require("node:test");
const assert = require("node:assert/strict");

const {
  parseManageBacDueText,
  parseManageBacTasks
} = require("../src/managebacParser");

test("parseManageBacDueText normalizes ManageBac English dates", () => {
  assert.equal(
    parseManageBacDueText("Jun 21, 11:55 PM", new Date("2026-06-18T00:00:00")),
    "2026-06-21T23:55:00"
  );
  assert.equal(
    parseManageBacDueText("Jan 2, 12:05 AM", new Date("2026-12-30T00:00:00")),
    "2027-01-02T00:05:00"
  );
});

test("parseManageBacTasks extracts task preview records", () => {
  const html = `
<div class="f-tile__body"><p class="f-tile__title h5"><a class="f-tile__title-link link-dark f-truncate-item" href="/student/classes/11465612/core_tasks/27421385"><span class="f-truncate-item">Final Group Project</span></a></p><div class="f-tile__description color-secondary"><div class="hstack gap-2 flex-wrap f-truncate"><span><svg></svg> Jun 21, 11:55 PM</span><span class="vr"></span><a class="f-truncate-item link-dark" href="/student/classes/11465612">HS Computer（25级选修） (Grade 10)</a></div></div></div>
<div class="f-tile__body"><p class="f-tile__title h5"><a class="f-tile__title-link link-dark f-truncate-item" href="/student/classes/11450107/core_tasks/27437018"><span class="f-truncate-item">Textbook practice: thermal energy transfers 2</span></a></p><div class="f-tile__description color-secondary"><div class="hstack gap-2 flex-wrap f-truncate"><span><svg></svg> Jun 23, 3:35 PM</span><span class="vr"></span><a class="f-truncate-item link-dark" href="/student/classes/11450107">IB DP PDP Physics-C（25级） (Grade 10)</a></div></div></div>
`;
  const tasks = parseManageBacTasks(html, { fetchedAt: "2026-06-18T10:50:26.270Z" });
  assert.equal(tasks.length, 2);
  assert.deepEqual(tasks[0], {
    source: "managebac",
    sourceId: "core_task:27421385",
    sourceUrl: "https://sdgj.managebac.cn/student/classes/11465612/core_tasks/27421385",
    title: "Final Group Project",
    subject: "",
    className: "HS Computer（25级选修） (Grade 10)",
    rawCourseName: "HS Computer（25级选修） (Grade 10)",
    dueAt: "2026-06-21T23:55:00",
    priority: "medium",
    note: "ManageBac: core_task:27421385"
  });
  assert.equal(tasks[1].subject, "");
  assert.equal(tasks[1].className, "IB DP PDP Physics-C（25级） (Grade 10)");
});
