from backend.core.resources import guarded_get
import os
import requests
import json
from datetime import datetime, timedelta
from backend.services.research import save_records

def get_sec_headers():
    """SEC requires User-Agent header for API access"""
    return {
        'User-Agent': os.getenv('SEC_USER_AGENT', 'StockScope research tool'),
        'Accept-Encoding': 'gzip, deflate'
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
        response = guarded_get(url, headers=get_sec_headers(), timeout=(5, 10))

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
        response = guarded_get(url, headers=get_sec_headers(), timeout=(5, 10))

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

        for i in range(min(len(forms), len(filing_dates), len(accession_numbers), len(primary_documents))):
            if len(results) >= limit:
                break
            form_type = forms[i]
            filing_date = filing_dates[i]
            accession = accession_numbers[i]
            doc = primary_documents[i]

            # Focus on key filing types that indicate sentiment - EXPANDED LIST
            if form_type in ['4', '8-K', '10-K', '10-Q', '13F', '13F-HR', 'SC 13G', 'SC 13D',
                           '25-NSE', '424B2', 'FWP', '3', '5', '11-K', 'DEF 14A']:
                # Create filing URL
                accession_clean = accession.replace('-', '')
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession_clean}/{doc}"

                results.append({
                    "form_type": form_type,
                    "filing_date": filing_date,
                    "accession_number": accession,
                    "url": filing_url,
                    "ticker": ticker,
                    "description": get_filing_description(form_type),
                    "source": "SEC",
                    "event_type": "filing",
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
        "25-NSE": "Removal from Listing and/or Registration",
        "13F-HR": "Institutional Investment Manager Holdings",
        "424B2": "Prospectus Supplement - Securities Offered Pursuant to Rule 424(b)(2)",
        "FWP": "Free Writing Prospectus",
        "3": "Initial Statement of Beneficial Ownership",
        "5": "Annual Statement of Changes in Beneficial Ownership",
        "11-K": "Annual Report of Employee Stock Purchase, Savings and Similar Plans",
        "DEF 14A": "Proxy Statement - Definitive Proxy Statement"
    }
    return descriptions.get(form_type, f"SEC Form {form_type}")

def fetch_sec_sentiment(ticker, limit=10):
    """Fetch filing events; the legacy function name is retained for callers."""
    print(f"🏛️ Fetching SEC filings for {ticker}...")

    filings = fetch_sec_filings(ticker, limit)

    if not filings:
        print(f"⚠️ No SEC filings data available for {ticker}")
        return None

    # Keep the filename for compatibility; records contain filing events, not sentiment.
    return save_records(ticker, "sec_sentiment", filings)

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
                print(f"   Source: {filing['url']}")
    else:
        print(f"❌ Failed to fetch SEC data for {ticker}")
