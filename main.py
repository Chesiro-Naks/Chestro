import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
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

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)

def initialize_driver():
    """Initialize the Selenium WebDriver with Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")

    try:
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
        return driver
    except Exception as e:
        logging.error(f"An error occurred while initializing the WebDriver: {str(e)}")
        return None

def click_live_button(driver):
    """Click the 'LIVE' button on the page."""
    try:
        live_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'filters__tab')]//div[contains(text(),'LIVE')]"))
        )
        ActionChains(driver).move_to_element(live_button).click().perform()
        logging.info("Clicked the 'LIVE' button successfully.")
        return True
    except Exception as e:
        logging.error(f"An error occurred while clicking the 'LIVE' button: {str(e)}")
        return False

def scrape_live_matches(driver):
    """Scrape live match details from the webpage."""
    match_details = []

    try:
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')

        # Gather all event titles
        event_titles = soup.find_all('div', class_='event__title')
        full_urls = []
        for title in event_titles:
            link = title.find('a', class_='wcl-linkBase_CdaEq')
            if link and 'href' in link.attrs:
                link_href = link['href']
                full_url = f"https://www.diretta.it{link_href}"
                full_urls.append(full_url)

        if not full_urls:
            logging.warning("No live match links found.")
            return match_details

        # Process each full URL
        for full_url in full_urls:
            try:
                driver.get(full_url)
                time.sleep(5)  # Increase wait time for the page to load fully
                new_page_content = driver.page_source
                new_soup = BeautifulSoup(new_page_content, 'html.parser')

                # Extract match details from the full link
                match_info = extract_match_info(new_soup, full_url)
                if match_info and match_info["Home Team"] != "N/A" and match_info["Away Team"] != "N/A":
                    match_details.append(match_info)

                # Process sub-links
                sub_links = extract_sub_links(new_soup)
                for sub_link in sub_links:
                    try:
                        driver.get(sub_link)
                        time.sleep(5)  # Wait for the sub-link page to load fully
                        sub_page_content = driver.page_source
                        sub_soup = BeautifulSoup(sub_page_content, 'html.parser')

                        sub_match_info = extract_match_info(sub_soup, sub_link)
                        if sub_match_info and sub_match_info["Home Team"] != "N/A" and sub_match_info["Away Team"] != "N/A":
                            match_details.append(sub_match_info)

                    except Exception as e:
                        logging.error(f"An error occurred while processing sub-link {sub_link}: {str(e)}")
                        traceback.print_exc()

            except Exception as e:
                logging.error(f"An error occurred while processing {full_url}: {str(e)}")
                traceback.print_exc()

        return match_details

    except Exception as e:
        logging.error(f"An error occurred while scraping live matches: {str(e)}")
        traceback.print_exc()
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
        logging.error(f"An error occurred while extracting sub-links: {str(e)}")
        traceback.print_exc()
        return sub_links

def extract_match_info(soup, match_link):
    """Extract match information from the given soup object."""
    match_time = "N/A"
    home_team = "N/A"
    away_team = "N/A"
    home_score = "N/A"
    away_score = "N/A"
    status = "N/A"

    try:
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

    except Exception as e:
        logging.error(f"An error occurred while extracting match info: {str(e)}")
        traceback.print_exc()

    return {
        "Match Time": match_time,
        "Home Team": home_team,
        "Away Team": away_team,
        "Home Score": home_score,
        "Away Score": away_score,
        "Status": status,
        "Match Link": match_link
    }

def save_to_csv(match_details):
    """Save the match details to a CSV file."""
    df = pd.DataFrame(match_details)
    df.to_csv('live_match_details.csv', index=False)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Send me a URL to scrape live match details and get all links.")

async def handle_message(update: Update, context: CallbackContext):
    url = update.message.text
    await update.message.reply_text(f"Scraping live matches from: {url}")

    driver = initialize_driver()
    if not driver:
        await update.message.reply_text("WebDriver could not be initialized.")
        return

    try:
        driver.get(url)
        if click_live_button(driver):
            match_details = scrape_live_matches(driver)
            if match_details:
                save_to_csv(match_details)  # Save data to CSV
                await update.message.reply_text("Scraping completed! Sending you the CSV file.")
                
                # Send the CSV file to the user
                try:
                    with open('live_match_details.csv', 'rb') as csv_file:
                        await context.bot.send_document(chat_id=update.effective_chat.id, document=csv_file)
                except Exception as e:
                    logging.error(f"An error occurred while sending the CSV file: {str(e)}")
                    await update.message.reply_text("An error occurred while sending the CSV file.")

                # Send match details as messages
                for match in match_details:
                    match_info = (
                        f"{match['Match Time']} - {match['Home Team']} vs {match['Away Team']}\n"
                        f"Score: {match['Home Score']} - {match['Away Score']}\n"
                        f"Status: {match['Status']}\n"
                        f"Link: {match['Match Link']}\n\n"
                    )
                    await update.message.reply_text(match_info)
            else:
                await update.message.reply_text("No live match links found.")
        else:
            await update.message.reply_text("Failed to click the 'LIVE' button.")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        await update.message.reply_text("An error occurred during scraping. Please try again.")
    finally:
        driver.quit()

def main():
    app = Application.builder().token("7697105114:AAFkQ-uVxKaZRG97fzxIqRQtSiM-vaIMUjk").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
