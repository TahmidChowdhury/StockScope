'use client'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { apiFetch, getAuthSession } from '@/lib/api'
export type PersonalList = { id: string; name: string; items: { symbol: string; pinned: boolean }[] }
export async function workspaceRequest(path: string, method = 'GET', body?: unknown) {
  const response = await apiFetch(path, { method, ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) })
  const result = await response.json()
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'The change could not be saved.')
  return result
}
export function useLists() {
  return useQuery<PersonalList[]>({ queryKey: ['personal-lists'], queryFn: () => workspaceRequest('/api/lists'), enabled: !!getAuthSession()?.user, staleTime: 60_000 })
}
export function useListAction() {
  const client = useQueryClient()
  return useMutation({ mutationFn: ({ path, method, body }: { path: string; method: string; body?: unknown }) => workspaceRequest(path, method, body), onSuccess: () => client.invalidateQueries({ queryKey: ['personal-lists'] }) })
}
