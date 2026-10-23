import Link from 'next/link'
import AppShell from '@/components/AppShell'

export default function SavedResearchNotFound() {
  return <AppShell>
    <div className="surface p-6 sm:p-8">
      <p className="eyebrow">404 · Saved research</p>
      <h1 className="page-title mt-3">This research link is invalid</h1>
      <p className="mt-3 text-sm text-slate-400">Open a saved experiment or paper portfolio from the workspace.</p>
      <Link className="button-primary mt-6 inline-flex" href="/trading?tab=backtest">Open saved experiments</Link>
    </div>
  </AppShell>
}
