const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')

const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/mobile-scroll.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText

function environment({ mobile = true } = {}) {
  function events(target = {}) {
    const listeners = new Map()
    target.addEventListener = (name, listener) => {
      if (!listeners.has(name)) listeners.set(name, new Set())
      listeners.get(name).add(listener)
    }
    target.removeEventListener = (name, listener) => listeners.get(name)?.delete(listener)
    target.emit = (name) => [...(listeners.get(name) ?? [])].forEach((listener) => listener())
    return target
  }
  const frames = new Map()
  const observers = new Set()
  const targets = new Map()
  let frameId = 0
  let entryId = 0
  let historyIndex = 0
  const entries = [{ url: new URL('https://stockscope.example/'), state: { __NA: true, __PRIVATE_NEXTJS_INTERNALS_TREE: ['initial'] } }]
  class Observer {
    constructor(callback) { this.callback = callback }
    observe() { observers.add(this) }
    disconnect() { observers.delete(this) }
  }
  const window = events({
    location: entries[0].url,
    crypto: { randomUUID: () => `entry-${++entryId}` },
    history: {
      get state() { return entries[historyIndex].state },
      replaceState(state) { entries[historyIndex].state = state },
    },
    matchMedia: () => ({ matches: mobile }),
    requestAnimationFrame: (callback) => { frames.set(++frameId, callback); return frameId },
    cancelAnimationFrame: (id) => frames.delete(id),
  })
  const api = {}
  vm.runInNewContext(compiled, {
    exports: api, window, document: { getElementById: (id) => targets.get(id) },
    ResizeObserver: Observer, MutationObserver: Observer, URL, Map, Math, decodeURIComponent,
  })
  const flush = () => {
    const pending = [...frames.values()]
    frames.clear()
    pending.forEach((callback) => callback())
  }
  return {
    window, targets, observers, flush,
    manager: () => api.createMobileScrollManager(),
    go(href, state = { __NA: true, __PRIVATE_NEXTJS_INTERNALS_TREE: [href] }) {
      window.location = new URL(href, window.location.origin)
      entries.splice(historyIndex + 1)
      entries.push({ url: window.location, state })
      historyIndex++
    },
    traverse(delta, emit = true) {
      historyIndex += delta
      window.location = entries[historyIndex].url
      if (emit) window.emit('popstate')
    },
    grow(element, height) {
      element.scrollHeight = height
      ;[...observers].forEach((observer) => observer.callback())
      flush()
    },
    main(height = 2000) {
      let top = 0
      const element = events({
        clientHeight: 500, scrollHeight: height, firstElementChild: {}, writes: 0,
        contains: (target) => target.parent === element,
        focus: () => { element.focused = true },
      })
      Object.defineProperty(element, 'scrollTop', {
        get: () => top,
        set: (value) => { element.writes++; top = Math.max(0, Math.min(value, element.scrollHeight - element.clientHeight)) },
      })
      return element
    },
  }
}

test('new routes start at the top; Back and Forward restore their separate positions', () => {
  const env = environment()
  const manager = env.manager()
  manager.start()
  const overview = env.main()
  let detach = manager.attach(overview)
  env.flush()
  overview.scrollTop = 640
  overview.emit('scroll')
  env.go('/stock/AAPL')
  detach()
  const company = env.main()
  detach = manager.attach(company)
  env.flush()
  assert.equal(company.scrollTop, 0)
  company.scrollTop = 280
  company.emit('scroll')
  env.traverse(-1)
  detach()
  const restoredOverview = env.main()
  detach = manager.attach(restoredOverview)
  env.flush()
  assert.equal(restoredOverview.scrollTop, 640)
  env.traverse(1)
  detach()
  const restoredCompany = env.main()
  manager.attach(restoredCompany)
  env.flush()
  assert.equal(restoredCompany.scrollTop, 280)
})

test('filter and tab URL changes retain position, while same-page history traversal restores it', () => {
  const env = environment()
  env.go('/disclosures')
  const manager = env.manager()
  manager.start()
  const main = env.main()
  manager.attach(main)
  env.flush()
  main.scrollTop = 420
  main.emit('scroll')
  const originalEntry = env.window.history.state.__stockscopeMobileScrollEntry
  env.go('/disclosures?symbol=AAPL')
  manager.sync()
  env.flush()
  assert.equal(main.scrollTop, 420)
  assert.notEqual(env.window.history.state.__stockscopeMobileScrollEntry, originalEntry)
  main.scrollTop = 730
  main.emit('scroll')
  env.traverse(-1)
  manager.sync()
  env.flush()
  assert.equal(main.scrollTop, 420)
})

test('repeated visits to the same URL restore the position of each history entry', () => {
  const env = environment()
  const manager = env.manager()
  manager.start()
  let detach
  for (const [href, top] of [['/', 600], ['/stock/AAPL', 300], ['/', 120], ['/stock/MSFT', 250]]) {
    if (detach) {
      env.go(href)
      detach()
    }
    const main = env.main()
    detach = manager.attach(main)
    env.flush()
    main.scrollTop = top
    main.emit('scroll')
  }
  env.traverse(-3)
  detach()
  const originalOverview = env.main()
  detach = manager.attach(originalOverview)
  env.flush()
  assert.equal(originalOverview.scrollTop, 600)
  env.traverse(2)
  detach()
  const laterOverview = env.main()
  manager.attach(laterOverview)
  env.flush()
  assert.equal(laterOverview.scrollTop, 120)
})

test('a departing page commit cannot consume the destination history restoration', () => {
  const env = environment()
  const manager = env.manager()
  manager.start()
  const overview = env.main()
  let detach = manager.attach(overview)
  env.flush()
  overview.scrollTop = 600
  overview.emit('scroll')
  env.go('/compare')
  detach()
  detach = manager.attach(env.main())
  env.flush()
  env.traverse(-1)
  manager.sync()
  detach()
  const returned = env.main()
  manager.attach(returned)
  env.flush()
  assert.equal(returned.scrollTop, 600)
})

test('restoration also works when Next commits the destination before our popstate listener', () => {
  const env = environment()
  const manager = env.manager()
  manager.start()
  const overview = env.main()
  let detach = manager.attach(overview)
  env.flush()
  overview.scrollTop = 643
  overview.emit('scroll')
  env.go('/compare')
  detach()
  detach = manager.attach(env.main())
  env.flush()

  // Next registered first and can finish its commit before this listener runs.
  env.traverse(-1, false)
  detach()
  const returned = env.main()
  detach = manager.attach(returned)
  // StrictMode may repeat the destination's layout effects within that commit.
  detach()
  manager.attach(returned)
  env.window.emit('popstate')
  env.flush()
  assert.equal(returned.scrollTop, 643)
})

test('entry labels preserve Next state and survive a router state rewrite after popstate', () => {
  const env = environment()
  const manager = env.manager()
  manager.start()
  const replaceState = env.window.history.replaceState
  const routerTree = env.window.history.state.__PRIVATE_NEXTJS_INTERNALS_TREE
  env.window.history.state.custom = { retained: true }
  const overview = env.main()
  let detach = manager.attach(overview)
  env.flush()
  const originalEntry = env.window.history.state.__stockscopeMobileScrollEntry
  assert.equal(env.window.history.state.__NA, true)
  assert.equal(env.window.history.state.__PRIVATE_NEXTJS_INTERNALS_TREE, routerTree)
  assert.equal(env.window.history.state.custom.retained, true)
  assert.equal(env.window.history.replaceState, replaceState)
  overview.scrollTop = 500
  overview.emit('scroll')
  env.go('/stock/AAPL')
  detach()
  detach = manager.attach(env.main())
  env.flush()
  env.traverse(-1)
  const updatedTree = ['restored-by-next']
  env.window.history.replaceState({ __NA: true, __PRIVATE_NEXTJS_INTERNALS_TREE: updatedTree }, '')
  detach()
  const restored = env.main()
  manager.attach(restored)
  env.flush()
  assert.equal(restored.scrollTop, 500)
  assert.equal(env.window.history.state.__stockscopeMobileScrollEntry, originalEntry)
  assert.equal(env.window.history.state.__PRIVATE_NEXTJS_INTERNALS_TREE, updatedTree)
  assert.equal(env.window.history.state.__NA, true)
  assert.equal(env.window.history.replaceState, replaceState)
})

test('restoration waits for async content growth without overwriting the saved position with a clamp', () => {
  const env = environment()
  const manager = env.manager()
  manager.start()
  const first = env.main()
  let detach = manager.attach(first)
  env.flush()
  first.scrollTop = 1100
  first.emit('scroll')
  env.go('/compare')
  detach()
  detach = manager.attach(env.main())
  env.flush()
  env.traverse(-1)
  detach()
  const loading = env.main(600)
  manager.attach(loading)
  env.flush()
  assert.equal(loading.scrollTop, 100)
  loading.emit('scroll')
  env.grow(loading, 900)
  assert.equal(loading.scrollTop, 400)
  env.grow(loading, 2200)
  assert.equal(loading.scrollTop, 1100)
  assert.equal(env.observers.size, 0)
})

test('user interaction cancels pending restoration so late data cannot move their view', () => {
  const env = environment()
  const manager = env.manager()
  manager.start()
  const first = env.main()
  let detach = manager.attach(first)
  env.flush()
  first.scrollTop = 900
  first.emit('scroll')
  env.go('/compare')
  detach()
  detach = manager.attach(env.main())
  env.flush()
  env.traverse(-1)
  detach()
  const loading = env.main(500)
  manager.attach(loading)
  env.flush()
  loading.emit('touchstart')
  env.grow(loading, 2200)
  assert.equal(loading.scrollTop, 0)
  assert.equal(env.observers.size, 0)
})

test('initial anchors wait for content and skip-to-content focuses and resets the main scrollport', () => {
  const env = environment()
  env.go('/#watchlist')
  const manager = env.manager()
  manager.start()
  const main = env.main()
  env.targets.set('main-content', main)
  manager.attach(main)
  env.flush()
  env.targets.set('watchlist', { parent: main, scrollIntoView: () => { main.scrollTop = 650 } })
  env.grow(main, 2100)
  assert.equal(main.scrollTop, 650)
  env.go('/#main-content')
  env.window.emit('hashchange')
  env.flush()
  assert.equal(main.scrollTop, 0)
  assert.equal(main.focused, true)
})

test('native hash entries remain null and traverse normally without acquiring custom-only state', () => {
  const env = environment()
  const manager = env.manager()
  manager.start()
  const main = env.main()
  env.targets.set('main-content', main)
  manager.attach(main)
  env.flush()
  main.scrollTop = 600
  main.emit('scroll')

  // A native <a href="#main-content"> creates a same-document entry with null state.
  env.go('/#main-content', null)
  env.window.emit('hashchange')
  env.flush()
  assert.equal(env.window.history.state, null)
  assert.equal(main.scrollTop, 0)

  env.traverse(-1)
  env.window.emit('hashchange')
  env.flush()
  assert.equal(main.scrollTop, 600)

  env.traverse(1)
  env.window.emit('hashchange')
  env.flush()
  manager.sync()
  assert.equal(env.window.history.state, null)
  assert.equal(main.scrollTop, 0)
  assert.equal(main.focused, true)
})

test('desktop document scrolling is untouched and a fresh auth manager has no prior positions', () => {
  const desktop = environment({ mobile: false })
  const main = desktop.main()
  const manager = desktop.manager()
  manager.start()
  manager.attach(main)
  desktop.flush()
  assert.equal(main.writes, 0)
  assert.equal(desktop.observers.size, 0)

  const env = environment()
  const old = env.manager()
  const prior = env.main()
  old.attach(prior)
  env.flush()
  prior.scrollTop = 800
  prior.emit('scroll')
  const signedInAgain = env.manager()
  signedInAgain.start()
  env.window.emit('popstate')
  const fresh = env.main()
  signedInAgain.attach(fresh)
  env.flush()
  assert.equal(fresh.scrollTop, 0)
})
