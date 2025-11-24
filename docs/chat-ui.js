(function () {
    const panel = document.createElement("div");
    panel.id = "novacool-chat-panel";
    panel.innerHTML = `
        <span id="novacool-close">✖</span>
        <iframe id="novacool-frame" src="https://novacool-rag.onrender.com/static/chat.html"></iframe>
    `;
    document.body.appendChild(panel);

    const bubble = document.getElementById("novacool-bubble");
    const closeBtn = document.getElementById("novacool-close");
    const iframe = document.getElementById("novacool-frame");

    let isOpen = false;

    bubble.addEventListener("click", () => {
        isOpen = !isOpen;
        panel.classList.toggle("open");

        if (isOpen) {
            iframe.contentWindow.postMessage({ action: "focus" }, "*");
        }
    });

    closeBtn.addEventListener("click", () => {
        isOpen = false;
        panel.classList.remove("open");
    });

    // 🔥 LISTEN for questions coming from chat.html
    window.addEventListener("message", async (e) => {
        if (e.data?.action === "ask") {
            const question = e.data.question;

            const response = await fetch("https://novacool-rag.onrender.com/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question })
            });

            const result = await response.json();
            iframe.contentWindow.postMessage(
                { action: "response", answer: result.answer },
                "*"
            );
        }
    });
})();
