# A* Pathfinding Architecture Plan

## Executive Summary

After analyzing the comprehensive state, map stitcher, and current navigation system, **we should implement A* pathfinding using the Map Stitcher as the primary data source**, with the comprehensive state providing real-time validation and immediate movement options.

## Available Data Sources Analysis

### 1. **Comprehensive State** (Real-time, Limited Range)
```
Position: X=7, Y=17
MOVEMENT PREVIEW:
  UP   : (  7, 16) [D] WALKABLE - Door/Entrance
  DOWN : (  7, 18) [.] WALKABLE
  LEFT : (  6, 17) [#] BLOCKED - Impassable
  RIGHT: (  8, 17) [.] WALKABLE

MAP: LITTLEROOT TOWN
  ? ? ? ? ? ? ? ? ? ? ? ? ? ? ?  
? . . . . . . . . . . . . . . . ?
? . . . . . . . . . . . . . . . ?
[... 15x15 grid ...]
```

**Strengths:**
- ✅ Real-time, 100% accurate for immediate surroundings
- ✅ Shows exact tile types (Door, Stairs/Warp, etc.)
- ✅ Provides WALKABLE/BLOCKED status for all 4 directions
- ✅ Includes world coordinates (absolute positions)
- ✅ Updated every frame

**Limitations:**
- ❌ Only 15x15 tiles (7-tile radius around player)
- ❌ No historical data (can't plan beyond visible range)
- ❌ Doesn't show previously explored areas
- ❌ No connection/warp information

**Best Use:**
- Immediate obstacle avoidance
- Validating pathfinding moves
- Detecting warps/doors/special tiles

### 2. **Map Stitcher** (Historical, Complete Maps)

```python
# Data structure
map_stitcher.map_areas = {
    260: MapArea(  # Birch's Lab
        map_id=260,
        location_name='LITTLEROOT TOWN PROFESSOR BIRCHS LAB',
        map_data=[[tile, tile, ...], ...],  # Complete 100x100+ grid
        explored_bounds={'min_x': 3, 'max_x': 10, 'min_y': 8, 'max_y': 16},
        player_last_position=(6, 12),
        warp_tiles=[(6, 13, 'door'), ...],
        visited_count=5
    ),
    9: MapArea(  # Littleroot Town
        map_id=9,
        location_name='LITTLEROOT TOWN',
        map_data=[...],
        explored_bounds={'min_x': 0, 'max_x': 30, 'min_y': 0, 'max_y': 25}
    )
}

# Connections between areas
map_stitcher.warp_connections = [
    WarpConnection(
        from_map_id=9,      # Littleroot Town
        to_map_id=260,      # Birch's Lab
        from_position=(7, 17),  # Outside lab
        to_position=(6, 11),    # Inside lab
        warp_type='door',
        direction='up'
    ),
    # ... more connections
]
```

**Strengths:**
- ✅ Complete maps of all explored areas (100x100+ tiles)
- ✅ Historical exploration data (knows where you've been)
- ✅ Warp connection tracking (knows how areas connect)
- ✅ Tile symbols: '.', '#', 'D', 'S', '~', etc.
- ✅ Persistent across runs (saved to disk)
- ✅ Shows explored bounds (can identify unexplored regions)

**Limitations:**
- ❌ Not real-time (updated on position change only)
- ❌ May have unexplored gaps ('?' symbols)
- ❌ Coordinate system requires translation (origin_offset)
- ❌ Doesn't know about NPCs/dynamic objects

**Best Use:**
- Long-range pathfinding (beyond 15x15 view)
- Strategic navigation (return to previous locations)
- Warp/connection planning
- Exploration tracking

### 3. **Current Movement Preview System** (Hybrid)

```python
# From utils/state_formatter.py:get_movement_preview()
movement_preview = {
    'UP': {
        'new_coords': (7, 16),
        'blocked': False,
        'tile_symbol': 'D',
        'tile_description': 'WALKABLE - Door/Entrance'
    },
    'DOWN': {
        'new_coords': (7, 18),
        'blocked': False,
        'tile_symbol': '.',
        'tile_description': 'WALKABLE'
    },
    # ... LEFT, RIGHT
}
```

**Strengths:**
- ✅ Pre-computed walkability for all 4 directions
- ✅ Includes world coordinates for each move
- ✅ Tile descriptions (human-readable)
- ✅ Already integrated into action.py

**Best Use:**
- Converting A* direction to action
- Validating A* suggestions

## Recommended Architecture

### **Hybrid Approach: Map Stitcher + Comprehensive State**

```
┌─────────────────────────────────────────────────────────┐
│                  A* PATHFINDING SYSTEM                  │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌───────────────────┐             ┌────────────────────┐
│   MAP STITCHER    │             │ COMPREHENSIVE STATE│
│  (Path Planning)  │             │   (Validation)     │
└───────────────────┘             └────────────────────┘
        │                                   │
        │ • Complete area maps              │ • Real-time accuracy
        │ • Warp connections                │ • Immediate obstacles
        │ • Historical exploration          │ • Dynamic hazards
        │ • Long-range planning             │ • Move validation
        │                                   │
        └──────────────┬────────────────────┘
                       ▼
              ┌─────────────────┐
              │  ACTION OUTPUT  │
              │  (UP/DOWN/etc)  │
              └─────────────────┘
```

### Implementation Strategy

#### **Phase 1: Local A* (Within Current Area)**

Goal: Navigate from current position to target within same map area (e.g., lab exit to north edge of Littleroot)

```python
# utils/pathfinding.py
from typing import Tuple, List, Optional, Dict
from utils.map_stitcher import MapStitcher
import heapq

def find_path_in_area(
    map_stitcher: MapStitcher,
    location_name: str,
    start_pos: Tuple[int, int],
    goal_pos: Tuple[int, int],
    validate_move_fn=None  # Optional real-time validation
) -> Optional[List[str]]:
    """
    Find A* path within a single map area.
    
    Args:
        map_stitcher: MapStitcher instance with area data
        location_name: Current location (e.g., "LITTLEROOT TOWN")
        start_pos: Starting (x, y) in world coordinates
        goal_pos: Target (x, y) in world coordinates
        validate_move_fn: Optional function to validate moves in real-time
        
    Returns:
        List of directions ['UP', 'RIGHT', 'DOWN', ...] or None if no path
    """
    # Get location grid from map stitcher
    grid = map_stitcher.get_location_grid(location_name, simplified=True)
    # grid = {(x, y): symbol, ...}  where symbol is '.', '#', 'D', etc.
    
    if not grid:
        return None  # Area not explored yet
    
    # Convert to grid suitable for A*
    # Need to handle coordinate translation
    # ... A* implementation ...
    
    return directions  # ['UP', 'RIGHT', 'DOWN']
```

**Data Flow:**
1. Get `location_grid` from Map Stitcher (historical complete map)
2. Run A* on the grid
3. Validate each move with comprehensive state (optional safety check)
4. Return first direction from path

#### **Phase 2: Goal Heuristics**

For common navigation goals where exact coordinates unknown:

```python
def find_direction_to_goal(
    map_stitcher: MapStitcher,
    current_location: str,
    current_pos: Tuple[int, int],
    goal: str,  # "NORTH_EDGE", "SOUTH_EDGE", "OLDALE_TOWN", "POKEMON_CENTER"
    movement_preview: Dict  # Real-time validation
) -> Optional[str]:
    """
    Find best direction for strategic goals.
    
    Goals:
        - "NORTH_EDGE": Navigate to northern boundary of current area
        - "SOUTH_EDGE": Navigate to southern boundary
        - "EXPLORE": Move toward unexplored (?) tiles
        - "RETURN_TO_<location>": Use warp connections to return somewhere
    """
    if goal == "NORTH_EDGE":
        # Get location bounds from map stitcher
        area = get_area_for_location(map_stitcher, current_location)
        target_y = area.explored_bounds['min_y']
        target_x = current_pos[0]  # Keep same X
        return find_path_in_area(map_stitcher, current_location, 
                                 current_pos, (target_x, target_y))
    
    elif goal == "EXPLORE":
        # Find nearest '?' tile
        grid = map_stitcher.get_location_grid(current_location)
        unknown_tiles = [(x, y) for (x, y), sym in grid.items() if sym == '?']
        if unknown_tiles:
            # Pick closest unknown tile
            closest = min(unknown_tiles, 
                         key=lambda p: abs(p[0]-current_pos[0]) + abs(p[1]-current_pos[1]))
            return find_path_in_area(map_stitcher, current_location,
                                     current_pos, closest)
    
    # ... more goal types
```

#### **Phase 3: Warp-Aware Navigation (Cross-Area)**

Navigate between different map areas using warp connections:

```python
def find_path_to_location(
    map_stitcher: MapStitcher,
    current_location: str,
    current_pos: Tuple[int, int],
    target_location: str
) -> Optional[List[str]]:
    """
    Find path to different map area using warp connections.
    
    Example: Navigate from Birch's Lab → Littleroot Town → Route 101
    """
    # Build warp graph
    warp_graph = build_warp_graph(map_stitcher.warp_connections)
    
    # Find sequence of warps
    warp_sequence = dijkstra_warp_search(
        warp_graph,
        current_location,
        target_location
    )
    
    # For each warp in sequence:
    #   1. Path to warp position in current area
    #   2. Use warp (move through door/transition)
    #   3. Update current area
    
    return full_path_sequence
```

### Integration with action.py

Replace the naive navigation logic:

```python
# agent/action.py (around line 1091)

# BEFORE (naive):
if 'UP' in available_directions:
    instruction = "Oldale Town is NORTH. Choose UP to move NORTH."

# AFTER (A* based):
from utils.pathfinding import find_direction_to_goal

# Determine strategic goal
if current_location == "LITTLEROOT TOWN" and not reached_route_101:
    goal = "NORTH_EDGE"  # Get to Route 101
elif current_location == "ROUTE 101":
    goal = "NORTH_EDGE"  # Get to Oldale Town
else:
    goal = "EXPLORE"  # Default: explore unknown areas

# Get A* suggestion
suggested_direction = find_direction_to_goal(
    map_stitcher=map_stitcher,
    current_location=location_name,
    current_pos=(current_x, current_y),
    goal=goal,
    movement_preview=movement_preview  # Real-time validation
)

if suggested_direction:
    instruction = f"Pathfinding suggests: {suggested_direction}"
    # Optionally limit VLM choices to this direction
else:
    # Fallback to VLM decision
    instruction = "Pathfinding unavailable. Choose based on map."
```

## Specific Solutions to Current Problems

### Problem 1: Re-entering Lab via Warp

**Issue:** At (7, 17) outside lab, VLM chooses UP (warp back inside) instead of continuing north.

**A* Solution:**
```python
# When at (7, 17) in LITTLEROOT TOWN
# Goal: "NORTH_EDGE"

# Map stitcher shows:
# Position (7, 17): '.' (walkable)
# Position (7, 16): 'D' (door/warp)  ← AVOID THIS
# Position (7, 18): '.' (walkable)

# A* pathfinding:
# Target: (7, 4) (northern edge based on explored_bounds)
# Path: [(7,17), (7,18), (7,19), ... (7,4)]
# First move: DOWN (to 7,18)

# This avoids the warp at (7,16)!
```

**Implementation:**
```python
def is_warp_tile(grid: Dict, pos: Tuple[int, int]) -> bool:
    """Check if tile at position is a warp/door."""
    symbol = grid.get(pos, '#')
    return symbol in ['D', 'S']  # Door, Stairs

def find_path_avoiding_warps(grid, start, goal):
    """A* that treats warps as obstacles unless they're the goal."""
    # ... A* implementation ...
    # In neighbor checking:
    for neighbor in get_neighbors(current):
        if is_warp_tile(grid, neighbor) and neighbor != goal:
            continue  # Skip warps unless it's our destination
```

### Problem 2: Unknown Terrain Beyond View

**Issue:** VLM can't see Route 101 is north because it's beyond 15x15 view.

**Map Stitcher Solution:**
```python
# Map stitcher remembers connections:
connections = map_stitcher.get_location_connections("LITTLEROOT TOWN")
# Returns: [
#   ("PROFESSOR BIRCHS LAB", (7,17), (6,11), "south"),
#   ("ROUTE 101", (7,4), (10,30), "north")  ← This tells us north leads to Route 101!
# ]

# Use this to set goals:
if "ROUTE 101" in [conn[0] for conn in connections]:
    goal = find_connection_position("ROUTE 101")  # (7, 4)
```

## Implementation Checklist

### Minimal Viable Product (MVP)
- [ ] Create `utils/pathfinding.py`
- [ ] Implement `find_path_in_area()` - basic A* within single location
- [ ] Implement `find_direction_to_goal()` with "NORTH_EDGE" support
- [ ] Integrate into `action.py` to replace naive UP=NORTH logic
- [ ] Test: Navigate from (7,17) → northern edge without entering lab

### Enhanced Features
- [ ] Add warp avoidance logic (treat D/S as obstacles unless goal)
- [ ] Implement exploration goal (move toward '?' tiles)
- [ ] Add "stuck" detection (if no progress after N moves, try different approach)
- [ ] Cross-area pathfinding using warp connections

### Future Enhancements
- [ ] NPC avoidance (use dynamic obstacle detection)
- [ ] Trainer avoidance (learn trainer positions, avoid line-of-sight)
- [ ] Item collection routes (plan path to visit all items)
- [ ] Backtracking optimization (return to Pokemon Center efficiently)

## Code Architecture

```
utils/
  pathfinding.py          # NEW - A* implementation
    - find_path_in_area()
    - find_direction_to_goal()
    - build_warp_graph()
    - is_walkable()
    - heuristic()

  map_stitcher.py         # EXISTING - No changes needed
    - get_location_grid()
    - get_location_connections()
    - map_areas dict

  state_formatter.py      # EXISTING - No changes needed
    - get_movement_preview()

agent/
  action.py               # MODIFIED
    - Import pathfinding module
    - Replace naive navigation with A* calls
    - Keep VLM as fallback
```

## Performance Considerations

**Efficiency:**
- Map stitcher grids are ~30x30 tiles (explored areas only)
- A* on 30x30 grid: <1ms (negligible overhead)
- Could cache paths between steps (if position unchanged)

**Reliability:**
- Always validate A* suggestion with movement_preview before executing
- Fallback to VLM if A* returns None (unexplored area)
- Re-plan if path becomes blocked (dynamic obstacles)

## Why This Approach?

1. **Leverages existing data:** Map stitcher already has complete maps, no need to rebuild
2. **Hybrid reliability:** A* for planning, comprehensive state for validation
3. **Incremental implementation:** Can start with simple local pathfinding, add complexity later
4. **Solves current problem:** Directly fixes the "re-enter lab" bug with warp avoidance
5. **Extensible:** Easy to add new goals (explore, return to location, etc.)

## Next Steps

1. **Implement MVP** (est. 2-3 hours)
   - Create pathfinding.py with basic A*
   - Add NORTH_EDGE goal for Littleroot → Route 101
   - Integrate into action.py

2. **Test with birch_lab save** (est. 30 min)
   - Verify: Exits lab → goes DOWN instead of UP
   - Verify: Reaches northern edge without looping

3. **Add warp avoidance** (est. 1 hour)
   - Treat D/S tiles as obstacles
   - Ensures won't re-enter buildings accidentally

4. **Iterate based on results**
   - If works: Add more goals (EXPLORE, RETURN_TO, etc.)
   - If issues: Debug with detailed logging
