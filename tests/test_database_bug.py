#!/usr/bin/env python3
"""
Test to demonstrate the bug where modified time slots are not detected
"""

import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import Database


def test_modified_slot_detection():
    """
    Test that demonstrates the bug: modified slots are NOT detected as new
    """
    print("=" * 70)
    print("TEST: Modified Slot Detection Bug")
    print("=" * 70)

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)

        # Step 1: Add a tracked URL
        print("\n1. Adding tracked URL...")
        tracked_url_id = db.add_tracked_url(
            user_id=12345,
            url="https://example.com/test",
            company_name="Test Company"
        )
        print(f"   Created tracked_url_id: {tracked_url_id}")

        # Step 2: Save initial slots
        print("\n2. Saving initial time slots...")
        initial_slots = [
            {
                'start_time': '2025-01-15 10:00:00',
                'end_time': '2025-01-15 11:00:00'
            },
            {
                'start_time': '2025-01-15 14:00:00',
                'end_time': '2025-01-15 15:00:00'
            }
        ]
        db.save_time_slots(tracked_url_id, initial_slots, is_notified=True)
        print(f"   Saved {len(initial_slots)} slots")
        for slot in initial_slots:
            print(f"   - {slot['start_time']} to {slot['end_time']}")

        # Step 3: Simulate a change - same start_time but different end_time
        print("\n3. Simulating modified slot (end_time changed)...")
        modified_slots = [
            {
                'start_time': '2025-01-15 10:00:00',
                'end_time': '2025-01-15 11:30:00'  # CHANGED: was 11:00, now 11:30
            },
            {
                'start_time': '2025-01-15 14:00:00',
                'end_time': '2025-01-15 15:00:00'  # Same as before
            }
        ]
        print("   Modified slot:")
        print(f"   - {modified_slots[0]['start_time']} to {modified_slots[0]['end_time']} (was 11:00, now 11:30)")

        # Step 4: Check for new slots (this is where the bug is!)
        print("\n4. Checking for new slots using get_new_slots()...")
        new_slots = db.get_new_slots(tracked_url_id, modified_slots)

        print(f"\n   Result: Found {len(new_slots)} new slots")

        # Step 5: Verify the bug
        print("\n5. Bug Analysis:")
        if len(new_slots) == 0:
            print("   ❌ BUG CONFIRMED!")
            print("   The modified slot was NOT detected as new")
            print("   Reason: get_new_slots() only checks start_time, not end_time")
            print("   User will NOT receive a notification about the change")
            return False
        else:
            print("   ✓ Bug appears to be fixed!")
            print(f"   Detected {len(new_slots)} modified slot(s)")
            return True

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_new_slot_detection():
    """
    Test that new slots ARE detected (this should work)
    """
    print("\n" + "=" * 70)
    print("TEST: New Slot Detection (Should Work)")
    print("=" * 70)

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)

        # Step 1: Add a tracked URL
        print("\n1. Adding tracked URL...")
        tracked_url_id = db.add_tracked_url(
            user_id=12345,
            url="https://example.com/test",
            company_name="Test Company"
        )

        # Step 2: Save initial slots
        print("\n2. Saving initial time slots...")
        initial_slots = [
            {
                'start_time': '2025-01-15 10:00:00',
                'end_time': '2025-01-15 11:00:00'
            }
        ]
        db.save_time_slots(tracked_url_id, initial_slots, is_notified=True)
        print(f"   Saved {len(initial_slots)} slots")

        # Step 3: Add a completely new slot
        print("\n3. Adding a completely new slot...")
        current_slots = [
            {
                'start_time': '2025-01-15 10:00:00',
                'end_time': '2025-01-15 11:00:00'
            },
            {
                'start_time': '2025-01-15 16:00:00',  # NEW start_time
                'end_time': '2025-01-15 17:00:00'
            }
        ]

        # Step 4: Check for new slots
        print("\n4. Checking for new slots...")
        new_slots = db.get_new_slots(tracked_url_id, current_slots)

        print(f"\n   Result: Found {len(new_slots)} new slots")

        # Step 5: Verify
        if len(new_slots) == 1:
            print("   ✓ Correctly detected the new slot")
            print(f"   New slot: {new_slots[0]['start_time']} to {new_slots[0]['end_time']}")
            return True
        else:
            print(f"   ❌ Expected 1 new slot, found {len(new_slots)}")
            return False

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    print("\nRunning Database Bug Tests")
    print("=" * 70)

    # Test 1: New slot detection (should work)
    test1_passed = test_new_slot_detection()

    # Test 2: Modified slot detection (will fail - this is the bug)
    test2_passed = test_modified_slot_detection()

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"New slot detection: {'✓ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Modified slot detection: {'✓ PASS' if test2_passed else '❌ FAIL (BUG)'}")
    print("=" * 70)

    if not test2_passed:
        print("\nCONCLUSION:")
        print("The bug is confirmed. Modified time slots are not detected.")
        print("Users will not receive notifications when slot times change.")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)
