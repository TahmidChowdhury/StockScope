'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { ArrowUpRight, ScanLine, SlidersHorizontal } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import AppShell from '@/components/AppShell'
import { useScreener } from '@/hooks/useFundamentals'
import { useWatchlist } from '@/hooks/useWatchlist'
import { useWorkspaceDraft } from '@/hooks/useWorkspaceDraft'
import { amount, parseSymbols, percent, ratio } from '@/lib/financial-format'
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
const columns: {
  key: keyof FundamentalsTTM
  label: string
  format: (value?: number | null) => string
}[] = [
  { key: 'revenue_ttm', label: 'Revenue · TTM', format: amount },
  { key: 'revenue_growth_yoy', label: 'Revenue growth', format: percent },
  { key: 'fcf_margin_ttm', label: 'FCF margin', format: percent },
  { key: 'fcf_growth_yoy', label: 'FCF growth', format: percent },
  { key: 'operating_margin_ttm', label: 'Operating margin', format: percent },
  { key: 'ebitda_growth_yoy', label: 'EBITDA growth', format: percent },
  { key: 'debt_to_cash', label: 'Debt / cash', format: ratio },
]

export default function ScreenerPage() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-[#101218]" />}>
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
  const returnTo = `/screener?${screenCriteriaParams(value.criteria)}`
  if (!ready || appliedUrl === null) return <AppShell><p role="status" className="text-sm text-slate-400">Restoring saved screen…</p></AppShell>
  return (
    <AppShell>
      <header className="mb-7">
        <p className="eyebrow mb-2">Discover with a clear set of criteria</p>
        <h1 className="page-title">Stock screener</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
          Narrow the field by growth, cash generation, and balance sheet
          strength. Coverage is shown alongside every result.
        </p>
      </header>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
        <p role="status">{draft.status === 'saved' ? `Draft saved in this browser · ${snapshotTime(draft.savedAt!)}` : 'Screening draft stays in this browser.'}{draft.message ? ` ${draft.message}` : ''}</p>
        <button type="button" className="button-secondary !text-xs" onClick={() => {
          reset()
          internalUrls.current.clear()
          screener.reset()
          setError('')
          queryClient.removeQueries({ queryKey: ['workspace', 'screener-snapshot'] })
          syncUrl(new URLSearchParams())
        }}>Clear saved screen</button>
      </div>
      <form
        className="surface mb-6 p-5 sm:p-6"
        onSubmit={(event) => {
          event.preventDefault()
          run()
        }}
      >
        <fieldset disabled={screener.isPending} className="min-w-0">
          <div className="mb-6 flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 text-violet-300" />
            <h2 className="text-sm font-semibold">Screening criteria</h2>
            <span className="ml-auto text-[11px] text-slate-500">
              Leave any filter blank to skip it
            </span>
          </div>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <label className="field-label">
              Company universe
              <select
                className="field-input"
                value={universe}
                onChange={(e) => setUniverse(e.target.value)}
              >
                <option value="curated">Curated US-stock list</option>
                <option value="watchlist">
                  Shared watchlist ({stocks.length})
                </option>
                <option value="custom">Custom tickers</option>
              </select>
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
          <p className="mb-6 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 text-[11px] leading-5 text-slate-400">
            {universe === 'curated'
              ? 'The bundled list is curated, with an unknown membership date. It is not the full current S&P 500. Larger screens may take a minute.'
              : universe === 'watchlist'
                ? 'Screen the companies already saved in this shared research workspace.'
                : 'Supply up to 500 unique symbols. Missing data and provider failures will be reported.'}
          </p>
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
          <div className="mt-6 grid gap-4 border-t border-white/[0.07] pt-6 sm:grid-cols-3">
            <label className="field-label">
              Sort by
              <select
                className="field-input"
                value={sort}
                onChange={(e) => setSort(e.target.value)}
              >
                {sortOptions.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Direction
              <select
                className="field-input"
                value={direction}
                onChange={(e) => setDirection(e.target.value)}
              >
                <option value="desc">Highest first</option>
                <option value="asc">Lowest first</option>
              </select>
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
          {error && (
            <p role="alert" className="mt-4 text-xs text-rose-200">
              {error}
            </p>
          )}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              className="button-primary disabled:opacity-40"
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
            <span className="text-[11px] text-slate-500">
              Inputs save in this browser and in the URL.
            </span>
          </div>
        </fieldset>
      </form>
      {screener.isPending && (
        <p role="status" className="surface mb-5 p-5 text-sm text-violet-200">
          Collecting financial data and evaluating your criteria…
        </p>
      )}
      {screener.isError && (
        <p
          role="alert"
          className="surface mb-5 border-rose-400/20 p-5 text-sm text-rose-200"
        >
          {screener.error.message} Run the screen again to retry.
        </p>
      )}
      {snapshot && data ? (
        <>
          {screenCriteriaKey(snapshot.criteria) !== formKey && (
            <p
              role="status"
              className="surface mb-4 border-amber-400/20 p-4 text-xs text-amber-200"
            >
              Criteria changed. The results below belong to your previous
              screen. Run again to apply the new filters.
            </p>
          )}
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ['Attempted', data.total_attempted],
              ['Evaluated', data.total_evaluated],
              ['Matches', data.total_matches],
              [
                'Failed / insufficient',
                `${data.total_failed} / ${data.total_insufficient}`,
              ],
            ].map(([label, value]) => (
              <div key={label} className="surface p-4">
                <p className="text-[11px] text-slate-500">{label}</p>
                <p className="mt-2 text-xl font-semibold tabular-nums">
                  {value}
                </p>
              </div>
            ))}
          </div>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Screening results</h2>
              <p className="mt-1 text-xs text-slate-500">
                {snapshot.universeName || data.universe_name} · Showing{' '}
                {data.results.length} of {data.total_matches} matches
              </p>
              <p className="mt-1 text-[11px] text-slate-500">
                Saved {snapshotTime(snapshot.capturedAt)} · Run screen to refresh
              </p>
            </div>
            <Link
              aria-disabled={selected.length < 2}
              onClick={(e) => {
                if (selected.length < 2) e.preventDefault()
              }}
              href={`/compare?tickers=${selected.join(',')}`}
              className={`button-secondary ${selected.length < 2 ? 'opacity-40' : ''}`}
            >
              Compare selected ({selected.length})
              <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
          {data.results.length ? (
            <div className="surface overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/10 text-[10px] uppercase tracking-wider text-slate-500">
                      <th className="p-4">
                        <span className="sr-only">Select</span>
                      </th>
                      <th className="p-4">Company</th>
                      {columns.map((column) => (
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
                    {data.results.map((company) => (
                      <tr
                        key={company.ticker}
                        className="border-b border-white/[0.05] last:border-0 hover:bg-white/[0.02]"
                      >
                        <td className="p-4">
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
                        </td>
                        <td className="p-4 font-semibold">
                          <Link
                            className="text-violet-200"
                            href={companyResearchHref(company.ticker, returnTo)}
                          >
                            {company.ticker} ↗
                          </Link>
                        </td>
                        {columns.map(({ key, format }) => {
                          const value = company[key]
                          const basis = company.growth_metadata?.[key]
                          return (
                            <td
                              key={key}
                              className="whitespace-nowrap p-4 text-right text-slate-200"
                            >
                              {format(typeof value === 'number' ? value : null)}
                              {basis && (
                                <span className="mt-1 block text-[10px] text-slate-500">
                                  {basis.status === 'available'
                                    ? basis.basis === 'fiscal_year'
                                      ? 'Fiscal year'
                                      : 'TTM'
                                    : 'Unavailable'}
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
          ) : (
            <div className="surface p-10 text-center">
              <h3 className="text-sm font-medium">
                No companies matched this screen
              </h3>
              <p className="mt-2 text-xs leading-6 text-slate-400">
                Review coverage above, loosen the filters, or try a different
                universe.
              </p>
            </div>
          )}
          <p className="mt-4 text-[11px] leading-6 text-slate-500">
            Growth can use TTM or fiscal-year comparisons; each available growth
            figure identifies its basis. Missing values stay unavailable and do
            not pass a filter that requires them. Amounts use provider reporting
            units; verify reporting currencies before comparing companies.
          </p>
        </>
      ) : (
        !screener.isPending && (
          <div className="surface px-6 py-10 text-center">
            <ScanLine className="mx-auto mb-4 h-7 w-7 text-violet-300" />
            <h2 className="text-base font-medium">
              Start broad. Find what deserves a closer look.
            </h2>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-400">
              Choose your universe and criteria, then run a screen. Select
              results to carry them straight into a comparison.
            </p>
          </div>
        )
      )}
    </AppShell>
  )
}
