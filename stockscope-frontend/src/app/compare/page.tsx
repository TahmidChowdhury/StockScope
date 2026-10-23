'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { ArrowUpRight, FlaskConical, Scale, X } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import AppShell from '@/components/AppShell'
import StockSearch from '@/components/StockSearch'
import { useCompare } from '@/hooks/useFundamentals'
import { useWatchlist } from '@/hooks/useWatchlist'
import { useWorkspaceDraft } from '@/hooks/useWorkspaceDraft'
import {
  amount,
  observed,
  parseSymbols,
  percent,
  ratio,
} from '@/lib/financial-format'
import type { FundamentalsTTM } from '@/types'
import { companyResearchHref, snapshotTime } from '@/lib/research-workflow'
import { completeComparison, draftFinancialRows, initialCompareDraft, isCompareDraft, replaceResearchUrl } from '@/lib/research-drafts'

const metrics: {
  key: keyof FundamentalsTTM
  label: string
  format: (v?: number | null) => string
}[] = [
  { key: 'revenue_ttm', label: 'Revenue · TTM', format: amount },
  { key: 'fcf_ttm', label: 'Free cash flow · TTM', format: amount },
  { key: 'fcf_margin_ttm', label: 'Free cash flow margin', format: percent },
  { key: 'operating_margin_ttm', label: 'Operating margin', format: percent },
  { key: 'revenue_growth_yoy', label: 'Revenue growth · YoY', format: percent },
  {
    key: 'fcf_growth_yoy',
    label: 'Free cash flow growth · YoY',
    format: percent,
  },
  { key: 'ebitda_growth_yoy', label: 'EBITDA growth · YoY', format: percent },
  { key: 'debt_to_cash', label: 'Debt / cash', format: ratio },
]
const chartStyle = {
  background: '#171a22',
  border: '1px solid #ffffff20',
  borderRadius: 8,
  color: '#e2e8f0',
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-[#101218]" />}>
      <CompareWorkspace />
    </Suspense>
  )
}

function CompareWorkspace() {
  const search = useSearchParams()
  const router = useRouter()
  const queryClient = useQueryClient()
  const draft = useWorkspaceDraft('compare', initialCompareDraft, isCompareDraft)
  const { value, setValue, ready, generation, reset } = draft
  const tickers = value.tickers
  const selection = tickers.join(',')
  const snapshot = value.snapshots.find((row) => row.tickers.join(',') === selection)
  const url = search.toString()
  const lastUrl = useRef<string | null>(null)
  const internalUrls = useRef(new Set<string>())
  const [appliedUrl, setAppliedUrl] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState('')
  const [handoffId] = useState(() => crypto.randomUUID())
  const [error, setError] = useState('')
  const compare = useCompare()
  const { data: stocks = [] } = useWatchlist()
  useEffect(() => {
    if (!ready || lastUrl.current === url) return
    lastUrl.current = url
    const params = new URLSearchParams(url)
    if (!internalUrls.current.delete(url) && params.has('tickers')) {
      const tickers = parseSymbols(params.get('tickers') || '').slice(0, 20)
      setValue((current) => ({ ...current, tickers }))
    }
    setAppliedUrl(url)
  }, [ready, url, setValue])
  useEffect(() => {
    const navigatingHistory = () => internalUrls.current.clear()
    window.addEventListener('popstate', navigatingHistory)
    return () => window.removeEventListener('popstate', navigatingHistory)
  }, [])
  const commit = (symbols: string[]) => {
    const params = new URLSearchParams(search.toString())
    params.set('tickers', symbols.join(','))
    setValue((current) => ({ ...current, tickers: symbols }))
    internalUrls.current = new Set([...internalUrls.current, params.toString()].slice(-50))
    replaceResearchUrl(window.history, '/compare', params)
    setError('')
  }
  const add = (symbol: string) => {
    symbol = parseSymbols(symbol)[0] || ''
    if (!symbol) return
    if (tickers.includes(symbol)) {
      setError(`${symbol} is already selected.`)
      return
    }
    if (tickers.length >= 20) {
      setError('Compare up to 20 companies at a time.')
      return
    }
    commit([...tickers, symbol])
  }
  const results = snapshot?.results
  const returnTo = `/compare?${new URLSearchParams({ tickers: selection })}`
  const missing = results
    ? tickers.filter(
        (ticker) => !results.some((company) => company.ticker === ticker),
      )
    : []
  const chartData = results?.map((company) => ({
    ticker: company.ticker,
    revenue: observed(company.revenue_ttm) ? company.revenue_ttm / 1e9 : null,
    fcf: observed(company.fcf_margin_ttm) ? company.fcf_margin_ttm * 100 : null,
    operating: observed(company.operating_margin_ttm)
      ? company.operating_margin_ttm * 100
      : null,
  }))
  if (!ready || appliedUrl === null) return <AppShell><p role="status" className="text-sm text-slate-400">Restoring saved comparison…</p></AppShell>
  return (
    <AppShell>
      <header className="mb-7">
        <p className="eyebrow mb-2">Perspective through comparison</p>
        <h1 className="page-title">Compare companies</h1>
        <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
          Put the same financial measures side by side. See where businesses
          differ, and where the evidence is incomplete.
        </p>
      </header>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
        <p role="status">{draft.status === 'saved' ? `Draft saved in this browser · ${snapshotTime(draft.savedAt!)}` : 'Comparison draft stays in this browser.'}{draft.message ? ` ${draft.message}` : ''}</p>
        <button type="button" className="button-secondary !text-xs" onClick={() => {
          reset()
          internalUrls.current.clear()
          compare.reset()
          setError('')
          queryClient.removeQueries({ queryKey: ['workspace', 'compare-snapshot'] })
          internalUrls.current.add('')
          replaceResearchUrl(window.history, '/compare', new URLSearchParams())
        }}>Clear saved comparison</button>
      </div>
      <section
        className="surface mb-6 p-5 sm:p-6"
        aria-label="Company selection"
      >
        <div className="mb-5 flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Build your comparison</h2>
          <span className="text-xs text-slate-500">
            {tickers.length} / 20 companies
          </span>
        </div>
        <StockSearch compact onAnalyze={add} isLoading={compare.isPending} />
        {error && (
          <p role="alert" className="mt-3 text-xs text-amber-200">
            {error}
          </p>
        )}
        {stocks.some((stock) => !tickers.includes(stock.symbol)) && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="mr-1 text-[11px] text-slate-500">
              From your watchlist
            </span>
            {stocks
              .filter((stock) => !tickers.includes(stock.symbol))
              .slice(0, 6)
              .map((stock) => (
                <button
                  key={stock.symbol}
                  disabled={compare.isPending}
                  className="button-secondary !px-2.5 !py-1.5 !text-[11px]"
                  onClick={() => add(stock.symbol)}
                >
                  + {stock.symbol}
                </button>
              ))}
          </div>
        )}
        <div className="my-5 flex min-h-10 flex-wrap gap-2">
          {tickers.length ? (
            tickers.map((ticker) => (
              <span
                key={ticker}
                className="inline-flex items-center gap-3 rounded-lg border border-violet-400/20 bg-violet-400/[0.08] py-2 pl-3 pr-2 text-xs font-medium text-violet-200"
              >
                {ticker}
                <button
                  disabled={compare.isPending}
                  aria-label={`Remove ${ticker}`}
                  onClick={() => commit(tickers.filter((t) => t !== ticker))}
                  className="rounded p-1 hover:bg-white/10"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))
          ) : (
            <p className="self-center text-xs text-slate-500">
              Add at least two companies to get started.
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3 border-t border-white/[0.07] pt-5">
          <button
            disabled={tickers.length < 2 || compare.isPending}
            onClick={() => {
              setSubmitted(selection)
              const id = crypto.randomUUID()
              setValue((current) => ({ ...current, requestId: id }))
              void compare.mutateAsync({ tickers }).then((results) => {
                setValue((current) => completeComparison(current, id, {
                  tickers, results: draftFinancialRows(results), capturedAt: new Date().toISOString(),
                }), generation)
              }).catch(() => { /* The mutation exposes the error while keeping saved evidence. */ })
            }}
            className="button-primary disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Scale className="h-4 w-4" />
            {compare.isPending ? 'Comparing…' : 'Run comparison'}
          </button>
          {tickers.length > 0 && (
            <button
              disabled={compare.isPending}
              className="button-secondary"
              onClick={() => commit([])}
            >
              Clear selection
            </button>
          )}
          {tickers.length >= 2 && !compare.isPending && (
            <Link
              href={`/trading?${new URLSearchParams({ tab: 'backtest', symbols: selection, handoff: handoffId })}`}
              onClick={(event) => {
                if (event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
                  event.preventDefault()
                  router.push(`/trading?${new URLSearchParams({ tab: 'backtest', symbols: selection, handoff: crypto.randomUUID() })}`)
                }
              }}
              className="button-secondary"
            >
              <FlaskConical className="h-4 w-4" />
              Backtest selected companies
            </Link>
          )}
          <span className="text-[11px] text-slate-500">
            Selections are saved in this page’s URL.
          </span>
        </div>
      </section>
      {compare.isPending && (
        <div role="status" className="surface mb-5 p-5 text-sm text-violet-200">
          Collecting financial statements for {submitted.split(',').join(', ')}…
        </div>
      )}
      {compare.isError && submitted === selection && (
        <div
          role="alert"
          className="surface mb-5 border-rose-400/20 p-5 text-sm text-rose-200"
        >
          {compare.error.message} Try running the comparison again.
        </div>
      )}
      {results && (
        <>
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Financial comparison</h2>
              <p className="mt-1 text-xs text-slate-400">
                {results.length} of {tickers.length} requested companies
                returned · — means unavailable
              </p>
              {snapshot && (
                <p className="mt-1 text-[11px] text-slate-500">
                  Saved {snapshotTime(snapshot.capturedAt)} · Run comparison to refresh
                </p>
              )}
            </div>
            <span className="text-xs text-slate-500">
              Trailing twelve months unless labeled
            </span>
          </div>
          {missing.length > 0 && (
            <p
              role="status"
              className="surface mb-4 border-amber-400/20 p-4 text-xs leading-6 text-amber-200"
            >
              No response for {missing.join(', ')}. Those companies are excluded
              from the table and charts. Retry to check coverage.
            </p>
          )}
          {!results.length ? (
            <div className="surface p-8 text-center text-sm text-slate-400">
              No company data was returned. Try again or choose different
              companies.
            </div>
          ) : (
            <>
              <p className="mb-4 text-[11px] leading-6 text-slate-500">
                Amounts use provider reporting units. Reporting currency is not
                verified here; check each company’s financials before comparing
                monetary totals.
              </p>
              <div className="surface overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="min-w-40 p-4 font-medium text-slate-500">
                          Metric
                        </th>
                        {results.map((company) => (
                          <th
                            key={company.ticker}
                            className="min-w-36 p-4 text-right"
                          >
                            <Link
                              href={companyResearchHref(company.ticker, returnTo)}
                              className="inline-flex items-center gap-2 text-violet-200"
                            >
                              {company.ticker}
                              <ArrowUpRight className="h-3 w-3" />
                            </Link>
                            {company.insufficient_data && (
                              <span className="mt-1 block font-normal text-amber-200">
                                Limited financial data
                              </span>
                            )}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.map(({ key, label, format }) => (
                        <tr
                          key={key}
                          className="border-b border-white/[0.05] last:border-0"
                        >
                          <th className="p-4 font-normal text-slate-400">
                            {label}
                          </th>
                          {results.map((company) => {
                            const value = company[key]
                            const basis = company.growth_metadata?.[key]
                            const period = company.period_metadata?.[key]
                            return (
                              <td
                                key={company.ticker}
                                className="p-4 text-right font-medium text-slate-100"
                              >
                                {format(
                                  typeof value === 'number' ? value : null,
                                )}
                                {basis && (
                                  <span className="mt-1 block text-[10px] font-normal text-slate-500">
                                    {basis.status === 'available'
                                      ? basis.basis === 'fiscal_year'
                                        ? 'Fiscal-year comparison'
                                        : 'TTM comparison'
                                      : 'Growth unavailable'}
                                  </span>
                                )}
                                {basis?.status === 'available' &&
                                  basis.current_period_end &&
                                  basis.prior_period_end && (
                                    <span className="mt-1 block text-[10px] font-normal leading-4 text-slate-500">
                                      Through {basis.current_period_end}
                                      <br />
                                      vs. {basis.prior_period_end}
                                    </span>
                                  )}
                                {period?.period_end && (
                                  <span className="mt-1 block text-[10px] font-normal text-slate-500">
                                    Through {period.period_end}
                                  </span>
                                )}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="mt-5 grid gap-5 xl:grid-cols-2">
                <section className="surface min-w-0 p-5">
                  <h3 className="mb-1 text-sm font-semibold">Revenue scale</h3>
                  <p className="mb-5 text-xs text-slate-500">
                    Trailing twelve months · Billions in provider reporting
                    units
                  </p>
                  <div
                    className="h-64"
                    role="img"
                    aria-label="Revenue comparison chart"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <CartesianGrid vertical={false} stroke="#ffffff0c" />
                        <XAxis
                          dataKey="ticker"
                          tick={{ fill: '#94a3b8', fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          tick={{ fill: '#64748b', fontSize: 10 }}
                          width={48}
                          tickLine={false}
                          axisLine={false}
                        />
                        <Tooltip
                          contentStyle={chartStyle}
                          formatter={(v) => [
                            `${Number(v).toFixed(2)}B`,
                            'Revenue',
                          ]}
                        />
                        <Bar
                          dataKey="revenue"
                          fill="#a78bfa"
                          radius={[4, 4, 0, 0]}
                          maxBarSize={52}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </section>
                <section className="surface min-w-0 p-5">
                  <h3 className="mb-1 text-sm font-semibold">
                    Margins in context
                  </h3>
                  <p className="mb-5 text-xs text-slate-500">
                    <span className="text-violet-300">Free cash flow</span> /{' '}
                    <span className="text-sky-300">Operating margin</span> ·
                    Percent
                  </p>
                  <div
                    className="h-64"
                    role="img"
                    aria-label="Margin comparison chart"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <CartesianGrid vertical={false} stroke="#ffffff0c" />
                        <XAxis
                          dataKey="ticker"
                          tick={{ fill: '#94a3b8', fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          tick={{ fill: '#64748b', fontSize: 10 }}
                          width={48}
                          tickFormatter={(v) => `${v}%`}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip
                          contentStyle={chartStyle}
                          formatter={(v) => `${Number(v).toFixed(1)}%`}
                        />
                        <Bar
                          dataKey="fcf"
                          name="Free cash flow margin"
                          fill="#a78bfa"
                          radius={[4, 4, 0, 0]}
                          maxBarSize={36}
                        />
                        <Bar
                          dataKey="operating"
                          name="Operating margin"
                          fill="#7dd3fc"
                          radius={[4, 4, 0, 0]}
                          maxBarSize={36}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </section>
              </div>
            </>
          )}
        </>
      )}
      {!results && !compare.isPending && (
        <div className="surface p-8 text-center sm:p-12">
          <Scale className="mx-auto mb-4 h-7 w-7 text-violet-300" />
          <h2 className="text-base font-medium">
            A useful comparison starts with context
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-400">
            Choose companies with comparable business models, then look at
            revenue, cash generation, margins, and debt together.
          </p>
        </div>
      )}
    </AppShell>
  )
}
