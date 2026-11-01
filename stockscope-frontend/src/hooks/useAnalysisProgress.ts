'use client'

import { useEffect, useState } from 'react'
import { useIsMutating, useMutation, useMutationState, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, ApiError, readApiJson } from '@/lib/api'
import { collectionActive, collectionOutcome, readCollectionJob } from '@/lib/collection'
import { scheduleDeadline } from '@/lib/price-cooldown'

export function useAnalysisProgress(symbol: string) {
  const client = useQueryClient()
  const key = ['collection-status', symbol]
  const mutationKey = ['collection-start', symbol]
  const starting = useIsMutating({ mutationKey }) > 0
  const errors = useMutationState({ filters: { mutationKey }, select: mutation => mutation.state.error })
  const startError = errors.at(-1)
  const query = useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const previousError = client.getQueryData<ApiError>(['collection-status-cooldown', symbol])
      if (previousError instanceof ApiError && previousError.status === 429 && (previousError.retryAt ?? 0) > Date.now()) throw previousError
      const response = await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}/status`, { signal })
      if (response.status === 404) return null // No run tracked, never inferred success.
      try {
        return readCollectionJob(await readApiJson(response, 'Collection status could not be checked.'), symbol)
      } catch (error) {
        if (error instanceof ApiError && error.status === 429 && error.retryAt !== null) {
          client.setQueryDefaults(['collection-status-cooldown', symbol], { gcTime: Infinity })
          client.setQueryData(['collection-status-cooldown', symbol], error)
        }
        throw error
      }
    },
    staleTime: 0, retry: false, refetchOnMount: 'always', refetchOnWindowFocus: query => !query.state.error, refetchOnReconnect: query => !query.state.error,
    refetchInterval: query => query.state.error ? false : collectionActive(query.state.data) ? 1500 : false,
    refetchIntervalInBackground: false,
  })
  const mutation = useMutation({
    mutationKey,
    onMutate: () => client.cancelQueries({ queryKey: key }),
    mutationFn: async () => readCollectionJob(await readApiJson(await apiFetch('/api/stocks/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, sources: ['news', 'sec_facts'] }),
      // Starting a backend run is not tied to this tab's AbortSignal.
    }), 'Could not start collection. Check status before trying again.'), symbol),
    onSuccess: async job => {
      await client.cancelQueries({ queryKey: key })
      client.setQueryData(key, job)
    },
    onSettled: () => client.invalidateQueries({ queryKey: key }),
    retry: false,
  })
  const outcome = collectionOutcome(query.data)
  useEffect(() => {
    if (!outcome || query.isError) return
    const appliedKey = ['collection-applied', symbol]
    if (client.getQueryData(appliedKey) === outcome) return
    client.setQueryData(appliedKey, outcome)
    void Promise.all([
      client.invalidateQueries({ queryKey: ['research-summary', symbol] }),
      client.invalidateQueries({ queryKey: ['saved-news', symbol] }),
      client.invalidateQueries({ queryKey: ['watchlist'] }),
    ])
    // SEC evidence and tone panels read saved data afresh when mounted.
  }, [client, outcome, query.isError, symbol])
  const retryAt = Math.max(...[startError, query.error].map(error => error instanceof ApiError && error.status === 429 ? error.retryAt ?? 0 : 0))
  const [, tick] = useState(0)
  useEffect(() => {
    if (retryAt > Date.now()) return scheduleDeadline(retryAt, () => tick(value => value + 1))
  }, [retryAt])
  const cooling = retryAt > Date.now()
  return {
    ...query, starting, startError, cooling, active: collectionActive(query.data),
    start: () => {
      if (client.isMutating({ mutationKey }) || collectionActive(query.data) || query.isPending || query.isFetching || query.isError || cooling) return
      mutation.mutate()
    },
  }
}
