/* ===========================================
   NOVACOOL CHAT ENGINE — FINAL JS
=========================================== */

(function () {
    let open = false;

    const bubble = document.getElementById("novacool-bubble");

    // Create chat panel container dynamically
    const panel = document.createElement("div");
    panel.id = "novacool-chat-panel";
    panel.innerHTML = `
        <div id="novacool-close">×</div>
        <iframe id="novacool-frame"
                src="https://novacool-rag.onrender.com/chat">
        </iframe>
    `;
    document.body.appendChild(panel);

    const frame = document.getElementById("novacool-frame");
    const closeBtn = document.getElementById("novacool-close");

    // Open / Close logic
    const toggle = () => {
        open = !open;
        if (open) {
            panel.classList.add("open");
            setTimeout(() => frame.contentWindow?.focus(), 200);
        } else {
            panel.classList.remove("open");
        }
    };

    bubble.addEventListener("click", toggle);
    closeBtn.addEventListener("click", toggle);

    // Auto-scroll inside iframe after messages arrive
    window.addEventListener("message", (evt) => {
        if (evt.data === "scrollChat") {
            try {
                const doc = frame.contentDocument || frame.contentWindow.document;
                let log = doc.getElementById("chat-log");
                if (log) log.scrollTop = log.scrollHeight;
            } catch (_) { }
        }
    });
})();
