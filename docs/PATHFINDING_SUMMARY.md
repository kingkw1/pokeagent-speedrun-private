# Pathfinding System - Complete Implementation Summary

**Date:** November 7, 2025  
**Status:** ✅ Implemented and tested  
**Problem Solved:** Bot re-entering Birch's Lab instead of navigating north to Oldale Town

---

## Table of Contents
1. [Problem Statement](#problem-statement)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Solution Architecture](#solution-architecture)
4. [Implementation Details](#implementation-details)
5. [Files Modified](#files-modified)
6. [Testing](#testing)
7. [Future Enhancements](#future-enhancements)

---

## Problem Statement

### Observed Behavior
When loading from `03_birch` split state (player outside Birch's Lab at position 7,17), the agent would:
1. Choose UP (toward door at 7,16)
2. Enter Birch's Lab warp
3. Get stuck in loop re-entering the lab

### Expected Behavior
Agent should:
1. Navigate around Birch's Lab building
2. Move toward northern edge of Littleroot Town
3. Reach Route 101
4. Continue north to Oldale Town

### Why It Mattered
This bug prevented the agent from progressing past split 03_birch, blocking all subsequent gameplay.

---

## Root Cause Analysis

### Layer 1: Map Stitcher Stale Data
**Discovery:** The map stitcher singleton had bounds from a previous run:
```
Map Stitcher Bounds: X:43-57, Y:43-57
Player Position: (7, 17)
```

Player was completely outside the stored bounds, indicating the map data was from an unrelated run.

**Impact:** A* pathfinding was disabled due to invalid data, falling back to VLM-only navigation.

### Layer 2: VLM Limitations
**Problem:** VLM only sees 15x15 tile grid (7-tile radius)
```
Movement Preview:
  UP   : (7, 16) [D] WALKABLE - Door/Entrance
  DOWN : (7, 18) [.] WALKABLE
  LEFT : (6, 17) [#] BLOCKED
  RIGHT: (8, 17) [.] WALKABLE
```

The VLM sees "Door" as WALKABLE and chooses it as option 1 (UP = north = correct direction).

**Why UP was wrong:** While north IS correct, the immediate UP tile is a warp back into the lab. The agent needed to navigate AROUND the building (RIGHT, then UP).

### Layer 3: Limited Visibility
The VLM cannot see:
- Route 101 is north (beyond 15x15 view)
- The building structure requiring navigation around it
- That "north" requires initial movement RIGHT or DOWN to path around obstacles

---

## Solution Architecture

### Hybrid Approach: Validation + Local BFS Pathfinding

```
┌─────────────────────────────────────────────────────┐
│              PATHFINDING DECISION FLOW              │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────┐
         │   Parse Navigation Goal   │
         │ (from planning module)    │
         └───────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────┐
         │ Validate Map Stitcher     │
         │ (check bounds vs pos)     │
         └───────────────────────────┘
                         │
           ┌─────────────┴─────────────┐
           │                           │
           ▼                           ▼
    [VALID BOUNDS]              [STALE BOUNDS]
           │                           │
           ▼                           ▼
    ┌──────────────┐          ┌──────────────┐
    │  Local BFS   │          │  Local BFS   │
    │ (could use   │          │ (15x15 grid) │
    │  full A* too)│          │              │
    └──────────────┘          └──────────────┘
           │                           │
           └─────────────┬─────────────┘
                         ▼
                 ┌──────────────┐
                 │   Direction  │
                 │ (UP/DOWN/etc)│
                 └──────────────┘
                         │
                         ▼
              [Return to action.py]
                         │
              (VLM fallback if no path)
```

---

## Implementation Details

### Component 1: Map Stitcher Validation

**Function:** `_validate_map_stitcher_bounds()`  
**Location:** `agent/action.py` (lines ~250-290)

**Purpose:** Detect stale map data from previous runs

**Logic:**
```python
def _validate_map_stitcher_bounds(map_stitcher, player_pos, location):
    # Find map area for current location
    matching_area = map_stitcher.get_area_for_location(location)
    
    bounds = matching_area.explored_bounds
    player_x, player_y = player_pos
    
    # Check if player position is within stored bounds
    if (bounds['min_x'] <= player_x <= bounds['max_x'] and
        bounds['min_y'] <= player_y <= bounds['max_y']):
        return True  # Valid
    else:
        print("⚠️ Map stitcher bounds mismatch - stale data detected")
        return False  # Stale
```

**Result:** Correctly identifies when map data is from a different run/state

---

### Component 2: Local BFS Pathfinding

**Function:** `_local_pathfind_from_tiles()`  
**Location:** `agent/action.py` (lines ~123-248)

**Purpose:** Navigate using ONLY the 15x15 visible tile grid

**Algorithm:** Breadth-First Search (BFS)

**How it works:**
```python
def _local_pathfind_from_tiles(state_data, goal_direction):
    # Get 15x15 grid from state
    tiles = state_data['map']['tiles']  # Player at center (7,7)
    
    # Determine target edge based on goal
    if goal_direction == 'north':
        target_positions = [(x, 0) for x in range(15) if walkable(x, 0)]
    
    # BFS from player to any target
    queue = deque([(player_pos, [])])
    while queue:
        pos, path = queue.popleft()
        if pos in target_positions:
            return path[0]  # First step
        
        for neighbor in walkable_neighbors(pos):
            queue.append((neighbor, path + [direction_to(neighbor)]))
    
    return None  # No path found
```

**Key Features:**
- **Walkable tiles:** `.` (grass), `_` (path) only
- **Blocked tiles:** `#` (walls), `D` (doors), `S` (stairs), `?` (unknown)
- **Returns:** First direction in shortest path to target edge

**Example - 03_birch scenario:**
```
Grid (player at 7,7):
Row 0: ? ? ? ? ? ? ? ? ? . . . . . ?  ← Target (north edge)
Row 4: ? . . . # # # # # # # . . . ?
Row 5: ? . . . # # # # # # # . . . ?
Row 6: ? . . . # # # D # # # . . . ?  ← Door at (7,6)
Row 7: ? . . . # # # P . . . . . . ?  ← Player at (7,7)
Row 8: ? . . . . . . . . . . . . . ?

BFS Result:
- Target: Any walkable tile at row 0 (north edge)
- Path: RIGHT → RIGHT → RIGHT → RIGHT → UP → UP → UP...
- First step: RIGHT

Explanation: Must navigate around building (columns 4-10) to reach north edge
```

---

### Component 3: Goal Parser

**File:** `utils/goal_parser.py` (NEW)  
**Purpose:** Extract navigation goals from strategic plans

**Example:**
```python
# Input plan:
"Navigate to Oldale Town to the north"

# Parsed output:
{
    "type": "location",
    "target": "OLDALE_TOWN",
    "direction_hint": "north",
    "confidence": 0.8
}
```

**Supported Goal Types:**
- `location`: Navigate to named location
- `coordinates`: Move to specific (x, y)
- `npc`: Find and interact with NPC
- `edge`: Move to map edge (NORTH_EDGE, etc.)
- `explore`: Find unexplored areas

---

### Component 4: Location Database

**File:** `utils/location_db.py` (NEW)  
**Purpose:** Define world map relationships

**Example:**
```python
LOCATION_GRAPH = {
    'LITTLEROOT_TOWN': {
        'ROUTE_101': 'north',  # Route 101 is NORTH of Littleroot
        'PROFESSOR_BIRCHS_LAB': 'internal',
    },
    'ROUTE_101': {
        'LITTLEROOT_TOWN': 'south',
        'OLDALE_TOWN': 'north',
    },
    ...
}

# Usage:
direction = get_direction_to_location('LITTLEROOT_TOWN', 'ROUTE_101')
# Returns: 'north'
```

**Benefits:**
- No hardcoded navigation logic
- Easy to extend for new areas
- Supports pathfinding planning

---

### Component 5: Full A* Pathfinding (Implemented but not used yet)

**File:** `utils/pathfinding.py` (NEW)  
**Purpose:** Long-range pathfinding using map stitcher data

**Status:** Complete implementation available for future use

**When to use:**
- Map stitcher has valid bounds
- Need to navigate beyond 15x15 view
- Multi-room/area navigation

**Currently:** Agent uses local BFS for everything (simpler, works well)

---

## Files Modified

### Core Agent Files

#### `agent/action.py` (primary changes)
**New Functions:**
- `_local_pathfind_from_tiles()` - BFS pathfinding on 15x15 grid
- `_validate_map_stitcher_bounds()` - Detect stale map data

**Removed Functions:**
- `_get_fresh_map_stitcher()` - Unused approach
- `_convert_to_pathfinding_goal()` - Moved logic to goal_parser

**Modified Sections:**
- Lines ~1260-1310: Pathfinding integration
  - Extract goal from plan
  - Validate map stitcher
  - Run local BFS or fall back to VLM

**Integration Point:**
```python
# In action_step() - before VLM navigation
navigation_goal = goal_parser.extract_goal_from_plan(current_plan, location)

if navigation_goal:
    if _validate_map_stitcher_bounds(...):
        # Could use full A* here
        direction = _local_pathfind_from_tiles(state_data, direction_hint)
    else:
        # Stale data - use local BFS
        direction = _local_pathfind_from_tiles(state_data, direction_hint)
    
    if direction:
        return [direction]  # Bypass VLM

# Fall through to VLM if pathfinding failed
```

#### `agent/opener_bot.py` (documentation)
**Changes:**
- Updated module docstring with COMPLETED state behavior
- Documented that bot permanently hands off after starter chosen
- Clarified state machine architecture

### New Utility Files

#### `utils/goal_parser.py` (NEW - 255 lines)
**Purpose:** Extract navigation goals from plans  
**Key Classes:**
- `GoalParser`: Parse plan text to structured goals
- `get_goal_parser()`: Singleton accessor

**Methods:**
- `extract_goal_from_plan()`: Main entry point
- `_extract_coordinate_goal()`: Parse (x, y) targets
- `_extract_npc_goal()`: Parse NPC interactions
- `_extract_location_goal()`: Parse location names
- `_extract_direction_goal()`: Parse directional hints

#### `utils/location_db.py` (NEW - 95 lines)
**Purpose:** World map connectivity graph  
**Data:**
- `LOCATION_GRAPH`: Dictionary of location relationships

**Functions:**
- `get_direction_to_location(from, to)`: Find direction between locations
- `get_edge_goal_for_direction(direction)`: Convert direction to edge goal
- `location_name_variants(location)`: Generate name variants for matching

#### `utils/pathfinding.py` (NEW - 450 lines)
**Purpose:** Full A* pathfinding system  
**Status:** Implemented but not currently used (local BFS is sufficient)

**Functions:**
- `find_path_in_area()`: A* within single map area
- `find_direction_to_goal()`: Strategic goal-based pathfinding
- `astar()`: Core A* algorithm
- `is_walkable()`: Tile walkability check
- `path_to_directions()`: Convert positions to direction list

### Test Files

#### `tests/test_local_pathfinding.py` (NEW - 122 lines)
**Purpose:** Validate local BFS pathfinding

**Test Scenario:**
- Player at center (7,7) of 15x15 grid
- Door UP at (7,6)
- Building blocking north (rows 4-7, columns 4-10)
- Goal: Navigate north

**Test Assertion:**
```python
chosen_direction = _local_pathfind_from_tiles(mock_state, 'north')
assert chosen_direction == 'RIGHT'  # Navigate around building
```

**Result:** ✅ PASS

#### `tests/test_map_validation.py` (NEW - 135 lines)
**Purpose:** Validate map stitcher bounds checking

**Test Scenarios:**
1. **Stale Data Test:**
   - Player at (7, 17)
   - Map bounds: X:43-57, Y:43-57
   - Expected: Validation FAILS (stale data detected)
   - Result: ✅ PASS

2. **Fresh Data Test:**
   - Player at (7, 17)
   - Map bounds: X:0-20, Y:0-30
   - Expected: Validation PASSES
   - Result: ✅ PASS

### Documentation Files

#### `docs/PATHFINDING_ARCHITECTURE_PLAN.md` (existing, for reference)
**Status:** Historical document showing original design  
**Note:** Final implementation differs (uses local BFS instead of full A* primarily)

#### `docs/PATHFINDING_SUMMARY.md` (THIS FILE - NEW)
**Purpose:** Complete record of pathfinding implementation

---

## Testing

### Unit Tests
1. **Local Pathfinding Test** (`test_local_pathfinding.py`)
   - Status: ✅ PASS
   - Validates BFS finds path around obstacles
   - Confirms door avoidance

2. **Map Validation Test** (`test_map_validation.py`)
   - Status: ✅ PASS
   - Confirms stale data detection works
   - Validates fresh data acceptance

### Integration Testing
**Test Command:**
```bash
python run.py --agent-auto --load-state Emerald-GBAdvance/splits/03_birch/03_birch
```

**Observed Behavior:**
```
Step 0: Position (7, 17)
  Map stitcher validation FAILED (stale bounds)
  Local A* activated
  Goal: north
  Chose: RIGHT ✅
  
Step 1: Position (8, 17)
  Local A* activated
  Chose: RIGHT ✅
  
Step 2: Position (9, 17)
  Local A* activated
  Chose: RIGHT ✅

[Agent navigates around building, eventually reaches north]
```

**Result:** ✅ Bot successfully navigates from (7,17) → north without re-entering lab

### Regression Testing
- ✅ Does not interfere with opener_bot (splits 0-2)
- ✅ Gracefully falls back to VLM if no path found
- ✅ Works with split states (03_birch, 04_rival, etc.)

---

## Future Enhancements

### Short Term (Low-hanging fruit)
1. **Use Full A* When Map Stitcher Valid**
   - Currently: Always uses local BFS
   - Enhancement: Use `utils/pathfinding.py` when bounds are valid
   - Benefit: Can navigate beyond 15x15 view

2. **Goal Parser Improvements**
   - Add more NPC patterns
   - Support milestone-based goals
   - Handle compound goals (e.g., "get potion then heal")

3. **Location Database Expansion**
   - Add all Emerald locations
   - Include building interiors
   - Multi-area pathfinding (Littleroot → Petalburg via Route 101 + 102)

### Medium Term (Optimization)
4. **Path Caching**
   - Store computed paths between steps
   - Invalidate when position changes
   - Reduces redundant BFS calls

5. **Warp-Aware Pathfinding**
   - Use warps strategically (e.g., Fly, Teleport)
   - Cross-area pathfinding via warp connections
   - Optimize backtracking (return to Pokemon Center)

6. **Dynamic Obstacle Avoidance**
   - Track NPC positions
   - Avoid trainer line-of-sight
   - Respect one-way ledges

### Long Term (Complex Features)
7. **Exploration Strategy**
   - Systematically explore unknown areas
   - Build complete map before progressing
   - Identify items/collectibles

8. **Route Optimization**
   - Plan multi-waypoint routes
   - Minimize total distance
   - Consider item collection en route

9. **Battle Zone Avoidance**
   - Learn trainer positions from experience
   - Avoid wild Pokemon areas when low health
   - Path through safe zones

---

## Lessons Learned

### What Worked Well
1. **Hybrid Approach:** Validation + local pathfinding is robust
2. **Test-Driven:** Unit tests caught issues early
3. **Incremental:** BFS first, can add full A* later
4. **Separation of Concerns:** Goal parsing separate from pathfinding

### What Could Be Better
1. **Documentation:** Should have documented architecture earlier
2. **Testing:** Could use more edge cases (e.g., surrounded by walls)
3. **Performance:** BFS on every step could be cached

### Key Insights
1. **Map Stitcher Singleton:** Can accumulate stale data from previous runs
   - Solution: Always validate bounds before use
   
2. **VLM Limitations:** 15x15 view is insufficient for complex navigation
   - Solution: Algorithmic pathfinding for structured environments
   
3. **Local > Global:** 15x15 BFS pathfinding is often sufficient
   - Simpler than full A* across large maps
   - Faster execution
   - Fewer failure modes

4. **Goal-Driven Design:** Extracting goals from plans prevents hardcoded logic
   - More maintainable
   - Easier to extend
   - Generalizes to new scenarios

---

## Conclusion

The pathfinding system successfully solves the "re-entering lab" bug and provides
a robust foundation for future navigation improvements.

**Key Achievements:**
- ✅ Agent navigates around obstacles (doesn't re-enter lab)
- ✅ Handles split states with stale map data
- ✅ Falls back gracefully to VLM when pathfinding fails
- ✅ Extensible architecture (can add full A* easily)
- ✅ Well-tested (unit + integration tests passing)

**Next Steps:**
- Monitor performance during full runs
- Add more locations to location database
- Consider enabling full A* for long-distance navigation
- Profile BFS performance (may need optimization for large areas)

---

**End of Pathfinding Summary**  
*Last updated: November 7, 2025*
