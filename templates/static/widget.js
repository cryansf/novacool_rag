<!-- 🌊 Novacool AI Assistant Floating Chat Bubble (Auto-Greeting Enabled) -->
<style>
  #novaChatBtn {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 62px;
    height: 62px;
    border-radius: 50%;
    background-color: #0066cc;
    box-shadow: 0 4px 10px rgba(0,0,0,0.25);
    color: #fff;
    border: none;
    cursor: pointer;
    font-size: 28px;
    font-weight: bold;
    z-index: 100000;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s ease, transform 0.2s ease;
    animation: pulseGlow 4s ease-in-out infinite;
  }
  #novaChatBtn:hover { background-color: #0052a3; transform: scale(1.08); }

  @keyframes pulseGlow {
    0% { box-shadow: 0 0 0 rgba(0,102,204,0.6); }
    50% { box-shadow: 0 0 20px rgba(0,102,204,0.7); }
    100% { box-shadow: 0 0 0 rgba(0,102,204,0.6); }
  }

  #novaChatFrame {
    position: fixed;
    bottom: 100px;
    right: 24px;
    width: 380px;
    height: 520px;
    border: none;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    display: none !important;
    z-index: 99999 !important;
    background: #fff;
  }
  #novaChatFrame.active { display: block !important; }

  @media (max-width: 600px) {
    #novaChatFrame {
      width: 90vw;
      height: 75vh;
      right: 5vw;
      bottom: 90px;
    }
  }

  #novaGreeting {
    position: fixed;
    bottom: 100px;
    right: 95px;
    background: #fff;
    color: #222;
    font-size: 15px;
    padding: 10px 14px;
    border-radius: 12px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.25);
    max-width: 240px;
    opacity: 0;
    transform: translateY(10px);
    transition: opacity 0.5s ease, transform 0.5s ease;
    z-index: 99998;
  }
  #novaGreeting.show { opacity: 1; transform: translateY(0); }
</style>

<button id="novaChatBtn" title="Chat with Novacool">💬</button>
<div id="novaGreeting">👋 Need help? Ask about Novacool!</div>

<iframe
  id="novaChatFrame"
  src="https://novacool-rag.onrender.com/widget"
  allow="microphone; clipboard-read; clipboard-write; autoplay; fullscreen; encrypted-media"
  sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
  title="Novacool AI Assistant"
  onload="setTimeout(() => this.contentWindow.postMessage({type:'novaChatInit'}, '*'), 1000)"
></iframe>

<script>
  const chatBtn = document.getElementById("novaChatBtn");
  const chatFrame = document.getElementById("novaChatFrame");
  const greeting = document.getElementById("novaGreeting");

  // Restore state
  let chatOpen = localStorage.getItem("novaChatOpen") === "true";
  if (chatOpen) {
    chatFrame.classList.add("active");
    chatBtn.textContent = "✖";
  }

  // Toggle chat visibility
  chatBtn.addEventListener("click", () => {
    chatOpen = !chatOpen;
    if (chatOpen) {
      chatFrame.classList.add("active");
      chatBtn.textContent = "✖";
      greeting.style.display = "none";

      // Force reload & show welcome message inside iframe
      chatFrame.src = chatFrame.src;
      setTimeout(() => {
        chatFrame.contentWindow.postMessage({
          type: "novaChatInitMessage",
          text: "👋 Hi there! I'm the Novacool Assistant — ask me about UEF mix rates, certifications, or environmental data."
        }, "*");
      }, 2000);
    } else {
      chatFrame.classList.remove("active");
      chatBtn.textContent = "💬";
    }
    localStorage.setItem("novaChatOpen", chatOpen);
  });

  // Timed external greeting bubble
  setTimeout(() => {
    if (!chatOpen && !localStorage.getItem("novaGreetingDismissed")) {
      greeting.classList.add("show");
      setTimeout(() => greeting.classList.remove("show"), 8000);
      localStorage.setItem("novaGreetingDismissed", "true");
    }
  }, 5000);
</script>
