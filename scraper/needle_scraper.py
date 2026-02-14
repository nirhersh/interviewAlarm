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

    This function handles two types of pages:
    1. Pages where slots are already visible (direct access)
    2. Already-booked interview pages that require navigation:
       - Click "Change or cancel interview" button
       - Click "Change interview date" button
    3. Extract available time slots from the calendar interface

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

        # Try to find Chrome binary (prefer Linux Chrome)
        import shutil
        import os
        chrome_binary = None

        # Check for Linux Chrome first
        for binary_name in ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium']:
            binary_path = shutil.which(binary_name)
            if binary_path:
                chrome_binary = binary_path
                logger.info(f"Found Linux browser: {chrome_binary}")
                break

        # If no Linux Chrome, try Windows Chrome paths (for WSL environments)
        if not chrome_binary:
            windows_chrome_paths = [
                '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe',
                '/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe',
            ]
            for win_path in windows_chrome_paths:
                if os.path.exists(win_path):
                    chrome_binary = win_path
                    logger.info(f"Found Windows Chrome: {chrome_binary}")
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

        # Check if slots are already visible (no buttons needed)
        try:
            short_wait = WebDriverWait(driver, 3)
            short_wait.until(EC.presence_of_element_located((
                By.CLASS_NAME, "SlotsComponent_slotsComponent__E9g_r"
            )))
            logger.info("Slots interface already visible - skipping button clicks")
            time.sleep(1)  # Brief wait for slots to fully load
        except TimeoutException:
            # Slots not visible yet, try clicking buttons to navigate to them
            logger.info("Slots interface not visible - attempting to navigate via buttons")

            # Click "Change or cancel interview" button (שינוי או ביטול הראיון)
            try:
                change_cancel_button = wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(@class, 'ant-btn')]//span[contains(text(), 'שינוי או ביטול')]"
                    ))
                )
                change_cancel_button.click()
                logger.info("Clicked 'Change or cancel interview' button")
                time.sleep(1.5)
            except TimeoutException:
                raise NeedleScraperError(
                    "Could not find 'Change or cancel interview' button and slots are not visible. "
                    "This might not be a valid interview scheduling page."
                )

            # Click "Change interview date" button (שינוי מועד הראיון)
            try:
                change_date_button = wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(@class, 'ant-btn')]//span[contains(text(), 'שינוי מועד')]"
                    ))
                )
                change_date_button.click()
                logger.info("Clicked 'Change interview date' button")
                time.sleep(2)  # Wait for slots to load
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
    """Extract company name from the page - looks for h4 with 'תודה ובהצלחה!' followed by company name"""
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find h4 containing "תודה ובהצלחה!"
        headings = soup.find_all('h4')
        for heading in headings:
            if 'תודה ובהצלחה' in heading.get_text():
                # The company name is after the <br> tag
                br = heading.find('br')
                if br and br.next_sibling:
                    company_name = br.next_sibling.strip()
                    if company_name:
                        return company_name

        return "Unknown Company"

    except Exception as e:
        logger.debug(f"Error extracting company name: {e}")
        return "Unknown Company"


def extract_time_slots_from_calendar(driver, wait) -> List[Dict]:
    """
    Extract available time slots from the new calendar interface

    Process:
    1. Iterate through all departments in the dropdown
    2. For each department, iterate through all available days
    3. For each day, extract all available time slots

    Structure:
    - Department selector: span.ant-select-selection-item (inside ant-select)
    - Date selector with left/right arrows
    - Time slots in: ul.SlotsComponent_slotsList__DzZ_L > li
    """
    all_slots = []

    try:
        # Wait for the form to be visible
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "SlotsComponent_slotsComponent__E9g_r")))
        time.sleep(1)

        # Get all available departments
        departments = get_all_departments(driver, wait)

        if departments == [None]:
            logger.info("No department selector - processing day/time slots only")
        else:
            logger.info(f"Found {len(departments)} departments")

        # Iterate through each department (or single None if no departments)
        for dept_index, department in enumerate(departments):
            try:
                dept_label = department if department else "default"
                if department:
                    logger.info(f"Processing department {dept_index + 1}/{len(departments)}: {department}")
                else:
                    logger.info("Processing time slots")

                # Select the department (skips if None)
                select_department(driver, wait, department)
                time.sleep(1)  # Wait for slots to load

                # Extract slots for all days in this department
                dept_slots = extract_slots_for_department(driver, wait, department)
                all_slots.extend(dept_slots)

            except Exception as e:
                logger.error(f"Error processing {dept_label}: {e}")
                continue

        logger.info(f"Total slots extracted across all departments: {len(all_slots)}")
        return all_slots

    except Exception as e:
        logger.error(f"Error extracting time slots: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_all_departments(driver, wait) -> List[str]:
    """Get list of all available departments from the dropdown

    Returns:
        List of department names, or [None] if no department selector exists
    """
    departments = []

    try:
        # Check if department selector exists (with shorter timeout)
        short_wait = WebDriverWait(driver, 2)
        dept_selector = short_wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, ".ant-select"
        )))

        # Make it clickable
        dept_selector = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, ".ant-select"
        )))
        dept_selector.click()
        time.sleep(0.5)

        # Find all options in the dropdown
        options = driver.find_elements(By.CSS_SELECTOR, ".ant-select-item-option")
        for option in options:
            dept_name = option.text.strip()
            if dept_name:
                departments.append(dept_name)

        # Close dropdown by clicking selector again or pressing escape
        try:
            dept_selector.click()
        except:
            pass

        time.sleep(0.3)

    except TimeoutException:
        # No department selector found - this is normal for some pages
        logger.info("No department selector found - page only has day/time selection")
        return [None]  # Return list with None to indicate no departments
    except Exception as e:
        logger.error(f"Error getting departments: {e}")
        # Fallback: try to get current department
        try:
            current_dept = driver.find_element(By.CSS_SELECTOR, "span.ant-select-selection-item")
            dept_text = current_dept.text.strip()
            if dept_text:
                departments.append(dept_text)
        except:
            # No department selector at all
            logger.info("No department selector found - page only has day/time selection")
            return [None]

    return departments if departments else [None]


def select_department(driver, wait, department_name: Optional[str]):
    """Select a specific department from the dropdown

    Args:
        department_name: Name of department to select, or None if no department selector
    """
    # Skip if no department (page has only day/time selection)
    if department_name is None:
        logger.debug("No department to select - page has only day/time selection")
        return

    try:
        # Click on the department selector
        dept_selector = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, ".ant-select"
        )))
        dept_selector.click()
        time.sleep(0.5)

        # Find and click the option with matching text
        options = driver.find_elements(By.CSS_SELECTOR, ".ant-select-item-option")
        for option in options:
            if option.text.strip() == department_name:
                option.click()
                time.sleep(0.5)
                return

        # If not found, close dropdown
        dept_selector.click()

    except Exception as e:
        logger.error(f"Error selecting department '{department_name}': {e}")


def extract_slots_for_department(driver, wait, department: Optional[str]) -> List[Dict]:
    """Extract all time slots for a given department by iterating through days

    Args:
        department: Department name, or None if page has no department selector
    """
    dept_slots = []
    max_days = 60  # Limit to prevent infinite loop
    visited_dates = set()
    dept_label = department if department else "default"

    for day_index in range(max_days):
        try:
            # Get current date from the date selector
            date_selector = driver.find_element(By.CLASS_NAME, "SlotsComponent_dateSelector__aXL6m")
            date_text = date_selector.text.strip()

            # Extract just the date part
            import re
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_text)
            current_date = date_match.group(1) if date_match else date_text

            # Skip if we've already visited this date (means we've looped)
            if current_date in visited_dates:
                logger.debug(f"Already visited date {current_date} for {dept_label}, stopping")
                break

            visited_dates.add(current_date)

            # Extract time slots for current day
            day_slots = extract_slots_for_current_day(driver, current_date, department)
            dept_slots.extend(day_slots)

            # Click the "next day" button (left arrow in RTL)
            try:
                next_button = driver.find_element(By.CSS_SELECTOR,
                    "button.SlotsComponent_left__KXo2o:not([disabled])")
                next_button.click()
                time.sleep(0.5)  # Wait for new slots to load
            except Exception:
                # No more days available or button is disabled
                logger.debug(f"No more days available for {dept_label}")
                break

        except Exception as e:
            logger.debug(f"Error processing day {day_index} for {dept_label}: {e}")
            break

    logger.info(f"Found {len(dept_slots)} slots for {dept_label}")
    return dept_slots


def extract_slots_for_current_day(driver, date_str: str, department: Optional[str]) -> List[Dict]:
    """
    Extract time slots for the currently selected day from ul.SlotsComponent_slotsList__DzZ_L > li

    Args:
        date_str: Date string in DD.MM.YYYY format
        department: Department name, or None if page has no department selector

    Returns:
        List of slot dictionaries with department (may be None), date, and time information
    """
    slots = []
    dept_label = department if department else "default"

    try:
        # Find the slots list
        slots_list = driver.find_element(By.CSS_SELECTOR, "ul.SlotsComponent_slotsList__DzZ_L")
        time_items = slots_list.find_elements(By.TAG_NAME, "li")

        for item in time_items:
            try:
                time_text = item.text.strip()

                # Validate it's a time (format: HH:MM)
                if ':' in time_text and len(time_text) <= 6:
                    # Convert DD.MM.YYYY HH:MM to ISO 8601 format for database compatibility
                    # date_str format: DD.MM.YYYY
                    # time_text format: HH:MM
                    day, month, year = date_str.split('.')
                    iso_datetime = f"{year}-{month}-{day}T{time_text}:00"

                    slots.append({
                        'department': department,  # May be None if no department selector
                        'date': date_str,
                        'time': time_text,
                        'datetime': f"{date_str} {time_text}",
                        'start_time': iso_datetime,  # ISO 8601 format for DB storage
                        'end_time': iso_datetime     # Placeholder - duration unknown
                    })

            except Exception as e:
                logger.debug(f"Error extracting time slot: {e}")
                continue

        if len(slots) > 0:
            logger.debug(f"Found {len(slots)} slots for {dept_label} on {date_str}")

    except Exception as e:
        logger.debug(f"No slots found for {dept_label} on {date_str}: {e}")

    return slots
