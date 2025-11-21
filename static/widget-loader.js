/* ===========================================
   NOVACOOL FIRE-GLOW CHAT WIDGET LOADER
=========================================== */
(function () {
    // Inject styles
    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = "https://novacool-rag.onrender.com/static/widget.css";
    document.head.appendChild(style);

    // Bubble + container
    const bubble = document.createElement("div");
    bubble.id = "novacool-widget";
    bubble.innerHTML = `
        <div id="novacool-bubble">
            <img src="https://novacool.com/wp-content/uploads/2024/06/novacool-fire-logo.png"
                 alt="Novacool"
                 style="width: 42px; height: 42px; border-radius: 50%;" />
        </div>
    `;
    document.body.appendChild(bubble);

    // Load chat engine
    const script = document.createElement("script");
    script.src = "https://novacool-rag.onrender.com/static/chat-ui.js";
    script.defer = true;
    script.onload = () => console.log("Novacool Chat UI loaded.");
    document.body.appendChild(script);
})();
