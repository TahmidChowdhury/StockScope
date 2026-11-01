'use client'

import AnimatedSelect from '@/components/ui/AnimatedSelect'

import { Suspense, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { ScanLine, SlidersHorizontal } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import AppShell from '@/components/AppShell'
import { comparisonCurrencyNotice } from '@/lib/financial-format'
import ScreenComparison, { screenMetrics, ScreenMetricValue } from '@/components/ScreenComparison'
import ResearchPanel from '@/components/ResearchPanel'
import { Skeleton } from '@/components/ResearchLoading'
import { useScreener } from '@/hooks/useFundamentals'
import { useWatchlist } from '@/hooks/useWatchlist'
import { useWorkspaceDraft } from '@/hooks/useWorkspaceDraft'
import { parseSymbols } from '@/lib/financial-format'
import { companyResearchHref, snapshotTime } from '@/lib/research-workflow'
import type { FundamentalsTTM, ScreenerRequest } from '@/types'
import { completeScreen, draftFinancialRows, editScreenDraft, initialScreenerDraft, isScreenerDraft, replaceResearchUrl, screenCriteriaFromUrl, screenCriteriaKey, screenCriteriaParams, type ScreenCriteria } from '@/lib/research-drafts'

const filterFields = [
  {
    key: 'min_revenue_growth_yoy',
    label: 'Minimum revenue growth',
    unit: '% YoY',
    placeholder: 'e.g. 10',
    divisor: 100,
  },
  {
    key: 'min_fcf_growth_yoy',
    label: 'Minimum free cash flow growth',
    unit: '% YoY',
    placeholder: 'e.g. 15',
    divisor: 100,
  },
  {
    key: 'min_margin_growth_yoy_pp',
    label: 'Minimum operating margin growth',
    unit: 'percentage points',
    placeholder: 'e.g. 1',
    divisor: 1,
  },
  {
    key: 'min_ebitda_growth_yoy',
    label: 'Minimum EBITDA growth',
    unit: '% YoY',
    placeholder: 'e.g. 12',
    divisor: 100,
  },
  {
    key: 'max_debt_to_cash',
    label: 'Maximum debt / cash',
    unit: 'ratio',
    placeholder: 'e.g. 2',
    divisor: 1,
  },
] as const
const sortOptions = [
  ['revenue_growth_yoy', 'Revenue growth'],
  ['fcf_growth_yoy', 'Free cash flow growth'],
  ['ebitda_growth_yoy', 'EBITDA growth'],
  ['fcf_margin_ttm', 'Free cash flow margin'],
  ['operating_margin_ttm', 'Operating margin'],
  ['revenue_ttm', 'Revenue · TTM'],
]
export default function ScreenerPage() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-[#111513]" />}>
      <ScreenerWorkspace />
    </Suspense>
  )
}
function ScreenerWorkspace() {
  return <ScreenForm />
}
function ScreenForm() {
  const search = useSearchParams()
  const queryClient = useQueryClient()
  const draft = useWorkspaceDraft('screener', initialScreenerDraft, isScreenerDraft)
  const { value, setValue, ready, generation, reset } = draft
  const [filtersOpen, setFiltersOpen] = useState<boolean | null>(null)
  const url = search.toString()
  const lastUrl = useRef<string | null>(null)
  const internalUrls = useRef(new Set<string>())
  const [appliedUrl, setAppliedUrl] = useState<string | null>(null)
  const { data: stocks = [] } = useWatchlist()
  const { filters, universe, custom, sort, direction, limit } = value.criteria
  const syncUrl = (params: URLSearchParams) => {
    const nextUrl = params.toString()
    internalUrls.current = new Set([...internalUrls.current, nextUrl].slice(-50))
    replaceResearchUrl(window.history, '/screener', params)
  }
  const updateCriteria = (changes: Partial<ScreenCriteria>) => setValue((current) => editScreenDraft(current, changes, syncUrl))
  const setFilters = (filters: Record<string, string>) => updateCriteria({ filters: Object.fromEntries(filterFields.map(({ key }) => [key, (filters[key] || '').slice(0, 40)])) })
  const setUniverse = (universe: string) => updateCriteria({ universe: universe as ScreenCriteria['universe'] })
  const setCustom = (custom: string) => updateCriteria({ custom })
  const setSort = (sort: string) => updateCriteria({ sort })
  const setDirection = (direction: string) => updateCriteria({ direction: direction as ScreenCriteria['direction'] })
  const setLimit = (limit: string) => updateCriteria({ limit: limit.slice(0, 8) })
  const [error, setError] = useState('')
  const screener = useScreener()
  const { snapshot, selected } = value
  const formKey = screenCriteriaKey(value.criteria)
  const run = () => {
    setError('')
    const symbols =
      universe === 'watchlist'
        ? stocks.map((stock) => stock.symbol)
        : universe === 'custom'
          ? parseSymbols(custom)
          : undefined
    if (symbols && (!symbols.length || symbols.length > 500)) {
      setError('Choose between 1 and 500 symbols for this universe.')
      return
    }
    if (
      universe === 'custom' &&
      custom
        .trim()
        .split(/[\s,]+/)
        .some((symbol) => !/^[A-Z][A-Z0-9.-]{0,9}$/i.test(symbol))
    ) {
      setError('Use valid ticker symbols, separated by commas or spaces.')
      return
    }
    const request: ScreenerRequest = {
      universe: symbols,
      sort_by: sort,
      sort_dir: direction,
      limit: Number(limit),
    }
    for (const field of filterFields)
      if (filters[field.key] !== '') {
        const value = Number(filters[field.key]) / field.divisor
        if (!Number.isFinite(value)) {
          setError('Every filter must be a valid number.')
          return
        }
        request[field.key] = value
      }
    const universeName =
      universe === 'watchlist'
        ? 'Shared watchlist'
        : universe === 'custom'
          ? 'Custom stock list'
          : ''
    const id = crypto.randomUUID()
    const criteria = value.criteria
    setValue((current) => ({ ...current, requestId: id }))
    syncUrl(screenCriteriaParams(criteria))
    void screener.mutateAsync(request).then((data) => {
      const { total_attempted, total_evaluated, total_matches, total_failed, total_insufficient, universe_name } = data
      setValue((current) => completeScreen(current, id, {
        criteria, universeName, capturedAt: new Date().toISOString(),
        data: { results: draftFinancialRows(data.results), total_attempted, total_evaluated, total_matches, total_failed, total_insufficient, universe_name },
      }), generation)
    }).catch(() => { /* The mutation exposes the request error without replacing saved evidence. */ })
  }
  useEffect(() => {
    if (!ready || lastUrl.current === url) return
    lastUrl.current = url
    const internallyUpdated = internalUrls.current.delete(url)
    if (!internallyUpdated) {
      const criteria = screenCriteriaFromUrl(new URLSearchParams(url))
      if (criteria) setValue((current) => ({ ...current, criteria }))
    }
    setAppliedUrl(url)
  }, [ready, url, setValue])
  useEffect(() => {
    const navigatingHistory = () => internalUrls.current.clear()
    window.addEventListener('popstate', navigatingHistory)
    return () => window.removeEventListener('popstate', navigatingHistory)
  }, [])
  const data = snapshot?.data
  const loading = screener.isPending && !data
  const rows: (FundamentalsTTM | null)[] = data?.results ?? (loading ? Array.from({ length: Math.min(Number(limit), 6) }, () => null) : [])
  const activeFilterCount = Object.values(filters).filter(Boolean).length
  const returnTo = `/screener?${screenCriteriaParams(value.criteria)}`
  if (!ready || appliedUrl === null) return <AppShell><p role="status" className="text-sm text-slate-400">Restoring saved screen…</p></AppShell>
  return (
    <AppShell>
      <header className="mb-7">
        <h1 className="page-title">Stock screener</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
          Filter companies with saved financials by growth, margins, or debt.
          Open a company’s Financials page to add coverage.
        </p>
      </header>
      <form
        className="surface mb-6 p-5 sm:p-6"
        onSubmit={(event) => {
          event.preventDefault()
          run()
        }}
      >
        <fieldset disabled={screener.isPending} className="min-w-0">
          <div className="mb-4 flex flex-wrap items-center gap-x-2 gap-y-1">
            <SlidersHorizontal className="h-4 w-4 text-sage-300" />
            <h2 className="text-base font-medium">Screening criteria</h2>
            <span className="w-full text-xs text-slate-400 sm:ml-auto sm:w-auto">
              Leave any filter blank to skip it
            </span>
          </div>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <label className="field-label">
              Company universe
              <AnimatedSelect
                className="field-input"
                value={universe}
                onValueChange={(value) => setUniverse(value)}
              >
                <option value="curated">Curated US-stock list</option>
                <option value="watchlist">
                  Shared watchlist ({stocks.length})
                </option>
                <option value="custom">Custom tickers</option>
              </AnimatedSelect>
            </label>
            {universe === 'custom' && (
              <label className="field-label sm:col-span-2">
                Ticker symbols
                <input
                  className="field-input"
                  value={custom}
                  onInput={(e) => setCustom(e.currentTarget.value.toUpperCase())}
                  onChange={(e) => setCustom(e.target.value.toUpperCase())}
                  placeholder="AAPL, MSFT, NVDA"
                  required
                  maxLength={6000}
                />
              </label>
            )}
          </div>
          <p className="mb-4 max-w-2xl text-xs leading-5 text-slate-400">
            {universe === 'curated'
              ? 'This list covers a selection of S&P 500 stocks. Its membership date is unknown. Larger screens may take a minute.'
              : universe === 'watchlist'
                ? 'Includes companies in the shared research library.'
                : 'Enter up to 500 distinct tickers, separated by commas or spaces.'}
          </p>
          <details
            className="border-y border-white/10"
            open={filtersOpen ?? (window.matchMedia('(min-width: 640px)').matches || activeFilterCount > 0)}
            onToggle={event => setFiltersOpen(event.currentTarget.open)}
          >
            <summary className="cursor-pointer py-3 text-sm font-medium text-sage-300">
              Filters &amp; sorting
              {activeFilterCount > 0 && <span className="ml-2 text-xs text-slate-400">{activeFilterCount} active</span>}
            </summary>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {filterFields.map((field) => (
                <label key={field.key} className="field-label">
                  {field.label}
                  <span className="ml-1 text-[10px] text-slate-500">
                    {' '}
                    {field.unit}
                  </span>
                  <input
                    className="field-input"
                    type="number"
                    step="any"
                    min={field.key === 'max_debt_to_cash' ? 0 : undefined}
                    value={filters[field.key]}
                    placeholder={field.placeholder}
                    onInput={(e) => setFilters({ ...filters, [field.key]: e.currentTarget.value })}
                    onChange={(e) =>
                      setFilters({ ...filters, [field.key]: e.target.value })
                    }
                  />
                </label>
              ))}
            </div>
            <div className="my-4 grid gap-4 sm:grid-cols-3">
              <label className="field-label">
                Sort by
                <AnimatedSelect
                  className="field-input"
                  value={sort}
                  onValueChange={(value) => setSort(value)}
                >
                  {sortOptions.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </AnimatedSelect>
              </label>
              <label className="field-label">
                Direction
                <AnimatedSelect
                  className="field-input"
                  value={direction}
                  onValueChange={(value) => setDirection(value)}
                >
                  <option value="desc">Highest first</option>
                  <option value="asc">Lowest first</option>
                </AnimatedSelect>
              </label>
              <label className="field-label">
                Maximum results
                <input
                  className="field-input"
                  type="number"
                  min={1}
                  max={500}
                  required
                  value={limit}
                  onInput={(e) => setLimit(e.currentTarget.value)}
                  onChange={(e) => setLimit(e.target.value)}
                />
              </label>
            </div>
          </details>
          {error && (
            <p role="alert" className="mt-4 text-xs text-rose-200">
              {error}
            </p>
          )}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              className="button-primary min-w-28 disabled:opacity-40"
              type="submit"
            >
              <ScanLine className="h-4 w-4" />
              {screener.isPending ? 'Screening…' : 'Run screen'}
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={() => {
                setFilters(
                  Object.fromEntries(
                    filterFields.map((field) => [field.key, '']),
                  ),
                )
                setError('')
              }}
            >
              Clear filters
            </button>
          </div>
        </fieldset>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/10 pt-3 text-xs text-slate-400">
          <p role="status">{draft.status === 'saved' ? `Draft saved in this browser · ${snapshotTime(draft.savedAt!)}` : 'Criteria are saved in this browser and reflected in the URL.'}{draft.message ? ` ${draft.message}` : ''}</p>
          <button type="button" className="text-xs underline decoration-white/20 underline-offset-4 hover:text-white" onClick={() => {
            reset()
            internalUrls.current.clear()
            screener.reset()
            setError('')
            queryClient.removeQueries({ queryKey: ['workspace', 'screener-snapshot'] })
            syncUrl(new URLSearchParams())
          }}>Clear saved screen</button>
        </div>
      </form>
      <ResearchPanel pending={screener.isPending} aria-label="Screen results">
        {screener.isError && <p role="alert" className="surface mb-4 border-rose-400/20 p-4 text-sm text-rose-200">
          {screener.error.message} Run the screen again.{snapshot && ' Your saved screen is still shown.'}
        </p>}
        {data || loading ? <>
          {snapshot && screenCriteriaKey(snapshot.criteria) !== formKey && (
            <p
              role="status"
              className="surface mb-4 border-amber-400/20 p-4 text-xs text-amber-200"
            >
              Criteria changed. The results below belong to your previous
              screen. Run again to apply the new filters.
            </p>
          )}
          <div data-reading-anchor="coverage" className="mb-5 grid grid-cols-2 gap-x-4 gap-y-3 border-y border-white/10 py-4 sm:grid-cols-4">
            {[
              ['Attempted', data?.total_attempted],
              ['Evaluated', data?.total_evaluated],
              ['Matches', data?.total_matches],
              [
                'Not cached / insufficient',
                data && `${data.total_failed} / ${data.total_insufficient}`,
              ],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-[11px] text-slate-500">{label}</p>
                <div className="mt-2 flex h-7 items-center text-xl font-semibold tabular-nums">
                  {loading ? <Skeleton className="h-5 w-10" /> : value}
                </div>
              </div>
            ))}
          </div>
          <div data-reading-anchor="summary" className="mb-4 grid justify-items-start gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <div>
              <h2 className="text-lg font-semibold">Screening results</h2>
              <p role="status" className="mt-1 text-xs text-slate-500">
                {snapshot && data ? `${snapshot.universeName || data.universe_name} · Showing ${data.results.length} of ${data.total_matches} matches` : 'Evaluating your criteria…'}
              </p>
              <p className="mt-1 min-h-4 text-[11px] text-slate-500">
                {snapshot && <>Saved {snapshotTime(snapshot.capturedAt)} · Run screen to refresh</>}
                {snapshot && screener.isPending && <span className="sr-only" role="status">Refreshing the saved screen…</span>}
              </p>
            </div>
            <ScreenComparison
              key={snapshot?.capturedAt}
              companies={data?.results.filter(company => selected.includes(company.ticker)) ?? []}
              capturedAt={snapshot?.capturedAt}
            />
          </div>
          {data && <p className="mb-3 text-xs text-slate-400">{comparisonCurrencyNotice(data.results)} Revenue sorting uses raw reported amounts, not a common currency.</p>}
          {rows.length ? (
            <div className="surface overflow-hidden">
              <p className="border-b border-white/[0.07] px-4 py-3 text-xs text-slate-500 sm:hidden">Swipe across for more metrics. Select companies to compare.</p>
              <div data-reading-anchor="table" className="overflow-x-auto" role="region" aria-label="Screening results, scroll horizontally for more metrics" tabIndex={0}>
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/10 text-[10px] uppercase tracking-wider text-slate-500">
                      <th className="sticky left-0 z-10 w-12 min-w-12 bg-[#191e1b] p-0">
                        <span className="sr-only">Select</span>
                      </th>
                      <th scope="col" className="sticky left-12 z-10 min-w-28 bg-[#191e1b] p-3">Company</th>
                      {screenMetrics.map((column) => (
                        <th
                          key={column.key}
                          className="whitespace-nowrap p-4 text-right font-medium"
                        >
                          {column.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((company, index) => (
                      <tr
                        key={company?.ticker ?? index}
                        data-reading-anchor={`result-${index}`}
                        aria-hidden={company ? undefined : true}
                        className="border-b border-white/[0.05] last:border-0 hover:bg-white/[0.02]"
                      >
                        <td className="sticky left-0 z-10 bg-[#191e1b] p-0">
                          {company ? <label className="flex h-12 w-12 cursor-pointer items-center justify-center">
                          <input
                            type="checkbox"
                            aria-label={`Select ${company.ticker} for comparison`}
                            checked={selected.includes(company.ticker)}
                            disabled={
                              !selected.includes(company.ticker) &&
                              selected.length >= 20
                            }
                            onChange={(e) => {
                              const checked = e.target.checked
                              setValue((current) => ({
                                  ...current,
                                  selected: checked
                                    ? [...current.selected, company.ticker]
                                    : current.selected.filter((ticker) => ticker !== company.ticker),
                              }))
                            }}
                          />
                          </label> : <Skeleton className="mx-auto h-3.5 w-3.5" />}
                        </td>
                        <td className="sticky left-12 z-10 bg-[#191e1b] p-3 font-semibold">
                          {company ? <Link
                            className="inline-flex min-h-11 items-center text-sage-200"
                            href={companyResearchHref(company.ticker, returnTo)}
                          >
                            {company.ticker} ↗
                          </Link> : <span className="flex h-11 items-center"><Skeleton className="h-3 w-12" /></span>}
                        </td>
                        {screenMetrics.map(metric => (
                          <td key={metric.key} className="whitespace-nowrap p-4 text-right text-slate-200">
                            {company ? <ScreenMetricValue company={company} metric={metric} /> : <Skeleton className="ml-auto h-3 w-12" />}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : data && (
            <div className="surface p-10 text-center">
              <h3 className="text-sm font-medium">
                {data.total_evaluated === 0 ? 'No saved fundamentals in this view' : 'No companies matched this screen'}
              </h3>
              <p className="mt-2 text-xs leading-6 text-slate-400">
                {data.total_evaluated === 0 ? 'Open a company’s Financials view to load its data, then run this screen again. This screen uses saved data only.' : 'Review coverage above, loosen the filters, or try a different universe.'}
              </p>
            </div>
          )}
          <p data-reading-anchor="notes" className="mt-4 text-[11px] leading-6 text-slate-500">
            Growth can use TTM or fiscal-year comparisons; each available growth
            figure identifies its basis. Missing values stay unavailable and do
            not pass a filter that requires them. Amounts use provider reporting
            units; verify reporting currencies before comparing companies.
          </p>
        </> : !screener.isError && (
          <div className="border-t border-white/10 pt-5">
            <h2 className="text-base font-medium">
              Screening results
            </h2>
            <p className="mt-1 max-w-lg text-sm leading-6 text-slate-400">
              Run a screen, then select two or more results to see their financials side by side.
            </p>
          </div>
        )}
      </ResearchPanel>
    </AppShell>
  )
}
