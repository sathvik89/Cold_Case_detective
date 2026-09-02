/*
  Provider settings, shared by all three tools.

  The key is kept in localStorage on this machine and sent with each request.
  It is never written to disk on the server, and the server falls back to the
  environment when no key is sent.
*/

const Settings = (() => {
  const STORE = "ai-provider-settings";

  let state = { provider: null, model: "", keys: {} };
  let providers = [];
  let onChange = () => {};

  function load() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE) || "{}");
      state = {
        provider: saved.provider || null,
        model: saved.model || "",
        keys: saved.keys || {},
      };
    } catch {
      /* corrupt or blocked storage - carry on with defaults */
    }
  }

  function save() {
    try {
      localStorage.setItem(STORE, JSON.stringify(state));
    } catch {
      /* private browsing - settings just will not persist */
    }
  }

  // what every request sends
  function creds() {
    return {
      provider: state.provider,
      api_key: state.keys[state.provider] || "",
      model: state.model,
    };
  }

  function spec(id) {
    return providers.find((p) => p.id === id);
  }

  function ready() {
    const p = spec(state.provider);
    if (!p) return false;
    return Boolean(state.keys[state.provider] || p.has_env_key);
  }

  // ---------- markup ----------

  function build(root) {
    root.innerHTML = `
      <button class="set-btn" id="setBtn" type="button" aria-haspopup="dialog">
        <span class="set-dot" id="setDot"></span>
        <span id="setLabel">Settings</span>
      </button>
      <div class="set-panel" id="setPanel" role="dialog" aria-label="Provider settings" hidden>
        <div class="set-row">
          <label for="setProvider">Provider</label>
          <select id="setProvider"></select>
        </div>
        <div class="set-row">
          <label for="setKey">API key</label>
          <div class="set-key">
            <input id="setKey" type="password" placeholder="Paste your key" autocomplete="off" spellcheck="false" />
            <button class="set-eye" id="setEye" type="button" aria-label="Show key">show</button>
          </div>
          <p class="set-hint" id="setHint"></p>
        </div>
        <div class="set-row">
          <label for="setModel">Model</label>
          <div class="set-model">
            <input id="setModel" list="setModelList" placeholder="Default" autocomplete="off" spellcheck="false" />
            <datalist id="setModelList"></datalist>
            <button class="set-load" id="setLoad" type="button">Load</button>
          </div>
          <p class="set-hint" id="setModelHint"></p>
        </div>
        <div class="set-actions">
          <button class="set-save" id="setSave" type="button">Save</button>
        </div>
      </div>`;

    const btn = root.querySelector("#setBtn");
    const panel = root.querySelector("#setPanel");
    const providerSel = root.querySelector("#setProvider");
    const keyInput = root.querySelector("#setKey");
    const eye = root.querySelector("#setEye");
    const hint = root.querySelector("#setHint");
    const modelInput = root.querySelector("#setModel");
    const modelList = root.querySelector("#setModelList");
    const modelHint = root.querySelector("#setModelHint");
    const loadBtn = root.querySelector("#setLoad");
    const saveBtn = root.querySelector("#setSave");
    const dot = root.querySelector("#setDot");
    const label = root.querySelector("#setLabel");

    function paintBadge() {
      const p = spec(state.provider);
      label.textContent = p ? p.label : "Settings";
      dot.classList.toggle("ok", ready());
      btn.title = ready()
        ? `${p.label}${state.model ? " · " + state.model : ""}`
        : "No API key set";
    }

    function paintHint() {
      const p = spec(state.provider);
      if (!p) return;
      const hasTyped = Boolean(state.keys[state.provider]);
      if (hasTyped) hint.textContent = "Saved in this browser.";
      else if (p.has_env_key) hint.textContent = "Using the key from .env. Paste one to override it.";
      else hint.textContent = "";
      hint.innerHTML =
        hint.textContent +
        ` <a href="${p.console}" target="_blank" rel="noopener">Get a key</a>`;
    }

    function selectProvider(id) {
      state.provider = id;
      const p = spec(id);
      keyInput.value = state.keys[id] || "";
      modelInput.value = "";
      modelInput.placeholder = p ? p.default_model : "Default";
      modelList.innerHTML = "";
      modelHint.textContent = "";
      paintHint();
      paintBadge();
    }

    providerSel.addEventListener("change", () => selectProvider(providerSel.value));

    eye.addEventListener("click", () => {
      const showing = keyInput.type === "text";
      keyInput.type = showing ? "password" : "text";
      eye.textContent = showing ? "show" : "hide";
    });

    // ask the provider which models the key can actually use
    loadBtn.addEventListener("click", async () => {
      loadBtn.disabled = true;
      loadBtn.textContent = "…";
      modelHint.textContent = "";
      try {
        const res = await fetch("/api/models", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            provider: providerSel.value,
            api_key: keyInput.value.trim(),
          }),
        });
        const data = await res.json();
        if (data.ok) {
          modelList.innerHTML = "";
          data.models.forEach((m) => {
            const opt = document.createElement("option");
            opt.value = m;
            modelList.appendChild(opt);
          });
          modelHint.textContent = `${data.models.length} models available - click the box to pick one.`;
        } else {
          modelHint.textContent = data.error;
        }
      } catch {
        modelHint.textContent = "Could not reach the server.";
      }
      loadBtn.disabled = false;
      loadBtn.textContent = "Load";
    });

    saveBtn.addEventListener("click", () => {
      state.provider = providerSel.value;
      const typed = keyInput.value.trim();
      if (typed) state.keys[state.provider] = typed;
      else delete state.keys[state.provider];
      state.model = modelInput.value.trim();
      save();
      paintHint();
      paintBadge();
      panel.hidden = true;
      onChange(ready());
    });

    btn.addEventListener("click", () => {
      panel.hidden = !panel.hidden;
      if (!panel.hidden) keyInput.focus();
    });

    // click outside or Escape closes it
    document.addEventListener("click", (e) => {
      if (!panel.hidden && !root.contains(e.target)) panel.hidden = true;
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") panel.hidden = true;
    });

    return { providerSel, modelInput, keyInput, paintBadge, selectProvider, panel };
  }

  async function init(root, changed) {
    onChange = changed || onChange;
    load();

    let data;
    try {
      data = await (await fetch("/api/providers")).json();
    } catch {
      return;
    }
    providers = data.providers || [];

    const ui = build(root);

    providers.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.label + (p.has_env_key ? " (key in .env)" : "");
      ui.providerSel.appendChild(opt);
    });

    // prefer what was saved, else a provider that already has a key, else the default
    const withKey = providers.find((p) => state.keys[p.id] || p.has_env_key);
    const chosen =
      (state.provider && spec(state.provider) && state.provider) ||
      (withKey && withKey.id) ||
      data.default;

    ui.providerSel.value = chosen;
    const savedModel = state.model;
    ui.selectProvider(chosen);
    state.model = savedModel;
    ui.modelInput.value = savedModel;
    ui.paintBadge();

    // no key anywhere yet - open the panel so it is obvious what to do
    if (!ready()) ui.panel.hidden = false;

    onChange(ready());
  }

  return { init, creds, ready, open: () => document.getElementById("setPanel") };
})();
