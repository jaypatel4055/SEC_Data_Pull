import requests
import os
from urllib.parse import urljoin
import pandas as pd
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import time 

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