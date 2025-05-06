def fetch_sec_frames_data(us_gaap_tags, start_year=2009, end_year=None):
    """
    Fetches financial data from SEC EDGAR API frames for specified US GAAP tags
    
    Args:
        us_gaap_tags (list): List of US GAAP taxonomy tags to fetch
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format
        
    Returns:
        dict: Dictionary with US GAAP tags as keys and their corresponding data as values
    """
    base_url = "https://data.sec.gov/api/xbrl/frames/"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov"
    }
    
    results = {}
    
    for tag in us_gaap_tags:
        try:
            # Construct URL with parameters
            url = f"{base_url}us-gaap/{tag}/USD/"
            if start_date:
                url += f"CY{start_date.split('-')[0]}"
            
            # Make API request
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            # Filter by date range if specified
            filtered_data = []
            for entry in data.get('data', []):
                if start_date and end_date:
                    entry_date = entry.get('filed')
                    if start_date <= entry_date <= end_date:
                        filtered_data.append(entry)
                else:
                    filtered_data.append(entry)
            
            results[tag] = filtered_data
            
        except Exception as e:
            print(f"Error fetching data for tag {tag}: {str(e)}")
            results[tag] = None
            
        # Add delay to avoid hitting rate limits
        time.sleep(0.1)
        
    return results
fetch_sec_frames_data(['NetIncomeLoss'])


