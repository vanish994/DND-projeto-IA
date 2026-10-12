/* Animação de dados do Rule Engine.
 *
 * Toda rolagem exibida aqui vem pronta do motor (`rolagens` na resposta do
 * backend ou no retorno das ações do mapa tático). Este módulo não sorteia
 * nenhum número: ele apenas apresenta valor, modificador, total, CD/CA e o
 * veredito que o motor já calculou.
 *
 * Uso:
 *   Dados.animar(rolagens)            -> Promise resolvida quando a animação acaba
 *   Dados.cartao(rolagens)            -> elemento com o resumo fixo das rolagens
 *   Dados.normalizarMapa(resposta)    -> registros a partir da resposta do mapa
 */
(() => {
  'use strict';

  const MAXIMO_NA_FILA = 12;
  const DURACAO_GIRO = 1100;
  const PAUSA_LEITURA = 2000;
  // Acima disso, as rolagens extras entram só como resumo: turnos com muitos
  // dados não podem segurar a narração por vários segundos.
  const MAXIMO_ANIMADO = 3;

  const VEREDITOS = {
    critico: {rotulo: 'Crítico!', classe: 'critico'},
    acerto: {rotulo: 'Acerto', classe: 'sucesso'},
    erro: {rotulo: 'Erro', classe: 'falha'},
    sucesso: {rotulo: 'Sucesso', classe: 'sucesso'},
    falha: {rotulo: 'Falha', classe: 'falha'},
    dano: {rotulo: 'Dano', classe: 'dano'},
    pendente: {rotulo: 'Aguardando CD', classe: 'pendente'},
    bloqueado: {rotulo: 'Bloqueado', classe: 'pendente'},
    rolado: {rotulo: 'Rolado', classe: 'neutro'},
  };

  const ROTULOS_TIPO = {
    ataque: 'Ataque', iniciativa: 'Iniciativa', teste: 'Teste',
    salvaguarda: 'Salvaguarda', dano: 'Dano', rolagem: 'Rolagem',
  };

  // Como o motor aplicou as defesas de dano do alvo (campo defesas_dano.aplicacao).
  const APLICACAO_DANO = {
    imunidade: 'imune ao tipo',
    resistencia: 'resistência: metade',
    vulnerabilidade: 'vulnerabilidade: dobro',
  };

  const ROTULOS_ATRIBUTO = {
    forca: 'Força', destreza: 'Destreza', constituicao: 'Constituição',
    inteligencia: 'Inteligência', sabedoria: 'Sabedoria', carisma: 'Carisma',
    strength: 'Força', dexterity: 'Destreza', constitution: 'Constituição',
    intelligence: 'Inteligência', wisdom: 'Sabedoria', charisma: 'Carisma',
  };

  const nomeAtributo = (valor) => {
    const chave = String(valor || '').trim().toLowerCase();
    return ROTULOS_ATRIBUTO[chave] || (chave ? chave.charAt(0).toUpperCase() + chave.slice(1) : 'criatura');
  };

  const fila = [];
  let ocupado = false;
  let pedidoDeSaida = null;

  const reduzido = () => {
    try {
      return Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
    } catch (_) {
      return false;
    }
  };

  function el(tag, props = {}, ...filhos) {
    const no = document.createElement(tag);
    for (const [chave, valor] of Object.entries(props)) {
      if (valor === null || valor === undefined || valor === false) continue;
      if (chave === 'className') no.className = valor;
      else if (chave === 'texto') no.textContent = valor;
      else if (chave === 'dataset') Object.assign(no.dataset, valor);
      else if (chave.startsWith('on')) no.addEventListener(chave.slice(2), valor);
      else no.setAttribute(chave, valor);
    }
    for (const filho of filhos.flat()) {
      if (filho === null || filho === undefined || filho === false) continue;
      no.append(typeof filho === 'string' ? document.createTextNode(filho) : filho);
    }
    return no;
  }

  const paraInteiro = (valor) => {
    const numero = Number.parseInt(valor, 10);
    return Number.isFinite(numero) ? numero : null;
  };

  function listaDeInteiros(valor) {
    if (valor === null || valor === undefined) return [];
    const bruto = Array.isArray(valor) ? valor : [valor];
    return bruto.map(paraInteiro).filter((numero) => numero !== null);
  }

  /* ------------------------------------------------------------------ *
   * Normalização
   * ------------------------------------------------------------------ */

  function normalizar(entrada, extras = {}) {
    if (!entrada || typeof entrada !== 'object') return null;
    const tipo = String(entrada.tipo || extras.tipo || 'rolagem').toLowerCase();
    const lados = paraInteiro(entrada.lados) || 20;
    const valor = paraInteiro(entrada.valor);
    const rolagens = listaDeInteiros(entrada.rolagens);
    if (valor === null && !rolagens.length && !entrada.expressao) return null;
    const registros = rolagens.length ? rolagens : valor === null ? [] : [valor];
    const dadosFinais = registros.length ? registros : listaDeInteiros(entrada.dados);
    return {
      tipo,
      dado: entrada.dado || `d${lados}`,
      lados,
      valor,
      rolagens: dadosFinais,
      modificador: paraInteiro(entrada.modificador) || 0,
      total: paraInteiro(entrada.total),
      expressao: entrada.expressao || null,
      dificuldade: paraInteiro(entrada.dificuldade),
      // Aceita o formato da API (snake_case) e o já normalizado (camelCase),
      // para que renormalizar um cartão não perca CD/CA nem o 1 natural.
      dificuldadeTipo: entrada.dificuldadeTipo || entrada.dificuldade_tipo || null,
      resultado: String(entrada.resultado || 'rolado').toLowerCase(),
      sucesso: entrada.sucesso === true ? true : entrada.sucesso === false ? false : null,
      critico: Boolean(entrada.critico),
      naturalUm: Boolean(entrada.naturalUm || entrada.natural_1) || (lados === 20 && valor === 1),
      vantagem: Boolean(entrada.vantagem),
      desvantagem: Boolean(entrada.desvantagem),
      rotulo: entrada.rotulo || extras.rotulo || ROTULOS_TIPO[tipo] || 'Rolagem',
      personagem: entrada.personagem || extras.personagem || null,
      alvo: entrada.alvo || extras.alvo || null,
      motivo: entrada.motivo || null,
      seed: entrada.seed || null,
      dano: entrada.dano && typeof entrada.dano === 'object' ? entrada.dano : null,
      origem: entrada.origem || extras.origem || 'rule_engine',
    };
  }

  function normalizarLista(entrada, extras = {}) {
    const itens = Array.isArray(entrada) ? entrada : [entrada];
    return itens.map((item) => normalizar(item, extras)).filter(Boolean);
  }

  /** Lados do dado a partir de uma expressão como "1d8" ou "2d6 + 3". */
  function ladosDaExpressao(expressao) {
    const encontrado = /d\s*(\d+)/i.exec(String(expressao || ''));
    return encontrado ? paraInteiro(encontrado[1]) : null;
  }

  function roladorDeSalvaguarda(salvaguarda, extras = {}) {
    const valor = paraInteiro(salvaguarda.dado ?? salvaguarda.rolagem ?? salvaguarda.valor);
    if (valor === null) return null;
    const total = paraInteiro(salvaguarda.total);
    const cd = paraInteiro(salvaguarda.cd ?? salvaguarda.dc);
    const sucesso = salvaguarda.sucesso === true ? true : salvaguarda.sucesso === false ? false : null;
    const dadosSave = listaDeInteiros(salvaguarda.rolagens || salvaguarda.dados_rolados);
    return normalizar({
      tipo: 'salvaguarda',
      dado: 'd20',
      lados: 20,
      valor,
      rolagens: dadosSave.length ? dadosSave : [valor],
      modificador: total !== null ? total - valor : 0,
      total,
      dificuldade: cd,
      dificuldade_tipo: 'cd',
      resultado: extras.resultado || (sucesso === true ? 'sucesso' : sucesso === false ? 'falha' : 'rolado'),
      sucesso,
      rotulo: extras.rotulo || `Salvaguarda de ${nomeAtributo(extras.atributo || salvaguarda.atributo)}`,
      personagem: extras.personagem || null,
      alvo: extras.alvo || null,
    }, {origem: 'rule_engine'});
  }

  /** Rótulo legível para ataques de arma, de monstro e de magia do mapa tático. */
  function rotuloDoAtaque(resposta, alvo) {
    const arma = String(resposta.arma || '').trim();
    const magia = String(resposta.magia || '').trim();
    const monstro = String(resposta.monstro || '').trim();
    const acao = String(resposta.acao || '').trim();
    let base;
    // Ataque com magia (truque ou magia de ataque) é identificado como tal.
    if (magia) base = `Ataque de magia: ${magia}${arma && arma !== magia ? ` (${arma})` : ''}`;
    else if (monstro && acao) base = `${acao} de ${monstro}`;
    else if (monstro) base = `Ataque de ${monstro}`;
    else if (/^ataque/i.test(arma)) base = arma;
    else if (arma) base = `Ataque com ${arma}`;
    else base = 'Jogada de ataque';
    if (alvo && !/\bcontra\b/i.test(base)) base += ` contra ${alvo}`;
    return base;
  }

  /** Converte a resposta de /mapa-tatico/atacar, /ataque-monstro e /conjurar. */
  function normalizarMapa(resposta, extras = {}) {
    if (!resposta || typeof resposta !== 'object') return [];
    if (Array.isArray(resposta.ataques_resolvidos)) {
      return resposta.ataques_resolvidos.flatMap((item) => normalizarMapa(item, extras));
    }

    const registros = [];
    const ataque = resposta.ataque || {};
    const rolagens = listaDeInteiros(resposta.rolagens || ataque.rolls);
    const valor = paraInteiro(resposta.rolagem ?? ataque.roll) ?? (rolagens.length ? rolagens[0] : null);
    const armas = Array.isArray(ataque.damage_dice) ? ataque.damage_dice : [];
    const nomePorId = typeof extras.nomePorId === 'function' ? extras.nomePorId : () => null;
    const quem = (indicador) => (indicador ? nomePorId(indicador) || String(indicador) : null);

    // Vantagem/desvantagem vêm da geometria do motor; com dois dados, o que fica
    // é o maior (vantagem) ou o menor (desvantagem).
    const estadoJogada = String((resposta.geometria || {}).estado_jogada || '').toLowerCase();
    const temVantagem = Boolean(ataque.advantage) || estadoJogada === 'vantagem' || (rolagens.length > 1 && valor === Math.max(...rolagens));
    const temDesvantagem = Boolean(ataque.disadvantage) || estadoJogada === 'desvantagem' || (rolagens.length > 1 && valor === Math.min(...rolagens));

    if (valor !== null) {
      registros.push(normalizar({
        tipo: 'ataque',
        dado: 'd20',
        lados: 20,
        valor,
        rolagens: rolagens.length ? rolagens : [valor],
        modificador: paraInteiro(resposta.bonus_ataque) || 0,
        total: paraInteiro(ataque.total) ?? (valor !== null ? valor + (paraInteiro(resposta.bonus_ataque) || 0) : null),
        dificuldade: paraInteiro(resposta.ca_alvo ?? ataque.target_ac),
        dificuldade_tipo: 'ca',
        resultado: ataque.result === 'hit' ? 'acerto' : ataque.result === 'miss' ? 'erro' : 'rolado',
        sucesso: ataque.result === 'hit',
        critico: Boolean(ataque.critical),
        natural_1: ataque.reason === 'natural_1',
        vantagem: temVantagem,
        desvantagem: temDesvantagem,
        rotulo: rotuloDoAtaque(resposta, extras.alvo),
        personagem: extras.personagem || resposta.monstro || null,
        alvo: extras.alvo || quem(resposta.alvo_id) || null,
        motivo: ataque.reason || null,
        seed: ataque.seed || null,
      }, {origem: 'rule_engine'}));
    }

    const dadosDano = listaDeInteiros(resposta.dados_dano).length ? listaDeInteiros(resposta.dados_dano) : listaDeInteiros(armas);
    const dano = paraInteiro(resposta.dano);
    const aplicacao = resposta.defesas_dano && resposta.defesas_dano.aplicacao;
    if (dano !== null && dano > 0) {
      const expressao = resposta.dano_expressao || null;
      registros.push(normalizar({
        tipo: 'dano',
        dado: 'dano',
        lados: ladosDaExpressao(expressao) || 6,
        valor: null,
        rolagens: dadosDano,
        modificador: paraInteiro(resposta.dano_modificador) || 0,
        total: dano,
        expressao: expressao || (dadosDano.length ? `${dadosDano.length}d6` : null),
        resultado: 'dano',
        critico: Boolean(ataque.critical),
        rotulo: resposta.magia ? `Dano de ${resposta.magia}`
          : resposta.arma ? `Dano de ${resposta.arma}`
          : resposta.tipo_dano ? `Dano ${resposta.tipo_dano}` : 'Dano',
        personagem: extras.personagem || resposta.monstro || null,
        alvo: extras.alvo || null,
        motivo: APLICACAO_DANO[aplicacao] || null,
      }, {origem: 'rule_engine'}));
    }

    for (const efeito of resposta.efeitos || []) {
      if (!efeito || typeof efeito !== 'object' || efeito.tipo !== 'salvaguarda_apos_ataque') continue;
      const registro = roladorDeSalvaguarda(efeito, {atributo: efeito.atributo, personagem: extras.alvo || null});
      if (registro) registros.push(registro);
    }

    for (const linha of resposta.salvaguardas_resolvidas || []) {
      const registro = roladorDeSalvaguarda(linha, {
        personagem: quem(linha.token_id),
        rotulo: `Salvaguarda contra ${linha.condicao || 'o efeito'}`,
        resultado: linha.encerrada === true ? 'sucesso' : linha.encerrada === false ? 'falha' : null,
      });
      if (registro) registros.push(registro);
    }

    for (const area of resposta.resultados_area || []) {
      const extraAlvo = {personagem: area.nome || null, alvo: area.nome || null};
      if (area.salvaguarda) {
        const atributo = area.salvaguarda.atributo;
        const registro = roladorDeSalvaguarda(area.salvaguarda, {
          ...extraAlvo,
          atributo,
          rotulo: atributo ? null : `Salvaguarda de ${area.nome || 'criatura'}${resposta.magia ? ` contra ${resposta.magia}` : ''}`,
        });
        if (registro) registros.push(registro);
      }
      const dadosArea = listaDeInteiros(area.dados_dano);
      if (paraInteiro(area.dano) > 0) {
        registros.push(normalizar({
          tipo: 'dano',
          dado: 'dano',
          lados: ladosDaExpressao(resposta.dano_expressao) || 6,
          valor: null,
          rolagens: dadosArea,
          modificador: 0,
          total: paraInteiro(area.dano),
          expressao: dadosArea.length ? `${dadosArea.length}d${ladosDaExpressao(resposta.dano_expressao) || 6}` : null,
          resultado: 'dano',
          rotulo: resposta.magia ? `Dano de ${resposta.magia}` : 'Dano em área',
          personagem: area.nome || null,
          alvo: area.nome || null,
        }, {origem: 'rule_engine'}));
      }
    }

    return registros.filter(Boolean);
  }

  /** Uma rolagem por participante vindo de /mapa-tatico/iniciativa/iniciar. */
  function normalizarIniciativa(iniciativa) {
    if (!Array.isArray(iniciativa)) return [];
    return iniciativa.map((linha) => normalizar({
      tipo: 'iniciativa',
      dado: 'd20',
      lados: 20,
      valor: paraInteiro(linha.rolagem),
      rolagens: [paraInteiro(linha.rolagem)],
      modificador: paraInteiro(linha.destreza) || 0,
      total: paraInteiro(linha.total),
      resultado: 'rolado',
      rotulo: `Iniciativa de ${linha.nome || 'criatura'}`,
      personagem: linha.nome || null,
      origem: 'rule_engine',
    })).filter(Boolean);
  }

  /* ------------------------------------------------------------------ *
   * Texto acessível
   * ------------------------------------------------------------------ */

  function vereditoDa(rolagem) {
    if (rolagem.critico && rolagem.tipo === 'ataque') return VEREDITOS.critico;
    if (rolagem.naturalUm && rolagem.dificuldade !== null) return VEREDITOS.falha;
    if (rolagem.tipo === 'dano') return VEREDITOS.dano;
    if (rolagem.resultado && VEREDITOS[rolagem.resultado]) return VEREDITOS[rolagem.resultado];
    if (rolagem.sucesso === true) return VEREDITOS.sucesso;
    if (rolagem.sucesso === false) return VEREDITOS.falha;
    return VEREDITOS.rolado;
  }

  /** Monta "17 + 6 = 23 contra CA 15" a partir do que o motor devolveu. */
  function formulaDa(rolagem) {
    const valores = (rolagem.tipo === 'dano' ? rolagem.rolagens : [rolagem.valor])
      .filter((valor) => valor !== null && valor !== undefined);
    const partes = valores.length ? valores.map(String) : ['—'];
    let conta = partes[0];
    for (const parte of partes.slice(1)) conta += ` + ${parte}`;
    if (rolagem.modificador > 0) conta += ` + ${rolagem.modificador}`;
    else if (rolagem.modificador < 0) conta += ` − ${Math.abs(rolagem.modificador)}`;

    if (rolagem.tipo === 'dano') {
      const total = rolagem.total;
      // Dano sem dados (ataque desarmado, efeito fixo): só o valor aplicado.
      if (!valores.length) return rolagem.motivo ? `${total ?? '—'} · ${rolagem.motivo}` : String(total ?? '—');
      const soma = valores.reduce((acumulado, valor) => acumulado + valor, 0) + rolagem.modificador;
      // Quando o motor ajusta o total (defesas, metade por salvaguarda), a seta
      // mostra o valor aplicado sem fingir que a soma fecha.
      const sinal = total === null || total === undefined ? '='
        : valores.length && soma === total ? '=' : '→';
      let texto = `${conta} ${sinal} ${total ?? '—'}`;
      if (rolagem.motivo) texto += ` · ${rolagem.motivo}`;
      return texto;
    }

    let texto = `${conta} = ${rolagem.total ?? '—'}`;
    if (rolagem.dificuldade !== null && rolagem.dificuldade !== undefined) {
      texto += ` contra ${rolagem.dificuldadeTipo === 'ca' ? 'CA' : 'CD'} ${rolagem.dificuldade}`;
    }
    if (rolagem.vantagem) texto += ' (vantagem)';
    if (rolagem.desvantagem) texto += ' (desvantagem)';
    return texto;
  }

  /** Frase única para leitores de tela anúnciarem a rolagem inteira. */
  function frase(rolagem) {
    const rotulo = rolagem.rotulo || 'Rolagem';
    const alvo = rolagem.alvo && !rotulo.toLowerCase().includes(String(rolagem.alvo).toLowerCase())
      ? ` em ${rolagem.alvo}` : '';
    const dono = rolagem.personagem && !rotulo.includes(rolagem.personagem) ? `${rolagem.personagem}: ` : '';
    if (rolagem.tipo === 'dano') {
      // "Dano de X. Dano 1 + 3 = 4. Dano" repetiria a palavra três vezes.
      return `${dono}${rotulo}${alvo}. ${formulaDa(rolagem)} de dano.`;
    }
    return `${dono}${rotulo}${alvo}. ${rolagem.dado} ${formulaDa(rolagem)}. ${vereditoDa(rolagem).rotulo}`;
  }

  /* ------------------------------------------------------------------ *
   * Camada de animação
   * ------------------------------------------------------------------ */

  function svgDado(lados) {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 100 100');
    svg.setAttribute('class', 'dado-forma');
    svg.setAttribute('aria-hidden', 'true');
    // Linhas curtas que ligam o rosto central aos vértices do hexágono.
    const linhas = [
      [50, 4, 50, 22], [7, 27, 22, 26], [93, 27, 78, 26],
      [7, 73, 22, 68], [93, 73, 78, 68], [50, 96, 50, 72],
    ];
    const adicionar = (tag, atributos) => {
      const no = document.createElementNS(ns, tag);
      for (const [chave, valor] of Object.entries(atributos)) no.setAttribute(chave, valor);
      svg.append(no);
      return no;
    };
    adicionar('polygon', {class: 'dado-aresta', points: '50,4 93,27 93,73 50,96 7,73 7,27'});
    adicionar('polygon', {class: 'dado-face', points: '22,26 78,26 50,72'});
    for (const [x1, y1, x2, y2] of linhas) {
      adicionar('line', {class: 'dado-aresta-fina', x1, y1, x2, y2});
    }
    svg.dataset.lados = String(lados);
    return svg;
  }

  function criarGlifoDado(rolagem) {
    const palco = el('div', {className: 'dado-glifo', dataset: {tipo: rolagem.tipo}});
    const giro = el('div', {className: 'dado-giro'}, svgDado(rolagem.lados));
    const numero = el('span', {className: 'dado-numero', texto: rolagem.valor === null ? '—' : String(rolagem.valor)});
    palco.append(giro, numero);
    return {palco, numero};
  }

  function criarBandeja(rolagem) {
    const bandeja = el('div', {className: 'dado-bandeja', dataset: {tipo: 'dano'}});
    const valores = rolagem.rolagens.length ? rolagem.rolagens : [rolagem.total ?? 0];
    const faces = valores.map((valor) => {
      const face = el('div', {className: 'dado-pequeno', dataset: {lados: String(rolagem.lados)}},
        el('span', {className: 'dado-pequeno-numero', texto: String(valor)}));
      bandeja.append(face);
      return face;
    });
    return {palco: bandeja, faces};
  }

  function montarDetalhes(rolagem, indice, total) {
    const veredito = vereditoDa(rolagem);
    const titulo = rolagem.tipo === 'dano' ? 'Rolagem de dano' : `Rolagem de ${rolagem.dado}`;
    return el('div', {className: 'dado-detalhes'},
      el('p', {className: 'dado-progresso', texto: total > 1 ? `${indice + 1} de ${total} · ${titulo}` : titulo}),
      el('p', {className: 'dado-rotulo', texto: rolagem.rotulo}),
      el('p', {className: 'dado-formula', texto: rolagem.tipo === 'dano' ? (rolagem.expressao || 'Dano') : `${rolagem.dado} · ${formulaDa(rolagem)}`}),
      el('p', {className: 'dado-veredito', dataset: {classe: veredito.classe}, texto: veredito.rotulo}),
      rolagem.personagem ? el('p', {className: 'dado-personagem', texto: rolagem.personagem}) : null,
    );
  }

  function abrirCamada(rolagem, indice, total) {
    return new Promise((resolver) => {
      const anterior = document.querySelector('.dado-camada');
      if (anterior) anterior.remove();

      const legenda = el('p', {className: 'visually-hidden', texto: frase(rolagem)});
      const palco = el('div', {className: 'dado-palco'});
      const continuar = el('button', {type: 'button', className: 'dado-continuar primary-button', texto: total > 1 && indice + 1 < total ? 'Próxima rolagem' : 'Continuar'});
      const painel = el('div', {className: 'dado-painel', dataset: {classe: vereditoDa(rolagem).classe, tipo: rolagem.tipo}},
        el('div', {className: 'dado-brilho'}),
        palco,
        continuar,
      );
      const camada = el('div', {
        className: 'dado-camada',
        role: 'dialog',
        'aria-modal': 'true',
        'aria-label': 'Rolagem do motor de regras',
        tabindex: '-1',
      }, legenda, painel);

      let finalizado = false;
      let temporizador = null;
      let animador = null;
      let agendamento = null;
      const concluir = () => {
        if (finalizado) return;
        finalizado = true;
        if (temporizador) clearTimeout(temporizador);
        if (animador) clearInterval(animador);
        if (agendamento) clearTimeout(agendamento);
        camada.remove();
        document.body.classList.remove('dado-aberto');
        document.removeEventListener('keydown', aoTeclar, true);
        document.removeEventListener('focusin', prenderFoco);
        if (pedidoDeSaida === concluir) pedidoDeSaida = null;
        resolver();
      };
      const aoTeclar = (evento) => {
        if (evento.key === 'Escape' || evento.key === ' ' || evento.key === 'Enter') {
          evento.preventDefault();
          evento.stopPropagation();
          concluir();
        }
      };

      if (rolagem.tipo === 'dano') {
        const {palco: bandeja, faces} = criarBandeja(rolagem);
        palco.append(bandeja);
        if (!reduzido()) {
          faces.forEach((face) => face.classList.add('girando'));
          const lados = rolagem.lados || 6;
          animador = setInterval(() => {
            faces.forEach((face, indiceFace) => {
              const alvo = face.querySelector('.dado-pequeno-numero');
              const base = rolagem.rolagens[indiceFace] || 1;
              const desvio = (Math.random() < .5 ? -1 : 1) * (1 + Math.floor(Math.random() * 3));
              alvo.textContent = String(Math.min(lados, Math.max(1, base + desvio)));
            });
          }, 90);
        }
      } else {
        const {palco: glifo, numero} = criarGlifoDado(rolagem);
        palco.append(glifo);
        if (!reduzido()) {
          glifo.classList.add('girando');
          const valores = rolagem.rolagens.length > 1 ? rolagem.rolagens : [rolagem.valor ?? 20];
          animador = setInterval(() => {
            const sorteio = Math.floor(Math.random() * (rolagem.lados || 20)) + 1;
            numero.textContent = String(Math.random() < .22 ? valores[Math.floor(Math.random() * valores.length)] : sorteio);
          }, 70);
        }
      }

      // Com várias rolagens na fila, cada uma passa mais rápido que a anterior.
      const pausa = reduzido() ? 700 : (indice + 1 < total ? 1000 : PAUSA_LEITURA);
      const atrasoDoGiro = reduzido() ? 120 : DURACAO_GIRO;
      const entrada = () => {
        if (finalizado) return;
        if (animador) { clearInterval(animador); animador = null; }
        palco.querySelectorAll('.girando').forEach((no) => no.classList.remove('girando'));
        const alvo = palco.querySelector('.dado-numero');
        if (alvo) alvo.textContent = String(rolagem.valor ?? '—');
        if (rolagem.tipo === 'dano') {
          const valores = rolagem.rolagens.length ? rolagem.rolagens : [rolagem.total ?? 0];
          palco.querySelectorAll('.dado-pequeno-numero').forEach((no, indiceFace) => {
            no.textContent = String(valores[indiceFace] ?? rolagem.total ?? 0);
          });
        }
        const detalhes = montarDetalhes(rolagem, indice, total);
        const existente = painel.querySelector('.dado-detalhes');
        if (existente) existente.replaceWith(detalhes);
        else painel.insertBefore(detalhes, continuar);
        painel.classList.add('assentou');
        temporizador = setTimeout(concluir, pausa);
      };

      const prenderFoco = (evento) => {
        if (!camada.contains(evento.target)) {
          evento.stopPropagation();
          continuar.focus({preventScroll: true});
        }
      };
      // Enquanto o dado gira, o painel do dado é a única região interativa.
      document.body.classList.add('dado-aberto');
      document.addEventListener('focusin', prenderFoco);
      painel.addEventListener('pointerenter', () => { if (temporizador) { clearTimeout(temporizador); temporizador = null; } });
      painel.addEventListener('pointerleave', () => {
        if (!finalizado && !temporizador && painel.classList.contains('assentou')) temporizador = setTimeout(concluir, 1400);
      });
      continuar.addEventListener('click', (evento) => { evento.stopPropagation(); concluir(); });
      camada.addEventListener('click', (evento) => { evento.stopPropagation(); concluir(); });
      painel.addEventListener('click', (evento) => { if (evento.target === painel || evento.target === palco) evento.stopPropagation(); });
      document.addEventListener('keydown', aoTeclar, true);
      pedidoDeSaida = concluir;
      document.body.append(camada);
      continuar.focus({preventScroll: true});
      agendamento = setTimeout(entrada, atrasoDoGiro);
    });
  }

  async function processar(item) {
    const {rolagens, opcoes, resolver} = item;
    const limite = Math.max(1, paraInteiro(opcoes.maximo) || rolagens.length);
    const animadas = rolagens.slice(0, Math.min(limite, rolagens.length));
    try {
      for (let indice = 0; indice < animadas.length; indice += 1) {
        await abrirCamada(animadas[indice], indice, animadas.length);
      }
      opcoes.aoFinal?.(rolagens);
      resolver(rolagens);
    } catch (erro) {
      // Falha na apresentação nunca deve travar a conversa.
      console.warn('Não foi possível animar a rolagem:', erro);
      resolver(rolagens);
    }
  }

  async function esvaziarFila() {
    if (ocupado) return;
    ocupado = true;
    try {
      while (fila.length) await processar(fila.shift());
    } finally {
      ocupado = false;
    }
  }

  /** Anima as rolagens em sequência e resolve quando todas terminam.

  ``opcoes.maximo`` limita quantos dados giram; as demais rolagens entram
  apenas no resumo fixo da mensagem. */
  function animar(entrada, opcoes = {}) {
    const rolagens = normalizarLista(entrada).slice(0, MAXIMO_NA_FILA);
    if (!rolagens.length) return Promise.resolve([]);
    if (fila.length >= MAXIMO_NA_FILA * 2) return Promise.resolve(rolagens);
    return new Promise((resolver) => {
      fila.push({rolagens, opcoes, resolver});
      esvaziarFila().catch(() => resolver(rolagens));
    });
  }

  /** Interrompe qualquer animação em curso (usado ao fechar a campanha). */
  function interromper() {
    fila.length = 0;
    pedidoDeSaida?.();
  }

  /* ------------------------------------------------------------------ *
   * Resumo fixo na mensagem
   * ------------------------------------------------------------------ */

  function linhaDaRolagem(rolagem) {
    const veredito = vereditoDa(rolagem);
    return el('li', {className: 'rolagem-item', dataset: {tipo: rolagem.tipo, classe: veredito.classe}},
      el('span', {className: 'rolagem-dado', texto: rolagem.tipo === 'dano' ? (rolagem.expressao || rolagem.dado) : rolagem.dado}),
      el('span', {className: 'rolagem-corpo'},
        el('span', {className: 'rolagem-titulo', texto: rolagem.rotulo}),
        el('span', {className: 'rolagem-formula', texto: formulaDa(rolagem)}),
      ),
      el('span', {className: 'rolagem-veredito', texto: veredito.rotulo}),
    );
  }

  /** Cartão com o resumo das rolagens de uma mensagem (sem animação). */
  function cartao(entrada, opcoes = {}) {
    const rolagens = normalizarLista(entrada);
    if (!rolagens.length) return null;
    const lista = el('ul', {className: 'rolagem-lista'}, rolagens.map(linhaDaRolagem));
    const repetir = el('button', {
      type: 'button', className: 'rolagem-repetir text-button',
      'aria-label': rolagens.length > 1 ? 'Repetir a animação das rolagens desta mensagem' : 'Repetir a animação deste dado',
      texto: 'Ver o dado',
    });
    repetir.addEventListener('click', () => animar(rolagens));
    const caixa = el('div', {className: 'rolagem-cartao', role: 'group', 'aria-label': 'Rolagens do motor de regras'},
      el('p', {className: 'rolagem-titulo-grupo', texto: rolagens.length > 1 ? `Rolagens do motor (${rolagens.length})` : 'Rolagem do motor'}),
      lista,
      repetir,
    );
    if (opcoes.somenteLeitura) repetir.remove();
    return caixa;
  }

  const api = {
    animar, cartao, interromper, frase, formulaDa, normalizar, normalizarLista,
    normalizarMapa, normalizarIniciativa, vereditoDa,
  };
  if (typeof window !== 'undefined') {
    window.Dados = api;
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
  }
})();
