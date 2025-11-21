/* ===========================================
   NOVACOOL CHAT — NO IFRAME VERSION
=========================================== */

(function () {
    const panel = document.createElement("div");
    panel.id = "novacool-chat-panel";
    panel.innerHTML = `
        <div id="novacool-close">✕</div>
        <div id="novacool-messages" style="height: 420px; overflow-y: auto; padding: 12px;"></div>
        <div style="padding: 10px; border-top: 2px solid #a30000;">
            <input id="novacool-input" type="text" placeholder="Ask anything about Novacool" 
                style="width: 72%; padding: 8px; border-radius: 6px; border: 1px solid #ccc;">
            <button id="novacool-send"
                style="background:#c40000; color:white; padding:8px 14px; border:none; border-radius:6px;">
                Send
            </button>
        </div>
    `;
    document.querySelector("#novacool-widget").appendChild(panel);

    const bubble = document.getElementById("novacool-bubble");
    const closeBtn = document.getElementById("novacool-close");
    const input = document.getElementById("novacool-input");
    const sendBtn = document.getElementById("novacool-send");
    const messages = document.getElementById("novacool-messages");

    function addMsg(text, from) {
        const el = document.createElement("div");
        el.style.margin = "8px 0";
        el.style.fontWeight = from === "bot" ? "600" : "400";
        el.textContent = text;
        messages.appendChild(el);
        messages.scrollTop = messages.scrollHeight;
    }

    async function ask() {
        const q = input.value.trim();
        if (!q) return;
        addMsg(q, "user");
        input.value = "";

        try {
            const r = await fetch("https://novacool-rag.onrender.com/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: q })
            });

            const data = await r.json();
            if (data.error) addMsg("⚠️ " + data.error, "bot");
            else addMsg(data.answer, "bot");
        } catch {
            addMsg("⚠️ Network error — try again.", "bot");
        }
    }

    sendBtn.addEventListener("click", ask);
    input.addEventListener("keydown", e => e.key === "Enter" && ask());

    bubble.addEventListener("click", () => panel.classList.toggle("open"));
    closeBtn.addEventListener("click", () => panel.classList.remove("open"));
})();
