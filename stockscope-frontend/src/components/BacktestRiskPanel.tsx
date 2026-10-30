'use client'

import AnimatedAccordion from '@/components/ui/AnimatedAccordion'

import { useQuery } from '@tanstack/react-query'
import { tradingRequest } from '@/lib/trading'

interface RiskReport {
  as_of: string
  sample_count: number
  metrics: {
    sharpe: number | null
    sortino: number | null
    annualized_volatility: number | null
    beta: number | null
    max_drawdown_duration_sessions: number | null
    max_drawdown_duration_calendar_days: number | null
  }
  coverage: { first_return_includes_initial_cash: boolean }
  method: {
    library: string
    library_version: string
    annual_risk_free_rate: number
    periods_per_year: number
    std_ddof: number
  }
  assumptions: string[]
}

const number = (value: number | null | undefined, suffix = '') =>
  value == null || !Number.isFinite(value)
    ? '—'
    : `${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}${suffix}`

export default function BacktestRiskPanel({
  runId,
  benchmark,
}: {
  runId: string
  benchmark: string
}) {
  const query = useQuery({
    queryKey: ['backtest-risk', runId],
    queryFn: () =>
      tradingRequest<RiskReport>(
        `/backtests/${encodeURIComponent(runId)}/risk`,
      ),
    staleTime: Infinity,
    retry: false,
  })

  return (
    <section
      className="surface min-w-0 p-4 sm:p-6"
      aria-label="Backtest risk profile"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Beyond total return</p>
          <h3 className="mt-2 text-lg font-semibold">Risk profile</h3>
          <p className="mt-2 text-xs leading-5 text-slate-400">
            Calculated from this experiment’s saved daily equity and benchmark
            observations.
          </p>
        </div>
        {query.isError && (
          <button
            className="button-secondary"
            onClick={() => void query.refetch()}
          >
            Retry risk report
          </button>
        )}
      </div>
      {query.isPending && (
        <p role="status" className="mt-4 text-sm text-slate-400">
          Calculating risk profile…
        </p>
      )}
      {query.isError && (
        <p role="alert" className="mt-4 text-sm text-amber-200">
          {query.error.message}
        </p>
      )}
      {query.data && (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {[
              [
                'Sharpe ratio',
                number(query.data.metrics.sharpe),
                'Return relative to total variability',
              ],
              [
                'Sortino ratio',
                number(query.data.metrics.sortino),
                'Return relative to downside variability',
              ],
              [
                'Annualized volatility',
                number(
                  query.data.metrics.annualized_volatility == null
                    ? null
                    : query.data.metrics.annualized_volatility * 100,
                  '%',
                ),
                'Daily standard deviation × √252',
              ],
              [
                `Beta vs. ${benchmark}`,
                number(query.data.metrics.beta),
                'Historical sensitivity to the benchmark',
              ],
              [
                'Longest drawdown',
                number(
                  query.data.metrics.max_drawdown_duration_sessions,
                  ' sessions',
                ),
                'Consecutive observed sessions below a prior peak',
              ],
              [
                'Drawdown duration',
                number(
                  query.data.metrics.max_drawdown_duration_calendar_days,
                  ' days',
                ),
                'Longest elapsed calendar time below a prior peak',
              ],
            ].map(([label, value, description]) => (
              <div
                key={label}
                className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4"
              >
                <div className="text-xs text-slate-400">{label}</div>
                <div className="mt-2 text-xl font-semibold text-slate-100">
                  {value}
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-500">
                  {description}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-400">
            {query.data.sample_count} return periods through {query.data.as_of}{' '}
            · Annualization: {query.data.method.periods_per_year} sessions ·
            Risk-free rate:{' '}
            {number(query.data.method.annual_risk_free_rate * 100, '%')} ·{' '}
            {query.data.method.library} {query.data.method.library_version}
          </p>
          <AnimatedAccordion className="mt-3 text-xs leading-6 text-slate-400" triggerClassName="text-slate-300" title="Risk methodology">
            <ul className="mt-3 list-disc space-y-1 pl-5">
              {query.data.assumptions.map((assumption) => (
                <li key={assumption}>{assumption}</li>
              ))}
            </ul>
          </AnimatedAccordion>
        </>
      )}
    </section>
  )
}
