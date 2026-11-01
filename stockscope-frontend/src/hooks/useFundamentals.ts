import { apiFetch, readApiJson } from '@/lib/api'
import { useQuery, useMutation } from '@tanstack/react-query'
import { 
  FundamentalsResponse, 
  ScreenerRequest, 
  ScreenerResponse 
} from '@/types'



// Fundamentals API hooks
export const useFundamentals = (ticker: string) => {
  return useQuery({
    queryKey: ['fundamentals', ticker],
    queryFn: async ({ signal }): Promise<FundamentalsResponse> => {
      const response = await apiFetch(
        `/api/fundamentals/${encodeURIComponent(ticker)}`,
        { signal },
      )
      
      return readApiJson<FundamentalsResponse>(response, `Couldn’t load financials for ${ticker}. Try again later.`)
    },
    enabled: !!ticker && ticker.length > 0,
    staleTime: 6 * 60 * 60_000,
    refetchOnWindowFocus: false,
    retry: false
  })
}

export const useScreener = () => {
  return useMutation({
    mutationFn: async (request: ScreenerRequest): Promise<ScreenerResponse> => {
      const response = await apiFetch(
        `/api/fundamentals/screener`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request)
        }
      )
      
      return readApiJson<ScreenerResponse>(response, 'The screen could not finish.')
    }
  })
}
