# StockScope Pro - Advanced Stock Analytics & Sentiment Analysis Platform

**StockScope Pro** is a comprehensive financial analysis platform that combines real-time sentiment analysis with fundamental stock analytics. The platform aggregates data from social media, financial news, and SEC filings while providing deep fundamental analysis including company comparisons, stock screening, and AI-powered investment recommendations.

---

## 🚀 New Features

### Fundamentals Analytics Suite
- **📊 Individual Company Analysis** - Deep dive into company fundamentals with interactive charts
- **⚖️ Multi-Company Comparison** - Side-by-side analysis of financial metrics
- **🔍 Advanced Stock Screener** - Filter stocks by financial criteria and performance metrics
- **📈 Interactive Charting** - Quarterly revenue, margins, cash flow, and profitability trends
- **🤖 AI Investment Recommendations** - Intelligent BUY/SELL/HOLD suggestions with reasoning

### Enhanced User Experience
- **🎯 Intuitive Navigation** - Easy access to all analytics features from the main dashboard
- **⚡ Real-time Updates** - Live data synchronization across all components
- **📱 Responsive Design** - Optimized for desktop, tablet, and mobile devices
- **🔒 Secure Authentication** - Multi-level access control with role-based permissions

---

## 🏗️ How StockScope Pro Works Now

### 1. **Multi-Source Data Collection**
```
Social Media → Reddit API → Sentiment Analysis
Financial News → NewsAPI → Content Processing  
SEC Filings → SEC API → Document Analysis
Stock Data → yFinance → Fundamental Metrics
```

### 2. **Integrated Analytics Pipeline**
```
Raw Data → AI Processing → Sentiment Scores
↓
Fundamental Data → Financial Analysis → Key Metrics
↓
Combined Intelligence → Investment Recommendations
```

### 3. **User Journey & Features**

#### **Main Dashboard**
- **Portfolio Overview**: View all analyzed stocks with real-time prices
- **Quick Actions**: Direct access to fundamentals from stock cards
- **Navigation Hub**: Easy access to comparison, screening, and analysis tools

#### **Sentiment Analysis** (Original Core Feature)
1. **Search & Analyze**: Enter any stock symbol (AAPL, TSLA, etc.)
2. **Real-time Processing**: Background analysis of Reddit, news, and SEC data
3. **Comprehensive Dashboard**: Sentiment trends, source breakdown, and insights
4. **Investment Advice**: AI-powered recommendations with confidence scores

#### **Fundamentals Analytics** (New Features)
1. **Individual Analysis**: `/fundamentals/AAPL`
   - Revenue trends and growth rates
   - Profitability margins (FCF, Operating, EBITDA)
   - Quarterly performance charts
   - Year-over-year comparisons

2. **Company Comparison**: `/compare`
   - Select multiple companies for side-by-side analysis
   - Compare financial metrics across time periods
   - Visual performance comparisons
   - Relative valuation analysis

3. **Stock Screener**: `/screener`
   - Filter by market cap, sector, performance
   - Advanced financial criteria screening
   - Real-time filtering with instant results
   - Export and save screening results

---

## Architecture

### Frontend (Next.js 15)
- **React Query Integration** - Efficient data fetching and caching
- **TypeScript Throughout** - Full type safety across all components
- **Tailwind CSS 4** - Modern, responsive UI design
- **Recharts Integration** - Interactive financial charting
- **Client-side Routing** - Fast navigation between features

### Backend (FastAPI)
- **Modular Router System** - Separate endpoints for sentiment and fundamentals
- **Async Processing** - Non-blocking operations for better performance
- **Multi-level Caching** - Optimized response times with intelligent cache management
- **Comprehensive API** - RESTful endpoints for all features

### New Backend Structure
```
backend/
├── api.py                 # Main FastAPI application
├── routers/
│   └── fundamentals.py    # Fundamentals analytics endpoints
├── services/
│   └── fundamentals.py    # Business logic for financial analysis
├── models/
│   └── fundamentals.py    # Data models and schemas
└── core/
    └── cache.py          # Caching utilities
```

---

## 🔥 Key Features

### Real-Time Sentiment Analysis
- **Multi-source Aggregation**: Reddit, news, SEC filings
- **VADER NLP Processing**: Advanced sentiment scoring
- **Live Updates**: Real-time analysis with progress tracking
- **Historical Trends**: Track sentiment changes over time

### Advanced Fundamentals Analytics
- **Financial Metrics**: Revenue, margins, cash flow, profitability
- **Growth Analysis**: YoY comparisons and trend identification
- **Interactive Charts**: Quarterly data visualization
- **Comparative Analysis**: Multi-company side-by-side comparisons

### AI-Powered Insights
- **Investment Recommendations**: BUY/SELL/HOLD with confidence scores
- **Risk Assessment**: Volatility and trend analysis
- **Reasoning Engine**: Detailed explanations for all recommendations
- **Quantitative Strategies**: Multiple analysis approaches

### Professional Tools
- **Stock Screening**: Advanced filtering capabilities
- **Portfolio Management**: Bulk operations and organization
- **Data Export**: Download analysis results
- **Real-time Updates**: Live price and sentiment data

---

## 📊 API Endpoints

### Sentiment Analysis (Original)
- `GET /api/stocks` - Portfolio overview with metadata
- `POST /api/stocks/analyze` - Start sentiment analysis
- `GET /api/stocks/{symbol}` - Get sentiment analysis results
- `GET /api/stocks/{symbol}/investment-advice` - AI recommendations

### Fundamentals Analytics (New)
- `GET /fundamentals/{ticker}` - Individual company fundamentals
- `POST /fundamentals/compare` - Multi-company comparison
- `POST /fundamentals/screener` - Advanced stock screening
- `GET /api/stocks/{symbol}/info` - Company information

### Utility Endpoints
- `GET /api/stocks/suggestions` - Stock symbol autocomplete
- `POST /api/auth/login` - Authentication
- `GET /api/health` - System status

---

## 🛠️ Development Setup

### Prerequisites
- **Node.js 18+** and npm
- **Python 3.9+** and pip
- **Git** for version control

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/TahmidChowdhury/StockScope.git
cd StockScope

# 2. Setup Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Setup frontend
cd stockscope-frontend
npm install
cd ..

# 4. Configure authentication
cp .env.example .env
# Edit .env with your passwords:
ADMIN_PASSWORD=your_secure_password
STOCKSCOPE_PASSWORD=your_secure_password

# 5. Start development servers
cd stockscope-frontend
npm run dev &
cd .. && python backend/api.py
```

### One-Command Development

For the best development experience, use the custom development script:

```bash
# From the root directory
./dev-env.sh

# Or from frontend directory
npm run full-app
```

This starts both backend (port 8000) and frontend (port 3000) with hot reloading.

---

## 🎯 How to Use StockScope Pro

### 1. **Getting Started**
- Navigate to `http://localhost:3000`
- Login with your configured password
- Explore the main dashboard

### 2. **Sentiment Analysis Workflow**
```
Search Stock → Start Analysis → View Results → Get Recommendations
```
- Use the search bar to find stocks
- Click "Analyze" to start sentiment processing
- Monitor real-time progress
- Review comprehensive sentiment dashboard

### 3. **Fundamentals Analytics Workflow**
```
Main Dashboard → Choose Tool → Analyze → Compare → Make Decisions
```

#### **Individual Analysis**
- Click navigation card "Company Analysis"
- Search for any stock symbol
- View detailed fundamental metrics
- Analyze trends and performance

#### **Company Comparison**
- Click "⚖️ Compare Companies"
- Add multiple companies to comparison
- View side-by-side metrics
- Identify relative strengths/weaknesses

#### **Stock Screening**
- Click "🔍 Stock Screener"
- Set filtering criteria
- Browse filtered results
- Deep dive into interesting companies

### 4. **Portfolio Management**
- View all analyzed stocks on main dashboard
- Quick access to fundamentals via hover buttons
- Bulk delete operations for portfolio cleanup
- Real-time price updates for tracked stocks

---

## 🔒 Authentication System

StockScope Pro uses a secure multi-level authentication system:

### Access Levels
1. **Admin** - Full access to all features including data deletion
2. **Demo** - Read-only access for demonstrations
3. **Guest** - Limited public access

### Setup
```bash
# In your .env file
ADMIN_PASSWORD=StockScope_Admin_2025_Secure!
DEMO_PASSWORD=StockScope_Demo_2025
GUEST_PASSWORD=StockScope_Guest_2025
STOCKSCOPE_PASSWORD=StockScope_Admin_2025_Secure!  # Active password
```

All API endpoints require password authentication for security.

---

## Production Deployment

### Containerized Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build
```

The project includes optimized Dockerfiles for both frontend and backend components.

### Recommended Hosting

**Frontend**: Vercel (optimized for Next.js)
- Global CDN distribution
- Automatic deployments from Git
- Built-in performance optimization

**Backend**: Railway or Render
- Python-optimized hosting
- Environment variable management
- Automatic scaling

### Environment Variables

**Production Frontend**:
```env
NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

**Production Backend**:
```env
ADMIN_PASSWORD=your_secure_admin_password
DEMO_PASSWORD=your_demo_password
GUEST_PASSWORD=your_guest_password
STOCKSCOPE_PASSWORD=your_active_password

# Optional API keys for enhanced features
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
NEWS_API_KEY=your_news_api_key
```

---

## Performance Features

### Caching Strategy
- **API Response Caching** with configurable TTL
- **Smart Cache Invalidation** when new data arrives
- **Memory-efficient** storage with automatic cleanup
- **Multi-layer caching** for different data types

### Optimization
- **Background Task Processing** for analysis operations
- **Debounced Search** to reduce API calls
- **Progressive Loading** for large datasets
- **Response Compression** for faster data transfer

### Monitoring
- **Health Check Endpoints** for uptime monitoring
- **Structured Logging** for debugging and analytics
- **Error Tracking** with detailed stack traces
- **Performance Metrics** for response times

---

## Data Sources & Analysis

### Reddit Sentiment
- **Subreddits**: r/stocks, r/wallstreetbets, r/investing, r/SecurityAnalysis
- **Real-time Processing**: Live posts and comments analysis
- **Sentiment Scoring**: VADER NLP with confidence metrics

### Financial News
- **NewsAPI Integration**: Professional financial news sources
- **Article Analysis**: Headline and content sentiment scoring
- **Source Credibility**: Weighted scoring based on publication quality

### SEC Filings
- **Official Documents**: 10-K, 10-Q, 8-K filings analysis
- **Regulatory Sentiment**: Management discussion analysis
- **Filing Impact**: Historical correlation with stock performance

### AI Investment Advisor
- **Multi-factor Analysis**: Combines all data sources
- **Risk Assessment**: Volatility and trend analysis
- **Confidence Scoring**: Transparent recommendation reliability
- **Reasoning Engine**: Detailed explanation of recommendations

---

## Security & Privacy

### Data Protection
- **Environment Variables**: All credentials secured in .env files
- **Git Security**: Sensitive files excluded from version control
- **API Authentication**: Password protection on all endpoints
- **Input Validation**: Comprehensive request sanitization

### Best Practices
- **HTTPS Enforcement** in production
- **CORS Configuration** for secure cross-origin requests
- **Error Handling** without sensitive data exposure
- **Dependency Updates** for security patches

---

## Contributing

### Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/yourusername/StockScope.git
cd StockScope

# Create a feature branch
git checkout -b feature/your-feature-name

# Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd stockscope-frontend && npm install && cd ..

# Configure authentication
cp .env.example .env
# Edit .env with your passwords

# Start development
cd stockscope-frontend
npm run full-app

# Make your changes and test
# Commit and push
git commit -m "Add your feature description"
git push origin feature/your-feature-name
```

### Code Standards
- **TypeScript** for frontend type safety
- **Python Type Hints** for backend code
- **ESLint** for JavaScript/TypeScript linting
- **Prettier** for consistent code formatting

---

## License

MIT License - Use this code to build amazing investment tools!

---

## Acknowledgments

- **Next.js & Vercel** - Modern web development platform
- **FastAPI** - High-performance Python web framework
- **VADER Sentiment** - Robust sentiment analysis
- **Tailwind CSS** - Utility-first CSS framework
- **React & TypeScript** - Modern frontend development

---

## Created By

**Tahmid Chowdhury**  
Portfolio: https://tahmidchowdhury.github.io/ | GitHub: https://github.com/TahmidChowdhury

---

**From Social Sentiment to Smart Investment Decisions**  
*Built with Next.js 15, FastAPI, React Query, and Modern Financial Analytics*
