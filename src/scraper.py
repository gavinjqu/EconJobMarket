# TODO: Main logic with Selenium and Beautifulsoup
from selenium import webdriver
from bs4 import BeautifulSoup
import csv

# 1. Setup Selenium
options = webdriver.ChromeOptions()
options.add_argument('--headless') # Run without a visible window
driver = webdriver.Chrome(options=options)

def scrape_uni(url):
    driver.get(url)
    
    # 2. The Handoff
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # 3. BeautifulSoup Extraction
    jobs = []
    listings = soup.find_all('div', class_='job-card') # Change class to match site
    for item in listings:
        jobs.append({
            'title': item.find('h2').text.strip(),
            'link': item.find('a')['href']
        })
    return jobs

# 4. Save to CSV
def save_to_csv(data):
    keys = data[0].keys()
    with open('data/output/jobs.csv', 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)

# Run it
# data = scrape_uni('https://university-job-site.edu')
# save_to_csv(data)
# driver.quit()