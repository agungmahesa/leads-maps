import pandas as pd
from apify_client import ApifyClient
import re
import requests
from datetime import datetime, timezone

def extract_instagram(url):
    if not url:
        return ""
    if "instagram.com" in url:
        return url
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        match = re.search(r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_\.]+)', response.text)
        if match:
            username = match.group(1).rstrip('"\'>')
            return f"https://www.instagram.com/{username}"
    except:
        pass
    return ""

def calculate_days_ago(published_at_date):
    if not published_at_date:
        return 9999
    try:
        # Example: "2024-03-12T10:00:00Z" or "2024-03-12T10:00:00.000Z"
        if published_at_date.endswith('Z'):
            published_at_date = published_at_date.replace('Z', '+00:00')
        review_date = datetime.fromisoformat(published_at_date)
        now = datetime.now(timezone.utc)
        delta = now - review_date
        return max(0, delta.days)
    except Exception as e:
        pass
    return 9999

def extract_phone_from_ig_bio(instagram_url):
    if not instagram_url: return ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(instagram_url, headers=headers, timeout=5)
        phone_match = re.search(r'(08\d{8,11}|628\d{8,11}|\+628\d{8,11})', response.text.replace(" ", "").replace("-", ""))
        if phone_match:
            return phone_match.group(1)
    except:
        pass
    return ""

def format_whatsapp(phone_string):
    if not phone_string: return ""
    clean = re.sub(r'\D', '', str(phone_string))
    if not clean: return ""
    if clean.startswith("0"): clean = "62" + clean[1:]
    return f"https://wa.me/{clean}"

def crawl_google_maps(api_token, search_query, max_results=50, fetch_details=False):
    if not api_token:
        raise ValueError("Apify API Token is required!")
        
    # Initialize the ApifyClient
    client = ApifyClient(api_token)
    
    # Prepare the Actor input
    run_input = {
        "searchStringsArray": [search_query],
        "maxCrawledPlacesPerSearch": max_results,
        "language": "id",
        "maxReviews": 1,
        "reviewsSort": "newest"
    }
    
    print(f"Starting Apify Google Maps Scraper on: {search_query}...")
    
    try:
        # Run the Actor and wait for it to finish
        run = client.actor("compass/crawler-google-places").call(run_input=run_input)
    except Exception as e:
        raise Exception(f"Failed to start Apify actor: {str(e)}")
    
    results = []
    
    # Fetch results from the actor's dataset
    try:
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            
            # Parsing reviews to find newest
            last_review_text = ""
            days_ago = 9999
            
            reviews = item.get("reviews", [])
            if reviews and isinstance(reviews, list) and len(reviews) > 0:
                try:
                    # Sort reviews descending by date
                    reviews_sorted = sorted(reviews, key=lambda x: str(x.get("publishedAtDate", "")), reverse=True)
                    latest_review = reviews_sorted[0]
                    pub_date = latest_review.get("publishedAtDate", "")
                    days_ago = calculate_days_ago(pub_date)
                    last_review_text = latest_review.get("textTranslated", latest_review.get("text", "")) or pub_date
                except:
                    pass
                    
            website_url = item.get("website", "")
            instagram_url = extract_instagram(website_url) if fetch_details else ""
            
            # Logic for WhatsApp
            phone_raw = item.get("phone", "")
            if not phone_raw and instagram_url and fetch_details:
                phone_raw = extract_phone_from_ig_bio(instagram_url)
                
            whatsapp_url = format_whatsapp(phone_raw)
            
            data = {
                "name": item.get("title", ""),
                "rating": item.get("totalScore", ""),
                "reviews": item.get("reviewsCount", ""),
                "category": item.get("categoryName", ""),
                "address": item.get("address", ""),
                "phone": phone_raw,
                "whatsapp": whatsapp_url,
                "website": website_url,
                "instagram": instagram_url,
                "last_review": last_review_text[:50] + "..." if len(last_review_text) > 50 else last_review_text,
                "days_ago": days_ago
            }
            results.append(data)
    except Exception as e:
        raise Exception(f"Failed to parse Apify output: {str(e)}")
        
    return results
