// widget-loader.js
// Injects a glowing bubble + overlay that loads /static/chat.html in an iframe.
// Hybrid behavior: popup on desktop, full-screen on mobile.

(function () {
  const HOST = "https://novacool-rag.onrender.com";
  const CSS_URL = HOST + "/static/widget.css";
  const CHAT_URL = HOST + "/static/chat.html";

  function injectCssOnce() {
    if (document.querySelector('link[data-novacool-widget="true"]')) {
      return;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = CSS_URL;
    link.setAttribute("data-novacool-widget", "true");
    document.head.appendChild(link);
  }

  function createBubble() {
    if (document.getElementById("nc-chat-bubble")) return;

    const bubble = document.createElement("div");
    bubble.id = "nc-chat-bubble";
    bubble.className = "nc-chat-bubble";

    bubble.innerHTML = `
      <div class="nc-chat-bubble-glow"></div>
      <div class="nc-chat-bubble-core">
        <span class="nc-chat-bubble-logo">🔥</span>
      </div>
    `;

    bubble.addEventListener("click", function () {
      toggleOverlay(true);
    });

    document.body.appendChild(bubble);
  }

  function createOverlay() {
    if (document.getElementById("nc-chat-overlay")) return;

    const overlay = document.createElement("div");
    overlay.id = "nc-chat-overlay";
    overlay.className = "nc-chat-overlay nc-hidden";

    overlay.innerHTML = `
      <div class="nc-chat-window">
        <div class="nc-overlay-header">
          <div class="nc-overlay-title">
            <span class="nc-overlay-logo">🔥</span>
            <span class="nc-overlay-text">
              Novacool AI Assistant
            </span>
          </div>
          <button type="button" class="nc-overlay-close" aria-label="Close chat">
            ×
          </button>
        </div>
        <div class="nc-overlay-body">
          <iframe
            id="nc-chat-iframe"
            src="${CHAT_URL}"
            class="nc-chat-iframe"
            title="Novacool AI Chat"
          ></iframe>
        </div>
      </div>
    `;

    const closeBtn = overlay.querySelector(".nc-overlay-close");
    closeBtn.addEventListener("click", function () {
      toggleOverlay(false);
    });

    overlay.addEventListener("click", function (e) {
      // Click outside the chat window closes overlay
      if (e.target === overlay) {
        toggleOverlay(false);
      }
    });

    document.body.appendChild(overlay);
  }

  function toggleOverlay(show) {
    const overlay = document.getElementById("nc-chat-overlay");
    if (!overlay) return;
    if (show) {
      overlay.classList.remove("nc-hidden");
    } else {
      overlay.classList.add("nc-hidden");
    }
  }

  function init() {
    injectCssOnce();
    createOverlay();
    createBubble();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
