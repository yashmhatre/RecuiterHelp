"use strict";
// Gmail tab. Loaded after app.js, so $ , esc and render() are already defined.

async function refreshGmail() {
  let data;
  try {
    data = await (await fetch("/api/gmail/status")).json();
  } catch {
    return;
  }

  const box = $("gmailStatus");
  box.className = "verdict " + (data.connected ? "drafted" : "review");
  box.innerHTML = data.connected
    ? `Connected to ${esc(data.address)}<small>Read, draft and label only &mdash; no send scope.</small>`
    : `Not connected<small>${esc(data.detail || "")}</small>`;

  $("fetchBtn").disabled = !data.connected;
  $("disconnectBtn").style.display = data.connected ? "inline-block" : "none";
  if (data.has_client_secret) {
    $("credLabel").textContent = "OAuth client JSON uploaded";
    $("credDrop").classList.add("has-file");
  }
  const setup = $("gmailSetup");
  if (setup) setup.open = !data.has_client_secret;
}

$("credDrop").addEventListener("click", () => $("credInput").click());

$("credInput").addEventListener("change", async () => {
  const file = $("credInput").files[0];
  if (!file) return;
  const notice = $("gmailNotice");
  const body = new FormData();
  body.append("credentials", file);
  try {
    const res = await fetch("/api/gmail/client-secret", { method: "POST", body });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "upload failed");
    notice.className = "notice ok";
    notice.textContent = `Saved OAuth client ${data.client_id}. Now click Connect Gmail.`;
    await refreshGmail();
  } catch (err) {
    notice.className = "notice err";
    notice.textContent = err.message;
  }
});

$("connectBtn").addEventListener("click", async () => {
  const btn = $("connectBtn");
  const notice = $("gmailNotice");
  btn.disabled = true;
  btn.textContent = "Opening Google…";

  try {
    const res = await fetch("/api/gmail/auth-url");
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "could not start sign-in");

    // Opened from a click, so the popup blocker allows it, and Google redirects back into
    // this app rather than into a throwaway local server.
    const tab = window.open(data.url, "_blank");
    notice.className = "notice ok";
    notice.innerHTML = tab
      ? `Approve access in the Google tab. You will see
         <b>&ldquo;Google hasn&rsquo;t verified this app&rdquo;</b> &mdash; expected for your own
         project. Click <b>Advanced</b>, then <b>Go to (your app)</b>.
         This page updates by itself once you are done.`
      : `Your browser blocked the popup.
         <a href="${data.url}" target="_blank" rel="noopener">Open the Google sign-in here</a>.`;

    btn.textContent = "Waiting for Google…";
    await waitForConnection();
  } catch (err) {
    notice.className = "notice err";
    notice.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Connect Gmail";
  }
});

async function waitForConnection(timeoutMs = 180000) {
  // Poll rather than block a request: the sign-in happens in another tab and may take a
  // minute, or be abandoned entirely.
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 2000));
    try {
      const data = await (await fetch("/api/gmail/status")).json();
      if (data.connected) {
        await refreshGmail();
        const notice = $("gmailNotice");
        notice.className = "notice ok";
        notice.textContent = `Connected to ${data.address}. Now click Fetch messages.`;
        return true;
      }
    } catch {
      /* server restarting or offline; keep waiting */
    }
  }
  const notice = $("gmailNotice");
  notice.className = "notice err";
  notice.textContent =
    "Gave up waiting for Google. If you finished signing in, click Connect Gmail again.";
  return false;
}

$("disconnectBtn").addEventListener("click", async () => {
  await fetch("/api/gmail/disconnect", { method: "POST" });
  $("gmailList").innerHTML = '<div class="empty">Disconnected.</div>';
  $("gmailResult").innerHTML = "";
  await refreshGmail();
});

$("fetchBtn").addEventListener("click", async () => {
  const btn = $("fetchBtn");
  const notice = $("gmailNotice");
  btn.disabled = true;
  btn.textContent = "Fetching…";
  try {
    const params = new URLSearchParams({
      limit: $("gmailLimit").value || "15",
      query: $("gmailQuery").value || "in:inbox",
    });
    const res = await fetch("/api/gmail/messages?" + params);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "fetch failed");
    renderMailbox(data.messages);
    notice.className = "notice ok";
    notice.textContent = `Fetched ${data.messages.length} message(s).`;
  } catch (err) {
    notice.className = "notice err";
    notice.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Fetch messages";
  }
});

function renderMailbox(messages) {
  const host = $("gmailList");
  if (!messages.length) {
    host.innerHTML = '<div class="empty">No messages matched that query.</div>';
    return;
  }

  host.innerHTML = messages
    .map((m) => {
      // The two free stages already ran server-side, so the list says what would happen next
      // without having spent a model call.
      let verdict;
      if (!m.prefilter_keep) verdict = `dropped by pre-filter: ${m.prefilter_rule}`;
      else if (m.auth !== "pass") verdict = `auth ${m.auth.toUpperCase()}`;
      else verdict = "would reach the model";

      const flags = (m.auth_flags || []).length
        ? ` <span class="chip" style="color:var(--warn)">${m.auth_flags.map(esc).join(", ")}</span>`
        : "";

      return `<div class="profile">
        <div class="top">
          <span class="nm">${esc(m.from_name || m.from_email)}</span>
          <span style="color:var(--muted);font-size:12px">${esc(m.from_email)}</span>
        </div>
        <div style="font-size:13.5px;margin-top:2px">${esc(m.subject || "(no subject)")}</div>
        <div class="meta">${esc(m.snippet)}</div>
        <div class="chips"><span class="chip">${esc(verdict)}</span>${flags}</div>
        <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
          <button class="ghost" data-run="${esc(m.id)}">Classify</button>
          <button class="ghost" data-save="${esc(m.id)}">Classify + save draft in Gmail</button>
        </div>
      </div>`;
    })
    .join("");

  host.querySelectorAll("[data-run]").forEach((b) =>
    b.addEventListener("click", () => runGmail(b.dataset.run, "no", b))
  );
  host.querySelectorAll("[data-save]").forEach((b) =>
    b.addEventListener("click", () => runGmail(b.dataset.save, "yes", b))
  );
}

async function runGmail(messageId, save, button) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Running…";
  try {
    const body = new FormData();
    body.append("message_id", messageId);
    body.append("save", save);
    const res = await fetch("/api/gmail/run", { method: "POST", body });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "run failed");

    // render() writes into #resultPane, so hand it this pane for the duration.
    const inboxPane = $("resultPane");
    inboxPane.id = "resultPane_inbox";
    const target = $("gmailResult");
    target.innerHTML = "";
    const swap = document.createElement("div");
    swap.id = "resultPane";
    target.appendChild(swap);
    render(data);
    swap.removeAttribute("id");
    inboxPane.id = "resultPane";

    if (data.gmail && data.gmail.draft_id) {
      target.insertAdjacentHTML(
        "afterbegin",
        `<div class="card"><div class="verdict drafted">Draft saved in Gmail
          <small>Open the thread in Gmail to review and send it yourself. Labelled
          &ldquo;AI Draft&rdquo;.</small></div></div>`
      );
    } else if (data.gmail && data.gmail.labelled) {
      target.insertAdjacentHTML(
        "afterbegin",
        `<div class="card"><div class="verdict review">No draft &mdash; labelled
          &ldquo;${esc(data.gmail.labelled)}&rdquo; in Gmail</div></div>`
      );
    }
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    const notice = $("gmailNotice");
    notice.className = "notice err";
    notice.textContent = err.message;
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

// app.js calls this when the Gmail tab is opened.
window.refreshGmail = refreshGmail;
refreshGmail();
