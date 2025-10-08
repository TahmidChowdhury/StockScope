import { useState, useEffect, useCallback } from 'react'

interface AnalysisStatus {
  symbol: string
  status: 'pending' | 'running' | 'completed' | 'error'
  progress: number
  message: string
  started_at?: string
  estimated_completion?: string
  current_phase?: string
}

interface UseAnalysisProgressProps {
  symbol?: string
  isAnalyzing: boolean
  onComplete?: () => void
  onError?: (error: string) => void
}

export function useAnalysisProgress({ 
  symbol, 
  isAnalyzing, 
  onComplete, 
  onError 
}: UseAnalysisProgressProps) {
  const [status, setStatus] = useState<AnalysisStatus | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const getPasswordParam = useCallback(() => {
    const password = localStorage.getItem('stockscope_password')
    return password ? `?password=${encodeURIComponent(password)}` : ''
  }, [])

  const pollStatus = useCallback(async () => {
    if (!symbol || !isAnalyzing) return

    // Check if user is authenticated before making the request
    const passwordParam = getPasswordParam()
    if (!passwordParam) {
      console.warn('No authentication found, skipping status poll')
      onError?.('Authentication required')
      return
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}/status${passwordParam}`)
      
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          throw new Error('Authentication failed')
        } else if (response.status === 404) {
          throw new Error('Analysis not found')
        } else {
          throw new Error(`Server error: ${response.status}`)
        }
      }

      const data = await response.json()
      setStatus(data)

      // Check if analysis is complete
      if (data.status === 'completed') {
        setIsPolling(false)
        onComplete?.()
      } else if (data.status === 'error') {
        setIsPolling(false)
        onError?.(data.message || 'Analysis failed')
      }
    } catch (error) {
      console.error('Error polling status:', error)
      // For auth errors, stop polling and notify user
      if (error instanceof Error && error.message.includes('Authentication')) {
        setIsPolling(false)
        onError?.(error.message)
      }
      // For other errors, continue polling (might be temporary network issues)
    }
  }, [symbol, isAnalyzing, API_BASE_URL, getPasswordParam, onComplete, onError])

  // Start polling when analysis begins
  useEffect(() => {
    if (isAnalyzing && symbol && !isPolling) {
      setIsPolling(true)
      pollStatus() // Initial call
    } else if (!isAnalyzing) {
      setIsPolling(false)
      setStatus(null)
    }
  }, [isAnalyzing, symbol, isPolling, pollStatus])

  // Poll every 2 seconds while analyzing
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null

    if (isPolling) {
      interval = setInterval(pollStatus, 2000)
    }

    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [isPolling, pollStatus])

  return {
    status,
    isPolling,
    progress: status?.progress || 0,
    message: status?.message || 'Starting analysis...',
    currentPhase: status?.current_phase || 'Initializing'
  }
}