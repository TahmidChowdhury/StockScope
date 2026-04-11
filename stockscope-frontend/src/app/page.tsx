'use client'

import { useState, useEffect } from 'react'
import StockSearch from '@/components/StockSearch'
import StockAnalysisHub from '@/components/StockAnalysisHub'
import LoadingScreen from '@/components/LoadingScreen'
import LoginForm from '@/components/LoginForm'
import SideNav from '@/components/SideNav'
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
  const [stocks, setStocks] = useState<StockMetadata[]>([])

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

  // Fetch portfolio data when authenticated
  useEffect(() => {
    const fetchPortfolioData = async () => {
      if (!authState.isAuthenticated) return
      
      try {
        const password = localStorage.getItem('stockscope_password')
        const passwordParam = password ? `?password=${encodeURIComponent(password)}` : ''
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
        console.error('Failed to fetch portfolio:', error)
      }
    }
    
    fetchPortfolioData()
    
    // Set up periodic refresh
    if (authState.isAuthenticated) {
      const interval = setInterval(() => {
        const isAnalyzing = localStorage.getItem('stockscope_analyzing') === 'true'
        if (!isAnalyzing) {
          fetchPortfolioData()
        }
      }, 30000)
      
      return () => clearInterval(interval)
    }
  }, [authState.isAuthenticated])

  // Progress updates are now handled entirely via useAnalysisProgress callbacks (onComplete/onError)

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
    setStocks([])
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
        refreshPortfolioData()
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

      // Kick off a portfolio refresh in the background so new symbols appear
      refreshPortfolioData()

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

  // Refresh portfolio data function
  const refreshPortfolioData = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/stocks${getPasswordParam()}`)
      if (response.ok) {
        const data = await response.json()
        if (Array.isArray(data.stocks)) {
          if (data.stocks.length > 0 && typeof data.stocks[0] === 'string') {
            setStocks(data.stocks.map((symbol: string) => ({
              symbol,
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
      console.error('Failed to refresh portfolio:', error)
    }
  }

  // Show login form if not authenticated
  if (!authState.isAuthenticated) {
    return <LoginForm onLoginSuccess={handleLoginSuccess} />
  }

  if (currentView === 'dashboard' && selectedStock) {
    return (
      <div className="flex h-screen overflow-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <SideNav
          stocks={stocks}
          onLogout={handleLogout}
          onStockSelect={handleAnalyze}
          currentStock={selectedStock}
          activePage="dashboard"
          hideMobileToggle
        />
        <main className="flex-1 overflow-y-auto pb-16 lg:pb-0">
          <StockAnalysisHub
            symbol={selectedStock}
            onBack={handleBackToSearch}
            stocks={stocks}
            onStockSelect={(symbol) => { handleAnalyze(symbol) }}
          />
        </main>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <SideNav
        stocks={stocks}
        onLogout={handleLogout}
        onStockSelect={handleAnalyze}
        activePage="dashboard"
      />

      <main className="flex-1 overflow-y-auto">
        {/* Bottom nav spacer on mobile */}
        {/* Loading screen — fixed full-viewport overlay */}
        {isAnalyzing && (
          <LoadingScreen
            progress={progress}
            details={currentPhase}
            message={message}
            symbol={selectedStock || undefined}
          />
        )}

        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8 pb-24 lg:pb-8 space-y-6">
          {/* Dashboard header */}
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white">Dashboard</h1>
              <p className="text-white/40 text-sm mt-0.5">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
              </p>
            </div>
            <div className="text-xs text-green-400/80 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
              Secure Session
            </div>
          </div>

          {/* Search */}
          <StockSearch onAnalyze={handleAnalyze} isLoading={isAnalyzing} />

          {/* Analysis status */}
          {analysisStatus && (
            <div className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 p-4 text-center">
              <p className="text-white text-sm">{analysisStatus}</p>
              {isAnalyzing && (
                <div className="mt-3 w-full bg-white/20 rounded-full h-1.5">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-purple-500 h-1.5 rounded-full animate-pulse"
                    style={{ width: `${Math.max(progress, 20)}%` }}
                  />
                </div>
              )}
            </div>
          )}

          {/* Portfolio */}
          <PortfolioView
            onViewDashboard={handleViewDashboard}
            passwordParam={getPasswordParam()}
            onStocksChange={setStocks}
          />


        </div>
      </main>
    </div>
  )
}

// Portfolio component to show existing analyzed stocks
function PortfolioView({ onViewDashboard, passwordParam, onStocksChange }: { 
  onViewDashboard: (symbol: string) => void
  passwordParam: string
  onStocksChange?: (stocks: StockMetadata[]) => void
}) {
  const [stocks, setStocks] = useState<StockMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedStocks, setSelectedStocks] = useState<Set<string>>(new Set())
  const [isSelectionMode, setIsSelectionMode] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deletingStock, setDeletingStock] = useState<string | null>(null)

  // Toast + confirm modal
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }
  const [confirmModal, setConfirmModal] = useState<{
    title: string
    body: string
    onConfirm: () => void
  } | null>(null)

  // Helper: update local state AND notify parent (keeps SideNav in sync)
  const applyStocks = (raw: StockMetadata[] | string[]) => {
    const normalised: StockMetadata[] = raw.length > 0 && typeof raw[0] === 'string'
      ? (raw as string[]).map((symbol) => ({ symbol, total_posts: 0, avg_sentiment: 0, last_updated: '', sources: [] }))
      : raw as StockMetadata[]
    setStocks(normalised)
    onStocksChange?.(normalised)
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/stocks${passwordParam}`)
        if (response.ok) {
          const data = await response.json()
          if (Array.isArray(data.stocks)) {
            applyStocks(data.stocks)
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
    setConfirmModal({
      title: `Delete ${symbol}`,
      body: `All sentiment analysis data for ${symbol} will be permanently removed. This cannot be undone.`,
      onConfirm: async () => {
        setConfirmModal(null)
        setDeletingStock(symbol)
        try {
          const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}${passwordParam}`, {
            method: 'DELETE'
          })

          if (response.ok) {
            const result = await response.json()
            showToast(`Deleted ${result.deleted_files.length} file${result.deleted_files.length !== 1 ? 's' : ''} for ${symbol}`, 'success')
            const refreshResponse = await fetch(`${API_BASE_URL}/api/stocks${passwordParam}`)
            if (refreshResponse.ok) {
              const data = await refreshResponse.json()
              if (Array.isArray(data.stocks)) { applyStocks(data.stocks) }
            }
          } else {
            const error = await response.json()
            throw new Error(error.detail || 'Failed to delete stock')
          }
        } catch (error) {
          console.error('Error deleting stock:', error)
          showToast(error instanceof Error ? error.message : 'Failed to delete stock data', 'error')
        } finally {
          setDeletingStock(null)
        }
      }
    })
  }

  const handleBulkDelete = async () => {
    if (selectedStocks.size === 0) return

    const stocksList = Array.from(selectedStocks).join(', ')
    setConfirmModal({
      title: `Delete ${selectedStocks.size} stock${selectedStocks.size !== 1 ? 's' : ''}`,
      body: `All data for ${stocksList} will be permanently removed. This cannot be undone.`,
      onConfirm: async () => {
        setConfirmModal(null)
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

          if (failedStocks.length === 0) {
            showToast(`Deleted ${deletedCount} stock${deletedCount !== 1 ? 's' : ''} successfully`, 'success')
          } else {
            showToast(`Deleted ${deletedCount}. Failed: ${failedStocks.join(', ')}`, 'error')
          }

          setSelectedStocks(new Set())
          setIsSelectionMode(false)

          const refreshResponse = await fetch(`${API_BASE_URL}/api/stocks${passwordParam}`)
          if (refreshResponse.ok) {
            const data = await refreshResponse.json()
            if (Array.isArray(data.stocks)) { applyStocks(data.stocks) }
          }
        } catch (error) {
          console.error('Error in bulk delete:', error)
          showToast('Bulk delete failed', 'error')
        } finally {
          setIsDeleting(false)
        }
      }
    })
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
    <>
      {/* Toast notification */}
      {toast && (
        <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl border text-sm font-medium ${
          toast.type === 'success'
            ? 'bg-green-900/90 border-green-500/40 text-green-100'
            : 'bg-red-900/90 border-red-500/40 text-red-100'
        }`}>
          <span>{toast.type === 'success' ? '✓' : '✕'}</span>
          {toast.message}
        </div>
      )}

      {/* Confirm modal */}
      {confirmModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gradient-to-br from-slate-900 to-red-900/60 rounded-2xl p-6 max-w-sm w-full border border-red-500/20 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-red-600/20 rounded-full p-2 flex-shrink-0">
                <span className="text-red-400 text-lg">×</span>
              </div>
              <h2 className="text-lg font-bold text-white">{confirmModal.title}</h2>
            </div>
            <p className="text-white/70 text-sm mb-6 leading-relaxed">{confirmModal.body}</p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmModal(null)}
                className="flex-1 bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                onClick={confirmModal.onConfirm}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium"
              >
                Delete Forever
              </button>
            </div>
          </div>
        </div>
      )}

    <div className="max-w-6xl mx-auto mb-8 sm:mb-12 px-3 sm:px-4">
      {/* Portfolio Header with Controls - Mobile optimized */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-white">Portfolio</h2>
        
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
                    Delete ({selectedStocks.size})
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
              <span className="hidden sm:inline">Manage Portfolio</span>
              <span className="sm:hidden">Manage</span>
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
              className="w-full min-h-[144px] bg-gradient-to-br from-white/10 to-white/5 hover:from-white/20 hover:to-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20 transition-all duration-200 hover:scale-105 hover:shadow-lg hover:shadow-white/10 disabled:hover:scale-100 disabled:cursor-default flex flex-col justify-between group"
              aria-label={`View ${stock.symbol} dashboard`}
            >
              {/* Top Section */}
              <div className="text-center">
                {/* Stock Symbol - Much larger */}
                <div className="text-lg sm:text-xl font-bold text-white mb-2">{stock.symbol}</div>
                
                {/* Company Name - Better truncation */}
                {stock.companyName && stock.companyName !== stock.symbol && (
                  <div className="text-xs sm:text-sm text-white/60 mb-2 line-clamp-1 leading-tight" title={stock.companyName}>
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
                  {stock.avg_sentiment > 0.1 ? 'Bullish' :
                   stock.avg_sentiment < -0.1 ? 'Bearish' : 'Neutral'}
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
    </>
  )
}
