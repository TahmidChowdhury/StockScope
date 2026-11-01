import type { ReactNode } from 'react'

export function Skeleton({ className = '' }: { className?: string }) {
  return <span aria-hidden="true" className={`block rounded bg-white/[0.055] motion-safe:animate-pulse ${className}`} />
}

export function LoadingRows({ label }: { label: string }) {
  return <div role="status" className="space-y-3">
    <span className="sr-only">{label}</span>
    {[0, 1, 2].map(row => <div key={row} aria-hidden="true" className="rounded-lg border border-white/[0.07] p-4">
      <Skeleton className="h-3 w-1/3" />
      <Skeleton className="mt-3 h-2.5 w-2/3" />
    </div>)}
  </div>
}

function Tiles({ count, grid, anchor, children }: { count: number; grid: string; anchor?: string; children: ReactNode }) {
  return <div className={grid}>{Array.from({ length: count }, (_, index) =>
    <div key={index} data-reading-anchor={anchor && `${anchor}-${index}`} className="rounded-xl border border-white/[0.07] p-4">{children}</div>,
  )}</div>
}

export function ValuationLoading() {
  const metric = <>
    <Skeleton className="h-3 w-3/5" />
    <Skeleton className="my-4 h-7 w-20 max-w-full" />
    <Skeleton className="h-3 w-4/5" />
  </>
  return <div role="status">
    <span className="sr-only">Loading valuation evidence…</span>
    <div aria-hidden="true">
      <Skeleton className="mt-6 h-28 sm:h-[70px]" />
      <h3 data-reading-anchor="quality" className="mb-3 mt-6 text-sm font-medium text-slate-200">Operating quality</h3>
      <Tiles count={5} anchor="quality" grid="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{metric}</Tiles>
      <h3 data-reading-anchor="ratios" className="mb-3 mt-6 text-sm font-medium text-slate-200">Price relative to financials</h3>
      <Tiles count={3} anchor="ratio" grid="grid gap-3 sm:grid-cols-3">{metric}</Tiles>
      <Skeleton className="mt-4 h-16" />
      <div data-reading-anchor="scenarios" className="mt-6 rounded-2xl border border-white/[0.07] p-5 sm:p-6">
        <h3 className="text-sm font-semibold text-slate-300">Your equity cash-flow scenarios</h3>
        <Skeleton className="mt-4 h-20" />
        <div className="my-5 grid gap-4 sm:grid-cols-2"><Skeleton className="h-20" /><Skeleton className="h-20" /></div>
        <Tiles count={3} anchor="scenario" grid="grid gap-3 lg:grid-cols-3">
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="my-5 h-16" />
          <Skeleton className="mb-4 h-12 w-4/5" />
        </Tiles>
        <Skeleton className="mt-4 h-16" />
      </div>
      <Skeleton className="mt-5 h-20" />
    </div>
  </div>
}

export function FinancialsLoading({ ticker }: { ticker: string }) {
  return <div role="status">
    <span className="sr-only">Loading {ticker} fundamentals…</span>
    <div aria-hidden="true">
      <Skeleton className="mb-6 h-4 w-28" />
      <h1 className="page-title">{ticker} fundamentals</h1>
      <Skeleton className="mb-8 mt-3 h-5 w-2/3" />
      <Skeleton className="mb-6 h-48" />
      <Tiles count={4} grid="mb-8 grid gap-4 sm:grid-cols-2 2xl:grid-cols-4">
        <Skeleton className="h-4 w-1/2" /><Skeleton className="mt-4 h-8 w-1/3" />
      </Tiles>
      <Tiles count={4} anchor="chart" grid="grid gap-6 lg:grid-cols-2">
        <Skeleton className="mb-4 h-6 w-1/2" /><Skeleton className="h-80" />
      </Tiles>
      <Skeleton className="mt-8 h-32" />
    </div>
  </div>
}

export function SentimentLoading() {
  return <section role="status" aria-label="Loading sentiment" className="space-y-6 rounded-2xl border border-white/10 bg-[#191e1b] p-4 sm:p-6">
    <span className="sr-only">Loading saved headlines and sentiment models…</span>
    <div aria-hidden="true" className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="w-full max-w-2xl space-y-3"><Skeleton className="h-3 w-32" /><Skeleton className="h-7 w-48" /><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-4/5" /></div>
        <Skeleton className="h-10 w-36" />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3"><Skeleton className="h-3 w-64 max-w-full" /><Skeleton className="h-9 w-44" /></div>
      <Tiles count={3} grid="grid gap-3 sm:grid-cols-3">
        <Skeleton className="h-3 w-3/5" /><Skeleton className="my-3 h-7 w-20" /><Skeleton className="h-3 w-full" /><Skeleton className="mt-2 h-3 w-4/5" />
      </Tiles>
      <Tiles count={3} grid="grid gap-3 sm:grid-cols-3">
        <Skeleton className="h-5 w-2/3" /><Skeleton className="my-4 h-6 w-24" /><Skeleton className="h-3 w-full" /><Skeleton className="mt-2 h-3 w-3/4" /><Skeleton className="mt-5 h-3 w-1/2" />
      </Tiles>
      <div className="flex flex-wrap gap-2"><Skeleton className="h-10 w-44" /><Skeleton className="h-10 w-36" /></div>
      <div className="divide-y divide-white/[0.07] rounded-xl border border-white/[0.07]">
        {[0, 1, 2].map(row => <div key={row} className="space-y-3 p-4"><Skeleton className="h-4 w-4/5" /><Skeleton className="h-3 w-1/2" /><div className="flex gap-4"><Skeleton className="h-6 w-16" /><Skeleton className="h-6 w-16" /><Skeleton className="h-6 w-16" /></div></div>)}
      </div>
    </div>
  </section>
}
