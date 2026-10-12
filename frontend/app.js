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
const confirmDialog = document.querySelector('#confirm-dialog');
const confirmText = document.querySelector('#confirm-text');
const desktop = window.matchMedia('(min-width: 900px)');
// Animação de dados do motor (frontend/dado.js). Sem o módulo, tudo continua funcionando.
const Dados = window.Dados || {animar: async () => [], cartao: () => null, interromper() {}, frase: () => ''};

// Campanha aguardando a confirmação de exclusão no diálogo.
let campanhaParaApagar = null;

const state = {
  campanhas: [],
  atual: null,
  pendentes: new Set(),
  rascunhos: lerJson(RASCUNHOS_KEY, {}),
  // Mensagens que chegaram enquanto o leitor estava no meio do histórico.
  novas: 0,
};

const enviosPendentes = new EnviosPendentes(localStorage);
// Um fechamento de aba depois do POST não pode perder o texto/chave do envio.
for (const [id, op] of Object.entries(enviosPendentes.listar())) {
  if (!state.rascunhos[id]) state.rascunhos[id] = op.texto;
}

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

function addMessage(papel, texto, extraClass = '', rolagens = [], criadaEm = null) {
  messages.querySelector('.empty-state')?.remove();
  // Decidido antes de inserir: só desce sozinho quem já estava acompanhando.
  const acompanhando = estaAcompanhando();
  marcarDia(criadaEm);
  const role = papel === 'user' ? 'user' : 'mj';
  const article = document.createElement('article');
  article.className = `message message-${role} ${extraClass}`.trim();
  article.innerHTML = `<div class="avatar" aria-hidden="true">${role === 'mj' ? 'MJ' : 'VC'}</div><div class="bubble"><span class="visually-hidden">${role === 'mj' ? 'MJ:' : 'Você:'}</span><span class="bubble-text"></span></div>`;
  article.querySelector('.bubble-text').replaceChildren(textoComDados(texto));
  const cartao = Dados.cartao ? Dados.cartao(rolagens) : null;
  if (cartao) article.querySelector('.bubble').append(cartao);
  if (role === 'mj' && !extraClass) {
    const opcoes = escolhasNarrativas(texto);
    if (opcoes.length) {
      const escolhas = document.createElement('section');
      escolhas.className = 'narrative-choices';
      escolhas.setAttribute('aria-label', 'Escolha o que fazer');
      const heading = document.createElement('h3');
      heading.textContent = '✧ Escolha o que fazer';
      escolhas.append(heading);
      for (const [index, opcao] of opcoes.entries()) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'narrative-choice';
        const number = document.createElement('span');
        number.className = 'choice-number';
        number.textContent = String(index + 1).padStart(2, '0');
        const label = document.createElement('span');
        label.textContent = opcao;
        const arrow = document.createElement('span');
        arrow.textContent = '›';
        arrow.setAttribute('aria-hidden', 'true');
        button.append(number, label, arrow);
        button.addEventListener('click', () => {
          if (!state.atual || state.pendentes.has(state.atual)) return;
          input.value = opcao;
          autoResize();
          guardarRascunhoAtual();
          input.focus({preventScroll: true});
          anunciar('Escolha preenchida. Você pode editar antes de enviar.');
        });
        escolhas.append(button);
      }
      const hint = document.createElement('p');
      hint.className = 'choice-hint';
      hint.textContent = 'Selecione para editar e enviar, ou escreva sua própria ação.';
      escolhas.append(hint);
      article.querySelector('.bubble').append(escolhas);
    }
  }
  messages.append(article);
  atualizarEscolhas();
  if (acompanhando || papel === 'user') rolarParaOFim();
  else {
    state.novas += 1;
    atualizarBotaoDeRolagem();
  }
  return article;
}

function renderEmpty(texto, comDado = false) {
  messages.replaceChildren();
  messages.dataset.dia = '';
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

// Quanto o leitor pode estar longe do fim e ainda querer acompanhar a conversa.
const LIMITE_PARA_ACOMPANHAR = 220;

function distanciaDoFim() {
  return messages.scrollHeight - messages.scrollTop - messages.clientHeight;
}

function estaAcompanhando() {
  return distanciaDoFim() < LIMITE_PARA_ACOMPANHAR;
}

function rolarParaOFim() {
  messages.scrollTop = messages.scrollHeight;
  state.novas = 0;
  atualizarBotaoDeRolagem();
}

function atualizarBotaoDeRolagem() {
  if (!scrollBottom) return;
  const mostrar = !estaAcompanhando();
  scrollBottom.hidden = !mostrar;
  // Ler o histórico não pode custar o aviso de que chegou coisa nova.
  scrollBottom.dataset.novas = state.novas ? String(state.novas) : '';
  scrollBottom.setAttribute(
    'aria-label',
    state.novas
      ? `Ir para as mensagens mais recentes (${state.novas} nova${state.novas > 1 ? 's' : ''})`
      : 'Ir para as mensagens mais recentes',
  );
}

function aoRolarConversa() {
  if (estaAcompanhando()) state.novas = 0;
  atualizarBotaoDeRolagem();
}

/* Marca o dia da conversa: "Hoje", "Ontem" ou a data, quando o dia muda. */
function diaDe(iso) {
  const data = iso ? new Date(iso) : new Date();
  return Number.isNaN(data.getTime()) ? null : data.toDateString();
}

function rotuloDoDia(iso) {
  const data = new Date(iso);
  const hoje = new Date();
  const ontem = new Date(hoje);
  ontem.setDate(hoje.getDate() - 1);
  if (data.toDateString() === hoje.toDateString()) return 'Hoje';
  if (data.toDateString() === ontem.toDateString()) return 'Ontem';
  return data.toLocaleDateString('pt-BR', {day: '2-digit', month: 'long'});
}

function marcarDia(criadaEm) {
  const dia = diaDe(criadaEm);
  if (!dia || dia === messages.dataset.dia) return;
  messages.dataset.dia = dia;
  const separador = document.createElement('p');
  separador.className = 'separador-dia';
  separador.setAttribute('role', 'presentation');
  separador.textContent = rotuloDoDia(criadaEm);
  messages.append(separador);
}

async function animarRolagens(rolagens) {
  if (!rolagens || !rolagens.length) return;
  const id = state.atual;
  await Dados.animar(rolagens, {maximo: 3});
  if (state.atual === id) anunciar(rolagens.map((rolagem) => Dados.frase(rolagem)).join(' '));
  atualizarBotaoDeRolagem();
}

function atualizarEscolhas() {
  const ultima = messages.querySelector('.message:last-child');
  messages.querySelectorAll('.narrative-choice').forEach((button) => {
    button.disabled = !state.atual || state.pendentes.has(state.atual) || button.closest('.message') !== ultima;
  });
}

function atualizarComposer() {
  atualizarEscolhas();
  const ocupado = !state.atual || state.pendentes.has(state.atual);
  input.disabled = !state.atual;
  sendButton.disabled = ocupado;
  sendButton.textContent = state.atual && state.pendentes.has(state.atual) ? 'Aguarde' : 'Enviar';
  optionsButton.disabled = !state.atual;
}

function autoResize() {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  input.style.overflowY = input.scrollHeight > 160 ? 'auto' : 'hidden';
}

async function abrirCampanha(id, mostrarEnvioPendente = true) {
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
    messages.dataset.dia = '';
    state.novas = 0;
    if (!detalhe.mensagens.length) renderEmpty('Ainda não há mensagens. Conte onde a cena começa.', true);
    for (const m of detalhe.mensagens) addMessage(m.papel, m.conteudo, '', m.rolagens || [], m.criada_em);
    if (mostrarEnvioPendente && state.pendentes.has(id)) addTyping();
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
  if (!id || state.pendentes.has(id)) return;
  let operacao;
  try {
    operacao = enviosPendentes.preparar(id, texto);
  } catch (_) {
    input.value = texto;
    autoResize();
    avisar('Não foi possível guardar o identificador do envio neste navegador. Nenhuma mensagem foi enviada.');
    return;
  }
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
      body: JSON.stringify({mensagem: texto, operacao_id: operacao.id}),
    });
    atualizarCampanha(dados.campanha);
    if (state.atual === id) {
      typing.remove();
      // O dado do motor aparece antes da narração: o valor auditável é
      // apresentado primeiro e o MJ descreve a consequência depois.
      await animarRolagens(dados.rolagens || []);
      if (state.atual === id) {
        if (operacao.repeticao) {
          // O histórico pode já conter a resposta cujo HTTP se perdeu.
          // Recarregar a versão canônica evita duplicar bolhas no navegador.
          await abrirCampanha(id, false);
        } else {
          addMessage('assistant', dados.resposta, '', dados.rolagens || []);
        }
      }
    }
    try { enviosPendentes.confirmar(id, operacao.id); }
    catch (_) { /* Manter a chave é seguro: a próxima repetição será deduplicada. */ }
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
      addMessage('assistant', `Não foi possível falar com o MJ agora (${erro.message}). Não foi possível confirmar o resultado. O texto está no campo; reenvie sem editar para recuperar o mesmo envio sem repetir a ação. Se editar, será uma nova operação.`, 'message-error');
    }
    renderList();
  } finally {
    state.pendentes.delete(id);
    renderList();
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

messages.addEventListener('scroll', aoRolarConversa);
scrollBottom?.addEventListener('click', () => {
  state.novas = 0;
  atualizarBotaoDeRolagem();
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
      // A confirmação é um diálogo do app, não o pop-up do navegador.
      pedirConfirmacaoDeExclusao(id);
    }
  } catch (erro) {
    avisar(`Não foi possível concluir a ação. ${erro.message}`);
  }
});

/** Abre o diálogo de exclusão nomeando exatamente o que será perdido. */
function pedirConfirmacaoDeExclusao(id) {
  const c = campanha(id);
  campanhaParaApagar = id;
  confirmText.textContent = c
    ? `"${c.titulo}" e todo o histórico desta campanha serão removidos. Não há como desfazer.`
    : 'Todo o histórico desta campanha será removido. Não há como desfazer.';
  confirmDialog.showModal();
}

confirmDialog.addEventListener('close', async () => {
  const id = campanhaParaApagar;
  const confirmado = confirmDialog.returnValue === 'confirm';
  campanhaParaApagar = null;
  if (!id || !confirmado) return;
  try {
    await api(`/v1/campanhas/${encodeURIComponent(id)}`, {method: 'DELETE'});
    state.campanhas = state.campanhas.filter((x) => x.id !== id);
    delete state.rascunhos[id];
    salvarRascunhos();
    if (state.atual === id) fecharCampanha();
    else renderList();
    avisar('Campanha apagada.', 'info');
  } catch (erro) {
    avisar(`Não foi possível apagar a campanha. ${erro.message}`);
  }
});

document.querySelector('#confirm-cancel')?.addEventListener('click', () => confirmDialog.close('cancel'));
document.querySelector('#confirm-delete')?.addEventListener('click', () => confirmDialog.close('confirm'));

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
