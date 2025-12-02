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
  const orderQuickReplyClass = 'order-quick-reply';
  const recommendedQuickActionClass = 'recommended-quick-action';
  const recommendedDefaults = ['Lacak pesanan', 'Hubungi admin', 'Cek metode pembayaran'];

  if (!bubble || !widget || !messagesEl || !form || !input) {
    return;
  }

  let initialized = false;
  let typingEl = null;

  function createBotAvatar() {
    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar-message';
    avatar.innerHTML = '<i class="fas fa-robot" aria-hidden="true"></i>';
    return avatar;
  }

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
    const row = document.createElement('div');
    row.className = `chat-row ${sender}`;

    if (sender === 'bot') {
      row.appendChild(createBotAvatar());
    }

    const bubble = document.createElement('div');
    bubble.className = `chat-message ${sender} fade-in`;
    bubble.textContent = text;
    row.appendChild(bubble);

    messagesEl.appendChild(row);
    scrollToBottom();
  }

  function showTyping() {
    if (typingEl) return;

    const row = document.createElement('div');
    row.className = 'chat-row bot typing-row';
    row.appendChild(createBotAvatar());

    const bubble = document.createElement('div');
    bubble.className = 'chat-message bot';

    const typingWrap = document.createElement('div');
    typingWrap.className = 'typing-indicator';

    const typingText = document.createElement('div');
    typingText.className = 'typing-text';
    typingText.textContent = 'Asisten Kaloriz sedang mengetik…';

    const dots = document.createElement('div');
    dots.className = 'typing-dots';
    dots.innerHTML = '<span></span><span></span><span></span>';

    typingWrap.appendChild(typingText);
    typingWrap.appendChild(dots);
    bubble.appendChild(typingWrap);
    row.appendChild(bubble);

    messagesEl.appendChild(row);
    typingEl = row;
    scrollToBottom();
  }

  function hideTyping() {
    if (typingEl) {
      typingEl.remove();
      typingEl = null;
    }
  }

  function clearOrderButtons() {
    if (!quickReplyContainer) return;
    quickReplyContainer
      .querySelectorAll(`.${orderQuickReplyClass}`)
      .forEach((btn) => btn.remove());
  }

  function renderRecommendedQuickActions(labels) {
    if (!quickReplyContainer) return;

    const actions = Array.isArray(labels) && labels.length ? labels : recommendedDefaults;
    quickReplyContainer
      .querySelectorAll(`.${recommendedQuickActionClass}`)
      .forEach((btn) => btn.remove());

    const existingButtons = Array.from(quickReplyContainer.querySelectorAll('.quick-reply'));
    const firstStaticButton = existingButtons.find((btn) => !btn.classList.contains(orderQuickReplyClass));

    actions.forEach((action) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `quick-reply ${recommendedQuickActionClass}`;
      btn.dataset.message = action;
      btn.textContent = action;

      if (firstStaticButton) {
        quickReplyContainer.insertBefore(btn, firstStaticButton);
      } else {
        quickReplyContainer.appendChild(btn);
      }
    });
  }

  // Render daftar pesanan dari response.orders sebagai quick reply tambahan
  function renderOrderButtons(orders) {
    if (!quickReplyContainer || !Array.isArray(orders)) return;
    clearOrderButtons();

    orders.forEach((order) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `quick-reply ${orderQuickReplyClass}`;
      btn.dataset.orderCode = order.code;
      btn.textContent = `${order.code} - ${order.date} - ${order.status}`;
      quickReplyContainer.appendChild(btn);
    });
  }

  function handleBotResponse(data) {
    if (data && data.reply) {
      addMessage('bot', data.reply);
    } else {
      addMessage('bot', 'Maaf, terjadi kesalahan mengambil balasan.');
    }

    renderRecommendedQuickActions(data && data.quick_actions);

    if (data && Array.isArray(data.orders)) {
      // Tangani daftar pesanan yang dikirim backend untuk ditampilkan sebagai tombol
      renderOrderButtons(data.orders);
    } else {
      clearOrderButtons();
    }
  }

  function scrollToBottom() {
    try {
      messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
    } catch (err) {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
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
      renderRecommendedQuickActions(data && data.quick_actions);
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
      handleBotResponse(data);
    } catch (error) {
      hideTyping();
      addMessage('bot', 'Jaringan bermasalah, silakan coba lagi.');
    }
  }

  // Mengirim request action "track_order" saat user klik tombol pesanan
  async function sendTrackOrder(orderCode, labelText) {
    if (!orderCode) return;

    const displayText = labelText || orderCode;
    addMessage('user', displayText);
    showTyping();

    try {
      const response = await fetch('/chatbot/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'track_order', order_code: orderCode }),
      });

      const data = await response.json();
      hideTyping();
      handleBotResponse(data);
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
        if (target.classList.contains(orderQuickReplyClass) && target.dataset.orderCode) {
          const label = target.textContent.trim();
          sendTrackOrder(target.dataset.orderCode, label);
          return;
        }
        const messageText = target.dataset.message || target.textContent;
        input.value = '';
        sendMessage(messageText.trim());
      }
    });
  }
})();
