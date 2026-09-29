const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

let options;
const context = {
  Vue: { createApp(value) { options = value; return { use() { return this; }, mount() {} }; } },
  ElementPlus: {},
  window: {},
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('web/app.js', 'utf8'), context);
const methods = options.methods;
const dates = {
  todayDateKey: '2026-09-29',
  dayRange: { past: 2, future: 2 },
  locale: 'zh-CN',
  todoTasksByDueDate: {},
};
for (const name of ['startOfDay', 'parseDateKey', 'timelineStartDate', 'timelineEndDate',
  'addDays', 'daysBetween', 'formatDateKey', 'formatDateLabel', 'relativeLabel', 'pad']) {
  dates[name] = methods[name].bind(dates);
}
let columns = options.computed.dayColumns.call(dates);
assert.equal(columns.find(day => day.key === '2026-09-29').subtitle, '今天');
dates.todayDateKey = '2026-09-30';
columns = options.computed.dayColumns.call(dates);
assert.equal(columns.find(day => day.key === '2026-09-29').subtitle, '昨天');
assert.equal(columns.at(-1).key, '2026-10-02');

let target;
const navigation = {
  activePage: 'ddl',
  currentViewDateKey: '2026-09-29',
  rememberCurrentViewDate() { this.currentViewDateKey = '2026-10-04'; },
  parseDateKey: dates.parseDateKey,
  addDays: dates.addDays,
  scrollToDate(date, page, behavior) { target = [dates.formatDateKey(date), page, behavior]; },
};
methods.jumpToOffset.call(navigation, -7);
assert.deepEqual(target, ['2026-09-27', 'ddl', 'instant'], 'week navigation uses the visible date');

const timeline = {
  scrollLeft: 0,
  scrollWidth: 1000,
  clientWidth: 200,
  style: { scrollBehavior: '' },
  getBoundingClientRect() { return { left: 0 }; },
  querySelector(selector) {
    assert.equal(selector, '[data-day="2026-09-29"]');
    return { getBoundingClientRect() { return { left: 500, width: 100 }; } };
  },
};
const locate = {
  activePage: 'ddl',
  pageViewDateKeys: { ddl: '' },
  parseDateKey: dates.parseDateKey,
  formatDateKey: dates.formatDateKey,
  ensureDateRangeForKey() { return false; },
  timelineScrollElements() { return { content: timeline }; },
  updateTimelineStickyScrollbar() {},
  syncTimelineStickyScrollbar() {},
  pauseTimelineAutoExpand() {},
};
methods.scrollToDate.call(locate, '2026-09-29', 'ddl', 'instant');
assert.equal(timeline.scrollLeft, 450, 'locate date centers its column');
assert.equal(locate.currentViewDateKey, '2026-09-29');

let restored;
const rollover = {
  todayDateKey: '2000-01-01',
  activePage: 'ddl',
  pageViewDateKeys: { ddl: '2026-09-29' },
  currentViewDateKey: '2026-09-29',
  formatDateKey: dates.formatDateKey,
  rememberCurrentViewDate() {},
  $nextTick(callback) { callback(); },
  scrollToDate(...args) { restored = args; },
  updateTimelineStickyScrollbars() {},
};
methods.refreshTodayDate.call(rollover);
assert.equal(rollover.todayDateKey, dates.formatDateKey(new Date()));
assert.equal(restored[0], '2026-09-29', 'date rollover preserves the visible timeline date');

const content = { scrollLeft: 100 };
const sticky = { scrollLeft: 0 };
const scroll = {
  timelineExpectedScroll: { ddl: { content: null, sticky: null } },
  timelineScrollElements() { return { content, sticky }; },
};
methods.syncTimelineStickyScrollbar.call(scroll, 'ddl', 'content');
assert.equal(sticky.scrollLeft, 100);
content.scrollLeft = 125;
methods.syncTimelineStickyScrollbar.call(scroll, 'ddl', 'sticky');
assert.equal(content.scrollLeft, 125, 'programmatic sticky event must not cancel content scrolling');
