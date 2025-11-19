/* ============================================================
   Novacool AI Widget Loader – Working Production Build
   ============================================================ */

(function () {
    // ============================================================
    // URL OF THE WIDGET UI (must be the exact HTML file we fixed)
    // ============================================================
    const IFRAME_URL = "https://novacool-rag.onrender.com/static/widget.html";

    // ============================================================
    // STYLE INJECTION
    // ============================================================
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
            box-shadow: 0 0 16px rgba(255,0,0,0.6);
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: 0.25s;
            z-index: 999999;
        }
        #novacool-bubble:hover { transform: scale(1.08); }

        #novacool-frame-container {
            position: fixed;
            bottom: 110px;
            right: 22px;
            width: 420px;
            height: 570px;
            background: black;
            border: 3px solid #b30000;
            border-radius: 16px;
            overflow: hidden;
            opacity: 0;
            display: none;
            transition: opacity 0.35s ease;
            z-index: 999998;
        }
        #novacool-frame-container.open {
            display: block;
            opacity: 1;
        }

        @media (max-width: 620px) {
            #novacool-frame-container {
                bottom: 0;
                right: 0;
                width: 100vw;
                height: 100vh;
                border-radius: 0;
                border: none;
            }
        }
    `;
    document.head.appendChild(style);

    // ============================================================
    // ELEMENT CREATION
    // ============================================================
    const bubble = document.createElement("div");
    bubble.id = "novacool-bubble";
    bubble.innerHTML = `<img src="https://novacool.com/wp-content/uploads/2024/08/novacool-icon-fire.png" style="width:36px;">`;

    const frameBox = document.createElement("div");
    frameBox.id = "novacool-frame-container";

    const iframe = document.createElement("iframe");
    iframe.src = IFRAME_URL;
    iframe.style = "width:100%; height:100%; border:none;";
    frameBox.appendChild(iframe);

    document.body.appendChild(bubble);
    document.body.appendChild(frameBox);

    // ============================================================
    // OPEN / CLOSE BEHAVIOR
    // ============================================================
    bubble.addEventListener("click", () => {
        const open = frameBox.classList.contains("open");
        if (open) {
            frameBox.classList.remove("open");
        } else {
            frameBox.classList.add("open");
        }
    });

    // ============================================================
    // DYNAMIC HEIGHT SUPPORT (for iframe resize reporting)
    // ============================================================
    window.addEventListener("message", (event) => {
        if (event.data && event.data.height) {
            frameBox.style.height = event.data.height + "px";
        }
    });
})();
