// Grupo e criação de personagens. Toda regra é validada no servidor pelo Rule Engine.
(function () {
  const groupButton = document.querySelector('#group-button');
  const groupDialog = document.querySelector('#group-dialog');
  const groupBody = document.querySelector('#group-body');
  const groupBack = document.querySelector('#group-back');
  const newCharacter = document.querySelector('#new-character');
  const charDialog = document.querySelector('#character-dialog');
  const charForm = document.querySelector('#character-form');
  const charBody = document.querySelector('#character-body');
  const charStep = document.querySelector('#character-step');
  const charError = document.querySelector('#character-error');
  const prevButton = document.querySelector('#character-prev');
  const nextButton = document.querySelector('#character-next');

  const ATRIBUTOS = ['forca', 'destreza', 'constituicao', 'inteligencia', 'sabedoria', 'carisma'];
  const NOMES = {
    forca: 'Força', destreza: 'Destreza', constituicao: 'Constituição', inteligencia: 'Inteligência', sabedoria: 'Sabedoria', carisma: 'Carisma',
    aasimar: 'Aasimar', draconato: 'Draconato', anao: 'Anão', elfo: 'Elfo', gnomo: 'Gnomo', golias: 'Golias', halfling: 'Halfling', humano: 'Humano', orc: 'Orc', tiefling: 'Tiefling',
    barbaro: 'Bárbaro', bardo: 'Bardo', clerigo: 'Clérigo', druida: 'Druida', guerreiro: 'Guerreiro', monge: 'Monge', paladino: 'Paladino', guardiao: 'Guardião', ladino: 'Ladino', feiticeiro: 'Feiticeiro', bruxo: 'Bruxo', mago: 'Mago', artifice: 'Artífice',
    pequeno: 'Pequeno', medio: 'Médio', pequeno_ou_medio: 'Pequeno ou Médio',
    iniciado_em_magia: 'Iniciado em Magia', artifista: 'Artifista', atacante_selvagem: 'Atacante Selvagem', valentao_de_taverna: 'Valentão de Taverna', olho_agucado: 'Olho Aguçado', dadiva_sombria: 'Dádiva Sombria',
    anatomia_aberrante: 'Anatomia Aberrante', sombra_viva: 'Sombra Viva', ser_simbiotico: 'Ser Simbiótico', alma_ecoante: 'Alma Ecoante', andarilho_das_brumas: 'Andarilho das Brumas', toque_da_morte: 'Toque da Morte', sussurros_reunidos: 'Sussurros Reunidos', segunda_pele: 'Segunda Pele', observadores: 'Observadores',
    intuicao: 'Intuição', religiao: 'Religião', investigacao: 'Investigação', persuasao: 'Persuasão', atuacao: 'Atuação', enganacao: 'Enganação', prestidigitacao: 'Prestidigitação', percepcao: 'Percepção', lidar_com_animais: 'Lidar com Animais', sobrevivencia: 'Sobrevivência', historia: 'História', intimidacao: 'Intimidação',
    forca_ou_destreza: 'Força ou Destreza', destreza_e_sabedoria: 'Destreza e Sabedoria', forca_ou_destreza_e_carisma: 'Força ou Destreza, e Carisma',
  };
  const PASSOS = ['Nome', 'Espécie', 'Classe', 'Antecedente', 'Atributos', 'Revisão'];

  let catalogo = null;
  let dados = null;
  let passo = 0;

  const nome = (chave) => NOMES[chave] || String(chave || '').replace(/_/g, ' ').replace(/^./, (l) => l.toUpperCase());
  const talentoNome = (chave) => {
    const [base, lista] = String(chave).split(':');
    return lista ? `${nome(base)} (${nome(lista)})` : nome(base);
  };
  const mod = (v) => { const m = Math.floor((v - 10) / 2); return m >= 0 ? `+${m}` : `${m}`; };
  const url = (sufixo = '') => `/v1/campanhas/${encodeURIComponent(state.atual)}/personagens${sufixo}`;
  const el = (tag, props = {}, ...filhos) => {
    const n = Object.assign(document.createElement(tag), props);
    n.append(...filhos.filter((f) => f !== null && f !== undefined));
    return n;
  };

  new MutationObserver(() => { groupButton.disabled = optionsButton.disabled; })
    .observe(optionsButton, {attributes: true, attributeFilter: ['disabled']});
  groupButton.disabled = optionsButton.disabled;

  async function carregarCatalogo() {
    if (!catalogo) catalogo = await api('/v1/catalogo/personagens');
    return catalogo;
  }

  // ---- Grupo ----
  async function abrirGrupo() {
    groupBack.hidden = true;
    newCharacter.hidden = false;
    groupBody.replaceChildren(el('p', {className: 'empty-inline', textContent: 'Carregando grupo…'}));
    if (!groupDialog.open) groupDialog.showModal();
    try {
      const grupo = await api(url());
      groupBody.replaceChildren();
      if (!grupo.length) {
        groupBody.append(el('p', {textContent: 'Ainda não há personagens nesta campanha. Crie o primeiro para o MJ conhecer o grupo.'}));
        return;
      }
      const lista = el('ul', {className: 'choice-list'});
      for (const p of grupo) {
        const botao = el('button', {type: 'button', className: 'character-card'},
          el('strong', {className: 'card-title', textContent: p.nome}),
          el('span', {className: 'card-preview', textContent: `${nome(p.especie)} · ${nome(p.classe)} ${p.nivel} · ${nome(p.antecedente)}`}),
          el('span', {className: 'card-action', textContent: `PV ${p.pv_atual}/${p.pv_maximo} — ver ficha`}));
        botao.addEventListener('click', () => mostrarFicha(p));
        lista.append(el('li', {}, botao));
      }
      groupBody.append(lista);
    } catch (erro) {
      groupBody.replaceChildren(el('p', {className: 'form-error', textContent: `Não foi possível carregar o grupo. ${erro.message}`}));
    }
  }

  function mostrarFicha(p) {
    groupBack.hidden = false;
    newCharacter.hidden = true;
    const atributos = el('div', {className: 'ability-grid'});
    for (const a of ATRIBUTOS) {
      atributos.append(el('div', {className: 'ability'},
        el('span', {className: 'ability-name', textContent: nome(a).slice(0, 3)}),
        el('span', {className: 'ability-value', textContent: p.atributos[a]}),
        el('span', {className: 'ability-mod', textContent: `mod ${mod(p.atributos[a])}`})));
    }
    const pv = el('span', {className: 'hp-value', textContent: `${p.pv_atual} / ${p.pv_maximo}`});
    const ajustar = async (delta) => {
      try {
        const novo = await api(url(`/${encodeURIComponent(p.id)}`), {method: 'PATCH', body: JSON.stringify({ajuste_pv: delta})});
        Object.assign(p, novo);
        pv.textContent = `${p.pv_atual} / ${p.pv_maximo}`;
      } catch (erro) { pv.textContent = `Erro: ${erro.message}`; }
    };
    const menos = el('button', {type: 'button', className: 'icon-button', textContent: '−', ariaLabel: 'Perder 1 PV'});
    const mais = el('button', {type: 'button', className: 'icon-button', textContent: '+', ariaLabel: 'Recuperar 1 PV'});
    menos.addEventListener('click', () => ajustar(-1));
    mais.addEventListener('click', () => ajustar(1));
    const fato = (rotulo, valor) => [el('dt', {textContent: rotulo}), el('dd', {textContent: valor})];
    const equip = p.equipamento_antecedente ? `A: ${p.equipamento_antecedente.A} · ou B: ${p.equipamento_antecedente.B}` : '—';
    const apagar = el('button', {type: 'button', className: 'danger-button', textContent: 'Apagar personagem'});
    apagar.addEventListener('click', async () => {
      if (!window.confirm(`Apagar ${p.nome}? Esta ação não pode ser desfeita.`)) return;
      try { await api(url(`/${encodeURIComponent(p.id)}`), {method: 'DELETE'}); abrirGrupo(); } catch (erro) { window.alert(erro.message); }
    });
    groupBody.replaceChildren(
      el('h3', {textContent: p.nome}),
      el('p', {className: 'choice-meta', textContent: `${nome(p.especie)} · ${nome(p.classe)} nível ${p.nivel} · ${nome(p.antecedente)}`}),
      el('h3', {textContent: 'Pontos de Vida'}),
      el('div', {className: 'hp-row'}, menos, pv, mais),
      el('h3', {textContent: 'Atributos'}),
      atributos,
      el('h3', {textContent: 'Detalhes'}),
      el('dl', {className: 'facts'},
        ...fato('Bônus de Proficiência', `+${p.bonus_proficiencia}`),
        ...fato('Dado de Vida', `d${p.dado_vida}`),
        ...fato('Tamanho', nome(p.tamanho)),
        ...fato('Deslocamento', `${String(p.deslocamento).replace('.', ',')} m`),
        ...fato('Perícias', p.pericias.map(nome).join(', ') || '—'),
        ...fato('Ferramenta', p.ferramenta || '—'),
        ...fato('Talentos', p.talentos.map(talentoNome).join(', ') || '—'),
        ...fato('Equipamento inicial', equip)),
      apagar);
    groupBody.scrollTop = 0;
  }

  // ---- Assistente de criação ----
  function novoRascunho() {
    return {nome: '', especie: '', classe: '', antecedente: '', talento_antecedente: '', metodo_atributos: 'matriz_padrao',
      atributos: Object.fromEntries(ATRIBUTOS.map((a) => [a, ''])), compra: Object.fromEntries(ATRIBUTOS.map((a) => [a, 8])),
      modo_aumento: '2-1', aumento2: '', aumento1: ''};
  }

  async function abrirCriacao() {
    try { await carregarCatalogo(); } catch (erro) { window.alert(`Não foi possível carregar as regras. ${erro.message}`); return; }
    dados = novoRascunho();
    passo = 0;
    if (groupDialog.open) groupDialog.close();
    charDialog.showModal();
    render();
  }

  function radios(nomeCampo, opcoes, atual, aoEscolher) {
    const lista = el('ul', {className: 'choice-list'});
    for (const [valor, titulo, meta] of opcoes) {
      const input = el('input', {type: 'radio', name: nomeCampo, value: valor, checked: valor === atual});
      input.addEventListener('change', () => aoEscolher(valor));
      lista.append(el('li', {}, el('label', {className: 'choice'}, input,
        el('span', {className: 'choice-text'}, el('span', {className: 'choice-title', textContent: titulo}), meta ? el('span', {className: 'choice-meta', textContent: meta}) : null))));
    }
    return lista;
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

  function render() {
    charError.textContent = '';
    charStep.textContent = `Passo ${passo + 1} de ${PASSOS.length} — ${PASSOS[passo]}`;
    prevButton.disabled = passo === 0;
    nextButton.textContent = passo === PASSOS.length - 1 ? 'Criar personagem' : 'Próximo';
    charBody.replaceChildren(...[passoNome, passoEspecie, passoClasse, passoAntecedente, passoAtributos, passoRevisao][passo]());
    charBody.scrollTop = 0;
  }

  function passoNome() {
    const input = el('input', {id: 'character-name', type: 'text', maxLength: 80, value: dados.nome, autocomplete: 'off', required: true});
    input.addEventListener('input', () => { dados.nome = input.value; });
    setTimeout(() => input.focus(), 0);
    return [el('label', {htmlFor: 'character-name', textContent: 'Nome do personagem'}), input,
      el('p', {className: 'choice-meta', textContent: 'Criação no nível 1, conforme o Livro do Jogador 2024.'})];
  }

  function passoEspecie() {
    const opcoes = Object.entries(catalogo.especies).map(([k, v]) => [k, nome(k), `Tamanho ${nome(v.tamanho)} · Deslocamento ${String(v.deslocamento).replace('.', ',')} m`]);
    return [el('fieldset', {}, el('legend', {textContent: 'Escolha a espécie'}), radios('especie', opcoes, dados.especie, (v) => { dados.especie = v; }))];
  }

  function passoClasse() {
    const opcoes = Object.entries(catalogo.classes).map(([k, v]) => [k, nome(k), `Dado de Vida d${v.dado_vida} · Atributo principal: ${nome(v.atributo_primario)}`]);
    return [el('fieldset', {}, el('legend', {textContent: 'Escolha a classe'}), radios('classe', opcoes, dados.classe, (v) => { dados.classe = v; }))];
  }

  function passoAntecedente() {
    const grupos = [['Livro do Jogador 2024', 'Livro do Jogador'], ['Ravenloft: Horror Wilds', 'Ravenloft']];
    const blocos = [];
    const extra = el('div');
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
      const opcoes = Object.entries(catalogo.antecedentes).filter(([, v]) => v.fonte.includes(filtro)).map(([k, v]) => [k, v.nome,
        `${v.atributos.map(nome).join(', ')} · Talento: ${talentoNome(v.talento)} · Perícias: ${v.pericias.map(nome).join(', ')}`]);
      blocos.push(el('h3', {textContent: titulo}), radios('antecedente', opcoes, dados.antecedente, (v) => {
        if (v !== dados.antecedente) { dados.aumento2 = ''; dados.aumento1 = ''; dados.talento_antecedente = ''; }
        dados.antecedente = v; desenharExtra();
      }));
    }
    desenharExtra();
    return [el('fieldset', {}, el('legend', {textContent: 'Escolha o antecedente'}), ...blocos), extra];
  }

  function passoAtributos() {
    const area = el('div');
    const desenhar = () => {
      const metodo = el('div', {className: 'segmented', role: 'group', ariaLabel: 'Método de geração de atributos'});
      for (const [valor, titulo] of [['matriz_padrao', 'Matriz padrão'], ['compra_pontos', 'Compra por pontos']]) {
        const b = el('button', {type: 'button', className: 'text-button', textContent: titulo});
        b.setAttribute('aria-pressed', String(dados.metodo_atributos === valor));
        b.addEventListener('click', () => { dados.metodo_atributos = valor; desenhar(); });
        metodo.append(b);
      }
      const grade = el('div', {className: 'ability-grid'});
      const extras = [];
      if (dados.metodo_atributos === 'matriz_padrao') {
        extras.push(el('p', {className: 'choice-meta', textContent: `Distribua ${catalogo.matriz_padrao.join(', ')} — cada valor uma vez.`}));
        for (const a of ATRIBUTOS) {
          const id = `matriz-${a}`;
          const select = el('select', {id}, el('option', {value: '', textContent: '—'}), ...catalogo.matriz_padrao.map((v) => el('option', {value: String(v), textContent: String(v)})));
          select.value = String(dados.atributos[a]);
          select.addEventListener('change', () => { dados.atributos[a] = select.value; });
          grade.append(el('div', {className: 'ability'}, el('label', {htmlFor: id, className: 'ability-name', textContent: nome(a)}), select));
        }
      } else {
        const restante = el('p', {className: 'points', role: 'status'});
        const atualizar = () => { restante.textContent = `Pontos restantes: ${catalogo.compra_pontos.total - pontosGastos()} de ${catalogo.compra_pontos.total}`; };
        for (const a of ATRIBUTOS) {
          const valor = el('span', {className: 'ability-value', textContent: dados.compra[a]});
          const passoValor = (d) => {
            const novo = dados.compra[a] + d;
            if (novo < 8 || novo > 15) return;
            const antes = dados.compra[a]; dados.compra[a] = novo;
            if (pontosGastos() > catalogo.compra_pontos.total) { dados.compra[a] = antes; return; }
            valor.textContent = novo; atualizar();
          };
          const menos = el('button', {type: 'button', className: 'icon-button', textContent: '−', ariaLabel: `Diminuir ${nome(a)}`});
          const mais = el('button', {type: 'button', className: 'icon-button', textContent: '+', ariaLabel: `Aumentar ${nome(a)}`});
          menos.addEventListener('click', () => passoValor(-1));
          mais.addEventListener('click', () => passoValor(1));
          grade.append(el('div', {className: 'ability'}, el('span', {className: 'ability-name', textContent: nome(a)}), el('div', {className: 'stepper'}, menos, valor, mais)));
        }
        atualizar();
        extras.push(restante);
      }
      area.replaceChildren(metodo, ...extras, grade, blocoAumentos());
    };
    desenhar();
    return [area];
  }

  function blocoAumentos() {
    const bg = catalogo.antecedentes[dados.antecedente];
    const caixa = el('fieldset', {}, el('legend', {textContent: `Aumentos do antecedente ${bg.nome}: ${bg.atributos.map(nome).join(', ')}`}));
    const modos = el('div', {className: 'segmented', role: 'group', ariaLabel: 'Distribuição dos aumentos'});
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
        for (const [campo, rotulo] of [['aumento2', '+2 em'], ['aumento1', '+1 em']]) {
          const id = `bg-${campo}`;
          const select = el('select', {id}, el('option', {value: '', textContent: '—'}), ...bg.atributos.map((a) => el('option', {value: a, textContent: nome(a)})));
          select.value = dados[campo];
          select.addEventListener('change', () => { dados[campo] = select.value; });
          corpo.append(el('label', {htmlFor: id, textContent: rotulo}), select);
        }
      } else {
        corpo.append(el('p', {className: 'choice-meta', textContent: `+1 em ${bg.atributos.map(nome).join(', ')}.`}));
      }
    };
    desenhar();
    caixa.append(modos, corpo);
    return caixa;
  }

  function payload() {
    return {nome: dados.nome.trim(), especie: dados.especie, classe: dados.classe, nivel: 1, metodo_atributos: dados.metodo_atributos,
      atributos: base(), antecedente: dados.antecedente, aumentos_antecedente: aumentos(), talento_antecedente: dados.talento_antecedente || null};
  }

  function passoRevisao() {
    const b = base(); const au = aumentos();
    const grade = el('div', {className: 'ability-grid'});
    for (const a of ATRIBUTOS) {
      const total = b[a] + (au[a] || 0);
      grade.append(el('div', {className: 'ability'}, el('span', {className: 'ability-name', textContent: nome(a).slice(0, 3)}),
        el('span', {className: 'ability-value', textContent: total}),
        el('span', {className: 'ability-mod', textContent: `${b[a]}${au[a] ? ` + ${au[a]}` : ''} · mod ${mod(total)}`})));
    }
    const bg = catalogo.antecedentes[dados.antecedente];
    const talento = dados.talento_antecedente || bg.talento;
    return [el('h3', {textContent: dados.nome.trim()}),
      el('p', {className: 'choice-meta', textContent: `${nome(dados.especie)} · ${nome(dados.classe)} nível 1 · ${bg.nome}`}),
      grade,
      el('dl', {className: 'facts'}, el('dt', {textContent: 'Talento'}), el('dd', {textContent: talentoNome(talento)}),
        el('dt', {textContent: 'Perícias'}), el('dd', {textContent: bg.pericias.map(nome).join(', ')}),
        el('dt', {textContent: 'Ferramenta'}), el('dd', {textContent: bg.ferramenta})),
      el('p', {className: 'choice-meta', textContent: 'PV, Bônus de Proficiência e demais valores são calculados pelo motor de regras ao criar.'})];
  }

  function validarPasso() {
    if (passo === 0 && !dados.nome.trim()) return 'Dê um nome ao personagem.';
    if (passo === 1 && !dados.especie) return 'Escolha uma espécie.';
    if (passo === 2 && !dados.classe) return 'Escolha uma classe.';
    if (passo === 3) {
      if (!dados.antecedente) return 'Escolha um antecedente.';
      if (catalogo.antecedentes[dados.antecedente].talento === 'dadiva_sombria' && !dados.talento_antecedente) return 'Escolha uma Dádiva Sombria.';
    }
    if (passo === 4) {
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
  document.querySelector('#group-close').addEventListener('click', () => groupDialog.close());
  groupBack.addEventListener('click', abrirGrupo);
  groupButton.addEventListener('click', abrirGrupo);
  newCharacter.addEventListener('click', abrirCriacao);
})();
