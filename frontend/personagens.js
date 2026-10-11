// Grupo, ficha e assistente de criação de personagens.
// Nenhuma regra é calculada aqui: a interface exibe o bloco devolvido pelo motor.
(function () {
  const groupButton = document.querySelector('#group-button');
  const groupDialog = document.querySelector('#group-dialog');
  const groupBody = document.querySelector('#group-body');
  const groupBack = document.querySelector('#group-back');
  const groupClose = document.querySelector('#group-close');
  const groupTitle = document.querySelector('#group-title');
  const groupEyebrow = document.querySelector('#group-eyebrow');
  const newCharacter = document.querySelector('#new-character');
  const charDialog = document.querySelector('#character-dialog');
  const charForm = document.querySelector('#character-form');
  const charBody = document.querySelector('#character-body');
  const charStep = document.querySelector('#character-step');
  const charStepper = document.querySelector('#character-stepper');
  const charSummary = document.querySelector('#character-summary');
  const charError = document.querySelector('#character-error');
  const prevButton = document.querySelector('#character-prev');
  const nextButton = document.querySelector('#character-next');

  const ATRIBUTOS = ['forca', 'destreza', 'constituicao', 'inteligencia', 'sabedoria', 'carisma'];
  const ABREVIATURAS = {forca: 'FOR', destreza: 'DES', constituicao: 'CON', inteligenia: 'INT', inteligencia: 'INT', sabedoria: 'SAB', carisma: 'CAR'};
  const NOMES = {
    forca: 'Força', destreza: 'Destreza', constituicao: 'Constituição', inteligencia: 'Inteligência', sabedoria: 'Sabedoria', carisma: 'Carisma',
    aasimar: 'Aasimar', draconato: 'Draconato', anao: 'Anão', elfo: 'Elfo', gnomo: 'Gnomo', golias: 'Golias', halfling: 'Halfling', humano: 'Humano', orc: 'Orc', tiefling: 'Tiefling',
    barbaro: 'Bárbaro', bardo: 'Bardo', clerigo: 'Clérigo', druida: 'Druída', guerreiro: 'Guerreiro', monge: 'Monge', paladino: 'Paladino', guardiao: 'Guardião', ladino: 'Ladino', feiticeiro: 'Feiticeiro', bruxo: 'Bruxo', mago: 'Mago', artifice: 'Artífice',
    pequeno: 'Pequeno', medio: 'Médio', pequeno_ou_medio: 'Pequeno ou Médio',
    iniciado_em_magia: 'Iniciado em Magia', artifista: 'Artifista', atacante_selvagem: 'Atacante Selvagem', valentao_de_taverna: 'Valentão de Taverna', olho_agucado: 'Olho Aguçado', dadiva_sombria: 'Dádiva Sombria',
    anatomia_aberrante: 'Anatomia Aberrante', sombra_viva: 'Sombra Viva', ser_simbiotico: 'Ser Simbiótico', alma_ecoante: 'Alma Ecoante', andarilho_das_brumas: 'Andarilho das Brumas', toque_da_morte: 'Toque da Morte', sussurros_reunidos: 'Sussurros Reunidos', segunda_pele: 'Segunda Pele', observadores: 'Observadores',
    intuicao: 'Intuição', religiao: 'Religião', investigacao: 'Investigação', persuasao: 'Persuasão', atuacao: 'Atuação', enganacao: 'Enganação', prestidigitacao: 'Prestidigitação', percepcao: 'Percepção', lidar_com_animais: 'Lidar com Animais', adestrar_animais: 'Lidar com Animais', arcanismo: 'Arcanismo', acrobacia: 'Acrobacia', atletismo: 'Atletismo', furtividade: 'Furtividade', medicina: 'Medicina', natureza: 'Natureza', sobrevivencia: 'Sobrevivência', historia: 'História', intimidacao: 'Intimidação',
    forca_ou_destreza: 'Força ou Destreza', destreza_e_sabedoria: 'Destreza e Sabedoria', forca_ou_destreza_e_carisma: 'Força ou Destreza, e Carisma',
    duas_maos: 'Duas mãos', acuidade: 'Acuidade', arremesso: 'Arremesso', leve: 'Leve', municao: 'Munição', versatil: 'Versátil', extensao: 'Extensão', pesada: 'Pesada', recarga: 'Recarga',
    contundente: 'contundente', cortante: 'cortante', perfurante: 'perfurante',
    leves: 'armaduras leves', medias: 'armaduras médias', pesadas: 'armaduras pesadas', escudos: 'escudos', simples: 'armas simples', marciais: 'armas marciais',
  };
  const PASSOS = ['Nome', 'Espécie', 'Classe', 'Perícias', 'Antecedente', 'Atributos', 'Revisão'];

  let catalogo = null;
  let catalogoEquipamento = null;
  let dados = null;
  let passo = 0;
  let abaAtiva = 'resumo';
  let personagemCriado = false;

  // ---------- utilidades ----------
  const nome = (chave) => NOMES[chave] || String(chave || '').replace(/_/g, ' ').replace(/^./, (l) => l.toUpperCase());
  const talentoNome = (chave) => {
    const [base, lista] = String(chave).split(':');
    return lista ? `${nome(base)} (${nome(lista)})` : nome(base);
  };
  const abreviar = (atributo) => ABREVIATURAS[atributo] || String(atributo || '').slice(0, 3).toUpperCase();
  const modificador = (valor) => Math.floor((Number(valor) - 10) / 2);
  const assinado = (n) => (Number(n) >= 0 ? `+${Number(n)}` : `${Number(n)}`);
  const url = (sufixo = '') => `/v1/campanhas/${encodeURIComponent(state.atual)}/personagens${sufixo}`;
  const el = (tag, props = {}, ...filhos) => {
    const no = document.createElement(tag);
    for (const [chave, valor] of Object.entries(props)) {
      if (valor === null || valor === undefined || valor === false) continue;
      if (chave.includes('-') || chave === 'role') no.setAttribute(chave, valor);
      else no[chave] = valor;
    }
    no.append(...filhos.filter((f) => f !== null && f !== undefined && f !== false));
    return no;
  };
  const meta = (texto) => el('p', {className: 'choice-meta', textContent: texto});

  function chipDado(texto, rotulo, variante = '') {
    const chip = el('span', {className: `chip chip-dado ${variante}`.trim()});
    chip.append(el('span', {className: 'dado-icone', 'aria-hidden': 'true'}));
    if (rotulo) chip.append(el('span', {className: 'chip-rotulo', textContent: rotulo}));
    chip.append(document.createTextNode(texto));
    return chip;
  }

  function blocoValor(rotulo, valor, nota) {
    return el('div', {className: 'bloco-valor'},
      el('span', {className: 'rotulo', textContent: rotulo}),
      el('span', {className: 'valor', textContent: valor}),
      nota ? el('span', {className: 'nota', textContent: nota}) : null);
  }

  function painel(titulo, ...conteudo) {
    return el('section', {className: 'painel'}, el('p', {className: 'painel-titulo', textContent: titulo}), ...conteudo);
  }

  function badge(texto, variante = '') {
    return el('span', {className: `badge ${variante}`.trim(), textContent: texto});
  }

  function barraPv(atual, maximo) {
    const percentual = maximo > 0 ? Math.max(0, Math.min(100, (atual / maximo) * 100)) : 0;
    return el('div', {className: 'pv-barra', role: 'img',
      'aria-label': `Pontos de vida: ${atual} de ${maximo}`},
      el('span', {className: 'pv-preenchimento', style: `width:${percentual}%`}));
  }

  function estadoPv(atual, maximo) {
    if (atual <= 0) return {texto: 'Inconsciente', cor: 'var(--color-danger)'};
    const razao = maximo > 0 ? atual / maximo : 0;
    if (razao <= 0.3) return {texto: 'Grave', cor: 'var(--color-danger)'};
    if (razao <= 0.7) return {texto: 'Ferido', cor: 'var(--color-accent)'};
    return {texto: 'Saudável', cor: 'var(--color-success)'};
  }

  // ---------- catálogos ----------
  async function carregarCatalogo() {
    if (!catalogo) catalogo = await api('/v1/catalogo/personagens');
    return catalogo;
  }

  async function carregarEquipamento() {
    if (!catalogoEquipamento) catalogoEquipamento = await api('/v1/catalogo/equipamento');
    return catalogoEquipamento;
  }

  new MutationObserver(() => { groupButton.disabled = optionsButton.disabled; })
    .observe(optionsButton, {attributes: true, attributeFilter: ['disabled']});
  groupButton.disabled = optionsButton.disabled;

  // ---------- grupo ----------
  let requisicaoGrupo = 0;
  async function abrirGrupo() {
    const token = ++requisicaoGrupo;
    const campanhaId = state.atual;
    groupBack.hidden = true;
    newCharacter.hidden = false;
    groupTitle.textContent = 'Grupo';
    groupEyebrow.textContent = 'Grupo da campanha';
    groupBody.replaceChildren(meta('Carregando grupo…'));
    if (!groupDialog.open) groupDialog.showModal();
    try {
      const grupo = await api(`/v1/campanhas/${encodeURIComponent(campanhaId)}/personagens`);
      if (token !== requisicaoGrupo || state.atual !== campanhaId) return;
      groupBody.replaceChildren();
      groupTitle.textContent = grupo.length ? `Grupo · ${grupo.length}` : 'Grupo';
      if (!grupo.length) {
        groupBody.append(meta('Ainda não há personagens nesta campanha. Crie o primeiro para o MJ conhecer o grupo.'));
        return;
      }
      const lista = el('ul', {className: 'choice-list'});
      for (const p of grupo) lista.append(el('li', {}, cartaoPersonagem(p)));
      groupBody.append(lista);
    } catch (erro) {
      if (token !== requisicaoGrupo || state.atual !== campanhaId) return;
      groupBody.replaceChildren(el('p', {className: 'form-error', textContent: `Não foi possível carregar o grupo. ${erro.message}`}));
    }
  }

  function cartaoPersonagem(p) {
    const estado = estadoPv(p.pv_atual, p.pv_maximo);
    const cartao = el('button', {type: 'button', className: 'cartao-grupo'},
      el('span', {className: 'cartao-topo'},
        el('span', {className: 'cartao-nome', textContent: p.nome}),
        el('span', {className: 'cartao-nivel', textContent: `Nível ${p.nivel}`})),
      el('span', {className: 'linha-resumo', textContent: `${nome(p.especie)} · ${nome(p.classe)} · ${nome(p.antecedente)}`}),
      barraPv(p.pv_atual, p.pv_maximo),
      el('span', {className: 'chips'},
        el('span', {className: 'chip', textContent: `${p.pv_atual}/${p.pv_maximo} PV`}),
        blocoDoCartao(p, 'ca', 'CA'),
        blocoDoCartao(p, 'ataque', 'Ataque', true),
        p.proficiencias_pendentes ? badge('Escolhas pendentes', 'badge-alerta') : null),
      el('span', {className: 'card-action', textContent: estado.texto + ' — ver ficha'}));
    cartao.addEventListener('click', () => mostrarFicha(p));
    return cartao;
  }

  function blocoDoCartao(p, chave, rotulo, sinal) {
    const origem = chave === 'ca' ? p.bloco?.ca : p.bloco?.arma?.ataque;
    if (origem === undefined || origem === null) return null;
    return el('span', {className: 'chip', textContent: `${rotulo} ${sinal ? assinado(origem) : origem}`});
  }

  // ---------- ficha ----------
  function mostrarFicha(p) {
    groupBack.hidden = false;
    newCharacter.hidden = true;
    groupTitle.textContent = p.nome;
    groupEyebrow.textContent = `${nome(p.especie)} · ${nome(p.classe)} nível ${p.nivel}`;
    groupBody.replaceChildren(cabecalhoFicha(p), abasFicha(p));
    groupBody.scrollTop = 0;
  }

  function cabecalhoFicha(p) {
    const pvAtual = p.pv_atual;
    const pvMaximo = p.pv_maximo;
    const estado = estadoPv(pvAtual, pvMaximo);
    const numero = el('p', {className: 'pv-numero'},
      el('strong', {textContent: String(pvAtual)}), el('span', {textContent: ` / ${pvMaximo} PV`}));
    const situacao = el('p', {className: 'pv-estado', textContent: estado.texto, style: `color:${estado.cor}`});
    const barra = barraPv(pvAtual, pvMaximo);
    const controles = el('div', {className: 'pv-controles'});
    const ajustar = async (delta) => {
      [...controles.children].forEach((b) => { b.disabled = true; });
      situacao.textContent = 'Ajustando…';
      try {
        const novo = await api(url(`/${encodeURIComponent(p.id)}`), {method: 'PATCH', body: JSON.stringify({ajuste_pv: delta})});
        Object.assign(p, novo);
        mostrarFicha(p);
        return;
      } catch (erro) {
        situacao.textContent = `Erro: ${erro.message}`;
      }
      [...controles.children].forEach((b) => { b.disabled = false; });
      situacao.textContent = estado.texto;
    };
    for (const delta of [-5, -1, 1, 5]) {
      const botao = el('button', {type: 'button', className: delta < 0 ? 'text-button' : 'icon-button',
        textContent: `${delta > 0 ? '+' : '−'}${Math.abs(delta)}`,
        'aria-label': `${delta > 0 ? 'Recuperar' : 'Perder'} ${Math.abs(delta)} PV`});
      botao.addEventListener('click', () => ajustar(delta));
      controles.append(botao);
    }
    return el('div', {className: 'painel'},
      el('div', {className: 'cabecalho-ficha'},
        el('h3', {className: 'nameplate', textContent: p.nome}),
        el('p', {className: 'linha-resumo', textContent: `${nome(p.especie)} · ${nome(p.classe)} nível ${p.nivel}${p.subclasse ? ` · ${nome(p.subclasse)}` : ''} · ${nome(p.antecedente)}`}),
        el('div', {className: 'badges'},
          badge(`Proficiência ${assinado(p.bonus_proficiencia)}`, 'badge-destaque'),
          badge(`Dado de Vida d${p.dado_vida}`),
          badge(`${nome(p.tamanho)} · ${String(p.deslocamento).replace('.', ',')} m`),
          p.bloco?.conjuracao ? badge(`Conjuração: ${abreviar(p.bloco.conjuracao.atributo)}`, 'badge-magia') : null,
          p.proficiencias_pendentes ? badge('Escolhas pendentes', 'badge-alerta') : null)),
      barra,
      el('div', {className: 'pv-topo'}, numero, situacao),
      controles);
  }

  function abasFicha(p) {
    const pares = [
      {id: 'resumo', rotulo: 'Resumo', montar: () => secaoResumo(p)},
      {id: 'atributos', rotulo: 'Atributos', montar: () => secaoAtributos(p)},
      {id: 'pericias', rotulo: 'Perícias', montar: () => secaoPericias(p)},
      {id: 'equipamento', rotulo: 'Equipamento', montar: () => secaoEquipamento(p)},
    ];
    if (p.bloco?.conjuracao) pares.push({id: 'magias', rotulo: 'Magias', montar: () => secaoMagias(p)});

    const lista = el('div', {className: 'abas', role: 'tablist', 'aria-label': 'Seções da ficha'});
    const palco = el('div');
    const botoes = new Map();
    const montados = new Map();

    const palcoWrapper = el('div', {id: 'painel-ficha', role: 'tabpanel', tabIndex: 0, 'aria-live': 'polite'}, palco);
    const ativar = (id, focar) => {
      abaAtiva = id;
      palcoWrapper.setAttribute('aria-labelledby', `aba-${id}`);
      for (const [chave, botao] of botoes) {
        const selecionado = chave === id;
        botao.setAttribute('aria-selected', String(selecionado));
        botao.tabIndex = selecionado ? 0 : -1;
        if (selecionado && focar) botao.focus();
      }
      if (!montados.has(id)) {
        const alvo = pares.find((par) => par.id === id);
        montados.set(id, alvo.montar());
      }
      palco.replaceChildren(montados.get(id));
    };

    for (const par of pares) {
      const botao = el('button', {type: 'button', className: 'aba', role: 'tab', id: `aba-${par.id}`,
        'aria-controls': 'painel-ficha', 'aria-selected': 'false', tabIndex: -1, textContent: par.rotulo});
      botao.addEventListener('click', () => ativar(par.id));
      botao.addEventListener('keydown', (evento) => {
        const ordem = pares.map((x) => x.id);
        const atual = ordem.indexOf(par.id);
        const proximo = evento.key === 'ArrowRight' ? ordem[atual + 1]
          : evento.key === 'ArrowLeft' ? ordem[atual - 1]
          : evento.key === 'Home' ? ordem[0]
          : evento.key === 'End' ? ordem[ordem.length - 1] : null;
        if (!proximo) return;
        evento.preventDefault();
        ativar(proximo, true);
      });
      botoes.set(par.id, botao);
      lista.append(botao);
    }

    const wrapper = el('div', {}, lista, palcoWrapper);
    ativar(pares.some((par) => par.id === abaAtiva) ? abaAtiva : pares[0].id);
    return wrapper;
  }

  function secaoResumo(p) {
    const bloco = p.bloco || {};
    const arma = bloco.arma || {};
    const conjuracao = bloco.conjuracao;
    const caixa = el('div');

    caixa.append(painel('Bloco de combate',
      el('div', {className: 'bloco-combate'},
        blocoValor('CA', bloco.ca ?? '—', 'classe de armadura'),
        blocoValor('Iniciativa', assinado(bloco.iniciativa ?? 0), 'Destreza'),
        blocoValor('Proficiência', assinado(bloco.bonus_proficiencia ?? 0)),
        blocoValor('Deslocamento', `${String(p.deslocamento).replace('.', ',')} m`),
        blocoValor('Dado de Vida', `d${p.dado_vida}`),
        conjuracao ? blocoValor('CD de magia', String(conjuracao.cd), abreviar(conjuracao.atributo)) : null),
      meta('Valores derivados pelo motor a partir da ficha e dos catálogos oficiais.')));

    const linhasArma = el('div', {className: 'chips'},
      chipDado(`d20 ${assinado(arma.ataque ?? 0)}`, 'Ataque'),
      arma.dado ? chipDado(arma.expressao_dano, 'Dano', 'chip-dano') : chipDado(String(arma.expressao_dano ?? '—'), 'Dano', 'chip-dano'));
    const detalhesArma = [];
    if (arma.nome) detalhesArma.push(arma.tipo ? `${nome(arma.tipo)}` : null);
    if (arma.a_distancia) detalhesArma.push(`alcance ${Math.round((arma.alcance_pes || 0) / 3.28084)} m`);
    else if (arma.alcance_pes > 5) detalhesArma.push(`extensão ${Math.round((arma.alcance_pes || 0) / 3.28084)} m`);
    else detalhesArma.push('corpo a corpo');
    if (arma.desarmado) detalhesArma.push('dano mínimo 0');
    if ((arma.propriedades || []).length) detalhesArma.push(arma.propriedades.map(nome).join(', '));
    const armadura = bloco.armadura || {};
    caixa.append(painel('Ataque e proteção',
      el('p', {className: 'linha-resumo', textContent: arma.nome || 'Desarmado'}),
      linhasArma,
      meta(detalhesArma.filter(Boolean).join(' · ')),
      el('hr', {className: 'regra-fina'}),
      el('p', {className: 'linha-resumo', textContent: armadura.nome ? `${armadura.nome}${armadura.escudo ? ' + escudo' : ''}` : 'Sem armadura'}),
      meta(armadura.nome
        ? `CA base ${armadura.ca_base} · ${nome(armadura.categoria || '')}${armadura.escudo ? ' · +2 do escudo' : ''}`
        : 'CA 10 + modificador de Destreza.'),
      arma.proficiente === false ? el('p', {className: 'form-error', textContent: 'A ficha não registra proficiência com esta arma.'}) : null,
      conjuracao ? el('div', {className: 'chips', style: 'margin-top:var(--space-3)'},
        chipDado(`d20 ${assinado(conjuracao.ataque)}`, 'Ataque mágico', 'chip-magia'),
        chipDado(`CD ${conjuracao.cd}`, 'Dificuldade', 'chip-magia')) : null));

    const talentos = (p.talentos || []).map(talentoNome);
    caixa.append(painel('Talentos e proficiências',
      talentos.length ? el('div', {className: 'chips'}, ...talentos.map((t) => el('span', {className: 'chip', textContent: t})))
        : meta('Nenhum talento registrado.'),
      el('hr', {className: 'regra-fina'}),
      el('dl', {className: 'facts'},
        el('dt', {textContent: 'Armas'}), el('dd', {textContent: (p.proficiencias_classe?.armas || []).map(nome).join(', ') || '—'}),
        el('dt', {textContent: 'Armaduras'}), el('dd', {textContent: (p.proficiencias_classe?.armaduras || []).map(nome).join(', ') || '—'}),
        el('dt', {textContent: 'Ferramentas'}), el('dd', {textContent: [...(p.proficiencias_classe?.ferramentas || []), p.ferramenta].filter(Boolean).join(', ') || '—'}))));

    if (p.equipamento_antecedente) {
      caixa.append(painel('Equipamento inicial do antecedente',
        meta(`Opção A: ${p.equipamento_antecedente.A}`),
        meta(`Opção B: ${p.equipamento_antecedente.B}`)));
    }

    const apagar = el('button', {type: 'button', className: 'danger-button', textContent: 'Apagar personagem'});
    apagar.addEventListener('click', async () => {
      if (!window.confirm(`Apagar ${p.nome}? Esta ação não pode ser desfeita.`)) return;
      try { await api(url(`/${encodeURIComponent(p.id)}`), {method: 'DELETE'}); abrirGrupo(); } catch (erro) { window.alert(erro.message); }
    });
    caixa.append(el('section', {className: 'painel zona-perigo'},
      el('p', {className: 'painel-titulo', textContent: 'Zona de perigo'}),
      meta('Apagar remove a ficha da campanha. O histórico da campanha não é afetado.'),
      apagar));
    return caixa;
  }

  function secaoAtributos(p) {
    const grade = el('div', {className: 'atributos'});
    for (const a of ATRIBUTOS) {
      const valor = p.atributos[a];
      const mod = p.modificadores?.[a] ?? modificador(valor);
      grade.append(el('div', {className: 'atributo', 'data-destaque': mod >= 3 ? 'sim' : 'nao'},
        el('span', {className: 'atributo-nome', textContent: abreviar(a)}),
        el('span', {className: 'atributo-valor', textContent: String(valor)}),
        el('span', {className: 'atributo-mod', textContent: assinado(mod)}),
        el('span', {className: 'choice-meta', textContent: nome(a)})));
    }
    return el('div', {},
      painel('Atributos', grade, meta('Os modificadores são calculados pelo motor de regras.')));
  }

  function secaoPericias(p) {
    const caixa = el('div');

    const salvaguardas = el('ul', {className: 'lista-pericias'});
    for (const linha of p.bloco?.salvaguardas || []) {
      salvaguardas.append(el('li', {className: 'linha-pericia', 'data-proficiente': linha.proficiente ? 'sim' : 'nao'},
        el('span', {className: 'marca', 'data-proficiente': linha.proficiente ? 'sim' : 'nao', 'aria-hidden': 'true'}),
        el('span', {className: 'nome-pericia', textContent: nome(linha.atributo)}),
        el('span', {className: 'atributo-pericia', textContent: linha.proficiente ? 'proficiente' : ''}),
        el('span', {className: 'total-pericia', textContent: assinado(linha.total)})));
    }
    caixa.append(painel('Salvaguardas', salvaguardas));

    const pericias = el('ul', {className: 'lista-pericias'});
    for (const linha of p.bloco?.pericias || []) {
      pericias.append(el('li', {className: 'linha-pericia', 'data-proficiente': linha.proficiente ? 'sim' : 'nao'},
        el('span', {className: 'marca', 'data-proficiente': linha.proficiente ? 'sim' : 'nao', 'aria-hidden': 'true'}),
        el('span', {className: 'nome-pericia', textContent: nome(linha.pericia)}),
        el('span', {className: 'atributo-pericia', textContent: abreviar(linha.atributo)}),
        el('span', {className: 'total-pericia', textContent: assinado(linha.total)})));
    }
    caixa.append(painel('Perícias', pericias,
      meta('A marca âmbar indica proficiência; o valor já soma o bônus de proficiência.')));

    caixa.append(editorProficiencias(p));
    return caixa;
  }

  function editorProficiencias(p) {
    const secao = painel('Escolhas de classe');
    const status = meta('Carregando opções…');
    secao.append(status);
    carregarCatalogo().then((cat) => {
      const opcoes = cat.pericias_classe_opcoes?.[p.classe] || [];
      const limite = Number(cat.quantidade_pericias_classe?.[p.classe] || 0);
      if (!opcoes.length) { status.textContent = 'Esta classe não exige escolha de perícias.'; return; }
      const selecionadas = new Set(p.pericias_classe || []);
      const lista = el('ul', {className: 'choice-list'});
      const atualizar = () => {
        status.textContent = `Escolha ${limite} perícias de classe. Selecionadas: ${selecionadas.size}/${limite}.`;
      };
      for (const pericia of opcoes) {
        const caixa = el('input', {type: 'checkbox', checked: selecionadas.has(pericia)});
        caixa.addEventListener('change', () => {
          if (caixa.checked && selecionadas.size >= limite) { caixa.checked = false; return; }
          if (caixa.checked) selecionadas.add(pericia); else selecionadas.delete(pericia);
          atualizar();
        });
        lista.append(el('li', {}, el('label', {className: 'choice'}, caixa,
          el('span', {className: 'choice-text'}, el('span', {className: 'choice-title', textContent: nome(pericia)})))));
      }
      let ferramentaSelect = null;
      if (p.classe === 'artifice') {
        const id = `artisan-tool-${p.id}`;
        ferramentaSelect = el('select', {id, className: 'field-control'},
          el('option', {value: '', textContent: 'Escolha uma ferramenta de artesão…'}),
          ...(cat.ferramentas_artesao || []).map((ferramenta) => el('option', {value: ferramenta, textContent: ferramenta})));
        ferramentaSelect.value = p.ferramenta_artesao || '';
        secao.append(el('label', {htmlFor: id, textContent: 'Ferramenta de artesão do Artífice'}), ferramentaSelect);
      }
      const salvar = el('button', {type: 'button', className: 'primary-button', textContent: 'Salvar escolhas'});
      salvar.addEventListener('click', async () => {
        if (selecionadas.size !== limite) { status.textContent = `Escolha exatamente ${limite} perícias antes de salvar.`; return; }
        salvar.disabled = true;
        status.textContent = 'Validando no motor…';
        try {
          const atualizado = await api(url(`/${encodeURIComponent(p.id)}/proficiencias`), {
            method: 'PATCH',
            body: JSON.stringify({pericias_classe: [...selecionadas], ferramenta_artesao: ferramentaSelect ? (ferramentaSelect.value || null) : null}),
          });
          Object.assign(p, atualizado);
          mostrarFicha(p);
        } catch (erro) {
          status.textContent = `Não foi possível salvar: ${erro.message}`;
          salvar.disabled = false;
        }
      });
      secao.append(lista, salvar);
      atualizar();
    }).catch((erro) => { status.textContent = `Não foi possível carregar as opções. ${erro.message}`; });
    return secao;
  }

  function secaoEquipamento(p) {
    const secao = painel('Armas e armadura');
    const status = meta('Carregando catálogo oficial…');
    secao.append(status);
    carregarEquipamento().then((cat) => {
      status.remove();
      const profs = p.proficiencias_classe || {};
      const armas = new Set(profs.armas || []);
      const armaduras = new Set(profs.armaduras || []);
      const categoriaArmadura = {leve: 'leves', media: 'medias', pesada: 'pesadas', escudo: 'escudos'};
      const temArma = (nomeArma) => {
        const categoria = cat.arma_simples.includes(nomeArma) ? 'simples' : 'marciais';
        return armas.has(categoria) || armas.has(cat.alias_proficiencia_arma[nomeArma]);
      };

      const armaSelect = el('select', {className: 'field-control', 'aria-label': 'Arma equipada'});
      armaSelect.append(el('option', {value: '', textContent: 'Desarmado'}));
      for (const [rotulo, filtro] of [['Armas simples', (n) => cat.arma_simples.includes(n)], ['Armas marciais', (n) => !cat.arma_simples.includes(n)]]) {
        const grupo = el('optgroup', {label: rotulo});
        for (const nomeArma of Object.keys(cat.armas).filter(filtro)) {
          const dadosArma = cat.armas[nomeArma];
          const opcao = el('option', {value: nomeArma,
            textContent: `${nomeArma} · ${dadosArma.dano} ${nome(dadosArma.tipo)}${temArma(nomeArma) ? '' : ' (sem proficiência)'}`});
          opcao.disabled = !temArma(nomeArma);
          grupo.append(opcao);
        }
        armaSelect.append(grupo);
      }

      const armaduraSelect = el('select', {className: 'field-control', 'aria-label': 'Armadura equipada'});
      armaduraSelect.append(el('option', {value: '', textContent: 'Sem armadura'}));
      for (const [nomeArmadura, dadosArmadura] of Object.entries(cat.armaduras)) {
        if (dadosArmadura.categoria === 'escudo') continue;
        const permitida = armaduras.has(categoriaArmadura[dadosArmadura.categoria]);
        const opcao = el('option', {value: nomeArmadura,
          textContent: `${nomeArmadura} · CA ${dadosArmadura.ca}${permitida ? '' : ' (sem proficiência)'}`});
        opcao.disabled = !permitida;
        armaduraSelect.append(opcao);
      }

      const escudoId = `escudo-${p.id}`;
      const escudoCheck = el('input', {type: 'checkbox', id: escudoId, checked: Boolean(p.equipamento?.escudo)});
      const equipamentoAtual = p.equipamento || {};
      armaSelect.value = equipamentoAtual.arma || '';
      armaduraSelect.value = equipamentoAtual.armadura || '';
      const feedback = el('p', {className: 'painel-nota', role: 'status', textContent: 'A CA e o dano são calculados pelo motor depois de salvar.'});
      const salvar = el('button', {type: 'button', className: 'primary-button', textContent: 'Salvar equipamento'});
      salvar.addEventListener('click', async () => {
        salvar.disabled = true;
        feedback.textContent = 'Validando equipamento e proficiências…';
        try {
          const atualizado = await api(url(`/${encodeURIComponent(p.id)}/equipamento`), {
            method: 'PATCH',
            body: JSON.stringify({arma: armaSelect.value || null, armadura: armaduraSelect.value || null, escudo: escudoCheck.checked}),
          });
          Object.assign(p, atualizado);
          mostrarFicha(p);
        } catch (erro) {
          feedback.textContent = `Não foi possível equipar: ${erro.message}`;
          salvar.disabled = false;
        }
      });
      secao.append(
        el('label', {className: 'field-label', htmlFor: `arma-${p.id}`, textContent: 'Arma equipada'}),
        Object.assign(armaSelect, {id: `arma-${p.id}`}),
        el('label', {className: 'field-label', htmlFor: `armadura-${p.id}`, textContent: 'Armadura'}),
        Object.assign(armaduraSelect, {id: `armadura-${p.id}`}),
        el('label', {className: 'choice', style: 'margin-top:var(--space-2)'}, escudoCheck,
          el('span', {className: 'choice-text'}, el('span', {className: 'choice-title', textContent: 'Escudo (+2 CA)'}))),
        salvar, feedback);
    }).catch((erro) => { status.textContent = `Não foi possível carregar o catálogo. ${erro.message}`; });
    return secao;
  }

  function secaoMagias(p) {
    const secao = painel('Conjuração',
      meta(p.classe === 'artifice'
        ? 'Lista, truques, magias preparadas e espaços são validados pela progressão do Artífice. Se o efeito de uma magia ainda não estiver implementado, o motor a recusará sem inventar o resultado.'
        : 'A seleção é registrada no catálogo; a validação completa por classe ainda está sendo implementada.'));
    const status = el('p', {className: 'painel-nota', role: 'status', textContent: 'Carregando catálogo de magias…'});
    secao.append(status);
    montarConjuracao(p, secao, status);
    return secao;
  }

  async function montarConjuracao(p, secao, status) {
    try {
      const [catalogoMagias, atual] = await Promise.all([
        api(`/v1/catalogo/magias?classe=${encodeURIComponent(p.classe)}&nivel=${encodeURIComponent(p.nivel)}`),
        api(url(`/${encodeURIComponent(p.id)}`)),
      ]);
      const conj = atual.conjuracao || {truques: [], magias_preparadas: [], espacos_totais: {}};
      const progresso = p.classe === 'artifice'
        ? await api(`/v1/catalogo/conjuracao?classe=artifice&nivel=${encodeURIComponent(p.nivel)}&inteligencia=${encodeURIComponent(p.atributos.inteligencia)}`)
        : null;
      status.remove();

      const limiteTruques = progresso?.truques ?? null;
      const limiteMagias = progresso?.magias_preparadas ?? null;
      // O catálogo e a ficha podem grafar o nome com maiúsculas diferentes.
      const normalizar = (texto) => String(texto).trim().toLocaleLowerCase('pt-BR');
      const conjuntoMagias = (lista) => {
        const mapa = new Map();
        for (const item of lista || []) mapa.set(normalizar(item), item);
        return mapa;
      };
      const truques = conjuntoMagias(conj.truques);
      const preparadas = conjuntoMagias(conj.magias_preparadas);

      const construirLista = (titulo, magias, selecionadas, limite, evento) => {
        const bloco = el('div');
        bloco.append(el('p', {className: 'painel-titulo', textContent: titulo}));
        const contador = meta('');
        const lista = el('ul', {className: 'lista-magias'});
        const atualizar = () => {
          contador.textContent = limite ? `Selecionadas: ${selecionadas.size}/${limite}.` : `${selecionadas.size} selecionada(s).`;
          for (const botao of lista.querySelectorAll('.botao-magia')) {
            botao.setAttribute('aria-pressed', String(selecionadas.has(normalizar(botao.dataset.nome))));
          }
        };
        for (const magia of magias) {
          const chave = normalizar(magia.nome);
          const botao = el('button', {type: 'button', className: 'botao-magia',
            'aria-pressed': String(selecionadas.has(chave))},
            el('span', {className: 'magia-nome', textContent: magia.nome}),
            el('span', {className: 'magia-meta', textContent: `${nome(magia.escola)}${magia.concentracao ? ' · concentração' : ''}${magia.ritual ? ' · ritual' : ''}`}));
          botao.dataset.nome = magia.nome;
          botao.addEventListener('click', () => {
            if (selecionadas.has(chave)) selecionadas.delete(chave);
            else {
              if (limite && selecionadas.size >= limite) { contador.textContent = `O motor limita esta lista a ${limite} magia(s).`; return; }
              selecionadas.add(chave, magia.nome);
            }
            atualizar();
            evento?.();
          });
          lista.append(el('li', {}, botao));
        }
        bloco.append(contador, lista);
        atualizar();
        return bloco;
      };

      const truquesBloco = construirLista('Truques', catalogoMagias.filter((m) => m.circulo === 0), truques, limiteTruques);
      const magiasBloco = construirLista('Magias preparadas/conhecidas', catalogoMagias.filter((m) => (m.circulo ?? 0) > 0), preparadas, limiteMagias);
      secao.append(truquesBloco, magiasBloco);

      // Espaços de magia
      const espacos = el('div', {className: 'espacos'});
      const slotsEsperados = progresso?.espacos_totais || conj.espacos_totais || {'1': 0};
      const restantes = conj.espacos_restantes || slotsEsperados;
      for (const [circulo, total] of Object.entries(slotsEsperados)) {
        const pips = el('span', {className: 'pips'});
        const usados = Number(total) - Number(restantes[circulo] ?? total);
        for (let i = 0; i < Number(total); i += 1) {
          pips.append(el('span', {className: 'pip', 'data-preenchido': i < Number(total) - usados ? 'sim' : 'nao'}));
        }
        espacos.append(el('div', {className: 'linha-espaco'},
          el('span', {className: 'rotulo-espaco', textContent: `${circulo}º círculo`}),
          pips,
          el('span', {className: 'magia-meta', textContent: `${restantes[circulo] ?? total}/${total} restantes`})));
      }
      secao.append(el('div', {},
        el('p', {className: 'painel-titulo', textContent: 'Espaços de magia'}),
        Object.keys(slotsEsperados).length ? espacos : meta('Nenhum espaço registrado.')));

      const feedback = el('p', {className: 'painel-nota', role: 'status'});
      const salvar = el('button', {type: 'button', className: 'primary-button', textContent: 'Salvar conjuração'});
      salvar.addEventListener('click', async () => {
        salvar.disabled = true;
        feedback.textContent = 'Salvando…';
        try {
          const resultado = await api(url(`/${encodeURIComponent(p.id)}/magias`), {
            method: 'PATCH',
            body: JSON.stringify({
              truques: [...truques],
              magias_preparadas: [...preparadas],
              espacos_totais: Object.fromEntries(Object.entries(slotsEsperados).map(([circulo, total]) => [circulo, Number(total)])),
            }),
          });
          Object.assign(p, resultado);
          mostrarFicha(p);
        } catch (erro) {
          feedback.textContent = `Não foi possível salvar: ${erro.message}`;
          salvar.disabled = false;
        }
      });
      const descanso = el('button', {type: 'button', className: 'text-button', textContent: 'Recuperar espaços (descanso longo)'});
      descanso.addEventListener('click', async () => {
        descanso.disabled = true;
        feedback.textContent = 'Recuperando espaços…';
        try {
          const atualizado = await api(url(`/${encodeURIComponent(p.id)}/descanso-longo`), {method: 'POST'});
          Object.assign(p, atualizado);
          mostrarFicha(p);
        } catch (erro) {
          feedback.textContent = `Não foi possível recuperar espaços: ${erro.message}`;
          descanso.disabled = false;
        }
      });
      secao.append(el('div', {className: 'sheet-actions'}, descanso, salvar), feedback);
    } catch (erro) {
      status.textContent = `Não foi possível carregar a conjuração. ${erro.message}`;
    }
  }

  // ---------- assistente de criação ----------
  function novoRascunho() {
    return {nome: '', especie: '', classe: '', antecedente: '', talento_antecedente: '', metodo_atributos: 'matriz_padrao',
      atributos: Object.fromEntries(ATRIBUTOS.map((a) => [a, ''])), compra: Object.fromEntries(ATRIBUTOS.map((a) => [a, 8])),
      modo_aumento: '2-1', aumento2: '', aumento1: '', pericias_classe: [], ferramenta_artesao: '', heranca_draconica: '', ferramenta_antecedente: '', equipamento_antecedente: ''};
  }

  async function abrirCriacao() {
    try { await carregarCatalogo(); } catch (erro) { window.alert(`Não foi possível carregar as regras. ${erro.message}`); return; }
    dados = novoRascunho();
    passo = 0;
    if (groupDialog.open) groupDialog.close();
    charDialog.showModal();
    render();
  }

  function cartaoEscolha(nomeCampo, valor, titulo, metaTexto, marcado, aoEscolher) {
    const input = el('input', {type: 'radio', name: nomeCampo, value: valor, checked: marcado});
    input.addEventListener('change', () => aoEscolher(valor));
    return el('label', {className: 'escolha-cartao'}, input,
      el('span', {className: 'escolha-texto'},
        el('span', {className: 'escolha-titulo', textContent: titulo}),
        metaTexto ? el('span', {className: 'escolha-meta', textContent: metaTexto}) : null));
  }

  function render() {
    charError.textContent = '';
    charStep.textContent = `Passo ${passo + 1} de ${PASSOS.length} — ${PASSOS[passo]}`;
    prevButton.disabled = passo === 0;
    nextButton.textContent = passo === PASSOS.length - 1 ? 'Criar personagem' : 'Próximo';
    desenharStepper();
    charBody.replaceChildren(...[passoNome, passoEspecie, passoClasse, passoPericiasClasse, passoAntecedente, passoAtributos, passoRevisao][passo]());
    charBody.scrollTop = 0;
  }

  function desenharStepper() {
    charStepper.replaceChildren();
    for (let i = 0; i < PASSOS.length; i += 1) {
      const estado = i === passo ? 'atual' : i < passo ? 'feito' : 'pendente';
      charStepper.append(el('li', {className: 'passo', 'data-estado': estado},
        el('span', {className: 'passo-marca', textContent: i < passo ? '✓' : String(i + 1)}),
        el('span', {className: 'passo-rotulo', textContent: PASSOS[i]})));
    }
    const partes = [];
    if (dados.especie) partes.push(['Espécie', nome(dados.especie)]);
    if (dados.classe) partes.push(['Classe', nome(dados.classe)]);
    if (dados.antecedente) partes.push(['Antecedente', catalogo.antecedentes[dados.antecedente]?.nome || nome(dados.antecedente)]);
    charSummary.replaceChildren(...partes.map(([rotulo, valor]) => el('span', {}, document.createTextNode(`${rotulo}: `), el('strong', {textContent: valor}))));
  }

  function passoNome() {
    const input = el('input', {id: 'character-name', type: 'text', maxLength: 80, value: dados.nome, autocomplete: 'off', required: true});
    input.addEventListener('input', () => { dados.nome = input.value; });
    setTimeout(() => input.focus(), 0);
    return [el('label', {htmlFor: 'character-name', textContent: 'Nome do personagem'}), input,
      meta('Criação no nível 1, conforme o Livro do Jogador 2024.')];
  }

  function passoEspecie() {
    const grade = el('div', {className: 'escolhas-grade'});
    for (const [chave, info] of Object.entries(catalogo.especies)) {
      grade.append(cartaoEscolha('especie', chave, nome(chave),
        `Tamanho ${nome(info.tamanho)} · Deslocamento ${String(info.deslocamento).replace('.', ',')} m`,
        dados.especie === chave, (v) => { dados.especie = v; }));
    }
    const extras = [];
    const escolha = catalogo.escolhas_especie?.[dados.especie];
    if (escolha) {
      const id = 'species-choice';
      const select = el('select', {id, className: 'field-control'},
        el('option', {value: '', textContent: 'Escolha uma herança dracônica…'}),
        ...((escolha.opcoes || []).map((info) =>
          el('option', {value: info.chave, textContent: `${info.nome} — dano ${info.dano}`})));
      select.value = dados.heranca_draconica || '';
      select.addEventListener('change', () => { dados.heranca_draconica = select.value; });
      extras.push(meta(escolha.nota), el('label', {htmlFor: id, textContent: escolha.rotulo}), select);
    } else {
      dados.heranca_draconica = '';
    }
    return [el('fieldset', {}, el('legend', {textContent: 'Escolha a espécie'}), grade, ...extras)];
  }

  function passoClasse() {
    const grade = el('div', {className: 'escolhas-grade'});
    for (const [chave, info] of Object.entries(catalogo.classes)) {
      grade.append(cartaoEscolha('classe', chave, nome(chave),
        `Dado de Vida d${info.dado_vida} · Atributo principal: ${nome(info.atributo_primario)}`,
        dados.classe === chave, (v) => { dados.classe = v; dados.pericias_classe = []; dados.ferramenta_artesao = ''; }));
    }
    return [el('fieldset', {}, el('legend', {textContent: 'Escolha a classe'}), grade)];
  }

  function passoPericiasClasse() {
    const opcoes = catalogo.pericias_classe_opcoes?.[dados.classe] || [];
    const limite = Number(catalogo.quantidade_pericias_classe?.[dados.classe] || 0);
    const status = meta(`Escolha ${limite} perícias de classe. Selecionadas: ${(dados.pericias_classe || []).length}/${limite}.`);
    const lista = el('ul', {className: 'choice-list'});
    for (const pericia of opcoes) {
      const caixa = el('input', {type: 'checkbox', checked: (dados.pericias_classe || []).includes(pericia)});
      caixa.addEventListener('change', () => {
        const atuais = new Set(dados.pericias_classe || []);
        if (caixa.checked && atuais.size >= limite) {
          caixa.checked = false;
          charError.textContent = `Esta classe permite escolher apenas ${limite} perícias.`;
          return;
        }
        charError.textContent = '';
        if (caixa.checked) atuais.add(pericia); else atuais.delete(pericia);
        dados.pericias_classe = [...atuais];
        status.textContent = `Escolha ${limite} perícias de classe. Selecionadas: ${atuais.size}/${limite}.`;
      });
      lista.append(el('li', {}, el('label', {className: 'choice'}, caixa,
        el('span', {className: 'choice-text'}, el('span', {className: 'choice-title', textContent: nome(pericia)})))));
    }
    const extras = [];
    if (dados.classe === 'artifice') {
      const id = 'artisan-tool-proficiency';
      const select = el('select', {id}, el('option', {value: '', textContent: 'Escolha uma ferramenta de artesão…'}),
        ...(catalogo.ferramentas_artesao || []).map((ferramenta) => el('option', {value: ferramenta, textContent: ferramenta})));
      select.value = dados.ferramenta_artesao || '';
      select.addEventListener('change', () => { dados.ferramenta_artesao = select.value; });
      extras.push(el('label', {htmlFor: id, textContent: 'Proficiência de ferramenta adicional do Artífice'}), select);
    }
    return [el('fieldset', {}, el('legend', {textContent: `Perícias de ${nome(dados.classe)}`}),
      meta('Essas escolhas são validadas pelo motor e somadas às perícias do antecedente, sem duplicar bônus.'),
      lista, status, ...extras)];
  }

  function passoAntecedente() {
    const grupos = [['Livro do Jogador 2024', 'Livro do Jogador'], ['Ravenloft: Horror Wilds', 'Ravenloft']];
    const blocos = [];
    const extra = el('div');
    const extraEscolhas = el('div');
    const desenharEscolhasAntecedente = () => {
      extraEscolhas.replaceChildren();
      const bg = catalogo.antecedentes[dados.antecedente];
      if (!bg) return;
      const info = catalogo.ferramentas_antecedente?.[dados.antecedente];
      if (info) {
        const id = 'background-tool';
        const select = el('select', {id, className: 'field-control'},
          el('option', {value: '', textContent: `Escolha ${info.rotulo}…`}),
          ...info.opcoes.map((item) => el('option', {value: item, textContent: item})));
        select.value = dados.ferramenta_antecedente || '';
        select.addEventListener('change', () => { dados.ferramenta_antecedente = select.value; });
        extraEscolhas.append(el('label', {htmlFor: id, textContent: `${info.rotulo} do antecedente`}), select);
      } else {
        dados.ferramenta_antecedente = '';
      }
      const idEquipamento = 'background-equipment';
      const equipamento = el('select', {id: idEquipamento, className: 'field-control'},
        el('option', {value: '', textContent: 'Escolha um pacote de equipamento…'}),
        el('option', {value: 'A', textContent: `Pacote A — ${bg.equipamento.A}`}),
        el('option', {value: 'B', textContent: `Pacote B — ${bg.equipamento.B}`}));
      equipamento.value = dados.equipamento_antecedente || '';
      equipamento.addEventListener('change', () => { dados.equipamento_antecedente = equipamento.value; });
      extraEscolhas.append(el('label', {htmlFor: idEquipamento, textContent: 'Equipamento inicial do antecedente'}), equipamento);
    };
    const desenharExtra = () => {
      extra.replaceChildren();
      const bg = catalogo.antecedentes[dados.antecedente];
      if (!bg) return;
      const precisa = bg.talento === 'dadiva_sombria';
      const opcional = bg.talentos_alternativos.includes('dadiva_sombria');
      if (!precisa && !opcional) { dados.talento_antecedente = ''; return; }
      const select = el('select', {id: 'background-feat'});
      if (opcional) select.append(el('option', {value: '', textContent: `${talentoNome(bg.talento)} (talento de origem)`}));
      else select.append(el('option', {value: '', textContent: 'Escolha uma Dádiva Sombria…'}));
      for (const d of catalogo.dadivas_sombrias) select.append(el('option', {value: d, textContent: `Dádiva Sombria: ${nome(d)}`}));
      select.value = dados.talento_antecedente;
      select.addEventListener('change', () => { dados.talento_antecedente = select.value; });
      extra.append(el('label', {htmlFor: 'background-feat', textContent: 'Talento do antecedente (Dádivas Sombrias exigem campanha de Ravenloft)'}), select);
    };
    for (const [titulo, filtro] of grupos) {
      const grade = el('div', {className: 'escolhas-grade'});
      for (const [chave, info] of Object.entries(catalogo.antecedentes).filter(([, v]) => v.fonte.includes(filtro))) {
        grade.append(cartaoEscolha('antecedente', chave, info.nome,
          `${info.atributos.map(nome).join(', ')} · ${talentoNome(info.talento)} · ${info.pericias.map(nome).join(', ')}`,
          dados.antecedente === chave, (v) => {
            if (v !== dados.antecedente) { dados.aumento2 = ''; dados.aumento1 = ''; dados.talento_antecedente = ''; }
            dados.antecedente = v;
            desenharExtra();
            desenharEscolhasAntecedente();
          }));
      }
      blocos.push(el('h3', {textContent: titulo}), grade);
    }
    desenharExtra();
    desenharEscolhasAntecedente();
    return [el('fieldset', {}, el('legend', {textContent: 'Escolha o antecedente'}), ...blocos), extra, extraEscolhas];
  }

  function passoAtributos() {
    const area = el('div');
    const desenhar = () => {
      const metodo = el('div', {className: 'segmented', role: 'group', 'aria-label': 'Método de geração de atributos'});
      for (const [valor, titulo] of [['matriz_padrao', 'Matriz padrão'], ['compra_pontos', 'Compra por pontos']]) {
        const b = el('button', {type: 'button', className: 'text-button', textContent: titulo});
        b.setAttribute('aria-pressed', String(dados.metodo_atributos === valor));
        b.addEventListener('click', () => { dados.metodo_atributos = valor; desenhar(); });
        metodo.append(b);
      }
      const grade = el('div', {className: 'atributos'});
      const extras = [];
      if (dados.metodo_atributos === 'matriz_padrao') {
        extras.push(meta(`Distribua ${catalogo.matriz_padrao.join(', ')} — cada valor uma vez.`));
        const selects = [];
        const sincronizar = () => {
          const usados = new Set(ATRIBUTOS.map((a) => String(dados.atributos[a])).filter((v) => v && v !== ''));
          for (const select of selects) {
            for (const opcao of select.options) {
              if (!opcao.value) continue;
              opcao.disabled = usados.has(opcao.value) && opcao.value !== select.value;
            }
          }
        };
        for (const a of ATRIBUTOS) {
          const id = `matriz-${a}`;
          const select = el('select', {id, className: 'field-control'}, el('option', {value: '', textContent: '—'}),
            ...catalogo.matriz_padrao.map((v) => el('option', {value: String(v), textContent: String(v)})));
          select.value = String(dados.atributos[a]);
          const valor = el('span', {className: 'atributo-mod'});
          const atualizarMod = () => { valor.textContent = select.value ? assinado(modificador(select.value)) : '—'; };
          select.addEventListener('change', () => { dados.atributos[a] = select.value; atualizarMod(); sincronizar(); });
          atualizarMod();
          selects.push(select);
          grade.append(el('div', {className: 'atributo'},
            el('label', {htmlFor: id, className: 'atributo-nome', textContent: abreviar(a)}),
            select, valor,
            el('span', {className: 'choice-meta', textContent: nome(a)})));
        }
        sincronizar();
      } else {
        const custos = catalogo.compra_pontos.custos;
        const gastos = () => ATRIBUTOS.reduce((total, a) => total + custos[dados.compra[a]], 0);
        const restante = el('p', {className: 'points', role: 'status'});
        const atualizar = () => {
          restante.textContent = `Pontos restantes: ${catalogo.compra_pontos.total - gastos()} de ${catalogo.compra_pontos.total}`;
        };
        for (const a of ATRIBUTOS) {
          const valor = el('span', {className: 'atributo-valor', textContent: String(dados.compra[a])});
          const custo = el('span', {className: 'compra-custo'});
          const mod = el('span', {className: 'atributo-mod'});
          const pintar = () => {
            valor.textContent = String(dados.compra[a]);
            custo.textContent = `custo ${custos[dados.compra[a]]}`;
            mod.textContent = assinado(modificador(dados.compra[a]));
          };
          const passoValor = (d) => {
            const novo = dados.compra[a] + d;
            if (novo < 8 || novo > 15) return;
            const antes = dados.compra[a];
            dados.compra[a] = novo;
            if (gastos() > catalogo.compra_pontos.total) { dados.compra[a] = antes; return; }
            pintar(); atualizar();
          };
          const menos = el('button', {type: 'button', className: 'icon-button', textContent: '−', 'aria-label': `Diminuir ${nome(a)}`});
          const mais = el('button', {type: 'button', className: 'icon-button', textContent: '+', 'aria-label': `Aumentar ${nome(a)}`});
          menos.addEventListener('click', () => passoValor(-1));
          mais.addEventListener('click', () => passoValor(1));
          pintar();
          grade.append(el('div', {className: 'atributo'},
            el('span', {className: 'atributo-nome', textContent: abreviar(a)}),
            el('div', {className: 'stepper'}, menos, valor, mais),
            mod, el('span', {className: 'compra-linha'}, el('span', {className: 'choice-meta', textContent: nome(a)}), custo)));
        }
        atualizar();
        extras.unshift(restante);
      }
      area.replaceChildren(metodo, ...extras, grade, blocoAumentos());
    };
    desenhar();
    return [area];
  }

  function blocoAumentos() {
    const bg = catalogo.antecedentes[dados.antecedente];
    const caixa = el('fieldset', {}, el('legend', {textContent: `Aumentos do antecedente ${bg.nome}: ${bg.atributos.map(nome).join(', ')}`}));
    const modos = el('div', {className: 'segmented', role: 'group', 'aria-label': 'Distribuição dos aumentos'});
    const corpo = el('div');
    const desenhar = () => {
      modos.replaceChildren();
      for (const [valor, titulo] of [['2-1', '+2 e +1'], ['1-1-1', '+1 em três']]) {
        const b = el('button', {type: 'button', className: 'text-button', textContent: titulo});
        b.setAttribute('aria-pressed', String(dados.modo_aumento === valor));
        b.addEventListener('click', () => { dados.modo_aumento = valor; desenhar(); });
        modos.append(b);
      }
      corpo.replaceChildren();
      if (dados.modo_aumento === '2-1') {
        const selects = [];
        const sincronizar = () => {
          const escolhidos = new Set(selects.map((s) => s.value).filter(Boolean));
          for (const select of selects) {
            for (const opcao of select.options) {
              if (!opcao.value) continue;
              opcao.disabled = escolhidos.has(opcao.value) && opcao.value !== select.value;
            }
          }
        };
        for (const [campo, rotulo] of [['aumento2', '+2 em'], ['aumento1', '+1 em']]) {
          const id = `bg-${campo}`;
          const select = el('select', {id, className: 'field-control'}, el('option', {value: '', textContent: '—'}),
            ...bg.atributos.map((a) => el('option', {value: a, textContent: nome(a)})));
          select.value = dados[campo];
          select.addEventListener('change', () => { dados[campo] = select.value; sincronizar(); });
          selects.push(select);
          corpo.append(el('label', {htmlFor: id, textContent: rotulo}), select);
        }
        sincronizar();
      } else {
        corpo.append(meta(`+1 em ${bg.atributos.map(nome).join(', ')}.`));
      }
    };
    desenhar();
    caixa.append(modos, corpo);
    return caixa;
  }

  const custos = () => catalogo.compra_pontos.custos;
  const pontosGastos = () => ATRIBUTOS.reduce((t, a) => t + custos()[dados.compra[a]], 0);
  function base() {
    if (dados.metodo_atributos === 'compra_pontos') return {...dados.compra};
    return Object.fromEntries(ATRIBUTOS.map((a) => [a, Number(dados.atributos[a]) || 0]));
  }
  function aumentos() {
    const r = {};
    const bg = catalogo.antecedentes[dados.antecedente];
    if (!bg) return r;
    if (dados.modo_aumento === '1-1-1') { for (const a of bg.atributos) r[a] = 1; return r; }
    if (dados.aumento2) r[dados.aumento2] = 2;
    if (dados.aumento1) r[dados.aumento1] = (r[dados.aumento1] || 0) + 1;
    return r;
  }

  function passoRevisao() {
    const b = base();
    const au = aumentos();
    const grade = el('div', {className: 'atributos'});
    for (const a of ATRIBUTOS) {
      const total = b[a] + (au[a] || 0);
      grade.append(el('div', {className: 'atributo', 'data-destaque': modificador(total) >= 3 ? 'sim' : 'nao'},
        el('span', {className: 'atributo-nome', textContent: abreviar(a)}),
        el('span', {className: 'atributo-valor', textContent: String(total)}),
        el('span', {className: 'atributo-mod', textContent: assinado(modificador(total))}),
        el('span', {className: 'choice-meta', textContent: au[a] ? `${b[a]} + ${au[a]}` : `${b[a]}`})));
    }
    const bg = catalogo.antecedentes[dados.antecedente];
    const talento = dados.talento_antecedente || bg.talento;
    return [
      el('div', {className: 'cabecalho-ficha'},
        el('h3', {className: 'nameplate', textContent: dados.nome.trim()}),
        el('p', {className: 'linha-resumo', textContent: `${nome(dados.especie)} · ${nome(dados.classe)} nível 1 · ${bg.nome}`}),
        el('div', {className: 'badges'},
          badge(nome(dados.especie)),
          badge(`d${catalogo.classes[dados.classe].dado_vida}`, 'badge-destaque'),
          badge(talentoNome(talento), 'badge-magia'))),
      grade,
      el('hr', {className: 'regra-fina'}),
      el('dl', {className: 'facts'},
        el('dt', {textContent: 'Perícias do antecedente'}), el('dd', {textContent: bg.pericias.map(nome).join(', ')}),
        el('dt', {textContent: 'Perícias de classe'}), el('dd', {textContent: (dados.pericias_classe || []).map(nome).join(', ')}),
        ...(dados.classe === 'artifice' ? [el('dt', {textContent: 'Ferramenta de artesão'}), el('dd', {textContent: dados.ferramenta_artesao || 'pendente'})] : []),
        el('dt', {textContent: 'Ferramenta do antecedente'}), el('dd', {textContent: dados.ferramenta_antecedente || bg.ferramenta}),
        el('dt', {textContent: 'Equipamento inicial'}), el('dd', {textContent: dados.equipamento_antecedente ? `${dados.equipamento_antecedente}: ${bg.equipamento[dados.equipamento_antecedente]}` : `Escolha A: ${bg.equipamento.A} · ou B: ${bg.equipamento.B}`})),
      meta('PV, bônus de proficiência, CA e salvaguardas são calculados pelo motor de regras ao criar o personagem.')];
  }

  function payload() {
    return {nome: dados.nome.trim(), especie: dados.especie, classe: dados.classe, nivel: 1, metodo_atributos: dados.metodo_atributos,
      atributos: base(), antecedente: dados.antecedente, aumentos_antecedente: aumentos(), talento_antecedente: dados.talento_antecedente || null,
      pericias_classe: dados.pericias_classe, ferramenta_artesao: dados.ferramenta_artesao || null,
      heranca_draconica: dados.heranca_draconica || null, ferramenta_antecedente: dados.ferramenta_antecedente || null,
      equipamento_antecedente: dados.equipamento_antecedente || null};
  }

  function validarPasso() {
    if (passo === 0 && !dados.nome.trim()) return 'Dê um nome ao personagem.';
    if (passo === 1 && !dados.especie) return 'Escolha uma espécie.';
    if (passo === 1 && catalogo.escolhas_especie?.[dados.especie] && !dados.heranca_draconica) return 'Escolha a herança dracônica.';
    if (passo === 2 && !dados.classe) return 'Escolha uma classe.';
    if (passo === 3) {
      const quantidade = Number(catalogo.quantidade_pericias_classe?.[dados.classe] || 0);
      if ((dados.pericias_classe || []).length !== quantidade) return `Escolha exatamente ${quantidade} perícias de classe.`;
      if (dados.classe === 'artifice' && !dados.ferramenta_artesao) return 'Escolha uma ferramenta de artesão para o Artífice.';
    }
    if (passo === 4) {
      if (!dados.antecedente) return 'Escolha um antecedente.';
      if (catalogo.antecedentes[dados.antecedente].talento === 'dadiva_sombria' && !dados.talento_antecedente) return 'Escolha uma Dádiva Sombria.';
      const bg = catalogo.antecedentes[dados.antecedente];
      const ferramenta = catalogo.ferramentas_antecedente?.[dados.antecedente];
      if (ferramenta && !dados.ferramenta_antecedente) return `Escolha ${ferramenta.rotulo} para o antecedente.`;
      if (!dados.equipamento_antecedente) return 'Escolha o pacote de equipamento A ou B.';
    }
    if (passo === 5) {
      if (dados.metodo_atributos === 'matriz_padrao') {
        const usados = ATRIBUTOS.map((a) => Number(dados.atributos[a])).sort((x, y) => y - x);
        if (usados.join() !== catalogo.matriz_padrao.join()) return 'Use cada valor da matriz padrão exatamente uma vez.';
      }
      if (dados.modo_aumento === '2-1' && (!dados.aumento2 || !dados.aumento1 || dados.aumento2 === dados.aumento1)) return 'Escolha atributos diferentes para +2 e +1.';
      const b = base(); const au = aumentos();
      if (ATRIBUTOS.some((a) => b[a] + (au[a] || 0) > 20)) return 'Nenhum atributo pode passar de 20.';
    }
    return '';
  }

  charForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const erro = validarPasso();
    if (erro) { charError.textContent = erro; return; }
    if (passo < PASSOS.length - 1) { passo += 1; render(); return; }
    nextButton.disabled = true;
    try {
      await api(url(), {method: 'POST', body: JSON.stringify(payload())});
      personagemCriado = true;
      charDialog.close();
      abrirGrupo();
    } catch (falha) {
      charError.textContent = `O motor de regras recusou a ficha: ${falha.message}`;
    } finally {
      nextButton.disabled = false;
    }
  });

  prevButton.addEventListener('click', () => { if (passo > 0) { passo -= 1; render(); } });
  document.querySelector('#character-cancel').addEventListener('click', () => charDialog.close());
  // Cancelar ou fechar o assistente devolve o jogador ao grupo, sem perder a campanha aberta.
  charDialog.addEventListener('close', () => {
    const reabrirGrupo = !personagemCriado && Boolean(state.atual) && !groupDialog.open;
    personagemCriado = false;
    if (reabrirGrupo) groupDialog.showModal();
  });
  groupClose.addEventListener('click', () => groupDialog.close());
  groupBack.addEventListener('click', abrirGrupo);
  groupButton.addEventListener('click', abrirGrupo);
  newCharacter.addEventListener('click', abrirCriacao);
})();
