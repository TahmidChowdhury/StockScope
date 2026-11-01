'use client'

import ResearchPanel from './ResearchPanel'
import { ValuationLoading } from './ResearchLoading'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowDownUp, Calculator, RefreshCw } from 'lucide-react'
import { apiFetch, readApiJson } from '@/lib/api'
import { withRequestTimeout } from '@/lib/request-timeout'
import { amount, percent, observed, ratio } from '@/lib/financial-format'
import { useWorkspaceDraft } from '@/hooks/useWorkspaceDraft'
import { isScenarioDraft, type ScenarioDraft } from '@/lib/company-drafts'
import {
  equityCashFlowScenario,
  valuationDate,
  type EvidenceMetric,
  type ValuationEvidence,
} from '@/lib/valuation'

function Metric({ item, anchor }: { item: EvidenceMetric; anchor: string }) {
  return (
    <div data-reading-anchor={anchor} className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4">
      <p className="text-xs leading-5 text-slate-400">{item.label}</p>
      <p
        className={`mt-2 text-2xl font-semibold tabular-nums ${observed(item.value) && item.value < 0 ? 'text-amber-200' : 'text-white'}`}
      >
        {item.format === 'percent'
          ? percent(item.value)
          : observed(item.value)
            ? `${ratio(item.value)}×`
            : '—'}
      </p>
      <p className="mt-2 text-[11px] leading-5 text-slate-500">
        {item.basis === 'fiscal_year'
          ? 'FY'
          : item.basis === 'ttm'
            ? 'TTM'
            : item.basis === 'balance_sheet'
              ? 'Balance sheet'
              : 'Basis unknown'}{' '}
        · {item.period_end || 'Period unknown'}
        {item.prior_period_end ? ` vs ${item.prior_period_end}` : ''}
      </p>
      {item.status !== 'available' && (
        <p className="mt-1 text-[11px] text-amber-200/80">
          {item.status === 'stale'
            ? 'Stale input'
            : item.status === 'missing'
              ? 'Missing data'
              : item.status === 'unknown'
                ? 'Basis not verified'
                : 'Not meaningful'}
        </p>
      )}
      {item.reason && (
        <p className="mt-1 text-[11px] leading-5 text-slate-400">
          {item.reason}
        </p>
      )}
    </div>
  )
}

function money(value: number | null, currency: string | null) {
  if (!observed(value)) return '—'
  return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)}${currency ? ` ${currency}` : ' · currency unknown'}`
}

const initialScenarios = [
  { name: 'Bear', change: '-15', multiple: '12' },
  { name: 'Base', change: '0', multiple: '18' },
  { name: 'Bull', change: '15', multiple: '24' },
]

function Scenarios({ data }: { data: ValuationEvidence }) {
  const initialDraft = useMemo<ScenarioDraft>(
    () => ({
      version: 1,
      cashFlow: '',
      shares:
        observed(data.quote.shares_outstanding) &&
        data.quote.shares_outstanding > 0
          ? String(data.quote.shares_outstanding / 1_000_000)
          : '',
      currency: data.quote.currency,
      scenarios: initialScenarios,
    }),
    [data.quote.currency, data.quote.shares_outstanding],
  )
  const {
    value: draft,
    setValue,
    ready,
    status,
    savedAt,
    message,
    generation,
    reset,
  } = useWorkspaceDraft<ScenarioDraft>(
    `company:${data.symbol}:valuation`,
    initialDraft,
    isScenarioDraft,
  )
  const { cashFlow, shares, scenarios } = draft
  const quoteCurrency = draft.currency
  const currencyMatches =
    quoteCurrency !== null && quoteCurrency === data.quote.currency
  const reference = data.quote.status === 'available' ? data.quote.price : null
  const update = (index: number, field: 'change' | 'multiple', value: string) =>
    setValue(
      (previous) => ({
        ...previous,
        scenarios: previous.scenarios.map((row, i) =>
          i === index ? { ...row, [field]: value } : row,
        ),
      }),
      generation,
    )
  return (
    <ResearchPanel pending={!ready} data-reading-anchor="scenarios" className="mt-6 rounded-2xl border border-sage-300/15 bg-sage-400/[0.04] p-5 sm:p-6">
      <div className="flex items-center gap-2 text-sage-200">
        <Calculator className="h-4 w-4" />
        <h3 className="text-sm font-semibold">
          Your equity cash-flow scenarios
        </h3>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-400">
        <p role="status">
          {!ready
            ? 'Reading your saved scenarios…'
            : status === 'saved'
              ? `Saved in this browser · ${valuationDate(savedAt)}`
              : 'Scenario inputs are kept in this browser when storage is available.'}
          {message ? ` ${message}` : ''}
        </p>
        <button
          type="button"
          disabled={!ready}
          onClick={() => {
            reset()
            setValue(initialDraft)
          }}
          className="rounded-lg border border-white/10 px-2.5 py-1.5 text-slate-300 hover:bg-white/5 disabled:opacity-40"
        >
          Reset scenarios
        </button>
      </div>
      <p className="mt-2 max-w-3xl text-xs leading-6 text-slate-400">
        Enter your own normalized annual free cash flow to equity (FCFE), after
        reinvestment and net debt flows. Provider FCF above is not verified FCFE
        and is not filled in. These multiples are editable examples, not
        forecasts or a discounted cash-flow valuation.
      </p>
      {!currencyMatches && (
        <p className="mt-3 text-xs text-amber-200">
          {quoteCurrency
            ? `Saved assumptions use ${quoteCurrency}, while the current quote currency is ${data.quote.currency || 'unknown'}. Calculations are withheld; reset scenarios to start with the current currency.`
            : 'A verified quote currency is required before calculating per-share scenarios. Reset scenarios after the currency becomes available.'}
        </p>
      )}
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <label className="text-xs text-slate-300">
          Your annual FCFE ({quoteCurrency || 'quote currency'} millions)
          <input
            aria-label={`Your annual FCFE (${quoteCurrency || 'quote currency'} millions)`}
            type="number"
            step="any"
            value={cashFlow}
            disabled={!ready}
            onChange={(e) =>
              setValue(
                (previous) => ({ ...previous, cashFlow: e.target.value }),
                generation,
              )
            }
            placeholder="Enter your assumption"
            className="mt-2 w-full rounded-xl border border-white/10 bg-[#111513] px-3 py-2.5 text-sm text-white outline-none focus:border-sage-400/60"
          />
        </label>
        <label className="text-xs text-slate-300">
          Your diluted share count (millions)
          <input
            aria-label="Your diluted share count (millions)"
            type="number"
            step="any"
            value={shares}
            disabled={!ready}
            onChange={(e) =>
              setValue(
                (previous) => ({ ...previous, shares: e.target.value }),
                generation,
              )
            }
            placeholder="Enter diluted shares"
            className="mt-2 w-full rounded-xl border border-white/10 bg-[#111513] px-3 py-2.5 text-sm text-white outline-none focus:border-sage-400/60"
          />
          <span className="mt-2 block text-[11px] text-slate-500">
            Starts with provider shares outstanding when available; verify
            dilution and share/ADR basis.
          </span>
        </label>
      </div>
      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        {scenarios.map((scenario, index) => {
          const result =
            ready && currencyMatches
              ? equityCashFlowScenario(
                  cashFlow,
                  shares,
                  scenario.change,
                  scenario.multiple,
                  reference,
                )
              : null
          return (
            <div
              key={scenario.name}
              data-reading-anchor={`scenario-${index}`}
              className="rounded-xl border border-white/10 bg-[#111513]/70 p-4"
            >
              <p className="text-xs font-semibold text-slate-200">
                {scenario.name}
              </p>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <label className="text-[11px] leading-5 text-slate-400">
                  FCFE change (%)
                  <input
                    aria-label={`${scenario.name} FCFE change (%)`}
                    type="number"
                    step="any"
                    value={scenario.change}
                    disabled={!ready}
                    onChange={(e) => update(index, 'change', e.target.value)}
                    className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.03] p-2 text-sm text-white"
                  />
                </label>
                <label className="text-[11px] leading-5 text-slate-400">
                  Equity multiple (×)
                  <input
                    aria-label={`${scenario.name} equity multiple`}
                    type="number"
                    step="any"
                    value={scenario.multiple}
                    disabled={!ready}
                    onChange={(e) => update(index, 'multiple', e.target.value)}
                    className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.03] p-2 text-sm text-white"
                  />
                </label>
              </div>
              <p className="mt-4 break-words text-xl font-semibold tabular-nums text-white">
                {money(result?.price ?? null, quoteCurrency)}
              </p>
              <p className="mt-1 text-[11px] text-slate-400">
                {result
                  ? result.difference === null
                    ? 'Reference quote unavailable'
                    : `${percent(result.difference)} vs reference quote`
                  : 'Enter positive FCFE and shares; change must exceed −100% and multiple must be positive.'}
              </p>
            </div>
          )
        })}
      </div>
      <p className="mt-4 text-[11px] leading-5 text-slate-500">
        Illustrative price = your annual FCFE × (1 + scenario change) × equity
        multiple ÷ diluted shares. The result is conditional on your
        assumptions, with no time horizon or promised return. Inputs are saved
        locally for this company and access role; refreshing provider evidence
        does not replace them.
      </p>
    </ResearchPanel>
  )
}

export default function ValuationPanel({ symbol, enabled = true }: { symbol: string; enabled?: boolean }) {
  const query = useQuery({
    queryKey: ['valuation', symbol],
    queryFn: ({ signal }): Promise<ValuationEvidence> => withRequestTimeout(signal, 30_000, async (requestSignal) => {
      const response = await apiFetch(
        `/api/valuation/${encodeURIComponent(symbol)}`,
        { signal: requestSignal },
      )
      return readApiJson<ValuationEvidence>(response, 'Valuation evidence is unavailable. Try again later.')
    }),
    enabled: enabled && !!symbol,
    staleTime: 60 * 60_000,
    refetchOnWindowFocus: false,
    retry: false,
  })
  return (
    <ResearchPanel pending={query.isPending}
      aria-label="Business quality and valuation"
      className="surface mt-6 p-5 sm:p-7"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-white">
            Business quality & valuation
          </h2>
          <p className="mt-2 text-xs leading-6 text-slate-400">
            Check the reporting period before comparing ratios.
          </p>
        </div>
        <button
          type="button"
          disabled={query.isFetching}
          onClick={() => void query.refetch()}
          className="button-secondary gap-2 text-xs"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${query.isFetching ? 'animate-spin' : ''}`}
          />
          {query.isFetching ? 'Loading' : 'Reload evidence'}
        </button>
      </div>
      {query.isPending && <ValuationLoading />}
      {query.isError && (
        <p
          role="alert"
          className="mt-5 rounded-xl border border-amber-400/20 bg-amber-400/5 p-4 text-sm text-amber-100"
        >
          {query.error instanceof Error && query.error.name !== 'TimeoutError'
            ? query.error.message
            : 'Loading valuation evidence timed out. Try again.'}
        </p>
      )}
      {query.data && (
        <>
          <div className="mt-6 flex flex-wrap gap-x-8 gap-y-3 rounded-xl border border-white/[0.07] p-4 text-xs">
            <div>
              <p className="text-slate-500">Reference quote</p>
              <p className="mt-1 font-medium text-white">
                {money(query.data.quote.price, query.data.quote.currency)}
              </p>
            </div>
            <div>
              <p className="text-slate-500">
                Price timestamp · {query.data.quote.status}
              </p>
              <p className="mt-1 text-slate-300">
                {valuationDate(query.data.quote.price_at)}
              </p>
            </div>
            <div>
              <p className="text-slate-500">
                Provider market cap / enterprise value
              </p>
              <p className="mt-1 text-slate-300">
                {amount(query.data.quote.market_cap)} /{' '}
                {amount(query.data.quote.enterprise_value)}{' '}
                {query.data.quote.currency || 'currency unknown'}
              </p>
            </div>
          </div>
          {query.data.warnings.length > 0 && (
            <ul className="mt-4 space-y-2 text-xs leading-6 text-amber-100/80">
              {query.data.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          )}
          <h3 data-reading-anchor="quality" className="mb-3 mt-6 text-sm font-medium text-slate-200">
            Operating quality
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {query.data.quality.map((item, index) => (
              <Metric key={item.key} item={item} anchor={`quality-${index}`} />
            ))}
          </div>
          <h3 data-reading-anchor="ratios" className="mb-3 mt-6 flex items-center gap-2 text-sm font-medium text-slate-200">
            <ArrowDownUp className="h-4 w-4 text-sage-300" />
            Price relative to financials
          </h3>
          <div className="grid gap-3 sm:grid-cols-3">
            {query.data.valuation.map((item, index) => (
              <Metric key={item.key} item={item} anchor={`ratio-${index}`} />
            ))}
          </div>
          <p className="mt-4 text-[11px] leading-6 text-slate-500">
            {query.data.methodology.fcf} {query.data.methodology.ratios}
          </p>
          <Scenarios key={query.data.symbol} data={query.data} />
          <div className="mt-5 border-t border-white/[0.07] pt-4 text-[11px] leading-6 text-slate-500">
            <p>
              {query.data.source} · Fetched{' '}
              {valuationDate(query.data.fetched_at)} · Financials fetched{' '}
              {valuationDate(query.data.financials.fetched_at)}
            </p>
            <p>
              Financial currency: {query.data.financials.currency || 'Unknown'}{' '}
              · {query.data.financials.currency_basis}. Quote currency:{' '}
              {query.data.quote.raw_currency || 'Unknown'}. Ratios require
              matching supported currencies and recent inputs.
            </p>
            <p>{query.data.methodology.coverage}</p>
          </div>
        </>
      )}
    </ResearchPanel>
  )
}
