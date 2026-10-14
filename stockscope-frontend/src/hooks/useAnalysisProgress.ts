import { useState, useEffect, useRef } from 'react'
import { apiFetch, ApiError } from '@/lib/api'

export interface AnalysisStatus {
  symbol: string
  status: 'pending' | 'processing' | 'completed' | 'partial' | 'failed'
  progress: number
  message: string
  started_at?: string
  estimated_completion?: string
  current_phase?: string
}

interface UseAnalysisProgressProps {
  symbol?: string
  isAnalyzing: boolean
  onComplete?: (status: AnalysisStatus) => void
  onError?: (error: string) => void
}

export function useAnalysisProgress({ symbol, isAnalyzing, onComplete, onError }: UseAnalysisProgressProps) {
  const [status, setStatus] = useState<AnalysisStatus | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const callbacks = useRef({ onComplete, onError })
  callbacks.current = { onComplete, onError }

  useEffect(() => {
    if (!symbol || !isAnalyzing) {
      setIsPolling(false)
      setStatus(null)
      return
    }
    let stopped = false
    let timer: ReturnType<typeof setTimeout> | undefined
    let failures = 0
    const controller = new AbortController()
    setIsPolling(true)
    setStatus(null)

    const poll = async () => {
      try {
        const response = await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}/status`, { signal: controller.signal })
        if (!response.ok) throw new ApiError(response.status === 404 ? 'Analysis status is unavailable. The server may have restarted; try again.' : 'Could not check analysis progress.', response.status)
        const next: AnalysisStatus = await response.json()
        if (stopped) return
        failures = 0
        setStatus(next)
        if (next.status === 'completed' || next.status === 'partial') {
          setIsPolling(false)
          callbacks.current.onComplete?.(next)
          return
        }
        if (next.status === 'failed') {
          setIsPolling(false)
          callbacks.current.onError?.(next.message || 'Analysis failed')
          return
        }
      } catch (error) {
        if (stopped) return
        failures += 1
        if ((error instanceof ApiError && error.status === 401) || failures >= 5) {
          setIsPolling(false)
          callbacks.current.onError?.(error instanceof Error ? error.message : 'Analysis status is unavailable')
          return
        }
      }
      if (!stopped) timer = setTimeout(poll, 2000)
    }
    void poll()
    return () => {
      stopped = true
      controller.abort()
      if (timer) clearTimeout(timer)
    }
  }, [symbol, isAnalyzing])

  return {
    status,
    isPolling,
    progress: status?.progress ?? 0,
    message: status?.message || 'Waiting for analysis status...',
    currentPhase: status?.current_phase || 'Initializing',
  }
}
