const { test } = require('node:test')
const assert = require('node:assert/strict')
const ts = require('typescript')
const fs = require('node:fs')
function load(name) {
  const result = { exports: {} }
  const code = ts.transpileModule(fs.readFileSync(`${__dirname}/${name}.ts`, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  require('node:vm').runInNewContext(code, result)
  return result.exports
}
const { resolveSearch } = load('search-resolution')
const { priceAmount, revenueAmount, comparisonCurrencyNotice } = load('financial-format')
test('name submission resolves to selected suggestion symbol; exact tickers take precedence', () => {
  const apple = [{ symbol: 'AAPL', name: 'Apple Inc.' }]
  assert.equal(resolveSearch('Apple', apple), 'AAPL')
  assert.equal(resolveSearch('apple', apple), 'AAPL')
  assert.equal(resolveSearch('aapl', [...apple, {symbol:'AAP',name:'Advance Auto'}]), 'AAPL')
  assert.equal(resolveSearch('BRK.B', [], true, true), 'BRK-B')
  assert.equal(resolveSearch('VOD.L', [], false, true), 'VOD.L')
  assert.throws(() => resolveSearch('Apple', [], false), /unavailable/)
})
test('ambiguous company submissions require selection', () => {
  assert.throws(() => resolveSearch('Alpha', [{symbol:'GOOG',name:'Alphabet'}, {symbol:'GOOGL',name:'Alphabet'}]), /Select a suggestion/)
})
test('prices preserve trading units and unknowns without converting pence or assuming dollars', () => {
  assert.equal(priceAmount(123.45, 'GBp'), '123.45 GBp')
  assert.equal(priceAmount(-1.25, 'EUR'), '-1.25 EUR')
  assert.equal(priceAmount(123.45), '123.45 Currency unknown')
  assert.equal(priceAmount(null, 'JPY'), 'Unavailable')
})
test('revenue labels each reporting currency and discloses incompatible comparison units', () => {
  assert.equal(revenueAmount(1200000, 'JPY'), '1.2M JPY')
  assert.equal(revenueAmount(0), '0 Currency unknown')
  assert.match(comparisonCurrencyNotice([{reporting_currency:'JPY'}, {reporting_currency:'USD'}]), /not directly comparable/)
  assert.match(comparisonCurrencyNotice([{}, {}]), /unknown/)
  assert.match(comparisonCurrencyNotice([{reporting_currency:'EUR'}, {reporting_currency:'EUR'}]), /same reporting currency/)
})

test('uncatalogued names never silently become tickers, even when uppercase', () => {
  for (const name of ['Vodafone', 'VODAFONE', 'Nonexistentzz']) {
    assert.throws(() => resolveSearch(name, []), /No matching companies/)
    assert.throws(() => resolveSearch(name, [], false), /unavailable/)
  }
  assert.equal(resolveSearch('Shopify', [{symbol:'SHOP',name:'Shopify Inc.'}]), 'SHOP')
  assert.throws(() => resolveSearch('Vodafone', [{symbol:'VOD',name:'Vodafone'}, {symbol:'VOD.L',name:'Vodafone'}]), /Select a suggestion/)
  assert.equal(resolveSearch('vod.l', [], false, true), 'VOD.L')
})
