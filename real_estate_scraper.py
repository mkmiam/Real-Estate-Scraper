import  streamlit as st
import csv
import time
import random
import io
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
cities = [c.strip().lower() for c in cities_input.split(',') if c.strip()]

# ======= Browser Setup =======
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920x1080")
    
    try:
        driver = uc.Chrome(options=chrome_options)  # Remove version_main and binary_location
        return driver
    except Exception as e:
        st.error(f"❌ Error initializing ChromeDriver: {str(e)}")
        return None

# ======= Cloudflare Bypass =======
def bypass_cloudflare(driver):
    """Handle Cloudflare protection"""
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception as e:
        print(f"❌ Cloudflare challenge failed: {str(e)}")
        raise

# ======= Core Scraping Functions =======
def search_city(driver, city_name):
    """Perform city search using the website's search bar"""
    driver.get(BASE_URL)
    
    # Bypass Cloudflare
    bypass_cloudflare(driver)
    
    # Accept cookies if present
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/div/div[1]/div/div/div[1]/div[1]/div[1]/div[1]/button/span"))
        ).click()
        st.success("✅ Clicked 'Do not accept' for cookies")
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
    for _ in range(3):  # Retry up to 3 times
        try:
            first_suggestion = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.ui-menu-item"))
            )
            first_suggestion.click()
            st.success(f"✅ Selected first suggestion for {city_name}")
            break
        except Exception as e:
            st.error(f"❌ Error selecting first suggestion for {city_name}: {str(e)}")
            time.sleep(1)  # Wait a bit before retrying
    
    # Click the "Rechercher" button
    try:
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input.btn.btn-full-width.btn-green"))
        )
        search_button.click()
        st.success("✅ Clicked 'Rechercher' button")
    except Exception as e:
        st.error(f"❌ Error clicking 'Rechercher' button: {str(e)}")
    
    time.sleep(2)

def extract_listings(driver, city_name):
    """Extract and filter listings with p2720 code and nearby city detection"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    listings = []
    
    for idx, item in enumerate(soup.select('a.item-thumb'), 1):
        try:
            href = item['href']
            if 'p2720' not in href:
                continue
            
            title = item.find('img')['alt'].strip()
            full_url = f"{BASE_URL}{href}"
            listing_code = href.split('/')[-1].split('?')[0]
            
            # Normalize city name in title and href
            normalized_title = title.replace(" ", "").lower()
            normalized_href = href.replace(" ", "").lower()
            
            # Check if the offer city is similar to the searched city
            if city_name in normalized_title or city_name in normalized_href:
                listings.append({
                    'City': city_name,
                    'Total Rank': idx,
                    'Page Number': 1,  # Will update in pagination
                    'Page Rank': idx,
                    'Title': title,
                    'URL': full_url,
                    'Code': listing_code
                })
            else:
                st.warning(f"⚠️ Possible different city detected: {title} ({full_url})")
        except Exception as e:
            st.warning(f"⚠️ Error parsing listing: {str(e)}")
    
    st.info(f"Extracted {len(listings)} listings for {city_name}")
    return listings

def scrape_city(city_name):
    """Full scraping workflow for a city"""
    driver = get_driver()
    if not driver:
        return []
    
    all_results = []
    
    try:
        with st.spinner(f"Scraping {city_name}..."):
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
                    next_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.LINK_TEXT, "Suivante"))
                    )
                    driver.execute_script("arguments[0].click();", next_btn)
                    st.info(f"Clicked next button for page {page_number}")
                    page_number += 1
                    time.sleep(2)
                except Exception as e:
                    st.warning(f"⚠️ No more pages or error clicking next button: {str(e)}")
                    break
                    
            st.success(f"Found {len(all_results)} listings in {city_name}")
            
        return all_results
    
    except Exception as e:
        st.error(f"❌ Error processing {city_name}: {str(e)}")
        return []
    
    finally:
        driver.quit()

# ======= Main Execution =======
if st.button("Start Scraping"):
    all_properties = []
    
    for city in cities:
        st.info(f"Starting to scrape {city}")
        city_results = scrape_city(city)
        st.info(f"Scraped {len(city_results)} listings for {city}")
        all_properties.extend(city_results)
    
    # Generate CSV
    if all_properties:
        csv_data = io.StringIO()
        writer = csv.DictWriter(csv_data, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for idx, prop in enumerate(all_properties, 1):
            prop['Total Rank'] = idx
            writer.writerow(prop)
        
        # Create downloadable CSV
        st.download_button(
            label="Download CSV",
            data=csv_data.getvalue(),
            file_name="property_results.csv",
            mime="text/csv"
        )
    else:
        st.warning("No listings found 😢")