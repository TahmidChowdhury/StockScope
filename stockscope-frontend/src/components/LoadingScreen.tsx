'use client'

interface LoadingScreenProps {
  message?: string
  symbol?: string
  // kept for API compatibility
  progress?: number
  details?: string
  className?: string
}

export default function LoadingScreen({
  message = 'Analyzing...',
  symbol,
}: LoadingScreenProps) {
  return (
    <div className="fixed inset-0 z-[60] flex flex-col items-center justify-center bg-slate-950/95 backdrop-blur-md">
      <div className="flex flex-col items-center gap-5">
        {/* Spinner */}
        <div className="relative w-14 h-14">
          <div className="absolute inset-0 rounded-full border-4 border-white/8" />
          <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-purple-400 animate-spin" />
        </div>

        {symbol && (
          <span className="font-mono font-bold text-white text-xl tracking-widest">{symbol}</span>
        )}

        <p className="text-white/60 text-sm">{message}</p>
      </div>

      {/* bottom safe-area for mobile tab bar */}
      <div className="h-16 lg:h-0" />
    </div>
  )
}
