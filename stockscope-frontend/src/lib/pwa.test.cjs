const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')

const source = fs.readFileSync(`${__dirname}/../../public/sw.js`, 'utf8')
const origin = 'https://stockscope.example'

function worker({ network = async () => new Response('live page'), cacheNames = [], failInstall = false } = {}) {
  const listeners = {}
  const stored = new Map()
  const added = []
  const opened = []
  const removed = []
  const fetched = []
  const offline = new Response('<h1>Let’s reconnect.</h1>', { headers: { 'Content-Type': 'text/html' } })
  const cache = {
    async add(request) {
      added.push(request)
      if (failInstall) throw new Error('Cannot cache fallback')
      stored.set(new URL(request.url).pathname, offline)
    },
    async match(url) { return stored.get(url)?.clone() },
  }

  vm.runInNewContext(source, {
    self: {
      location: { origin },
      addEventListener: (name, listener) => { listeners[name] = listener },
      skipWaiting: () => assert.fail('Must not force activation during an active session'),
      clients: { claim: () => assert.fail('Must not replace an active page controller') },
    },
    caches: {
      async open(name) { opened.push(name); return cache },
      async keys() { return cacheNames },
      async delete(name) { removed.push(name); return true },
    },
    async fetch(request) { fetched.push(request); return network(request) },
    Request: class extends Request {
      constructor(url, options) { super(new URL(url, origin), options) }
    },
    Response,
    URL,
  })

  return {
    added, opened, removed, fetched, stored,
    async lifecycle(name) {
      const pending = []
      listeners[name]({ waitUntil: (promise) => pending.push(promise) })
      await Promise.all(pending)
    },
    request(path, options = {}) {
      let intercepted = null
      listeners.fetch({
        request: { url: new URL(path, origin).href, method: 'GET', mode: 'navigate', ...options },
        respondWith: (promise) => { intercepted = promise },
      })
      return intercepted
    },
  }
}

test('installation stores only the anonymous public fallback and leaves updates waiting', async () => {
  const sw = worker({ cacheNames: ['stockscope-offline-v0', 'stockscope-offline-v1', 'another-app-cache'] })
  await sw.lifecycle('install')
  assert.equal(sw.added.length, 1)
  assert.equal(sw.added[0].url, `${origin}/offline.html`)
  assert.equal(sw.added[0].credentials, 'omit')
  assert.equal(sw.added[0].cache, 'reload')
  await sw.lifecycle('activate')
  assert.deepEqual(sw.removed, ['stockscope-offline-v0'])
})

test('a failed offline download rejects installation rather than replacing a working worker', async () => {
  const sw = worker({ failInstall: true })
  await assert.rejects(sw.lifecycle('install'), /Cannot cache fallback/)
})

test('online navigation returns fresh network content without caching private page content', async () => {
  const sw = worker({ network: async () => new Response('private workspace', { status: 200 }) })
  const response = await sw.request('/trading/portfolios/private-record')
  assert.equal(await response.text(), 'private workspace')
  assert.equal(sw.fetched.length, 1)
  assert.equal(sw.opened.length, 0)
  assert.equal(sw.added.length, 0)
})

test('offline page navigation uses the public fallback, never cached research', async () => {
  const sw = worker({ network: async () => { throw new TypeError('Offline') } })
  await sw.lifecycle('install')
  const response = await sw.request('/stock/AAPL?tab=news')
  assert.match(await response.text(), /Let’s reconnect/)
  assert.equal(sw.stored.size, 1)
  assert.ok(sw.stored.has('/offline.html'))
  sw.stored.clear()
  assert.equal((await sw.request('/stock/AAPL')).type, 'error')
})

test('APIs, auth calls, mutations, Next.js data and cross-origin requests bypass the worker', () => {
  const sw = worker({ network: async () => assert.fail('Should not intercept this request') })
  for (const [path, options] of [
    ['/api', {}],
    ['/api/auth/session', {}],
    ['/api/portfolios', { mode: 'cors' }],
    ['/trading', { method: 'POST' }],
    ['/stock/AAPL?_rsc=private', { mode: 'cors' }],
    ['/_next/static/chunks/app.js', { mode: 'no-cors' }],
    ['https://api.example/private', {}],
  ]) {
    assert.equal(sw.request(path, options), null, path)
  }
  assert.equal(sw.opened.length, 0)
})

test('server errors remain visible and are not presented as an offline success', async () => {
  const sw = worker({ network: async () => new Response('Server error', { status: 503 }) })
  assert.equal((await sw.request('/')).status, 503)
  assert.equal(sw.opened.length, 0)
})
