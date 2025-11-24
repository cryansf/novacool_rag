function initNovacoolChatWidget({ containerId }) {
  const container = document.getElementById(containerId);

  const frame = document.createElement("iframe");
  frame.src = "https://novacool-rag.onrender.com/chat";
  frame.style.cssText = `
    width: 100%;
    height: 100%;
    border: none;
    background: transparent;
  `;

  container.appendChild(frame);

  // Auto-scroll to latest answer
  window.addEventListener("message", (e) => {
    if (e.data?.action === "scroll") {
      frame.contentWindow.postMessage({ action: "scroll" }, "*");
    }
  });

  // Forward typed question → backend
  window.addEventListener("message", async (e) => {
    if (e.data?.action === "ask") {
      const question = e.data.question;

      const response = await fetch("https://novacool-rag.onrender.com/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });

      const result = await response.json();
      frame.contentWindow.postMessage(
        { action: "response", answer: result.answer },
        "*"
      );
    }
  });
}
