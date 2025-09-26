(function () {
  const form = document.getElementById("agent-form");
  const triggerField = document.getElementById("trigger-field");
  const consoleEl = document.getElementById("console");
  const outputEl = document.getElementById("final-output");
  const artifactsEl = document.getElementById("artifacts");

  let currentStream = null;

  function resetPanels() {
    consoleEl.textContent = "";
    outputEl.textContent = "";
    artifactsEl.innerHTML = "";
  }

  function appendConsole(text) {
    consoleEl.textContent += text;
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function appendToolEvent(prefix, payload) {
    const block = document.createElement("div");
    block.className = "tool-event";
    block.innerHTML = `<strong>${prefix}</strong><pre>${JSON.stringify(payload, null, 2)}</pre>`;
    consoleEl.appendChild(block);
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function appendArtifacts(paths) {
    artifactsEl.innerHTML = "";
    paths.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      artifactsEl.appendChild(li);
    });
  }

  function openStream(runId) {
    if (currentStream) {
      currentStream.close();
    }
    const url = `/stream/${runId}`;
    const source = new EventSource(url);
    currentStream = source;

    source.addEventListener("token", (event) => {
      const data = JSON.parse(event.data);
      appendConsole(data.text || "");
    });

    source.addEventListener("tool_start", (event) => {
      const data = JSON.parse(event.data);
      appendToolEvent("➡️ Tool start", data);
    });

    source.addEventListener("tool_end", (event) => {
      const data = JSON.parse(event.data);
      appendToolEvent("✅ Tool end", data);
    });

    source.addEventListener("final", (event) => {
      const data = JSON.parse(event.data);
      outputEl.textContent = data.text || "";
      if (Array.isArray(data.artifacts)) {
        appendArtifacts(data.artifacts);
      }
      source.close();
    });

    source.addEventListener("error", (event) => {
      try {
        const data = JSON.parse(event.data);
        appendToolEvent("❌ Error", data);
      } catch (err) {
        appendConsole("\n[error]\n");
      }
      source.close();
    });
  }

  if (form) {
    form.addEventListener("click", (event) => {
      const target = event.target;
      if (target.matches("button[data-trigger]")) {
        triggerField.value = target.dataset.trigger;
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!triggerField.value) {
        return;
      }
      resetPanels();
      const formData = new FormData(form);
      try {
        const response = await fetch("/run", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          const message = await response.text();
          appendToolEvent("❌ Error", { message });
          return;
        }
        const payload = await response.json();
        if (payload.run_id) {
          openStream(payload.run_id);
        }
      } catch (error) {
        appendToolEvent("❌ Error", { message: error.message });
      }
    });
  }
})();
