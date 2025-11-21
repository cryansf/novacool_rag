/* ===========================================
   NOVACOOL CHAT UI — OPEN/CLOSE & FOCUS
=========================================== */

document.addEventListener("click", function (e) {
    const bubble = e.target.closest("#novacool-bubble");
    const closeBtn = e.target.closest("#novacool-close");
    const panel = document.getElementById("novacool-chat-panel");

    if (!panel) return;

    // Open panel
    if (bubble) {
        panel.classList.add("open");
        return;
    }

    // Close panel
    if (closeBtn) {
        panel.classList.remove("open");
        return;
    }
});
