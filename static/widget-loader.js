/* ============================================================================
   NOVACOOL AI — FLOATING CHAT WIDGET LOADER
   ============================================================================ */
(function () {
  const IFRAME_URL = "https://novacool-rag.onrender.com/static/widget.html";

  /* -------------------- Create Bubble -------------------- */
  const bubble = document.createElement("div");
  bubble.id = "novaBubble";
  bubble.style.cssText = `
    position: fixed;
    bottom: 22px;
    right: 22px;
    width: 72px;
    height: 72px;
    border-radius: 50%;
    cursor: pointer;
    z-index: 999999;
    background: url("https://novacool.com/wp-content/uploads/2024/04/NovacoolFlame-Icon.png") center/cover no-repeat;
    box-shadow: 0 0 18px rgba(255, 60, 0, 0.6);
    animation: firePulse 2.8s infinite ease-in-out;
  `;

  const pulse = document.createElement("style");
  pulse.innerHTML = `
    @keyframes firePulse {
      0% { box-shadow: 0 0 10px rgba(255,60,0,0.4); }
      50% { box-shadow: 0 0 27px rgba(255,60,0,0.9); }
      100% { box-shadow: 0 0 10px rgba(255,60,0,0.4); }
    }
  `;
  document.head.appendChild(pulse);
  document.body.appendChild(bubble);

  /* -------------------- Create Iframe -------------------- */
  const frame = document.createElement("iframe");
  frame.id = "novaFrame";
  frame.src = "";
  frame.allow = "clipboard-read; clipboard-write";
  frame.style.cssText = `
    position: fixed;
    bottom: 105px;
    right: 22px;
    width: 380px;
    height: 540px;
    border-radius: 16px;
    border: 2px solid #ff5722;
    background: #000;
    display: none;
    z-index: 999999;
  `;
  document.body.appendChild(frame);

  /* -------------------- Open / Close Logic -------------------- */
  let isOpen = false;

  function openChat() {
    if (!isOpen) {
      frame.style.display = "block";
      frame.src = IFRAME_URL;
      isOpen = true;
    }
  }

  function closeChat() {
    frame.style.display = "none";
    isOpen = false;
  }

  bubble.addEventListener("click", () => {
    if (isOpen) closeChat();
    else openChat();
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && isOpen) closeChat();
  });

  /* -------------------- Optional Auto-Open -------------------- */
  let scrolled = false;
  window.addEventListener("scroll", () => {
    if (!scrolled) {
      scrolled = true;
      setTimeout(openChat, 400);
    }
  });

  /* -------------------- Mobile Responsiveness -------------------- */
  function adjustForMobile() {
    if (window.innerWidth < 600) {
      frame.style.width = "92%";
      frame.style.height = "78%";
      frame.style.right = "4%";
      frame.style.bottom = "90px";
    } else {
      frame.style.width = "380px";
      frame.style.height = "540px";
      frame.style.right = "22px";
      frame.style.bottom = "105px";
    }
  }

  adjustForMobile();
  window.addEventListener("resize", adjustForMobile);
})();
