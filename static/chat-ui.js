/* ============================================
   NOVACOOL CHAT UI — FINAL STABLE VERSION
============================================== */
(function () {
    const API_URL = "https://novacool-rag.onrender.com/chat";

    // Create chat container
    const wrapper = document.createElement("div");
    wrapper.id = "novacool-chat-container";
    wrapper.innerHTML = `
        <div id="chat-window">
            <div id="chat-header">
                🔥 Ask Novacool AI
                <span id="close-chat">×</span>
            </div>
            <div id="chat-messages"></div>
            <div id="chat-input-row">
                <input type="text" id="chat-input" placeholder="Ask anything about Novacool">
                <button id="chat-send">Send</button>
            </div>
        </div>
    `;
    document.body.appendChild(wrapper);

    const bubble = document.getElementById("novacool-bubble");
    const closeBtn = wrapper.querySelector("#close-chat");
    const sendBtn = wrapper.querySelector("#chat-send");
    const input = wrapper.querySelector("#chat-input");
    const messages = wrapper.querySelector("#chat-messages");

    let opened = false;

    function toggleChat(open) {
        opened = open;
        wrapper.style.display = opened ? "block" : "none";
    }

    bubble.addEventListener("click", () => toggleChat(!opened));
    closeBtn.addEventListener("click", () => toggleChat(false));

    // Display message inside chat
    function addMessage(text, sender) {
        const div = document.createElement("div");
        div.className = sender;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    // Send message
    async function handleSend() {
        const question = input.value.trim();
        if (!question) return;

        addMessage(question, "user");
        input.value = "";

        try {
            const res = await fetch(API_URL, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ question })
            });

            const data = await res.json();
            if (data.answer) addMessage(data.answer, "bot");
            else addMessage("⚠️ No answer available.", "bot");

        } catch (err) {
            addMessage("⚠️ Connection error.", "bot");
        }
    }

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keydown", e => e.key === "Enter" && handleSend());
})();
