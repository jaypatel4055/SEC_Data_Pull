def parse_xbrl_to_dataframe(xbrl_file_path):
    """
    Parse XBRL file and convert it to a pandas DataFrame
    
    Args:
        xbrl_file_path (str): Path to the XBRL file
        
    Returns:
        pandas.DataFrame: DataFrame containing the XBRL data
    """
    try:
        # Import required libraries
        import pandas as pd
        from bs4 import BeautifulSoup
        
        # Read and parse XBRL file
        with open(xbrl_file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'xml')
        
        # Initialize lists to store data
        contexts = {}
        data = []
        
        # Extract contexts
        context_elements = soup.find_all('context')
        for context in context_elements:
            context_id = context.get('id')
            period = context.find('period')
            if period:
                instant = period.find('instant')
                if instant:
                    contexts[context_id] = instant.text
                else:
                    start_date = period.find('startDate')
                    end_date = period.find('endDate')
                    if start_date and end_date:
                        contexts[context_id] = f"{start_date.text} to {end_date.text}"
        
        # Extract facts
        for tag in soup.find_all():
            if tag.name != 'context' and tag.get('contextRef'):
                fact = {
                    'concept': tag.name,
                    'value': tag.text.strip(),
                    'context_ref': tag.get('contextRef'),
                    'period': contexts.get(tag.get('contextRef'), ''),
                    'unit': tag.get('unitRef', ''),
                    'decimals': tag.get('decimals', '')
                }
                data.append(fact)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        return df
        
    except Exception as e:
        print(f"Error parsing XBRL file: {str(e)}")
        return None

def get_ticker_to_cik_mapping():
    """
    Get mapping of stock tickers to CIK numbers from SEC
    
    Returns:
        dict: Dictionary mapping tickers to CIK numbers
    """
    import requests
    
    headers = {
        'User-Agent': 'Your Name (your.email@domain.com)'
    }
    
    try:
        # Get the company tickers mapping file from SEC
        response = requests.get(
            'https://www.sec.gov/files/company_tickers.json',
            headers=headers
        )
        response.raise_for_status()
        
        # Convert to dictionary with ticker as key and CIK as value
        ticker_cik_mapping = {}
        for item in response.json().values():
            ticker_cik_mapping[item['ticker']] = str(item['cik_str']).zfill(10)
            
        return ticker_cik_mapping
    except Exception as e:
        print(f"Error fetching CIK mapping: {str(e)}")
        return {}

def get_sp500_sec_filings(filing_types=['10-K', '10-Q'], start_date=None, end_date=None):
    """
    Get SEC filing links for S&P 500 companies
    
    Args:
        filing_types (list): List of filing types to fetch (default: ['10-K', '10-Q'])
        start_date (str): Start date in YYYY-MM-DD format (default: None)
        end_date (str): End date in YYYY-MM-DD format (default: None)
        
    Returns:
        list: List of dictionaries containing filing information and links
    """
    import requests
    import pandas as pd
    from datetime import datetime, timedelta
    import time

    # Get S&P 500 tickers
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        tickers = sp500['Symbol'].tolist()
    except Exception as e:
        print(f"Error fetching S&P 500 tickers: {str(e)}")
        return []

    # Get ticker to CIK mapping
    ticker_cik_mapping = get_ticker_to_cik_mapping()
    if not ticker_cik_mapping:
        return []

    # Set default dates if not provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    # Initialize results list
    filing_links = []

    # SEC EDGAR API headers
    headers = {
        'User-Agent': 'Your Name (your.email@domain.com)'
    }

    # Process each ticker
    for ticker in tickers:
        try:
            # Skip if ticker not found in mapping
            if ticker not in ticker_cik_mapping:
                print(f"No CIK found for ticker: {ticker}")
                continue

            # Respect SEC EDGAR's rate limiting (10 requests per second)
            time.sleep(0.1)
            
            # Get CIK and construct API URL
            cik = ticker_cik_mapping[ticker]
            base_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            
            # Make API request
            response = requests.get(base_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Get recent filings
                for filing in data.get('filings', {}).get('recent', {}).get('accessionNumber', []):
                    filing_index = data['filings']['recent']['accessionNumber'].index(filing)
                    
                    # Get filing type and date
                    filing_type = data['filings']['recent']['form'][filing_index]
                    filing_date = data['filings']['recent']['filingDate'][filing_index]
                    
                    # Check if filing type matches and is within date range
                    if (filing_type in filing_types and 
                        start_date <= filing_date <= end_date):
                        
                        # Construct document URL
                        accession_number = filing.replace('-', '')
                        doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number}"
                        
                        filing_links.append({
                            'ticker': ticker,
                            'cik': cik,
                            'company_name': data.get('name', ''),
                            'filing_type': filing_type,
                            'filing_date': filing_date,
                            'accession_number': filing,
                            'filing_url': doc_url,
                            'interactive_url': f"{doc_url}/index.json",
                            'documents_url': f"{doc_url}/FilingSummary.xml"
                        })
                        
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
            continue

    return filing_links


    

