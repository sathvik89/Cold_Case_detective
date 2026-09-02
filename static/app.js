const evidenceList = document.getElementById("evidence");
const countBadge = document.getElementById("count");
const addLabel = document.getElementById("add");
const fileInput = document.getElementById("file");
const thread = document.getElementById("thread");
const empty = document.getElementById("empty");
const form = document.getElementById("composer");
const input = document.getElementById("question");
const send = document.getElementById("send");

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// ---------- evidence ----------

function renderEvidence(files) {
  evidenceList.textContent = "";
  countBadge.textContent = files.length;

  if (!files.length) {
    evidenceList.appendChild(
      el("div", "no-files", "No evidence yet. Add a .txt file to open the case.")
    );
    return;
  }

  files.forEach((f) => {
    const card = el("div", "file");
    card.appendChild(el("div", "file-name", f.name));
    card.appendChild(el("div", "file-meta", `${f.words} words`));
    if (f.preview) card.appendChild(el("div", "file-preview", f.preview));

    const del = el("button", "file-del", "×");
    del.type = "button";
    del.title = `Remove ${f.name}`;
    del.setAttribute("aria-label", `Remove ${f.name}`);
    del.addEventListener("click", async () => {
      if (!confirm(`Remove ${f.name} from the case file?`)) return;
      try {
        const data = await (
          await fetch(`/api/evidence/${encodeURIComponent(f.name)}`, { method: "DELETE" })
        ).json();
        if (data.ok) renderEvidence(data.files);
        else notice(data.error, true);
      } catch {
        notice("Could not reach the server.", true);
      }
    });
    card.appendChild(del);

    evidenceList.appendChild(card);
  });
}

function loadEvidence() {
  fetch("/api/evidence")
    .then((r) => r.json())
    .then((d) => renderEvidence(d.files || []))
    .catch(() => notice("Could not reach the server.", true));
}

async function upload(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".txt")) {
    notice("Evidence files have to be .txt", true);
    return;
  }

  addLabel.classList.add("busy");
  const body = new FormData();
  body.append("file", file);

  let data;
  try {
    data = await (await fetch("/api/evidence", { method: "POST", body })).json();
  } catch {
    data = { ok: false, error: "Could not reach the server." };
  }

  addLabel.classList.remove("busy");
  if (data.ok) renderEvidence(data.files);
  else notice(data.error || "Upload failed.", true);
}

fileInput.addEventListener("change", () => {
  upload(fileInput.files[0]);
  fileInput.value = "";
});

["dragenter", "dragover"].forEach((evt) =>
  addLabel.addEventListener(evt, (e) => {
    e.preventDefault();
    addLabel.classList.add("over");
  })
);

["dragleave", "drop"].forEach((evt) =>
  addLabel.addEventListener(evt, (e) => {
    e.preventDefault();
    addLabel.classList.remove("over");
  })
);

addLabel.addEventListener("drop", (e) => {
  upload(e.dataTransfer.files && e.dataTransfer.files[0]);
});

["dragover", "drop"].forEach((evt) =>
  window.addEventListener(evt, (e) => e.preventDefault())
);

// ---------- asking ----------

function clearEmpty() {
  if (empty && empty.parentNode) empty.remove();
}

function notice(text, isError) {
  clearEmpty();
  const turn = el("div", "turn");
  turn.appendChild(el("div", isError ? "err" : "report-body", text));
  thread.appendChild(turn);
  thread.scrollTop = thread.scrollHeight;
}

function autosize() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 150) + "px";
}
input.addEventListener("input", autosize);

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    input.value = chip.textContent.trim();
    autosize();
    form.requestSubmit();
  });
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question || send.disabled) return;

  clearEmpty();

  const turn = el("div", "turn");
  const asked = el("div", "asked");
  asked.appendChild(el("div", "who", "?"));
  asked.appendChild(el("div", "text", question));
  turn.appendChild(asked);

  const thinking = el("div", "thinking");
  thinking.appendChild(el("span", "pulse"));
  // first question also has to embed everything, which is the slow one
  thinking.appendChild(el("span", null, "Reviewing the evidence…"));
  turn.appendChild(thinking);

  thread.appendChild(turn);
  thread.scrollTop = thread.scrollHeight;

  input.value = "";
  autosize();
  send.disabled = true;
  send.classList.add("busy");

  let data;
  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, ...Settings.creds() }),
    });
    data = await res.json();
  } catch {
    data = { ok: false, error: "Could not reach the server. Is uvicorn still running?" };
  }

  thinking.remove();

  if (!data.ok) {
    turn.appendChild(el("div", "err", data.error || "Something went wrong."));
  } else {
    const report = el("div", "report");
    report.appendChild(
      el("div", "report-head", data.model ? `Investigative report · ${data.model}` : "Investigative report")
    );
    report.appendChild(el("div", "report-body", data.report));
    turn.appendChild(report);

    if (data.sources && data.sources.length) {
      const details = el("details", "sources");
      details.appendChild(
        el("summary", null, `Cited evidence · ${data.sources.length}`)
      );
      const body = el("div", "sources-body");
      data.sources.forEach((s) => {
        const src = el("div", "src");
        const top = el("div", "src-top");
        top.appendChild(el("span", "src-name", s.source));
        top.appendChild(el("span", "src-score", `${(s.score * 100).toFixed(1)}% match`));
        src.appendChild(top);
        src.appendChild(el("div", "src-text", s.content));
        body.appendChild(src);
      });
      details.appendChild(body);
      turn.appendChild(details);
    }
  }

  send.disabled = false;
  send.classList.remove("busy");
  thread.scrollTop = thread.scrollHeight;
  input.focus();
});

Settings.init(document.getElementById("settings"), (ready) => {
  send.disabled = !ready;
  input.placeholder = ready
    ? "Put a question to the case file…"
    : "Add an API key in Settings to begin";
});

loadEvidence();
input.focus();
