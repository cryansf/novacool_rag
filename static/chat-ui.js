/* =======================
   Novacool Chat UI
======================= */
const BACKEND_URL = "https://novacool-rag.onrender.com/chat";

function addMessage(role, text) {
    const box = document.getElementById("messages");
    const div = document.createElement("div");
    div.textContent = (role === "user" ? "🧑 " : "🧯 ") + text;
    div.style.margin = "12px 0";
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById("userMessage");
    const question = input.value.trim();
    if (!question) return;

    addMessage("user", question);
    input.value = "";

    try {
        const res = await fetch(BACKEND_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: question })
        });

        const data = await res.json();
        addMessage("assistant", data.answer);
    } catch (err) {
        addMessage("assistant", "⚠️ Error connecting to backend.");
    }
}
