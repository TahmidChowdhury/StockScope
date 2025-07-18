import os
import requests
import json
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def classify_sentiment(compound):
    if compound >= 0.05:
        return "positive"
    elif compound <= -0.05:
        return "negative"
    else:
        return "neutral"

def get_sec_headers():
    """SEC requires User-Agent header for API access"""
    return {
        'User-Agent': 'StockScope Sentiment Analysis Tool (contact@stockscope.app)',
        'Accept-Encoding': 'gzip, deflate',
        'Host': 'data.sec.gov'
    }

def get_company_cik(ticker):
    """Get Company CIK (Central Index Key) from ticker symbol"""
    # Common ticker to CIK mappings
    TICKER_CIK_MAP = {
        "AAPL": "0000320193",
        "MSFT": "0000789019", 
        "GOOGL": "0001652044",
        "AMZN": "0001018724",
        "TSLA": "0001318605",
        "META": "0001326801",
        "NVDA": "0001045810",
        "NFLX": "0001065280",
        "PLTR": "0001321655",
        "RKLB": "0001819994"
    }
    
    cik = TICKER_CIK_MAP.get(ticker.upper())
    if cik:
        return cik
    
    # Fallback: Search for CIK using SEC company tickers API
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers=get_sec_headers())
        
        if response.status_code == 200:
            companies = response.json()
            for company_data in companies.values():
                if company_data.get('ticker', '').upper() == ticker.upper():
                    cik = str(company_data['cik_str']).zfill(10)
                    return cik
    except Exception as e:
        print(f"⚠️ Could not find CIK for {ticker}: {e}")
    
    return None

def fetch_sec_filings(ticker, limit=10):
    """Fetch recent SEC filings for a company"""
    cik = get_company_cik(ticker)
    if not cik:
        print(f"❌ Could not find CIK for ticker {ticker}")
        return []
    
    # SEC EDGAR API endpoint for company filings
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    
    try:
        response = requests.get(url, headers=get_sec_headers())
        
        if response.status_code != 200:
            print(f"❌ SEC API error: {response.status_code}")
            return []
        
        data = response.json()
        filings = data.get('filings', {}).get('recent', {})
        
        if not filings:
            print(f"⚠️ No recent filings found for {ticker}")
            return []
        
        # Process filings
        results = []
        forms = filings.get('form', [])
        filing_dates = filings.get('filingDate', [])
        accession_numbers = filings.get('accessionNumber', [])
        primary_documents = filings.get('primaryDocument', [])
        
        for i in range(min(limit, len(forms))):
            form_type = forms[i]
            filing_date = filing_dates[i]
            accession = accession_numbers[i]
            doc = primary_documents[i]
            
            # Focus on key filing types that indicate sentiment - EXPANDED LIST
            if form_type in ['4', '8-K', '10-K', '10-Q', '13F', 'SC 13G', 'SC 13D', 
                           '25-NSE', '424B2', 'FWP', '3', '5', '11-K', 'DEF 14A']:
                # Create filing URL
                accession_clean = accession.replace('-', '')
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession_clean}/{doc}"
                
                # Determine filing sentiment context
                sentiment_context = get_filing_sentiment_context(form_type, ticker)
                sentiment = analyzer.polarity_scores(sentiment_context)
                
                results.append({
                    "form_type": form_type,
                    "filing_date": filing_date,
                    "accession_number": accession,
                    "url": filing_url,
                    "ticker": ticker,
                    "description": get_filing_description(form_type),
                    "sentiment_context": sentiment_context,
                    "sentiment": {
                        **sentiment,
                        "label": classify_sentiment(sentiment["compound"])
                    }
                })
        
        print(f"📄 Found {len(results)} SEC filings for {ticker}")
        return results
        
    except Exception as e:
        print(f"❌ Error fetching SEC data for {ticker}: {e}")
        return []

def get_filing_description(form_type):
    """Get human-readable description of SEC form types"""
    descriptions = {
        "4": "Insider Trading - Statement of Changes in Beneficial Ownership",
        "8-K": "Current Report - Major Corporate Events",
        "10-K": "Annual Report - Comprehensive Company Overview", 
        "10-Q": "Quarterly Report - Financial Performance Update",
        "13F": "Institutional Investment Manager Holdings",
        "SC 13G": "Beneficial Ownership Report (Passive)",
        "SC 13D": "Beneficial Ownership Report (Active)",
        "25-NSE": "Notice of Exempt Offering of Securities",
        "424B2": "Prospectus Supplement - Securities Offered Pursuant to Rule 424(b)(2)",
        "FWP": "Free Writing Prospectus",
        "3": "Initial Statement of Beneficial Ownership",
        "5": "Annual Statement of Changes in Beneficial Ownership",
        "11-K": "Annual Report of Employee Stock Purchase, Savings and Similar Plans",
        "DEF 14A": "Proxy Statement - Definitive Proxy Statement"
    }
    return descriptions.get(form_type, f"SEC Form {form_type}")

def get_filing_sentiment_context(form_type, ticker):
    """Generate sentiment context based on filing type for analysis"""
    contexts = {
        "4": f"Insider trading activity for {ticker}. Corporate executives or directors bought or sold shares, indicating their confidence in company prospects.",
        "8-K": f"Major corporate event announced for {ticker}. This current report indicates significant business developments that could impact stock performance.",
        "10-K": f"Annual comprehensive report filed for {ticker}. This detailed financial disclosure provides full business outlook and risk assessment.",
        "10-Q": f"Quarterly financial update for {ticker}. Regular business performance report showing recent financial health and operational results.",
        "13F": f"Institutional investment activity in {ticker}. Large fund managers disclosed their holdings, showing institutional confidence levels.",
        "SC 13G": f"Passive beneficial ownership filing for {ticker}. Large shareholder disclosed significant position without intent to influence control.",
        "SC 13D": f"Active beneficial ownership filing for {ticker}. Large shareholder disclosed significant position with potential intent to influence company direction.",
        "25-NSE": f"Notice of exempt offering of securities for {ticker}. Indicates a private placement of securities without registration.",
        "424B2": f"Prospectus supplement for {ticker}. Provides details of securities offered, including pricing and underwriting.",
        "FWP": f"Free writing prospectus for {ticker}. Offers additional information about a security offering, often used for complex securities.",
        "3": f"Initial statement of beneficial ownership for {ticker}. Filed by insiders to report their ownership stakes in the company.",
        "5": f"Annual statement of changes in beneficial ownership for {ticker}. Filed by insiders to report changes in their ownership stakes.",
        "11-K": f"Annual report of employee stock purchase, savings and similar plans for {ticker}. Provides information on company-sponsored employee benefit plans.",
        "DEF 14A": f"Definitive proxy statement for {ticker}. Provides details on matters to be voted on at the company's annual meeting, including executive compensation."
    }
    return contexts.get(form_type, f"SEC regulatory filing for {ticker}")

def fetch_sec_sentiment(ticker, limit=10):
    """Main function to fetch and analyze SEC filing sentiment"""
    print(f"🏛️ Fetching SEC filings for {ticker}...")
    
    filings = fetch_sec_filings(ticker, limit)
    
    if not filings:
        print(f"⚠️ No SEC filings data available for {ticker}")
        return None
    
    # Save results
    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", f"{ticker}_sec_sentiment.json")
    
    with open(output_path, "w") as f:
        json.dump(filings, f, indent=2)
    
    print(f"✅ Saved {len(filings)} SEC filings to {output_path}")
    return output_path

# Run this script standalone with a test ticker
if __name__ == "__main__":
    ticker = "AAPL"
    result_path = fetch_sec_sentiment(ticker)
    
    if result_path:
        print(f"✅ Successfully analyzed SEC filings for {ticker}")
        
        # Show a sample of the data
        with open(result_path, 'r') as f:
            data = json.load(f)
            print(f"\n📊 Sample of {len(data)} SEC filings:")
            for i, filing in enumerate(data[:3]):
                print(f"{i+1}. {filing['form_type']}: {filing['description']}")
                print(f"   Filed: {filing['filing_date']}")
                print(f"   Sentiment: {filing['sentiment']['label']} ({filing['sentiment']['compound']:.3f})")
    else:
        print(f"❌ Failed to fetch SEC data for {ticker}")