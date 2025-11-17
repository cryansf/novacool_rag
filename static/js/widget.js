(function () {
  if (window.NovacoolWidgetLoaded) return;
  window.NovacoolWidgetLoaded = true;

  const BACKEND_ORIGIN = "https://novacool-rag.onrender.com";
  const CHAT_URL = BACKEND_ORIGIN + "/chat";

  function createBubble() {
    const bubble = document.createElement("div");
    bubble.id = "novacool-bubble";
    bubble.textContent = "Ask Novacool AI 🔥";
    bubble.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 9999999;
      background: linear-gradient(135deg,#0051ff,#ff3b3b);
      color: #ffffff;
      padding: 12px 18px;
      border-radius: 999px;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      font-weight: 700;
      box-shadow: 0 8px 24px rgba(0,0,0,0.35);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
    `;
    return bubble;
  }

  function createFrame() {
    const frame = document.createElement("iframe");
    frame.id = "novacool-chat-frame";
    frame.src = CHAT_URL;
    frame.style.cssText = `
      position: fixed;
      bottom: 70px;
      right: 20px;
      width: 420px;
      max-width: 96vw;
      height: 540px;
      border: none;
      border-radius: 18px;
      box-shadow: 0 18px 40px rgba(0,0,0,0.45);
      z-index: 9999998;
      display: none;
      overflow: hidden;
    `;
    return frame;
  }

  function init() {
    const bubble = createBubble();
    const frame = createFrame();

    document.body.appendChild(frame);
    document.body.appendChild(bubble);

    bubble.addEventListener("click", () => {
      frame.style.display = "block";
      bubble.style.display = "none";
    });

    // Optional: ESC key to close iframe and show bubble again
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        frame.style.display = "none";
        bubble.style.display = "flex";
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
