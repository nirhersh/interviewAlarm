from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)


class NeedleScraperError(Exception):
    """Custom exception for scraper errors"""
    pass


def scrape_needle_page(url: str) -> Dict:
    """
    Scrape a needle.co.il interview scheduling page using Selenium

    This function handles already-booked interview pages by:
    1. Clicking "Change or cancel interview" button
    2. Clicking "Change interview date" button
    3. Extracting available time slots from the calendar interface

    Args:
        url: The needle.co.il candidate-slots URL

    Returns:
        Dictionary with:
        - company_name: Name of the company
        - slots: List of time slots with start_time and end_time

    Raises:
        NeedleScraperError: If scraping fails
    """
    driver = None
    try:
        # Validate URL
        if not url.startswith("https://needle.co.il/candidate-slots/"):
            raise NeedleScraperError("Invalid URL. Must be a needle.co.il candidate-slots URL")

        # Set up Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--lang=he-IL")  # Hebrew locale
        chrome_options.add_argument("--remote-debugging-port=9222")  # For WSL compatibility

        # Try to find Chrome binary (prefer Windows Chrome on WSL)
        import shutil
        import os
        chrome_binary = None

        # Check for Windows Chrome first (for WSL environments)
        windows_chrome_paths = [
            '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe',
            '/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe',
        ]

        for win_path in windows_chrome_paths:
            if os.path.exists(win_path):
                chrome_binary = win_path
                logger.info(f"Found Windows Chrome: {chrome_binary}")
                break

        # If no Windows Chrome, try Linux binaries
        if not chrome_binary:
            for binary_name in ['google-chrome', 'chromium-browser', 'chromium', 'google-chrome-stable']:
                binary_path = shutil.which(binary_name)
                if binary_path:
                    chrome_binary = binary_path
                    logger.info(f"Found Linux browser: {chrome_binary}")
                    break

        # Set the Chrome binary location if found
        if chrome_binary:
            chrome_options.binary_location = chrome_binary

        # Initialize the Chrome driver using webdriver-manager
        # It will automatically download the correct ChromeDriver version
        try:
            # Get the driver path from webdriver-manager
            driver_path = ChromeDriverManager().install()

            # Fix path if webdriver-manager returns the wrong file
            # Sometimes it points to THIRD_PARTY_NOTICES instead of chromedriver
            if 'THIRD_PARTY_NOTICES' in driver_path:
                # Get the directory and find the actual chromedriver
                import os as path_os
                driver_dir = path_os.path.dirname(driver_path)
                actual_driver = path_os.path.join(driver_dir, 'chromedriver')
                if path_os.path.exists(actual_driver):
                    driver_path = actual_driver
                    logger.info(f"Fixed driver path to: {driver_path}")

            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            raise NeedleScraperError(
                f"Failed to start Chrome browser.\n"
                f"Make sure Google Chrome is installed.\n"
                f"Original error: {str(e)}"
            )

        logger.info(f"Navigating to {url}")
        driver.get(url)

        # Wait for page to load
        wait = WebDriverWait(driver, 15)

        # Extract company name early (from page title or logo)
        company_name = extract_company_name_from_page(driver)

        # Click "Change or cancel interview" button (שינוי או ביטול הראיון)
        try:
            change_cancel_button = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[.//span[contains(text(), 'שינוי או ביטול')]]"
                ))
            )
            change_cancel_button.click()
            logger.info("Clicked 'Change or cancel interview' button")
            time.sleep(1)
        except TimeoutException:
            raise NeedleScraperError(
                "Could not find 'Change or cancel interview' button. "
                "This might not be a booked interview page."
            )

        # Click "Change interview date" button (שינוי מועד הראיון)
        try:
            change_date_button = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[.//span[contains(text(), 'שינוי מועד')]]"
                ))
            )
            change_date_button.click()
            logger.info("Clicked 'Change interview date' button")
            time.sleep(2)  # Wait for calendar to load
        except TimeoutException:
            raise NeedleScraperError(
                "Could not find 'Change interview date' button"
            )

        # Extract available time slots
        slots = extract_time_slots_from_calendar(driver, wait)

        logger.info(f"Extracted {len(slots)} time slots")

        return {
            "company_name": company_name,
            "slots": slots
        }

    except WebDriverException as e:
        raise NeedleScraperError(f"Browser automation error: {str(e)}")
    except Exception as e:
        if isinstance(e, NeedleScraperError):
            raise
        raise NeedleScraperError(f"Unexpected error while scraping: {str(e)}")
    finally:
        if driver:
            driver.quit()


def extract_company_name_from_page(driver) -> str:
    """Extract company name from the page"""
    try:
        # Try to get from page title
        title = driver.title
        if title and title != "Needle":
            return title

        # Try to find company name in the page content
        # Look for firm/company information in various places
        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Look for any heading or text that might be the company name
            # This is a best-effort approach
            headings = soup.find_all(['h1', 'h2', 'h3'])
            for heading in headings:
                text = heading.get_text(strip=True)
                # Skip common Hebrew phrases that aren't company names
                if text and text not in ['הראיון נקבע בהצלחה', 'שינוי או ביטול הראיון']:
                    return text
        except Exception:
            pass

        return "Unknown Company"

    except Exception:
        return "Unknown Company"


def extract_time_slots_from_calendar(driver, wait) -> List[Dict]:
    """
    Extract available time slots from the calendar interface

    The slots appear as buttons after clicking on different days in the calendar
    """
    all_slots = []

    try:
        # Wait for calendar to be visible
        time.sleep(1)

        # Get the current page source and parse it
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Strategy 1: Look for time slot buttons in the current view
        # Time slots are usually displayed as clickable buttons with time text
        time_buttons = driver.find_elements(By.XPATH,
            "//button[contains(@class, 'ant-btn') and contains(., ':')]"
        )

        # Extract times from visible buttons
        for button in time_buttons:
            try:
                button_text = button.text.strip()
                # Check if it looks like a time (contains ':')
                if ':' in button_text and len(button_text) <= 10:
                    # This is likely a time slot
                    # We need to construct full datetime from the time
                    # For now, we'll collect what we can see
                    logger.debug(f"Found time slot button: {button_text}")
            except Exception:
                continue

        # Strategy 2: Try to click through available days to find all slots
        # Find all clickable day cells in the calendar
        try:
            day_cells = driver.find_elements(By.XPATH,
                "//td[contains(@class, 'ant-picker-cell') and not(contains(@class, 'ant-picker-cell-disabled'))]"
            )

            logger.info(f"Found {len(day_cells)} available days in calendar")

            # Click on each available day (limit to first 10 to avoid too long execution)
            for i, day_cell in enumerate(day_cells[:10]):
                try:
                    # Scroll to element and click
                    driver.execute_script("arguments[0].scrollIntoView(true);", day_cell)
                    time.sleep(0.3)
                    day_cell.click()
                    time.sleep(0.5)

                    # Get the selected date (from the cell's aria-label or text)
                    date_str = day_cell.get_attribute('title') or day_cell.text

                    # Now look for time slots for this day
                    day_slots = extract_slots_for_current_day(driver, date_str)
                    all_slots.extend(day_slots)

                    logger.debug(f"Day {i+1}: Found {len(day_slots)} slots")

                except Exception as e:
                    logger.debug(f"Error clicking day {i}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Could not iterate through calendar days: {e}")

        # Remove duplicates based on start_time
        unique_slots = []
        seen_times = set()
        for slot in all_slots:
            if slot['start_time'] not in seen_times:
                unique_slots.append(slot)
                seen_times.add(slot['start_time'])

        return unique_slots

    except Exception as e:
        logger.error(f"Error extracting time slots: {e}")
        return []


def extract_slots_for_current_day(driver, date_str: str) -> List[Dict]:
    """
    Extract time slots for the currently selected day
    """
    slots = []

    try:
        # Find all time slot buttons (they usually have time format like "14:30")
        time_buttons = driver.find_elements(By.XPATH,
            "//button[contains(@class, 'ant-btn') and contains(., ':')]"
        )

        for button in time_buttons:
            try:
                time_text = button.text.strip()

                # Parse time (e.g., "14:30")
                if ':' in time_text and len(time_text) <= 6:
                    # Try to combine with date to create full datetime
                    # This is approximate - we'll do our best to construct it

                    # For now, create a placeholder datetime
                    # In production, you'd parse the date_str properly
                    slots.append({
                        'start_time': time_text,  # We'll improve this
                        'end_time': time_text,     # Placeholder
                        'raw_time': time_text,
                        'raw_date': date_str
                    })

            except Exception:
                continue

    except Exception as e:
        logger.debug(f"Error extracting slots for day: {e}")

    return slots
