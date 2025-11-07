const messagesDiv = document.getElementById('messages');
const input = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');

// Add a message to the chat
function addMessage(text, sender) {
  const msg = document.createElement('div');
  msg.classList.add('message', sender);
  msg.textContent = text;
  messagesDiv.appendChild(msg);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Send the user's message to the backend
async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;
  addMessage(message, 'user');
  input.value = '';

  try {
    const res = await fetch("https://novacool-rag.onrender.com/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text}`);
    }

    const data = await res.json();
    addMessage(data.reply || data.error || 'No response.', 'bot');
  } catch (err) {
    addMessage('Error: ' + err.message, 'bot');
  }
}

// Event listeners
sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keypress', e => {
  if (e.key === 'Enter') sendMessage();
});

// ✅ Display a friendly greeting when widget loads
window.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    addMessage("👋 Hi there! I'm the Novacool Assistant — ask me about UEF mix rates, certifications, or environmental data.", "bot");
  }, 500);
});
