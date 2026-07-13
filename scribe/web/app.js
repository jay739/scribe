"use strict";

const $ = (sel) => document.querySelector(sel);
const jobsEl = $("#jobs");
const dropzone = $("#dropzone");
const fileInput = $("#fileInput");
const diarizeToggle = $("#diarizeToggle");
const viewer = $("#viewer");

let pollTimer = null;
let openJobId = null;

function clock(sec) {
  sec = Math.max(0, Math.floor(sec));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const mm = h ? String(m).padStart(2, "0") : String(m);
  return (h ? h + ":" + mm : mm) + ":" + String(s).padStart(2, "0");
}

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/* ---------- health ---------- */

async function loadHealth() {
  try {
    const h = await fetchJSON("/api/health");
    let text = `${h.model} on ${h.device} (${h.compute})`;
    if (!h.diarization_available) {
      text += ` &middot; <span class="warn" title="${(h.diarization_note || "").replace(/"/g, "&quot;")}">diarization unavailable, hover for why</span>`;
    }
    $("#health").innerHTML = text;
  } catch {
    $("#health").textContent = "server unreachable";
  }
}

/* ---------- upload ---------- */

dropzone.addEventListener("click", (e) => {
  if (e.target.closest(".opt")) return;
  fileInput.click();
});
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("drag");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  upload([...e.dataTransfer.files]);
});
fileInput.addEventListener("change", () => {
  upload([...fileInput.files]);
  fileInput.value = "";
});

async function upload(files) {
  for (const file of files) {
    const form = new FormData();
    form.append("file", file);
    form.append("diarize", diarizeToggle.checked);
    try {
      await fetchJSON("/api/jobs", { method: "POST", body: form });
    } catch (err) {
      alert(`upload failed for ${file.name}:\n${err.message}`);
    }
  }
  refresh();
}

/* ---------- job list ---------- */

function jobRow(job) {
  const row = document.createElement("div");
  row.className = "job";

  const name = document.createElement("span");
  name.className = "name";
  name.textContent = job.filename;
  row.appendChild(name);

  const status = document.createElement("span");
  status.className = `status ${job.status}`;
  if (job.status === "running") {
    status.textContent = job.stage || "running";
    const bar = document.createElement("div");
    bar.className = "progress";
    bar.innerHTML = `<div style="width:${Math.round(job.progress * 100)}%"></div>`;
    row.appendChild(bar);
  } else if (job.status === "error") {
    status.textContent = "error";
    status.title = job.error || "";
  } else {
    status.textContent = job.status;
  }
  row.appendChild(status);

  if (job.status === "done") {
    const view = document.createElement("button");
    view.textContent = "view";
    view.onclick = () => openResult(job.id);
    row.appendChild(view);
  }

  const del = document.createElement("button");
  del.textContent = "delete";
  del.onclick = async () => {
    await fetch(`/api/jobs/${job.id}`, { method: "DELETE" });
    if (openJobId === job.id) closeViewer();
    refresh();
  };
  row.appendChild(del);

  return row;
}

async function refresh() {
  let jobs;
  try {
    jobs = await fetchJSON("/api/jobs");
  } catch {
    return;
  }
  jobsEl.replaceChildren();
  if (!jobs.length) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = "no jobs yet";
    jobsEl.appendChild(p);
  } else {
    jobs.forEach((j) => jobsEl.appendChild(jobRow(j)));
  }
  const active = jobs.some(
    (j) => j.status === "queued" || j.status === "running",
  );
  clearTimeout(pollTimer);
  pollTimer = setTimeout(refresh, active ? 1000 : 5000);
}

/* ---------- transcript viewer ---------- */

function speakerClass(result, speaker) {
  if (!speaker) return "";
  const i = result.speakers.indexOf(speaker);
  return `s${(i % 6) + 1}`;
}

async function openResult(id) {
  const result = await fetchJSON(`/api/jobs/${id}/result`);
  openJobId = id;

  $("#viewerTitle").textContent = result.filename;

  const meta = [];
  meta.push(`${clock(result.duration)} long`);
  meta.push(`language: ${result.language}`);
  if (result.diarization.applied) {
    meta.push(`${result.speakers.length} speaker(s)`);
  } else if (result.diarization.requested) {
    meta.push(
      `<span class="warn" title="${(result.diarization.note || "").replace(/"/g, "&quot;")}">no speaker labels, hover for why</span>`,
    );
  }
  $("#viewerMeta").innerHTML = meta.join(" &middot; ");

  const exports = $("#exports");
  exports.replaceChildren();
  for (const fmt of ["txt", "srt", "vtt", "md", "json"]) {
    const a = document.createElement("a");
    a.href = `/api/jobs/${id}/export?format=${fmt}`;
    a.textContent = fmt;
    exports.appendChild(a);
  }

  const transcript = $("#transcript");
  transcript.replaceChildren();
  for (const u of result.utterances) {
    const div = document.createElement("div");
    div.className = `utt ${speakerClass(result, u.speaker)}`;
    const t = document.createElement("span");
    t.className = "t";
    t.textContent = clock(u.start);
    const body = document.createElement("span");
    if (u.speaker) {
      const who = document.createElement("span");
      who.className = "who";
      who.textContent = u.speaker;
      body.appendChild(who);
    }
    body.appendChild(document.createTextNode(u.text));
    div.append(t, body);
    transcript.appendChild(div);
  }

  viewer.hidden = false;
  viewer.scrollIntoView({ behavior: "smooth" });
}

function closeViewer() {
  viewer.hidden = true;
  openJobId = null;
}
$("#closeViewer").addEventListener("click", closeViewer);

/* ---------- init ---------- */

loadHealth();
refresh();
