(function () {
    // Avoid double-loading
    if (window.NovacoolWidgetLoaded) return;
    window.NovacoolWidgetLoaded = true;

    // Create bubble button
    const bubble = document.createElement("div");
    bubble.id = "novacool-chat-bubble";
    bubble.style.position = "fixed";
    bubble.style.bottom = "20px";
    bubble.style.right = "20px";
    bubble.style.width = "70px";
    bubble.style.height = "70px";
    bubble.style.background = "#0055ff";
    bubble.style.borderRadius = "50%";
    bubble.style.boxShadow = "0 4px 10px rgba(0,0,0,0.25)";
    bubble.style.cursor = "pointer";
    bubble.style.zIndex = "999999";
    bubble.style.display = "flex";
    bubble.style.alignItems = "center";
    bubble.style.justifyContent = "center";
    bubble.style.color = "white";
    bubble.style.fontSize = "32px";
    bubble.style.fontWeight = "bold";
    bubble.innerHTML = "💬";
    document.body.appendChild(bubble);

    // Create iframe panel
    const panel = document.createElement("iframe");
    panel.id = "novacool-chat-panel";
    panel.style.position = "fixed";
    panel.style.bottom = "100px";
    panel.style.right = "20px";
    panel.style.width = "420px";
    panel.style.height = "600px";
    panel.style.border = "1px solid #ccc";
    panel.style.borderRadius = "12px";
    panel.style.display = "none";
    panel.style.zIndex = "999999";
    panel.src = "https://novacool-rag.onrender.com/";
    document.body.appendChild(panel);

    // Toggle open/close
    bubble.addEventListener("click", () => {
        panel.style.display = panel.style.display === "none" ? "block" : "none";
    });
})();
