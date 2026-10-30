const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')

// Exercise the actual browser helper without a DOM or extra test dependencies.
const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/api.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText

function storage() {
  const values = new Map()
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }
}
function harness(fetchImpl = async () => new Response('{}', { status: 200 }), timers = {}) {
  const window = new EventTarget()
  window.localStorage = storage()
  window.sessionStorage = storage()
  const exports = {}
  const calls = []
  vm.runInNewContext(compiled, {
    exports, window, Headers, Event, Date, AbortController, setTimeout, clearTimeout, ...timers,
    process: { env: { NEXT_PUBLIC_API_URL: 'https://api.example.test/' } },
    fetch: async (...args) => { calls.push(args); return fetchImpl(...args) },
  })
  return { api: exports, window, calls }
}
function login(api, token = 'session-token', role = 'demo') {
  api.saveAuthSession({ success: true, message: 'OK', access_token: token, token_type: 'bearer', expires_in_seconds: 3600, role })
}

test('legacy password sessions are deleted and require a fresh login', () => {
  const { api, window } = harness()
  window.localStorage.setItem('stockscope_password', 'old-password')
  window.localStorage.setItem('stockscope_authenticated', 'true')
  assert.equal(api.getAuthSession(), null)
  assert.equal(window.localStorage.getItem('stockscope_password'), null)
  assert.equal(window.localStorage.getItem('stockscope_authenticated'), null)
})

test('session is stored only in sessionStorage and auth changes notify the UI', () => {
  const { api, window } = harness()
  let changes = 0
  window.addEventListener(api.AUTH_CHANGED_EVENT, () => changes++)
  login(api)
  assert.equal(api.getAuthSession().role, 'demo')
  assert.equal(window.localStorage.getItem('stockscope_session'), null)
  assert.ok(window.sessionStorage.getItem('stockscope_session'))
  api.clearAuthSession()
  assert.equal(api.getAuthSession(), null)
  assert.equal(changes, 2)
})

test('requests attach the current bearer token, preserve content headers, and prohibit redirects', async () => {
  const { api, calls } = harness()
  login(api)
  await api.apiFetch('/api/fundamentals/compare', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer stale' }, body: '{}' })
  assert.equal(calls[0][0], 'https://api.example.test/api/fundamentals/compare')
  assert.equal(calls[0][1].headers.get('Authorization'), 'Bearer session-token')
  assert.equal(calls[0][1].headers.get('Content-Type'), 'application/json')
  assert.equal(calls[0][1].cache, 'no-store')
  assert.equal(calls[0][1].redirect, 'error')
})

test('unauthenticated requests do not reach the network', async () => {
  const { api, calls } = harness()
  await assert.rejects(api.apiFetch('/api/stocks'), { status: 401 })
  assert.equal(calls.length, 0)
})

test('API rejects absolute URLs and password query credentials', async () => {
  const { api, calls } = harness()
  login(api)
  await assert.rejects(api.apiFetch('https://other.example/api/stocks'))
  await assert.rejects(api.apiFetch('/api/stocks?password=secret'))
  assert.equal(calls.length, 0)
})

test('401 invalidates the current session and notifies cache/UI consumers', async () => {
  const { api, window } = harness(async () => new Response('{}', { status: 401 }))
  login(api)
  let changes = 0
  window.addEventListener(api.AUTH_CHANGED_EVENT, () => changes++)
  await assert.rejects(api.apiFetch('/api/stocks'), { status: 401 })
  assert.equal(api.getAuthSession(), null)
  assert.equal(changes, 1)
})

test('an old request cannot log out a newer session', async () => {
  let finish
  const pending = new Promise(resolve => { finish = resolve })
  const { api } = harness(() => pending)
  login(api, 'old-token')
  const request = api.apiFetch('/api/stocks')
  login(api, 'new-token', 'admin')
  finish(new Response('{}', { status: 401 }))
  await assert.rejects(request, { status: 401 })
  assert.equal(api.getAuthSession().accessToken, 'new-token')
})

test('403 does not terminate an otherwise valid session', async () => {
  const { api } = harness(async () => new Response('{}', { status: 403 }))
  login(api)
  assert.equal((await api.apiFetch('/api/stocks/TEST', { method: 'DELETE' })).status, 403)
  assert.ok(api.getAuthSession())
})

test('expired or malformed stored sessions are rejected', () => {
  const { api, window } = harness()
  window.sessionStorage.setItem('stockscope_session', JSON.stringify({ accessToken: 'old', role: 'admin', expiresAt: Date.now() - 1 }))
  assert.equal(api.getAuthSession(), null)
  window.sessionStorage.setItem('stockscope_session', '{invalid')
  assert.equal(api.getAuthSession(), null)
})

test('incomplete login responses cannot create an authenticated session', () => {
  const { api } = harness()
  assert.throws(() => api.saveAuthSession({ success: true, message: 'Legacy response' }))
  assert.equal(api.getAuthSession(), null)
})


test('stalled reads time out and caller cancellation is preserved', async () => {
  let expire
  let delay
  const { api } = harness((_url, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true })
  }), { setTimeout: (callback, ms) => { expire = callback; delay = ms; return 1 }, clearTimeout: () => {} })
  login(api)
  const stalled = api.apiFetch('/api/stocks')
  assert.equal(delay, 45000)
  expire()
  await assert.rejects(stalled, error => error.status === 504 && /too long/.test(error.message))
  const controller = new AbortController()
  const cancelled = api.apiFetch('/api/stocks', { signal: controller.signal })
  controller.abort()
  await assert.rejects(cancelled, error => error.message === 'aborted' && error.status !== 504)
})
