const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')

const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/trading.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
function harness(response) {
  const exports = {}
  const calls = []
  vm.runInNewContext(compiled, {
    exports, Intl, Date,
    require: () => ({ apiFetch: async (...args) => { calls.push(args); return response } }),
  })
  return { api: exports, calls }
}

test('timestamps use New York dates across midnight UTC and daylight-saving seasons', () => {
  const { api } = harness()
  assert.equal(api.tradingDate('2026-10-16T00:10:00+00:00'), '2026-10-15')
  assert.equal(api.tradingDate('2026-01-16T04:10:00+00:00'), '2026-01-15')
})

test('saved experiments display their names and older unnamed experiments retain strategy labels', () => {
  const { api } = harness()
  assert.equal(api.backtestName({ name: '  Walkthrough · AAPL + MSFT  ', strategy: 'buy_hold' }), 'Walkthrough · AAPL + MSFT')
  assert.equal(api.backtestName({ strategy: 'buy_hold' }), 'Buy and hold experiment')
  assert.equal(api.backtestName({ name: null, strategy: 'sma' }), 'Moving average experiment')
  assert.equal(api.backtestName({ name: ' ', strategy: 'congress', member: 'Example Member' }), 'Congress · Example Member')
})

test('backtest links carry normalized distinct symbols and reject invalid or oversized universes', () => {
  const { api } = harness()
  assert.equal(api.backtestSymbols(' aapl, msft, AAPL,brk-b ').join(','), 'AAPL,MSFT,BRK-B')
  for (const value of [null, '', ', ,', 'AAPL,../../bad', 'AAPL,$MSFT', Array.from({ length: 21 }, (_, i) => `A${i}`).join(',')]) {
    assert.equal(api.backtestSymbols(value), null)
  }
})

test('a failed financial-input request exposes structured validation details', async () => {
  const { api } = harness(new Response(JSON.stringify({ detail: [{ loc: ['body', 'end'], msg: 'End must precede today' }] }), { status: 422 }))
  await assert.rejects(api.tradingRequest('/backtests', {}), /end: End must precede today/)
})

test('proxy failures retain their status without treating HTML as a successful experiment', async () => {
  const { api } = harness(new Response('<html>Unavailable</html>', { status: 503 }))
  await assert.rejects(api.tradingRequest('/backtests', {}), /Request failed \(503\)/)
})

test('cancellation submits an action and preserves the order journal', async () => {
  const { api, calls } = harness(new Response('{"orders":[]}', { status: 200 }))
  await api.tradingRequest('/portfolios/portfolio-test/orders/order-test/cancel', {})
  assert.equal(calls[0][0], '/api/trading/portfolios/portfolio-test/orders/order-test/cancel')
  assert.equal(calls[0][1].method, 'POST')
  assert.equal(calls[0][1].body, '{}')
})

test('paper cancellation eligibility uses the submission date in New York', () => {
  const { api } = harness()
  const order = { signal_date: '2026-10-15' }
  assert.equal(api.canCancelPaperOrder(order, new Date('2026-10-16T00:10:00Z')), true)
  assert.equal(api.canCancelPaperOrder(order, new Date('2026-10-16T04:10:00Z')), false)
  assert.equal(api.canCancelPaperOrder({ ...order, cancelled_at: '2026-10-15T21:00:00Z' }, new Date('2026-10-15T22:00:00Z')), false)
})

test('backtest submission reads the entered date window without falling back to rolling defaults', () => {
  const { api } = harness()
  const form = new FormData()
  form.set('start', '2025-01-01')
  form.set('end', '2025-12-31')
  assert.equal(api.backtestDates(form).start, '2025-01-01')
  assert.equal(api.backtestDates(form).end, '2025-12-31')
  form.set('start', '2024-01-01')
  form.set('end', '2024-12-31')
  assert.equal(api.backtestDates(form).start, '2024-01-01')
  assert.equal(api.backtestDates(form).end, '2024-12-31')
  for (const [start, end] of [['', '2025-12-31'], ['2025-01-01', ''], ['2025-02-30', '2025-12-31'], ['2025-12-31', '2025-01-01']]) {
    form.set('start', start); form.set('end', end)
    assert.throws(() => api.backtestDates(form), /Enter valid start and end dates/)
  }
})
