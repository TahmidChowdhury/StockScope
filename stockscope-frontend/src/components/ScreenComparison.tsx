'use client'

import { useState } from 'react'
import { Description, Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { X } from 'lucide-react'
import { amount, percent, ratio, revenueAmount, comparisonCurrencyNotice } from '@/lib/financial-format'
import { snapshotTime } from '@/lib/research-workflow'
import type { FundamentalsTTM } from '@/types'

type ScreenMetric = {
  key: keyof FundamentalsTTM
  label: string
  format: (value?: number | null) => string
}

export const screenMetrics: ScreenMetric[] = [
  { key: 'revenue_ttm', label: 'Revenue · TTM', format: amount },
  { key: 'revenue_growth_yoy', label: 'Revenue growth', format: percent },
  { key: 'fcf_margin_ttm', label: 'FCF margin', format: percent },
  { key: 'fcf_growth_yoy', label: 'FCF growth', format: percent },
  { key: 'operating_margin_ttm', label: 'Operating margin', format: percent },
  { key: 'ebitda_growth_yoy', label: 'EBITDA growth', format: percent },
  { key: 'debt_to_cash', label: 'Debt / cash', format: ratio },
]

export function ScreenMetricValue({ company, metric }: { company: FundamentalsTTM; metric: ScreenMetric }) {
  const value = company[metric.key]
  const basis = company.growth_metadata?.[metric.key]
  return <>
    {metric.key === 'revenue_ttm' ? revenueAmount(typeof value === 'number' ? value : null, company.reporting_currency) : metric.format(typeof value === 'number' ? value : null)}
    {basis && (
      <span className="mt-1 block text-[10px] text-slate-500">
        {basis.status === 'available' ? (basis.basis === 'fiscal_year' ? 'Fiscal year' : 'TTM') : 'Unavailable'}
      </span>
    )}
  </>
}

export default function ScreenComparison({ companies, capturedAt }: { companies: FundamentalsTTM[]; capturedAt?: string }) {
  const [open, setOpen] = useState(false)
  return <>
    <button type="button" disabled={companies.length < 2} aria-haspopup="dialog"
      onClick={() => setOpen(true)} className="button-secondary disabled:opacity-40">
      Compare selected ({companies.length})
    </button>
    <Dialog open={open} onClose={() => setOpen(false)} className="fixed inset-0 z-[60]">
      <div className="fixed inset-0 bg-black/75" aria-hidden="true" />
      <div className="fixed inset-0 grid place-items-center overflow-y-auto p-3 sm:p-6">
        <DialogPanel className="surface max-h-[90dvh] w-full min-w-0 max-w-3xl overflow-y-auto p-4 sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <DialogTitle className="text-lg font-semibold">Selected companies</DialogTitle>
              <Description className="mt-1 text-xs leading-5 text-slate-400">
                {capturedAt && `Screen saved ${snapshotTime(capturedAt)}. `}Missing values appear as —.
              </Description>
            </div>
            <button type="button" aria-label="Close comparison" onClick={() => setOpen(false)}
              className="button-secondary h-11 w-11 shrink-0 !p-0"><X className="h-4 w-4" /></button>
          </div>
          <div role="region" aria-label="Selected financial metrics" tabIndex={0} className="mt-4 overflow-x-auto rounded-lg border border-white/10">
            <table className="w-full text-right text-xs tabular-nums">
              <thead><tr className="border-b border-white/10">
                <th scope="col" className="sticky left-0 bg-[#191e1b] p-3 text-left font-medium text-slate-400">Metric</th>
                {companies.map(company => <th key={company.ticker} scope="col" className="px-3 py-3">{company.ticker}</th>)}
              </tr></thead>
              <tbody>{screenMetrics.map(metric => (
                <tr key={metric.key} className="border-b border-white/[0.06] last:border-0">
                  <th scope="row" className="sticky left-0 min-w-24 bg-[#191e1b] p-3 text-left font-normal text-slate-300">{metric.label}</th>
                  {companies.map(company => (
                    <td key={company.ticker} className="min-w-20 p-3"><ScreenMetricValue company={company} metric={metric} /></td>
                  ))}
                </tr>
              ))}</tbody>
            </table>
          </div>
          <p className="mt-3 text-xs leading-5 text-slate-400">{comparisonCurrencyNotice(companies)}</p>
        </DialogPanel>
      </div>
    </Dialog>
  </>
}
