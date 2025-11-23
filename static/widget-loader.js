/* ===========================================
   NOVACOOL FIRE-GLOW CHAT WIDGET LOADER
=========================================== */
(function () {

    // Inject CSS
    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = "https://novacool-rag.onrender.com/static/widget.css";
    document.head.appendChild(style);

    // Bubble HTML
    const widget = document.createElement("div");
    widget.id = "novacool-widget";
    widget.innerHTML = `
        <div id="novacool-bubble">
            <img src="https://us-wbe-img2.gr-cdn.com/user/123a38dc-e766-4012-98fe-ef769251a075/552046ab-dad4-498c-8cf3-9f1f4abffded.png"
                 alt="Novacool"
                 style="width: 48px; height: 48px; border-radius: 50%;" />
        </div>
    `;
    document.body.appendChild(widget);

    // Load chat UI script
    const s = document.createElement("script");
    s.src = "https://novacool-rag.onrender.com/static/chat-ui.js";
    s.defer = true;
    document.body.appendChild(s);
})();
