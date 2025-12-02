// Chatbot front-end logic for Kaloriz (vanilla JS)
// Connect in templates via: <script src="{% static 'js/chatbot.js' %}"></script>
(function () {
  const bubble = document.getElementById('kaloriz-chat-bubble');
  const widget = document.getElementById('kaloriz-chat-widget');
  const closeBtn = widget ? widget.querySelector('.chat-close') : null;
  const messagesEl = document.getElementById('kaloriz-chat-messages');
  const form = document.getElementById('kaloriz-chat-form');
  const input = document.getElementById('kaloriz-chat-input');
  const quickReplyContainer = document.querySelector('.chat-quick-replies');

  if (!bubble || !widget || !messagesEl || !form || !input) {
    return;
  }

  const quickReplies = [
    { label: 'Lacak pesanan', message: 'Lacak pesanan' },
    { label: 'Cara pemesanan', message: 'Cara pemesanan' },
    { label: 'Metode pembayaran', message: 'Metode pembayaran' },
    { label: 'Ongkir & pengiriman', message: 'Ongkir & pengiriman' },
    { label: 'Jam operasional', message: 'Jam operasional' },
    { label: 'Hubungi admin', message: 'Hubungi admin' },
  ];

  let initialized = false;
  let typingEl = null;

  function getCsrfToken() {
    if (typeof getCookie === 'function') {
      const token = getCookie('csrftoken');
      if (token) return token;
    }
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function renderQuickReplies() {
    if (!quickReplyContainer) return;
    quickReplyContainer.innerHTML = '';
    quickReplies.forEach(({ label, message }) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'quick-reply';
      button.dataset.message = message;
      button.textContent = label;
      quickReplyContainer.appendChild(button);
    });
  }

  function toggleWidget(show) {
    const shouldShow = typeof show === 'boolean' ? show : !widget.classList.contains('open');
    widget.classList.toggle('open', shouldShow);
    if (shouldShow && !initialized) {
      initialized = true;
      renderQuickReplies();
      addMessage('bot', 'Halo! Aku Asisten Kaloriz. Ada yang bisa aku bantu?');
    }
    if (shouldShow) {
      input.focus();
    }
  }

  function addMessage(sender, text) {
    const wrapper = document.createElement('div');
    wrapper.className = `chat-message ${sender}`;
    wrapper.textContent = text;
    messagesEl.appendChild(wrapper);
    scrollToBottom();
  }

  function showTyping() {
    if (typingEl) return;
    const indicator = document.createElement('div');
    indicator.className = 'chat-message bot';
    const dots = document.createElement('div');
    dots.className = 'typing-indicator';
    dots.innerHTML = '<span></span><span></span><span></span>';
    indicator.appendChild(dots);
    messagesEl.appendChild(indicator);
    typingEl = indicator;
    scrollToBottom();
  }

  function hideTyping() {
    if (typingEl) {
      typingEl.remove();
      typingEl = null;
    }
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function sendMessage(messageText) {
    if (!messageText) return;
    addMessage('user', messageText);
    showTyping();

    try {
      const response = await fetch('/chatbot/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': getCsrfToken(),
        },
        body: new URLSearchParams({ message: messageText }),
      });

      const data = await response.json();
      hideTyping();
      if (response.ok && data && data.reply) {
        addMessage('bot', data.reply);
      } else {
        addMessage('bot', 'Maaf, terjadi kesalahan mengambil balasan.');
      }
    } catch (error) {
      hideTyping();
      addMessage('bot', 'Jaringan bermasalah, silakan coba lagi.');
    }
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    sendMessage(text);
  });

  bubble.addEventListener('click', function () {
    toggleWidget();
  });

  bubble.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleWidget();
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', function () {
      toggleWidget(false);
    });
  }

  if (quickReplyContainer) {
    quickReplyContainer.addEventListener('click', function (event) {
      const target = event.target;
      if (target && target.classList.contains('quick-reply')) {
        const messageText = target.dataset.message || target.textContent;
        input.value = '';
        sendMessage(messageText.trim());
      }
    });
  }
})();
