import os
import time
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import schedule

# Telegram Bot Token
TOKEN = "7843954209:AAFke64Fi-4wuKo8b-mfjkqw6Q0Mzjg1Mmk"

# List of user IDs for broadcasting
user_ids = []

# ==================== SELENIUM SETUP ==========================
def initialize_driver():
    """Initialize Selenium WebDriver with Chrome options."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    try:
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {str(e)}")
        return None

# ==================== SCRAPER FUNCTIONS ==========================
def scrape_live_matches():
    """Scrapes live match data and returns it as a formatted message."""
    driver = initialize_driver()
    if not driver:
        return "Error: WebDriver could not be initialized."

    url = "https://www.diretta.it"  # Set the correct URL here
    driver.get(url)
    time.sleep(3)  # Adjust sleep for page load time

    match_details = []
    try:
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        event_titles = soup.find_all('div', class_='event__title')

        for title in event_titles:
            link = title.find('a', class_='wcl-linkBase_CdaEq')
            if link and 'href' in link.attrs:
                full_url = f"https://www.diretta.it{link['href']}"
                match_info = extract_match_info(full_url)
                if match_info:
                    match_details.append(match_info)

        driver.quit()
        return format_match_details(match_details)
    except Exception as e:
        driver.quit()
        return f"Error scraping live matches: {str(e)}"

def extract_match_info(match_link):
    """Extracts detailed match information from the given match link."""
    match_info = {
        "Match Time": "N/A",
        "Home Team": "N/A",
        "Away Team": "N/A",
        "Home Score": "N/A",
        "Away Score": "N/A",
        "Status": "N/A",
        "Match Link": match_link
    }

    driver = initialize_driver()
    if not driver:
        return None

    try:
        driver.get(match_link)
        time.sleep(3)  # Adjust sleep for page load time
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract match details
        match_time_elem = soup.find('div', class_='duelParticipant__startTime')
        if match_time_elem:
            match_info["Match Time"] = match_time_elem.get_text(strip=True)

        home_team_elem = soup.find('div', class_='duelParticipant__home')
        if home_team_elem:
            home_team_link = home_team_elem.find('a', class_='participant__participantName')
            if home_team_link:
                match_info["Home Team"] = home_team_link.get_text(strip=True)

        away_team_elem = soup.find('div', class_='duelParticipant__away')
        if away_team_elem:
            away_team_link = away_team_elem.find('a', class_='participant__participantName')
            if away_team_link:
                match_info["Away Team"] = away_team_link.get_text(strip=True)

        score_wrapper = soup.find('div', class_='detailScore__wrapper')
        if score_wrapper:
            scores = score_wrapper.find_all('span')
            if len(scores) >= 3:
                match_info["Home Score"] = scores[0].get_text(strip=True)
                match_info["Away Score"] = scores[2].get_text(strip=True)

        status_elem = soup.find('span', class_='fixedHeaderDuel__detailStatus')
        if status_elem:
            match_info["Status"] = status_elem.get_text(strip=True)

        if match_info["Home Team"] == "N/A" and match_info["Away Team"] == "N/A":
            return None

        return match_info
    except Exception as e:
        print(f"Error extracting match info: {str(e)}")
        return None
    finally:
        driver.quit()

def format_match_details(matches):
    """Formats scraped match details into a readable message."""
    if not matches:
        return "No live matches found."
    return "\n\n".join(f"{match['Home Team']} vs {match['Away Team']}: {match['Status']}" for match in matches)

# ==================== TELEGRAM BOT FUNCTIONS ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcomes the user and subscribes them for updates."""
    uid = update.message.chat_id
    if uid not in user_ids:
        user_ids.append(uid)
    await context.bot.send_message(chat_id=uid, text="Welcome to the Live Match Bot! You’ll receive updates on live matches.")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Immediately scrapes live matches and sends the results to the user."""
    message = scrape_live_matches()
    await context.bot.send_message(chat_id=update.message.chat_id, text=message)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcasts the scraped live matches to all users."""
    message = scrape_live_matches()
    await broadcast_message(message)

async def broadcast_message(message):
    """Sends a message to all users."""
    bot = telegram.Bot(TOKEN)
    for uid in user_ids:
        await bot.send_message(chat_id=uid, text=message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the help message."""
    help_text = (
        "Available commands:\n"
        "/start - Start the bot and subscribe for updates.\n"
        "/live - Scrape live matches immediately.\n"
        "/broadcast - Broadcast live match updates to all subscribers."
    )
    await context.bot.send_message(chat_id=update.message.chat_id, text=help_text)

# ==================== SCHEDULING & MAIN FUNCTION ==========================
def job():
    """Scheduled job to scrape and broadcast live match data."""
    message = scrape_live_matches()
    broadcast_message(message)

def main():
    """Main function to run the bot and schedule the scraper job."""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("live", live))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("help", help_command))

    # Schedule the job every day at a specific time
    schedule.every().day.at("10:00").do(job)  # Adjust time as needed

    # Run the bot
    application.run_polling()

    # Run scheduled jobs in a loop
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
