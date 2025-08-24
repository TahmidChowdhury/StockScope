'use client'

import { useState, useEffect } from 'react'
import StockSearch from '@/components/StockSearch'
import StockDashboard from '@/components/StockDashboard'
import LoginForm from '@/components/LoginForm'
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

  // Check for existing authentication on component mount
  useEffect(() => {
    const isAuthenticated = localStorage.getItem('stockscope_authenticated') === 'true'
    if (isAuthenticated) {
      setAuthState({ isAuthenticated: true })
    }
  }, [])

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
    
    setIsAnalyzing(true)
    setAnalysisStatus(`Starting analysis for ${symbol}...`)
    
    // Set analysis flag to prevent infinite polling
    localStorage.setItem('stockscope_analyzing', 'true')

    try {
      // First check if data already exists
      const existingDataResponse = await fetch(`${API_BASE_URL}/api/stocks/${symbol}${getPasswordParam()}`)
      if (existingDataResponse.ok) {
        setSelectedStock(symbol)
        setCurrentView('dashboard')
        setIsAnalyzing(false)
        setAnalysisStatus(null)
        localStorage.removeItem('stockscope_analyzing')
        return
      }

      // Start new analysis
      const response = await fetch(`${API_BASE_URL}/api/stocks/analyze${getPasswordParam()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: symbol,
          sources: ['reddit', 'news', 'sec']
        }),
      })

      if (response.status === 401) {
        handleLogout()
        localStorage.removeItem('stockscope_analyzing')
        return
      }

      const data = await response.json()
      
      if (response.ok) {
        setAnalysisStatus(`✅ Analysis started for ${symbol}! This may take 30-60 seconds.`)
        
        // Poll for completion
        let attempts = 0
        const maxAttempts = 20 // Maximum 2 minutes (20 * 6 seconds)
        
        const pollForCompletion = async () => {
          try {
            attempts++
            
            // First check if analysis data is available
            const dataResponse = await fetch(`${API_BASE_URL}/api/stocks/${symbol}${getPasswordParam()}`)
            if (dataResponse.ok) {
              setAnalysisStatus(`🎉 Analysis completed for ${symbol}!`)
              localStorage.removeItem('stockscope_analyzing')
              setTimeout(() => {
                setSelectedStock(symbol)
                setCurrentView('dashboard')
                setIsAnalyzing(false)
                setAnalysisStatus(null)
              }, 1000)
              return
            }
            
            // If no data yet, check status endpoint
            const statusResponse = await fetch(`${API_BASE_URL}/api/stocks/${symbol}/status${getPasswordParam()}`)
            if (statusResponse.ok) {
              const statusData = await statusResponse.json()
              if (statusData.status === 'completed') {
                setAnalysisStatus(`🎉 Analysis completed for ${symbol}!`)
                localStorage.removeItem('stockscope_analyzing')
                setTimeout(() => {
                  setSelectedStock(symbol)
                  setCurrentView('dashboard')
                  setIsAnalyzing(false)
                  setAnalysisStatus(null)
                }, 1000)
                return
              } else if (statusData.status === 'failed') {
                localStorage.removeItem('stockscope_analyzing')
                throw new Error(statusData.message || 'Analysis failed')
              } else {
                // Still processing, update status
                setAnalysisStatus(`🔄 ${statusData.message || `Analyzing ${symbol}...`} (${statusData.progress || 0}%)`)
              }
            }
            
            // Continue polling if not completed and haven't exceeded max attempts
            if (attempts < maxAttempts) {
              setTimeout(pollForCompletion, 6000) // Poll every 6 seconds
            } else {
              // Timeout - try once more to check for data
              const finalCheck = await fetch(`${API_BASE_URL}/api/stocks/${symbol}${getPasswordParam()}`)
              if (finalCheck.ok) {
                setAnalysisStatus(`🎉 Analysis completed for ${symbol}!`)
                localStorage.removeItem('stockscope_analyzing')
                setTimeout(() => {
                  setSelectedStock(symbol)
                  setCurrentView('dashboard')
                  setIsAnalyzing(false)
                  setAnalysisStatus(null)
                }, 1000)
              } else {
                localStorage.removeItem('stockscope_analyzing')
                throw new Error('Analysis timed out. Please try refreshing and check your portfolio.')
              }
            }
          } catch (error) {
            console.error('Error polling for completion:', error)
            if (attempts >= maxAttempts) {
              localStorage.removeItem('stockscope_analyzing')
              setAnalysisStatus(`⚠️ Analysis may have completed for ${symbol}. Check your portfolio below or try refreshing.`)
              setIsAnalyzing(false)
            } else {
              // Try again
              setTimeout(pollForCompletion, 6000)
            }
          }
        }
        
        // Start polling after 3 seconds
        setTimeout(pollForCompletion, 3000)
        
      } else {
        localStorage.removeItem('stockscope_analyzing')
        throw new Error(data.detail || 'Analysis failed')
      }
    } catch (error) {
      console.error('Analysis failed:', error)
      localStorage.removeItem('stockscope_analyzing')
      setAnalysisStatus(`❌ Analysis failed for ${symbol}. Please try again.`)
      setIsAnalyzing(false)
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
    return <StockDashboard symbol={selectedStock} onBack={handleBackToSearch} />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-16">
        {/* Header with logout */}
        <div className="text-center mb-12 relative">
          <button
            onClick={handleLogout}
            className="absolute top-0 right-0 bg-red-500/20 hover:bg-red-500/30 text-red-300 px-4 py-2 rounded-lg border border-red-500/50 transition-all duration-200"
          >
            🔓 Logout
          </button>
          
          <h1 className="text-5xl font-bold text-white mb-4">
            📊 StockScope Pro
          </h1>
          <p className="text-xl text-white/80 max-w-2xl mx-auto">
            AI-Powered Stock Sentiment Analysis with Real-Time Data from Reddit, News, and SEC Filings
          </p>
          <div className="mt-4 text-sm text-green-400">
            🔒 Secure Session Active
          </div>
        </div>

        {/* Stock Search */}
        <div className="mb-8">
          <StockSearch onAnalyze={handleAnalyze} isLoading={isAnalyzing} />
        </div>

        {/* Analysis Status */}
        {analysisStatus && (
          <div className="max-w-2xl mx-auto mb-8">
            <div className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 p-6 text-center">
              <p className="text-white text-lg">{analysisStatus}</p>
              {isAnalyzing && (
                <div className="mt-4 w-full bg-white/20 rounded-full h-2">
                  <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full animate-pulse" style={{ width: '70%' }}></div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Portfolio Section */}
        <PortfolioView onViewDashboard={handleViewDashboard} passwordParam={getPasswordParam()} />

        {/* Features */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <div className="text-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-white mb-2">Real-Time Search</h3>
            <p className="text-white/70">Instant autocomplete with 70+ popular stocks and custom symbol support</p>
          </div>
          
          <div className="text-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
            <div className="text-4xl mb-4">🤖</div>
            <h3 className="text-xl font-semibold text-white mb-2">AI Analysis</h3>
            <p className="text-white/70">Advanced sentiment analysis from multiple data sources with ML insights</p>
          </div>
          
          <div className="text-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
            <div className="text-4xl mb-4">📈</div>
            <h3 className="text-xl font-semibold text-white mb-2">Investment Insights</h3>
            <p className="text-white/70">Get BUY/SELL/HOLD recommendations with confidence scores and risk analysis</p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-16 text-center text-white/60">
          <p>Built with Next.js + Turbopack ⚡ FastAPI + Python 🐍</p>
        </div>
      </div>
    </div>
  )
}

// Portfolio component to show existing analyzed stocks
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

  const fetchAvailableStocks = async () => {
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

  useEffect(() => {
    fetchAvailableStocks()
    
    // Set up periodic refresh to catch newly completed analyses, but only when no analysis is running
    const interval = setInterval(() => {
      // Only refresh if we're not currently analyzing anything
      const isAnalyzing = localStorage.getItem('stockscope_analyzing') === 'true'
      if (!isAnalyzing) {
        fetchAvailableStocks()
      }
    }, 30000) // Refresh every 30 seconds instead of 10
    
    return () => clearInterval(interval)
  }, [passwordParam]) // Remove fetchAvailableStocks from dependencies to prevent recreation

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
        await fetchAvailableStocks() // Refresh the list
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
      await fetchAvailableStocks()

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
      <div className="max-w-4xl mx-auto mb-12">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/30 border-t-white mx-auto mb-2" />
          <p className="text-white/60">Loading your portfolio...</p>
        </div>
      </div>
    )
  }

  if (stocks.length === 0) {
    return (
      <div className="max-w-4xl mx-auto mb-12 text-center">
        <div className="bg-white/5 backdrop-blur-sm rounded-xl p-8 border border-white/10">
          <div className="text-4xl mb-4">📈</div>
          <h3 className="text-xl font-semibold text-white mb-2">No Stocks Analyzed Yet</h3>
          <p className="text-white/70">Use the search above to analyze your first stock and start building your portfolio</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto mb-12">
      {/* Portfolio Header with Controls */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">📊 Your Portfolio</h2>
        
        <div className="flex items-center gap-3">
          {isSelectionMode ? (
            <>
              <span className="text-white/70 text-sm">
                {selectedStocks.size} of {stocks.length} selected
              </span>
              <button
                onClick={handleSelectAll}
                className="text-blue-400 hover:text-blue-300 text-sm"
              >
                {selectedStocks.size === stocks.length ? 'Deselect All' : 'Select All'}
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={selectedStocks.size === 0 || isDeleting}
                className="bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm transition-colors flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Deleting...
                  </>
                ) : (
                  <>🗑️ Delete Selected ({selectedStocks.size})</>
                )}
              </button>
              <button
                onClick={exitSelectionMode}
                className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsSelectionMode(true)}
              className="bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg text-sm transition-colors border border-white/20"
            >
              ✏️ Manage Portfolio
            </button>
          )}
        </div>
      </div>

      {/* Portfolio Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {stocks.map((stock) => (
          <div key={stock.symbol} className="relative group">
            {/* Selection Mode Overlay */}
            {isSelectionMode && (
              <div
                className="absolute inset-0 z-10 bg-black/50 rounded-lg flex items-center justify-center cursor-pointer"
                onClick={() => handleStockSelection(stock.symbol)}
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

            {/* Stock Card */}
            <button
              onClick={() => !isSelectionMode && onViewDashboard(stock.symbol)}
              disabled={isSelectionMode}
              className="w-full bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-4 border border-white/20 transition-all duration-200 hover:scale-105 disabled:hover:scale-100 disabled:cursor-default"
            >
              <div className="text-center">
                <div className="text-lg font-bold text-white mb-1">{stock.symbol}</div>
                
                {/* Company Name */}
                {stock.companyName && stock.companyName !== stock.symbol && (
                  <div className="text-xs text-white/60 mb-2 truncate" title={stock.companyName}>
                    {stock.companyName}
                  </div>
                )}
                
                {/* Current Price */}
                {stock.currentPrice && stock.currentPrice > 0 ? (
                  <div className="mb-2">
                    <div className="text-lg font-semibold text-white">
                      ${stock.currentPrice.toFixed(2)}
                    </div>
                    
                    {/* Price Change */}
                    {stock.priceChange !== undefined && stock.priceChangePercent !== undefined && (
                      <div className={`text-xs flex items-center justify-center gap-1 ${
                        stock.priceChange > 0 ? 'text-green-400' : 
                        stock.priceChange < 0 ? 'text-red-400' : 'text-white/60'
                      }`}>
                        <span>
                          {stock.priceChange > 0 ? '↗' : stock.priceChange < 0 ? '↘' : '→'}
                        </span>
                        <span>
                          {stock.priceChange > 0 ? '+' : ''}{stock.priceChange.toFixed(2)} 
                          ({stock.priceChangePercent > 0 ? '+' : ''}{stock.priceChangePercent.toFixed(1)}%)
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-white/60 mb-2">
                    {stock.total_posts > 0 ? `${stock.total_posts} posts` : 'View Dashboard'}
                  </div>
                )}
                
                {/* Sentiment */}
                {stock.avg_sentiment !== 0 && (
                  <div className={`text-xs ${
                    stock.avg_sentiment > 0.1 ? 'text-green-400' : 
                    stock.avg_sentiment < -0.1 ? 'text-red-400' : 'text-yellow-400'
                  }`}>
                    {stock.avg_sentiment > 0 ? '📈' : stock.avg_sentiment < 0 ? '📉' : '➡️'} 
                    Sentiment: {(stock.avg_sentiment * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            </button>

            {/* Individual Delete Button (only visible on hover when not in selection mode) */}
            {!isSelectionMode && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteStock(stock.symbol)
                }}
                disabled={deletingStock === stock.symbol}
                className="absolute -top-2 -right-2 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
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
        <div className="mt-4 text-center text-white/60 text-sm">
          Click on stocks to select them for bulk deletion, or use &ldquo;Select All&rdquo; to choose all stocks.
        </div>
      )}
    </div>
  )
}
