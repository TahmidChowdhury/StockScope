// Controlled fixtures. Requires Playwright + Chrome, a running frontend, and QA_BASE.
const {chromium}=require('playwright')
const assert=require('node:assert/strict')
const fs=require('node:fs')
const base=process.env.QA_BASE || 'http://127.0.0.1:3000'
const out=process.env.ARTIFACT_DIR || '/tmp/stockscope-reliability'
fs.mkdirSync(out,{recursive:true})
const quote=(symbol,period)=>({symbol,period,currency:'GBp',quote_currency:'GBP',currentPrice:1.25,priceChange:-.05,priceChangePercent:-3.85,lastHistoricalClose:123.45,lastHistoricalCloseDate:'2026-10-30',quote_as_of:'2026-10-30T20:00:00Z',data:[{date:'2026-10-29',open:120,high:124,low:119,close:122,volume:100},{date:'2026-10-30',open:122,high:125,low:121,close:123.45,volume:110}]})
const portfolios=[{id:'p1',name:'Preserved portfolio',initial_cash:10000,created_at:'2026-10-30T12:00:00Z',benchmark:'SPY'}]
const runs=[{id:'b1',name:'Preserved experiment',strategy:'buy_hold',start:'2026-01-01',end:'2026-10-30'}]
const congress={records:[{disclosure_id:'d1',member:'Fixture Member',owner:'self',symbol:'AAPL',side:'buy',transaction_date:'2026-10-01',available_date:'2026-10-05',lag_days:4,amount_range:'$1,001–$15,000',asset_type:'Stock',source_url:'https://example.com/filing'}],total:1,offset:0,members:['Fixture Member'],last_import:null}
async function setup(browser,width) {
 const page=await browser.newPage({viewport:{width,height:900},serviceWorkers:'block',reducedMotion:'reduce'})
 page.setDefaultTimeout(15000);page.setDefaultNavigationTimeout(45000)
 page.on('crash',()=>console.error('Page crashed'));
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.addInitScript(()=>sessionStorage.setItem('stockscope_session',JSON.stringify({user:{id:'reliability',name:'Test',role:'member'},role:'member',expiresAt:Date.now()+3600000,accessToken:'fixture'})))
 const state={fail:new Set(),empty:new Set(),counts:{},chartMode:'normal',chartCount:0,delay:0}
 await page.route('https://**', route=>route.fulfill({status:404,body:''}));
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url()),path=url.pathname
  if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers:{'access-control-allow-origin':base,'access-control-allow-headers':'Authorization,Content-Type','access-control-allow-methods':'GET,POST,OPTIONS'}})
  let json=[],status=200,extra={}
  const dataset=path.match(/^\/api\/trading\/(portfolios|backtests|congress)$/)?.[1]
  if(dataset) {
   state.counts[dataset]=(state.counts[dataset]||0)+1
   if(state.hold)await state.hold
   if(state.delay)await new Promise(resolve=>setTimeout(resolve,state.delay))
   if(state.fail.has(dataset)){status=503;json={detail:'Controlled '+dataset+' failure'}}
   else json=dataset==='portfolios'?(state.empty.has(dataset)?[]:portfolios):dataset==='backtests'?(state.empty.has(dataset)?[]:runs):state.empty.has(dataset)?{...congress,records:[],total:0}:congress
  } else if(path.includes('/price-history')) {
   state.chartCount++
   if(state.chartMode==='normal')json=quote(path.split('/')[3],url.searchParams.get('period'))
   else {status=429;json={detail:'Controlled chart cooldown'};if(state.chartMode==='seconds')extra['Retry-After']='3';if(state.chartMode==='date')extra['Retry-After']=new Date(Date.now()+4000).toUTCString()}
  } else if(path.endsWith('/info'))json={symbol:path.split('/')[3],displayName:path.includes('/VOD.L/')?'Vodafone Group Plc':path.split('/')[3]}
  else if(path.endsWith('/stocks'))json={stocks:[]}
  else if(path.endsWith('/congress/collection'))json={enabled:false,state:'disabled',row_count:1,source:null}
  if(dataset==='congress' && url.searchParams.has('symbol') && status===200)json={...json,records:[],total:0,symbols:[],summary:{},filtered_summary:{},mode:'csv_import',provenance:{source:'user_supplied_csv',dates_verified:false}}
  await route.fulfill({status,json,headers:{...extra,'access-control-expose-headers':'Retry-After','access-control-allow-origin':base,'access-control-allow-headers':'Authorization,Content-Type','access-control-allow-methods':'GET,POST,OPTIONS'}})
 })
 return {page,state,errors}
}
async function checkTrading(browser,width,failed) {
 const {page,state,errors}=await setup(browser,width)
 state.fail.add(failed)
 await page.goto(base+'/trading',{waitUntil:'networkidle'})
 const tabs={portfolios:'Paper portfolio',backtests:'Backtesting',congress:'Disclosure imports'}
 const retry={portfolios:'Retry portfolios',backtests:'Retry backtests',congress:'Retry disclosures'}
 for(const dataset of ['portfolios','backtests','congress']) {
  await page.getByRole('button',{name:tabs[dataset],exact:true}).click()
  if(dataset===failed){await page.getByRole('button',{name:retry[dataset],exact:true}).waitFor().catch(async error=>{console.error('Failed state',state.counts,await page.locator('main').innerText());await page.screenshot({path:`${out}/failure-${failed}-${width}.png`});throw error});const text=await page.locator('main').innerText();assert.ok(!text.includes('No paper portfolios yet.'));assert.ok(!text.includes('No saved experiments yet'));assert.ok(!text.includes('No disclosures available.'))}
  else if(dataset==='portfolios')await page.getByText('Preserved portfolio',{exact:true}).waitFor()
  else if(dataset==='backtests')await page.getByText('Preserved experiment',{exact:false}).waitFor()
  else await page.getByRole('cell',{name:'Fixture Member',exact:false}).waitFor()
 }
 await page.getByRole('button',{name:tabs[failed],exact:true}).click()
 const before={...state.counts};state.fail.delete(failed);state.delay=400
 await page.getByRole('button',{name:retry[failed],exact:true}).click()
 if(failed==='portfolios')await page.getByText('Preserved portfolio',{exact:true}).waitFor()
 else if(failed==='backtests')await page.getByText('Preserved experiment',{exact:false}).waitFor()
 else await page.getByRole('cell',{name:'Fixture Member',exact:false}).waitFor()
 assert.equal(state.counts[failed],before[failed]+1)
 for(const dataset of Object.keys(before))if(dataset!==failed)assert.equal(state.counts[dataset],before[dataset])
 assert.deepEqual(errors,[])
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
 await page.screenshot({path:`${out}/trading-${failed}-${width}.png`})
 console.log(width,failed,'independent failure, no false empty, isolated retry PASS')
 await page.close()
}
async function checkChart(browser,width) {
 const {page,state,errors}=await setup(browser,width)
 await page.goto(base+'/stock/VOD.L',{waitUntil:'networkidle'})
 await page.getByText('Chart unit: GBp',{exact:false}).waitFor()
 const ranges=page.getByRole('group',{name:'Price history period'})
 const range=name=>ranges.getByRole('button',{name,exact:true})
 state.chartMode='seconds';await range('1M').click()
 const retry=page.getByRole('button',{name:'Retry price history',exact:true})
 await retry.waitFor();assert.equal(await retry.isDisabled(),true)
 const count=state.chartCount
 await range('1Y').click();await page.getByText('Latest chart close: 123.45 GBp',{exact:false}).waitFor()
 assert.equal(await range('3M').isDisabled(),true);assert.equal(state.chartCount,count)
 await range('1M').waitFor({state:'visible'})
 await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='1M'&&!b.disabled))
 assert.equal(state.chartCount,count,'deadline must not automatically retry')
 await range('1M').click();await retry.waitFor();assert.equal(await retry.isEnabled(),true)
 state.chartMode='date';await retry.click();await page.getByText('Price requests are cooling down until',{exact:false}).waitFor();assert.equal(await retry.isDisabled(),true);assert.equal(state.chartCount,count+1)
 await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Retry price history'&&!b.disabled))
 assert.equal(state.chartCount,count+1)
 state.chartMode='normal';await retry.click();await page.getByText('Latest chart close: 123.45 GBp',{exact:false}).waitFor();await retry.waitFor({state:'hidden'});assert.equal(state.chartCount,count+2)
 // No usable deadline follows existing manual-retry behavior.
 state.chartMode='missing';await range('3M').click();await retry.waitFor();assert.equal(await retry.isEnabled(),true)
 state.chartMode='normal';await retry.click();await retry.waitFor({state:'hidden'})
 // Navigate away with an active timer, then return. Cached errors preserve the deadline.
 state.chartMode='seconds';await range('6M').click();await retry.waitFor();assert.equal(await retry.isDisabled(),true)
 const leavingCount=state.chartCount
 await page.getByRole('link',{name:'News',exact:true}).click();await page.getByRole('link',{name:'Overview',exact:true}).last().click();await page.getByText('Price requests are cooling down until',{exact:false}).waitFor();assert.equal(state.chartCount,leavingCount);await page.getByRole('link',{name:'News',exact:true}).click();await page.waitForTimeout(3500)
 assert.equal(state.chartCount,leavingCount)
 assert.deepEqual(errors,[])
 console.log(width,'chart seconds/date/repeated 429, cached ranges, manual recovery, unmount PASS')
 await page.close()
}
async function checkEmptyAndRefresh(browser,width) {
 const {page,state,errors}=await setup(browser,width)
 let release
 state.empty=new Set(['portfolios','backtests','congress'])
 state.hold=new Promise(resolve=>{release=resolve})
 await page.goto(base+'/trading',{waitUntil:'domcontentloaded'})
 await page.getByText('Loading portfolios…',{exact:true}).waitFor()
 assert.equal(await page.getByText('No paper portfolios yet.',{exact:true}).count(),0)
 release();state.hold=null
 await page.getByText('No paper portfolios yet.',{exact:true}).waitFor()
 await page.getByRole('button',{name:'Backtesting',exact:true}).click();await page.getByText('No saved experiments yet',{exact:true}).waitFor()
 await page.getByRole('button',{name:'Disclosure imports',exact:true}).click();await page.getByText('No disclosures available.',{exact:false}).waitFor()
 // Restore populated data, then fail a stale revalidation after client navigation.
 state.empty.clear()
 await page.goto(base+'/trading',{waitUntil:'networkidle'})
 await page.getByText('Preserved portfolio',{exact:true}).waitFor()
 await page.clock.install()
 await page.clock.fastForward(301000)
 state.fail.add('portfolios')
 await page.locator('a[href="/"]').filter({visible:true}).first().click()
 await page.waitForURL(base+'/')
 await page.goBack({waitUntil:'domcontentloaded'})
 await page.getByRole('button',{name:'Retry portfolios',exact:true}).waitFor()
 await page.getByText('Preserved portfolio',{exact:true}).waitFor()
 const counts={...state.counts};state.fail.clear();state.delay=300
 await page.getByRole('button',{name:'Retry portfolios',exact:true}).click()
 await page.getByText('Preserved portfolio',{exact:true}).waitFor()
 await page.getByRole('button',{name:'Retry portfolios',exact:true}).waitFor({state:'hidden'})
 assert.equal(state.counts.portfolios,counts.portfolios+1)
 assert.equal(state.counts.backtests,counts.backtests)
 assert.equal(state.counts.congress,counts.congress)
 assert.deepEqual(errors,[])
 console.log(width,'empty only after successful response; stale data retained through failure/retry PASS')
 await page.close()
}
;(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try {
 for(const width of [1440,390]) {
  for(const failed of ['congress','portfolios','backtests'])await checkTrading(browser,width,failed)
  await checkEmptyAndRefresh(browser,width)
  await checkChart(browser,width)
 }
}finally{await browser.close()}})().catch(error=>{console.error(error);process.exitCode=1})
