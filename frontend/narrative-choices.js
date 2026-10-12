/* Apenas listas explicitamente apresentadas como escolhas, nunca regras ou loot. */
function escolhasNarrativas(texto) {
  const trecho = String(texto).split(/(?:escolha o que fazer|o que voc[eê] faz|suas op[çc][õo]es|voc[eê] pode escolher)\s*[:?]?/i);
  if (trecho.length < 2) return [];
  const linhas = trecho.at(-1).trim().split('\n').filter((linha) => linha.trim());
  const opcoes = [];
  for (const linha of linhas) {
    const item = linha.match(/^\s*(?:\d+[.)]|[-*])\s+(.+)$/);
    if (!item) break;
    opcoes.push(item[1].replace(/\*\*/g, '').trim());
  }
  return opcoes.length >= 2 && opcoes.length <= 6 ? opcoes : [];
}
if (typeof module !== 'undefined') module.exports = { escolhasNarrativas };
