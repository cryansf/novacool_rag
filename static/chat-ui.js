// chat-ui.js
// Handles chat behavior inside /static/chat.html iframe

(function () {
  const messagesEl = document.getElementById("nc-messages");
  const inputEl = document.getElementById("nc-user-input");
  const sendBtn = document.getElementById("nc-send-btn");
  const reindexBtn = document.getElementById("nc-reindex-btn");
  const footerStatusEl = document.getElementById("nc-footer-status");

  const API_BASE = window.location.origin;
  const CHAT_ENDPOINT = API_BASE + "/chat";
  const REINDEX_ENDPOINT = API_BASE + "/reindex";

  let isSending = false;

  // ---------------
  // Helpers
  // ---------------
  function scrollToBottom() {
    if (!messagesEl) return;
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function createMessageBubble(role, text) {
    const wrapper = document.createElement("div");
    wrapper.className = "nc-msg-row nc-msg-row-" + role;

    const bubble = document.createElement("div");
    bubble.className = "nc-msg nc-msg-" + role;
    bubble.textContent = text;

    wrapper.appendChild(bubble);
    return wrapper;
  }

  function appendMessage(role, text) {
    if (!messagesEl) return;
    const node = createMessageBubble(role, text);
    messagesEl.appendChild(node);
    scrollToBottom();
    return node;
  }

  function setFooterStatus(text) {
    if (footerStatusEl) {
      footerStatusEl.textContent = text;
    }
  }

  // ---------------
  // Initial greeting
  // ---------------
  function showWelcome() {
    appendMessage(
      "assistant",
      "Hi, I’m the Novacool AI Assistant. You can ask me about Novacool UEF, " +
        "foam application rates, compatibility, fire scenarios, training guidance, and more."
    );
  }

  // ---------------
  // Send message
  // ---------------
  async function sendMessage() {
    if (isSending) return;

    const raw = (inputEl.value || "").trim();
    if (!raw) return;

    isSending = true;
    inputEl.value = "";
    inputEl.style.height = "auto";

    // Show user message
    appendMessage("user", raw);

    // Show "thinking" bubble
    const thinkingNode = appendMessage("assistant", "Novacool AI is thinking...");

    try {
      const res = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: raw }),
      });

      if (!res.ok) {
        throw new Error("HTTP " + res.status);
      }

      const data = await res.json();

      const reply = (data && data.reply) || "⚠️ No reply received.";
      thinkingNode.querySelector(".nc-msg").textContent = reply;
      scrollToBottom();
    } catch (err) {
      console.error("Chat error:", err);
      thinkingNode.querySelector(".nc-msg").textContent =
        "⚠️ Sorry, I had trouble reaching the Novacool AI backend. Please try again.";
      scrollToBottom();
    } finally {
      isSending = false;
    }
  }

  // ---------------
  // Reindex from inside chat
  // ---------------
  async function triggerReindex() {
    if (!confirm("Reindex all uploaded files now? This may take a moment.")) {
      return;
    }

    setFooterStatus("🔄 Reindexing knowledge base...");
    const statusNode = appendMessage(
      "assistant",
      "Starting reindex of all uploaded Novacool documents. I’ll let you know when it’s done."
    );

    try {
      const res = await fetch(REINDEX_ENDPOINT, {
        method: "POST",
      });

      if (!res.ok) {
        throw new Error("HTTP " + res.status);
      }

      const data = await res.json();
      const summary =
        (data && data.summary) ||
        "Reindex completed, but no summary message was returned.";

      statusNode.querySelector(".nc-msg").textContent =
        "✅ Reindex complete: " + summary;
      setFooterStatus("✅ Knowledge base updated. New files are now searchable.");
      scrollToBottom();
    } catch (err) {
      console.error("Reindex error:", err);
      statusNode.querySelector(".nc-msg").textContent =
        "⚠️ Reindex failed. Please check the uploader page or logs.";
      setFooterStatus("⚠️ Reindex failed. See logs for details.");
      scrollToBottom();
    }
  }

  // ---------------
  // Event bindings
  // ---------------
  if (sendBtn) {
    sendBtn.addEventListener("click", sendMessage);
  }

  if (inputEl) {
    inputEl.addEventListener("keydown", function (e) {
      // Enter to send, Shift+Enter for newline
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-resize textarea
    inputEl.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = this.scrollHeight + "px";
    });
  }

  if (reindexBtn) {
    reindexBtn.addEventListener("click", triggerReindex);
  }

  // ---------------
  // Init
  // ---------------
  document.addEventListener("DOMContentLoaded", showWelcome);
})();
