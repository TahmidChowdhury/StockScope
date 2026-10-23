const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')
const compiled = ts.transpileModule(
  fs.readFileSync(`${__dirname}/workspace-drafts.ts`, 'utf8'),
  {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  },
).outputText
const api = {}
vm.runInNewContext(compiled, {
  exports: api,
  Date,
  Set,
  JSON,
  Object,
  Number,
  encodeURIComponent,
})
const valid = (value) =>
  !!value &&
  typeof value.text === 'string' &&
  typeof value.count === 'number' &&
  Number.isFinite(value.count)
const initial = { text: '', count: 0 }
function storage() {
  const values = new Map()
  return {
    values,
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  }
}
test('drafts survive a fresh store and separate API, access role, and workspace', () => {
  const local = storage()
  const key = api.workspaceDraftKey(
    'https://api.example',
    'admin',
    'scenario:AAPL',
  )
  const first = api.createDraftStore(local, key, initial, valid)
  first.setValue({ text: 'unsaved thesis', count: 3 })
  const restored = api
    .createDraftStore(local, key, initial, valid)
    .getSnapshot()
  assert.equal(restored.value.text, 'unsaved thesis')
  assert.equal(restored.status, 'saved')
  assert.ok(Date.parse(restored.savedAt))
  for (const different of [
    api.workspaceDraftKey('https://other.example', 'admin', 'scenario:AAPL'),
    api.workspaceDraftKey('https://api.example', 'guest', 'scenario:AAPL'),
    api.workspaceDraftKey('https://api.example', 'admin', 'scenario:MSFT'),
  ])
    assert.equal(
      api.createDraftStore(local, different, initial, valid).getSnapshot().value
        .text,
      '',
    )
  assert.deepEqual(Object.keys(JSON.parse(local.getItem(key))).sort(), [
    'updatedAt',
    'value',
    'version',
  ])
})
test('functional updates merge the latest browser copy and synchronize external clears', () => {
  const local = storage()
  const first = api.createDraftStore(local, 'key', initial, valid)
  const second = api.createDraftStore(local, 'key', initial, valid)
  first.setValue({ text: 'latest text', count: 1 })
  second.setValue((previous) => ({ ...previous, count: previous.count + 1 }))
  first.refresh()
  assert.equal(first.getSnapshot().value.text, 'latest text')
  assert.equal(first.getSnapshot().value.count, 2)
  second.reset()
  first.refresh()
  assert.equal(first.getSnapshot().status, 'empty')
})
test('reset affects one workspace and prevents an old asynchronous generation from recreating it', () => {
  const local = storage()
  const store = api.createDraftStore(local, 'one', initial, valid)
  store.setValue({ text: 'draft', count: 1 })
  local.setItem('other-workspace', 'keep')
  const generation = store.getSnapshot().generation
  store.reset()
  assert.equal(
    store.setValue({ text: 'late response', count: 2 }, generation),
    false,
  )
  assert.equal(local.getItem('one'), null)
  assert.equal(local.getItem('other-workspace'), 'keep')
})
test('quota or blocked storage retains edits in memory and reports that they were not saved', () => {
  const local = storage()
  local.setItem = () => {
    throw new Error('quota')
  }
  const store = api.createDraftStore(local, 'key', initial, valid)
  assert.equal(store.setValue({ text: 'new work', count: 2 }), false)
  assert.equal(store.getSnapshot().value.text, 'new work')
  assert.equal(store.getSnapshot().status, 'memory-only')
  store.refresh()
  assert.equal(store.getSnapshot().value.text, 'new work')
  assert.match(store.getSnapshot().message, /lost if you leave or refresh/)
  const blocked = api.createDraftStore(
    {
      getItem() {
        throw new Error('denied')
      },
      setItem: local.setItem,
      removeItem: local.removeItem,
    },
    'blocked',
    initial,
    valid,
  )
  assert.equal(blocked.getSnapshot().status, 'unavailable')
  blocked.setValue({ text: 'still editable', count: 3 })
  assert.equal(blocked.getSnapshot().value.text, 'still editable')
})
test('malformed, wrong-version, and invalid-shape drafts never become application state', () => {
  for (const raw of [
    '{broken',
    JSON.stringify({
      version: 9,
      updatedAt: new Date().toISOString(),
      value: initial,
    }),
    JSON.stringify({ version: 1, updatedAt: 'not a date', value: initial }),
    JSON.stringify({
      version: 1,
      updatedAt: new Date().toISOString(),
      value: { text: false, count: 1 },
    }),
  ]) {
    const local = storage()
    local.setItem('key', raw)
    const store = api.createDraftStore(local, 'key', initial, valid)
    assert.equal(store.getSnapshot().status, 'invalid')
    assert.equal(store.getSnapshot().value.text, '')
    store.reset()
    assert.equal(local.getItem('key'), null)
  }
})
