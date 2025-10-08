'use client'

import { useState, useEffect } from 'react'

interface LoadingScreenProps {
  message?: string
  progress?: number
  details?: string
  className?: string
}

export default function LoadingScreen({ 
  message = "Loading...", 
  progress, 
  details,
  className = "" 
}: LoadingScreenProps) {
  const [dots, setDots] = useState("")

  // Animated dots effect
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? "" : prev + ".")
    }, 500)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className={`min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center px-4 ${className}`}>
      <div className="text-center max-w-md w-full">
        {/* Animated spinner */}
        <div className="relative mb-8">
          <div className="h-16 w-16 mx-auto">
            <div className="absolute inset-0 rounded-full border-4 border-white/20"></div>
            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-purple-400 animate-spin"></div>
            <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-white animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
          </div>
        </div>

        {/* Main message */}
        <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">
          {message}{dots}
        </h2>

        {/* Progress bar if provided */}
        {typeof progress === 'number' && (
          <div className="w-full mb-4">
            <div className="flex items-center justify-between text-sm text-gray-300 mb-2">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-purple-500 to-purple-400 h-2 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${Math.min(progress, 100)}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Details text */}
        {details && (
          <p className="text-gray-300 text-sm leading-relaxed">
            {details}
          </p>
        )}

        {/* Phase indicators */}
        <div className="mt-6 flex justify-center space-x-2">
          {[1, 2, 3].map((phase, index) => {
            const isActive = progress ? progress > (index * 33.33) : false
            const isCurrent = progress ? (progress >= (index * 33.33) && progress < ((index + 1) * 33.33)) : false
            
            return (
              <div
                key={phase}
                className={`w-2 h-2 rounded-full transition-all duration-300 ${
                  isActive 
                    ? 'bg-purple-400' 
                    : isCurrent 
                      ? 'bg-purple-400 animate-pulse' 
                      : 'bg-slate-600'
                }`}
              />
            )
          })}
        </div>
      </div>
    </div>
  )
}