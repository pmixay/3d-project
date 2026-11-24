"use strict";
const $ = (id) => document.getElementById(id);
const TOKEN_KEY = "hercules-token";
let token = "";
try { token = localStorage.getItem(TOKEN_KEY) || ""; } catch (e) { /* storage unavailable */ }
let thresholds = { warn: 0.38, critical: 0.665 };
let history = [];
let lastStatus = null;
let roi = [0, 0, 1, 1];

async function api(path, opts = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  if (token) headers["X-Hercules-Token"] = token;
  const r = await fetch(path, Object.assign({}, opts, { headers }));
  if (r.status === 401) {
    const t = prompt("This dashboard requires an access token (web.auth_token):");
    if (t) { token = t; try { localStorage.setItem(TOKEN_KEY, t); } catch (e) {} return api(path, opts); }
  }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || body.detail || r.statusText);
  return body;
}
const post = (path, data) => api(path, { method: "POST", body: JSON.stringify(data || {}) });

function fmtDur(s) {
  if (s == null || isNaN(s)) return "—";
  s = Math.round(s); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), sec = s % 60;
  return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(sec).padStart(2, "0");
}
const fmt = (v, d = 2) => (v == null || isNaN(v)) ? "—" : Number(v).toFixed(d);
const tstr = (t) => t ? new Date(t * 1000).toLocaleString() : "—";
function pill(id, cls, text) { const el = $(id); el.className = "pill " + cls; el.textContent = text; }

// ---------------------------------------------------------------- status
function renderStatus(s) {
  lastStatus = s;
  thresholds = s.thresholds;
  const m = s.monitoring, cam = s.camera, pr = s.printer, an = s.analysis, met = s.metrics;
  $("mon-enabled").checked = m.enabled;
  pill("pill-mon", !m.enabled ? "" : m.active ? "ok" : "info", m.active ? "monitoring" : (m.enabled ? "standby" : "disabled"));
  $("pill-mon").title = m.reason;
  const camCls = { online: "ok", stalled: "warn", connecting: "warn", offline: "crit", ended: "info", stopped: "" }[cam.state] || "";
  pill("pill-cam", camCls, "camera " + cam.state);
  $("pill-cam").title = cam.error || cam.source;
  if (!pr.enabled) pill("pill-printer", "", "no printer link");
  else pill("pill-printer", pr.connected ? (pr.state === "printing" ? "ok" : "info") : "crit",
    pr.connected ? "printer " + pr.state : "printer offline");
  $("pill-printer").title = pr.error || pr.url;
  pill("pill-model", "ok", s.detector.backend);
  $("pill-model").title = s.detector.providers.join(", ");

  $("feed-meta").textContent = `${cam.kind} · ${cam.resolution.join("×")} · ${fmt(cam.fps, 1)} fps` + (an && an.frame_label ? " · " + an.frame_label : "");
  $("feed-off").classList.toggle("hidden", cam.state === "online" || cam.state === "ended" || cam.frames > 0);

  const a = an && an.assessment;
  const lvl = $("level");
  if (!m.active) { lvl.className = "level idle"; lvl.textContent = "IDLE"; }
  else if (!a) { lvl.className = "level idle"; lvl.textContent = an && an.skipped ? "FRAME SKIPPED" : "WAITING"; }
  else {
    lvl.className = "level " + a.level;
    let t = a.level.toUpperCase();
    if (a.warmup) t += " · warm-up"; else if (a.suppressed) t += " · suppressed";
    else if (a.level === "ok" && a.raw_level !== "ok") t += " · awaiting evidence";
    lvl.textContent = t;
  }
  $("d-type").textContent = a && a.level !== "ok" ? "spaghetti / filament mess" : (s.open_camera_incidents && Object.keys(s.open_camera_incidents).length ? Object.keys(s.open_camera_incidents).join(", ").replace(/_/g, " ") : "none");
  $("d-score").textContent = a ? `${fmt(a.score)} (warn ${fmt(thresholds.warn)})` : "—";
  $("d-p").textContent = a ? fmt(a.p) : "—";
  $("d-conf").textContent = an ? fmt(an.max_conf) : "—";
  $("d-ev").textContent = a ? String(a.evidence) : "—";
  $("d-q").textContent = an ? (an.skipped ? "skipped: " + an.skipped : (an.quality.flags.join(", ") || "ok")) : "—";
  $("det-age").textContent = an ? Math.max(0, Math.round(s.time - an.t)) + " s ago" : "—";

  $("p-state").textContent = !pr.enabled ? "not configured" : pr.connected ? pr.state : "unreachable";
  $("p-file").textContent = pr.filename || "—"; $("p-file").title = pr.filename || "";
  $("p-time").textContent = fmtDur(pr.print_duration);
  $("p-layer").textContent = pr.current_layer != null ? `${pr.current_layer} / ${pr.total_layer || "?"}` : "—";
  const prog = pr.progress || 0;
  $("p-bar").style.width = (100 * prog).toFixed(1) + "%";
  $("p-prog").textContent = pr.connected ? (100 * prog).toFixed(1) + " %" : "—";
  $("btn-pause").disabled = !(pr.connected && pr.state === "printing");

  $("s-backend").textContent = s.detector.providers[0].replace("ExecutionProvider", "");
  $("s-cpu").textContent = `${fmt(met.cpu_system_pct, 0)} % / ${fmt(met.cpu_process_pct, 0)} %`;
  $("s-ram").textContent = `${fmt(met.ram_system_pct, 0)} % / ${fmt(met.ram_process_mb, 0)} MB`;
  $("s-temp").textContent = met.cpu_temp_c != null ? met.cpu_temp_c + " °C" : "n/a";
  $("s-lat").textContent = met.latency_ms_mean != null ? `${met.latency_ms_mean} / ${met.latency_ms_p95} ms` : "—";
  $("s-rate").textContent = String(met.inferences_per_min);
  $("s-cam").textContent = `${fmt(cam.fps, 1)} / ${cam.resolution.join("×")}`;
  const c = met.counters || {};
  $("s-skip").textContent = `${c.skipped_duplicate || 0} / ${c.skipped_blurred || 0} / ${c.skipped_unusable || 0}`;
}

// ---------------------------------------------------------------- chart
function drawChart() {
  const cv = $("chart"), dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = 150;
  cv.width = w * dpr; cv.height = h * dpr;
  const g = cv.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
  const now = Date.now() / 1000, t0 = now - 1800;
  const pts = history.filter(p => p[0] >= t0);
  const vmax = Math.max(thresholds.critical * 1.25, ...pts.map(p => Math.max(p[1], p[2])), 0.5);
  const X = t => 36 + (w - 44) * (t - t0) / 1800, Y = v => h - 18 - (h - 28) * Math.max(0, v) / vmax;
  g.font = "10px ui-monospace,monospace"; g.fillStyle = "#6e7681"; g.strokeStyle = "#20252c"; g.lineWidth = 1;
  for (let i = 0; i <= 4; i++) { const v = vmax * i / 4, y = Y(v); g.beginPath(); g.moveTo(36, y); g.lineTo(w - 8, y); g.stroke(); g.fillText(v.toFixed(2), 2, y + 3); }
  for (let m = 0; m <= 30; m += 10) g.fillText(m === 0 ? "now" : `-${m}m`, X(now - m * 60) - 10, h - 4);
  [[thresholds.warn, "#e3a008"], [thresholds.critical, "#f85149"]].forEach(([v, col]) => {
    g.strokeStyle = col; g.setLineDash([4, 4]); g.beginPath(); g.moveTo(36, Y(v)); g.lineTo(w - 8, Y(v)); g.stroke(); g.setLineDash([]);
  });
  const line = (idx, col, lw) => {
    if (pts.length < 2) return; g.strokeStyle = col; g.lineWidth = lw; g.beginPath();
    pts.forEach((p, i) => i ? g.lineTo(X(p[0]), Y(p[idx])) : g.moveTo(X(p[0]), Y(p[idx]))); g.stroke();
  };
  line(2, "#4a525c", 1); line(1, "#58a6ff", 2);
  $("chart-meta").textContent = pts.length ? `${pts.length} analyses · last 30 min` : "no analyses yet";
}

// ---------------------------------------------------------------- incidents
let incidents = [];
function renderIncidents(list) {
  incidents = list;
  const tb = $("inc-body");
  $("inc-count").textContent = list.length ? `${list.length} shown` : "";
  if (!list.length) { tb.innerHTML = '<tr><td colspan="9" class="muted">no incidents yet</td></tr>'; }
  else tb.innerHTML = list.map(i => {
    const img = i.evidence.find(f => f.includes("annotated"));
    const thumb = img ? `<a href="/incidents/${i.id}/${img}" target="_blank"><img loading="lazy" src="/incidents/${i.id}/${img}" alt="evidence"></a>` : "";
    const actions = i.status === "open"
      ? `<button class="btn small" data-dismiss="${i.id}">False alarm</button>` : "";
    return `<tr><td>${thumb}</td><td class="mono">${i.id}</td><td>${i.label}</td>
      <td><span class="tag ${i.severity}">${i.severity}</span></td><td><span class="tag ${i.status}">${i.status}</span></td>
      <td class="mono">${tstr(i.started_at)}</td><td class="mono">${fmt(i.peak_score)}</td>
      <td title="${(i.action_detail || "").replace(/"/g, "&quot;")}">${i.action.replace(/_/g, " ")}</td>
      <td>${actions} <a class="btn small ghost" href="/incidents/${i.id}/report.html" target="_blank">Report</a></td></tr>`;
  }).join("");
  // banner for the open failure incident (or newest open camera incident)
  const open = list.find(i => i.status === "open" && i.category === "failure") || list.find(i => i.status === "open");
  const al = $("alert");
  if (!open) { al.classList.add("hidden"); return; }
  al.classList.remove("hidden"); al.classList.toggle("warn", open.severity !== "critical");
  $("alert-title").textContent = `Incident #${open.id}: ${open.label}`;
  const waiting = open.action === "awaiting_confirmation";
  $("alert-text").textContent = waiting ? " — critical: confirm to pause the print." : ` — ${open.action_detail || open.action}`;
  $("alert-pause").dataset.id = open.id;
  $("alert-pause").disabled = !(lastStatus && lastStatus.printer.connected && lastStatus.printer.state === "printing");
  $("alert-dismiss").dataset.id = open.id;
  $("alert-report").href = `/incidents/${open.id}/report.html`;
}

// ---------------------------------------------------------------- settings
let settingsMeta = null;
function fillSettings(s) {
  settingsMeta = s;
  const form = $("settings");
  for (const [sec, vals] of Object.entries(s.values)) for (const [k, v] of Object.entries(vals)) {
    const el = form.elements[`${sec}.${k}`]; if (!el) continue;
    if (el.type === "checkbox") el.checked = !!v; else el.value = v;
  }
  $("cats").innerHTML = '<div class="muted" style="font-size:12px;margin-bottom:4px">Enabled detection categories</div>' +
    s.categories.map(c => `<label class="chk"><input type="checkbox" data-cat="${c}" ${s.values.decision.enabled_categories.includes(c) ? "checked" : ""}>${c.replace(/_/g, " ")}</label>`).join("");
  roi = s.values.pipeline.roi.slice(); drawRoi();
}
function collectSettings() {
  const form = $("settings"), out = {};
  for (const [sec, keys] of Object.entries(settingsMeta.editable)) for (const k of keys) {
    const el = form.elements[`${sec}.${k}`]; if (!el) continue;
    let v = el.type === "checkbox" ? el.checked : el.type === "number" ? Number(el.value) : el.value;
    if (v === settingsMeta.values[sec][k]) continue;
    (out[sec] = out[sec] || {})[k] = v;
  }
  const cats = [...document.querySelectorAll("[data-cat]")].filter(x => x.checked).map(x => x.dataset.cat);
  if (JSON.stringify(cats) !== JSON.stringify(settingsMeta.values.decision.enabled_categories)) (out.decision = out.decision || {}).enabled_categories = cats;
  if (JSON.stringify(roi) !== JSON.stringify(settingsMeta.values.pipeline.roi)) (out.pipeline = out.pipeline || {}).roi = roi;
  return out;
}
$("settings").addEventListener("submit", async (e) => {
  e.preventDefault();
  const changes = collectSettings();
  if (!Object.keys(changes).length) { $("set-msg").textContent = "nothing changed"; return; }
  try { fillSettings(await post("/api/settings", changes)); $("set-msg").textContent = "saved " + new Date().toLocaleTimeString(); }
  catch (err) { $("set-msg").textContent = "error: " + err.message; }
});

// ROI editor
function drawRoi() {
  const b = $("roi-box");
  b.style.left = roi[0] * 100 + "%"; b.style.top = roi[1] * 100 + "%";
  b.style.width = (roi[2] - roi[0]) * 100 + "%"; b.style.height = (roi[3] - roi[1]) * 100 + "%";
  $("roi-val").textContent = "ROI " + roi.map(v => v.toFixed(2)).join(", ");
}
(function roiEditor() {
  const wrap = document.querySelector(".roi-wrap"); let start = null;
  const pos = (e) => { const r = wrap.getBoundingClientRect(); return [Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))]; };
  wrap.addEventListener("pointerdown", e => { start = pos(e); wrap.setPointerCapture(e.pointerId); });
  wrap.addEventListener("pointermove", e => { if (!start) return; const p = pos(e);
    roi = [Math.min(start[0], p[0]), Math.min(start[1], p[1]), Math.max(start[0], p[0]), Math.max(start[1], p[1])].map(v => +v.toFixed(3)); drawRoi(); });
  wrap.addEventListener("pointerup", () => { start = null; if (roi[2] - roi[0] < 0.05 || roi[3] - roi[1] < 0.05) { roi = settingsMeta.values.pipeline.roi.slice(); drawRoi(); } });
  $("roi-reset").onclick = () => { roi = [0, 0, 1, 1]; drawRoi(); };
  const refresh = () => { $("roi-img").src = "/snapshot.jpg?raw=1&t=" + Date.now(); };
  $("roi-img").onerror = () => setTimeout(refresh, 5000);
  refresh(); setInterval(refresh, 30000);
})();

// ---------------------------------------------------------------- actions
document.addEventListener("click", async (e) => {
  const d = e.target.dataset && e.target.dataset.dismiss;
  if (d) { if (confirm(`Mark incident #${d} as a false alarm?`)) { await post(`/api/incidents/${d}/dismiss`).catch(err => alert(err.message)); pollIncidents(); } }
});
$("alert-dismiss").onclick = async (e) => { const id = e.target.dataset.id; if (id && confirm(`Mark incident #${id} as a false alarm?`)) { await post(`/api/incidents/${id}/dismiss`).catch(err => alert(err.message)); pollIncidents(); } };
$("alert-pause").onclick = async (e) => { const id = e.target.dataset.id; if (!confirm("Pause the print now?")) return;
  try { const r = await post(`/api/incidents/${id}/pause`); alert(r.detail); } catch (err) { alert("Pause failed: " + err.message); } pollIncidents(); };
$("btn-pause").onclick = async () => { if (!confirm("Pause the print now?")) return;
  try { const r = await post("/api/printer/pause"); alert(r.detail); } catch (err) { alert("Pause failed: " + err.message); } };
$("mon-enabled").onchange = async (e) => { await post("/api/monitoring", { enabled: e.target.checked }).catch(err => alert(err.message)); };

// ---------------------------------------------------------------- polling
async function pollStatus() {
  try {
    renderStatus(await api("/api/status"));
    const since = history.length ? history[history.length - 1][0] : 0;
    const h = await api("/api/history?since=" + since);
    history = history.concat(h.points).filter(p => p[0] > Date.now() / 1000 - 1800);
    drawChart();
  } catch (e) { pill("pill-mon", "crit", "backend unreachable"); }
}
async function pollIncidents() { try { renderIncidents(await api("/api/incidents?limit=30")); } catch (e) {} }
function startFeed() {
  const img = $("feed");
  img.onerror = () => { $("feed-off").classList.remove("hidden"); setTimeout(() => { img.src = "/stream.mjpg?t=" + Date.now(); }, 3000); };
  img.onload = () => $("feed-off").classList.add("hidden");
  img.src = "/stream.mjpg";
}
api("/api/settings").then(fillSettings).catch(() => {});
startFeed(); pollStatus(); pollIncidents();
setInterval(pollStatus, 1000); setInterval(pollIncidents, 3000);
window.addEventListener("resize", drawChart);
