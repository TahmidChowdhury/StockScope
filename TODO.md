# StockScope TODO List
*Last Updated: August 26, 2025*

## 📊 **Data Coverage TODOs** (Priority: HIGH)

### 1. **YoY Growth Data Enhancement** 🔴 CRITICAL
- **Issue**: Growth metrics (YoY) are missing ~80% of the time, showing as "N/A"
- **Impact**: Screener filters for growth are largely ineffective
- **Files**: `backend/services/fundamentals.py`
- **Solution**: 
  ```python
  # TODO: Implement historical data caching
  def get_historical_quarters(ticker: str, periods: int = 8):
      """Fetch and cache 8 quarters of data for reliable YoY calculations"""
      # Cache quarterly data locally to avoid repeated API calls
      # Implement fallback calculations when exact quarters unavailable
  ```

### 2. **Alternative Data Sources** 🟡 HIGH
- **Issue**: Only using yfinance (rate limited, incomplete data)
- **Impact**: Single point of failure, missing data for many companies
- **Files**: `backend/services/data_providers.py` (new file needed)
- **Solution**:
  ```python
  # TODO: Add fallback data providers
  class MultiSourceDataProvider:
      def __init__(self):
          self.providers = [
              YFinanceProvider(), 
              AlphaVantageProvider(), 
              PolygonProvider(),
              FinancialModelingPrepProvider()
          ]
      
      def get_data_with_fallback(self, ticker: str):
          # Try each provider in order until success
  ```

### 3. **Field Aliases Expansion** 🟡 HIGH  
- **Issue**: Some companies use different field names, causing data detection failures
- **Impact**: Valid data exists but isn't found due to naming variations
- **Files**: `backend/services/fundamentals.py`
- **Solution**:
  ```python
  # TODO: Expand field detection patterns
  EXPANDED_FIELD_ALIASES = {
      'capex': [
          'Capital Expenditures', 'CapEx', 'Property Plant Equipment',
          'Additions To Property Plant Equipment', 'Investment In Property Plant Equipment',
          'Purchase Of Property Plant Equipment', 'Capital Investment',
          'Acquisition Of Property Plant Equipment', 'PP&E Investment'
      ],
      'revenue': [
          'Total Revenue', 'Net Sales', 'Revenue', 'Sales', 'Total Net Sales',
          'Operating Revenue', 'Net Revenue', 'Total Net Revenue', 'Gross Revenue'
      ],
      'free_cash_flow': [
          'Free Cash Flow', 'FCF', 'Operating Cash Flow Minus Capex',
          'Net Cash From Operations Minus Capex', 'Unlevered Free Cash Flow'
      ]
  }
  ```

### 4. **EBITDA Calculation Enhancement** 🟡 HIGH
- **Issue**: EBITDA calculations failing for ~60% of companies
- **Impact**: Major screening metric unavailable
- **Files**: `backend/services/fundamentals.py`
- **Solution**:
  ```python
  # TODO: Multiple EBITDA calculation methods
  def calculate_ebitda_with_fallbacks(self, financials):
      # Method 1: Net Income + Interest + Taxes + Depreciation + Amortization
      # Method 2: Operating Income + Depreciation + Amortization  
      # Method 3: Operating Cash Flow + Interest - Taxes + Non-cash charges
  ```

## 📱 **Mobile Responsiveness TODOs** (Priority: MEDIUM)

### 5. **Mobile Header Optimization** 🟢 COMPLETED
- **Status**: ✅ Added mobile card view for screener results
- **Files**: `stockscope-frontend/src/app/screener/page.tsx`

### 6. **Filter Grid Mobile Optimization** 🟡 MEDIUM
- **Issue**: 3-column filter grid may be cramped on mobile
- **Files**: `stockscope-frontend/src/app/screener/page.tsx`
- **Solution**:
  ```tsx
  // TODO: Optimize filter grid breakpoints
  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
  ```

### 7. **Mobile Navigation Enhancement** 🟡 MEDIUM
- **Issue**: Header might be cramped on small screens
- **Files**: All page components
- **Solution**:
  ```tsx
  // TODO: Responsive header component
  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
    <h1 className="text-2xl sm:text-4xl font-bold text-white">
  ```

### 8. **Touch-Friendly Interactions** 🟡 MEDIUM
- **Issue**: Some buttons/inputs may be too small for touch
- **Files**: All frontend components
- **Solution**: Ensure minimum 44px touch targets, increase padding on mobile

## 🚀 **Performance & UX TODOs** (Priority: MEDIUM)

### 9. **Progressive Data Loading** 🟡 HIGH
- **Issue**: Screener processes all companies at once (slow, poor UX)
- **Impact**: Users wait 30-60 seconds with no feedback
- **Files**: `backend/routers/fundamentals.py`
- **Solution**:
  ```python
  # TODO: Implement progressive screening with Server-Sent Events
  @router.post("/screener/progressive")
  async def progressive_screener(request: ScreenerRequest):
      """Stream results as they're computed for better UX"""
      # Return results in batches of 10-20 companies
      # Show real-time progress: "Processing 50/500 companies..."
  ```

### 10. **Smart Default Filters** 🟢 MEDIUM
- **Issue**: Users don't know what filter values to use
- **Files**: `stockscope-frontend/src/app/screener/page.tsx`
- **Solution**:
  ```tsx
  // TODO: Add preset filter buttons
  const presetFilters = {
    'growth': { 
      min_revenue_growth_yoy: 0.15, 
      max_debt_to_cash: 3.0,
      sort_by: 'revenue_growth_yoy'
    },
    'value': { 
      max_debt_to_cash: 2.0, 
      sort_by: 'fcf_margin_ttm'
    },
    'quality': { 
      min_fcf_margin_ttm: 0.10, 
      max_debt_to_cash: 1.5,
      sort_by: 'operating_margin_ttm'
    }
  }
  ```

### 11. **Data Quality Indicators** 🟢 MEDIUM
- **Issue**: Users don't know how reliable the data is
- **Files**: Frontend components, backend services
- **Solution**:
  ```tsx
  // TODO: Show data confidence scores
  <div className="flex items-center gap-2">
    <span className="text-white font-medium">{formatPercent(company.fcf_margin_ttm)}</span>
    <span className="text-xs bg-green-500/20 text-green-300 px-2 py-1 rounded">
      High Confidence
    </span>
  </div>
  ```

## 🔧 **Technical Improvements** (Priority: LOW-MEDIUM)

### 12. **Caching Strategy Enhancement** 🟢 LOW
- **Issue**: Current caching is basic, could be more intelligent
- **Files**: `backend/core/cache.py`
- **Solution**: Implement Redis for production, smart cache invalidation

### 13. **Error Handling Improvement** 🟢 MEDIUM
- **Issue**: Generic error messages don't help users understand issues
- **Files**: All API endpoints
- **Solution**: Specific error messages, retry mechanisms, graceful degradation

### 14. **Data Export Functionality** 🟢 LOW
- **Issue**: Users can't export screener results
- **Files**: `stockscope-frontend/src/app/screener/page.tsx`
- **Solution**: Add CSV/Excel export buttons

### 15. **Historical Data Storage** 🟡 MEDIUM
- **Issue**: No local storage of historical data, repeated API calls
- **Files**: `backend/services/fundamentals.py`, database integration
- **Solution**: SQLite for development, PostgreSQL for production

## 📊 **Data Source Diversification** (Priority: HIGH)

### 16. **API Key Management** 🟡 HIGH
- **Issue**: Need multiple data source APIs configured
- **Files**: `.env`, `backend/services/data_providers.py`
- **APIs Needed**:
  - Alpha Vantage (free tier: 5 calls/minute, 500/day)
  - Financial Modeling Prep (free tier: 250 calls/day)  
  - Polygon.io (free tier: 5 calls/minute)
  - Yahoo Finance (unofficial, unlimited but unreliable)

### 17. **Data Validation Pipeline** 🟡 MEDIUM
- **Issue**: No validation of data quality from different sources
- **Files**: `backend/services/fundamentals.py`
- **Solution**: Cross-validate data from multiple sources, flag inconsistencies

## 🎯 **Implementation Timeline**

### **Week 1 - Data Coverage (CRITICAL)**
- [ ] Implement expanded field aliases for CapEx detection
- [ ] Add Alpha Vantage as backup data source  
- [ ] Cache historical data for YoY calculations
- [ ] Fix EBITDA calculation methods

### **Week 2 - Mobile UX**
- [ ] Test mobile responsiveness across devices (iPhone, Android, iPad)
- [ ] Add preset filter buttons ("Growth", "Value", "Quality")
- [ ] Implement progressive loading with progress indicators
- [ ] Optimize filter grid for mobile breakpoints

### **Week 3 - Performance & Polish**
- [ ] Add data confidence indicators
- [ ] Implement CSV export functionality
- [ ] Add error handling improvements
- [ ] Set up Redis caching for production

### **Week 4 - Advanced Features**
- [ ] Historical data storage (SQLite)
- [ ] Cross-source data validation
- [ ] API rate limiting and queue management
- [ ] Advanced screening presets

## 🧪 **Testing Checklist**

### **Data Coverage Testing**
- [ ] Test YoY growth calculations with 20+ companies
- [ ] Verify field detection improvements reduce "N/A" by >50%
- [ ] Test multiple data source fallbacks
- [ ] Validate EBITDA calculations against known values

### **Mobile Responsiveness Testing**  
- [ ] Test on iPhone 12/13/14 (Safari)
- [ ] Test on Samsung Galaxy S21+ (Chrome)
- [ ] Test on iPad (Safari)
- [ ] Verify all buttons are >44px touch targets
- [ ] Test filter forms in portrait/landscape

### **Performance Testing**
- [ ] Screener completes <30 seconds for S&P 500
- [ ] Progressive loading shows results within 5 seconds
- [ ] Cache hit rates >80% for repeat requests
- [ ] API rate limits respected across all sources

## 📝 **Notes**

- **Current Status**: Screener works but has ~70% "N/A" data for growth metrics
- **User Impact**: App appears broken due to missing data, but underlying functionality is solid
- **Priority**: Focus on data coverage first (Week 1) as it has highest user impact
- **Mobile**: Already improved with card view, further optimization can wait
- **Performance**: Progressive loading will dramatically improve perceived performance

---

*This TODO list should be reviewed and updated weekly as items are completed and new issues are discovered.*