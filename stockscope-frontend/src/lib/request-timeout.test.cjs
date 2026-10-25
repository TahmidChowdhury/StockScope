const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require('typescript')

const compiled = ts.transpileModule(fs.readFileSync(`${__dirname}/request-timeout.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
const exportsObject = {}
vm.runInNewContext(compiled, { exports: exportsObject, AbortController, setTimeout, clearTimeout })
const { withRequestTimeout } = exportsObject

const waitForAbort = (signal) => new Promise((resolve) => {
  if (signal.aborted) resolve('aborted')
  else signal.addEventListener('abort', () => resolve('aborted'), { once: true })
})

test('query cancellation reaches the request without AbortSignal.any or timeout', async () => {
  const parent = new AbortController()
  const request = withRequestTimeout(parent.signal, 1000, waitForAbort)
  parent.abort()
  assert.equal(await request, 'aborted')
})

test('request timeout aborts a stalled request', async () => {
  assert.equal(await withRequestTimeout(new AbortController().signal, 5, waitForAbort), 'aborted')
})

test('already cancelled queries receive an aborted signal immediately', async () => {
  const parent = new AbortController()
  parent.abort()
  assert.equal(await withRequestTimeout(parent.signal, 1000, waitForAbort), 'aborted')
})

test('successful requests remove cancellation listeners and preserve their result', async () => {
  const parent = new AbortController()
  let requestSignal
  const result = await withRequestTimeout(parent.signal, 5, async (signal) => {
    requestSignal = signal
    return 'ready'
  })
  parent.abort()
  await new Promise(resolve => setTimeout(resolve, 10))
  assert.equal(result, 'ready')
  assert.equal(requestSignal.aborted, false)
})
