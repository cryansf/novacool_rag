/* ============================================================
   Novacool AI Widget Loader – Full Working Edition
   ============================================================ */

(function () {
    // ==============================
    // CONFIGURATION
    // ==============================
    const IFRAME_URL = "https://novacool-rag.onrender.com/static/widget.html";
    const WIDGET_WIDTH = "420px";
    const WIDGET_HEIGHT = "570px";

    // ==============================
    // STYLE INJECTION
    // ==============================
    const style = document.createElement("style");
    style.innerHTML = `
        #novacool-bubble {
            position: fixed;
            bottom: 22px;
            right: 22px;
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: linear-gradient(45deg, #001e46, #b30000);
            box-shadow: 0 0 12px rgba(255,0,0,0.55);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.25s;
            z-index: 999999;
            animation: firePulse 2.2s infinite ease-in-out;
        }
        #novacool-bubble:hover {
            transform: scale(1.08);
        }
        @keyframes firePulse {
            0% { box-shadow: 0 0 6px rgba(255,0,0,0.35); }
            50% { box-shadow: 0 0 22px rgba(255,0,0,0.85); }
            100% { box-shadow: 0 0 6px rgba(255,0,0,0.35); }
        }

        #novacool-frame-container {
            position: fixed;
            bottom: 110px;
            right: 22px;
            width: ${WIDGET_WIDTH};
            height: ${WIDGET_HEIGHT};
            background: black;
            border-radius: 16px;
            overflow: hidden;
            border: 3px solid #b30000;
            display: none;
            opacity: 0;
            transition: 0.35s ease;
            z-index: 999998;
        }
        #novacool-frame-container.open {
            display: block;
            opacity: 1;
        }

        @media(max-width: 640px) {
            #novacool-frame-container {
                width: 100vw;
                height: 100vh;
                bottom: 0;
                right: 0;
                border-radius: 0;
                border: none;
            }
        }
    `;
    document.head.appendChild(style);

    // ==============================
    // CREATE ELEMENTS
    // ==============================
    const bubble = document.createElement("div");
    bubble.id = "novacool-bubble";
    bubble.innerHTML = `<img src="https://novacool.com/wp-content/uploads/2024/08/novacool-icon-fire.png" style="width:34px;">`;

    const frameBox = document.createElement("div");
    frameBox.id = "novacool-frame-container";

    const iframe = document.createElement("iframe");
    iframe.src = IFRAME_URL;
    iframe.style = "width:100%; height:100%; border:none;";

    frameBox.appendChild(iframe);
    document.body.appendChild(bubble);
    document.body.appendChild(frameBox);

    // ==============================
    // EVENT HANDLERS
    // ==============================
    bubble.addEventListener("click", () => {
        const isOpen = frameBox.classList.contains("open");
        if (isOpen) {
            frameBox.classList.remove("open");
        } else {
            frameBox.classList.add("open");
        }
    });

    // Allow iframe to resize parent
    window.addEventListener("message", (event) => {
        if (event.data && event.data.height) {
            frameBox.style.height = event.data.height + "px";
        }
    });
})();
