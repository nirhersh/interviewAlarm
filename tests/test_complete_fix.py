#!/usr/bin/env python3
"""
End-to-end test to verify the complete fix for modified slot detection
"""

import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import Database


def test_complete_workflow():
    """
    Test the complete workflow: detect modified slot, save it, verify no duplicate detection
    """
    print("=" * 70)
    print("END-TO-END TEST: Complete Modified Slot Workflow")
    print("=" * 70)

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)

        # Setup
        print("\n1. Setting up tracked URL...")
        tracked_url_id = db.add_tracked_url(
            user_id=12345,
            url="https://example.com/test",
            company_name="Test Company"
        )
        print(f"   ✓ Created tracked_url_id: {tracked_url_id}")

        # Initial state
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
        print(f"   ✓ Saved {len(initial_slots)} initial slots")
        for slot in initial_slots:
            print(f"     - {slot['start_time']} to {slot['end_time']}")

        # Simulate first check - modified slot
        print("\n3. First check: Simulating modified slot (end_time changed)...")
        modified_slots = [
            {
                'start_time': '2025-01-15 10:00:00',
                'end_time': '2025-01-15 11:30:00'  # Changed from 11:00 to 11:30
            },
            {
                'start_time': '2025-01-15 14:00:00',
                'end_time': '2025-01-15 15:00:00'  # Unchanged
            }
        ]

        new_slots = db.get_new_slots(tracked_url_id, modified_slots)
        print(f"   ✓ Detected {len(new_slots)} modified slot(s)")

        if len(new_slots) != 1:
            print(f"   ❌ FAIL: Expected 1 modified slot, got {len(new_slots)}")
            return False

        print(f"     Modified: {new_slots[0]['start_time']} to {new_slots[0]['end_time']}")

        # Save the modified slot (simulating what scheduler does)
        print("\n4. Saving modified slot to database...")
        db.save_time_slots(tracked_url_id, new_slots, is_notified=False)
        print("   ✓ Saved modified slot")

        # Mark as notified
        print("\n5. Marking slot as notified...")
        start_times = [slot['start_time'] for slot in new_slots]
        db.mark_slots_notified(tracked_url_id, start_times)
        print("   ✓ Marked as notified")

        # Verify the slot was updated in DB
        print("\n6. Verifying database was updated correctly...")
        db_slots = db.get_time_slots(tracked_url_id)
        print(f"   Database now contains {len(db_slots)} slots:")
        for slot in db_slots:
            print(f"     - {slot['start_time']} to {slot['end_time']}")

        # Find the updated slot
        updated_slot = next(
            (s for s in db_slots if s['start_time'] == '2025-01-15 10:00:00'),
            None
        )

        if not updated_slot:
            print("   ❌ FAIL: Slot not found in database")
            return False

        if updated_slot['end_time'] != '2025-01-15 11:30:00':
            print(f"   ❌ FAIL: Slot not updated correctly. end_time is {updated_slot['end_time']}, expected 11:30:00")
            return False

        print("   ✓ Slot was updated correctly in database")

        # Second check - verify no duplicate detection
        print("\n7. Second check: Verifying no duplicate detection...")
        new_slots_again = db.get_new_slots(tracked_url_id, modified_slots)
        print(f"   Found {len(new_slots_again)} new slots")

        if len(new_slots_again) != 0:
            print(f"   ❌ FAIL: Should not detect any new slots, but found {len(new_slots_again)}")
            print("   This would cause duplicate notifications!")
            return False

        print("   ✓ No duplicate detection - user won't get spammed")

        # Test adding a completely new slot
        print("\n8. Third check: Adding a completely new slot...")
        new_slot_added = [
            {
                'start_time': '2025-01-15 10:00:00',
                'end_time': '2025-01-15 11:30:00'
            },
            {
                'start_time': '2025-01-15 14:00:00',
                'end_time': '2025-01-15 15:00:00'
            },
            {
                'start_time': '2025-01-15 16:00:00',  # NEW
                'end_time': '2025-01-15 17:00:00'
            }
        ]

        new_slots_third = db.get_new_slots(tracked_url_id, new_slot_added)
        print(f"   ✓ Detected {len(new_slots_third)} new slot(s)")

        if len(new_slots_third) != 1:
            print(f"   ❌ FAIL: Expected 1 new slot, got {len(new_slots_third)}")
            return False

        if new_slots_third[0]['start_time'] != '2025-01-15 16:00:00':
            print(f"   ❌ FAIL: Wrong slot detected")
            return False

        print(f"     New slot: {new_slots_third[0]['start_time']} to {new_slots_third[0]['end_time']}")
        print("   ✓ New slot detection still works correctly")

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nSummary:")
        print("  ✓ Modified slots are detected")
        print("  ✓ Modified slots are saved/updated in database")
        print("  ✓ No duplicate notifications")
        print("  ✓ New slots still detected correctly")
        return True

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    success = test_complete_workflow()
    sys.exit(0 if success else 1)
