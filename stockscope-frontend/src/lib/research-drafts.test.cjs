const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')
const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/research-drafts.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
const api = {}
vm.runInNewContext(compiled, { exports: api, URLSearchParams, Date, Set, Number })
const storageApi = {}
vm.runInNewContext(ts.transpileModule(fs.readFileSync(`${__dirname}/workspace-drafts.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText, { exports: storageApi, Date, Set, Number })
const clone = (value) => JSON.parse(JSON.stringify(value))
const row = (ticker = 'AAPL') => ({ ticker, insufficient_data: false, revenue_ttm: 0, fcf_ttm: -12, growth_metadata: { revenue_growth_yoy: { basis: 'fiscal_year', status: 'available', current_period_end: '2025-12-31', prior_period_end: '2024-12-31' } }, period_metadata: { revenue_ttm: { basis: 'ttm', period_end: '2025-12-31', quarter_ends: ['2025-03-31', '2025-06-30', '2025-09-30', '2025-12-31'] } } })
const snapshot = () => ({ criteria: clone(api.defaultScreenCriteria), universeName: 'Custom stock list', capturedAt: '2026-10-22T16:00:00Z', data: { results: [row()], total_attempted: 1, total_evaluated: 1, total_matches: 1, total_failed: 0, total_insufficient: 0, universe_name: 'Custom' } })

test('explicit screening links override saved criteria and root links resume the draft', () => {
  assert.equal(api.screenCriteriaFromUrl(new URLSearchParams()), null)
  const linked = api.screenCriteriaFromUrl(new URLSearchParams('universe=custom&symbols=AAPL,MSFT&min_revenue_growth_yoy=12'))
  assert.equal(linked.universe, 'custom')
  assert.equal(linked.filters.min_revenue_growth_yoy, '12')
  assert.equal(linked.filters.min_fcf_growth_yoy, '')
  assert.equal(linked.limit, '50')
  assert.equal(api.screenCriteriaKey(api.screenCriteriaFromUrl(api.screenCriteriaParams(linked))), api.screenCriteriaKey(linked))
  assert.equal(api.screenCriteriaFromUrl(new URLSearchParams('limit=&sort=invalid')).limit, '')
  assert.equal(api.screenCriteriaFromUrl(new URLSearchParams('limit=999&sort=invalid')).limit, '999')
})

test('inactive custom tickers survive URL hydration under curated and watchlist universes', () => {
  for (const universe of ['curated', 'watchlist']) {
    const criteria = { ...clone(api.defaultScreenCriteria), universe, custom: 'AAPL, MSFT, BRK.B' }
    const restored = api.screenCriteriaFromUrl(api.screenCriteriaParams(criteria))
    assert.equal(restored.universe, universe)
    assert.equal(restored.custom, 'AAPL, MSFT, BRK.B')
    // Inactive symbols remain a draft field, without changing the active screen key.
    assert.equal(api.screenCriteriaKey(criteria), api.screenCriteriaKey({ ...criteria, custom: '' }))
  }
})

test('an immediate reload keeps the latest numeric input and Clear cannot replay the old URL', () => {
  const stored = new Map()
  const storage = { getItem: (key) => stored.get(key) ?? null, setItem: (key, value) => stored.set(key, value), removeItem: (key) => stored.delete(key) }
  const key = 'screen-regression'
  let href = '/screener'
  const history = { replaceState: (_data, _title, url) => { href = url } }
  const writeUrl = (params) => api.replaceResearchUrl(history, '/screener', params)
  const store = storageApi.createDraftStore(storage, key, clone(api.initialScreenerDraft), api.isScreenerDraft)
  store.setValue((current) => api.editScreenDraft(current, { universe: 'custom', custom: 'AAPL,MSFT' }, writeUrl))
  store.setValue((current) => api.editScreenDraft(current, { filters: { ...current.criteria.filters, min_revenue_growth_yoy: '5' } }, writeUrl))

  // Reload immediately, without blur, timers, or an asynchronous router flush.
  const reloaded = storageApi.createDraftStore(storage, key, clone(api.initialScreenerDraft), api.isScreenerDraft)
  const intent = api.screenCriteriaFromUrl(new URL(href, 'https://stockscope.local').searchParams)
  reloaded.setValue((current) => ({ ...current, criteria: intent }))
  assert.equal(reloaded.getSnapshot().value.criteria.filters.min_revenue_growth_yoy, '5')
  assert.equal(reloaded.getSnapshot().value.criteria.custom, 'AAPL,MSFT')

  reloaded.reset()
  api.replaceResearchUrl(history, '/screener', new URLSearchParams())
  const cleared = storageApi.createDraftStore(storage, key, clone(api.initialScreenerDraft), api.isScreenerDraft)
  assert.equal(api.screenCriteriaFromUrl(new URL(href, 'https://stockscope.local').searchParams), null)
  assert.equal(cleared.getSnapshot().value.criteria.filters.min_revenue_growth_yoy, '')
  assert.equal(cleared.getSnapshot().value.criteria.custom, '')
  assert.equal(stored.has(key), false)
})

test('draft validators retain partial inputs, observed zero and losses, and reject corrupt or oversized persisted records', () => {
  const draft = { ...clone(api.initialScreenerDraft), snapshot: snapshot(), selected: ['AAPL'] }
  draft.criteria.limit = '' // Incomplete input is a valid draft before submission.
  assert.equal(api.isScreenerDraft(draft), true)
  assert.equal(api.isScreenerDraft({ ...draft, selected: ['MSFT'] }), false)
  assert.equal(api.isScreenerDraft({ ...draft, accessToken: 'must never persist' }), false)
  const bad = clone(draft)
  bad.snapshot.data.results[0].revenue_ttm = Infinity
  assert.equal(api.isScreenerDraft(bad), false)
  bad.snapshot.data.results = Array.from({ length: 501 }, () => row())
  assert.equal(api.isScreenerDraft(bad), false)
})

test('financial snapshot projection retains displayed provenance and excludes arbitrary provider payloads', () => {
  const source = { ...row(), auth_token: 'not part of research', long_description: 'unbounded provider text', total_debt: 500 }
  const projected = api.draftFinancialRows([source])[0]
  assert.equal(projected.revenue_ttm, 0)
  assert.equal(projected.fcf_ttm, -12)
  assert.equal(projected.growth_metadata.revenue_growth_yoy.prior_period_end, '2024-12-31')
  assert.equal(projected.period_metadata.revenue_ttm.period_end, '2025-12-31')
  assert.equal('auth_token' in projected, false)
  assert.equal('long_description' in projected, false)
  assert.equal('total_debt' in projected, false)
})

test('screen completion preserves newer input edits and cannot overwrite a newer run or cleared workspace', () => {
  const draft = clone(api.initialScreenerDraft)
  draft.requestId = 'aaaa'
  draft.criteria.custom = 'MSFT'
  const completed = api.completeScreen(draft, 'aaaa', snapshot())
  assert.equal(completed.criteria.custom, 'MSFT')
  assert.equal(completed.snapshot.criteria.custom, '')
  assert.equal(completed.requestId, null)
  assert.equal(api.completeScreen({ ...draft, requestId: 'bbbb' }, 'aaaa', snapshot()).snapshot, null)
  assert.equal(api.completeScreen(api.initialScreenerDraft, 'aaaa', snapshot()), api.initialScreenerDraft)
})

test('screen snapshots retain reporting currencies across storage and accept legacy unknowns', () => {
  const draft = { ...clone(api.initialScreenerDraft), snapshot: snapshot(), selected: ['AAPL'] }
  draft.snapshot.data.results = api.draftFinancialRows([{ ...row(), reporting_currency: 'JPY' }])
  assert.equal(draft.snapshot.data.results[0].reporting_currency, 'JPY')
  assert.equal(api.isScreenerDraft(JSON.parse(JSON.stringify(draft))), true)
  delete draft.snapshot.data.results[0].reporting_currency
  assert.equal(api.isScreenerDraft(draft), true)
  draft.snapshot.data.results[0].reporting_currency = 123
  assert.equal(api.isScreenerDraft(draft), false)
})
