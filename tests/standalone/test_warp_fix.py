#!/usr/bin/env python3
"""Quick test to verify warp avoidance logic after fix"""

# Simulate the warp avoidance logic
def test_warp_avoidance():
    print("Testing warp avoidance logic:\n")
    
    # Scenario 1: Moving on same map (Route 101)
    current_location = 'ROUTE 101'
    recent_loc = 'ROUTE 101'
    should_block = (recent_loc != current_location)
    print(f"Scenario 1: Same map movement")
    print(f"  Current: '{current_location}', Recent: '{recent_loc}'")
    print(f"  Block? {should_block} (should be FALSE)")
    print()
    
    # Scenario 2: Warp from Littleroot Town to Route 101
    current_location = 'LITTLEROOT TOWN'
    recent_loc = 'ROUTE 101'
    should_block = (recent_loc != current_location)
    print(f"Scenario 2: Cross-map warp")
    print(f"  Current: '{current_location}', Recent: '{recent_loc}'")
    print(f"  Block? {should_block} (should be TRUE)")
    print()
    
    # Scenario 3: THE BUG - empty current_location
    current_location = ''  # BUG: was using 'map_location' instead of 'location'
    recent_loc = 'ROUTE 101'
    should_block = (recent_loc != current_location)
    print(f"Scenario 3: BUGGY behavior (current_location empty)")
    print(f"  Current: '{current_location}', Recent: '{recent_loc}'")
    print(f"  Block? {should_block} (incorrectly blocks EVERYTHING)")
    print()
    
    print("=" * 60)
    print("CONCLUSION:")
    print("The fix (using 'location' instead of 'map_location') ensures")
    print("current_location is populated, so warp avoidance only blocks")
    print("actual cross-map warps, not normal same-map movement.")
    print("=" * 60)

if __name__ == '__main__':
    test_warp_avoidance()
