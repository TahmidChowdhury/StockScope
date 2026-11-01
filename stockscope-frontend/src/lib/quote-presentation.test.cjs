const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript'),vm=require('node:vm')
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server')
const financial={exports:{}}
vm.runInNewContext(ts.transpileModule(fs.readFileSync(`${__dirname}/financial-format.ts`,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,financial)
let data
const component={exports:{},require:name=>{
 if(name==='react/jsx-runtime')return require(name)
 if(name==='@/lib/financial-format')return financial.exports
 if(name==='@tanstack/react-query')return {useQuery:()=>({data,isPending:false,isError:false,refetch:()=>{}})}
 if(name==='@/lib/api')return {ApiError:class extends Error{}}
 if(name==='./ResearchPanel')return {default:({children})=>React.createElement('section',null,children)}
 if(name==='./ResearchLoading')return {Skeleton:()=>null}
 if(name==='lucide-react')return {RefreshCw:()=>null}
 throw new Error(name)
}}
vm.runInNewContext(ts.transpileModule(fs.readFileSync(`${__dirname}/../components/KeyMetrics.tsx`,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText,component)
test('actual VOD.L quote is rendered with its case-sensitive trading unit, never reporting currency',()=>{
 data={currency:'GBp',financialCurrency:'EUR',currentPrice:119.1,quote_as_of:'2026-10-30T16:47:03Z',dayLow:116.65,dayHigh:119.2}
 const html=renderToStaticMarkup(React.createElement(component.exports.default,{symbol:'VOD.L'}))
 assert.match(html,/119\.10 GBp/);assert.match(html,/116\.65 GBp/)
 assert.doesNotMatch(html,/119\.10 GBP|119\.10 EUR/)
 assert.match(html,/<p class="[^"]*">Provider quote · GBp<\/p>/)
 assert.doesNotMatch(html,/<p class="[^"]*(eyebrow|uppercase)[^"]*">Provider quote/)
})
test('missing quote-unit metadata is explicit even when reporting currency exists',()=>{
 data={currency:null,financialCurrency:'EUR',currentPrice:119.1,earningsPerShare:-.01}
 const html=renderToStaticMarkup(React.createElement(component.exports.default,{symbol:'VOD.L'}))
 assert.match(html,/119\.10 Currency unknown/)
 assert.match(html,/-0\.01 Currency unknown/)
})
