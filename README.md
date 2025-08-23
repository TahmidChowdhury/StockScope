# StockScope Pro - Advanced Stock Sentiment Analysis Platform

**StockScope Pro** is a comprehensive real-time stock sentiment analysis platform that combines social media sentiment, financial news analysis, and SEC filings to provide AI-powered investment recommendations. Built with a modern Next.js frontend and optimized FastAPI backend for professional-grade performance.

---

## Architecture

### Frontend
- **Next.js 15** with Turbopack for blazing-fast development
- **React 19** with modern hooks and state management
- **TypeScript** for type safety and developer experience
- **Tailwind CSS 4** for responsive, modern UI design
- **Headless UI** for accessible component primitives

### Backend
- **FastAPI** with async/await for high-performance API endpoints
- **Python 3.9+** with comprehensive data analysis libraries
- **Pydantic** for data validation and serialization
- **In-memory caching** with TTL for optimized response times
- **Background task processing** for long-running analysis

### Data Sources
- **Reddit API** - Community sentiment from financial subreddits
- **NewsAPI** - Professional financial news analysis
- **SEC API** - Official regulatory document processing
- **VADER NLP** - Advanced sentiment analysis engine

---

## Key Features

### Real-Time Analysis
- **Live sentiment tracking** from multiple data sources
- **Background processing** with real-time status updates
- **Intelligent caching** for sub-second response times
- **Auto-refresh capabilities** with configurable intervals

### AI-Powered Insights
- **Investment recommendations** with confidence scores
- **Risk assessment** and trend analysis
- **Multi-source sentiment aggregation**
- **Quantitative strategy integration**

### Professional Dashboard
- **Modern dark theme** optimized for financial professionals
- **Responsive design** that works on all devices
- **Interactive charts** with real-time data updates
- **Portfolio management** with bulk operations

### Developer Experience
- **One-command startup** for development environment
- **Hot reloading** for both frontend and backend
- **TypeScript integration** with full type safety
- **Comprehensive error handling** and logging

---

## Quick Start

### Prerequisites
- **Node.js 18+** and npm
- **Python 3.9+** and pip
- **Git** for version control

### Installation

```bash
# Clone the repository
git clone https://github.com/TahmidChowdhury/StockScope.git
cd StockScope

# Install Python dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install Node.js dependencies
cd stockscope-frontend
npm install
cd ..
```

### Environment Setup

1. **Backend Environment** (optional - works with sample data):
```bash
cp .env.example .env
# Edit .env with your API keys if desired
```

2. **Frontend Environment**:
```bash
cd stockscope-frontend
cp .env.example .env.local
# API URL is pre-configured for local development
```

### Run the Application

**Single Command** (recommended):
```bash
cd stockscope-frontend
npm run full-app
```

This will start:
- **Backend API** on http://localhost:8000
- **Frontend App** on http://localhost:3000
- **API Documentation** on http://localhost:8000/docs

---

## API Endpoints

### Stock Analysis
- `GET /api/stocks` - List all analyzed stocks with metadata
- `GET /api/stocks/{symbol}` - Get comprehensive analysis for a stock
- `POST /api/stocks/analyze` - Start analysis for a new stock
- `GET /api/stocks/{symbol}/status` - Real-time analysis progress

### Investment Insights
- `GET /api/stocks/{symbol}/investment-advice` - AI-powered recommendations
- `GET /api/stocks/{symbol}/quantitative` - Quantitative strategy analysis

### Search & Discovery
- `GET /api/stocks/suggestions` - Smart stock symbol autocomplete
- `GET /api/health` - System health and metrics

### Administration
- `DELETE /api/cache` - Clear API cache (admin)

---

## Development Workflow

### Available Commands

```bash
# Development (run both servers)
npm run full-app

# Individual servers
npm run backend    # FastAPI only
npm run frontend   # Next.js only

# Utilities
npm run setup      # Install all dependencies
```

### Code Structure

```
StockScope/
├── backend/
│   └── api.py              # FastAPI application with caching
├── stockscope-frontend/
│   ├── src/
│   │   ├── app/            # Next.js app router
│   │   └── components/     # React components
│   └── package.json
├── analysis/               # AI analysis modules
├── scraping/              # Data collection scripts
├── data/                  # Sentiment analysis results
└── requirements.txt       # Python dependencies
```

---

## Production Deployment

### Containerized Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build
```

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
REDDIT_CLIENT_ID=your_reddit_client_id
NEWS_API_KEY=your_news_api_key
# ... other API keys
```

---

## Performance Features

### Caching Strategy
- **API Response Caching** with configurable TTL
- **Smart Cache Invalidation** when new data arrives
- **Memory-efficient** storage with automatic cleanup

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
- **Environment Variables**: All API keys secured in .env files
- **Git Security**: Sensitive files excluded from version control
- **API Rate Limiting**: Protection against abuse
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

# Make your changes and test
npm run full-app

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
*Built with Next.js, FastAPI, and Modern Web Technologies*
