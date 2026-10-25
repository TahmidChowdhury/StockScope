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
  const [paused, setPaused] = useState(false)
  const callbacks = useRef({ onComplete, onError })
  callbacks.current = { onComplete, onError }

  useEffect(() => {
    if (!symbol || !isAnalyzing) {
      setIsPolling(false)
      setPaused(false)
      setStatus(null)
      return
    }
    let stopped = false
    let finished = false
    let inFlight = false
    let timer: ReturnType<typeof setTimeout> | undefined
    let failures = 0
    let controller: AbortController | undefined
    const available = () => !document.hidden && navigator.onLine !== false
    setStatus(null)

    const poll = async () => {
      if (stopped || finished || inFlight || !available()) return
      inFlight = true
      const request = new AbortController()
      controller = request
      try {
        const response = await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}/status`, { signal: request.signal })
        if (!response.ok) throw new ApiError(response.status === 404 ? 'Analysis status is unavailable. The server may have restarted; try again.' : 'Could not check analysis progress.', response.status)
        const next: AnalysisStatus = await response.json()
        if (stopped || request.signal.aborted) return
        failures = 0
        setStatus(next)
        if (next.status === 'completed' || next.status === 'partial') {
          finished = true
          setIsPolling(false)
          callbacks.current.onComplete?.(next)
          return
        }
        if (next.status === 'failed') {
          finished = true
          setIsPolling(false)
          callbacks.current.onError?.(next.message || 'Analysis failed')
          return
        }
      } catch (error) {
        if (stopped || request.signal.aborted || !available()) return
        failures += 1
        if ((error instanceof ApiError && error.status === 401) || failures >= 5) {
          finished = true
          setIsPolling(false)
          callbacks.current.onError?.(error instanceof Error ? error.message : 'Analysis status is unavailable')
          return
        }
      } finally {
        inFlight = false
        if (!stopped && !finished && available()) timer = setTimeout(poll, 2000)
      }
    }
    const resume = () => {
      if (stopped || finished) return
      if (timer) clearTimeout(timer)
      const canPoll = available()
      setIsPolling(canPoll)
      setPaused(!canPoll)
      if (canPoll) void poll()
      else controller?.abort()
    }
    document.addEventListener('visibilitychange', resume)
    window.addEventListener('online', resume)
    window.addEventListener('offline', resume)
    resume()
    return () => {
      stopped = true
      controller?.abort()
      if (timer) clearTimeout(timer)
      document.removeEventListener('visibilitychange', resume)
      window.removeEventListener('online', resume)
      window.removeEventListener('offline', resume)
    }
  }, [symbol, isAnalyzing])

  return {
    status,
    isPolling,
    progress: status?.progress ?? 0,
    message: paused ? 'Progress updates paused. Reconnect or return to the app to check the running research.' : status?.message || 'Waiting for analysis status...',
    currentPhase: status?.current_phase || 'Initializing',
  }
}
