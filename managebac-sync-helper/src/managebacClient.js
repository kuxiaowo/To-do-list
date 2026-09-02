const PAGE_REQUEST_HEADERS = Object.freeze({
  accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
  "accept-language": "zh-CN,zh;q=0.9,en-GB;q=0.8,en-US;q=0.7,en;q=0.6",
  "cache-control": "no-cache",
  pragma: "no-cache",
  "upgrade-insecure-requests": "1"
});

function fetchManageBacTasksPage(manageBacSession, tasksUrl) {
  return manageBacSession.fetch(tasksUrl, {
    credentials: "include",
    redirect: "follow",
    headers: { ...PAGE_REQUEST_HEADERS }
  });
}

module.exports = {
  PAGE_REQUEST_HEADERS,
  fetchManageBacTasksPage
};
