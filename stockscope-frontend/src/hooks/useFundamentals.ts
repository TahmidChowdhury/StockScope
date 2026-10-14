import { apiFetch, ApiError } from '@/lib/api'
import { useQuery, useMutation } from '@tanstack/react-query'
import { 
  FundamentalsResponse, 
  FundamentalsTTM, 
  CompareRequest, 
  ScreenerRequest, 
  ScreenerResponse 
} from '@/types'



// Fundamentals API hooks
export const useFundamentals = (ticker: string) => {
  return useQuery({
    queryKey: ['fundamentals', ticker],
    queryFn: async (): Promise<FundamentalsResponse> => {
      const response = await apiFetch(
        `/api/fundamentals/${ticker}`
      )
      
      if (!response.ok) {
        throw new Error(`Failed to fetch fundamentals for ${ticker}`)
      }
      
      return response.json()
    },
    enabled: !!ticker && ticker.length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (count, error) => !(error instanceof ApiError && error.status === 401) && count < 2
  })
}

export const useCompare = () => {
  return useMutation({
    mutationFn: async (request: CompareRequest): Promise<FundamentalsTTM[]> => {
      const response = await apiFetch(
        `/api/fundamentals/compare`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request)
        }
      )
      
      if (!response.ok) {
        throw new Error('Failed to compare fundamentals')
      }
      
      return response.json()
    }
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
      
      if (!response.ok) {
        throw new Error('Failed to run screener')
      }
      
      return response.json()
    }
  })
}