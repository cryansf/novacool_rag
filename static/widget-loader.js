(function () {
  const bubble = document.createElement("div");
  bubble.id = "novacool-bubble";
  bubble.innerHTML = `<img src="https://novacool.com/wp-content/uploads/2024/06/novacool-fire-logo.png"
                        style="width:52px; height:52px; border-radius:50%;">`;
  document.body.appendChild(bubble);

  const box = document.createElement("div");
  box.id = "novacool-chat-box";
  box.innerHTML = `
    <div id="nc-header">
      <span>Novacool AI Assistant</span>
      <button id="nc-close">×</button>
    </div>
    <div id="nc-body"></div>
    <input id="nc-input" type="text" placeholder="Ask a question…">
  `;
  document.body.appendChild(box);

  let open = false;

  bubble.onclick = () => {
    open = !open;
    box.style.display = open ? "flex" : "none";
    document.getElementById("nc-input").focus();
  };

  document.getElementById("nc-close").onclick = () => {
    open = false;
    box.style.display = "none";
  };

  document.getElementById("nc-input").addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      let q = e.target.value.trim();
      if (!q) return;
      e.target.value = "";
      document.getElementById("nc-body").innerHTML += `<div class="me">${q}</div>`;

      const r = await fetch("https://novacool-rag.onrender.com/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q })
      });
      const json = await r.json();
      document.getElementById("nc-body").innerHTML += `<div class="bot">${json.answer}</div>`;
      document.getElementById("nc-body").scrollTop = 999999;
    }
  });
})();
