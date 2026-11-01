const { test } = require('node:test')
const assert = require('node:assert/strict')
const ts = require('typescript')
const fs = require('node:fs')
const vm = require('node:vm')
const code = ts.transpileModule(fs.readFileSync(`${__dirname}/price-cooldown.ts`, 'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText
function clock() {
  let now = 1000, id = 0
  const timers = new Map(), exports = {}
  vm.runInNewContext(code, {exports,Date:{now:()=>now},setTimeout:(fn,delay)=>{timers.set(++id,{fn,delay});return id},clearTimeout:id=>timers.delete(id)})
  return {timers,schedule:exports.scheduleDeadline, advance(ms) {now+=ms;const pending=[...timers.values()];timers.clear();pending.forEach(t=>t.fn())}}
}
test('cooldown expiry fires once and cancellation prevents stale updates on unmount', () => {
  const c=clock();let updates=0
  const cleanup=c.schedule(2000,()=>updates++)
  assert.equal(c.timers.size,1)
  c.advance(1000);assert.equal(updates,1);assert.equal(c.timers.size,0)
  cleanup()
  const cancel=c.schedule(5000,()=>updates++)
  const queued=[...c.timers.values()][0].fn
  cancel();assert.equal(c.timers.size,0)
  queued();assert.equal(updates,1)
})
test('replacement deadlines cancel old timers and long deadlines do not overflow', () => {
  const c=clock();let updates=0
  const cancel=c.schedule(2000,()=>updates++)
  cancel();c.schedule(4000,()=>updates++)
  c.advance(1000);assert.equal(updates,0)
  c.advance(2000);assert.equal(updates,1)
  const stop=c.schedule(1e12,()=>updates++)
  assert.equal([...c.timers.values()][0].delay,2147483647)
  stop();assert.equal(c.timers.size,0)
})

test('cooldown persists across ranges, query garbage collection, and repeated denials', () => {
  class ApiError extends Error { constructor(status,retryAt) {super('limited');this.status=status;this.retryAt=retryAt} }
  const hooks = {}
  const source = ts.transpileModule(fs.readFileSync(`${__dirname}/../hooks/usePriceCooldown.ts`, 'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText
  vm.runInNewContext(source, {exports:hooks,require:name=>name==='@/lib/api'?{ApiError}:{}})
  let rows=[],stored=0,defaults
  const client={getQueryCache:()=>({findAll:()=>rows}),getQueryData:()=>stored,setQueryDefaults:(_key,value)=>{defaults=value},setQueryData:(_key,update)=>{stored=update(stored)}}
  rows=[{state:{error:new ApiError(429,3000)}}]
  assert.equal(hooks.priceCooldownDeadline(client),3000)
  hooks.rememberPriceCooldown(client,rows[0].state.error)
  rows=[] // Range cache can expire without allowing an early request.
  assert.equal(hooks.priceCooldownDeadline(client),3000)
  assert.equal(defaults.gcTime,Infinity)
  hooks.rememberPriceCooldown(client,new ApiError(429,5000))
  hooks.rememberPriceCooldown(client,new ApiError(429,2000))
  hooks.rememberPriceCooldown(client,new ApiError(429,null))
  hooks.rememberPriceCooldown(client,new ApiError(503,9000))
  assert.equal(hooks.priceCooldownDeadline(client),5000)
})
