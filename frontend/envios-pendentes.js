/* A identidade do envio sobrevive a timeout, troca de campanha e recarga.
   A mesma mensagem pendente é uma repetição; edição é uma nova operação. */
class EnviosPendentes {
  constructor(storage, criarId = () => crypto.randomUUID()) {
    this.storage = storage;
    this.criarId = criarId;
    this.chave = 'dnd-mj-envios-pendentes';
  }

  listar() {
    let dados;
    try { dados = JSON.parse(this.storage.getItem(this.chave) || '{}'); }
    catch (_) { return {}; }
    if (!dados || typeof dados !== 'object' || Array.isArray(dados)) return {};
    return Object.fromEntries(Object.entries(dados).filter(([, op]) =>
      op && typeof op.id === 'string' && /^[a-zA-Z0-9_-]{1,64}$/.test(op.id)
      && typeof op.texto === 'string' && op.texto.length > 0 && op.texto.length <= 20000));
  }

  preparar(campanha, texto) {
    const dados = this.listar();
    const anterior = dados[campanha];
    if (anterior?.texto === texto) return {...anterior, repeticao: true};
    const operacao = {id: this.criarId(), texto};
    dados[campanha] = operacao;
    // Falhar antes de enviar se não for possível guardar a chave de repetição.
    this.storage.setItem(this.chave, JSON.stringify(dados));
    return {...operacao, repeticao: false};
  }

  confirmar(campanha, id) {
    const dados = this.listar();
    if (dados[campanha]?.id !== id) return;
    delete dados[campanha];
    this.storage.setItem(this.chave, JSON.stringify(dados));
  }
}
if (typeof module !== 'undefined') module.exports = {EnviosPendentes};
