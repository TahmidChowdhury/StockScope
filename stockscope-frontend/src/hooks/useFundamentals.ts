import { useQuery, useMutation } from '@tanstack/react-query'
import { 
  FundamentalsResponse, 
  FundamentalsTTM, 
  CompareRequest, 
  ScreenerRequest, 
  ScreenerResponse 
} from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Get the password from localStorage for API calls
const getPassword = () => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('stockscope_password') || ''
  }
  return ''
}

// Fundamentals API hooks
export const useFundamentals = (ticker: string) => {
  return useQuery({
    queryKey: ['fundamentals', ticker],
    queryFn: async (): Promise<FundamentalsResponse> => {
      const password = getPassword()
      const response = await fetch(
        `${API_BASE}/api/fundamentals/${ticker}?password=${encodeURIComponent(password)}`
      )
      
      if (!response.ok) {
        throw new Error(`Failed to fetch fundamentals for ${ticker}`)
      }
      
      return response.json()
    },
    enabled: !!ticker && ticker.length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2
  })
}

export const useCompare = () => {
  return useMutation({
    mutationFn: async (request: CompareRequest): Promise<FundamentalsTTM[]> => {
      const password = getPassword()
      const response = await fetch(
        `${API_BASE}/api/fundamentals/compare?password=${encodeURIComponent(password)}`,
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
      const password = getPassword()
      const response = await fetch(
        `${API_BASE}/api/fundamentals/screener?password=${encodeURIComponent(password)}`,
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