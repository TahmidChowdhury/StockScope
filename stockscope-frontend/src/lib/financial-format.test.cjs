const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')
const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/financial-format.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
const api = {}
vm.runInNewContext(compiled, { exports: api, Intl, Set, Number })

test('financial displays distinguish unavailable values from observed zero and losses', () => {
  for (const format of [api.amount, api.percent, api.ratio]) {
    for (const missing of [undefined, null, NaN, Infinity, -Infinity, '0', false]) assert.equal(format(missing), '—')
    assert.notEqual(format(0), '—')
    assert.match(format(-2), /-/)
  }
  assert.equal(api.percent(0), '0%')
  assert.equal(api.percent(-0.125), '-12.5%')
  assert.equal(api.amount(1000000000), '1B')
  assert.equal(api.ratio(0), '0.00')
})
test('company selections normalize class shares and deduplicate aliases', () => {
  assert.equal(Array.from(api.parseSymbols('aapl, BRK.B brk-b MSFT, aapl')).join(','), 'AAPL,BRK-B,MSFT')
  assert.equal(Array.from(api.parseSymbols('AAPL, ../../file, https://example.com, ,MSFT')).join(','), 'AAPL,MSFT')
})
