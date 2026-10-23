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
  assert.equal(api.isBacktestDraft({ ...draft, symbols: '', start: '', fast: 0 }), true)
  assert.equal(api.isBacktestDraft({ ...draft, strategy: 'unknown' }), false)
  assert.equal(api.isBacktestDraft({ ...draft, costs: { ...draft.costs, commission: NaN } }), false)
  assert.equal(api.isBacktestDraft({ ...draft, start: null }), false)
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
