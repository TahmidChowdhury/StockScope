import { useState, useEffect, useCallback, useRef } from 'react'

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
  // Smoothed client-side progress that interpolates toward real backend value
  const [displayProgress, setDisplayProgress] = useState(0)
  const displayRef = useRef(0)
  const rafRef = useRef<number>(0)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const getPasswordParam = useCallback(() => {
    const password = localStorage.getItem('stockscope_password')
    return password ? `?password=${encodeURIComponent(password)}` : ''
  }, [])

  // Animate displayProgress toward a target value
  const animateTo = useCallback((target: number) => {
    cancelAnimationFrame(rafRef.current)
    const step = () => {
      const diff = target - displayRef.current
      if (Math.abs(diff) < 0.3) {
        displayRef.current = target
        setDisplayProgress(target)
        return
      }
      displayRef.current += diff * 0.04
      setDisplayProgress(Math.round(displayRef.current * 10) / 10)
      rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
  }, [])

  // While analyzing but waiting for backend to report, creep progress slowly
  // so the ring always moves. Caps at 85% so the real completion jump to 100 is visible.
  useEffect(() => {
    if (!isAnalyzing) {
      displayRef.current = 0
      setDisplayProgress(0)
      return
    }
    const realProgress = status?.progress ?? 0
    // If backend has reported progress, shoot straight there (capped at 95 until complete)
    const backendTarget = status?.status === 'completed' ? 100 : Math.min(realProgress, 95)

    // If we're already ahead of or at backend target, keep creeping slowly up to 85
    if (displayRef.current >= backendTarget && displayRef.current < 85) {
      const creep = setInterval(() => {
        const next = Math.min(displayRef.current + 0.4, 85)
        animateTo(next)
      }, 500)
      return () => clearInterval(creep)
    }

    // Otherwise animate to wherever the backend says
    animateTo(backendTarget)
  }, [isAnalyzing, status, animateTo])

  // Cleanup RAF on unmount
  useEffect(() => () => cancelAnimationFrame(rafRef.current), [])

  const pollStatus = useCallback(async () => {
    if (!symbol || !isAnalyzing) return

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

      if (data.status === 'completed') {
        setIsPolling(false)
        animateTo(100)
        // Small delay so user sees 100% before transition
        setTimeout(() => onComplete?.(), 600)
      } else if (data.status === 'error' || data.status === 'failed') {
        setIsPolling(false)
        onError?.(data.message || 'Analysis failed')
      }
    } catch (error) {
      console.error('Error polling status:', error)
      if (error instanceof Error && error.message.includes('Authentication')) {
        setIsPolling(false)
        onError?.(error.message)
      }
    }
  }, [symbol, isAnalyzing, API_BASE_URL, getPasswordParam, onComplete, onError, animateTo])

  useEffect(() => {
    if (isAnalyzing && symbol && !isPolling) {
      setIsPolling(true)
      pollStatus()
    } else if (!isAnalyzing) {
      setIsPolling(false)
      setStatus(null)
    }
  }, [isAnalyzing, symbol, isPolling, pollStatus])

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    if (isPolling) {
      interval = setInterval(pollStatus, 2000)
    }
    return () => { if (interval) clearInterval(interval) }
  }, [isPolling, pollStatus])

  return {
    status,
    isPolling,
    progress: displayProgress,
    message: status?.message || 'Starting analysis...',
    currentPhase: status?.current_phase || 'Initializing'
  }
}