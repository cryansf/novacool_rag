/* ===========================================
   NOVACOOL FIRE-GLOW CHAT WIDGET LOADER
=========================================== */
(function () {

    /* ---- Load CSS ---- */
    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = "https://novacool-rag.onrender.com/static/widget.css";
    document.head.appendChild(style);

    /* ---- Create Widget Container (bubble + panel) ---- */
    const html = `
        <div id="novacool-bubble">
            <img src="https://novacool.com/wp-content/uploads/2024/06/novacool-fire-logo.png"
                 alt="Novacool"
                 style="width: 42px; height: 42px; border-radius: 50%;" />
        </div>

        <div id="novacool-chat-panel">
            <iframe id="novacool-frame"
                src="https://novacool-rag.onrender.com/chat"
                loading="lazy"></iframe>
        </div>
    `;

    const container = document.createElement("div");
    container.id = "novacool-widget";
    container.innerHTML = html;
    document.body.appendChild(container);

    /* ---- Load chat UI script ---- */
    const script = document.createElement("script");
    script.src = "https://novacool-rag.onrender.com/static/chat-ui.js";
    script.defer = true;
    document.body.appendChild(script);

    /* ---- Bubble Click → Open Panel ---- */
    document.body.addEventListener("click", (e) => {
        if (!e.target.closest("#novacool-bubble")) return;
        document.getElementById("novacool-chat-panel")?.classList.add("open");
    });
})();
