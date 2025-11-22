/* ============================================
   NOVACOOL — CHAT UI CONTROLLER
   Works with app_flask.py /chat POST endpoint
============================================ */

(function () {
    console.log("Novacool Chat UI initializing...");

    const widget = document.getElementById("novacool-widget");
    const bubble = document.getElementById("novacool-bubble");

    // Create chat panel
    const panel = document.createElement("div");
    panel.id = "novacool-chat-panel";
    panel.innerHTML = `
        <span id="novacool-close">×</span>
        <div id="novacool-messages" style="padding:12px; overflow-y:auto; height:85%; color:#fff; font-family:system-ui;"></div>
        <div style="display:flex; gap:6px; padding:8px; align-items:center;">
            <input id="novacool-input" type="text" placeholder="Ask anything about Novacool"
                style="flex:1; padding:8px 10px; border-radius:6px; border:1px solid #ccc; font-size:15px;">
            <button id="novacool-send"
                style="background:#c40000; border:none; padding:8px 16px; border-radius:6px; color:#fff; cursor:pointer; font-size:15px;">
                Send
            </button>
        </div>
    `;
    widget.appendChild(panel);

    const messages = document.getElementById("novacool-messages");
    const input = document.getElementById("novacool-input");
    const sendBtn = document.getElementById("novacool-send");
    const closeBtn = document.getElementById("novacool-close");

    let isOpen = false;

    // Toggle chat
    bubble.addEventListener("click", () => {
        isOpen = !isOpen;
        panel.classList.toggle("open", isOpen);
    });

    closeBtn.addEventListener("click", () => {
        isOpen = false;
        panel.classList.remove("open");
    });

    // Append message to UI
    function addMessage(text, sender) {
        const row = document.createElement("div");
        row.style.margin = "6px 0";
        row.style.color = sender === "bot" ? "#ffe9e9" : "#87e3ff";
        row.textContent = text;
        messages.appendChild(row);
        messages.scrollTop = messages.scrollHeight;
    }

    // Send chat request
    async function sendQuestion() {
        const question = input.value.trim();
        if (!question) return;

        addMessage(question, "user");
        input.value = "";

        try {
            const res = await fetch("https://novacool-rag.onrender.com/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question })
            });

            const data = await res.json();
            if (data.answer) addMessage(data.answer, "bot");
            else addMessage("⚠️ Error: " + (data.error || "Unknown error"), "bot");

        } catch (e) {
            addMessage("⚠️ Network error — backend unreachable.", "bot");
        }
    }

    sendBtn.addEventListener("click", sendQuestion);
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendQuestion();
    });

    console.log("Novacool Chat UI loaded.");
})();
