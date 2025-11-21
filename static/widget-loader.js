/* ===========================================
   NOVACOOL FIRE-GLOW CHAT WIDGET LOADER
=========================================== */
(function () {
    // Inject styles
    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = "https://novacool-rag.onrender.com/static/widget.css";
    document.head.appendChild(style);

    // Bubble + container with iframe
    const container = document.createElement("div");
    container.id = "novacool-widget";
    container.innerHTML = `
        <div id="novacool-bubble">
            <img src="https://novacool.com/wp-content/uploads/2024/06/novacool-fire-logo.png"
                 alt="Novacool"
                 style="width:42px;height:42px;border-radius:50%;" />
        </div>
        <div id="novacool-chatbox">
            <iframe id="novacool-iframe"
                src="https://novacool-rag.onrender.com/static/chat.html"
                frameborder="0"
                allow="clipboard-write; microphone">
            </iframe>
        </div>
    `;
    document.body.appendChild(container);

    // Load UI logic
    const script = document.createElement("script");
    script.src = "https://novacool-rag.onrender.com/static/chat-ui.js";
    script.defer = true;
    document.body.appendChild(script);
})();
