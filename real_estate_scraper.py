# real_estate_scraper.py
import streamlit as st
import csv
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

# ======= Configuration =======
MAX_PAGES = 5
BASE_URL = "https://www.immoneuf.com"
CSV_HEADERS = ['City', 'Total Rank', 'Page Number', 'Page Rank', 'Title', 'URL', 'Code']

# ======= Streamlit UI =======
st.set_page_config(page_title="🏠 Real Estate Scraper", layout="wide")
st.title("Property Finder with Code p2720")

# User input
cities_input = st.text_input("Enter cities (comma-separated):", "Paris, Lyon")
cities = [c.strip() for c in cities_input.split(',') if c.strip()]

# ======= Browser Setup =======
@st.cache_resource
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920x1080")
    return uc.Chrome(options=chrome_options)

# ======= Core Scraping Functions =======
def search_city(driver, city_name):
    """Perform city search using the website's search bar"""
    driver.get(BASE_URL)
    
    # Accept cookies if present
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
        ).click()
        st.success("✅ Accepted cookies")
    except:
        pass
    
    # Locate search bar using provided XPath
    search_input = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div/div/div/div[2]/div/div/form/div[3]/input[1]"))
    )
    
    # Human-like typing
    search_input.clear()
    for char in city_name:
        search_input.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))
    
    # Select first suggestion
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.autocomplete-suggestion"))
    ).click()
    time.sleep(2)

def extract_listings(driver, city_name):
    """Extract and filter listings with p2720 code"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    listings = []
    
    for idx, item in enumerate(soup.select('a.item-thumb'), 1):
        try:
            href = item['href']
            if 'p2720' not in href:
                continue
                
            listings.append({
                'City': city_name,
                'Total Rank': idx,
                'Page Number': 1,  # Will update in pagination
                'Page Rank': idx,
                'Title': item.find('img')['alt'].strip(),
                'URL': f"{BASE_URL}{href}",
                'Code': href.split('/')[-1].split('?')[0]
            })
        except Exception as e:
            st.warning(f"⚠️ Error parsing listing: {str(e)}")
    
    return listings

def scrape_city(driver, city_name):
    """Full scraping workflow for a city"""
    all_results = []
    
    try:
        with st.status(f"Scraping {city_name}...", state="running"):
            search_city(driver, city_name)
            
            # Pagination handling
            page_number = 1
            while page_number <= MAX_PAGES:
                listings = extract_listings(driver, city_name)
                if not listings:
                    break
                
                # Update page numbers
                for listing in listings:
                    listing['Page Number'] = page_number
                
                all_results.extend(listings)
                
                # Try next page
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "a.next")
                    driver.execute_script("arguments[0].click();", next_btn)
                    page_number += 1
                    time.sleep(2)
                except:
                    break
            
            st.success(f"Found {len(all_results)} listings in {city_name}")
            
        return all_results
    
    except Exception as e:
        st.error(f"❌ Error processing {city_name}: {str(e)}")
        return []

# ======= Main Execution =======
if st.button("Start Scraping"):
    driver = get_driver()
    all_properties = []
    
    for city in cities:
        city_results = scrape_city(driver, city)
        all_properties.extend(city_results)
        time.sleep(random.uniform(1, 3))  # Avoid rate limiting
    
    driver.quit()
    
    # Generate CSV
    if all_properties:
        csv_data = []
        for idx, prop in enumerate(all_properties, 1):
            prop['Total Rank'] = idx
            csv_data.append(prop)
        
        # Create downloadable CSV
        st.download_button(
            label="Download CSV",
            data=csv.DictWriter(st, fieldnames=CSV_HEADERS).writeheader() + '\n'.join([csv.DictWriter(st, fieldnames=CSV_HEADERS).writerow(row) for row in csv_data]),
            file_name="property_results.csv",
            mime="text/csv"
        )
    else:
        st.warning("No listings found 😢")