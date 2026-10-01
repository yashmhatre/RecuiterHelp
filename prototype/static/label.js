"use strict";
// Labelling screen. Loaded after app.js, so $ and esc already exist.
//
// Keyboard-first on purpose: this is 200-300 repetitions, and the difference between a few
// keystrokes and a mouse round-trip per email decides whether the set ever gets finished.

let CURRENT = null;
let IS_RECRUITER = null;
let INTENT = null;

const INTENT_KEYS = {
  1: "new_requirement",
  2: "resume_request",
  3: "follow_up",
  4: "interview",
  5: "other",
};

function renderProgress(s) {
  const pct = Math.min(100, Math.round((s.labelled / s.target_min) * 100));
  const shareOk = s.non_recruiter_share >= s.target_non_recruiter_share;
  const missing = s.missing_intents || [];

  $("labelProgress").innerHTML = `
    <h2>Progress</h2>
    <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:baseline;margin-bottom:10px">
      <span style="font-size:26px;font-weight:700;font-family:var(--mono)">${s.labelled}</span>
      <span style="color:var(--muted)">of ${s.target_min}&ndash;${s.target_max} target
        &middot; ${s.remaining} left in the queue
        ${s.skipped ? "&middot; " + s.skipped + " skipped" : ""}</span>
    </div>
    <div style="height:6px;background:var(--bg);border-radius:3px;overflow:hidden;margin-bottom:12px">
      <div style="height:100%;width:${pct}%;background:var(--accent)"></div>
    </div>
    <div class="chips">
      <span class="chip">${s.recruiter} recruiter</span>
      <span class="chip" style="color:${shareOk ? "var(--ok)" : "var(--warn)"}">
        ${s.non_recruiter} not recruiter (${Math.round(s.non_recruiter_share * 100)}%,
        need ${Math.round(s.target_non_recruiter_share * 100)}%)</span>
      ${Object.entries(s.intents || {})
        .map(([k, v]) => `<span class="chip">${esc(k)} ${v}</span>`)
        .join("")}
      ${missing.length
        ? `<span class="chip" style="color:var(--warn)">missing: ${missing.map(esc).join(", ")}</span>`
        : ""}
    </div>`;
}

function resetForm() {
  IS_RECRUITER = null;
  INTENT = null;
  for (const id of ["lab_role", "lab_skills", "lab_years", "lab_location", "lab_names",
                    "lab_profiles", "lab_notes"]) {
    $(id).value = "";
  }
  $("lab_resume").checked = false;
  $("labelRecruiterFields").hidden = true;
  document.querySelectorAll("#labelRecruiter button, #labelIntent button")
    .forEach((b) => b.classList.remove("adv"));
}

function setRecruiter(value) {
  IS_RECRUITER = value;
  $("labelRecruiterFields").hidden = !value;
  document.querySelectorAll("#labelRecruiter button").forEach((b) =>
    b.classList.toggle("adv", (b.dataset.rec === "yes") === value)
  );
}

function setIntent(intent) {
  INTENT = intent;
  document.querySelectorAll("#labelIntent button").forEach((b) =>
    b.classList.toggle("adv", b.dataset.intent === intent)
  );
}

async function loadNextLabel() {
  const data = await (await fetch("/api/label/next")).json();
  renderProgress(data.stats);
  CURRENT = data.email;
  resetForm();
  $("labelNotice").className = "notice";

  if (!CURRENT) {
    $("labelEmail").innerHTML =
      '<div class="empty">Queue empty. Pull more from the Gmail tab.</div>';
    $("labelCounter").textContent = "";
    return;
  }

  $("labelCounter").textContent = `#${CURRENT.id}`;
  const h = CURRENT.headers || {};
  $("labelEmail").innerHTML = `
    <div class="draft">
      <div class="hdr">
        <div><b>From</b> ${esc(h.from || "(unknown)")}</div>
        <div><b>Subject</b> ${esc(CURRENT.subject || "(no subject)")}</div>
        ${h["list-unsubscribe"] ? '<div><b>Bulk</b> has List-Unsubscribe</div>' : ""}
      </div>
      <div class="body" style="max-height:460px;overflow:auto">${esc(CURRENT.body_text || "")}</div>
    </div>`;
}

async function saveLabel() {
  if (!CURRENT) return;
  const notice = $("labelNotice");

  if (IS_RECRUITER === null) {
    notice.className = "notice err";
    notice.textContent = "Press y or n first: is this from a recruiter?";
    return;
  }
  if (IS_RECRUITER && !INTENT) {
    notice.className = "notice err";
    notice.textContent = "Pick an intent, 1 to 5.";
    return;
  }

  const list = (id) =>
    $(id).value.split(",").map((v) => v.trim()).filter(Boolean);
  const intent = IS_RECRUITER ? INTENT : "other";
  const profileIds = list("lab_profiles")
    .map((v) => parseInt(v, 10))
    .filter((v) => !Number.isNaN(v));

  // The schema requires these for a recruiter requirement or resume request, so say so here
  // rather than letting the server reject it after the fact.
  if (IS_RECRUITER && ["new_requirement", "resume_request"].includes(intent) && !profileIds.length) {
    notice.className = "notice err";
    notice.textContent =
      "Profile IDs are required for a requirement or a resume request — which of our " +
      "candidates should match? Use 0 if genuinely none.";
    return;
  }

  const years = parseFloat($("lab_years").value);
  const record = {
    id: CURRENT.id,
    provider: CURRENT.provider || "gmail",
    headers: CURRENT.headers || {},
    subject: CURRENT.subject || "",
    body_text: CURRENT.body_text || "",
    is_recruiter: IS_RECRUITER,
    intent,
    fields: {
      role: $("lab_role").value.trim() || null,
      skills: list("lab_skills").map((s) => s.toLowerCase()),
      min_years_experience: Number.isNaN(years) ? null : years,
      location: $("lab_location").value.trim() || null,
      candidate_names: list("lab_names"),
      resume_requested: $("lab_resume").checked,
    },
    expected_profile_ids: profileIds,
    notes: $("lab_notes").value.trim(),
  };

  const body = new FormData();
  body.append("record", JSON.stringify(record));
  try {
    const res = await fetch("/api/label/save", { method: "POST", body });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "save failed");
    await loadNextLabel();
  } catch (err) {
    notice.className = "notice err";
    notice.textContent = err.message;
  }
}

async function skipLabel() {
  if (!CURRENT) return;
  const body = new FormData();
  body.append("email_id", CURRENT.id);
  await fetch("/api/label/skip", { method: "POST", body });
  await loadNextLabel();
}

document.querySelectorAll("#labelRecruiter button").forEach((b) =>
  b.addEventListener("click", () => setRecruiter(b.dataset.rec === "yes"))
);
document.querySelectorAll("#labelIntent button").forEach((b) =>
  b.addEventListener("click", () => setIntent(b.dataset.intent))
);
$("labelSaveBtn").addEventListener("click", saveLabel);
$("labelSkipBtn").addEventListener("click", skipLabel);

document.addEventListener("keydown", (e) => {
  if ($("tab-label").hidden) return;
  // Never hijack a key the person is typing into a field.
  const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);

  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    saveLabel();
    return;
  }
  if (typing) return;

  if (e.key === "y") setRecruiter(true);
  else if (e.key === "n") setRecruiter(false);
  else if (e.key === "s") skipLabel();
  else if (INTENT_KEYS[e.key] && IS_RECRUITER) setIntent(INTENT_KEYS[e.key]);
});

window.loadNextLabel = loadNextLabel;
