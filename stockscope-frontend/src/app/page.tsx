'use client'

import { useState, useEffect } from 'react'
import StockSearch from '@/components/StockSearch'
import StockAnalysisHub from '@/components/StockAnalysisHub'
import LoadingScreen from '@/components/LoadingScreen'
import LoginForm from '@/components/LoginForm'
import { useAnalysisProgress } from '@/hooks/useAnalysisProgress'
import type { ViewType, StockMetadata, AuthState } from '@/types'

// Get API URL from environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false
  })
  const [currentView, setCurrentView] = useState<ViewType>('search')
  const [selectedStock, setSelectedStock] = useState<string>('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState<string | null>(null)

  // Use the analysis progress hook
  const { status, progress, message, currentPhase } = useAnalysisProgress({
    symbol: selectedStock,
    isAnalyzing,
    onComplete: () => {
      setIsAnalyzing(false)
      setCurrentView('dashboard')
      setAnalysisStatus(null)
    },
    onError: (error) => {
      setIsAnalyzing(false)
      setAnalysisStatus(`❌ ${error}`)
    }
  })

  // Check for existing authentication on component mount
  useEffect(() => {
    const isAuthenticated = localStorage.getItem('stockscope_authenticated') === 'true'
    if (isAuthenticated) {
      setAuthState({ isAuthenticated: true })
    }
  }, [])

  // Handle progress updates
  useEffect(() => {
    if (isAnalyzing && selectedStock && status) {
      if (status.status === 'completed') {
        setAnalysisStatus(`🎉 Analysis completed for ${selectedStock}!`)
        setTimeout(() => {
          setCurrentView('dashboard')
          setIsAnalyzing(false)
          setAnalysisStatus(null)
        }, 1000)
      } else if (status.status === 'error') {
        setIsAnalyzing(false)
        setAnalysisStatus(`❌ Analysis failed for ${selectedStock}: ${message || 'Unknown error'}`)
        setTimeout(() => {
          setAnalysisStatus(null)
        }, 5000)
      } else {
        setAnalysisStatus(`🔄 ${message || `Analyzing ${selectedStock}...`} (${Math.round(progress)}%)`)
      }
    }
  }, [status, progress, message, isAnalyzing, selectedStock])

  const handleLoginSuccess = () => {
    setAuthState({ isAuthenticated: true })
  }

  const handleLogout = () => {
    localStorage.removeItem('stockscope_authenticated')
    localStorage.removeItem('stockscope_password')
    setAuthState({ isAuthenticated: false })
    setCurrentView('search')
    setSelectedStock('')
    setAnalysisStatus(null)
  }

  const getPasswordParam = () => {
    const password = localStorage.getItem('stockscope_password')
    return password ? `?password=${encodeURIComponent(password)}` : ''
  }

  const handleAnalyze = async (symbol: string) => {
    if (!authState.isAuthenticated) return
    
    try {
      // First check if data already exists
      const existingDataResponse = await fetch(`${API_BASE_URL}/api/stocks/${symbol}${getPasswordParam()}`)
      if (existingDataResponse.ok) {
        setSelectedStock(symbol)
        setCurrentView('dashboard')
        return
      }

      // Start analysis and enable progress tracking
      setSelectedStock(symbol)
      setIsAnalyzing(true)
      setAnalysisStatus(`Starting analysis for ${symbol}...`)

      // Start new analysis
      const response = await fetch(`${API_BASE_URL}/api/stocks/analyze${getPasswordParam()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: symbol,
          sources: ['news', 'sec']  // Removed reddit since it's not implemented
        }),
      })

      if (response.status === 401) {
        handleLogout()
        return
      }

      if (!response.ok) {
        throw new Error('Failed to start analysis')
      }

      // The progress hook will handle polling and completion
      
    } catch (error) {
      console.error('Error starting analysis:', error)
      setIsAnalyzing(false)
      setAnalysisStatus(`❌ Failed to analyze ${symbol}: ${error instanceof Error ? error.message : 'Unknown error'}`)
      
      setTimeout(() => {
        setAnalysisStatus(null)
      }, 5000)
    }
  }

  const handleViewDashboard = (symbol: string) => {
    setSelectedStock(symbol)
    setCurrentView('dashboard')
  }

  const handleBackToSearch = () => {
    setCurrentView('search')
    setSelectedStock('')
    setAnalysisStatus(null)
  }

  // Show login form if not authenticated
  if (!authState.isAuthenticated) {
    return <LoginForm onLoginSuccess={handleLoginSuccess} />
  }

  if (currentView === 'dashboard' && selectedStock) {
    return (
      <StockAnalysisHub 
        symbol={selectedStock} 
        onBack={handleBackToSearch}
        onStockSelect={(symbol) => {
          setSelectedStock(symbol)
          // Stay in dashboard view with new stock
        }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Show loading screen when analysis is running */}
      {isAnalyzing && (
        <LoadingScreen 
          progress={progress}
          details={currentPhase}
          message={message}
        />
      )}
      
      <div className="container mx-auto px-3 sm:px-4 py-8 sm:py-16">
        {/* Header with logout - Mobile optimized */}
        <div className="text-center mb-8 sm:mb-12 relative">
          <button
            onClick={handleLogout}
            className="absolute top-0 right-0 bg-red-500/20 hover:bg-red-500/30 text-red-300 px-2 sm:px-4 py-1.5 sm:py-2 rounded-lg border border-red-500/50 transition-all duration-200 text-xs sm:text-sm"
          >
            <span className="hidden sm:inline">🔓 Logout</span>
            <span className="sm:hidden">🔓</span>
          </button>
          
          <h1 className="text-3xl sm:text-5xl font-bold text-white mb-2 sm:mb-4 pr-16 sm:pr-0">
            📊 StockScope Pro
          </h1>
          <p className="text-base sm:text-xl text-white/80 max-w-2xl mx-auto px-2">
            AI-Powered Stock Sentiment Analysis with Real-Time Data from News and SEC Filings
          </p>
          <div className="mt-2 sm:mt-4 text-xs sm:text-sm text-green-400">
            🔒 Secure Session Active
          </div>
        </div>

        {/* Navigation Menu */}
        <div className="max-w-4xl mx-auto mb-8">
          <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-4 text-center">📈 Fundamentals Analytics</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Company Comparison */}
              <a
                href="/compare"
                className="group bg-gradient-to-r from-blue-600/20 to-purple-600/20 hover:from-blue-600/30 hover:to-purple-600/30 border border-blue-500/30 rounded-lg p-6 transition-all duration-200 hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20"
              >
                <div className="text-center">
                  <div className="text-3xl mb-3">⚖️</div>
                  <h3 className="text-lg font-semibold text-white mb-2">Compare Companies</h3>
                  <p className="text-sm text-white/70 mb-3">
                    Side-by-side comparison of financial metrics and performance
                  </p>
                  <span className="inline-flex items-center text-blue-300 text-sm group-hover:text-blue-200">
                    Launch Comparison Tool →
                  </span>
                </div>
              </a>

              {/* Stock Screener */}
              <a
                href="/screener"
                className="group bg-gradient-to-r from-green-600/20 to-emerald-600/20 hover:from-green-600/30 hover:to-emerald-600/30 border border-green-500/30 rounded-lg p-6 transition-all duration-200 hover:scale-105 hover:shadow-lg hover:shadow-green-500/20"
              >
                <div className="text-center">
                  <div className="text-3xl mb-3">🔍</div>
                  <h3 className="text-lg font-semibold text-white mb-2">Stock Screener</h3>
                  <p className="text-sm text-white/70 mb-3">
                    Advanced filtering to find stocks matching your criteria
                  </p>
                  <span className="inline-flex items-center text-green-300 text-sm group-hover:text-green-200">
                    Open Screener →
                  </span>
                </div>
              </a>

              {/* Individual Analysis */}
              <div className="group bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/30 rounded-lg p-6">
                <div className="text-center">
                  <div className="text-3xl mb-3">📊</div>
                  <h3 className="text-lg font-semibold text-white mb-2">Company Analysis</h3>
                  <p className="text-sm text-white/70 mb-3">
                    Deep dive into individual company fundamentals
                  </p>
                  <span className="text-purple-300 text-sm">
                    Use search below or click portfolio stocks ↓
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stock Search */}
        <div className="mb-6 sm:mb-8">
          <StockSearch onAnalyze={handleAnalyze} isLoading={isAnalyzing} />
        </div>

        {/* Analysis Status */}
        {analysisStatus && (
          <div className="max-w-2xl mx-auto mb-6 sm:mb-8">
            <div className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 p-4 sm:p-6 text-center mx-2 sm:mx-0">
              <p className="text-white text-sm sm:text-lg">{analysisStatus}</p>
              {isAnalyzing && (
                <div className="mt-3 sm:mt-4 w-full bg-white/20 rounded-full h-2">
                  <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full animate-pulse" style={{ width: '70%' }}></div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Portfolio Section */}
        <PortfolioView onViewDashboard={handleViewDashboard} passwordParam={getPasswordParam()} />

        {/* Footer */}
        <div className="mt-12 sm:mt-16 text-center text-white/60 px-2">
          <p className="text-sm sm:text-base">Built with Next.js + Turbopack ⚡ FastAPI + Python 🐍</p>
        </div>
      </div>
    </div>
  )
}

// Portfolio component to show existing analyzed stocks - Mobile optimized
function PortfolioView({ onViewDashboard, passwordParam }: { 
  onViewDashboard: (symbol: string) => void
  passwordParam: string
}) {
  const [stocks, setStocks] = useState<StockMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedStocks, setSelectedStocks] = useState<Set<string>>(new Set())
  const [isSelectionMode, setIsSelectionMode] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deletingStock, setDeletingStock] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/stocks${passwordParam}`)
        if (response.ok) {
          const data = await response.json()
          // Handle both old format (array of strings) and new format (array of objects)
          if (Array.isArray(data.stocks)) {
            if (data.stocks.length > 0 && typeof data.stocks[0] === 'string') {
              // Old format: convert strings to objects
              setStocks(data.stocks.map((symbol: string) => ({
                symbol,
                total_posts: 0,
                avg_sentiment: 0,
                last_updated: '',
                sources: []
              })))
            } else {
              // New format: use objects directly
              setStocks(data.stocks || [])
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch stocks:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
    
    // Set up periodic refresh to catch newly completed analyses, but only when no analysis is running
    const interval = setInterval(() => {
      // Only refresh if we're not currently analyzing anything
      const isAnalyzing = localStorage.getItem('stockscope_analyzing') === 'true'
      if (!isAnalyzing) {
        fetchData()
      }
    }, 30000) // Refresh every 30 seconds instead of 10
    
    return () => clearInterval(interval)
  }, [passwordParam])

  const handleStockSelection = (symbol: string) => {
    const newSelected = new Set(selectedStocks)
    if (newSelected.has(symbol)) {
      newSelected.delete(symbol)
    } else {
      newSelected.add(symbol)
    }
    setSelectedStocks(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedStocks.size === stocks.length) {
      setSelectedStocks(new Set())
    } else {
      setSelectedStocks(new Set(stocks.map(s => s.symbol)))
    }
  }

  const handleDeleteStock = async (symbol: string) => {
    if (!confirm(`Are you sure you want to delete all data for ${symbol}? This action cannot be undone.`)) {
      return
    }

    setDeletingStock(symbol)
    try {
      const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}${passwordParam}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        const result = await response.json()
        alert(`Successfully deleted ${result.deleted_files.length} files for ${symbol}`)
        // Refresh the list by refetching data
        const refreshResponse = await fetch(`${API_BASE_URL}/api/stocks${passwordParam}`)
        if (refreshResponse.ok) {
          const data = await refreshResponse.json()
          if (Array.isArray(data.stocks)) {
            if (data.stocks.length > 0 && typeof data.stocks[0] === 'string') {
              setStocks(data.stocks.map((s: string) => ({
                symbol: s,
                total_posts: 0,
                avg_sentiment: 0,
                last_updated: '',
                sources: []
              })))
            } else {
              setStocks(data.stocks || [])
            }
          }
        }
      } else {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete stock')
      }
    } catch (error) {
      console.error('Error deleting stock:', error)
      alert(error instanceof Error ? error.message : 'Failed to delete stock data')
    } finally {
      setDeletingStock(null)
    }
  }

  const handleBulkDelete = async () => {
    if (selectedStocks.size === 0) return

    const stocksList = Array.from(selectedStocks).join(', ')
    if (!confirm(`Are you sure you want to delete data for ${selectedStocks.size} stocks (${stocksList})? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(true)
    let deletedCount = 0
    const failedStocks: string[] = []

    try {
      for (const symbol of selectedStocks) {
        try {
          const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}${passwordParam}`, {
            method: 'DELETE'
          })

          if (response.ok) {
            deletedCount++
          } else {
            failedStocks.push(symbol)
          }
        } catch {
          failedStocks.push(symbol)
        }
      }

      // Show results
      if (failedStocks.length === 0) {
        alert(`Successfully deleted data for ${deletedCount} stocks!`)
      } else {
        alert(`Deleted ${deletedCount} stocks successfully. Failed to delete: ${failedStocks.join(', ')}`)
      }

      // Reset selection and refresh
      setSelectedStocks(new Set())
      setIsSelectionMode(false)
      
      // Refresh the list by refetching data
      const refreshResponse = await fetch(`${API_BASE_URL}/api/stocks${passwordParam}`)
      if (refreshResponse.ok) {
        const data = await refreshResponse.json()
        if (Array.isArray(data.stocks)) {
          if (data.stocks.length > 0 && typeof data.stocks[0] === 'string') {
            setStocks(data.stocks.map((s: string) => ({
              symbol: s,
              total_posts: 0,
              avg_sentiment: 0,
              last_updated: '',
              sources: []
            })))
          } else {
            setStocks(data.stocks || [])
          }
        }
      }

    } catch (error) {
      console.error('Error in bulk delete:', error)
      alert('Bulk delete operation failed')
    } finally {
      setIsDeleting(false)
    }
  }

  const exitSelectionMode = () => {
    setIsSelectionMode(false)
    setSelectedStocks(new Set())
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto mb-8 sm:mb-12 px-2 sm:px-0">
        <div className="text-center">
          <div className="h-6 w-6 sm:h-8 sm:w-8 animate-spin rounded-full border-2 border-white/30 border-t-white mx-auto mb-2" />
          <p className="text-white/60 text-sm sm:text-base">Loading your portfolio...</p>
        </div>
      </div>
    )
  }

  if (stocks.length === 0) {
    return (
      <div className="max-w-4xl mx-auto mb-8 sm:mb-12 text-center px-2 sm:px-0">
        <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 sm:p-8 border border-white/10">
          <div className="text-3xl sm:text-4xl mb-2 sm:mb-4">📈</div>
          <h3 className="text-lg sm:text-xl font-semibold text-white mb-1 sm:mb-2">No Stocks Analyzed Yet</h3>
          <p className="text-sm sm:text-base text-white/70">Use the search above to analyze your first stock and start building your portfolio</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto mb-8 sm:mb-12 px-3 sm:px-4">
      {/* Portfolio Header with Controls - Mobile optimized */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-white">📊 Portfolio</h2>
        
        <div className="flex items-center gap-2 sm:gap-3">
          {isSelectionMode ? (
            <>
              <span className="text-white/70 text-sm">
                <span className="hidden sm:inline">{selectedStocks.size} of {stocks.length} selected</span>
                <span className="sm:hidden">{selectedStocks.size}/{stocks.length}</span>
              </span>
              <button
                onClick={handleSelectAll}
                className="text-blue-400 hover:text-blue-300 text-sm"
              >
                <span className="hidden sm:inline">{selectedStocks.size === stocks.length ? 'Deselect All' : 'Select All'}</span>
                <span className="sm:hidden">All</span>
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={selectedStocks.size === 0 || isDeleting}
                className="bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    <span className="hidden sm:inline">Deleting...</span>
                  </>
                ) : (
                  <>
                    🗑️ 
                    <span className="hidden sm:inline">Delete ({selectedStocks.size})</span>
                    <span className="sm:hidden">({selectedStocks.size})</span>
                  </>
                )}
              </button>
              <button
                onClick={exitSelectionMode}
                className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-lg text-sm transition-colors"
              >
                <span className="hidden sm:inline">Cancel</span>
                <span className="sm:hidden">✕</span>
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsSelectionMode(true)}
              className="bg-white/10 hover:bg-white/20 text-white px-3 py-2 rounded-lg text-sm transition-colors border border-white/20 flex items-center gap-2"
            >
              <span className="hidden sm:inline">✏️ Manage Portfolio</span>
              <span className="sm:hidden">✏️</span>
            </button>
          )}
        </div>
      </div>

      {/* Portfolio Grid - MUCH better mobile layout */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 sm:gap-6">
        {stocks.map((stock) => (
          <div key={stock.symbol} className="relative group">
            {/* Selection Mode Overlay */}
            {isSelectionMode && (
              <div
                role="checkbox"
                aria-checked={selectedStocks.has(stock.symbol)}
                aria-label={`Select ${stock.symbol}`}
                tabIndex={0}
                className="absolute inset-0 z-10 bg-black/50 rounded-xl flex items-center justify-center cursor-pointer"
                onClick={() => handleStockSelection(stock.symbol)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    handleStockSelection(stock.symbol)
                  }
                }}
              >
                <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                  selectedStocks.has(stock.symbol) 
                    ? 'bg-blue-500 border-blue-500' 
                    : 'border-white bg-transparent'
                }`}>
                  {selectedStocks.has(stock.symbol) && (
                    <span className="text-white text-sm">✓</span>
                  )}
                </div>
              </div>
            )}

            {/* Stock Card - Much larger and more readable */}
            <button
              onClick={() => !isSelectionMode && onViewDashboard(stock.symbol)}
              disabled={isSelectionMode}
              className="w-full h-36 sm:h-40 bg-gradient-to-br from-white/10 to-white/5 hover:from-white/20 hover:to-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20 transition-all duration-200 hover:scale-105 hover:shadow-lg hover:shadow-white/10 disabled:hover:scale-100 disabled:cursor-default flex flex-col justify-between group"
              aria-label={`View ${stock.symbol} dashboard`}
            >
              {/* Top Section */}
              <div className="text-center">
                {/* Stock Symbol - Much larger */}
                <div className="text-lg sm:text-xl font-bold text-white mb-2">{stock.symbol}</div>
                
                {/* Company Name - Better truncation */}
                {stock.companyName && stock.companyName !== stock.symbol && (
                  <div className="text-xs sm:text-sm text-white/60 mb-2 line-clamp-2 leading-tight" title={stock.companyName}>
                    {stock.companyName}
                  </div>
                )}
              </div>

              {/* Middle Section - Price or Post Count */}
              <div className="text-center">
                {stock.currentPrice && stock.currentPrice > 0 ? (
                  <div className="space-y-1">
                    <div className="text-base sm:text-lg font-semibold text-white">
                      ${stock.currentPrice.toFixed(2)}
                    </div>
                    {/* Price Change */}
                    {stock.priceChange !== undefined && stock.priceChangePercent !== undefined && (
                      <div className={`text-sm flex items-center justify-center gap-1 ${
                        stock.priceChange > 0 ? 'text-green-400' : 
                        stock.priceChange < 0 ? 'text-red-400' : 'text-white/60'
                      }`}>
                        {stock.priceChange > 0 ? '↗' : stock.priceChange < 0 ? '↘' : '→'}
                        {stock.priceChange > 0 ? '+' : ''}{stock.priceChangePercent.toFixed(1)}%
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-white/70">
                    {stock.total_posts > 0 ? `${stock.total_posts.toLocaleString()} posts` : 'View Dashboard'}
                  </div>
                )}
              </div>
              
              {/* Bottom Section - Sentiment */}
              <div className="text-center">
                <div className={`text-sm flex items-center justify-center gap-1 ${
                  stock.avg_sentiment > 0.1 ? 'text-green-400' : 
                  stock.avg_sentiment < -0.1 ? 'text-red-400' : 'text-yellow-400'
                }`}>
                  {stock.avg_sentiment > 0.1 ? '📈 Bullish' : 
                   stock.avg_sentiment < -0.1 ? '📉 Bearish' : '➡️ Neutral'}
                </div>
              </div>
            </button>

            {/* Individual Delete Button - Better positioned */}
            {!isSelectionMode && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteStock(stock.symbol)
                }}
                disabled={deletingStock === stock.symbol}
                className="absolute -top-2 -right-2 bg-red-600 hover:bg-red-700 text-white rounded-full w-7 h-7 flex items-center justify-center text-sm opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50"
                title={`Delete ${stock.symbol}`}
              >
                {deletingStock === stock.symbol ? (
                  <div className="h-3 w-3 animate-spin rounded-full border border-white/30 border-t-white" />
                ) : (
                  '×'
                )}
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Bulk Selection Help Text */}
      {isSelectionMode && (
        <div className="mt-6 text-center text-white/60 text-sm">
          <span className="hidden sm:inline">Click on stocks to select them for bulk deletion, or use "Select All" to choose all stocks.</span>
          <span className="sm:hidden">Tap stocks to select for deletion</span>
        </div>
      )}
    </div>
  )
}
