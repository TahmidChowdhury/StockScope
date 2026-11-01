'use client'

import { useCallback, useEffect, useState, useSyncExternalStore } from 'react'
import { QueryClient, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'
import { scheduleDeadline } from '@/lib/price-cooldown'

// All ranges share the provider cooldown. Read error deadlines from the query
// cache so switching ranges or remounting cannot bypass an outstanding limit.
const cooldownKey = ['price-history-cooldown'] as const

export function rememberPriceCooldown(client: QueryClient, error: unknown) {
  if (!(error instanceof ApiError) || error.status !== 429 || error.retryAt === null) return
  // One small record survives range-query garbage collection; auth changes clear it.
  client.setQueryDefaults(cooldownKey, { gcTime: Infinity })
  client.setQueryData<number>(cooldownKey, previous => Math.max(previous ?? 0, error.retryAt!))
}

export function priceCooldownDeadline(client: QueryClient): number {
  return client.getQueryCache().findAll({ queryKey: ['price-history'] }).reduce((latest, query) => {
    const error = query.state.error
    return error instanceof ApiError && error.status === 429
      ? Math.max(latest, error.retryAt ?? 0) : latest
  }, client.getQueryData<number>(cooldownKey) ?? 0)
}

export function usePriceCooldown() {
  const client = useQueryClient()
  const subscribe = useCallback((notify: () => void) => client.getQueryCache().subscribe(notify), [client])
  const snapshot = useCallback(() => priceCooldownDeadline(client), [client])
  const deadline = useSyncExternalStore(subscribe, snapshot, () => 0)
  const [, tick] = useState(0)
  useEffect(() => {
    if (deadline > Date.now()) return scheduleDeadline(deadline, () => tick(value => value + 1))
  }, [deadline])
  return { deadline, cooling: deadline > Date.now() }
}
