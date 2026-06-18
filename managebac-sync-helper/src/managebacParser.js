const MANAGEBAC_ORIGIN = "https://sdgj.managebac.cn";

const MONTHS = {
  jan: 0,
  january: 0,
  feb: 1,
  february: 1,
  mar: 2,
  march: 2,
  apr: 3,
  april: 3,
  may: 4,
  jun: 5,
  june: 5,
  jul: 6,
  july: 6,
  aug: 7,
  august: 7,
  sep: 8,
  sept: 8,
  september: 8,
  oct: 9,
  october: 9,
  nov: 10,
  november: 10,
  dec: 11,
  december: 11
};

function decodeHtml(value) {
  return String(value || "")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, "\"")
    .replace(/&#39;/g, "'")
    .replace(/&#(\d+);/g, (_match, code) => String.fromCharCode(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_match, code) => String.fromCharCode(parseInt(code, 16)));
}

function stripTags(value) {
  return decodeHtml(String(value || "").replace(/<[^>]*>/g, " "));
}

function normalizeWhitespace(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function textFromHtml(value) {
  return normalizeWhitespace(stripTags(value));
}

function readAttribute(attrs, name) {
  const pattern = new RegExp(`${name}\\s*=\\s*["']([^"']+)["']`, "i");
  const match = String(attrs || "").match(pattern);
  return match ? decodeHtml(match[1]) : "";
}

function findAnchors(html) {
  const anchors = [];
  const pattern = /<a\b([^>]*)>([\s\S]*?)<\/a>/gi;
  let match;
  while ((match = pattern.exec(html))) {
    anchors.push({
      attrs: match[1],
      href: readAttribute(match[1], "href"),
      className: readAttribute(match[1], "class"),
      body: match[2],
      text: textFromHtml(match[2])
    });
  }
  return anchors;
}

function absoluteManageBacUrl(href) {
  if (!href) return "";
  try {
    return new URL(href, MANAGEBAC_ORIGIN).toString();
  } catch (_error) {
    return href;
  }
}

function formatLocalDateTime(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hour}:${minute}:00`;
}

function parseManageBacDueText(rawText, fetchedAt = new Date()) {
  const text = normalizeWhitespace(rawText);
  const match = text.match(/\b([A-Za-z]{3,9})\s+(\d{1,2})(?:,\s*(\d{4}))?,\s*(\d{1,2}):(\d{2})\s*(AM|PM)\b/i);
  if (!match) return "";

  const month = MONTHS[match[1].toLowerCase()];
  if (month === undefined) return "";

  const fetchedDate = fetchedAt instanceof Date ? fetchedAt : new Date(fetchedAt);
  let year = match[3] ? Number(match[3]) : fetchedDate.getFullYear();
  let hour = Number(match[4]);
  const minute = Number(match[5]);
  const meridiem = match[6].toUpperCase();

  if (meridiem === "PM" && hour < 12) hour += 12;
  if (meridiem === "AM" && hour === 12) hour = 0;

  let dueDate = new Date(year, month, Number(match[2]), hour, minute, 0, 0);
  if (!match[3]) {
    const staleThreshold = new Date(fetchedDate.getFullYear(), fetchedDate.getMonth(), fetchedDate.getDate() - 30);
    if (dueDate < staleThreshold) {
      year += 1;
      dueDate = new Date(year, month, Number(match[2]), hour, minute, 0, 0);
    }
  }

  return formatLocalDateTime(dueDate);
}

function extractDueText(rowHtml) {
  const match = rowHtml.match(/<span[^>]*>\s*<svg[\s\S]*?<\/svg>\s*([^<]+)<\/span>/i);
  return match ? decodeHtml(match[1]) : "";
}

function parseManageBacTasks(html, options = {}) {
  const fetchedAt = options.fetchedAt ? new Date(options.fetchedAt) : new Date();
  const rows = String(html || "")
    .split(/\r?\n/)
    .filter((line) => line.includes("f-tile__body") && line.includes("f-tile__title-link") && line.includes("/core_tasks/"));
  const seen = new Set();
  const tasks = [];

  for (const row of rows) {
    const anchors = findAnchors(row);
    const taskAnchor = anchors.find((anchor) => {
      return anchor.className.includes("f-tile__title-link") && /\/core_tasks\/\d+/.test(anchor.href);
    });
    if (!taskAnchor) continue;

    const classAnchor = anchors.find((anchor) => {
      return /\/student\/classes\/\d+$/.test(anchor.href) && !anchor.href.includes("/core_tasks/");
    });
    const idMatch = taskAnchor.href.match(/\/core_tasks\/(\d+)/);
    const sourceId = idMatch ? `core_task:${idMatch[1]}` : taskAnchor.href;
    if (seen.has(sourceId)) continue;
    seen.add(sourceId);

    const rawCourseName = classAnchor ? classAnchor.text : "";
    const dueText = extractDueText(row);
    const title = taskAnchor.text;
    if (!title || !dueText) continue;

    tasks.push({
      source: "managebac",
      sourceId,
      sourceUrl: absoluteManageBacUrl(taskAnchor.href),
      title,
      subject: "",
      className: rawCourseName,
      rawCourseName,
      dueAt: parseManageBacDueText(dueText, fetchedAt),
      priority: "medium",
      note: `ManageBac: ${sourceId}`
    });
  }

  return tasks;
}

module.exports = {
  decodeHtml,
  parseManageBacDueText,
  parseManageBacTasks
};
