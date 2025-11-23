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
            <img src="https://us-wbe-img2.gr-cdn.com/user/123a38dc-e766-4012-98fe-ef769251a075/552046ab-dad4-498c-8cf3-9f1f4abffded.png"
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
