/* ===========================================
   NOVACOOL FIRE-GLOW CHAT WIDGET LOADER
   Backend API: https://novacool-rag.onrender.com/chat
=========================================== */

(function () {

    /* ---- 1) Inject widget container into page ---- */
    const widget = document.createElement("div");
    widget.id = "novacool-widget";
    widget.innerHTML = `
        <div id="novacool-bubble">
            <img src="https://novacool.com/wp-content/uploads/2024/06/novacool-fire-logo.png"
                 alt="Novacool"
                 style="width: 42px; height: 42px; border-radius: 50%;" />
        </div>
        <div id="novacool-window" style="display:none;"></div>
    `;
    document.body.appendChild(widget);


    /* ---- 2) Elements for interaction ---- */
    const bubbleBtn = document.getElementById("novacool-bubble");
    const chatWindow = document.getElementById("novacool-window");
    let opened = false;


    /* ---- 3) Open/close widget on click ---- */
    bubbleBtn.addEventListener("click", () => {
        opened = !opened;
        chatWindow.style.display = opened ? "block" : "none";
    });


    /* ---- 4) Auto-open after scrolling down 40% ---- */
    let autoOpened = false;
    window.addEventListener("scroll", () => {
        if (!autoOpened && window.scrollY > window.innerHeight * 0.40) {
            chatWindow.style.display = "block";
            opened = true;
            autoOpened = true;
        }
    });


    /* ---- 5) Load React chat app into novacool-window ---- */
    const scriptReact = document.createElement("script");
    scriptReact.src = "https://novacool-rag.onrender.com/static/chat-ui.js";
    scriptReact.defer = true;
    document.body.appendChild(scriptReact);

})();
