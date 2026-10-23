const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')
function load(name) {
  const compiled = ts.transpileModule(
    fs.readFileSync(`${__dirname}/${name}.ts`, 'utf8'),
    {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2020,
      },
    },
  ).outputText
  const api = {}
  vm.runInNewContext(compiled, { exports: api })
  return api
}
const api = load('company-drafts')
const { createDraftStore } = load('workspace-drafts')
const sample = 'a'.repeat(24)
const hash = 'b'.repeat(64)
const key = `${sample}:${hash}`
const empty = { version: 1, report: null, annotations: {} }
function report() {
  return {
    symbol: 'AAPL',
    generated_at: '2026-10-22T16:00:00Z',
    elapsed_ms: 100,
    text_scope: 'Saved headline',
    language_policy: 'English',
    sample: {
      requested: 12,
      returned: 1,
      eligible: 1,
      empty_text: 0,
      unknown_language: 0,
      unsupported_language: 0,
      company_release_excluded: 0,
    },
    baseline: { model_id: 'vaderSentiment', revision: '3.3.2', license: 'MIT' },
    challengers: ['finsense', 'modernfinbert'].map((name) => ({
      key: name,
      model_id: name,
      revision: 'abc123',
      source_url: `https://huggingface.co/example/${name}`,
      license: 'Apache-2.0',
      provenance: 'Example',
      caveat: 'Research',
      status: 'compared',
      message: 'Complete',
      inference_latency_ms: 1,
    })),
    evaluation: {
      status: 'not_evaluated',
      annotation_count: 0,
      label_source: 'Caller',
      metric_policy: 'Three classes',
      models: Object.fromEntries(
        ['vader', 'finsense', 'modernfinbert'].map((name) => [
          name,
          { status: 'not_evaluated', evaluated_count: 0 },
        ]),
      ),
    },
    rows: [
      {
        sample_id: sample,
        text_sha256: hash,
        title: 'Saved company headline',
        text: 'Saved company headline\nDescription',
        url: 'https://example.com/story',
        source: { name: 'Publisher' },
        published_at: null,
        status: 'eligible',
        coverage: 'title+description',
        character_truncated: false,
        predictions: Object.fromEntries(
          ['vader', 'finsense', 'modernfinbert'].map((name) => [
            name,
            { status: 'scored', label: 'positive', score: 0.4 },
          ]),
        ),
      },
    ],
  }
}
function storage() {
  const values = new Map()
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  }
}

test('scenario inputs survive a new provider seed and reset only their workspace', () => {
  const browser = storage()
  const initial = {
    version: 1,
    cashFlow: '',
    shares: '100',
    currency: 'USD',
    scenarios: [
      { name: 'Bear', change: '-15', multiple: '12' },
      { name: 'Base', change: '0', multiple: '18' },
      { name: 'Bull', change: '15', multiple: '24' },
    ],
  }
  assert.equal(api.isScenarioDraft(initial), true)
  const draft = {
    ...initial,
    cashFlow: '250',
    shares: '120',
    scenarios: initial.scenarios.map((row) => ({ ...row, multiple: '22' })),
  }
  const first = createDraftStore(
    browser,
    'valuation:AAPL',
    initial,
    api.isScenarioDraft,
  )
  first.setValue(draft)
  browser.setItem('saved-news', 'leave intact')
  const restored = createDraftStore(
    browser,
    'valuation:AAPL',
    { ...initial, shares: '999' },
    api.isScenarioDraft,
  )
  assert.equal(restored.getSnapshot().value.cashFlow, '250')
  assert.equal(restored.getSnapshot().value.shares, '120')
  assert.equal(restored.getSnapshot().value.scenarios[1].multiple, '22')
  restored.reset()
  assert.equal(browser.getItem('saved-news'), 'leave intact')
  assert.equal(browser.getItem('valuation:AAPL'), null)
  for (const invalid of [
    { ...initial, cashFlow: {} },
    { ...initial, shares: '1; alert(1)' },
    { ...initial, scenarios: initial.scenarios.slice(1) },
    { ...initial, currency: '<USD>' },
  ])
    assert.equal(api.isScenarioDraft(invalid), false)
})

test('completed tone report and explicit hashed annotations survive local reload', () => {
  const browser = storage()
  const saved = {
    version: 1,
    report: report(),
    annotations: {
      [key]: { sample_id: sample, text_sha256: hash, label: 'negative' },
    },
  }
  assert.equal(api.isToneDraft(saved), true)
  createDraftStore(browser, 'tone:AAPL', empty, api.isToneDraft).setValue(saved)
  const restored = createDraftStore(
    browser,
    'tone:AAPL',
    empty,
    api.isToneDraft,
  ).getSnapshot().value
  assert.equal(restored.report.generated_at, saved.report.generated_at)
  assert.equal(restored.report.rows[0].predictions.finsense.score, 0.4)
  assert.equal(api.sameToneSample(restored.report, report()), true)
  assert.equal(
    api.matchingToneAnnotations(restored.annotations, report())[sample],
    'negative',
  )
})

test('changed text, sample identities or eligibility withhold reports and labels without deleting them', () => {
  const old = report()
  const annotations = {
    [key]: { sample_id: sample, text_sha256: hash, label: 'positive' },
  }
  for (const changes of [
    { text_sha256: 'c'.repeat(64) },
    { sample_id: 'd'.repeat(24) },
    { status: 'unknown_language' },
  ]) {
    const current = report()
    Object.assign(current.rows[0], changes)
    assert.equal(api.sameToneSample(old, current), false)
    assert.equal(
      Object.keys(api.matchingToneAnnotations(annotations, current)).length,
      0,
    )
    assert.equal(Object.keys(annotations).length, 1)
  }
  const changed = report()
  changed.rows[0].text = 'Different text with a forged old hash'
  assert.equal(api.sameToneSample(old, changed), false)
  const otherCompany = report()
  otherCompany.symbol = 'MSFT'
  assert.equal(api.sameToneSample(old, otherCompany), false)
})

test('malformed local reports, unsafe model links, prediction numbers and annotation identities are rejected', () => {
  const badValues = []
  const unsafeLink = report()
  unsafeLink.challengers[0].source_url = 'javascript:alert(1)'
  badValues.push(unsafeLink)
  const badPredictions = report()
  badPredictions.rows[0].predictions.finsense.score = Infinity
  badValues.push(badPredictions)
  const incomplete = report()
  delete incomplete.evaluation.models.vader
  badValues.push(incomplete)
  const duplicate = report()
  duplicate.rows.push({ ...duplicate.rows[0] })
  duplicate.sample.returned = 2
  badValues.push(duplicate)
  const notAnArray = report()
  notAnArray.rows = {}
  badValues.push(notAnArray)
  const wrongDate = report()
  wrongDate.generated_at = 'not a date'
  badValues.push(wrongDate)
  for (const value of badValues)
    assert.equal(api.isToneDraft({ ...empty, report: value }), false)
  assert.equal(
    api.isToneDraft({
      ...empty,
      annotations: {
        [key]: {
          sample_id: sample,
          text_sha256: 'c'.repeat(64),
          label: 'negative',
        },
      },
    }),
    false,
  )
  assert.equal(
    api.isToneDraft({
      ...empty,
      annotations: {
        [key]: { sample_id: sample, text_sha256: hash, label: 'buy' },
      },
    }),
    false,
  )
  assert.equal(
    api.isToneDraft({ version: 2, report: null, annotations: {} }),
    false,
  )
})
