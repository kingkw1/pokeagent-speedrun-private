# Intelligent A* Pathfinding with Frontier-Based Maze Navigation

**Document Type**: Technical Architecture  
**Created**: November 14, 2025  
**Location**: `agent/action.py::_astar_pathfind_with_grid_data()`  
**Status**: Production-Ready ✅

---

## Executive Summary

The agent's pathfinding system is one of its most sophisticated components, enabling autonomous navigation through complex environments including mazes, obstacles, and unexplored areas. The key innovation is **multi-directional frontier exploration** that allows the agent to navigate maze-like areas (e.g., Petalburg Woods) without hard-coded routes.

### Key Achievement
Successfully navigates complex mazes by intelligently exploring perpendicular directions when direct paths are blocked, discovering alternative routes autonomously.

---

## Why This System Exists

### The Problem
Early pathfinding attempts failed in maze environments:
- **Route 104 → Petalburg Woods → Route 104 North** (Split 5)
- Agent would get stuck hitting walls repeatedly
- Simple "go north" instructions failed when direct path was blocked
- VLM alone couldn't plan multi-step maze navigation

### The Solution
Three-tier navigation system that combines:
1. **Global pathfinding** - Uses complete explored map (not just 15x15 view)
2. **Frontier-based exploration** - Discovers new areas intelligently
3. **Multi-directional search** - Finds alternative routes when blocked

---

## Architecture Overview

### Superiority Over Local Pathfinding

**`_astar_pathfind_with_grid_data()` vs `_local_pathfind_from_tiles()`**:

| Aspect | Local Pathfinding | Global A* (This System) |
|--------|------------------|------------------------|
| Map Size | 15x15 tiles (225 tiles) | Complete explored area (500-1000+ tiles) |
| Planning Scope | Immediate vicinity only | Entire room/area layout |
| Obstacle Awareness | Can't see beyond view | Sees all explored obstacles |
| Maze Navigation | Often fails | Handles complex mazes |
| Integration | Isolated | Uses MapStitcher data |

### Data Source: MapStitcher

The pathfinding system leverages the **MapStitcher** singleton which maintains:
- Complete explored map grid for each area
- Tile types ('.', '~', '#', 'D', '?', etc.)
- World coordinate mapping
- Area boundaries and connections

```python
# MapStitcher provides global context
location_grid = {
    (5, 10): '.',   # Floor
    (6, 10): '~',   # Grass
    (7, 10): '#',   # Wall
    (8, 10): '?',   # Portal/Unknown
    # ... hundreds more tiles
}
```

---

## Three-Tier Navigation Strategy

### 1️⃣ Direct Pathfinding (Specific Goal)

**When**: `goal_coords` provided AND goal tile is explored

**Process**:
```
Goal: (7, 0) - North exit portal
↓
Check if goal in explored grid
↓
Validate tile is walkable (., _, ~, D, ?)
↓
If walkable: A* path directly to goal
If blocked: Fall through to frontier navigation
```

**Use Cases**:
- Navigate to specific NPC coordinates
- Walk to known portal location
- Reach specific map position

**Key Innovation**: If goal coordinates point to a WALL (common with approximate goals), automatically falls back to frontier navigation to find actual walkable tiles nearby.

### 2️⃣ Frontier Navigation (Exploration)

**When**: Goal unexplored OR goal blocked

**Frontier Tile Definition**:
A walkable tile that has at least one unexplored neighbor (unknown '?' tile adjacent).

**Why Frontiers?**:
- Represent the "edge" of explored territory
- Moving to frontier = discovering new tiles
- Prioritizing frontiers = efficient exploration

#### The Maze Navigation Breakthrough

**Problem**: Direct frontier often blocked in mazes

**Old Behavior**:
```
Goal: North exit at (7, 0)

Map:
  ####?####  ← Goal somewhere here
  ##?..?##   
  ##....##
  ##.P..##   ← Player
  
Strategy: Only try north frontiers (?)
Result: No path found → STUCK
```

**New Behavior - Multi-Directional Frontier Search**:
```
Goal: North exit at (7, 0)

Map:
  ####?####  ← PRIMARY targets
  ##5..3##   ← PERPENDICULAR targets (backup)
  ##4.2.##
  ##.P..##
  
Strategy:
1. Find PRIMARY frontiers (north direction)
2. Find PERPENDICULAR frontiers (east/west)
3. A* tries PRIMARY first, then PERPENDICULAR
4. Discovers maze path by exploring sideways!

Result: Path found via 3→4→5→2→1 🎯
```

#### Frontier Selection Algorithm

```python
PRIMARY frontiers (toward goal):
- Tile in general goal direction (north for north goal)
- Makes progress on primary axis (Y for north/south)
- OR doesn't go backwards (allows perpendicular)
- Score = distance_to_goal + (distance_to_player * 0.1) - 5 (bonus)

PERPENDICULAR frontiers (backup):
- Tile perpendicular to goal direction (east/west for north goal)  
- At least 2 tiles offset perpendicular
- Within 3 tiles on goal axis (not going backwards)
- Score = distance_to_goal + (distance_to_player * 0.2)

Final target list:
[primary_1, primary_2, ..., perp_1, perp_2, ...]
      ↑ Try these first       ↑ Backup options
```

#### Scoring System

Lower score = higher priority for pathfinding:

```
score = distance_to_goal + (distance_to_player * weight)

Primary frontiers:
- weight = 0.1 (minimal player distance penalty)
- bonus = -5 (strongly preferred)

Perpendicular frontiers:
- weight = 0.2 (slight player distance penalty)
- bonus = 0 (allowed but secondary)
```

This ensures A* tries direct routes first, but has perpendicular fallbacks when blocked.

### 3️⃣ Fallback to VLM

**When**: No pathfindable frontiers found

**Action**: Return `None` → let VLM use visual context to decide

**Why**: Some edge cases benefit from visual analysis:
- Newly loaded areas (minimal explored map)
- Dialog interruptions
- Special game events

---

## A* Implementation Details

### Walkability Rules

```python
def is_walkable(pos):
    tile = location_grid[pos]
    
    # Walkable tiles:
    return tile in [
        '.',  # Floor/path
        '_',  # Bridge
        '~',  # Tall grass (with cost penalty)
        'D',  # Door (allowed as final target)
        'S',  # Stairs (allowed as final target)
    ]
    
    # NOT walkable:
    # '#' - Wall/tree/obstacle
    # Diagonal ledges - Player can't move diagonally
```

### Movement Cost System

Enables intelligent path selection (avoid grass for speedruns):

```python
def get_tile_cost(pos, avoid_grass=True):
    tile = location_grid[pos]
    
    if avoid_grass:
        if tile == '~':
            return 10.0  # Heavy penalty (wild encounters)
        elif tile in ['.', '_']:
            return 1.0   # Normal cost
    else:  # Training mode (future)
        if tile == '~':
            return 0.5   # PREFER grass (level grinding)
        elif tile in ['.', '_']:
            return 1.0
    
    # Ledges: small penalty (point of no return)
    if tile in LEDGE_TILES:
        return 1.5
```

**Grass Avoidance**: Current speedrun mode uses `avoid_grass=True`
- Paths around tall grass when possible
- Reduces random encounter rate
- Future: `training_mode=True` will SEEK grass for leveling

### Heuristic: Manhattan Distance

```python
def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
```

Perfect for grid-based Pokemon movement (no diagonal moves).

### Path Batching & Safety

**Batching**: Execute up to 8 moves in sequence for efficiency
```python
MAX_MOVEMENT_BATCH_SIZE = 8  # ~1 second of movement
```

**Warp Truncation**: Stop path at warp tiles for safety
```python
def _truncate_path_at_warp(path, path_coords, location_grid):
    for i, (x, y) in enumerate(path_coords):
        tile = location_grid.get((x, y))
        if tile in ['D', 'S', '?']:  # Door/Stairs/Portal
            return path[:i+1]  # Include warp step
    return path
```

Why? After warping, coordinates change → remaining path is invalid.

---

## Real-World Performance

### Petalburg Woods Case Study

**Challenge**: Navigate from Route 104 South to Route 104 North through maze

**Initial Behavior** (before multi-directional frontier):
- Agent stuck at Y=23, oscillating LEFT-RIGHT
- Could see north frontiers but couldn't path to them
- Smart fallback tried perpendicular but blindly (no pathfinding)
- Result: Infinite oscillation

**After Multi-Directional Frontier**:
```
Step 1: Find PRIMARY north frontiers → blocked
Step 2: Find PERPENDICULAR east/west frontiers → found!
Step 3: A* paths to east frontier
Step 4: Discovers new tiles, reveals maze path
Step 5: Eventually finds north path around obstacle
Step 6: SUCCESS - reaches Route 104 North ✅
```

**Key Metrics**:
- Explored tiles: 551 → 753 (40% increase through exploration)
- Position progress: Y=32 → Y=24 → Y=0 (reached goal)
- Oscillation: Eliminated (purposeful exploration, not bouncing)

---

## Integration with Game Systems

### Portal Handling

Portals ('?') are valid walkable targets:
```python
if goal_tile == '?':
    print(f"✅ Goal is portal/warp tile, pathfinding to: {goal_coords}")
    target_positions = [goal_coords]
```

Agent must walk ONTO portal to trigger warp.

### Ledge Navigation

Ledges are one-way obstacles with directional constraints:
```python
LEDGE_TILES = {
    '→': 'RIGHT',   # Can only traverse right
    '←': 'LEFT',    # Can only traverse left
    '↑': 'UP',      # Can only traverse up
    '↓': 'DOWN',    # Can only traverse down
}

# Diagonal ledges = WALLS (can't move diagonally)
DIAGONAL_LEDGES = ['↗', '↖', '↘', '↙']
```

### Warp Avoidance

Prevents immediate backtracking through warps:
```python
recent_positions = deque(maxlen=10)  # Last 10 positions
recent_positions.append((x, y, location))

def should_avoid_position(pos):
    # Check if position was recently visited in DIFFERENT location
    # (indicates a warp back to previous area)
    for recent_x, recent_y, recent_loc in recent_positions:
        if pos == (recent_x, recent_y) and location != recent_loc:
            return True  # Avoid warp loop
```

---

## Code Structure

### Function Signature

```python
def _astar_pathfind_with_grid_data(
    location_grid: dict,           # (x,y) → tile_symbol
    bounds: dict,                  # min_x, max_x, min_y, max_y
    current_pos: Tuple[int, int],  # Player world coords
    location: str,                 # Current area name
    goal_direction: str,           # 'north', 'south', etc.
    recent_positions: deque,       # Warp avoidance
    goal_coords: Tuple[int, int]   # Optional specific goal
) -> Optional[str]:                # 'UP', 'DOWN', 'LEFT', 'RIGHT' or None
```

### Execution Flow

```
1. Validate inputs (grid, position)
   ↓
2. Determine navigation mode:
   - goal_coords + explored? → Direct pathfinding
   - goal_coords but unexplored/blocked? → Frontier navigation
   - no goal_coords? → Frontier navigation
   ↓
3. Build target_positions list:
   - Direct: [goal_coords]
   - Frontier: [primary_1, primary_2, ..., perp_1, perp_2, ...]
   ↓
4. A* pathfinding to targets:
   - Priority queue with f_score = g_score + heuristic
   - Explore neighbors, check walkability
   - Apply movement costs (grass penalty)
   - Build path list
   ↓
5. Path post-processing:
   - Truncate at warp tiles
   - Batch movements (up to 8 steps)
   - Return first direction
   ↓
6. Return result or None
```

---

## Future Enhancements

### Training Mode
```python
# Current: Avoid grass (speedrun)
avoid_grass = True

# Future: Seek grass (training)
avoid_grass = False
```

When `training_mode=True`:
- Reverse grass cost (prefer grass over paths)
- Agent actively seeks tall grass for wild encounters
- Use for leveling up Pokemon before gyms

### Dynamic Difficulty
```python
# Adjust based on party strength
if party_avg_level < area_recommended_level:
    avoid_grass = False  # Need to level up
else:
    avoid_grass = True   # Strong enough, speedrun
```

### Multi-Goal Pathfinding
```python
# Current: Single goal
goal_coords = (7, 0)

# Future: Multiple acceptable goals
goal_coords = [(7, 0), (8, 0), (6, 0)]  # Any of these work
```

Useful for:
- Multiple NPCs that can advance objective
- Alternative exits
- Item pickup locations

---

## Debugging & Diagnostics

### Logging Levels

The system uses extensive logging for diagnostics:

```python
print(f"✅ [A* FRONTIER → GOAL] Found {len(primary_targets)} PRIMARY frontier tiles")
print(f"✅ [A* FRONTIER → GOAL] Found {len(perp_positions)} PERPENDICULAR frontier tiles")
print(f"🎯 [A* MAP] Found {len(target_positions)} potential targets")
print(f"⚠️ [A* MAP] No path found to {goal_direction}")
```

### Key Debug Indicators

| Symbol | Meaning |
|--------|---------|
| ✅ | Success - operation completed |
| ⚠️ | Warning - fallback or unexpected state |
| 🎯 | Target/Goal information |
| 🧭 | Navigation decision point |
| 🗺️ | Map/Pathfinding operation |

### Troubleshooting

**Agent stuck in one position**:
- Check `✅ [A* MAP] Using map stitcher grid with X tiles` - is X growing?
- If not growing: Agent not discovering new tiles → VLM might be stuck
- If growing but stuck: Path might be blocked → check frontier logs

**Agent oscillating**:
- Check `Found X PRIMARY frontier tiles` - are there primary options?
- Check `Found X PERPENDICULAR frontier tiles` - using backups?
- If both present: A* should succeed
- If neither present: Map data might be stale

**No path found**:
- Check `Target positions checked: X` - how many targets tried?
- Check explored tile count - is map too small? (need more exploration)
- Check bounds - is goal within explored area?

---

## Performance Characteristics

### Time Complexity
- A* worst case: **O(b^d)** where b=4 (directions), d=path_length
- With heuristic: **O(b·d·log(b·d))** for priority queue operations
- Typical: **O(n log n)** where n = explored tiles (~500-1000)

### Space Complexity
- Grid storage: **O(n)** for n explored tiles
- Visited set: **O(n)** worst case
- Priority queue: **O(n)** worst case
- Total: **O(n)** where n = explored tiles

### Real-World Performance
- Pathfinding decision: **< 100ms** typical
- Map stitcher query: **< 10ms**
- Total overhead: **Negligible** compared to VLM inference (~2-5 seconds)

---

## Testing & Validation

### Successful Test Cases

✅ **Petalburg Woods** (Complex maze)
- Multi-directional frontier search enabled completion
- No hard-coded routes required

✅ **Route transitions** (Simple pathfinding)
- Direct pathfinding to portal coordinates
- Handles approximate goals gracefully

✅ **Town navigation** (Building interiors)
- Finds doors and stairs correctly
- Avoids getting stuck in rooms

### Edge Cases Handled

✅ **Approximate goal coordinates**
- If goal points to wall, finds nearby walkable tiles
- Falls back to frontier navigation automatically

✅ **Freshly loaded save states**
- Handles minimal explored map gracefully
- Discovers tiles as needed

✅ **Warp loops**
- Recent position tracking prevents backtracking
- Avoids infinite warp cycles

---

## Conclusion

The intelligent A* pathfinding system with multi-directional frontier navigation is a cornerstone of the agent's autonomous capabilities. By combining:

1. **Global map awareness** (MapStitcher integration)
2. **Smart exploration** (frontier-based navigation)
3. **Maze handling** (perpendicular backup frontiers)

The agent can navigate complex game environments without hard-coded routes, discovering optimal paths through trial and intelligent exploration.

**Key Innovation**: When stuck, don't give up—explore perpendicular directions to discover alternative routes. This simple strategy enables autonomous maze navigation that rivals human intuition.

---

## References

**Source Code**: `agent/action.py`
- `_astar_pathfind_with_grid_data()` - Main pathfinding function (lines 655-1050)
- `_truncate_path_at_warp()` - Path safety (lines 115-145)

**Related Systems**:
- `pokemon_env/map_stitcher.py` - Global map storage
- `agent/objective_manager.py` - Goal coordination
- `agent/planning.py` - High-level strategy

**Test States**:
- `tests/save_states/route104_entered_save` - Petalburg Woods entrance

---

*Document generated from production code and real-world agent performance data.*
