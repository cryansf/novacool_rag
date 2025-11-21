/* ==========================================================
   NOVACOOL — CHAT UI (WORKS WITH /chat JSON API)
========================================================== */

(function () {
  const panel = document.createElement("div");
  panel.id = "novacool-chat-panel";
  panel.innerHTML = `
      <span id="novacool-close">✖</span>
      <iframe id="novacool-frame"></iframe>
  `;
  document.body.appendChild(panel);

  const iframe = document.getElementById("novacool-frame").contentWindow;
  const bubble = document.getElementById("novacool-bubble");
  const closeBtn = document.getElementById("novacool-close");

  /* Load chat UI page into iframe */
  document.getElementById("novacool-frame").src =
    "https://novacool-rag.onrender.com/static/chat.html";

  /* Open chat on bubble click */
  bubble.addEventListener("click", () => {
    panel.classList.add("open");
  });

  /* Close button */
  closeBtn.addEventListener("click", () => {
    panel.classList.remove("open");
  });

  /* Listen for messages FROM iframe (user pressed Send) */
  window.addEventListener("message", async (e) => {
    if (!e.data || !e.data.type || e.data.type !== "question") return;
    const question = e.data.text;

    try {
      const res = await fetch("https://novacool-rag.onrender.com/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });

      const data = await res.json();
      const answer = data.answer || "⚠️ No response from backend.";

      iframe.postMessage({ type: "answer", text: answer }, "*");
    } catch (err) {
      iframe.postMessage(
        {
          type: "answer",
          text: "⚠️ Error: Unable to contact server."
        },
        "*"
      );
    }
  });
})();
