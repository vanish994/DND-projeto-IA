const JOGADOR_KEY = 'dnd-mj-jogador';
const ULTIMA_KEY = 'dnd-mj-ultima-campanha';
const RASCUNHOS_KEY = 'dnd-mj-rascunhos';
const LEGADO_KEY = 'dnd-mj-sessao';

const app = document.querySelector('#app');
const list = document.querySelector('#campaign-list');
const listStatus = document.querySelector('#campaigns-status');
const newCampaignButton = document.querySelector('#new-campaign');
const backButton = document.querySelector('#back-button');
const optionsButton = document.querySelector('#options-button');
const mapButton = document.querySelector('#map-button');
const helpButton = document.querySelector('#help-button');
const title = document.querySelector('#campaign-title');
const messages = document.querySelector('#messages');
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');
const scrollBottom = document.querySelector('#scroll-bottom');
const anuncios = document.querySelector('#anuncios');
const avisos = document.querySelector('#avisos');
const optionsDialog = document.querySelector('#options-dialog');
const renameInput = document.querySelector('#rename-input');
const helpDialog = document.querySelector('#help-dialog');
const desktop = window.matchMedia('(min-width: 900px)');
// Animação de dados do motor (frontend/dado.js). Sem o módulo, tudo continua funcionando.
const Dados = window.Dados || {animar: async () => [], cartao: () => null, interromper() {}, frase: () => ''};

const state = {
  campanhas: [],
  atual: null,
  pendentes: new Set(),
  rascunhos: lerJson(RASCUNHOS_KEY, {}),
};

function lerJson(chave, padrao) {
  try { return JSON.parse(localStorage.getItem(chave)) ?? padrao; } catch (_) { return padrao; }
}

function jogadorId() {
  let id = localStorage.getItem(JOGADOR_KEY);
  if (!id) {
    id = `jogador-${crypto.randomUUID()}`;
    localStorage.setItem(JOGADOR_KEY, id);
  }
  return id;
}

async function api(caminho, opcoes = {}) {
  const resposta = await fetch(caminho, {
    ...opcoes,
    headers: {'Content-Type': 'application/json', 'X-Jogador-Id': jogadorId(), ...(opcoes.headers || {})},
  });
  if (resposta.status === 204) return null;
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const detalhe = typeof dados.detail === 'string' ? dados.detail : 'Erro inesperado.';
    throw Object.assign(new Error(detalhe), {status: resposta.status});
  }
  return dados;
}

function salvarRascunhos() {
  localStorage.setItem(RASCUNHOS_KEY, JSON.stringify(state.rascunhos));
}

function guardarRascunhoAtual() {
  if (!state.atual) return;
  const texto = input.value;
  if (texto.trim()) state.rascunhos[state.atual] = texto;
  else delete state.rascunhos[state.atual];
  salvarRascunhos();
}

function campanha(id) {
  return state.campanhas.find((c) => c.id === id);
}

function dataRelativa(iso) {
  const data = new Date(iso);
  const dias = Math.floor((Date.now() - data.getTime()) / 86400000);
  if (dias <= 0) return `hoje, ${data.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}`;
  if (dias === 1) return 'ontem';
  if (dias < 7) return `há ${dias} dias`;
  return data.toLocaleDateString('pt-BR', {day: '2-digit', month: 'short'});
}

function resumo(texto) {
  if (!texto) return 'Ainda não há mensagens.';
  const limpo = texto.replace(/\s+/g, ' ').trim();
  return limpo.length > 90 ? `${limpo.slice(0, 90)}…` : limpo;
}

function setView(view) {
  app.dataset.view = view;
}

/** Aviso flutuante não bloqueante (erros de lista, renomear, apagar). */
function avisar(texto, tipo = 'erro') {
  if (!avisos) return;
  const caixa = document.createElement('div');
  caixa.className = `aviso aviso-${tipo}`;
  caixa.textContent = texto;
  avisos.append(caixa);
  setTimeout(() => caixa.classList.add('saindo'), 4600);
  setTimeout(() => caixa.remove(), 5200);
}

function anunciar(texto) {
  if (anuncios) anuncios.textContent = texto;
}

function renderList() {
  list.replaceChildren();
  if (!state.campanhas.length) {
    listStatus.textContent = 'Nenhuma campanha ainda. Crie a primeira para começar.';
    return;
  }
  listStatus.textContent = '';
  for (const c of state.campanhas) {
    const item = document.createElement('li');
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'campaign-card';
    botao.dataset.id = c.id;
    if (c.id === state.atual) botao.setAttribute('aria-current', 'true');
    botao.innerHTML = '<span class="card-top"><strong class="card-title"></strong><span class="card-date"></span></span><span class="card-preview"></span><span class="card-foot"><span class="card-count"></span><span class="card-action">Retomar campanha</span></span>';
    botao.querySelector('.card-title').textContent = c.titulo;
    botao.querySelector('.card-date').textContent = dataRelativa(c.atualizada_em);
    botao.querySelector('.card-preview').textContent = state.pendentes.has(c.id) ? 'O MJ está respondendo…' : resumo(c.ultima_mensagem);
    botao.querySelector('.card-count').textContent = c.total_mensagens
      ? `${c.total_mensagens} ${c.total_mensagens === 1 ? 'mensagem' : 'mensagens'}` : 'Nova campanha';
    botao.addEventListener('click', () => abrirCampanha(c.id));
    item.append(botao);
    list.append(item);
  }
}

function atualizarCampanha(dados) {
  state.campanhas = [dados, ...state.campanhas.filter((c) => c.id !== dados.id)];
  renderList();
}

// Dados e CDs citados na narração ganham destaque visual; o texto não é alterado.
const PADRAO_DADOS = /(\d*d(\d+)(?:\s*[+\-−]\s*\d+)?)|(CD\s*\d+)/gi;

function textoComDados(texto) {
  const fragmento = document.createDocumentFragment();
  let ultimo = 0;
  for (const ocorrencia of String(texto).matchAll(PADRAO_DADOS)) {
    if (ocorrencia.index > ultimo) fragmento.append(String(texto).slice(ultimo, ocorrencia.index));
    const chip = document.createElement('span');
    chip.className = 'chip chip-dado';
    if (ocorrencia[2]) chip.dataset.lados = ocorrencia[2];
    const icone = document.createElement('span');
    icone.className = 'dado-icone';
    icone.setAttribute('aria-hidden', 'true');
    chip.append(icone, document.createTextNode(ocorrencia[0].trim()));
    fragmento.append(chip);
    ultimo = ocorrencia.index + ocorrencia[0].length;
  }
  fragmento.append(String(texto).slice(ultimo));
  return fragmento;
}

function addMessage(papel, texto, extraClass = '', rolagens = []) {
  messages.querySelector('.empty-state')?.remove();
  const role = papel === 'user' ? 'user' : 'mj';
  const article = document.createElement('article');
  article.className = `message message-${role} ${extraClass}`.trim();
  article.innerHTML = `<div class="avatar" aria-hidden="true">${role === 'mj' ? 'MJ' : 'VC'}</div><div class="bubble"><span class="visually-hidden">${role === 'mj' ? 'MJ:' : 'Você:'}</span><span class="bubble-text"></span></div>`;
  article.querySelector('.bubble-text').replaceChildren(textoComDados(texto));
  const cartao = Dados.cartao ? Dados.cartao(rolagens) : null;
  if (cartao) article.querySelector('.bubble').append(cartao);
  messages.append(article);
  rolarParaOFim();
  return article;
}

function renderEmpty(texto, comDado = false) {
  messages.replaceChildren();
  const p = document.createElement('p');
  p.className = 'empty-state';
  if (comDado) {
    const glifo = document.createElement('span');
    glifo.className = 'empty-die';
    glifo.setAttribute('aria-hidden', 'true');
    glifo.textContent = '20';
    p.append(glifo);
  }
  p.append(document.createTextNode(texto));
  messages.append(p);
}

function addTyping() {
  messages.querySelector('.empty-state')?.remove();
  const article = document.createElement('article');
  article.className = 'message message-mj typing';
  article.innerHTML = '<div class="avatar" aria-hidden="true">MJ</div><div class="bubble"><span class="visually-hidden">O MJ está pensando…</span><span class="typing-dots" aria-hidden="true"><i></i><i></i><i></i></span></div>';
  messages.append(article);
  rolarParaOFim();
  return article;
}

function rolarParaOFim() {
  messages.scrollTop = messages.scrollHeight;
  atualizarBotaoDeRolagem();
}

function atualizarBotaoDeRolagem() {
  if (!scrollBottom) return;
  const distancia = messages.scrollHeight - messages.scrollTop - messages.clientHeight;
  scrollBottom.hidden = distancia < 220;
}

async function animarRolagens(rolagens) {
  if (!rolagens || !rolagens.length) return;
  const id = state.atual;
  await Dados.animar(rolagens, {maximo: 3});
  if (state.atual === id) anunciar(rolagens.map((rolagem) => Dados.frase(rolagem)).join(' '));
  atualizarBotaoDeRolagem();
}

function atualizarComposer() {
  const ocupado = !state.atual || state.pendentes.has(state.atual);
  input.disabled = !state.atual;
  sendButton.disabled = ocupado;
  sendButton.textContent = state.atual && state.pendentes.has(state.atual) ? 'Aguarde' : 'Enviar';
  optionsButton.disabled = !state.atual;
  mapButton.disabled = !state.atual;
}

function autoResize() {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  input.style.overflowY = input.scrollHeight > 160 ? 'auto' : 'hidden';
}

async function abrirCampanha(id) {
  guardarRascunhoAtual();
  state.atual = id;
  localStorage.setItem(ULTIMA_KEY, id);
  const c = campanha(id);
  title.textContent = c ? c.titulo : 'Carregando…';
  input.value = state.rascunhos[id] || '';
  autoResize();
  atualizarComposer();
  renderList();
  setView('conversa');
  renderEmpty('Carregando a campanha…');
  try {
    const detalhe = await api(`/v1/campanhas/${encodeURIComponent(id)}`);
    if (state.atual !== id) return;
    title.textContent = detalhe.titulo;
    messages.replaceChildren();
    if (!detalhe.mensagens.length) renderEmpty('Ainda não há mensagens. Conte onde a cena começa.', true);
    for (const m of detalhe.mensagens) addMessage(m.papel, m.conteudo, '', m.rolagens || []);
    if (state.pendentes.has(id)) addTyping();
    rolarParaOFim();
  } catch (erro) {
    if (state.atual !== id) return;
    if (erro.status === 404) {
      state.campanhas = state.campanhas.filter((x) => x.id !== id);
      fecharCampanha();
      listStatus.textContent = 'Essa campanha não existe mais.';
      return;
    }
    renderEmpty('Não foi possível carregar esta campanha. Tente novamente; seu histórico salvo não foi alterado.');
  }
  if (desktop.matches || document.activeElement === document.body) input.focus({preventScroll: true});
  atualizarBotaoDeRolagem();
}

function fecharCampanha() {
  guardarRascunhoAtual();
  Dados.interromper();
  state.atual = null;
  localStorage.removeItem(ULTIMA_KEY);
  title.textContent = 'Nenhuma campanha aberta';
  input.value = '';
  renderEmpty('Escolha uma campanha ou crie uma nova para começar.');
  atualizarComposer();
  renderList();
  setView('inicio');
}

async function enviar(texto) {
  const id = state.atual;
  state.pendentes.add(id);
  delete state.rascunhos[id];
  salvarRascunhos();
  const enviada = addMessage('user', texto);
  const typing = addTyping();
  atualizarComposer();
  renderList();
  try {
    const dados = await api(`/v1/campanhas/${encodeURIComponent(id)}/mensagens`, {
      method: 'POST',
      body: JSON.stringify({mensagem: texto}),
    });
    state.pendentes.delete(id);
    atualizarCampanha(dados.campanha);
    if (state.atual === id) {
      typing.remove();
      // O dado do motor aparece antes da narração: o valor auditável é
      // apresentado primeiro e o MJ descreve a consequência depois.
      await animarRolagens(dados.rolagens || []);
      if (state.atual === id) addMessage('assistant', dados.resposta, '', dados.rolagens || []);
    }
  } catch (erro) {
    state.pendentes.delete(id);
    if (!state.rascunhos[id]) {
      state.rascunhos[id] = texto;
      salvarRascunhos();
    }
    if (state.atual === id) {
      typing.remove();
      enviada.remove();
      if (!input.value.trim()) input.value = texto;
      autoResize();
      addMessage('assistant', `Não foi possível falar com o MJ agora (${erro.message}). Sua mensagem não foi salva e voltou para o campo de texto.`, 'message-error');
    }
    renderList();
  } finally {
    atualizarComposer();
    if (state.atual === id) input.focus({preventScroll: true});
  }
}

async function carregarCampanhas() {
  listStatus.textContent = 'Carregando campanhas…';
  try {
    state.campanhas = await api('/v1/campanhas');
    renderList();
    return true;
  } catch (_) {
    listStatus.textContent = 'Não foi possível carregar as campanhas. Verifique a conexão e recarregue a página.';
    return false;
  }
}

newCampaignButton.addEventListener('click', async () => {
  newCampaignButton.disabled = true;
  try {
    const nova = await api('/v1/campanhas', {method: 'POST', body: JSON.stringify({})});
    atualizarCampanha(nova);
    await abrirCampanha(nova.id);
  } catch (erro) {
    avisar(`Não foi possível criar a campanha. ${erro.message}`);
  } finally {
    newCampaignButton.disabled = false;
  }
});

backButton.addEventListener('click', () => {
  guardarRascunhoAtual();
  setView('inicio');
  newCampaignButton.focus({preventScroll: true});
});

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const texto = input.value.trim();
  if (!texto || !state.atual || state.pendentes.has(state.atual)) return;
  input.value = '';
  autoResize();
  enviar(texto);
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && desktop.matches) {
    event.preventDefault();
    form.requestSubmit();
  }
});

input.addEventListener('input', () => {
  autoResize();
  guardarRascunhoAtual();
});

messages.addEventListener('scroll', atualizarBotaoDeRolagem);
scrollBottom?.addEventListener('click', () => {
  messages.scrollTo({top: messages.scrollHeight, behavior: 'smooth'});
  input.focus({preventScroll: true});
});

optionsButton.addEventListener('click', () => {
  const c = campanha(state.atual);
  renameInput.value = c ? c.titulo : title.textContent;
  optionsDialog.showModal();
});

optionsDialog.addEventListener('close', async () => {
  const id = state.atual;
  const acao = optionsDialog.returnValue;
  optionsDialog.returnValue = '';
  if (!id) return;
  try {
    if (acao === 'rename') {
      const nome = renameInput.value.trim();
      if (!nome) return;
      const dados = await api(`/v1/campanhas/${encodeURIComponent(id)}`, {method: 'PATCH', body: JSON.stringify({titulo: nome})});
      atualizarCampanha(dados);
      if (state.atual === id) title.textContent = dados.titulo;
    } else if (acao === 'delete') {
      const c = campanha(id);
      if (!window.confirm(`Apagar "${c ? c.titulo : 'esta campanha'}" e todo o histórico?`)) return;
      await api(`/v1/campanhas/${encodeURIComponent(id)}`, {method: 'DELETE'});
      state.campanhas = state.campanhas.filter((x) => x.id !== id);
      delete state.rascunhos[id];
      salvarRascunhos();
      fecharCampanha();
    }
  } catch (erro) {
    avisar(`Não foi possível concluir a ação. ${erro.message}`);
  }
});

mapButton.addEventListener('click', () => {
  if (!state.atual) return;
  window.location.href = `/mapa-tatico.html?campanha=${encodeURIComponent(state.atual)}`;
});

helpButton.addEventListener('click', () => helpDialog.showModal());

if (window.visualViewport) {
  const ajustarAltura = () => {
    document.documentElement.style.setProperty('--app-height', `${window.visualViewport.height}px`);
    if (document.activeElement === input) rolarParaOFim();
  };
  document.documentElement.classList.add('has-visual-viewport');
  window.visualViewport.addEventListener('resize', ajustarAltura);
  ajustarAltura();
}

(async function iniciar() {
  localStorage.removeItem(LEGADO_KEY);
  autoResize();
  atualizarComposer();
  if (!(await carregarCampanhas())) return;
  const ultima = localStorage.getItem(ULTIMA_KEY);
  if (desktop.matches && ultima && campanha(ultima)) abrirCampanha(ultima);
})();
