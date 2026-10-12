const {test} = require('node:test');
const assert = require('node:assert/strict');
const {EnviosPendentes} = require('../frontend/envios-pendentes.js');
function storage() {
  const data = new Map();
  return {getItem: k => data.get(k) ?? null, setItem: (k,v) => data.set(k,v)};
}
test('repetição conserva id, inclusive após recriar o estado do navegador', () => {
  const local = storage();
  const initial = new EnviosPendentes(local, () => 'op-1').preparar('campanha', 'Conjuro');
  const replay = new EnviosPendentes(local, () => 'nao-usado').preparar('campanha', 'Conjuro');
  assert.equal(initial.id, replay.id);
  assert.equal(replay.repeticao, true);
  assert.equal(initial.repeticao, false);
});
test('mesmo texto após confirmação é uma ação nova', () => {
  let n = 0;
  const envios = new EnviosPendentes(storage(), () => `op-${++n}`);
  const first = envios.preparar('campanha', 'Ataco');
  envios.confirmar('campanha', first.id);
  assert.notEqual(envios.preparar('campanha', 'Ataco').id, first.id);
});
test('edição e outra campanha não reutilizam a chave anterior', () => {
  let n = 0;
  const envios = new EnviosPendentes(storage(), () => `op-${++n}`);
  const a = envios.preparar('a', 'Ataco');
  const b = envios.preparar('b', 'Ataco');
  const changed = envios.preparar('a', 'Curo');
  assert.equal(new Set([a.id, b.id, changed.id]).size, 3);
  envios.confirmar('a', a.id);
  assert.equal(envios.listar().a.id, changed.id);
  assert.equal(envios.listar().b.id, b.id);
});
test('erro de armazenamento ocorre antes de criar envio persistido', () => {
  const envios = new EnviosPendentes({getItem: () => null, setItem: () => {throw new Error('quota');}}, () => 'op-1');
  assert.throws(() => envios.preparar('a', 'Conjuro'), /quota/);
});
test('JSON inválido e entradas sem forma válida são ignorados', () => {
  const local = storage();
  local.setItem('dnd-mj-envios-pendentes', 'invalid');
  const envios = new EnviosPendentes(local);
  assert.deepEqual(envios.listar(), {});
  local.setItem(envios.chave, JSON.stringify({a: {id: 'op-1', texto: 'Mensagem'}, b: {id: null, texto: 'Mensagem'}}));
  assert.deepEqual(Object.keys(envios.listar()), ['a']);
});
