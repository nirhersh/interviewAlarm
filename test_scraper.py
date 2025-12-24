#!/usr/bin/env python3
"""
Test script for the needle scraper
"""

import logging
from scraper.needle_scraper import scrape_needle_page, NeedleScraperError

# Set up logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_scraper():
    url = "https://needle.co.il/candidate-slots/dfb99ed2-0469-4bf1-b98a-6cb16f9728ea"

    print(f"Testing scraper with URL: {url}")
    print("-" * 60)

    try:
        result = scrape_needle_page(url)

        print(f"\nCompany Name: {result['company_name']}")
        print(f"\nTotal Slots Found: {len(result['slots'])}")
        print("\nTime Slots:")
        print("-" * 60)

        for i, slot in enumerate(result['slots'][:20], 1):  # Show first 20
            print(f"{i}. Start: {slot.get('start_time')} | End: {slot.get('end_time')}")
            if 'raw_date' in slot and 'raw_time' in slot:
                print(f"   Raw: {slot['raw_date']} at {slot['raw_time']}")

        if len(result['slots']) > 20:
            print(f"\n... and {len(result['slots']) - 20} more slots")

        print("\n" + "=" * 60)
        print("SUCCESS: Scraper completed successfully!")

    except NeedleScraperError as e:
        print(f"\nERROR: {e}")
        return False
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    test_scraper()
