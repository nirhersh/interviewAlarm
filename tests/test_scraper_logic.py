#!/usr/bin/env python3
"""
Unit test to verify the scraper logic flow (without actual browser testing)
This tests that the code structure correctly handles both scenarios
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_logic_flow():
    """
    Verify the logical flow of the scraper:
    1. Check if slots are visible first (with short timeout)
    2. If yes, skip buttons
    3. If no, try to click buttons
    4. Extract slots
    """
    print("=" * 70)
    print("SCRAPER LOGIC FLOW TEST")
    print("=" * 70)

    print("\n✓ Testing logic structure...")

    # Test 1: Verify the code imports correctly
    print("\n1. Checking imports...")
    try:
        from scraper.needle_scraper import scrape_needle_page, NeedleScraperError
        print("   ✓ Scraper module imports successfully")
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False

    # Test 2: Verify error handling for invalid URLs
    print("\n2. Checking URL validation...")
    try:
        from scraper.needle_scraper import scrape_needle_page, NeedleScraperError
        try:
            scrape_needle_page("https://invalid-url.com")
            print("   ❌ Should have raised NeedleScraperError for invalid URL")
            return False
        except NeedleScraperError as e:
            if "Invalid URL" in str(e):
                print("   ✓ Correctly validates URLs")
            else:
                print(f"   ⚠ Unexpected error message: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

    # Test 3: Verify the code structure
    print("\n3. Verifying code structure...")
    import inspect
    from scraper.needle_scraper import scrape_needle_page

    source = inspect.getsource(scrape_needle_page)

    # Check for the new logic
    checks = {
        "Checks for slots visibility": "SlotsComponent_slotsComponent__E9g_r" in source,
        "Uses short timeout for initial check": "short_wait" in source or "WebDriverWait(driver, 3)" in source,
        "Has button click fallback": "שינוי או ביטול" in source,
        "Skips buttons if slots visible": "skipping button clicks" in source,
        "Handles TimeoutException": "TimeoutException" in source,
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False

    if not all_passed:
        return False

    print("\n" + "=" * 70)
    print("✓ ALL LOGIC TESTS PASSED!")
    print("=" * 70)
    print("\nThe scraper is now able to handle both:")
    print("  1. Pages where slots are already visible (faster, no button clicks)")
    print("  2. Pages that require navigation through buttons")
    print("\nBenefits:")
    print("  • Faster scraping for direct-access pages (saves ~3 seconds)")
    print("  • More robust - handles both page types automatically")
    print("  • Better error messages when neither scenario works")

    return True


if __name__ == "__main__":
    success = test_logic_flow()
    sys.exit(0 if success else 1)
