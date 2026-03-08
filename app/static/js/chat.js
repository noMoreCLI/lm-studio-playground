(function () {
  const historyEl = document.getElementById("history");
  const tokenUsageEl = document.getElementById("token-usage");
  const rawRequestEl = document.getElementById("raw-request");
  const rawResponseEl = document.getElementById("raw-response");
  const connectionStatusEl = document.getElementById("connection-status");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const newChatBtn = document.getElementById("new-chat-btn");

  let messages = [];

  function resetChat() {
    messages = [];
    renderHistory();
    setTokenUsage(null);
    setRaw(null, null);
  }

  function renderHistory() {
    if (!messages.length) {
      historyEl.innerHTML = "<p class=\"empty\">No messages yet. Send a message below.</p>";
      setTokenUsageFromMessages();
      return;
    }
    historyEl.innerHTML = messages
      .filter(function (m) {
        return m.role !== "system";
      })
      .map(function (m) {
        const role = m.role === "user" ? "You" : "Assistant";
        const cls = m.role === "user" ? "user" : "assistant";
        let html = "<div class=\"message " + cls + "\"><strong>" + escapeHtml(role) + "</strong>: " + escapeHtml(m.content);
        if (m.role === "assistant" && m.usage) {
          const u = m.usage;
          const p = u.prompt_tokens || 0;
          const c = u.completion_tokens || 0;
          const t = u.total_tokens !== undefined ? u.total_tokens : p + c;
          html += "<div class=\"message-usage small text-muted mt-1\">Tokens this turn: prompt " + p + ", completion " + c + ", total " + t + "</div>";
        }
        html += "</div>";
        return html;
      })
      .join("");
    historyEl.scrollTop = historyEl.scrollHeight;
    setTokenUsageFromMessages();
  }

  function setTokenUsageFromMessages() {
    let totalPrompt = 0;
    let totalCompletion = 0;
    messages.forEach(function (m) {
      if (m.role === "assistant" && m.usage) {
        totalPrompt += m.usage.prompt_tokens || 0;
        totalCompletion += m.usage.completion_tokens || 0;
      }
    });
    if (totalPrompt === 0 && totalCompletion === 0) {
      setTokenUsage(null);
      return;
    }
    setTokenUsage({
      prompt_tokens: totalPrompt,
      completion_tokens: totalCompletion,
      total_tokens: totalPrompt + totalCompletion,
    });
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function setTokenUsage(usage) {
    if (!usage || (usage.prompt_tokens === undefined && usage.completion_tokens === undefined)) {
      tokenUsageEl.textContent = "";
      return;
    }
    const p = usage.prompt_tokens || 0;
    const c = usage.completion_tokens || 0;
    const t = usage.total_tokens !== undefined ? usage.total_tokens : p + c;
    tokenUsageEl.textContent = "Prompt: " + p + ", Completion: " + c + ", Total: " + t;
  }

  function setRaw(requestObj, responseObj) {
    rawRequestEl.textContent = requestObj ? JSON.stringify(requestObj, null, 2) : "";
    rawResponseEl.textContent = responseObj ? JSON.stringify(responseObj, null, 2) : "";
  }

  function setConnectionStatus(connected, text, error) {
    connectionStatusEl.classList.toggle("connected", !!connected);
    connectionStatusEl.classList.toggle("disconnected", !connected);
    connectionStatusEl.textContent = text || (connected ? "Connected" : "Disconnected");
    if (error) {
      connectionStatusEl.title = error;
    }
  }

  function fetchStatus() {
    fetch("/api/status")
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data.connected) {
          setConnectionStatus(true, "LM Studio @ " + (data.base_url || "") + " – model: " + (data.model || "—"));
        } else {
          setConnectionStatus(false, "Disconnected – " + (data.error || "Unknown error"), data.error);
        }
      })
      .catch(function (err) {
        setConnectionStatus(false, "Disconnected – " + err.message, err.message);
      });
  }

  function sendMessage() {
    const text = (userInput.value || "").trim();
    if (!text) return;
    const userMsg = { role: "user", content: text };
    messages.push(userMsg);
    userInput.value = "";
    renderHistory();
    sendBtn.disabled = true;

    fetch("/api/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: messages.slice(0, -1), message: text }),
    })
      .then(function (r) {
        return r.json()
          .then(function (data) {
            if (!r.ok) {
              data = data || {};
              data.error = data.error || "Request failed (" + r.status + ")";
            }
            return data;
          })
          .catch(function () {
            return { error: "Request failed (" + r.status + ")" };
          });
      })
      .then(function (data) {
        if (data.error) {
          messages.push({ role: "assistant", content: "Error: " + data.error });
        } else {
          messages.push({
            role: "assistant",
            content: data.content || "",
            usage: data.usage || null,
          });
        }
        renderHistory();
        setRaw(data.raw_request, data.raw_response);
      })
      .catch(function (err) {
        messages.push({ role: "assistant", content: "Request failed: " + err.message });
        renderHistory();
        setTokenUsage(null);
        setRaw(null, null);
      })
      .finally(function () {
        sendBtn.disabled = false;
      });
  }

  newChatBtn.addEventListener("click", resetChat);
  sendBtn.addEventListener("click", sendMessage);
  userInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  fetchStatus();
  renderHistory();
})();
