(function () {
    console.log("🔥 Novacool Fire Widget Loader initializing...");

    if (window.NovaWidgetLoaded) {
        console.warn("Novacool widget already loaded.");
        return;
    }
    window.NovaWidgetLoaded = true;

    // Widget + Logo URLs
    const WIDGET_URL = "https://novacool-rag.onrender.com/static/widget.html";
    const LOGO_URL = "https://novacool-rag.onrender.com/static/logo-fire.png";

    /* ===========================================================
       🔥 CREATE CHAT PANEL
       =========================================================== */
    const widget = document.createElement("div");
    widget.id = "novacool-chat-widget";
    widget.style.cssText = `
        position: fixed;
        bottom: 22px;
        right: 22px;
        width: 400px;
        height: 520px;
        background: linear-gradient(180deg, #FF6A00, #8B0000);
        border-radius: 16px;
        box-shadow: 0 0 30px rgba(255,80,0,0.7);
        overflow: hidden;
        display: none;
        opacity: 0;
        transition: opacity 0.35s ease;
        z-index: 999999;
    `;

    const frame = document.createElement("iframe");
    frame.src = WIDGET_URL;
    frame.style.cssText = `
        width: 100%;
        height: 100%;
        border: none;
    `;
    widget.appendChild(frame);

    /* ===========================================================
       🔥 FIRE CHAT BUBBLE BUTTON
       =========================================================== */
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
        box-shadow: 0 0 22px rgba(255,60,0,1);
        cursor: pointer;
        z-index: 999999;
        animation: fireFlicker 1.8s infinite ease-in-out;
    `;

    /* ===========================================================
       🔥 FIRE FLICKER + EMBER ANIMATIONS
       =========================================================== */
    const style = document.createElement("style");
    style.innerHTML = `
        @keyframes fireFlicker {
            0%   { transform: scale(1.00); box-shadow: 0 0 14px rgba(255,80,0,0.8); }
            5%   { transform: scale(1.03); box-shadow: 0 0 22px rgba(255,50,0,1); }
            10%  { transform: scale(1.01); box-shadow: 0 0 18px rgba(255,100,0,0.9); }
            15%  { transform: scale(1.04); box-shadow: 0 0 26px rgba(255,40,0,1); }
            22%  { transform: scale(1.02); box-shadow: 0 0 20px rgba(255,85,0,0.9); }
            30%  { transform: scale(1.06); box-shadow: 0 0 32px rgba(255,30,0,1); }
            40%  { transform: scale(1.03); box-shadow: 0 0 24px rgba(255,100,0,0.95); }
            55%  { transform: scale(1.01); box-shadow: 0 0 18px rgba(255,60,0,0.8); }
            70%  { transform: scale(1.05); box-shadow: 0 0 30px rgba(255,20,0,1); }
            85%  { transform: scale(1.02); box-shadow: 0 0 22px rgba(255,95,0,0.9); }
            100% { transform: scale(1.00); box-shadow: 0 0 14px rgba(255,80,0,0.8); }
        }

        @keyframes emberFloat {
            0%   { opacity: 0; transform: translateY(0) scale(0.2); }
            40%  { opacity: 1; }
            100% { opacity: 0; transform: translateY(-40px) scale(0.4); }
        }
    `;
    document.head.appendChild(style);

    /* ===========================================================
       🔥 TOGGLE OPEN/CLOSE
       =========================================================== */
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

    /* ===========================================================
       🔥 AUTO-OPEN ON FIRST SCROLL
       =========================================================== */
    window.addEventListener("scroll", () => {
        if (!window.NovaOpened && window.scrollY > window.innerHeight * 0.3) {
            bubble.click();
            window.NovaOpened = true;
        }
    });

    /* ===========================================================
       🔥 EMBER PARTICLE SYSTEM
       =========================================================== */
    function spawnEmber() {
        const ember = document.createElement("div");
        const size = Math.floor(Math.random() * 4) + 3;

        ember.style.cssText = `
            position: fixed;
            bottom: 22px;
            right: 22px;
            width: ${size}px;
            height: ${size}px;
            background: radial-gradient(circle,
                rgba(255,160,0,1) 0%,
                rgba(255,80,0,0.6) 60%,
                rgba(255,0,0,0) 100%
            );
            border-radius: 50%;
            pointer-events: none;
            z-index: 999997;
            opacity: 0;
        `;

        document.body.appendChild(ember);

        const driftX = (Math.random() * 60) - 30;
        const driftY = 80 + Math.random() * 50;
        const duration = 1500 + Math.random() * 900;

        ember.animate(
            [
                { transform: "translate(0, 0) scale(1)", opacity: 0 },
                { opacity: 1, offset: 0.2 },
                {
                    transform: `translate(${driftX}px, -${driftY}px) scale(0.4)`,
                    opacity: 0
                }
            ],
            {
                duration: duration,
                easing: "ease-out",
                fill: "forwards",
            }
        );

        setTimeout(() => {
            document.body.removeChild(ember);
        }, duration + 200);
    }

    setInterval(() => {
        if (Math.random() < 0.4) spawnEmber();
    }, 280);

    /* ===========================================================
       🔥 ADD TO PAGE
       =========================================================== */
    document.body.appendChild(widget);
    document.body.appendChild(bubble);

    console.log("🔥 Novacool Fire Widget Loaded");
})();
