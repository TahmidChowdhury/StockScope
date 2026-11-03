// Controlled asynchronous fixtures; no live providers or credentials.
// NODE_PATH=<playwright installation>/node_modules QA_BASE=http://127.0.0.1:3107 node scripts/verify-price-loading.cjs
const {chromium} = require('playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const base = process.env.QA_BASE || 'http://127.0.0.1:3107'
const out = process.env.ARTIFACT_DIR || '/tmp/stockscope-loading-qa'
fs.mkdirSync(out, {recursive:true})
const gate = () => { let release; const promise = new Promise(resolve => { release = resolve }); return {promise, release} }
;(async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true})
  try {
    for (const width of [390, 320, 1440]) {
      const page = await browser.newPage({viewport:{width,height:900}, serviceWorkers:'block', reducedMotion:width===320?'reduce':'no-preference'})
      page.setDefaultTimeout(20000)
      const errors = []
      page.on('pageerror', e => errors.push(e.message))
      await page.addInitScript(() => sessionStorage.setItem('stockscope_session', JSON.stringify({user:{id:'qa',name:'QA',role:'member'},role:'member',expiresAt:Date.now()+3600000,accessToken:'fixture'})))
      let prices = gate(), metrics = gate(), fail = false
      await page.route('https://**', r => r.fulfill({status:404,body:''}))
      await page.route('**/api/**', async r => {
        const u = new URL(r.request().url()), p = u.pathname
        let json = []
        if (p.endsWith('/stocks')) json = {stocks:[]}
        else if (p.endsWith('/info')) {
          await metrics.promise
          json = {symbol:'AAPL',displayName:'Apple Inc.',currentPrice:123.45,currency:'USD'}
        } else if (p.endsWith('/price-history')) {
          await prices.promise
          if (fail) return r.fulfill({status:503,json:{detail:'Price provider temporarily unavailable.'}})
          const interval = u.searchParams.get('interval')
          const date = interval === '1h' ? '2026-11-03T10:30:00-05:00' : '2026-11-03'
          json = {symbol:'AAPL',period:u.searchParams.get('period'),interval,currency:'USD',quote_currency:'USD',currentPrice:123.45,priceChange:1.25,priceChangePercent:1.02,quote_as_of:'2026-11-03T15:30:00Z',lastHistoricalClose:123.45,lastHistoricalCloseDate:date,data:[{date, timestamp:Date.parse(date),open:122,high:125,low:121,close:123.45,volume:100}]}
        } else if (p.endsWith('/congress')) json = {records:[],symbols:[],summary:{},filtered_summary:{},mode:'csv_import',provenance:{source:'user_supplied_csv',dates_verified:false}}
        await r.fulfill({json})
      })
      await page.goto(base+'/stock/AAPL', {waitUntil:'domcontentloaded'})
      const card = page.getByRole('region', {name:'AAPL price chart'})
      await card.getByText('Loading price history…', {exact:true}).waitFor()
      assert.doesNotMatch(await card.innerText(), /unavailable|Unknown|Date unknown/i)
      const skeleton = card.locator('span[aria-hidden="true"]').first()
      assert.equal(await skeleton.evaluate(el => getComputedStyle(el).animationName), width===320?'none':'pulse')
      const plotHeight = await card.locator('[aria-busy]').evaluate(el => el.getBoundingClientRect().height)
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth && document.querySelector('main').scrollWidth <= document.querySelector('main').clientWidth+1), 'No horizontal overflow')
      await page.screenshot({path:`${out}/loading-${width}.png`})
      metrics.release()
      await page.getByRole('heading', {name:'Apple Inc.',exact:true}).waitFor()
      assert.match(await card.innerText(), /Loading price history/)
      if (width===390) await card.getByText(/Prices are taking longer than usual/).waitFor()
      prices.release()
      await card.locator('.recharts-wrapper').waitFor()
      assert.equal(await card.locator('[aria-busy]').evaluate(el => el.getBoundingClientRect().height), plotHeight)
      assert.equal(await card.locator('span[aria-hidden="true"]').count(), 0)
      prices = gate()
      await card.getByRole('button', {name:'5D',exact:true}).click()
      await card.getByText(/Loading 5D/).waitFor()
      assert.equal(await card.locator('.recharts-wrapper').count(), 1, 'Keep loaded prices during range requests')
      prices.release()
      await card.getByText(/Hourly bars/).waitFor()
      prices = gate(); fail = true
      await page.reload({waitUntil:'domcontentloaded'})
      await card.getByText('Loading price history…', {exact:true}).waitFor()
      prices.release()
      await card.getByRole('button', {name:'Retry price history'}).waitFor()
      assert.equal(await card.locator('span[aria-hidden="true"]').count(), 0, 'Errors replace skeletons')
      assert.deepEqual(errors, [])
      console.log(`${width}: async metrics, skeletons, motion preference, stable plot height, range placeholder, and error recovery passed`)
      await page.close()
    }
  } finally { await browser.close() }
})().catch(error => {console.error(error); process.exitCode=1})
