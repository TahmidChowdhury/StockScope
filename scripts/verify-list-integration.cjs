// Controlled API fixtures for the list merge reconciliation; no live writes/providers.
const {chromium}=require('playwright'),assert=require('node:assert/strict')
const base=process.env.QA_BASE||'http://127.0.0.1:3198'
;(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 for(const width of [1440,320]){
  const page=await browser.newPage({viewport:{width,height:900},reducedMotion:'reduce',serviceWorkers:'block'})
  await page.addInitScript(()=>sessionStorage.setItem('stockscope_session',JSON.stringify({user:{id:'fixture',role:'member'},role:'member',accessToken:'fixture',expiresAt:Date.now()+3600000})))
  const lists=[],writes=[],errors=[];page.on('pageerror',e=>errors.push(e.message))
  await page.route('https://**',r=>r.fulfill({status:404,body:''}))
  await page.route('**/api/**',async r=>{const p=new URL(r.request().url()).pathname,m=r.request().method();let json=[]
   if(m==='POST'&&p==='/api/lists'){const body=r.request().postDataJSON();writes.push(body);json={id:'session',name:body.name,items:body.initial_symbol?[{symbol:body.initial_symbol,pinned:false}]:[]};lists.push(json)}
   else if(m==='PUT'&&p.endsWith('/items/batch')){const body=r.request().postDataJSON();writes.push(body);for(const symbol of body.symbols)lists[0].items.push({symbol,pinned:false});json=lists[0]}
   else if(p==='/api/lists')json=lists
   else if(p==='/api/stocks')json={stocks:[]}
   await r.fulfill({json,headers:{'access-control-allow-origin':base,'access-control-allow-headers':'Authorization,Content-Type','access-control-allow-methods':'GET,POST,PUT,OPTIONS'}})
  })
  await page.goto(base+'/lists?add=VOD.L')
  await page.getByRole('textbox',{name:'New list',exact:true}).fill('Session list')
  await page.getByRole('button',{name:'Create list',exact:true}).click()
  await page.getByRole('button',{name:'Quick view VOD.L',exact:true}).waitFor()
  assert.deepEqual(writes[0],{name:'Session list',initial_symbol:'VOD.L'})
  const input=page.getByRole('textbox',{name:/Add tickers/})
  await input.fill('BAD$');await page.getByRole('button',{name:'Add to list',exact:true}).click()
  await page.getByRole('alert').filter({hasText:'not a valid ticker'}).waitFor();assert.equal(writes.length,1)
  await input.fill('AAPL');await page.getByRole('button',{name:'Add to list',exact:true}).click()
  await page.getByRole('button',{name:'Quick view AAPL',exact:true}).waitFor();assert.equal(writes.length,2)
  assert.ok(await page.getByRole('button',{name:'Remove AAPL from Session list',exact:true}).isVisible())
  assert.ok(await page.getByRole('link',{name:'Logos provided by Elbstream'}).evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=16))
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[])
  await page.goto(base+'/lists?list=missing');await page.getByText('This list is unavailable.',{exact:false}).waitFor()
  await page.getByRole('link',{name:'View all saved research',exact:true}).click();await page.getByRole('heading',{name:'Research library',exact:true}).waitFor()
  await page.close();console.log(width,'create-and-save, retained initial ticker, invalid ticker blocked, confirmed membership, missing list recovery, attribution PASS')
 }
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1})
