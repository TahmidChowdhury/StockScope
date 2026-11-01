import type { ReactNode } from 'react'

export function Skeleton({ className = '' }: { className?: string }) {
  return <span aria-hidden="true" className={`block rounded bg-white/[0.055] motion-safe:animate-pulse ${className}`} />
}

function Tiles({ count, grid, anchor, children }: { count: number; grid: string; anchor?: string; children: ReactNode }) {
  return <div className={grid}>{Array.from({ length: count }, (_, index) =>
    <div key={index} data-reading-anchor={anchor && `${anchor}-${index}`} className="rounded-xl border border-white/[0.07] p-4">{children}</div>,
  )}</div>
}

export function SentimentLoading() {
  return <section role="status" aria-label="Loading sentiment" className="space-y-6 rounded-2xl border border-white/10 bg-[#16161e] p-4 sm:p-6">
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
