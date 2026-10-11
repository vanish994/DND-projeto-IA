const STORAGE_KEY = 'dnd-mj-sessao';
const messages = document.querySelector('#messages');
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');
const newSessionButton = document.querySelector('#new-session');
const sessionLabel = document.querySelector('#session-label');

function sessionId() {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = `campanha-${crypto.randomUUID().slice(0, 8)}`;
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}

function addMessage(role, text) {
  const article = document.createElement('article');
  article.className = `message message-${role}`;
  article.innerHTML = `<div class="avatar">${role === 'mj' ? 'MJ' : 'VOCÊ'}</div><div class="bubble"></div>`;
  article.querySelector('.bubble').textContent = text;
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function setSessionLabel() {
  sessionLabel.textContent = sessionId();
}

async function sendMessage(text) {
  addMessage('user', text);
  sendButton.disabled = true;
  input.disabled = true;
  const typing = document.createElement('article');
  typing.className = 'message message-mj typing';
  typing.innerHTML = '<div class="avatar">MJ</div><div class="bubble">O MJ está pensando...</div>';
  messages.append(typing);
  messages.scrollTop = messages.scrollHeight;
  try {
    const response = await fetch('/v1/mj/mensagem', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({sessao_id: sessionId(), mensagem: text}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Não foi possível consultar o MJ.');
    typing.remove();
    addMessage('mj', data.resposta);
  } catch (error) {
    typing.remove();
    addMessage('mj', `Não consegui consultar o MJ agora. ${error.message}`);
  } finally {
    sendButton.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || sendButton.disabled) return;
  input.value = '';
  sendMessage(text);
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

newSessionButton.addEventListener('click', async () => {
  const oldId = sessionId();
  try { await fetch(`/v1/mj/sessoes/${encodeURIComponent(oldId)}`, {method: 'DELETE'}); } catch (_) {}
  localStorage.removeItem(STORAGE_KEY);
  messages.innerHTML = '<article class="message message-mj"><div class="avatar">MJ</div><div class="bubble"><p>Uma nova mesa se abre. Onde começa a sua história?</p></div></article>';
  setSessionLabel();
  input.focus();
});

setSessionLabel();
