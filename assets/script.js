/* assets/script.js */
"use strict";

/** Config */
const EVENTS_JSON_URL = "./data/events.json";

/** State */
let allData = [];
let filtered = [];

/** Elements */
const els = {
  tbody: document.getElementById("table-body"),
  lastUpdated: document.getElementById("last-updated"),
  count: document.getElementById("count-badge"),
  fName: document.getElementById("filter-name"),
  fStart: document.getElementById("filter-start"),
  fEnd: document.getElementById("filter-end"),
  fLoc: document.getElementById("filter-location"),
  fUrl: document.getElementById("filter-url"),
};

/** Utils */
function safe(val) {
  return (val ?? "").toString().trim();
}

function escapeHtml(str) {
  return safe(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function isValidHttpUrl(maybeUrl) {
  try {
    const u = new URL(maybeUrl);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

/** Rendering */
function rowHtml(evt) {
  const name = escapeHtml(evt.name);
  const start = escapeHtml(evt.start_date);
  const end = escapeHtml(evt.end_date);
  const loc = escapeHtml(evt.location);
  const urlRaw = safe(evt.url || evt.link);
  const url = isValidHttpUrl(urlRaw) ? urlRaw : "";
  const a = url ? `<a class="link" href="${escapeHtml(url)}" target="_blank" rel="noopener">Open</a>` : "";

  return `
    <tr>
      <td>${name}</td>
