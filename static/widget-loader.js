// Novacool Chat Widget Loader – Option C, Animation Style #3 (Ember Burst, Safe Duplicate-Proof Version)

// === Global duplicate protection ===
if (window.__NOVACOOL_WIDGET_ACTIVE__) {
  console.warn("Novacool widget already loaded — duplicate script tag ignored.");
  // Stop here if a previous instance already ran
  // This prevents double bubbles, double iframes, and broken close behavior.
} else {
  window.__NOVACOOL_WIDGET_ACTIVE__ = true;

  (function () {
    // Avoid running inside iframes (only on top window)
    try {
      if (window.top !== window.self) return;
    } catch (e) {
      // Ignore cross-origin access errors, assume we're in an iframe
      return;
    }

    // Old-style guard (kept for backward compatibility)
    if (window.__NOVACOOL_WIDGET_LOADED__) return;
    window.__NOVACOOL_WIDGET_LOADED__ = true;

    // === CONFIG: update this to where you host widget.html ===
    // This is your full-page chat URL (works both in iframe + menu link)
    var WIDGET_URL = "https://novacool-rag.onrender.com/static/widget.html";

    // Auto-open once per session after scroll
    var AUTO_OPEN_SCROLL_PX = 450;
    var AUTO_OPEN_KEY = "nc_widget_auto_open_v1";

    function createStyles() {
      if (document.getElementById("nc-widget-styles")) return;
      var css = document.createElement("style");
      css.id = "nc-widget-styles";
      css.textContent = `
        #nc-chat-panel {
          position: fixed;
          z-index: 999999;
          bottom: 98px;
          right: 22px;
          width: min(420px, 92vw);
          height: 540px;
          border-radius: 20px;
          overflow: hidden;
          background: radial-gradient(circle at top, #151725 0, #05070a 60%);
          box-shadow:
            0 10px 45px rgba(0, 0, 0, 0.85),
            0 0 40px rgba(255, 120, 40, 0.45);
          border: 1px solid rgba(255, 255, 255, 0.12);
          transform-origin: bottom right;
          transform: translateY(18px) scale(0.9);
          opacity: 0;
          pointer-events: none;
          transition:
            opacity 0.25s ease-out,
            transform 0.25s ease-out;
        }

        #nc-chat-panel.nc-open {
          opacity: 1;
          pointer-events: auto;
          transform: translateY(0) scale(1);
        }

        #nc-chat-panel iframe {
          width: 100%;
          height: 100%;
          border: none;
          display: block;
        }

        #nc-chat-bubble {
          position: fixed;
          z-index: 999999;
          bottom: 22px;
          right: 22px;
          width: 64px;
          height: 64px;
          border-radius: 50%;
          border: 1px solid rgba(255, 255, 255, 0.4);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 0;
          cursor: pointer;
          color: #ffffff;
          font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          font-size: 0.7rem;
          font-weight: 700;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          text-align: center;
          background:
            radial-gradient(circle at 30% 0, #ffe8e0 0, #ff7a1a 32%, #c8102e 75%, #05070a 100%);
          box-shadow:
            0 0 0 0 rgba(200, 16, 46, 0.6),
            0 0 26px rgba(255, 140, 0, 0.9);
          animation: nc-fire-pulse 2.4s infinite;
          transition:
            transform 0.12s ease-out,
            box-shadow 0.15s ease-out,
            background 0.15s ease-out;
        }

        #nc-chat-bubble span {
          line-height: 1.1;
        }

        #nc-chat-bubble:hover {
          transform: translateY(-2px) scale(1.03);
          box-shadow:
            0 0 0 12px rgba(255, 120, 50, 0.05),
            0 0 34px rgba(255, 180, 80, 1);
        }

        #nc-chat-bubble.nc-open {
          background: radial-gradient(circle at 30% 0, #e0f2ff 0, #2563eb 40%, #0b1120 90%);
          box-shadow:
            0 0 0 10px rgba(37, 99, 235, 0.15),
            0 0 30px rgba(56, 189, 248, 0.7);
          animation: none;
        }

        @keyframes nc-fire-pulse {
          0% {
            box-shadow:
              0 0 0 0 rgba(200, 16, 46, 0.65),
              0 0 22px rgba(255, 140, 0, 0.9);
          }
          60% {
            box-shadow:
              0 0 0 22px rgba(200, 16, 46, 0),
              0 0 40px rgba(255, 200, 80, 1);
          }
          100% {
            box-shadow:
              0 0 0 0 rgba(200, 16, 46, 0),
              0 0 22px rgba(255, 140, 0, 0.9);
          }
        }

        #nc-header-cta {
          position: fixed;
          z-index: 999998;
          top: 16px;
          right: 22px;
          padding: 0.45rem 0.85rem;
          border-radius: 999px;
          border: 1px solid rgba(255, 255, 255, 0.35);
          background: linear-gradient(120deg, #003a70, #2563eb);
          color: #f9fafb;
          font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          font-size: 0.72rem;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          cursor: pointer;
          box-shadow:
            0 6px 16px rgba(15, 23, 42, 0.7),
            0 0 18px rgba(56, 189, 248, 0.5);
          display: none;
        }

        #nc-header-cta span {
          margin-left: 0.3rem;
          font-size: 0.85rem;
        }

        #nc-header-cta.nc-visible {
          display: inline-flex;
          align-items: center;
        }

        .nc-ember {
          position: fixed;
          z-index: 999997;
          width: 5px;
          height: 5px;
          border-radius: 999px;
          pointer-events: none;
          background: radial-gradient(circle, rgba(255, 200, 120, 1) 0%, rgba(200, 16, 46, 0.1) 70%);
          opacity: 0;
          animation: nc-ember-rise 0.85s ease-out forwards;
        }

        @keyframes nc-ember-rise {
          0% {
            transform: translate(0, 0) scale(0.7);
            opacity: 0;
          }
          25% {
            opacity: 1;
          }
          100% {
            transform: translate(var(--dx, 0px), -54px) scale(1.1);
            opacity: 0;
          }
        }

        @media (max-width: 640px) {
          #nc-chat-panel {
            width: min(420px, 96vw);
            height: min(560px, 80vh);
            right: 12px;
            bottom: 90px;
          }
          #nc-chat-bubble {
            right: 12px;
            bottom: 16px;
          }
        }
      `;
      document.head.appendChild(css);
    }

    function createPanel() {
      if (document.getElementById("nc-chat-panel")) return;

      var panel = document.createElement("div");
      panel.id = "nc-chat-panel";

      var iframe = document.createElement("iframe");
      iframe.src = WIDGET_URL;
      iframe.title = "Novacool AI Assistant";
      iframe.loading = "lazy";

      panel.appendChild(iframe);
      document.body.appendChild(panel);
    }

    function createBubble() {
      if (document.getElementById("nc-chat-bubble")) return;

      var bubble = document.createElement("button");
      bubble.id = "nc-chat-bubble";
      bubble.type = "button";
      bubble.innerHTML = "<span>Ask<br/>Nova cool<br/>AI</span>";

      document.body.appendChild(bubble);
      return bubble;
    }

    function createHeaderCTA(openHandler) {
      var existing = document.getElementById("nc-header-cta");
      if (existing) return existing;

      var cta = document.createElement("button");
      cta.id = "nc-header-cta";
      cta.type = "button";
      cta.innerHTML = 'Ask Novacool AI<span>🔥</span>';

      cta.addEventListener("click", function () {
        if (typeof openHandler === "function") {
          openHandler();
        }
      });

      // Try to place inside a header if it exists, otherwise fixed
      var header =
        document.querySelector("header nav") ||
        document.querySelector("header .nav") ||
        document.querySelector("header");

      if (header && getComputedStyle(header).position !== "fixed") {
        // Inline in header
        cta.style.position = "relative";
        cta.style.top = "auto";
        cta.style.right = "auto";
        header.appendChild(cta);
      } else {
        // Fixed fallback
        document.body.appendChild(cta);
      }

      // Small delay then show to avoid layout popping
      setTimeout(function () {
        cta.classList.add("nc-visible");
      }, 600);

      return cta;
    }

    function togglePanel(forceOpen) {
      var panel = document.getElementById("nc-chat-panel");
      var bubble = document.getElementById("nc-chat-bubble");
      if (!panel || !bubble) return;

      var isOpen = panel.classList.contains("nc-open");
      var shouldOpen = forceOpen === true ? true : !isOpen;

      if (shouldOpen) {
        panel.classList.add("nc-open");
        bubble.classList.add("nc-open");
        spawnEmberBurst();
      } else {
        panel.classList.remove("nc-open");
        bubble.classList.remove("nc-open");
      }
    }

    function spawnEmberBurst() {
      var bubble = document.getElementById("nc-chat-bubble");
      if (!bubble) return;

      var rect = bubble.getBoundingClientRect();
      var baseX = rect.right - rect.width / 2;
      var baseY = rect.top + rect.height / 2;

      var count = 12 + Math.floor(Math.random() * 6);

      for (var i = 0; i < count; i++) {
        (function () {
          var ember = document.createElement("div");
          ember.className = "nc-ember";

          var offsetX = (Math.random() - 0.5) * 40; // spread left/right
          var delay = Math.random() * 0.18;

          ember.style.left = baseX + "px";
          ember.style.top = baseY + "px";
          ember.style.setProperty("--dx", offsetX + "px");
          ember.style.animationDelay = delay + "s";

          document.body.appendChild(ember);

          setTimeout(function () {
            if (ember && ember.parentNode) ember.parentNode.removeChild(ember);
          }, 1200);
        })();
      }
    }

    function setupAutoOpen() {
      try {
        if (sessionStorage.getItem(AUTO_OPEN_KEY) === "1") return;
      } catch (e) {
        // ignore sessionStorage failure
      }

      function onScroll() {
        if (window.scrollY < AUTO_OPEN_SCROLL_PX) return;

        togglePanel(true);
        spawnEmberBurst();

        try {
          sessionStorage.setItem(AUTO_OPEN_KEY, "1");
        } catch (e) {}

        window.removeEventListener("scroll", onScroll);
      }

      window.addEventListener("scroll", onScroll, { passive: true });
    }

    function init() {
      createStyles();
      createPanel();
      var bubble = createBubble();

      if (!bubble) return;

      bubble.addEventListener("click", function () {
        togglePanel();
      });

      bubble.addEventListener("mouseenter", function () {
        spawnEmberBurst();
      });

      createHeaderCTA(function () {
        togglePanel(true);
      });

      setupAutoOpen();

      // Signal that the widget is ready (for future integrations)
      try {
        var evt = new Event("NovacoolWidgetReady");
        document.dispatchEvent(evt);
      } catch (e) {
        // IE fallback if ever needed
        var ieEvt = document.createEvent("Event");
        ieEvt.initEvent("NovacoolWidgetReady", true, true);
        document.dispatchEvent(ieEvt);
      }
    }

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  })();
}
// === ENABLE CLOSE BUTTON FOR CHAT WIDGET ===
document.addEventListener("click", (e) => {
    const widget = document.querySelector(".novacool-chat-widget");
    const bubble = document.querySelector(".novacool-chat-bubble");

    // Close when "X" button pressed
    if (e.target.closest(".nc-close")) {
        widget.style.display = "none";
        bubble.style.display = "flex";
    }

    // Open when bubble pressed
    if (e.target.closest(".novacool-chat-bubble")) {
        widget.style.display = "flex";
        bubble.style.display = "none";
    }
});
