const {test}=require('node:test')
const assert=require('node:assert/strict')
const ts=require('typescript'), fs=require('node:fs'), vm=require('node:vm')
const api={}
vm.runInNewContext(ts.transpileModule(fs.readFileSync(`${__dirname}/collection.ts`,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:api})
const job={symbol:'AAPL',run_id:'run-1',status:'processing',message:'Collecting news',started_at:'2026-11-01T01:00:00Z',providers:{news:{status:'completed',count:3,message:'Saved three'}}}
test('job validation rejects another ticker and malformed progress without fabricating identity',()=>{
 assert.equal(api.readCollectionJob(job,'AAPL'),job)
 assert.throws(()=>api.readCollectionJob(job,'MSFT'))
 assert.throws(()=>api.readCollectionJob({...job,status:'invented'},'AAPL'))
 assert.throws(()=>api.readCollectionJob({...job,started_at:null},'AAPL'))
 assert.throws(()=>api.readCollectionJob({...job,providers:{news:null}},'AAPL'))
})
test('active and terminal states have distinct labels and stable outcome identities',()=>{
 for(const status of ['pending','processing']) {assert.equal(api.collectionActive({...job,status}),true);assert.equal(api.collectionOutcome({...job,status}),null)}
 const keys=new Set()
 for(const status of ['completed','partial','failed']) {
  const result={...job,status,completed_at:'2026-11-01T01:01:00Z'}
  assert.equal(api.collectionActive(result),false)
  assert.equal(api.collectionOutcome(result),api.collectionOutcome({...result}))
  keys.add(api.collectionOutcome(result))
 }
 assert.equal(keys.size,3)
 assert.equal(api.collectionLabel({...job,status:'partial'}),'Collection partially completed')
 assert.equal(api.collectionLabel({...job,status:'failed'}),'Collection failed')
 assert.notEqual(api.collectionOutcome({...job,status:'completed'}),api.collectionOutcome({...job,status:'completed',run_id:'run-2'}))
})
