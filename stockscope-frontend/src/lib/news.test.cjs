const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')
const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/news.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
const api = {}
vm.runInNewContext(compiled, { exports: api })

test('unknown and invalid provider sentiment does not become a neutral score', () => {
  for (const value of [undefined, null, {}, { label: 'positive' }, { compound: null }, { compound: '0.5' }, { compound: false }, { compound: NaN }, { compound: Infinity }, { compound: 1.1 }, { compound: -1.1 }]) {
    assert.equal(api.normalizeNewsSentiment(value), undefined)
  }
})

test('a measured zero remains a valid neutral observation', () => {
  const result = api.normalizeNewsSentiment({ compound: 0 })
  assert.equal(result.score, 0)
  assert.equal(result.label, 'Neutral')
})

test('labels match the same inclusive tone thresholds as the research API', () => {
  assert.equal(api.normalizeNewsSentiment({ compound: 0.05, label: 'incorrect provider label' }).label, 'Positive')
  assert.equal(api.normalizeNewsSentiment({ compound: -0.05 }).label, 'Negative')
  assert.equal(api.normalizeNewsSentiment({ compound: 0.049 }).label, 'Neutral')
})

test('company releases never inherit legacy or provider sentiment', () => {
  for (const compound of [-1, 0, 1]) {
    assert.equal(api.normalizeNewsSentiment({ compound }, 'company_release'), undefined)
  }
  assert.equal(api.normalizeNewsSentiment({ compound: 0 }, 'news').score, 0)
})

test('GDELT discovery does not become publication time', () => {
  const labels = api.newsDateLabels(null, '2026-04-11T12:00:00Z', Date.parse('2026-04-11T13:00:00Z'))
  assert.equal(labels.publication, 'Publication date unknown')
  assert.equal(labels.discovery, 'Discovered 1h ago')
})

test('publisher date and later discovery remain independently labeled', () => {
  const labels = api.newsDateLabels('2026-04-11T11:00:00Z', '2026-04-11T12:00:00Z', Date.parse('2026-04-11T13:00:00Z'))
  assert.equal(labels.publication, 'Published 2h ago')
  assert.equal(labels.discovery, 'Discovered 1h ago')
  const unknown = api.newsDateLabels('invalid', 'invalid')
  assert.equal(unknown.publication, 'Publication date unknown')
  assert.equal(unknown.discovery, null)
})
