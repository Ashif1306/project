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

  let initialized = false;
  let typingEl = null;

  function toggleWidget(show) {
    const shouldShow = typeof show === 'boolean' ? show : !widget.classList.contains('open');
    widget.classList.toggle('open', shouldShow);
    if (shouldShow && !initialized) {
      initialized = true;
      loadGreeting();
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

  async function loadGreeting() {
    showTyping();
    try {
      const response = await fetch('/chatbot/');
      const data = await response.json();
      hideTyping();
      if (data && data.reply) {
        addMessage('bot', data.reply);
      }
    } catch (error) {
      hideTyping();
      addMessage('bot', 'Maaf, terjadi masalah saat memulai percakapan.');
    }
  }

  async function sendMessage(messageText) {
    if (!messageText) return;
    addMessage('user', messageText);
    showTyping();

    try {
      const response = await fetch('/chatbot/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: messageText }),
      });

      const data = await response.json();
      hideTyping();
      if (data && data.reply) {
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

  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.dispatchEvent(new Event('submit'));
    }
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
