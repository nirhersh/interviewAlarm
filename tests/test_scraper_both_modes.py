#!/usr/bin/env python3
"""
Test script to verify the scraper handles both page types:
1. Pages with slots already visible
2. Pages that require button clicks to navigate to slots
"""

import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scraper.needle_scraper import scrape_needle_page, NeedleScraperError

# Set up logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_scraper_with_url(url: str, test_name: str):
    """Test the scraper with a given URL"""
    print(f"\n{'=' * 70}")
    print(f"TEST: {test_name}")
    print(f"URL: {url}")
    print("=" * 70)

    try:
        result = scrape_needle_page(url)

        print(f"\n✓ SUCCESS!")
        print(f"Company Name: {result['company_name']}")
        print(f"Total Slots Found: {len(result['slots'])}")

        if result['slots']:
            print("\nFirst few slots:")
            for i, slot in enumerate(result['slots'][:5]):
                print(f"  {i+1}. {slot.get('date', 'N/A')} {slot.get('time', 'N/A')}")
            if len(result['slots']) > 5:
                print(f"  ... and {len(result['slots']) - 5} more")
        else:
            print("\n⚠ Warning: No slots found (this might be expected if there are no available slots)")

        return True

    except NeedleScraperError as e:
        print(f"\n❌ SCRAPER ERROR: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SCRAPER DUAL-MODE TEST")
    print("Testing ability to handle both page types")
    print("=" * 70)

    # You can test with your actual URLs here
    # For now, we'll just demonstrate that the code structure is correct

    print("\n📝 NOTE:")
    print("This test requires actual needle.co.il URLs to run.")
    print("The scraper has been updated to handle two cases:")
    print("  1. Pages where slots are already visible (no button clicks needed)")
    print("  2. Pages that require clicking 'Change or cancel' -> 'Change date'")
    print("\nThe scraper will:")
    print("  - First check if slots interface is visible")
    print("  - If yes: skip button clicks and extract slots directly")
    print("  - If no: click the buttons to navigate to slots")
    print("\nThis makes the scraper more robust and faster for direct-access pages.")

    # Uncomment and add your test URLs here:
    # test_scraper_with_url("https://needle.co.il/candidate-slots/YOUR-UUID", "Direct slots page")
    # test_scraper_with_url("https://needle.co.il/candidate-slots/ANOTHER-UUID", "Booked interview page")

    print("\n" + "=" * 70)
