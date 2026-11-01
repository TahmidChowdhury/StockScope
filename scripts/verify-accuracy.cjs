// Controlled API fixtures only; no live providers or credentials.
// Run against `npm run dev`: QA_BASE=http://127.0.0.1:3000 node scripts/verify-accuracy.cjs
// Requires Playwright and Chrome; ARTIFACT_DIR controls screenshot output.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const out=process.env.ARTIFACT_DIR || '/tmp/stockscope-accuracy';
fs.mkdirSync(out,{recursive:true});
const base=process.env.QA_BASE || 'http://127.0.0.1:3000';
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try {
for(const width of [1440,390,320]) {
 const page=await browser.newPage({viewport:{width,height:900},serviceWorkers:'block',reducedMotion:'reduce'});page.setDefaultTimeout(15000);page.setDefaultNavigationTimeout(45000);
 const errors=[];page.on('pageerror', e=>errors.push(e.message));
 let mixed=false;
 await page.addInitScript(()=>sessionStorage.setItem('stockscope_session',JSON.stringify({user:{id:'accuracy',name:'Test',role:'member'},role:'member',expiresAt:Date.now()+3600000,accessToken:'fixture'})));
 const companies=[{ticker:'EUR',insufficient_data:false,revenue_ttm:1200000,reporting_currency:'EUR'},{ticker:'JPY',insufficient_data:false,revenue_ttm:2000000,reporting_currency:'JPY'},{ticker:'UNK',insufficient_data:false,revenue_ttm:3000000}];
 await page.route('https://**', route=>route.fulfill({status:404,body:''}));
 await page.route('**/api/**',async r=>{const u=new URL(r.request().url()),p=u.pathname;let json=[];
 if(p.endsWith('/stocks'))json={stocks:[]};
 else if(p.endsWith('/suggestions'))json=/alpha/i.test(u.searchParams.get('q'))?[{symbol:'GOOG',name:'Alphabet'},{symbol:'GOOGL',name:'Alphabet'}]:/apple|aapl/i.test(u.searchParams.get('q'))?[{symbol:'AAPL',name:'Apple Inc.'}]:[];
 else if(p.endsWith('/market-tape'))json=[{symbol:'SPY',change:1,as_of:'2026-10-30T20:00:00Z'},{symbol:'QQQ',change:2,as_of:mixed?'2026-10-29T20:00:00Z':'2026-10-30T20:00:00Z'}];
 else if(p.endsWith('/info')) { const symbol=p.split('/')[3];json={symbol,displayName:symbol==='AAPL'?'Apple Inc.':symbol==='VOD.L'?'Vodafone Group Plc':symbol}; }
 else if(p.includes('/price-history')) {
   const symbol=p.split('/')[3], vod=symbol==='VOD.L', unknownQuote=symbol==='UNK', unknownHistory=symbol==='UNKH';
   json={symbol,period:u.searchParams.get('period'),currency:unknownHistory?null:vod?'GBp':unknownQuote?'EUR':'USD',quote_currency:unknownQuote?null:vod?'GBP':unknownHistory?'JPY':'USD',currentPrice:vod?1.25:123.45,priceChange:vod?-.05:1.25,priceChangePercent:vod?-3.85:1.02,quote_as_of:'2026-10-30T20:00:00Z',lastHistoricalClose:123.45,lastHistoricalCloseDate:'2026-10-30',data:[{date:'2026-10-29',open:120,high:124,low:119,close:122,volume:100},{date:'2026-10-30',open:122,high:125,low:121,close:123.45,volume:110}]};
 }
 else if(p.includes('/screener'))json={results:companies,total_attempted:3,total_failed:0,total_insufficient:0,total_evaluated:3,total_matches:3,total_screened:3,filters_applied:{},universe_name:'Fixture'};
 else if(p.endsWith('/congress'))json={records:[],total:0,summary:{},filtered_summary:{},members:[],symbols:[]};
 await r.fulfill({json,headers:{'access-control-allow-origin':base,'access-control-allow-headers':'Authorization,Content-Type','access-control-allow-methods':'GET,POST,OPTIONS'}});
 });
 const visit=async path=>{await page.goto(base+path,{waitUntil:'networkidle'})};
 const overflow=async label=>{
  const fits=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth && document.querySelector('main').scrollWidth<=document.querySelector('main').clientWidth+1);
  if(!fits){await page.screenshot({path:`${out}/overflow-${width}.png`});console.error(await page.evaluate(()=>[...document.querySelectorAll('main *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).map(el=>({tag:el.tagName,class:el.className,text:el.textContent?.slice(0,90),right:el.getBoundingClientRect().right})).slice(-12)));}
  assert.ok(fits,`${width} ${label} overflow`);
 };
 for(const method of ['Explore','Enter','suggestion','keyboard']) {
 await visit('/');const input=page.getByRole('combobox');await input.fill('Apple');
 if(method==='Explore')await page.getByRole('button',{name:'Explore',exact:true}).click();
 else if(method==='Enter') { await page.getByRole('option',{name:/AAPL/}).waitFor();await input.press('Enter'); }
 else if(method==='keyboard') { await page.getByRole('option',{name:/AAPL/}).waitFor();await input.press('ArrowDown');await input.press('Enter'); }
 else await page.getByRole('option',{name:/AAPL/}).click();
 await page.waitForURL('**/stock/AAPL');await page.getByRole('heading',{name:'Apple Inc.',exact:true}).waitFor();await page.getByText('Chart unit: USD', {exact:false}).waitFor();await overflow('chart');
 assert.match(await page.locator('main').innerText(),/123.45 USD/);
 if(method==='Explore') { const box=await page.locator('.recharts-wrapper').boundingBox();await page.mouse.move(box.x+box.width-30,box.y+50);await page.getByText(/Close: .* USD/).waitFor(); }
 if(method==='Explore')await page.screenshot({path:`${out}/accuracy-chart-${width}.png`});
 console.log(width,method,'Apple -> AAPL');
 }
 await visit('/');await page.getByRole('combobox').fill('Alpha');await page.getByRole('button',{name:'Explore',exact:true}).click();await page.getByRole('alert').filter({hasText:'Several companies match'}).waitFor();assert.equal(new URL(page.url()).pathname,'/');
 await visit('/');await page.getByRole('combobox').fill('Alpha');await page.getByRole('option').first().waitFor();await page.getByRole('combobox').press('Enter');await page.getByRole('alert').filter({hasText:'Several companies match'}).waitFor();assert.equal(new URL(page.url()).pathname,'/');
 await page.getByRole('combobox').press('Escape');await page.getByRole('checkbox',{name:'Enter ticker directly',exact:true}).check();await page.getByRole('combobox').fill('VOD.L');await page.getByRole('button',{name:'Explore',exact:true}).click();await page.waitForURL('**/stock/VOD.L');
 await page.getByRole('heading',{name:'Vodafone Group Plc',exact:true}).waitFor();
 await page.getByRole('heading',{name:'VOD.L Stock Price',exact:true}).waitFor();
 assert.ok(await page.getByRole('link',{name:'Logos provided by Elbstream',exact:true}).evaluate(el=>parseFloat(getComputedStyle(el).fontSize)>=16));
 await page.getByText('Chart unit: GBp',{exact:false}).waitFor();
 let content=await page.locator('main').innerText();assert.match(content,/1.25 GBP/);assert.match(content,/-0.05 GBP \(-3.85%\)/);assert.match(content,/Latest chart close: 123.45 GBp/);assert.doesNotMatch(content,/123.45 GBP/);
 let box=await page.locator('.recharts-wrapper').boundingBox();await page.mouse.move(box.x+box.width-30,box.y+50);await page.getByText(/Close: .* GBp/).waitFor();
 for(const [symbol,chartUnit,quoteUnit] of [['UNK','EUR','Currency unknown'],['UNKH','Currency unknown','JPY']]) {
   await visit('/stock/'+symbol);await page.getByRole('heading',{name:symbol,exact:true}).waitFor();await page.getByText('Chart unit: '+chartUnit,{exact:false}).waitFor();
   content=await page.locator('main').innerText();assert.ok(content.includes('123.45 '+quoteUnit));assert.ok(content.includes('+1.25 '+quoteUnit+' (+1.02%)'));assert.ok(content.includes('Latest chart close: 123.45 '+chartUnit));
   box=await page.locator('.recharts-wrapper').boundingBox();await page.mouse.move(box.x+box.width-30,box.y+50);await page.getByText(new RegExp('Close: .* '+chartUnit)).waitFor();
   await overflow('unknown chart');await page.screenshot({path:`${out}/accuracy-${symbol}-${width}.png`});
 }
 await visit('/');const tape=page.getByRole('region',{name:'Saved daily percentage changes'});await tape.waitFor();assert.equal(await tape.getByText('Oct 30, 2026',{exact:true}).count(),1);
 mixed=true;await visit('/');await tape.locator('.market-tape-set').first().getByText('Oct 29, 2026',{exact:true}).waitFor();assert.equal(await tape.locator('.market-tape-set').first().getByText('Oct 30, 2026',{exact:true}).count(),1);await overflow('mixed tape');await page.screenshot({path:`${out}/accuracy-tape-${width}.png`});
 await visit('/screener');await page.getByRole('button',{name:/Run screen/i}).click();await page.getByText('1.2M EUR',{exact:true}).waitFor();await page.getByText('2M JPY',{exact:true}).waitFor();await page.getByText('3M Currency unknown',{exact:true}).waitFor();
 const checks=page.getByRole('checkbox');console.log('checkboxes',await checks.count());for(const c of await checks.all())if((await c.getAttribute('aria-label')||'').includes('Select'))await c.check();
 await page.getByRole('button',{name:/Compare selected/}).click();const dialog=page.getByRole('dialog');await dialog.waitFor();await dialog.getByText('1.2M EUR',{exact:true}).waitFor();await dialog.getByText('3M Currency unknown',{exact:true}).waitFor();assert.match(await dialog.innerText(),/not directly comparable/);await overflow('comparison');await page.screenshot({path:`${out}/accuracy-compare-${width}.png`});
 await dialog.getByRole('button',{name:'Close comparison'}).click();await page.reload({waitUntil:'networkidle'});await page.getByText('1.2M EUR',{exact:true}).waitFor();
 assert.deepEqual(errors,[]);console.log(width,'unknown units, mixed comparison, shared/mixed tape, no overflow or page errors PASS');await page.close();
}
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
