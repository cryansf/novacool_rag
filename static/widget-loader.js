/* ===========================================
   NOVACOOL FIRE-GLOW CHAT WIDGET LOADER
   Backend: https://novacool-rag.onrender.com/chat
=========================================== */

(function () {
    const bubble = document.createElement("div");
    bubble.id = "novacool-widget";
    bubble.innerHTML = `
        <div id="novacool-bubble">
            <img src="https://novacool.com/wp-content/uploads/2024/06/novacool-fire-logo.png" 
                 alt="Novacool"
                 style="width: 42px; height: 42px; border-radius: 50%;"/>
        </div>
        <iframe id="novacool-frame" src="https://novacool-rag.onrender.com/static/chat.html"></iframe>
    `;
    document.body.appendChild(bubble);

    const css = document.createElement("style");
    css.innerHTML = `
        #novacool-widget {
            position: fixed;
            bottom: 26px;
            right: 26px;
            z-index: 999999;
        }

        #novacool-bubble {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255,70,70,1) 0%, rgba(180,0,0,1) 70%);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 0 18px rgba(255,0,0,0.65);
            animation: firePulse 2.4s infinite ease-in-out;
            transition: transform 0.3s;
        }

        #novacool-bubble:hover {
            transform: scale(1.12);
        }

        @keyframes firePulse {
            0% { box-shadow: 0 0 12px rgba(255,0,0,0.35); }
            50% { box-shadow: 0 0 26px rgba(255,60,0,0.9); }
            100% { box-shadow: 0 0 12px rgba(255,0,0,0.35); }
        }

        #novacool-frame {
            width: 420px;
            height: 550px;
            border: none;
            border-radius: 15px;
            position: fixed;
            bottom: 105px;
            right: 26px;
            display: none;
            box-shadow: 0 0 24px rgba(0,0,0,0.55);
        }
    `;
    document.head.appendChild(css);

    const bubbleBtn = document.getElementById("novacool-bubble");
    const frame = document.getElementById("novacool-frame");
    let opened = false;

    bubbleBtn.addEventListener("click", () => {
        opened = !opened;
        frame.style.display = opened ? "block" : "none";
    });

    /* Auto open after scrolling 40% of the page */
    let autoOpened = false;
    window.addEventListener("scroll", () => {
        if (!autoOpened && window.scrollY > window.innerHeight * 0.4) {
            autoOpened = true;
            frame.style.display = "block";
            opened = true;
        }
    });
})();
