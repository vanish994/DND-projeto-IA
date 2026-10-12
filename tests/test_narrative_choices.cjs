const {test} = require('node:test');
const assert = require('node:assert/strict');
const {escolhasNarrativas} = require('../frontend/narrative-choices.js');
test('extrai opções explícitas sem markdown', () => {
  assert.deepEqual(escolhasNarrativas('O que você faz?\n1. **Entrar** no forte\n2. Buscar a floresta'), ['Entrar no forte', 'Buscar a floresta']);
});
test('não transforma inventário ou prosa em escolhas', () => {
  assert.deepEqual(escolhasNarrativas('Tesouro:\n1. Espada\n2. Escudo'), []);
  assert.deepEqual(escolhasNarrativas('O que você faz?\nVocê pode entrar ou sair.'), []);
});
test('exige duas a seis opções e aceita marcadores', () => {
  assert.deepEqual(escolhasNarrativas('Suas opções:\n- Entrar\n- Sair'), ['Entrar', 'Sair']);
  assert.deepEqual(escolhasNarrativas('Escolha o que fazer:\n1. Entrar'), []);
  assert.deepEqual(escolhasNarrativas('Suas opções:\n' + Array.from({length: 7}, (_, i) => `${i + 1}. Opção`).join('\n')), []);
});
test('para no fim da lista', () => {
  assert.deepEqual(escolhasNarrativas('Você pode escolher:\n1) Entrar\n2) Sair\nOutra ação é possível.\n3) não é opção'), ['Entrar', 'Sair']);
});
