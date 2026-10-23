const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')
const compiled = ts.transpileModule(
  fs.readFileSync(`${__dirname}/valuation.ts`, 'utf8'),
  {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  },
).outputText
const api = {}
vm.runInNewContext(compiled, { exports: api, Number, Date })

test('equity multiple scenarios cancel millions correctly and show signed differences', () => {
  const base = api.equityCashFlowScenario('100', '20', '0', '15', 100)
  assert.equal(base.price, 75)
  assert.equal(base.difference, -0.25)
  assert.equal(
    api.equityCashFlowScenario('100', '20', '20', '20', 100).price,
    120,
  )
  assert.equal(
    api.equityCashFlowScenario('100', '20', '-50', '10', null).difference,
    null,
  )
})

test('scenarios never silently substitute missing, nonfinite or nonpositive assumptions', () => {
  for (const input of [
    ['', '20', '0', '15'],
    [' ', '20', '0', '15'],
    ['NaN', '20', '0', '15'],
    ['100', '0', '0', '15'],
    ['-100', '20', '0', '15'],
    ['100', '20', '-100', '15'],
    ['100', '20', '0', '0'],
    ['Infinity', '20', '0', '15'],
    ['1e308', '1e-100', '0', '1e308'],
  ]) {
    assert.equal(api.equityCashFlowScenario(...input, 100), null)
  }
  assert.equal(
    api.equityCashFlowScenario('100', '20', '0', '15', 0).difference,
    null,
  )
})
