/* ===============================
   NOVACOOL AI FLOATING WIDGET LOADER — FIRE GLOW EDITION
   =============================== */

(function () {
    const IFRAME_URL = "https://novacool-rag.onrender.com/static/chat.html";
    const bubble = document.createElement("div");
    const frame = document.createElement("iframe");

    /* --- Bubble Icon --- */
    bubble.id = "novaBubble";
    bubble.style.cssText = `
        position: fixed;
        bottom: 22px;
        right: 22px;
        width: 70px;
        height: 70px;
        border-radius: 50%;
        background: url("https://novacool.com/wp-content/uploads/2024/04/fire-logo.png") center/cover no-repeat;
        cursor: pointer;
        z-index: 2147483647;
        box-shadow: 0 0 18px rgba(255, 60, 0, 0.6);
        animation: firePulse 2.8s infinite ease-in-out;
    `;
    document.body.appendChild(bubble);

    /* --- Glow Animation --- */
    const pulse = document.createElement("style");
    pulse.innerHTML = `
    @keyframes firePulse {
        0% { box-shadow: 0 0 10px rgba(255,60,0,.4); }
        50% { box-shadow: 0 0 26px rgba(255,60,0,.9); }
        100% { box-shadow: 0 0 10px rgba(255,60,0,.4); }
    }
    `;
    document.head.appendChild(pulse);

    /* --- Chat Iframe Window --- */
    frame.id = "novaFrame";
    frame.src = IFRAME_URL;
    frame.style.cssText = `
        position: fixed;
        bottom: 105px;
        right: 22px;
        width: 360px;
        height: 520px;
        border-radius: 14px;
        border: 2px solid #ff5722;
        display: none;
        z-index: 2147483647;
        background: #000;
    `;
    document.body.appendChild(frame);

    /* --- Show Chat on Bubble Click --- */
    bubble.addEventListener("click", () => {
        frame.style.display = "block";
    });

    /* --- Auto-open on first scroll (once) --- */
    let autoOpened = false;
    window.addEventListener("scroll", () => {
        if (!autoOpened) {
            autoOpened = true;
            frame.style.display = "block";
        }
    });

    /* --- Allow chat to close itself via postMessage --- */
    window.addEventListener("message", (event) => {
        if (event.data === "nova_close") {
            frame.style.display = "none";
        }
    });

})();
