// Controlled API fixtures, not live-provider verification. Run with QA_BASE and Playwright on NODE_PATH.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs')
const base=process.env.QA_BASE||'http://127.0.0.1:3198',out='/tmp/stockscope-research'
fs.mkdirSync(out,{recursive:true})
const pause=ms=>new Promise(r=>setTimeout(r,ms))
const job=(symbol,status='processing')=>({symbol,run_id:`run-${symbol}`,status,message:`${symbol} actual ${status} outcome`,started_at:'2026-10-30T10:00:00Z',completed_at:status==='processing'?null:'2026-10-30T10:05:00Z',providers:{news:{status:'completed',count:1,message:'Saved publisher evidence'},sec_facts:{status:status==='partial'||status==='failed'?'failed':'pending',count:0,message:'SEC fixture outcome'}}})
async function setup(browser,width,role='member'){
 const page=await browser.newPage({viewport:{width,height:900},reducedMotion:'reduce',serviceWorkers:'block'});page.setDefaultTimeout(12000)
 await page.addInitScript(role=>sessionStorage.setItem('stockscope_session',JSON.stringify({user:{id:'fixture',role},role,accessToken:'fixture',expiresAt:Date.now()+3600000})),role)
 const state={jobs:{},version:1,posts:0,gets:0,forbidden:0,failStatus:false,rate:false,empty:false,delay:0,concurrent:0,max:0},errors=[]
 page.on('pageerror',e=>errors.push(e.message));await page.route('https://**',r=>r.fulfill({status:404,body:''}))
 await page.route('**/api/**',async r=>{
  const url=new URL(r.request().url()),p=url.pathname,symbol=p.split('/')[3];let json=[],status=200,extra={}
  if(r.request().method()==='OPTIONS'){}
  else if(p==='/api/stocks/analyze') {state.posts++;const s=r.request().postDataJSON().symbol;if(state.rate){status=429;json={detail:'Controlled collection cooldown'};extra['Retry-After']='2'}else{state.jobs[s]=job(s);json=state.jobs[s];await pause(500)}}
  else if(p.endsWith('/status')){state.gets++;state.concurrent++;state.max=Math.max(state.max,state.concurrent);await pause(state.delay);state.concurrent--;if(state.failStatus){status=503;json={detail:'Controlled status failure'}}else if(state.jobs[symbol])json=state.jobs[symbol];else{status=404;json={detail:'No tracked job'}}}
  else if(p.endsWith('/investment-advice')||p.endsWith('/quantitative'))state.forbidden++
  else if(p.endsWith('/news')){const articles=state.empty?[]:[{title:`Saved ${symbol} article v${state.version}`,source:'Fixture publisher',url:`https://example.com/${symbol}`,publishedAt:'2026-10-29T12:00:00Z',provider_seen_at:'2026-10-30T09:00:00Z'}];json={articles,sources:['Fixture publisher'],count:articles.length,total:articles.length,saved_total:articles.length,offset:0,limit:Number(url.searchParams.get('limit')||20),has_more:false,can_collect:['member','admin'].includes(role)}}
  else if(p==='/api/lists')json=[{id:'fixture',name:'Fixture pins',items:['AAPL','MSFT'].map(symbol=>({symbol,pinned:true}))}]
  else if(p.endsWith('/stocks'))json={stocks:['AAPL','MSFT'].map(symbol=>({symbol,total_posts:1,last_updated:'2026-10-30'}))}
  else if(p.endsWith('/info'))json={symbol,displayName:symbol==='AAPL'?'Apple Inc.':'Microsoft Corporation'}
  else if(/^\/api\/stocks\/[^/]+$/.test(p)){if(state.empty){status=404;json={detail:'No saved evidence'}}else json={ticker:symbol,total_posts:1,sources:[{source:'Fixture publisher',count:1,latest_update:'2026-10-29T12:00:00Z',freshness:'stale',unknown_timestamps:0}],sentiment_metrics:{sample_size:1,avg_sentiment:.1},freshness:'stale',generated_at:'2026-10-31T12:00:00Z',filings:[{form_type:'8-K',description:`${symbol} filing event`,filing_date:'2026-10-28',url:'https://sec.gov/fixture'}]}}
  await r.fulfill({status,json,headers:{...extra,'access-control-expose-headers':'Retry-After','access-control-allow-origin':base,'access-control-allow-headers':'Authorization,Content-Type','access-control-allow-methods':'GET,POST,OPTIONS'}}).catch(()=>{})
 });return {page,state,errors}
}
async function lifecycle(browser,width){
 const {page,state,errors}=await setup(browser,width),tab=name=>page.getByRole('navigation',{name:'Company research sections'}).getByRole('link',{name,exact:true}).click(),run=page.locator('[aria-label="Collection status"]'),refresh=page.getByRole('button',{name:'Refresh sources',exact:true})
 await page.goto(base+'/stock/AAPL?tab=analysis');await page.getByRole('link',{name:'Saved AAPL article v1'}).waitFor();await refresh.click();await tab('News');await pause(700);await tab('Research summary');await page.getByText('AAPL actual processing outcome',{exact:true}).waitFor();assert.equal(await run.getAttribute('data-run-id'),'run-AAPL');assert.equal(state.posts,1)
 state.delay=1800;state.max=0;await pause(5200);assert.equal(state.max,1);state.delay=0
 await tab('News');await pause(2000);const stopped=state.gets;await pause(1800);assert.equal(state.gets,stopped)
 state.jobs.AAPL=job('AAPL','partial');state.version=2;await tab('Research summary');await page.getByText('Collection partially completed',{exact:true}).waitFor();await page.getByRole('link',{name:'Saved AAPL article v2'}).waitFor();await page.getByText('SEC facts: failed · 0 items',{exact:true}).waitFor()
 assert.ok((await page.getByRole('region',{name:'Recent saved articles'}).innerText()).includes('Published:'));await page.getByText('SEC · Filed: 2026-10-28',{exact:true}).waitFor()
 await page.screenshot({path:`${out}/partial-${width}.png`,fullPage:true})
 await page.getByText('Source coverage and dates',{exact:true}).click();await page.getByText('Research limitations',{exact:true}).click();await page.getByText('Research limitations',{exact:true}).scrollIntoViewIfNeeded();await page.getByText(/Evidence summary calculated:/).waitFor();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:`${out}/coverage-${width}.png`,fullPage:true})
 await tab('News');await page.getByRole('link',{name:'Saved AAPL article v2'}).waitFor();await tab('Research summary');await pause(1700);assert.equal(state.posts,1)
 state.failStatus=true;await tab('News');await tab('Research summary');await page.getByRole('button',{name:'Retry collection status'}).waitFor();assert.ok(await refresh.isDisabled());state.failStatus=false;await page.getByRole('button',{name:'Retry collection status'}).click();await page.getByText('AAPL actual partial outcome',{exact:true}).waitFor()
 state.jobs.AAPL=job('AAPL','failed');await tab('News');await tab('Research summary');await page.getByText('Collection failed',{exact:true}).waitFor();await page.getByRole('link',{name:'Saved AAPL article v2'}).waitFor();await page.screenshot({path:`${out}/failed-${width}.png`,fullPage:true})
 state.jobs.AAPL=job('AAPL','completed');await tab('News');await tab('Research summary');await page.getByText('Collection completed',{exact:true}).waitFor()
 // Client navigation to another company (shared cache), then recover the original run.
 if(width<1024)await page.getByRole('button',{name:'Open workspace menu'}).click()
 await page.getByRole('link',{name:'MSFT',exact:true}).click();await tab('Research summary');await page.getByRole('link',{name:'Saved MSFT article v2'}).waitFor();assert.equal(await run.getAttribute('data-run-id'),null);assert.ok(!(await run.innerText()).includes('AAPL'))
 if(width<1024)await page.getByRole('button',{name:'Open workspace menu'}).click()
 await page.getByRole('link',{name:'AAPL',exact:true}).click();await tab('Research summary');await page.getByText('AAPL actual completed outcome',{exact:true}).waitFor();assert.equal(state.posts,1)
 state.rate=true;await refresh.click();await page.getByRole('alert').filter({hasText:'Collection request:'}).waitFor();assert.ok(await refresh.isDisabled());await pause(2300);assert.ok(await refresh.isEnabled());assert.equal(state.posts,2)
 assert.equal(state.forbidden,0);assert.equal(await page.getByRole('button',{name:/Generate summary|Metric availability/}).count(),0);assert.deepEqual(errors,[]);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.close();console.log(width,'job identity, tab-away partial/completed/failed outcomes, polling cleanup, ticker isolation, status retry, cooldown, direct evidence PASS')
}
async function empty(browser,width,role){const {page,state,errors}=await setup(browser,width,role);state.empty=true;await page.goto(base+'/stock/EMPTY?tab=analysis');await page.getByText('No saved articles for EMPTY.',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Refresh sources'}).count(),role==='member'?1:0);if(role==='member'){await page.getByRole('button',{name:'Refresh sources'}).click();await page.getByText('EMPTY actual processing outcome',{exact:true}).waitFor();await page.getByText('Collection is in progress. Articles will appear if sources return usable evidence.',{exact:true}).waitFor()}await page.screenshot({path:`${out}/empty-${role}-${width}.png`,fullPage:true});assert.deepEqual(errors,[]);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.close();console.log(width,role,'empty/collecting permissions PASS')}
;(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{for(const width of [1440,320]){await lifecycle(browser,width);for(const role of ['member','viewer','guest','demo'])await empty(browser,width,role)}}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1})
