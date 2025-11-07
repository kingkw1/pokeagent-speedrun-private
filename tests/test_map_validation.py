"""
Test map stitcher validation logic.

This test demonstrates that the validation function correctly detects when
player position doesn't match map stitcher bounds (indicating stale data from
a previous run or different save state).
"""

def test_validation_with_stale_data():
    """Simulate the scenario from 03_birch split state"""
    
    # Mock map area with stale bounds (from a different run)
    class MockMapArea:
        def __init__(self, location_name, bounds):
            self.location_name = location_name
            self.explored_bounds = bounds
    
    # Mock map stitcher with stale data
    class MockMapStitcher:
        def __init__(self):
            self.map_areas = {
                9: MockMapArea(
                    location_name="LITTLEROOT TOWN",
                    bounds={'min_x': 43, 'max_x': 57, 'min_y': 43, 'max_y': 57}
                    # ^^^ These bounds are from a previous run - completely wrong!
                )
            }
    
    # Current player position (from 03_birch state)
    player_pos = (7, 17)  # Player is outside these bounds!
    location = "LITTLEROOT TOWN"
    
    # Import validation function
    import sys
    sys.path.insert(0, '/home/kevin/Documents/pokeagent-speedrun')
    from agent.action import _validate_map_stitcher_bounds
    
    # Test validation
    map_stitcher = MockMapStitcher()
    
    print("\n" + "="*80)
    print("🧪 TEST: Map Stitcher Validation with Stale Data")
    print("="*80)
    print(f"\n📍 Current State:")
    print(f"   Location: {location}")
    print(f"   Player Position: {player_pos}")
    print(f"\n🗺️  Map Stitcher Bounds (STALE from previous run):")
    for area in map_stitcher.map_areas.values():
        if area.location_name.upper() == location.upper():
            bounds = area.explored_bounds
            print(f"   X: {bounds['min_x']} to {bounds['max_x']}")
            print(f"   Y: {bounds['min_y']} to {bounds['max_y']}")
    
    print(f"\n🔍 Running Validation...")
    is_valid = _validate_map_stitcher_bounds(map_stitcher, player_pos, location)
    
    print(f"\n📊 RESULT:")
    if not is_valid:
        print("   ✅ CORRECTLY DETECTED stale data!")
        print("   ✅ Pathfinding will be skipped for this step")
        print("   ✅ VLM will navigate instead")
        print("   ✅ Fresh map data will be accumulated as agent explores")
    else:
        print("   ❌ FAILED - Should have detected mismatch!")
        return False
    
    print("\n" + "="*80)
    print("✅ TEST PASSED - Validation working correctly!")
    print("="*80 + "\n")
    return True


def test_validation_with_fresh_data():
    """Test with matching bounds (fresh, valid data)"""
    
    class MockMapArea:
        def __init__(self, location_name, bounds):
            self.location_name = location_name
            self.explored_bounds = bounds
    
    class MockMapStitcher:
        def __init__(self):
            self.map_areas = {
                9: MockMapArea(
                    location_name="LITTLEROOT TOWN",
                    bounds={'min_x': 0, 'max_x': 20, 'min_y': 0, 'max_y': 30}
                    # ^^^ Player at (7, 17) IS within these bounds
                )
            }
    
    player_pos = (7, 17)
    location = "LITTLEROOT TOWN"
    
    import sys
    sys.path.insert(0, '/home/kevin/Documents/pokeagent-speedrun')
    from agent.action import _validate_map_stitcher_bounds
    
    map_stitcher = MockMapStitcher()
    
    print("\n" + "="*80)
    print("🧪 TEST: Map Stitcher Validation with Fresh Data")
    print("="*80)
    print(f"\n📍 Current State:")
    print(f"   Location: {location}")
    print(f"   Player Position: {player_pos}")
    print(f"\n🗺️  Map Stitcher Bounds (FRESH, matching current state):")
    for area in map_stitcher.map_areas.values():
        if area.location_name.upper() == location.upper():
            bounds = area.explored_bounds
            print(f"   X: {bounds['min_x']} to {bounds['max_x']}")
            print(f"   Y: {bounds['min_y']} to {bounds['max_y']}")
    
    print(f"\n🔍 Running Validation...")
    is_valid = _validate_map_stitcher_bounds(map_stitcher, player_pos, location)
    
    print(f"\n📊 RESULT:")
    if is_valid:
        print("   ✅ CORRECTLY VALIDATED fresh data!")
        print("   ✅ Pathfinding will proceed normally")
    else:
        print("   ❌ FAILED - Should have accepted valid bounds!")
        return False
    
    print("\n" + "="*80)
    print("✅ TEST PASSED - Validation working correctly!")
    print("="*80 + "\n")
    return True


if __name__ == "__main__":
    print("\n" + "🔬 "*20)
    print("MAP STITCHER VALIDATION TEST SUITE")
    print("🔬 "*20)
    
    test1 = test_validation_with_stale_data()
    test2 = test_validation_with_fresh_data()
    
    if test1 and test2:
        print("\n" + "🎉 "*20)
        print("ALL TESTS PASSED!")
        print("🎉 "*20 + "\n")
        print("✅ Competition split states with stale map data will be handled gracefully")
        print("✅ Pathfinding will skip when bounds mismatch detected")
        print("✅ VLM navigation will take over until fresh data accumulated\n")
    else:
        print("\n❌ SOME TESTS FAILED\n")
        exit(1)
