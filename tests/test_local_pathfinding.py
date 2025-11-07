#!/usr/bin/env python3
"""
Test local A* pathfinding with 15x15 visible tile grid.
Simulates player outside Birch's Lab with door UP and building blocking north.
"""

from typing import Dict, Any, Tuple
import sys
sys.path.insert(0, '/home/kevin/Documents/pokeagent-speedrun')
from pokemon_env.enums import MetatileBehavior

# Mock state data - player at center (7,7) of 15x15 grid
def get_mock_state() -> Dict[str, Any]:
    """
    Create mock state with:
    - Player at center (7, 7)
    - Door at (7, 6) = UP direction
    - Building blocking LEFT and north area
    - Open paths: RIGHT to navigate around building
    
    Tiles are tuples: (tile_id, behavior, collision, elevation)
    """
    
    # Helper to create tiles
    def walkable() -> Tuple:
        return (1, MetatileBehavior.NORMAL, 0, 0)  # Normal walkable
    
    def blocked() -> Tuple:
        return (1023, MetatileBehavior.NORMAL, 1, 0)  # Wall/blocked
    
    def door() -> Tuple:
        return (100, MetatileBehavior.ANIMATED_DOOR, 1, 0)  # Door tile
    
    def unknown() -> Tuple:
        return (1023, MetatileBehavior.NORMAL, 1, 0)  # Out of bounds (tile_id 1023 = blocked)
    
    # 15x15 grid
    grid = [
        # Row 0 (north edge) - mostly blocked by building, some walkable on right
        [unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 1
        [unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 2
        [unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 3
        [unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 4 - building starts (7 tiles wide, columns 4-10)
        [unknown(), walkable(), walkable(), walkable(), blocked(), blocked(), blocked(), blocked(), blocked(), blocked(), blocked(), walkable(), walkable(), walkable(), unknown()],
        # Row 5 - building continues
        [unknown(), walkable(), walkable(), walkable(), blocked(), blocked(), blocked(), blocked(), blocked(), blocked(), blocked(), walkable(), walkable(), walkable(), unknown()],
        # Row 6 - door at center (7, 6)
        [unknown(), walkable(), walkable(), walkable(), blocked(), blocked(), blocked(), door(), blocked(), blocked(), blocked(), walkable(), walkable(), walkable(), unknown()],
        # Row 7 - PLAYER at (7, 7), blocked LEFT by building
        [unknown(), walkable(), walkable(), walkable(), blocked(), blocked(), blocked(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 8
        [unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 9
        [unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 10
        [unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 11
        [unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 12
        [unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 13
        [unknown(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), walkable(), unknown()],
        # Row 14 (south edge)
        [unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown(), unknown()],
    ]
    
    return {
        'map': {
            'tiles': grid
        }
    }

def test_local_pathfinding():
    """Test that local A* finds path around building to north edge."""
    from agent.action import _local_pathfind_from_tiles
    
    state = get_mock_state()
    goal = 'north'
    
    print("=" * 60)
    print("🧪 Testing Local A* Pathfinding")
    print("=" * 60)
    print(f"🎯 Goal: Navigate NORTH (toward Route 101/Oldale Town)")
    print(f"   Player at center (7, 7)")
    print(f"   Building blocks: rows 4-7, columns 4-10")
    print(f"   Door at (7, 6) = UP")
    print(f"   Correct path: RIGHT (around building) then UP to north edge")
    print()
    
    # Call local pathfinding
    chosen_direction = _local_pathfind_from_tiles(state, goal)
    
    print()
    print("=" * 60)
    
    if chosen_direction == 'RIGHT':
        print("✅ SUCCESS! Chose RIGHT to navigate around building")
        print("   This is the correct first step toward the north edge")
        print("✅ TEST PASSED - Local A* working correctly!")
        return True
    elif chosen_direction == 'UP':
        print("❌ FAILURE! Chose UP (would enter door)")
        print("   Local A* should navigate around building, not into it")
        print("❌ TEST FAILED")
        return False
    elif chosen_direction in ['DOWN', 'LEFT']:
        print(f"❌ FAILURE! Chose {chosen_direction} (wrong direction)")
        print("   Should choose RIGHT to navigate around building toward north")
        print("❌ TEST FAILED")
        return False
    else:
        print(f"❌ ERROR! Unexpected result: {chosen_direction}")
        print("❌ TEST FAILED")
        return False

if __name__ == '__main__':
    success = test_local_pathfinding()
    sys.exit(0 if success else 1)

