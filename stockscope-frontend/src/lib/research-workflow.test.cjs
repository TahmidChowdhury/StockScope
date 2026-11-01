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

test('company return links accept only the supported local research workspaces', () => {
  assert.equal(api.researchReturn('/screener?universe=custom&symbols=AAPL%2CMSFT').label, 'Back to screener')
  assert.equal(api.researchReturn('/compare?tickers=AAPL%2CMSFT').href, '/compare?tickers=AAPL%2CMSFT')
  assert.equal(api.researchReturn('/disclosures?member=Example%20Member&symbol=AAPL').label, 'Back to disclosures')
  assert.equal(api.researchReturn('/disclosures?member=Example%20Member&symbol=AAPL').href, '/disclosures?member=Example%20Member&symbol=AAPL')
  for (const destination of [null, '', 'https://example.com/compare', '//example.com/compare', '/\\example.com/compare', '/trading', '/compare/extra', '/disclosures/extra', '/%63ompare', '/compare\n']) {
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
  const disclosure = new URL(api.companyResearchHref('MSFT', '/disclosures?member=Example%20Member&symbol=MSFT'), 'https://stockscope.local')
  assert.equal(disclosure.searchParams.get('returnTo'), '/disclosures?member=Example%20Member&symbol=MSFT')
  assert.equal(disclosure.searchParams.get('member'), null)
})

test('financial research preserves disclosure context through the company round trip', () => {
  const returnTo = '/disclosures?member=Michael+Rulli&symbol=GOOG&offset=20'
  const financials = new URL(api.companyFundamentalsHref('GOOG', returnTo), 'https://stockscope.local')
  assert.equal(financials.pathname, '/fundamentals/GOOG')
  assert.equal(financials.searchParams.get('returnTo'), returnTo)
  const company = new URL(api.companyResearchHref('GOOG', financials.searchParams.get('returnTo')), 'https://stockscope.local')
  assert.equal(api.researchReturn(company.searchParams.get('returnTo')).href, returnTo)
  assert.equal(api.companyFundamentalsHref('GOOG', '//example.com/disclosures'), '/fundamentals/GOOG')
})

test('empty news can open research summary without losing disclosure filters', () => {
  const returnTo = '/disclosures?member=Michael+Rulli&symbol=GOOG'
  const summary = new URL(api.companyResearchHref('GOOG', returnTo, 'analysis'), 'https://stockscope.local')
  assert.equal(summary.pathname, '/stock/GOOG')
  assert.equal(summary.searchParams.get('tab'), 'analysis')
  assert.equal(summary.searchParams.get('returnTo'), returnTo)
  assert.equal(summary.searchParams.get('member'), null)
  assert.equal(api.companyResearchHref('GOOG', 'https://example.com', 'analysis'), '/stock/GOOG?tab=analysis')
})
