/* ===========================================
   NOVACOOL FIRE-GLOW CHAT WIDGET LOADER
   (Bubble opens panel and stays open until X pressed)
=========================================== */
(function () {

    /* ---- Load CSS ---- */
    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = "https://novacool-rag.onrender.com/static/widget.css";
    document.head.appendChild(style);

    /* ---- Build UI container (bubble + panel) ---- */
    const html = `
        <div id="novacool-bubble">
            <img src="https://novacool.com/wp-content/uploads/2024/06/novacool-fire-logo.png"
                 alt="Novacool"
                 style="width: 42px; height: 42px; border-radius: 50%;" />
        </div>

        <div id="novacool-chat-panel">
            <div id="novacool-close">✕</div>
            <iframe id="novacool-frame"
                src="https://novacool-rag.onrender.com/chat"
                loading="lazy"></iframe>
        </div>
    `;

    const container = document.createElement("div");
    container.id = "novacool-widget";
    container.innerHTML = html;
    document.body.appendChild(container);

    /* ---- Load chat UI behavior ---- */
    const script = document.createElement("script");
    script.src = "https://novacool-rag.onrender.com/static/chat-ui.js";
    script.defer = true;
    document.body.appendChild(script);
})();
