const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')
const api = {}
vm.runInNewContext(ts.transpileModule(fs.readFileSync(`${__dirname}/trading-draft.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText, { exports: api })

test('trading drafts retain incomplete edits while rejecting corrupt structures and nonfinite costs', () => {
  const funding = { capital: 10000, benchmark: 'SPY', costs: { slippage_bps: 5, spread_bps: 2, commission: 0 } }
  const draft = { ...funding, strategy: 'buy_hold', backtestLabel: 'Baseline', symbols: 'AAPL, MSFT', start: '2025-01-01', end: '2025-12-31', fast: 20, slow: 50, member: '', tradeFraction: 10, maxWeight: 25, delay: 0 }
  assert.equal(api.isBacktestDraft(draft), true)
  for (const allowEstimatedDates of [true, false]) assert.equal(api.isBacktestDraft(JSON.parse(JSON.stringify({ ...draft, allowEstimatedDates }))), true)
  for (const allowEstimatedDates of ['true', 1, null]) assert.equal(api.isBacktestDraft({ ...draft, allowEstimatedDates }), false)
  assert.equal(api.isBacktestDraft({ ...draft, symbols: '', start: '', fast: 0 }), true)
  assert.equal(api.isBacktestDraft({ ...draft, strategy: 'unknown' }), false)
  assert.equal(api.isBacktestDraft({ ...draft, costs: { ...draft.costs, commission: NaN } }), false)
  assert.equal(api.isBacktestDraft({ ...draft, start: null }), false)
  assert.equal(api.isBacktestDraft({ ...draft, memberHandoffs: ['handoff-1', 'handoff-2'] }), true)
  for (const memberHandoffs of [['duplicate', 'duplicate'], ['bad id'], Array.from({ length: 101 }, (_, i) => `handoff-${i}`), 'handoff-1']) {
    assert.equal(api.isBacktestDraft({ ...draft, memberHandoffs }), false)
  }
  assert.equal(api.isPaperSetupDraft({ ...funding, name: 'Paper' }), true)
  assert.equal(api.isPaperSetupDraft({ ...funding, name: 'x'.repeat(81) }), false)
})

test('order drafts retain their idempotency key and reject unsupported actions or oversized evidence', () => {
  const draft = { orderSymbol: 'AAPL', orderSide: 'buy', budget: 1000, thesis: 'Before earnings', clientOrderId: 'order-11111111' }
  assert.equal(api.isPaperOrderDraft(draft), true)
  assert.equal(api.isPaperOrderDraft({ ...draft, clientOrderId: '' }), false)
  assert.equal(api.isPaperOrderDraft({ ...draft, orderSide: 'short' }), false)
  assert.equal(api.isPaperOrderDraft({ ...draft, thesis: 'x'.repeat(2001) }), false)
  assert.equal(api.isCongressDraft({ csv: 'disclosure_id,member\n' }), true)
  assert.equal(api.isCongressDraft({ csv: 'x'.repeat(2000001) }), false)
})

test('refreshing a research handoff preserves later edits while a fresh Compare action overrides symbols', () => {
  const original = { strategy: 'sma', symbols: 'NVDA', backtestLabel: 'Keep this name', start: '2024-01-01', end: '2024-12-31' }
  const applied = api.applyBacktestSymbols(original, ['AAPL', 'MSFT'], 'handoff-1')
  assert.equal(applied.symbols, 'AAPL, MSFT')
  assert.equal(applied.strategy, 'buy_hold')
  const edited = { ...applied, symbols: 'NVDA', end: '2025-12-31' }
  assert.equal(api.applyBacktestSymbols(edited, ['AAPL', 'MSFT'], 'handoff-1'), edited)
  const fresh = api.applyBacktestSymbols(edited, ['AAPL', 'MSFT'], 'handoff-2')
  assert.equal(fresh.symbols, 'AAPL, MSFT')
  assert.equal(fresh.backtestLabel, 'Keep this name')
  assert.equal(fresh.end, '2025-12-31')
  const plain = api.applyBacktestSymbols(original, ['AAPL'], null)
  const plainEdited = { ...plain, symbols: 'NVDA' }
  assert.equal(api.applyBacktestSymbols(plainEdited, ['AAPL'], null), plainEdited)
})

test('a company comparison replaces a Congress strategy without discarding experiment settings', () => {
  const original = {
    strategy: 'congress', symbols: 'AAPL', member: 'Michael Rulli',
    backtestLabel: 'Research baseline', start: '2025-01-01', end: '2026-10-21',
    capital: 20000, benchmark: 'SPY', costs: { slippage_bps: 5, spread_bps: 2, commission: 1 },
  }
  const applied = api.applyBacktestSymbols(original, ['GOOG', 'MSFT'], 'company-handoff')
  assert.equal(applied.strategy, 'buy_hold')
  assert.equal(applied.symbols, 'GOOG, MSFT')
  for (const key of ['member', 'backtestLabel', 'start', 'end', 'capital', 'benchmark', 'costs']) {
    assert.equal(applied[key], original[key])
  }
  const edited = { ...applied, strategy: 'congress', symbols: 'NVDA', end: '2026-09-30' }
  assert.equal(api.applyBacktestSymbols(edited, ['GOOG', 'MSFT'], 'company-handoff'), edited)
  assert.equal(api.applyBacktestSymbols(original, ['GOOG'], 'one-company').strategy, 'buy_hold')
  assert.equal(api.applyBacktestSymbols({ ...original, strategy: 'sma' }, ['GOOG'], 'one-sma').strategy, 'sma')
  assert.equal(api.applyBacktestSymbols({ ...original, strategy: 'sma' }, ['GOOG', 'MSFT'], 'multiple-sma').strategy, 'buy_hold')
})

test('stock requests exclude incomplete hidden Congress inputs while preserving the draft', () => {
  const draft = {
    strategy: 'congress', symbols: 'AAPL', member: '', tradeFraction: 0, maxWeight: 0, delay: 1000,
    allowEstimatedDates: true, backtestLabel: '  Research baseline  ', start: '2024-01-01', end: '2024-12-31',
    capital: 20000, benchmark: 'SPY', costs: { slippage_bps: 5, spread_bps: 2, commission: 1 }, fast: 0, slow: 0,
  }
  const applied = api.applyBacktestSymbols(draft, ['GOOG', 'MSFT'], 'company-request')
  const before = JSON.stringify(applied)
  const request = api.buildBacktestRequest(applied, { start: '2025-01-01', end: '2026-10-21' })
  const payload = JSON.parse(JSON.stringify(request))
  assert.deepEqual(payload, {
    name: 'Research baseline', strategy: 'buy_hold', start: '2025-01-01', end: '2026-10-21',
    initial_cash: 20000, benchmark: 'SPY', costs: draft.costs, symbols: ['GOOG', 'MSFT'],
  })
  assert.equal(JSON.stringify(applied), before)
  const sma = api.buildBacktestRequest({ ...applied, strategy: 'sma', symbols: 'GOOG', fast: 20, slow: 50 }, { start: '2025-01-01', end: '2026-10-21' })
  assert.equal(sma.fast_window, 20)
  assert.equal(sma.slow_window, 50)
  for (const key of ['member', 'trade_fraction', 'max_weight', 'disclosure_delay_days', 'allow_estimated_disclosure_dates']) {
    assert.equal(Object.hasOwn(sma, key), false)
  }
})

test('Congress requests retain active disclosure controls and exclude stock-only controls', () => {
  const draft = {
    strategy: 'congress', symbols: 'invalid hidden ticker', member: 'Michael Rulli', tradeFraction: 10, maxWeight: 25,
    delay: 3, allowEstimatedDates: true, backtestLabel: '', capital: 10000, benchmark: 'SPY',
    costs: { slippage_bps: 5, spread_bps: 2, commission: 0 }, fast: 0, slow: 0,
  }
  const request = JSON.parse(JSON.stringify(api.buildBacktestRequest(draft, { start: '2025-01-01', end: '2026-10-21' })))
  assert.equal(request.member, draft.member)
  assert.equal(request.trade_fraction, 0.1)
  assert.equal(request.max_weight, 0.25)
  assert.equal(request.disclosure_delay_days, 3)
  assert.equal(request.allow_estimated_disclosure_dates, true)
  assert.deepEqual(request.symbols, [])
  assert.equal(Object.hasOwn(request, 'fast_window'), false)
  assert.equal(Object.hasOwn(request, 'slow_window'), false)
})

test('member backtest handoffs wait for known imported members and reject invalid or missing selections', () => {
  const member = "Zoë O'Neil"
  assert.equal(api.resolveMemberBacktestHandoff('/trading', 'backtest', member, 'handoff-1', [], false).status, 'pending')
  const ready = api.resolveMemberBacktestHandoff('/trading', 'backtest', member, 'handoff-1', [member], true)
  assert.equal(ready.status, 'ready')
  assert.equal(ready.member, member)
  assert.equal(ready.handoff, 'handoff-1')
  const unavailable = api.resolveMemberBacktestHandoff('/trading', 'backtest', 'Unknown Member', 'handoff-1', [member], true)
  assert.equal(unavailable.status, 'invalid')
  assert.match(unavailable.message, /No disclosures.*Unknown Member/)
  for (const [name, handoff] of [['', 'id'], [' A member', 'id'], ['A member\n', 'id'], ['x'.repeat(151), 'id'], ['A member', null], ['A member', ''], ['A member', 'bad id']]) {
    assert.equal(api.resolveMemberBacktestHandoff('/trading', 'backtest', name, handoff, [member], true).status, 'invalid')
  }
})

test('member handoffs select Congress once, persist later edits and do not replay on Back/Forward', () => {
  const original = { strategy: 'buy_hold', symbols: 'AAPL', member: '', backtestLabel: 'Keep this name', start: '2025-01-01', end: '2025-12-31' }
  const applied = api.applyBacktestMember(original, 'First Member', 'handoff-1')
  assert.equal(applied.strategy, 'congress')
  assert.equal(applied.member, 'First Member')
  assert.equal(applied.symbols, 'AAPL')
  const restored = JSON.parse(JSON.stringify({ ...applied, strategy: 'sma', member: 'Edited member', end: '2025-06-30' }))
  assert.equal(api.applyBacktestMember(restored, 'First Member', 'handoff-1'), restored)
  const fresh = api.applyBacktestMember(restored, 'Second Member', 'handoff-2')
  assert.equal(fresh.strategy, 'congress')
  assert.equal(fresh.member, 'Second Member')
  assert.equal(fresh.backtestLabel, 'Keep this name')
  assert.equal(fresh.end, '2025-06-30')
  const editedAgain = { ...fresh, member: 'Manual choice' }
  assert.equal(api.applyBacktestMember(editedAgain, 'First Member', 'handoff-1'), editedAgain)
})

test('saved records and unrelated tabs cannot apply stray symbols or member handoff parameters', () => {
  for (const [path, tab] of [
    ['/trading/backtests/run-11111111-1111-4111-8111-111111111111', 'backtest'],
    ['/trading/portfolios/portfolio-11111111-1111-4111-8111-111111111111', 'backtest'],
    ['/trading/backtests/invalid', 'backtest'], ['/trading', 'paper'], ['/trading', 'congress'],
  ]) {
    assert.equal(api.isBacktestWorkspace(path, tab), false)
    assert.equal(api.resolveMemberBacktestHandoff(path, tab, 'Known Member', 'handoff-1', ['Known Member'], true).status, 'none')
  }
  assert.equal(api.isBacktestWorkspace('/trading', 'backtest'), true)
  assert.equal(api.resolveMemberBacktestHandoff('/trading', 'backtest', null, null, [], true).status, 'none')
})
