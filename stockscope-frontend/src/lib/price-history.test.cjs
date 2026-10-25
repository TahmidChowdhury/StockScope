const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')

const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/price-history.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
const exportsObject = {}
vm.runInNewContext(compiled, { exports: exportsObject })
const { priceHistorySummary } = exportsObject

test('empty history reports missing observations, never infinity or zero prices', () => {
  const result = priceHistorySummary([])
  assert.equal(result.high, null)
  assert.equal(result.low, null)
  assert.equal(result.averageVolume, null)
})

test('summary keeps observed zero volume and excludes unavailable or invalid observations', () => {
  const result = priceHistorySummary([
    { high: 110, low: 100, volume: 0 },
    { high: 120, low: 90, volume: 100 },
    { high: null, low: undefined, volume: null },
    { high: Infinity, low: NaN, volume: -1 },
    { high: '130', low: '80', volume: Infinity },
  ])
  assert.equal(result.high, 120)
  assert.equal(result.low, 90)
  assert.equal(result.averageVolume, 50)
})
