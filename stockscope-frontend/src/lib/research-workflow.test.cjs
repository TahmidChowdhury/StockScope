const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')
const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/research-workflow.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
const api = {}
vm.runInNewContext(compiled, { exports: api, URL, URLSearchParams, Intl, Date })

test('company return links accept only the two local research workspaces', () => {
  assert.equal(api.researchReturn('/screener?universe=custom&symbols=AAPL%2CMSFT').label, 'Back to screener')
  assert.equal(api.researchReturn('/compare?tickers=AAPL%2CMSFT').href, '/compare?tickers=AAPL%2CMSFT')
  for (const destination of [null, '', 'https://example.com/compare', '//example.com/compare', '/\\example.com/compare', '/trading', '/compare/extra', '/%63ompare', '/compare\n']) {
    assert.equal(api.researchReturn(destination), null)
  }
})

test('company links preserve the entire return selection without turning it into company query parameters', () => {
  const path = api.companyResearchHref('BRK-B', '/compare?tickers=BRK-B,AAPL&sort=revenue')
  const url = new URL(path, 'https://stockscope.local')
  assert.equal(url.pathname, '/stock/BRK-B')
  assert.equal(url.searchParams.get('returnTo'), '/compare?tickers=BRK-B,AAPL&sort=revenue')
  assert.equal(url.searchParams.get('sort'), null)
  assert.equal(api.companyResearchHref('AAPL', '//example.com/compare'), '/stock/AAPL')
})
