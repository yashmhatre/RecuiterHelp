"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

// ---------------------------------------------------------------- tabs

document.querySelectorAll("nav button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const tab = btn.dataset.tab;
    $("tab-candidates").hidden = tab !== "candidates";
    $("tab-inbox").hidden = tab !== "inbox";
  });
});

$("themeToggle").addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
});
const savedTheme = localStorage.getItem("theme");
if (savedTheme) document.documentElement.setAttribute("data-theme", savedTheme);

// ---------------------------------------------------------------- textareas

function autoGrow(el) {
  if (!el) return;
  el.style.height = "auto";
  // Capped by max-height in CSS; beyond that the box scrolls rather than pushing the
  // Save button off screen.
  el.style.height = Math.min(el.scrollHeight + 2, 420) + "px";
}

function wireGrow(el, counterId) {
  if (!el) return;
  const counter = counterId ? $(counterId) : null;
  const update = () => {
    autoGrow(el);
    if (counter) {
      const n = el.value.trim().length;
      counter.textContent = n ? `— ${n} characters` : "";
    }
  };
  el.addEventListener("input", update);
  el._refresh = update;
  update();
}

// ---------------------------------------------------------------- status

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    const badge = $("backendBadge");
    badge.textContent = data.backend;
    badge.className = "badge " + (data.using_fallback ? "fallback" : "live");
    badge.title = data.using_fallback
      ? "No API key found: using keyword heuristics. Add GEMINI_API_KEY or GROQ_API_KEY to .env."
      : "Using a real model for classification and re-ranking.";
    $("profileCount").textContent =
      data.profiles + (data.profiles === 1 ? " profile" : " profiles");
    if (data.build) $("buildBadge").textContent = "build " + data.build;
  } catch {
    $("backendBadge").textContent = "server offline";
  }
}

// ---------------------------------------------------------------- candidates

async function loadProfiles() {
  const res = await fetch("/api/profiles");
  const { profiles } = await res.json();
  const host = $("profileList");

  if (!profiles.length) {
    host.innerHTML =
      '<div class="empty">No candidates yet. Add one on the left &mdash; matching needs at least one.</div>';
    return;
  }

  const byCandidate = new Map();
  for (const p of profiles) {
    if (!byCandidate.has(p.candidate_id)) byCandidate.set(p.candidate_id, []);
    byCandidate.get(p.candidate_id).push(p);
  }

  host.innerHTML = [...byCandidate.values()]
    .map((group) => {
      const c = group[0];
      const rows = group
        .map((p) => {
          const skills = (p.skills || [])
            .slice(0, 10)
            .map((s) => `<span class="chip">${esc(s)}</span>`)
            .join("");
          const resume = p.has_resume
            ? `<a href="/api/resume/${p.profile_id}" target="_blank">${esc(p.filename)}</a>`
            : '<span style="color:var(--bad)">no resume &mdash; will not be attached</span>';
          return `<div class="profile">
            <div class="top"><span class="tt">${esc(p.title)}</span>
              <span style="color:var(--muted);font-size:12px">#${p.profile_id}</span></div>
            <div class="meta">${Number(p.years_experience)} yrs
              &middot; ${esc(p.location || "location not set")}
              ${p.notice_period_days != null ? "&middot; " + p.notice_period_days + "-day notice" : ""}
              &middot; ${resume}</div>
            <div class="chips">${skills}</div>
          </div>`;
        })
        .join("");
      return `<div style="margin-bottom:18px">
        <div class="top" style="display:flex;gap:8px;align-items:baseline;margin-bottom:6px">
          <span class="nm">${esc(c.name)}</span>
          <span style="color:var(--muted);font-size:12.5px">${esc(c.email)}</span>
          <span class="spacer" style="flex:1"></span>
          <button class="ghost" data-del="${c.candidate_id}">Remove</button>
        </div>${rows}</div>`;
    })
    .join("");

  host.querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Remove this candidate and all their profiles and resumes?")) return;
      await fetch(`/api/candidates/${btn.dataset.del}`, { method: "DELETE" });
      await loadProfiles();
      await refreshStatus();
    });
  });
}

// resume upload -> auto-fill
$("fileDrop").addEventListener("click", () => $("resumeInput").click());
$("resumeInput").addEventListener("change", async () => {
  const file = $("resumeInput").files[0];
  if (!file) return;

  $("fileDrop").classList.add("has-file");
  $("fileLabel").textContent = file.name;
  const note = $("parseNote");
  note.className = "note show";
  note.textContent = "Reading resume…";

  const body = new FormData();
  body.append("resume", file);
  try {
    const res = await fetch("/api/parse-resume", { method: "POST", body });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "could not read the file");

    const h = data.hints || {};
    const setIfEmpty = (el, value) => {
      if (value && !el.value) el.value = value;
    };
    setIfEmpty($("f_name"), h.name);
    setIfEmpty($("f_email"), h.email);
    setIfEmpty($("f_phone"), h.phone);
    setIfEmpty($("f_location"), h.location);
    setIfEmpty($("f_title"), h.title);
    setIfEmpty($("f_skills"), h.skills);
    setIfEmpty($("f_summary"), h.summary);
    if (h.years_experience && !Number($("f_years").value)) $("f_years").value = h.years_experience;

    if ($("f_summary")._refresh) $("f_summary")._refresh();

    const warn = (data.warnings || []).length ? ` Warnings: ${data.warnings.join(", ")}.` : "";
    note.textContent =
      "Pre-filled from the resume — check every field before saving, especially skills and years." +
      warn;
  } catch (err) {
    note.className = "note show";
    note.textContent = "Could not read that file: " + err.message + ". Fill the form by hand.";
  }
});

$("candidateForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = $("saveBtn");
  const notice = $("saveNotice");
  btn.disabled = true;
  btn.textContent = "Saving…";

  try {
    const body = new FormData($("candidateForm"));
    const res = await fetch("/api/candidates", { method: "POST", body });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "save failed");

    notice.className = "notice ok";
    notice.textContent = data.message;

    // Keep name and email so adding a second profile for the same person is quick.
    for (const id of ["f_title", "f_skills", "f_summary"]) $(id).value = "";
    $("f_years").value = "0";
    $("resumeInput").value = "";
    $("fileDrop").classList.remove("has-file");
    $("fileLabel").textContent = "Choose a file to upload and auto-fill";
    $("parseNote").className = "note";
    if ($("f_summary")._refresh) $("f_summary")._refresh();

    await loadProfiles();
    await refreshStatus();
  } catch (err) {
    notice.className = "notice err";
    notice.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Save candidate";
  }
});

// ---------------------------------------------------------------- samples

let SAMPLES = [];

async function loadSamples() {
  const res = await fetch("/api/samples");
  const { samples } = await res.json();
  SAMPLES = samples;

  $("sampleList").innerHTML = samples
    .map(
      (s, i) =>
        `<button type="button" data-i="${i}" class="${
          s.group === "Adversarial" ? "adv" : ""
        }" title="${esc(s.note)}">${esc(s.label)}</button>`
    )
    .join("");

  $("sampleList")
    .querySelectorAll("button")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const s = SAMPLES[Number(btn.dataset.i)];
        $("r_sender").value = s.sender || "";
        $("r_subject").value = s.subject || "";
        $("r_body").value = s.body || "";
        $("r_auth").value = s.auth || "";
        $("r_replyto").value = s.reply_to || "";
        const note = $("sampleNote");
        note.className = "note show";
        note.textContent = s.note || "";
      });
    });
}

// ---------------------------------------------------------------- run

const VERDICTS = {
  drafted: ["drafted", "Draft saved", "Passed every check. A person reviews and sends it."],
  needs_review: ["review", "Needs review — no draft", "Labelled for a human. Nothing was drafted or sent."],
  not_recruiter: ["dropped", "Not a recruiter email", "No draft, no label."],
  skipped_bulk: ["dropped", "Dropped before any model ran", "Bulk or automated mail."],
};

$("runForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = $("runBtn");
  const notice = $("runNotice");
  notice.className = "notice";
  btn.disabled = true;
  btn.textContent = "Running…";

  try {
    const body = new FormData($("runForm"));
    const res = await fetch("/api/run", { method: "POST", body });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "run failed");
    render(data);
  } catch (err) {
    notice.className = "notice err";
    notice.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Run pipeline";
  }
});

function render(data) {
  const [cls, title, sub] = VERDICTS[data.status] || ["review", data.status, ""];
  const parts = [];

  parts.push(`<div class="card">
    <div class="verdict ${cls}">${esc(title)}<small>${esc(sub)}</small></div>
    <h2>Pipeline</h2>
    <p class="hint">Stages run in order. Verification is before classification on purpose, so a
      spoofed sender never reaches a model.</p>
    ${data.stages
      .map(
        (s) => `<div class="stage ${s.ok ? "pass" : "stop"}">
        <div class="stage-head">
          <span class="dot"></span>
          <span class="name">${esc(s.name)}</span>
          <span class="sum">${esc(s.summary)}</span>
        </div>
        ${
          Object.keys(s.detail || {}).length
            ? `<pre hidden>${esc(JSON.stringify(s.detail, null, 2))}</pre>`
            : ""
        }
      </div>`
      )
      .join("")}
    <p class="hint" style="margin:10px 0 0">Model backend: <code>${esc(data.backend)}</code>
      &middot; ${data.profile_count} profile(s) in the database</p>
  </div>`);

  if (data.matches && data.matches.length) {
    parts.push(`<div class="card">
      <h2>Matches</h2>
      <p class="hint">At most one profile per candidate, so the same person is never offered twice.</p>
      <table><thead><tr><th>Candidate</th><th>Profile</th><th>Why</th><th class="num">Score</th></tr></thead>
      <tbody>${data.matches
        .map(
          (m) => `<tr>
            <td>${esc(m.name)}</td>
            <td>${esc(m.title)}</td>
            <td style="color:var(--muted)">${esc(m.reason)}</td>
            <td class="num">${Number(m.score).toFixed(2)}</td>
          </tr>`
        )
        .join("")}</tbody></table>
    </div>`);
  }

  if (data.draft) {
    const d = data.draft;
    const issues = (d.validation && d.validation.issues) || [];
    parts.push(`<div class="card">
      <h2>${d.discarded ? "Draft (discarded by validation)" : "Draft"}</h2>
      <p class="hint">${
        d.discarded
          ? "This is shown so you can see what was rejected. It was not saved."
          : "Review, then send it yourself. The agent has no send path."
      }</p>
      ${
        issues.length
          ? `<div class="verdict dropped">${issues.length} check(s) failed<small>${issues
              .map((i) => esc(i.check) + ": " + esc(i.detail))
              .join("<br>")}</small></div>`
          : ""
      }
      <div class="draft">
        <div class="hdr">
          <div><b>To</b> ${esc((d.to || []).join(", "))}</div>
          <div><b>Subject</b> ${esc(d.subject)}</div>
          <div><b>Thread</b> ${esc(d.thread_id)}</div>
        </div>
        <div class="body">${esc(d.body_text)}</div>
        ${(d.attachments || [])
          .map(
            (a) => `<div class="attach"><span class="clip">&#128206;</span>
              <a href="/api/resume/${a.profile_id}" target="_blank">${esc(a.filename)}</a>
              <span style="color:var(--muted)">&mdash; ${esc(a.candidate_name)}</span></div>`
          )
          .join("")}
      </div>
      ${
        (d.dropped || []).length
          ? `<p class="hint" style="margin-top:10px;color:var(--warn)">Dropped from the draft:
             ${d.dropped.map(esc).join("; ")}</p>`
          : ""
      }
      ${
        d.discarded
          ? ""
          : `<a class="ghost" style="display:inline-block;margin-top:12px;text-decoration:none"
               href="/api/runs/${data.run_id}/eml">Download .eml</a>`
      }
    </div>`);
  }

  $("resultPane").innerHTML = parts.join("");

  // Click a stage to reveal its raw detail.
  $("resultPane")
    .querySelectorAll(".stage-head")
    .forEach((head) => {
      head.addEventListener("click", () => {
        const pre = head.parentElement.querySelector("pre");
        if (pre) pre.hidden = !pre.hidden;
      });
    });
}

// ---------------------------------------------------------------- boot

wireGrow($("f_summary"), "summaryCount");
wireGrow($("r_body"));

refreshStatus();
loadProfiles();
loadSamples();
