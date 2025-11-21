/* NOVACOOL Chat UI — React Webapp Loader */

const container = document.getElementById("novacool-window");
if (container) {
  container.innerHTML = `
    <iframe
      src="https://novacool-rag.onrender.com/chat"
      style="width:100%; height:100%; border:none;"
    ></iframe>
  `;
}
