import pandas as pd
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import time 




def get_sp500_tickers():
    """
    Get list of S&P 500 tickers using pandas_datareader
    
    Returns:
        list: List of S&P 500 tickers
    """
    try:
        import pandas_datareader.data as web
        sp500 = web.DataReader(
            'sp500', 'wikipedia', 
            start=datetime.now()
        )
        return sp500.index.tolist()
    except Exception as e:
        print(f"Error fetching S&P 500 tickers: {str(e)}")
        return []



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


def download_sec_filing(filing_url):
    """
    Downloads SEC filing files from given URL and returns paths to downloaded files
    """
    try:
        import requests
        import os
        from urllib.parse import urljoin
        
        # Create directory to store files
        base_dir = "sec_filings"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        # Download main filing page
        response = requests.get(filing_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        downloaded_files = {}
        
        # Find and download all relevant files (XBRL, HTML)
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and (href.endswith('.xml') or href.endswith('.htm') or href.endswith('.html')):
                file_url = urljoin(filing_url, href)
                file_name = os.path.join(base_dir, os.path.basename(href))
                
                # Download file
                file_response = requests.get(file_url)
                with open(file_name, 'wb') as f:
                    f.write(file_response.content)
                
                downloaded_files[href.split('.')[-1]] = file_name
                
        return downloaded_files
        
    except Exception as e:
        print(f"Error downloading SEC filing: {str(e)}")
        return None

def parse_sec_filing(filing_url):
    """
    Main function to download and parse SEC filing files
    """
    try:
        # Download all filing files
        files = download_sec_filing(filing_url)
        if not files:
            return None
            
        all_data = {}
        
        # Parse XBRL file if available
        if 'xml' in files:
            xbrl_df = parse_xbrl_to_dataframe(files['xml'])
            all_data['xbrl_data'] = xbrl_df
        
        # Parse HTML file for text blocks and footnotes
        if 'htm' in files or 'html' in files:
            html_file = files.get('htm') or files.get('html')
            with open(html_file, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file, 'html.parser')
                
            # Extract text blocks and footnotes
            text_blocks = []
            footnotes = []
            
            # Find all div elements that might contain text blocks or footnotes
            for div in soup.find_all('div', class_=['textBlock', 'footnote']):
                block_data = {
                    'text': div.get_text(strip=True),
                    'type': 'text_block' if 'textBlock' in div.get('class', []) else 'footnote',
                    'id': div.get('id', ''),
                }
                if block_data['type'] == 'text_block':
                    text_blocks.append(block_data)
                else:
                    footnotes.append(block_data)
            
            all_data['text_blocks'] = pd.DataFrame(text_blocks)
            all_data['footnotes'] = pd.DataFrame(footnotes)
        
        return all_data
        
    except Exception as e:
        print(f"Error parsing SEC filing: {str(e)}")
        return None
# Test notebook for SEC filing functions

def create_test_notebook():
    """
    Creates a Jupyter notebook to test SEC filing download and parsing for Microsoft's 2024 10-K
    """
    import nbformat as nbf
    nb = nbf.v4.new_notebook()
    
    # Cell 1 - Imports
    cell1 = nbf.v4.new_code_cell('''
import pandas as pd
from bs4 import BeautifulSoup
import requests
from sec_filing_parser import download_sec_filing, parse_sec_filing
''')
    
    # Cell 2 - Microsoft 10-K URL
    cell2 = nbf.v4.new_code_cell('''
# Microsoft 2024 10-K filing URL
msft_10k_url = "https://www.sec.gov/Archives/edgar/data/789019/000156459024003825/msft-10k_20240630.htm"
''')
    
    # Cell 3 - Test download_sec_filing
    cell3 = nbf.v4.new_code_cell('''
# Test downloading the filing
files = download_sec_filing(msft_10k_url)
print("Downloaded files:", files.keys() if files else None)
''')
    
    # Cell 4 - Test parse_sec_filing
    cell4 = nbf.v4.new_code_cell('''
# Test parsing the filing
filing_data = parse_sec_filing(msft_10k_url)

if filing_data:
    print("\nAvailable data sections:", filing_data.keys())
    
    # Display XBRL data summary if available
    if 'xbrl_data' in filing_data:
        print("\nXBRL Data Preview:")
        print(filing_data['xbrl_data'].head())
    
    # Display text blocks summary if available
    if 'text_blocks' in filing_data:
        print("\nText Blocks Preview:")
        print(filing_data['text_blocks'].head())
    
    # Display footnotes summary if available
    if 'footnotes' in filing_data:
        print("\nFootnotes Preview:")
        print(filing_data['footnotes'].head())
else:
    print("Failed to parse filing")
''')
    
    # Add cells to notebook
    nb.cells.extend([cell1, cell2, cell3, cell4])
    
    # Save notebook
    with open('sec_filing_test.ipynb', 'w') as f:
        nbf.write(nb, f)
    
    print("Test notebook 'sec_filing_test.ipynb' has been created")
