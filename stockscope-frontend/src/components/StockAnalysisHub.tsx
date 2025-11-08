'use client'

import { useState, useEffect } from 'react'
import { ArrowLeftIcon, ChartBarIcon, NewspaperIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import StockDashboard from './StockDashboard'
import PriceChart from './PriceChart'
import NewsComponent from './NewsComponent'
import KeyMetricsComponent from './KeyMetrics'
import StockSearch from './StockSearch'

interface StockAnalysisHubProps {
  symbol: string
  onBack: () => void
  onStockSelect?: (symbol: string) => void
}

type ViewMode = 'charts' | 'analysis'

export default function StockAnalysisHub({ symbol, onBack, onStockSelect }: StockAnalysisHubProps) {
  const [activeView, setActiveView] = useState<ViewMode>('charts') // Start with charts & news
  const [showStockSwitcher, setShowStockSwitcher] = useState(false)
  const [isTransitioning, setIsTransitioning] = useState(false)

  // Handle view switching with transition
  const handleViewChange = (newView: ViewMode) => {
    if (newView === activeView) return
    
    setIsTransitioning(true)
    setTimeout(() => {
      setActiveView(newView)
      setIsTransitioning(false)
    }, 150) // Quick transition
  }

  // Handle stock switching
  const handleStockSwitch = (newSymbol: string) => {
    setShowStockSwitcher(false)
    if (onStockSelect) {
      onStockSelect(newSymbol)
    }
  }

  if (showStockSwitcher) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="bg-slate-800/50 backdrop-blur-sm border-b border-purple-500/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <button 
                onClick={() => setShowStockSwitcher(false)}
                className="flex items-center space-x-2 text-gray-300 hover:text-white transition-colors"
              >
                <ArrowLeftIcon className="h-5 w-5" />
                <span>Back to {symbol}</span>
              </button>
              <h1 className="text-xl font-bold text-white">Switch Stock</h1>
              <div className="w-24"></div>
            </div>
          </div>
        </div>
        <div className="max-w-4xl mx-auto p-8">
          <StockSearch
            onAnalyze={handleStockSwitch}
            isLoading={false}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Navigation Header */}
      <div className="bg-slate-800/50 backdrop-blur-sm border-b border-purple-500/20 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 xl:px-8">
          <div className="flex items-center justify-between h-14 sm:h-16">
            {/* Left side - Back button and symbol */}
            <div className="flex items-center space-x-2 sm:space-x-4 min-w-0 flex-shrink">
              <button 
                onClick={onBack}
                className="flex items-center space-x-1 sm:space-x-2 text-gray-300 hover:text-white transition-colors"
              >
                <ArrowLeftIcon className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="hidden sm:inline">Back to Search</span>
              </button>
              <div className="h-4 w-px bg-gray-600 hidden sm:block"></div>
              <h1 className="text-lg sm:text-2xl font-bold text-white truncate">{symbol}</h1>
            </div>
            
            {/* Center - View Toggle Tabs */}
            <div className="flex items-center bg-slate-700/50 rounded-lg p-0.5 sm:p-1 mx-2">
              <button
                onClick={() => handleViewChange('charts')}
                className={`px-2 sm:px-4 py-1.5 sm:py-2 rounded-md text-xs sm:text-sm font-medium transition-all flex items-center gap-1 sm:gap-2 ${
                  activeView === 'charts'
                    ? 'bg-purple-600 text-white shadow-lg'
                    : 'text-gray-300 hover:text-white hover:bg-slate-600/50'
                }`}
              >
                <NewspaperIcon className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="hidden md:inline">Charts & News</span>
                <span className="md:hidden">Charts</span>
              </button>
              <button
                onClick={() => handleViewChange('analysis')}
                className={`px-2 sm:px-4 py-1.5 sm:py-2 rounded-md text-xs sm:text-sm font-medium transition-all flex items-center gap-1 sm:gap-2 ${
                  activeView === 'analysis'
                    ? 'bg-purple-600 text-white shadow-lg'
                    : 'text-gray-300 hover:text-white hover:bg-slate-600/50'
                }`}
              >
                <ChartBarIcon className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="hidden md:inline">Sentiment & Fundamentals</span>
                <span className="md:hidden">Analysis</span>
              </button>
            </div>

            {/* Right side - Stock switcher */}
            <div className="flex items-center flex-shrink-0">
              <button
                onClick={() => setShowStockSwitcher(true)}
                className="bg-slate-600/50 hover:bg-slate-500/50 text-gray-300 hover:text-white px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg transition-colors flex items-center gap-1 sm:gap-2"
              >
                <MagnifyingGlassIcon className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="hidden lg:inline">Switch Stock</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="relative">
        {isTransitioning ? (
          <div className="min-h-screen flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
          </div>
        ) : activeView === 'charts' ? (
          <div className="animate-fadeIn">
            <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 xl:px-8 py-4 sm:py-6 lg:py-8">
              <div className="space-y-4 sm:space-y-6">
                {/* Price Chart - Full width on mobile */}
                <div className="w-full">
                  <PriceChart symbol={symbol} className="shadow-sm" />
                </div>
                
                {/* News Component - Full width */}
                <div className="w-full">
                  <NewsComponent symbol={symbol} className="shadow-sm" />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="animate-fadeIn">
            <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 xl:px-8 py-4 sm:py-6 lg:py-8">
              <div className="space-y-6 lg:space-y-8">
                {/* Top Section - Key Metrics */}
                <div className="w-full">
                  <KeyMetricsComponent symbol={symbol} className="shadow-sm" />
                </div>
                
                {/* Bottom Section - Sentiment Analysis */}
                <div className="w-full">
                  <StockDashboard symbol={symbol} onBack={onBack} embedded={true} />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}