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

        # Group slots by department for better readability
        from collections import defaultdict
        slots_by_dept = defaultdict(list)
        for slot in result['slots']:
            dept = slot.get('department', 'Unknown')
            slots_by_dept[dept].append(slot)

        # Display slots grouped by department
        for department, dept_slots in slots_by_dept.items():
            print(f"\n📌 {department} ({len(dept_slots)} slots)")
            print("-" * 60)

            # Group by date
            slots_by_date = defaultdict(list)
            for slot in dept_slots:
                date = slot.get('date', 'Unknown')
                slots_by_date[date].append(slot)

            for date in sorted(slots_by_date.keys()):
                times = [s.get('time', '') for s in slots_by_date[date]]
                times_str = ', '.join(sorted(times))
                print(f"  {date}: {times_str}")

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
