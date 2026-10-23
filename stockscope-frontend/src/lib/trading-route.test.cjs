const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')
const exportsObject = {}
vm.runInNewContext(ts.transpileModule(fs.readFileSync(`${__dirname}/trading-route.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText, { exports: exportsObject, Error })
const { tradingRoute, savedTradingHref, loadSavedTradingRoute } = exportsObject
const first = 'run-11111111-1111-4111-8111-111111111111'
const second = 'run-22222222-2222-4222-8222-222222222222'
const portfolio = 'portfolio-33333333-3333-4333-8333-333333333333'
const flush = () => new Promise((resolve) => setImmediate(resolve))

test('saved experiments and portfolios have canonical paths that override stale tab parameters', () => {
  const run = tradingRoute(savedTradingHref('backtest', first), 'paper')
  assert.equal(run.tab, 'backtest')
  assert.equal(run.saved.id, first)
  assert.equal(run.saved.apiPath, `/backtests/${first}`)
  const paper = tradingRoute(savedTradingHref('portfolio', portfolio), 'backtest')
  assert.equal(paper.tab, 'paper')
  assert.equal(paper.saved.apiPath, `/portfolios/${portfolio}`)
  assert.equal(tradingRoute('/trading', 'congress').tab, 'congress')
  assert.equal(tradingRoute('/trading', 'backtest').saved, null)
})

test('malformed or wrong-kind IDs never produce fetchable saved routes', () => {
  for (const path of ['/trading/backtests/not-a-run', `/trading/backtests/${portfolio}`, '/trading/portfolios/%2e%2e%2fsecret', '/trading/backtests/%zz']) {
    const route = tradingRoute(path, 'backtest')
    assert.equal(route.saved, null)
    assert.match(route.error, /invalid \(404\)/)
  }
})

test('Back/Forward selection ignores a slower earlier saved-record response and late errors', async () => {
  let finishFirst
  const seen = []
  const cancelFirst = loadSavedTradingRoute(tradingRoute(savedTradingHref('backtest', first), null).saved,
    () => new Promise((resolve) => { finishFirst = resolve }), (record) => seen.push(record.id), (error) => seen.push(error.message))
  cancelFirst()
  loadSavedTradingRoute(tradingRoute(savedTradingHref('backtest', second), null).saved,
    async () => ({ id: second }), (record) => seen.push(record.id), (error) => seen.push(error.message))
  await flush()
  finishFirst({ id: first })
  await flush()
  assert.deepEqual(seen, [second])
  let fail
  const cancel = loadSavedTradingRoute(tradingRoute(savedTradingHref('backtest', first), null).saved,
    () => new Promise((_, reject) => { fail = reject }), () => assert.fail('Cancelled result'), () => assert.fail('Cancelled error'))
  cancel()
  fail(new Error('Late missing record'))
  await flush()
})

test('unavailable records and mismatched payloads report a failure without showing prior results', async () => {
  const errors = []
  const route = tradingRoute(savedTradingHref('backtest', first), null).saved
  loadSavedTradingRoute(route, async () => { throw new Error('Trading record not found') }, () => assert.fail('Missing record'), (error) => errors.push(error.message))
  loadSavedTradingRoute(route, async () => ({ id: second }), () => assert.fail('Wrong record'), (error) => errors.push(error.message))
  await flush()
  assert.equal(errors.length, 2)
  assert.match(errors[0], /not found/)
  assert.match(errors[1], /did not match/)
})
