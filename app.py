import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import traceback
import time

def initialize_driver():
    """Initialize the Selenium WebDriver with Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")

    try:
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"An error occurred while initializing the WebDriver: {str(e)}")
        return None

def click_live_button(driver):
    """Click the 'LIVE' button on the page."""
    try:
        live_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'filters__tab')]//div[contains(text(),'LIVE')]"))
        )
        ActionChains(driver).move_to_element(live_button).click().perform()
        return True
    except Exception as e:
        st.error(f"An error occurred while clicking the 'LIVE' button: {str(e)}")
        return False

def scrape_live_matches(driver):
    """Scrape live match details from the webpage."""
    match_details = []

    try:
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')

        # Gather all event titles
        event_titles = soup.find_all('div', class_='event__title')  # Use the correct class name
        full_urls = []
        for title in event_titles:
            link = title.find('a', class_='wcl-linkBase_CdaEq')
            if link and 'href' in link.attrs:
                link_href = link['href']
                full_url = f"https://www.diretta.it{link_href}"
                full_urls.append(full_url)        

        if not full_urls:
            st.warning("No live match links found.")
            return match_details

        # Process each full URL (main links)
        for idx, full_url in enumerate(full_urls, start=1):
            st.write(f"Processing {idx}/{len(full_urls)}: {full_url}")
            try:
                driver.execute_script(f"window.open('{full_url}', '_blank');")
                driver.switch_to.window(driver.window_handles[-1])
                
                new_page_content = driver.page_source
                new_soup = BeautifulSoup(new_page_content, 'html.parser')

                # Extract match details from the full link
                match_info = extract_match_info(new_soup, full_url)
                if match_info:
                    match_details.append(match_info)

                # Process sub-links
                sub_links = extract_sub_links(new_soup)
                for sub_link in sub_links:
                    try:
                        st.write(f"Processing sub-link: {sub_link}")
                        driver.execute_script(f"window.open('{sub_link}', '_blank');")
                        driver.switch_to.window(driver.window_handles[-1])
                        time.sleep(2)  # Wait for the sub-link page to load

                        sub_page_content = driver.page_source
                        sub_soup = BeautifulSoup(sub_page_content, 'html.parser')
                        
                        sub_match_info = extract_match_info(sub_soup, sub_link)
                        if sub_match_info:
                            match_details.append(sub_match_info)

                        driver.close()  # Close the sub-link tab
                        driver.switch_to.window(driver.window_handles[0])

                    except Exception as e:
                        st.error(f"An error occurred while processing sub-link {sub_link}: {str(e)}")
                        st.text(traceback.format_exc())
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                # Close full link tab after sub-links are processed
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            except Exception as e:
                st.error(f"An error occurred while processing {full_url}: {str(e)}")
                st.text(traceback.format_exc())
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

        return match_details

    except Exception as e:
        st.error(f"An error occurred while scraping live matches: {str(e)}")
        st.text(traceback.format_exc())
        return match_details

def extract_sub_links(soup):
    """Extract sub-links from the soup object."""
    sub_links = []
    try:
        sub_links_found = soup.find('section', class_='event event--summary').find_all('a', href=True)
        for sub_link in sub_links_found:
            sub_link_url = sub_link['href']
            if "https://www.diretta.it#" not in sub_link_url:
                sub_links.append(sub_link_url)  # Store the sub-link
        return sub_links
    except Exception as e:
        st.error(f"An error occurred while extracting sub-links: {str(e)}")
        return sub_links

def extract_match_info(soup, match_link):
    """Extract match information from the given soup object."""
    match_time = "N/A"
    home_team = "N/A"
    away_team = "N/A"
    home_score = "N/A"
    away_score = "N/A"
    status = "N/A"
    
    # Extract match time
    match_time_elem = soup.find('div', class_='duelParticipant__startTime')
    if match_time_elem:
        match_time = match_time_elem.get_text(strip=True)
    
    # Extract home team
    home_team_elem = soup.find('div', class_='duelParticipant__home')
    if home_team_elem:
        home_team_link = home_team_elem.find('a', class_='participant__participantName')
        if home_team_link:
            home_team = home_team_link.get_text(strip=True)
    
    # Extract away team
    away_team_elem = soup.find('div', class_='duelParticipant__away')
    if away_team_elem:
        away_team_link = away_team_elem.find('a', class_='participant__participantName')
        if away_team_link:
            away_team = away_team_link.get_text(strip=True)
    
    # Extract scores
    score_wrapper = soup.find('div', class_='detailScore__wrapper')
    if score_wrapper:
        scores = score_wrapper.find_all('span')
        if len(scores) >= 3:
            home_score = scores[0].get_text(strip=True)
            away_score = scores[2].get_text(strip=True)
    
    # Extract match status
    status_elem = soup.find('span', class_='fixedHeaderDuel__detailStatus')
    if status_elem:
        status = status_elem.get_text(strip=True)
    
    match_info = {
        "Match Time": match_time,
        "Home Team": home_team,
        "Away Team": away_team,
        "Home Score": home_score,
        "Away Score": away_score,
        "Status": status,
        "Match Link": match_link
    }
    
    # Filter out entries with both teams as "N/A"
    if home_team == "N/A" and away_team == "N/A":
        return None  # Exclude this match info
    
    return match_info

def main():
    st.title("Live Match Scraper")
    st.write("Enter the URL of the competition page to scrape live match details.")
    
    url = st.text_input("Enter URL:")
    
    if st.button("Scrape Live Matches"):
        if not url:
            st.warning("Please enter a valid URL.")
            return
        
        driver = initialize_driver()
        
        if not driver:
            st.error("WebDriver could not be initialized.")
            return

        driver.get(url)  # Navigate to the input URL
        
        if click_live_button(driver):
            match_details = scrape_live_matches(driver)
            if match_details:
                st.success("Scraping completed!")
                st.write(pd.DataFrame(match_details))  # Display the match details as a DataFrame
            else:
                st.warning("No match details found.")
        else:
            st.error("Failed to click the 'LIVE' button.")
        
        driver.quit()  # Close the driver after finishing the process

if __name__ == '__main__':
    main()
