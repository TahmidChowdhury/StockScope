'use client'

import { FormEvent, ReactNode, Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import AppShell from '@/components/AppShell'
import BacktestRiskPanel from '@/components/BacktestRiskPanel'
import { getAuthSession } from '@/lib/api'
import { useWorkspaceDraft } from '@/hooks/useWorkspaceDraft'
import { BacktestDraft, CongressDraft, PaperOrderDraft, PaperSetupDraft, applyBacktestSymbols, isBacktestDraft, isCongressDraft, isPaperOrderDraft, isPaperSetupDraft } from '@/lib/trading-draft'
import { loadSavedTradingRoute, savedTradingHref, tradingRoute } from '@/lib/trading-route'
import {
  CongressData,
  Costs,
  Portfolio,
  Result,
  Run,
  Summary,
  downloadTradingFile,
  tradingRequest,
  tradingDate,
  canCancelPaperOrder,
  backtestDates,
  backtestName,
  backtestSymbols,
} from '@/lib/trading'

const money = (value: number) =>
  value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  })
const percent = (value: number) => `${(value * 100).toFixed(2)}%`
const inputStyle = 'field-input disabled:opacity-40'
const buttonStyle =
  'button-primary disabled:opacity-40 disabled:cursor-not-allowed'
const panelStyle = 'surface min-w-0 p-4 sm:p-6'
const emptyCongress: CongressData = {
  records: [],
  total: 0,
  offset: 0,
  members: [],
  last_import: null,
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm text-white/65">
      {label}
      {children}
    </label>
  )
}
function DraftControls({ draft, label, disabled }: {
  draft: { ready: boolean; status: string; message: string | null; reset: () => void }
  label: string; disabled: boolean
}) {
  const state = draft.message || ({ saved: 'Saved in this browser.', empty: 'No saved draft.', 'memory-only': 'Kept for this session.', loading: 'Restoring draft…' }[draft.status] || 'Draft storage is unavailable.')
  return <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-xs text-slate-500">
    <p role="status">{label} · {state}</p>
    <button type="button" className="text-slate-400 underline underline-offset-4 disabled:opacity-40" disabled={disabled || !draft.ready || draft.status === 'empty'} onClick={draft.reset}>Clear draft</button>
  </div>
}
function CostFields({
  costs,
  setCosts,
}: {
  costs: Costs
  setCosts: (c: Costs) => void
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Field label="Slippage per side (bps)">
        <input
          className={inputStyle}
          type="number"
          min="0"
          max="500"
          step="0.1"
          required
          value={costs.slippage_bps}
          onChange={(e) =>
            setCosts({ ...costs, slippage_bps: +e.target.value })
          }
        />
      </Field>
      <Field label="Full bid–ask spread (bps)">
        <input
          className={inputStyle}
          type="number"
          min="0"
          max="500"
          step="0.1"
          required
          value={costs.spread_bps}
          onChange={(e) => setCosts({ ...costs, spread_bps: +e.target.value })}
        />
      </Field>
      <Field label="Commission per order ($)">
        <input
          className={inputStyle}
          type="number"
          min="0"
          max="100"
          step="0.01"
          required
          value={costs.commission}
          onChange={(e) => setCosts({ ...costs, commission: +e.target.value })}
        />
      </Field>
    </div>
  )
}

function Results({
  result,
  benchmark,
  riskRunId,
}: {
  result: Result
  benchmark: string
  riskRunId?: string
}) {
  const m = result.metrics
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-3">
        {[
          ['Ending equity', money(m.ending_equity)],
          ['Return after modeled costs', percent(m.total_return)],
          [`${benchmark} return after costs`, percent(m.benchmark_return)],
          [
            'Excess return',
            `${(m.excess_return * 100).toFixed(2)} percentage points`,
          ],
          ['Maximum drawdown', percent(m.max_drawdown)],
          ['Trading costs', money(m.total_costs)],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-xl border border-white/10 bg-slate-900/50 p-4"
          >
            <div className="text-xs text-white/50">{label}</div>
            <div className="mt-2 text-lg font-semibold sm:text-xl">{value}</div>
          </div>
        ))}
      </div>
      {riskRunId && (
        <BacktestRiskPanel runId={riskRunId} benchmark={benchmark} />
      )}
      <div className={panelStyle}>
        <h3 className="mb-1 font-semibold">Portfolio vs. {benchmark}</h3>
        <p className="mb-4 text-xs text-white/50">
          Through {result.as_of} · Both start with the same cash · Daily closing
          equity, including cash dividends
        </p>
        <div
          className="h-72 w-full"
          role="img"
          aria-label={`Daily portfolio and ${benchmark} equity comparison`}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={result.curve} margin={{ left: 10, right: 15 }}>
              <CartesianGrid stroke="#ffffff12" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                minTickGap={50}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                width={65}
                tickFormatter={(v) => `$${Number(v).toLocaleString()}`}
                domain={['auto', 'auto']}
              />
              <Tooltip
                contentStyle={{
                  background: '#0f172a',
                  borderColor: '#475569',
                  color: 'white',
                }}
                formatter={(v) => money(Number(v))}
              />
              <Legend />
              <Line
                isAnimationActive={false}
                type="linear"
                dataKey="equity"
                name="Paper strategy"
                stroke="#c084fc"
                dot={false}
                strokeWidth={2}
              />
              <Line
                isAnimationActive={false}
                type="linear"
                dataKey="benchmark"
                name={benchmark}
                stroke="#38bdf8"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-3 text-xs text-white/50">
          Cash {money(result.cash)} · Cash dividends {money(m.dividends)} ·
          Realized trading P&amp;L {money(m.realized_pnl)} · Benchmark costs{' '}
          {money(m.benchmark_costs)}
          {m.cagr !== null ? ` · Annualized return ${percent(m.cagr)}` : ''}
        </p>
      </div>
      {result.positions.length > 0 && (
        <div className={panelStyle}>
          <h3 className="mb-3 font-semibold">Open positions</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-white/45">
                <tr>
                  {[
                    'Symbol',
                    'Shares',
                    'Cost basis',
                    'Market value',
                    'Unrealized P&L',
                  ].map((v) => (
                    <th className="p-2" key={v}>
                      {v}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.positions.map((p) => (
                  <tr className="border-t border-white/10" key={p.symbol}>
                    <td className="p-2 font-mono">{p.symbol}</td>
                    <td className="p-2">{p.shares.toFixed(6)}</td>
                    <td className="p-2">{money(p.cost_basis)}</td>
                    <td className="p-2">{money(p.market_value)}</td>
                    <td className="p-2">{money(p.unrealized_pnl)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <div className={panelStyle}>
        <h3 className="mb-3 font-semibold">
          Execution ledger · {result.fills.length} fills
        </h3>
        {result.fills.length ? (
          <div className="max-h-96 overflow-auto">
            <table className="w-full whitespace-nowrap text-left text-sm">
              <thead className="text-white/45">
                <tr>
                  {[
                    'Signal',
                    'Filled',
                    'Symbol',
                    'Side',
                    'Shares',
                    'Fill price',
                    'Costs',
                    'Realized P&L',
                  ].map((v) => (
                    <th className="p-2" key={v}>
                      {v}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.fills.map((f, i) => (
                  <tr className="border-t border-white/10" key={i}>
                    <td className="p-2">{f.signal_date}</td>
                    <td className="p-2">{f.execution_date}</td>
                    <td className="p-2 font-mono">
                      {f.source_url ? (
                        <a
                          className="text-purple-300 underline"
                          href={f.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {f.symbol}
                        </a>
                      ) : (
                        f.symbol
                      )}
                    </td>
                    <td className="p-2">{f.side}</td>
                    <td className="p-2">{f.shares.toFixed(6)}</td>
                    <td className="p-2">{money(f.price)}</td>
                    <td className="p-2">{money(f.cost)}</td>
                    <td className="p-2">
                      {f.realized_pnl === null ? '—' : money(f.realized_pnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-white/50">
            No executed trades in this period.
          </p>
        )}
      </div>
      {(result.rejected.length > 0 ||
        result.pending.length > 0 ||
        (result.exclusions?.length || 0) > 0) && (
        <div className={panelStyle}>
          <h3 className="mb-3 font-semibold">Unexecuted signals</h3>
          <ul className="max-h-64 space-y-2 overflow-y-auto text-sm text-amber-200/80">
            {result.rejected.map((r, i) => (
              <li key={`r-${i}`}>
                {r.execution_date}: {r.side} {r.symbol} — {r.reason}
              </li>
            ))}
            {result.pending.map((r, i) => (
              <li key={`p-${i}`}>
                {r.signal_date}: {r.side} {r.symbol} — awaiting an eligible
                completed session
              </li>
            ))}
            {result.exclusions?.map((r, i) => (
              <li key={`e-${i}`}>
                {r.disclosure_id} — {r.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
      <details className={panelStyle}>
        <summary className="cursor-pointer text-sm font-semibold">
          Execution assumptions and limitations
        </summary>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-white/60">
          {result.assumptions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </details>
    </div>
  )
}

export default function TradingPage() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-[#101218]" />}>
      <TradingWorkspace />
    </Suspense>
  )
}

function TradingWorkspace() {
  const search = useSearchParams()
  const pathname = usePathname()
  const symbolsQuery = search.get('symbols')
  const handoffQuery = search.get('handoff')
  const router = useRouter()
  const route = tradingRoute(pathname, search.get('tab'))
  const tab = route.tab
  const setTab = (value: string) => {
    const params = new URLSearchParams(search.toString())
    params.set('tab', value)
    router.push(`/trading?${params}`, { scroll: false })
  }
  const [portfolios, setPortfolios] = useState<Summary[]>([])
  const [runs, setRuns] = useState<Summary[]>([])
  const [savedPortfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [savedRun, setRun] = useState<Run | null>(null)
  const portfolio = route.saved?.kind === 'portfolio' && savedPortfolio?.id === route.saved.id ? savedPortfolio : null
  const run = route.saved?.kind === 'backtest' && savedRun?.id === route.saved.id ? savedRun : null
  const [selectionError, setSelectionError] = useState('')
  const [selectionLoading, setSelectionLoading] = useState(false)
  const [selectionRetry, setSelectionRetry] = useState(0)
  const selectedKind = route.saved?.kind
  const selectedId = route.saved?.id
  useEffect(() => {
    setRun(null)
    setPortfolio(null)
    setSelectionError('')
    const selected = tradingRoute(pathname, null).saved
    if (!selected) { setSelectionLoading(false); return }
    setSelectionLoading(true)
    return loadSavedTradingRoute(selected, (path) => tradingRequest<Run | Portfolio>(path), (record) => {
      if (selected.kind === 'backtest') setRun(record as Run)
      else setPortfolio(record as Portfolio)
      setSelectionLoading(false)
    }, (reason) => {
      setSelectionError(/not found/i.test(reason.message)
        ? 'This saved research was not found (404). Choose another saved item below.'
        : `Saved research could not be opened: ${reason.message}`)
      setSelectionLoading(false)
    })
  }, [pathname, selectedKind, selectedId, selectionRetry])
  const [renaming, setRenaming] = useState(false)
  const [renameLabel, setRenameLabel] = useState('')
  useEffect(() => setRenaming(false), [run?.id])
  const [congress, setCongress] = useState<CongressData>(emptyCongress)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const [memberFilter, setMemberFilter] = useState('')
  const [dateRange] = useState(() => {
    const marketToday = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/New_York',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(new Date())
    const end = new Date(`${marketToday}T12:00:00Z`)
    end.setUTCDate(end.getUTCDate() - 1)
    const start = new Date(end)
    start.setUTCFullYear(start.getUTCFullYear() - 1)
    return {
      start: start.toISOString().slice(0, 10),
      end: end.toISOString().slice(0, 10),
    }
  })
  const paperDraft = useWorkspaceDraft<PaperSetupDraft>('trading:paper-setup', {
    name: 'My paper portfolio', capital: 10000, benchmark: 'SPY',
    costs: { slippage_bps: 5, spread_bps: 2, commission: 0 },
  }, isPaperSetupDraft)
  const backtestDraft = useWorkspaceDraft<BacktestDraft>('trading:backtest', {
    capital: 10000, benchmark: 'SPY', costs: { slippage_bps: 5, spread_bps: 2, commission: 0 },
    strategy: 'buy_hold', backtestLabel: '', symbols: 'AAPL, MSFT', symbolsContext: '', start: dateRange.start, end: dateRange.end,
    fast: 20, slow: 50, member: '', tradeFraction: 10, maxWeight: 25, delay: 0,
  }, isBacktestDraft)
  const [initialOrder] = useState<PaperOrderDraft>(() => ({ orderSymbol: 'AAPL', orderSide: 'buy', budget: 1000, thesis: '', clientOrderId: crypto.randomUUID() }))
  const orderDraft = useWorkspaceDraft<PaperOrderDraft>(`trading:order:${selectedKind === 'portfolio' ? selectedId : 'unselected'}`, initialOrder, isPaperOrderDraft)
  const congressDraft = useWorkspaceDraft<CongressDraft>('trading:congress-import', { csv: '' }, isCongressDraft)
  const { name } = paperDraft.value
  const fundingDraft = tab === 'paper' ? paperDraft : backtestDraft
  const { capital, benchmark, costs } = fundingDraft.value
  const { strategy, backtestLabel, symbols, start, end, fast, slow, member, tradeFraction, maxWeight, delay } = backtestDraft.value
  const { orderSymbol, orderSide, budget, thesis, clientOrderId } = orderDraft.value
  const { csv } = congressDraft.value
  function setBacktestField<K extends keyof BacktestDraft>(key: K, value: BacktestDraft[K]) {
    backtestDraft.setValue((current) => Object.is(current[key], value) ? current : ({ ...current, [key]: value }))
  }
  const setName = (name: string) => paperDraft.setValue((current) => ({ ...current, name }))
  const setCapital = (capital: number) => tab === 'paper'
    ? paperDraft.setValue((current) => ({ ...current, capital }))
    : setBacktestField('capital', capital)
  const setBenchmark = (benchmark: string) => tab === 'paper'
    ? paperDraft.setValue((current) => ({ ...current, benchmark }))
    : setBacktestField('benchmark', benchmark)
  const setCosts = (costs: Costs) => tab === 'paper'
    ? paperDraft.setValue((current) => ({ ...current, costs }))
    : setBacktestField('costs', costs)
  const setStrategy = (strategy: string) => setBacktestField('strategy', strategy)
  const setSymbols = (symbols: string) => setBacktestField('symbols', symbols)
  const setBacktestLabel = (value: string) => setBacktestField('backtestLabel', value)
  const setStart = (value: string) => setBacktestField('start', value)
  const setEnd = (value: string) => setBacktestField('end', value)
  const setFast = (value: number) => setBacktestField('fast', value)
  const setSlow = (value: number) => setBacktestField('slow', value)
  const setMember = (value: string) => setBacktestField('member', value)
  const setTradeFraction = (value: number) => setBacktestField('tradeFraction', value)
  const setMaxWeight = (value: number) => setBacktestField('maxWeight', value)
  const setDelay = (value: number) => setBacktestField('delay', value)
  const setOrderSymbol = (orderSymbol: string) => orderDraft.setValue((current) => ({ ...current, orderSymbol }))
  const setOrderSide = (orderSide: string) => orderDraft.setValue((current) => ({ ...current, orderSide }))
  const setBudget = (budget: number) => orderDraft.setValue((current) => ({ ...current, budget }))
  const setThesis = (thesis: string) => orderDraft.setValue((current) => ({ ...current, thesis }))
  const setCsv = (csv: string) => congressDraft.setValue({ csv })
  const draftsReady = paperDraft.ready && backtestDraft.ready && orderDraft.ready && congressDraft.ready
  const backtestReady = backtestDraft.ready
  const updateBacktestDraft = backtestDraft.setValue
  useEffect(() => {
    if (!backtestReady) return
    const passedSymbols = backtestSymbols(symbolsQuery)
    if (!passedSymbols) return
    updateBacktestDraft((current) => applyBacktestSymbols(current, passedSymbols, handoffQuery))
  }, [symbolsQuery, handoffQuery, backtestReady, updateBacktestDraft])

  async function reloadLists() {
    const [p, r, c] = await Promise.all([
      tradingRequest<Summary[]>('/portfolios'),
      tradingRequest<Summary[]>('/backtests'),
      tradingRequest<CongressData>('/congress'),
    ])
    setPortfolios(p)
    setRuns(r)
    setCongress(c)
    setMemberFilter('')
  }
  useEffect(() => {
    setIsAdmin(getAuthSession()?.role === 'admin')
    reloadLists()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  async function act(operation: () => Promise<void>) {
    setError('')
    setNotice('')
    setBusy(true)
    try {
      await operation()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setBusy(false)
    }
  }
  const prevent = (event: FormEvent, operation: () => Promise<void>) => {
    event.preventDefault()
    void act(operation)
  }
  const formDisabled = busy || loading || !isAdmin || !draftsReady

  return (
    <AppShell>
      <div className="space-y-6">
        <header>
          <p className="eyebrow">Strategy workspace</p>
          <h1 className="page-title mt-2">Paper portfolios & tests</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-white/55">
            Paper portfolios and daily historical tests with explicit costs and
            a benchmark. All portfolios and research are shared across this app.
            No real orders are placed.
          </p>
        </header>
        {!isAdmin && !loading && (
          <p className="rounded-lg border border-blue-400/20 bg-blue-400/10 p-3 text-sm text-blue-200">
            Read-only access. Sign in as admin to create portfolios, run tests,
            or import disclosures.
          </p>
        )}
        <nav
          className="flex gap-5 overflow-x-auto border-b border-white/10"
          aria-label="Trading workspace"
        >
          {(
            [
              ['paper', 'Paper portfolio'],
              ['backtest', 'Backtesting'],
              ['congress', 'Congress disclosures'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              disabled={busy}
              className={`whitespace-nowrap border-b-2 px-1 pb-3 pt-2 text-sm ${tab === id ? 'border-violet-400 text-violet-200' : 'border-transparent text-slate-500 hover:text-slate-200'}`}
              onClick={() => setTab(id)}
              aria-pressed={tab === id}
            >
              {label}
            </button>
          ))}
        </nav>
        {(route.error || selectionError) && (
          <div role="alert" className="rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-200">
            <p>{route.error || selectionError}</p>
            <div className="mt-3 flex flex-wrap gap-4 text-xs">
              <Link href={`/trading?tab=${tab}`} className="underline underline-offset-4">Open workspace</Link>
              {route.saved && <button disabled={busy} onClick={() => setSelectionRetry((current) => current + 1)} className="underline underline-offset-4">Retry saved record</button>}
            </div>
          </div>
        )}
        {selectionLoading && <p role="status" className="text-sm text-white/50">Opening saved {selectedKind === 'backtest' ? 'experiment' : 'portfolio'}…</p>}
        {error && (
          <div
            role="alert"
            className="rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-200"
          >
            <p>{error}</p>
            <button
              disabled={busy}
              className="mt-3 text-xs underline underline-offset-4"
              onClick={() => void act(reloadLists)}
            >
              Reload saved workspace
            </button>
          </div>
        )}
        {notice && (
          <p
            role="status"
            className="rounded-lg border border-green-400/20 bg-green-400/10 p-3 text-sm text-green-200"
          >
            {notice}
          </p>
        )}
        {loading && (
          <p role="status" className="text-sm text-white/50">
            Loading saved research…
          </p>
        )}
        {busy && (
          <p role="status" className="text-sm text-purple-200">
            Working… Price collection may take a minute. Keep this page open.
          </p>
        )}

        {tab === 'paper' && (
          <>
            <div className="grid gap-5 xl:grid-cols-2">
              <form
                className={panelStyle}
                onSubmit={(e) =>
                  prevent(e, async () => {
                    const p = await tradingRequest<Portfolio>('/portfolios', {
                      name,
                      initial_cash: capital,
                      benchmark,
                      costs,
                    })
                    setPortfolio(p)
                    router.push(savedTradingHref('portfolio', p.id), { scroll: false })
                    await reloadLists()
                    setNotice(
                      'Paper portfolio created. Submit a thesis and queue your first order.',
                    )
                  })
                }
              >
                <h2 className="mb-4 text-lg font-semibold">
                  Create a paper portfolio
                </h2>
                <DraftControls draft={paperDraft} label="Portfolio setup draft" disabled={busy} />
                <fieldset disabled={formDisabled} className="space-y-4">
                  <Field label="Portfolio name">
                    <input
                      className={inputStyle}
                      required
                      maxLength={80}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Starting cash ($)">
                      <input
                        className={inputStyle}
                        type="number"
                        min="100"
                        max="100000000"
                        required
                        value={capital}
                        onChange={(e) => setCapital(+e.target.value)}
                      />
                    </Field>
                    <Field label="Benchmark">
                      <input
                        className={inputStyle}
                        required
                        maxLength={10}
                        value={benchmark}
                        onChange={(e) =>
                          setBenchmark(e.target.value.toUpperCase())
                        }
                      />
                    </Field>
                  </div>
                  <CostFields costs={costs} setCosts={setCosts} />
                  <button className={buttonStyle}>Create portfolio</button>
                </fieldset>
              </form>
              <div className={panelStyle}>
                <h2 className="mb-4 text-lg font-semibold">Saved portfolios</h2>
                <div className="max-h-96 space-y-2 overflow-y-auto">
                  {portfolios.length === 0 ? (
                    <p className="text-sm text-white/50">
                      No paper portfolios yet.
                    </p>
                  ) : (
                    portfolios.map((p) => (
                      <Link
                        key={p.id}
                        href={savedTradingHref('portfolio', p.id)}
                        aria-current={portfolio?.id === p.id ? 'page' : undefined}
                        aria-disabled={busy || undefined}
                        onClick={(event) => { if (busy) event.preventDefault() }}
                        className={`block w-full rounded-lg border p-3 text-left ${portfolio?.id === p.id ? 'border-purple-400 bg-purple-500/10' : 'border-white/10 hover:bg-white/5'}`}
                      >
                        <span className="font-medium">{p.name}</span>
                        <span className="mt-1 block text-xs text-white/50">
                          Created {tradingDate(p.created_at)} ·{' '}
                          {p.metrics
                            ? `${percent(p.metrics.total_return)} through ${p.as_of}`
                            : 'Awaiting completed sessions'}
                        </span>
                      </Link>
                    ))
                  )}
                </div>
              </div>
            </div>
            {portfolio && (
              <>
                <section className={panelStyle}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h2 className="text-xl font-semibold">
                        {portfolio.name}
                      </h2>
                      <p className="mt-1 text-xs text-white/50">
                        Starting cash {money(portfolio.initial_cash)} ·
                        Benchmark {portfolio.benchmark} ·{' '}
                        {portfolio.costs.slippage_bps} bps slippage + half of{' '}
                        {portfolio.costs.spread_bps} bps spread +{' '}
                        {money(portfolio.costs.commission)} commission per fill
                      </p>
                    </div>
                    <button
                      disabled={formDisabled}
                      className={buttonStyle}
                      onClick={() =>
                        void act(async () => {
                          setPortfolio(
                            await tradingRequest<Portfolio>(
                              `/portfolios/${portfolio.id}/refresh`,
                              {},
                            ),
                          )
                          await reloadLists()
                          setNotice(
                            'Evaluated orders using completed daily sessions. Today’s session is excluded.',
                          )
                        })
                      }
                    >
                      Refresh completed sessions
                    </button>
                  </div>
                  <p className="my-4 text-sm leading-6 text-white/55">
                    Queue a buy by cash budget, or sell the entire position.
                    Orders become eligible at an open after the submission date
                    in New York and appear once that daily session has
                    completed. Refresh explicitly to evaluate them. Cash and
                    position checks happen at execution.
                  </p>
                  <form
                    onSubmit={(e) =>
                      prevent(e, async () => {
                        setPortfolio(
                          await tradingRequest<Portfolio>(
                            `/portfolios/${portfolio.id}/orders`,
                            {
                              client_order_id: clientOrderId,
                              symbol: orderSymbol,
                              side: orderSide,
                              budget,
                              thesis,
                            },
                          ),
                        )
                        orderDraft.setValue((current) => ({ ...current, thesis: '', clientOrderId: crypto.randomUUID() }), orderDraft.generation)
                        setNotice(
                          'Paper order queued. It will be evaluated after the next eligible daily session completes.',
                        )
                      })
                    }
                  >
                    <DraftControls draft={orderDraft} label="Order draft for this portfolio" disabled={busy} />
                    <fieldset disabled={formDisabled} className="space-y-4">
                      <div className="grid gap-3 sm:grid-cols-3">
                        <Field label="Symbol">
                          <input
                            className={inputStyle}
                            required
                            maxLength={10}
                            value={orderSymbol}
                            onChange={(e) =>
                              setOrderSymbol(e.target.value.toUpperCase())
                            }
                          />
                        </Field>
                        <Field label="Action">
                          <select
                            className={inputStyle}
                            value={orderSide}
                            onChange={(e) => setOrderSide(e.target.value)}
                          >
                            <option value="buy">Buy by cash budget</option>
                            <option value="sell">Sell entire position</option>
                          </select>
                        </Field>
                        <Field label="Buy budget, including costs ($)">
                          <input
                            className={inputStyle}
                            disabled={orderSide === 'sell'}
                            type="number"
                            min="1"
                            max="100000000"
                            required
                            step="0.01"
                            value={budget}
                            onChange={(e) => setBudget(+e.target.value)}
                          />
                        </Field>
                      </div>
                      <Field label="Thesis / reason, recorded before execution">
                        <textarea
                          className={inputStyle}
                          required
                          maxLength={2000}
                          rows={2}
                          value={thesis}
                          onChange={(e) => setThesis(e.target.value)}
                          placeholder="Why this trade? What would change your view?"
                        />
                      </Field>
                      <button className={buttonStyle}>Queue paper order</button>
                    </fieldset>
                  </form>
                </section>
                <section className={panelStyle}>
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="font-semibold">Trade journal</h3>
                    <button
                      disabled={busy}
                      className="text-xs text-purple-300 underline"
                      onClick={() =>
                        void act(async () =>
                          downloadTradingFile(
                            `/portfolios/${portfolio.id}/export`,
                            `${portfolio.id}.json`,
                          ),
                        )
                      }
                    >
                      Export ledger and observations
                    </button>
                  </div>
                  {portfolio.orders.length === 0 ? (
                    <p className="text-sm text-white/50">
                      Your submitted orders and reasons will appear here.
                    </p>
                  ) : (
                    <div className="max-h-80 space-y-3 overflow-y-auto">
                      {portfolio.orders.map((o) => {
                        const filled = portfolio.result?.fills.some(
                          (f) => f.id === o.id,
                        )
                        const rejected = portfolio.result?.rejected.find(
                          (r) => r.id === o.id,
                        )
                        return (
                          <div
                            key={o.id}
                            className="rounded-lg border border-white/10 p-3"
                          >
                            <div className="flex flex-wrap justify-between gap-2 text-sm">
                              <span className="font-medium">
                                {o.side.toUpperCase()} {o.symbol}
                                {o.side === 'buy'
                                  ? ` · up to ${money(o.budget)}`
                                  : ''}
                              </span>
                              <span className="text-white/50">
                                {o.signal_date} ·{' '}
                                {o.cancelled_at
                                  ? 'Cancelled'
                                  : filled
                                    ? 'Filled'
                                    : rejected
                                      ? 'Rejected'
                                      : 'Queued'}
                              </span>
                            </div>
                            <p className="mt-2 whitespace-pre-wrap text-sm text-white/65">
                              {o.thesis}
                            </p>
                            {rejected && (
                              <p className="mt-2 text-xs text-amber-200">
                                {rejected.reason}
                              </p>
                            )}
                            {!filled &&
                              !rejected &&
                              !o.cancelled_at &&
                              !canCancelPaperOrder(o) && (
                                <p className="mt-2 text-xs leading-5 text-slate-500">
                                  Past the same-day cancellation window. Refresh
                                  completed sessions to evaluate this order.
                                </p>
                              )}
                            {!filled &&
                              !rejected &&
                              canCancelPaperOrder(o) &&
                              isAdmin && (
                                <button
                                  className="mt-2 text-xs text-purple-300 underline disabled:opacity-40"
                                  disabled={busy}
                                  onClick={() =>
                                    void act(async () =>
                                      setPortfolio(
                                        await tradingRequest<Portfolio>(
                                          `/portfolios/${portfolio.id}/orders/${o.id}/cancel`,
                                          {},
                                        ),
                                      ),
                                    )
                                  }
                                >
                                  Cancel same-day order
                                </button>
                              )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </section>
                {portfolio.result ? (
                  <Results
                    result={portfolio.result}
                    benchmark={portfolio.benchmark}
                  />
                ) : (
                  <p className="rounded-xl border border-dashed border-white/15 p-6 text-sm text-white/50">
                    No completed-session valuation yet. Your starting cash is{' '}
                    {money(portfolio.initial_cash)}. Performance begins on the
                    first benchmark session after portfolio creation.
                  </p>
                )}
              </>
            )}
          </>
        )}

        {tab === 'backtest' && (
          <>
            <form
              className={panelStyle}
              onSubmit={(e) => {
                e.preventDefault()
                let dates: { start: string; end: string }
                try {
                  dates = backtestDates(new FormData(e.currentTarget))
                } catch (reason) {
                  setError(
                    reason instanceof Error
                      ? reason.message
                      : 'Check the experiment dates.',
                  )
                  return
                }
                setStart(dates.start)
                setEnd(dates.end)
                void act(async () => {
                  const r = await tradingRequest<Run>('/backtests', {
                    name: backtestLabel.trim() || null,
                    strategy,
                    ...dates,
                    initial_cash: capital,
                    benchmark,
                    costs,
                    symbols: symbols
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean),
                    fast_window: fast,
                    slow_window: slow,
                    member,
                    trade_fraction: tradeFraction / 100,
                    max_weight: maxWeight / 100,
                    disclosure_delay_days: delay,
                  })
                  setRun(r)
                  router.push(savedTradingHref('backtest', r.id), { scroll: false })
                  await reloadLists()
                  setNotice(
                    'Backtest saved with its price observations and execution assumptions.',
                  )
                })
              }}
            >
              <h2 className="mb-2 text-lg font-semibold">
                Run a historical experiment
              </h2>
              <p className="mb-5 text-sm text-white/55">
                Choose rules before looking at results. Reserve a later, unseen
                period for validation. Results are historical simulations, not a
                forecast.
              </p>
              <DraftControls draft={backtestDraft} label="Experiment draft" disabled={busy} />
              {symbolsQuery !== null && !backtestSymbols(symbolsQuery) && (
                <p role="alert" className="mb-4 text-sm text-amber-200">
                  The linked symbols could not be used. Enter 1–20 valid stock
                  symbols below.
                </p>
              )}
              <fieldset disabled={formDisabled} className="space-y-4">
                <Field label="Experiment name (optional)">
                  <input
                    className={inputStyle}
                    maxLength={80}
                    value={backtestLabel}
                    placeholder="e.g. AAPL + MSFT · one-year baseline"
                    onChange={(e) => setBacktestLabel(e.target.value)}
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-3">
                  <Field label="Strategy">
                    <select
                      className={inputStyle}
                      value={strategy}
                      onChange={(e) => {
                        setStrategy(e.target.value)
                        if (e.target.value === 'sma')
                          setSymbols(backtestSymbols(symbols)?.[0] || 'AAPL')
                      }}
                    >
                      <option value="buy_hold">
                        Buy and hold · equal starting budgets
                      </option>
                      <option value="sma">Moving average · one stock</option>
                      <option value="congress">
                        Copy Congress disclosures
                      </option>
                    </select>
                  </Field>
                  <Field label="Start date">
                    <input
                      className={inputStyle}
                      type="date"
                      required
                      max={dateRange.end}
                      name="start"
                      value={start}
                      onInput={(e) => setStart(e.currentTarget.value)}
                      onBlur={(e) => setStart(e.currentTarget.value)}
                      onChange={(e) => setStart(e.target.value)}
                    />
                  </Field>
                  <Field label="End date (before today)">
                    <input
                      className={inputStyle}
                      type="date"
                      required
                      min={start}
                      max={dateRange.end}
                      name="end"
                      value={end}
                      onInput={(e) => setEnd(e.currentTarget.value)}
                      onBlur={(e) => setEnd(e.currentTarget.value)}
                      onChange={(e) => setEnd(e.target.value)}
                    />
                  </Field>
                </div>
                {strategy === 'congress' ? (
                  <>
                    <Field label="Member with imported disclosures">
                      <select
                        className={inputStyle}
                        required
                        value={member}
                        onChange={(e) => setMember(e.target.value)}
                      >
                        <option value="">Select a member</option>
                        {congress.members.map((m) => (
                          <option key={m}>{m}</option>
                        ))}
                      </select>
                    </Field>
                    <div className="grid gap-3 sm:grid-cols-3">
                      <Field label="Budget per buy (% of initial cash)">
                        <input
                          className={inputStyle}
                          type="number"
                          min="0.1"
                          max="100"
                          step="0.1"
                          required
                          value={tradeFraction}
                          onChange={(e) => setTradeFraction(+e.target.value)}
                        />
                      </Field>
                      <Field label="Maximum symbol weight at purchase (%)">
                        <input
                          className={inputStyle}
                          type="number"
                          min="0.1"
                          max="100"
                          step="0.1"
                          required
                          value={maxWeight}
                          onChange={(e) => setMaxWeight(+e.target.value)}
                        />
                      </Field>
                      <Field label="Extra disclosure delay (calendar days)">
                        <input
                          className={inputStyle}
                          type="number"
                          min="0"
                          max="90"
                          required
                          value={delay}
                          onChange={(e) => setDelay(+e.target.value)}
                        />
                      </Field>
                    </div>
                    <p className="text-xs leading-5 text-amber-100/70">
                      Uses disclosures first public inside the selected window.
                      Buys use your fixed budget; sales close the copied symbol.
                      Owners are pooled. Options are excluded. This tests a
                      disclosure-following rule, not the member’s actual
                      portfolio return.
                    </p>
                  </>
                ) : (
                  <Field
                    label={
                      strategy === 'sma'
                        ? 'Stock symbol'
                        : 'Stock symbols (comma-separated, maximum 20)'
                    }
                  >
                    <input
                      className={inputStyle}
                      required
                      value={symbols}
                      onChange={(e) => setSymbols(e.target.value.toUpperCase())}
                    />
                  </Field>
                )}
                {strategy === 'sma' && (
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Fast average (sessions)">
                      <input
                        className={inputStyle}
                        required
                        type="number"
                        min="2"
                        max="100"
                        value={fast}
                        onChange={(e) => setFast(+e.target.value)}
                      />
                    </Field>
                    <Field label="Slow average (sessions)">
                      <input
                        className={inputStyle}
                        required
                        type="number"
                        min="3"
                        max="250"
                        value={slow}
                        onChange={(e) => setSlow(+e.target.value)}
                      />
                    </Field>
                  </div>
                )}
                {strategy === 'sma' && (
                  <p className="text-xs text-white/50">
                    Hold when the prior session’s fast average exceeds the slow
                    average; otherwise hold cash. Signals use adjusted closing
                    prices, and fills use the next open.
                  </p>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Initial cash ($)">
                    <input
                      className={inputStyle}
                      required
                      type="number"
                      min="100"
                      max="100000000"
                      value={capital}
                      onChange={(e) => setCapital(+e.target.value)}
                    />
                  </Field>
                  <Field label="Benchmark">
                    <input
                      className={inputStyle}
                      required
                      maxLength={10}
                      value={benchmark}
                      onChange={(e) =>
                        setBenchmark(e.target.value.toUpperCase())
                      }
                    />
                  </Field>
                </div>
                <CostFields costs={costs} setCosts={setCosts} />
                <p className="text-xs text-white/45">
                  1 basis point = 0.01%. Half of the full spread is charged per
                  side. Every filled order incurs the commission.
                </p>
                <button className={buttonStyle}>Run and save backtest</button>
              </fieldset>
            </form>
            {!loading && !error && runs.length === 0 && (
              <div className={panelStyle}>
                <h3 className="text-sm font-medium">
                  No saved experiments yet
                </h3>
                <p className="mt-2 text-xs leading-6 text-slate-400">
                  Run a historical experiment to save its results, assumptions,
                  and price observations here.
                </p>
              </div>
            )}
            {runs.length > 0 && (
              <div className={panelStyle}>
                <h3 className="mb-3 font-semibold">Saved experiments</h3>
                <div className="flex max-h-52 flex-wrap gap-2 overflow-y-auto">
                  {runs.map((r) => (
                    <Link
                      key={r.id}
                      href={savedTradingHref('backtest', r.id)}
                      aria-current={run?.id === r.id ? 'page' : undefined}
                      aria-disabled={busy || undefined}
                      onClick={(event) => { if (busy) event.preventDefault() }}
                      className={`rounded-lg border p-3 text-left text-xs ${run?.id === r.id ? 'border-purple-400 bg-purple-500/10' : 'border-white/10 hover:bg-white/5'}`}
                    >
                      {backtestName(r)}
                      <span className="mt-1 block text-white/50">
                        {r.start} → {r.end}
                        {r.metrics
                          ? ` · ${percent(r.metrics.total_return)}`
                          : ''}
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
            {run && (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold">
                      {backtestName(run)}
                    </h2>
                    {isAdmin && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          setRenameLabel(backtestName(run))
                          setRenaming(true)
                        }}
                        className="mt-2 text-xs text-violet-300 underline underline-offset-4"
                      >
                        Rename experiment
                      </button>
                    )}
                    <p className="mt-1 text-xs text-white/50">
                      {run.start} → {run.end} · Saved{' '}
                      {tradingDate(run.created_at)} · {run.costs.slippage_bps}{' '}
                      bps slippage / {run.costs.spread_bps} bps full spread /{' '}
                      {money(run.costs.commission)} commission
                    </p>
                  </div>
                  <button
                    disabled={busy}
                    className={buttonStyle}
                    onClick={() =>
                      void act(async () =>
                        downloadTradingFile(
                          `/backtests/${run.id}/export`,
                          `${run.id}.json`,
                        ),
                      )
                    }
                  >
                    Export complete experiment
                  </button>
                </div>
                {renaming && (
                  <form
                    className={panelStyle}
                    onSubmit={(e) =>
                      prevent(e, async () => {
                        const renamed = await tradingRequest<Run>(
                          `/backtests/${run.id}/name`,
                          { name: renameLabel },
                        )
                        setRun(renamed)
                        setRuns((current) =>
                          current.map((saved) =>
                            saved.id === renamed.id
                              ? { ...saved, name: renamed.name }
                              : saved,
                          ),
                        )
                        setRenaming(false)
                        setNotice(
                          'Experiment renamed. Price observations and results are unchanged.',
                        )
                      })
                    }
                  >
                    <Field label="Saved experiment name">
                      <input
                        className={inputStyle}
                        value={renameLabel}
                        onChange={(e) => setRenameLabel(e.target.value)}
                        required
                        maxLength={80}
                        disabled={busy}
                      />
                    </Field>
                    <div className="mt-4 flex gap-3">
                      <button
                        disabled={busy || !renameLabel.trim()}
                        className={buttonStyle}
                      >
                        Save name
                      </button>
                      <button
                        type="button"
                        className="button-secondary"
                        disabled={busy}
                        onClick={() => setRenaming(false)}
                      >
                        Cancel rename
                      </button>
                    </div>
                  </form>
                )}
                <Results
                  result={run.result}
                  benchmark={run.benchmark}
                  riskRunId={run.id}
                />
              </>
            )}
          </>
        )}

        {tab === 'congress' && (
          <>
            <section className={panelStyle}>
              <h2 className="text-lg font-semibold">
                Congress disclosure evidence
              </h2>
              <p className="mt-3 text-sm leading-6 text-white/60">
                Import normalized transaction rows from public disclosures or a
                data provider. No live Congress feed is connected. Dates and
                classifications are supplied by the importer; verify public
                availability against the original evidence. Each disclosure ID
                must identify one transaction row. This version does not support
                amendments.
              </p>
              <div className="mt-4 flex flex-wrap gap-4 text-sm">
                <button
                  className="text-purple-300 underline"
                  onClick={() =>
                    void act(async () =>
                      downloadTradingFile(
                        '/congress/template',
                        'congress-template.csv',
                      ),
                    )
                  }
                >
                  Download CSV header template
                </button>
                <a
                  className="text-purple-300 underline"
                  href="https://disclosures-clerk.house.gov/FinancialDisclosure"
                  target="_blank"
                  rel="noreferrer"
                >
                  House disclosure portal ↗
                </a>
                <a
                  className="text-purple-300 underline"
                  href="https://efdsearch.senate.gov/search/"
                  target="_blank"
                  rel="noreferrer"
                >
                  Senate disclosure portal ↗
                </a>
              </div>
              <details className="mt-4 text-sm text-white/60">
                <summary className="cursor-pointer">
                  CSV field requirements
                </summary>
                <p className="mt-3 leading-6">
                  Required columns in order: disclosure_id, member, owner,
                  symbol, side, transaction_date, available_date, asset_type,
                  amount_range, source_url. Dates use YYYY-MM-DD. Side is buy or
                  sell. Asset type is stock, etf, option, or other. Use an HTTPS
                  evidence URL, the reported amount range, and the actual owner
                  (member, spouse, or dependent). Quote fields containing
                  commas. Identical reimports are skipped; conflicting IDs
                  reject the entire import.
                </p>
              </details>
              <form
                className="mt-5"
                onSubmit={(e) =>
                  prevent(e, async () => {
                    const result = await tradingRequest<{
                      inserted: number
                      duplicates: number
                    }>('/congress/import', { csv_text: csv })
                    await reloadLists()
                    congressDraft.setValue({ csv: '' }, congressDraft.generation)
                    setNotice(
                      `Imported ${result.inserted} disclosures; skipped ${result.duplicates} identical duplicates.`,
                    )
                  })
                }
              >
                <DraftControls draft={congressDraft} label="Disclosure import draft" disabled={busy} />
                <fieldset disabled={formDisabled} className="space-y-3">
                  <Field label="Choose a normalized CSV file">
                    <input
                      className={inputStyle}
                      type="file"
                      accept=".csv,text/csv"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (!file) return
                        if (file.size > 2000000) {
                          setError('CSV must be smaller than 2 MB')
                          return
                        }
                        void file
                          .text()
                          .then((csv) => congressDraft.setValue({ csv }, congressDraft.generation))
                          .catch(() => setError('Could not read CSV'))
                      }}
                    />
                  </Field>
                  <Field label="Or paste the CSV, including its header">
                    <textarea
                      rows={5}
                      className={`${inputStyle} font-mono text-xs`}
                      required
                      maxLength={2000000}
                      value={csv}
                      onChange={(e) => setCsv(e.target.value)}
                      placeholder="disclosure_id,member,owner,symbol,side,transaction_date,available_date,asset_type,amount_range,source_url"
                    />
                  </Field>
                  <button className={buttonStyle}>Validate and import</button>
                </fieldset>
              </form>
            </section>
            <section className={panelStyle}>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold">
                    Imported transactions · {congress.total}
                  </h3>
                  {congress.last_import && (
                    <p className="mt-1 text-xs text-white/50">
                      Last import{' '}
                      {tradingDate(congress.last_import.imported_at)}
                    </p>
                  )}
                </div>
                <label className="text-xs text-white/60">
                  Filter member
                  <select
                    disabled={busy}
                    className={inputStyle}
                    value={memberFilter}
                    onChange={(e) => {
                      const value = e.target.value
                      void act(async () => {
                        const data = await tradingRequest<CongressData>(
                          `/congress?member=${encodeURIComponent(value)}`,
                        )
                        setCongress(data)
                        setMemberFilter(value)
                      })
                    }}
                  >
                    <option value="">All members</option>
                    {congress.members.map((m) => (
                      <option key={m}>{m}</option>
                    ))}
                  </select>
                </label>
              </div>
              {congress.records.length === 0 ? (
                <p className="text-sm text-white/50">
                  No disclosures imported. Import source-backed records to test
                  a copying strategy.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full whitespace-nowrap text-left text-xs">
                    <thead className="text-white/45">
                      <tr>
                        {[
                          'Member / owner',
                          'Symbol',
                          'Action',
                          'Traded',
                          'Publicly available',
                          'Lag',
                          'Reported amount',
                          'Evidence',
                        ].map((v) => (
                          <th key={v} className="p-2">
                            {v}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {congress.records.map((r) => (
                        <tr
                          key={r.disclosure_id}
                          className="border-t border-white/10"
                        >
                          <td className="p-2">
                            {r.member}
                            <span className="block text-white/40">
                              {r.owner}
                            </span>
                          </td>
                          <td className="p-2 font-mono">
                            {r.symbol}
                            <span className="block text-white/40">
                              {r.asset_type}
                            </span>
                          </td>
                          <td className="p-2">{r.side}</td>
                          <td className="p-2">{r.transaction_date}</td>
                          <td className="p-2">{r.available_date}</td>
                          <td className="p-2">{r.lag_days} days</td>
                          <td className="p-2">{r.amount_range}</td>
                          <td className="p-2">
                            <a
                              className="text-purple-300 underline"
                              href={r.source_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Source ↗
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="mt-4 flex items-center justify-between text-xs text-white/50">
                <span>
                  {congress.total
                    ? `${congress.offset + 1}–${congress.offset + congress.records.length} of ${congress.total}`
                    : '0 records'}
                </span>
                <div className="flex gap-4">
                  {[
                    [-100, 'Previous'],
                    [100, 'Next'],
                  ].map(([delta, label]) => (
                    <button
                      key={label}
                      disabled={
                        busy ||
                        (Number(delta) < 0
                          ? congress.offset === 0
                          : congress.offset + congress.records.length >=
                            congress.total)
                      }
                      className="text-purple-300 disabled:opacity-30"
                      onClick={() =>
                        void act(async () =>
                          setCongress(
                            await tradingRequest<CongressData>(
                              `/congress?member=${encodeURIComponent(memberFilter)}&offset=${congress.offset + Number(delta)}`,
                            ),
                          ),
                        )
                      }
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  )
}
