(function () {

    if (window.NovaWidgetLoaded) return;
    window.NovaWidgetLoaded = true;

    const WIDGET_URL = "https://novacool-rag.onrender.com/static/widget.html";
    const LOGO_URL   = "https://novacool-rag.onrender.com/static/logo-fire.png";

    /* PANEL */
    const widget = document.createElement("div");
    widget.id = "novacool-chat-widget";
    widget.style.cssText = `
        position: fixed;
        bottom: 22px;
        right: 22px;
        width: 400px;
        height: 520px;
        background: #1a0000;
        border-radius: 16px;
        box-shadow: 0 0 30px rgba(255,0,0,0.7);
        overflow: hidden;
        display: none;
        opacity: 0;
        transition: opacity 0.35s ease;
        z-index: 999999;
    `;

    const frame = document.createElement("iframe");
    frame.src = WIDGET_URL;
    frame.style.cssText = "width:100%; height:100%; border:none;";
    widget.appendChild(frame);

    /* RED GLOW BUBBLE */
    const bubble = document.createElement("div");
    bubble.id = "novacool-chat-bubble";
    bubble.style.cssText = `
        position: fixed;
        bottom: 22px;
        right: 22px;
        width: 80px;
        height: 80px;
        background: url('${LOGO_URL}') center/contain no-repeat;
        border-radius: 50%;
        box-shadow: 0 0 22px rgba(255,0,0,1);
        cursor: pointer;
        z-index: 999999;
        animation: redFlicker 1.8s infinite ease-in-out;
    `;

    /* FIRE FLICKER ANIMATION (RED VERSION) */
    const style = document.createElement("style");
    style.innerHTML = `
        @keyframes redFlicker {
            0%   { transform: scale(1.00); box-shadow: 0 0 14px rgba(255,0,0,0.8); }
            5%   { transform: scale(1.03); box-shadow: 0 0 22px rgba(255,0,0,1); }
            10%  { transform: scale(1.01); box-shadow: 0 0 18px rgba(255,50,50,0.9); }
            15%  { transform: scale(1.04); box-shadow: 0 0 26px rgba(255,0,0,1); }
            22%  { transform: scale(1.02); box-shadow: 0 0 20px rgba(255,60,60,0.9); }
            30%  { transform: scale(1.06); box-shadow: 0 0 32px rgba(255,0,0,1); }
            40%  { transform: scale(1.03); box-shadow: 0 0 24px rgba(255,80,80,0.95); }
            55%  { transform: scale(1.01); box-shadow: 0 0 18px rgba(255,40,40,0.8); }
            70%  { transform: scale(1.05); box-shadow: 0 0 30px rgba(255,0,0,1); }
            85%  { transform: scale(1.02); box-shadow: 0 0 22px rgba(255,70,70,0.9); }
            100% { transform: scale(1.00); box-shadow: 0 0 14px rgba(255,0,0,0.8); }
        }
    `;
    document.head.appendChild(style);

    /* OPEN / CLOSE */
    bubble.onclick = () => {
        const open = widget.style.display === "block";
        if (open) {
            widget.style.opacity = 0;
            setTimeout(() => (widget.style.display = "none"), 250);
        } else {
            widget.style.display = "block";
            setTimeout(() => (widget.style.opacity = 1), 10);
        }
    };

    /* AUTO OPEN ON SCROLL */
    window.addEventListener("scroll", () => {
        if (!window.NovaOpened && window.scrollY > window.innerHeight * 0.3) {
            bubble.click();
            window.NovaOpened = true;
        }
    });

    /* ADD TO PAGE */
    document.body.appendChild(widget);
    document.body.appendChild(bubble);

})();
