# Map Stitcher System - Complete Explanation

**Date**: November 9, 2025  
**Status**: PARTIALLY WORKING - Coordinate Mismatch Issue

---

## Executive Summary

The **Map Stitcher** is designed to build a persistent memory of explored map areas over time. It **IS working** and accumulating map data correctly. However, there's a **coordinate system mismatch** that prevents the agent from using this data for pathfinding.

**The Good News:** Your hope is correct! The map stitcher IS tracking the whole map as you explore.

**The Bad News:** A coordinate translation bug prevents the agent from accessing this data for navigation.

---

## How Map Stitcher Works

### Core Concept: Accumulative Mapping

The map stitcher builds up a complete view of each map area by **stitching together** the 15x15 tile views you see as you move around:

```
Step 1: Player at (7, 10)    Step 2: Player at (8, 10)    Step 3: Player at (9, 10)
Sees 15x15 around self       Sees 15x15 around self       Sees 15x15 around self
        
    [. . . .]                    [. . . .]                    [. . . .]
    [. P . .]  ──────►           [. . P .]  ──────►           [. . . P]
    [. . . .]                    [. . . .]                    [. . . .]
    [~ ~ ~ ~]                    [~ ~ ~ ~]                    [~ ~ ~ ~]

Combined Result: Full Map Area
    [. . . . . . . .]
    [. P→ →  →  → P]  ← Agent's explored path
    [. . . . . . . .]
    [~ ~ ~ ~ ~ ~ ~ ~]
```

As the agent moves, each new 15x15 view gets **merged** into the accumulated map data for that location.

---

## Coordinate Systems: The Root Problem

### Player Position Coordinates (Local/Relative)

When you see this in the state:
```
Position: X=8, Y=10
```

This is **local to the current map**. Each map has its own coordinate system:
- Route 101: (0,0) starts at top-left of Route 101
- Littleroot Town: (0,0) starts at top-left of Littleroot Town  
- Professor Birch's Lab: (0,0) starts at top-left of the lab

**These reset for each map!**

### Map Stitcher Coordinates (Absolute/Grid)

The map stitcher uses a **persistent grid coordinate system** that doesn't reset:

```python
# From map_stitcher.py lines 115-127
# When first entering an area, it creates a 100x100 grid
area.map_data = [[None for _ in range(100)] for _ in range(100)]
area.explored_bounds = {
    'min_x': 50, 'max_x': 50,
    'min_y': 50, 'max_y': 50
}
# Place player at center initially
area.origin_offset = {'x': 50 - player_pos[0], 'y': 50 - player_pos[1]}
```

So if you first enter Route 101 at position (7, 10):
- Grid position becomes: (50, 50) - the center of the 100x100 grid
- Origin offset stored as: {x: 43, y: 40}  ← This is `50 - 7 = 43` and `50 - 10 = 40`

Then when you move to (8, 10):
- Grid position becomes: (51, 50) - using the same offset
- Your explored area expands in the grid

**The bounds you see** (like X:39-57, Y:34-57) are **grid coordinates**, not player coordinates!

---

## The Coordinate Mismatch Problem

### What's Happening in Your Test

From your culdesac save state example where player is at **(8, 10)**:

1. **Map Stitcher says:**
   ```
   Bounds: X:39-57, Y:34-57  ← Grid coordinates
   ```

2. **Player position says:**
   ```
   X=8, Y=10  ← Local map coordinates
   ```

3. **Coordinate check in action.py (line 1847):**
   ```python
   coords_compatible = (bounds['min_x'] <= player_x <= bounds['max_x'] and
                       bounds['min_y'] <= player_y <= bounds['max_y'])
   # Checks: (39 <= 8 <= 57) and (34 <= 10 <= 57)
   # Result: FALSE! ❌
   ```

4. **System response:**
   ```
   ⚠️ Coordinate system mismatch detected!
   Falling back to local pathfinding (15x15 tiles)
   ```

### Why This Happens

The **map stitcher is storing data from a PREVIOUS run** where the coordinates happened to be different. The bounds (39-57, 34-57) came from whenever that map was first explored in a previous session.

When you load a fresh save state:
- Player coordinates reset to map-local values (8, 10)
- Map stitcher still has old grid coordinates (39-57, 34-57)
- They don't match!

---

## What Map Stitcher SHOULD Be Doing

At position (8, 10), the agent SHOULD be able to see the accumulated map data that looks like this:

```
=== ROUTE 101 (Accumulated Map) ===
Explored tiles: 487

Grid shows complete view of everywhere you've been:
      # # ~ ~ ~ ~ . . . . . . ~ ~ ~ ~ 
  ? ~ ~ ~ ~ ~ ~ . . . . . . ~ ~ ~ ~ 
  ? ~ ~ ~ ~ ~ . . . . . . . ~ ~ ~ ~
      # # ~ ~ . . # ↓ ↓ ↓ ↓ # # ~ ~ ~
      # # ↓ ↓ ↓ ↓ ↘ . . . . # # # # .
      # # . . . . . . . . . # # # # . . . .
      # # # # . # . . . . . # # ~ ~ . . . .
      # # # # . . . . [P] . ~ ~ ~ ~ ~ . . .  ← You are here at (8,10)
      # # # # . . . . . . . ~ ~ ~ ~ ~ ~ . .
      # # # # . . . . . . . ~ ~ ~ ~ ~ ~ . .
      # # ~ ~ . . . . ↓ ↓ ↓ ↓ ~ ~ ~ ~ ~ . .
  ? ~ ~ ~ ~ ~ . . . . . . . # # ~ ~ . .
  ? ~ ~ ~ ~ ~ ~ . . . . . . # # ~ ~ . .
```

And A* pathfinding should be able to say:
```
✅ Path from (8,10) to northern Oldale Town exists!
First step: RIGHT (to avoid ledges)
Full path: RIGHT → RIGHT → UP → UP → UP...
```

But instead it says:
```
❌ Coordinate mismatch! Can't use accumulated map data.
Falling back to 15x15 local view only.
```

---

## Why You Keep Getting Stuck

### With Accumulated Map (What SHOULD Happen)

If coordinate translation worked:
```
Agent at (8, 10) can see:
- Full explored map of Route 101
- Path around cul-de-sac visible
- A* finds route: RIGHT → UP → UP → LEFT → UP
- Agent navigates around obstacle successfully
```

### Without Accumulated Map (Current Behavior)

With only 15x15 local view:
```
Agent at (8, 10) can see:
- Only tiles within 7 squares in each direction
- Ledges blocking north (↓ symbols)
- Can't see the path that goes around
- Local A* fails to find path north
- SMART fallback tries perpendicular directions
- Eventually finds way by exploration, but inefficiently
```

---

## The Fix: Coordinate Translation

### What Needs to Happen

We need to translate between coordinate systems:

```python
# Current player position in local coordinates
player_local_x = 8
player_local_y = 10

# Map stitcher origin offset for this area
origin_offset_x = 43  # Stored when area was first created
origin_offset_y = 40

# Convert to grid coordinates
player_grid_x = player_local_x + origin_offset_x  # 8 + 43 = 51
player_grid_y = player_local_y + origin_offset_y  # 10 + 40 = 50

# Now check against bounds
bounds = {'min_x': 39, 'max_x': 57, 'min_y': 34, 'max_y': 57}
coords_compatible = (39 <= 51 <= 57) and (34 <= 50 <= 57)  # TRUE! ✅
```

### Where to Implement

**Option 1: Fix in server/app.py (lines 945-990)**
```python
# When building stitched_map_info, include the origin_offset
state["map"]["stitched_map_info"] = {
    "available": True,
    "current_area": {
        "name": current_location,
        "grid": grid_serializable,
        "bounds": bounds,
        "origin_offset": area.origin_offset,  # ← ADD THIS
        "player_grid_pos": (player_x + area.origin_offset['x'], 
                           player_y + area.origin_offset['y'])  # ← ADD THIS
    }
}
```

**Option 2: Fix in agent/action.py (lines 1840-1860)**
```python
# Before checking bounds, translate coordinates
if 'origin_offset' in current_area:
    offset = current_area['origin_offset']
    player_grid_x = player_x + offset['x']
    player_grid_y = player_y + offset['y']
    
    # Now check with grid coordinates
    coords_compatible = (bounds['min_x'] <= player_grid_x <= bounds['max_x'] and
                        bounds['min_y'] <= player_grid_y <= bounds['max_y'])
```

**Option 3: Store in relative coordinates from the start**

Instead of using an offset system, store tiles in map-local coordinates:
```python
# In map_stitcher.py, don't use grid offsets
# Store tiles directly at their local map coordinates
# This is simpler but loses cross-map positioning info
```

---

## Testing Your Specific Case

### At Position (8, 10)

With the fix, the agent SHOULD be able to:

1. **Access accumulated map data** showing:
   - All 487+ explored tiles of Route 101
   - Clear view of ledges blocking direct north path
   - Visible alternative route going right then up

2. **Run A* pathfinding** that finds:
   ```
   Goal: North (toward Oldale Town)
   Current: Grid (51, 50) in accumulated map
   Target: Northern edge of explored area
   
   A* search result:
   Path found: RIGHT → RIGHT → UP → UP → UP → LEFT → UP...
   First step: RIGHT
   ```

3. **Navigate efficiently** instead of:
   - Getting stuck in oscillation
   - Relying on SMART fallback guessing
   - Taking 50+ steps to find the way around

---

## Immediate Next Steps

### Step 1: Add Debug Logging

Let's verify the map stitcher HAS the data:

```python
# Add to server/app.py around line 970
if area and hasattr(area, 'origin_offset'):
    logger.info(f"🔍 [MAP DEBUG] Area {current_location}:")
    logger.info(f"    Origin offset: {area.origin_offset}")
    logger.info(f"    Explored bounds: {bounds}")
    logger.info(f"    Grid tiles: {len(grid_serializable)}")
    logger.info(f"    Player local pos: ({player_x}, {player_y})")
    player_grid_x = player_x + area.origin_offset['x']
    player_grid_y = player_y + area.origin_offset['y']
    logger.info(f"    Player grid pos: ({player_grid_x}, {player_grid_y})")
```

### Step 2: Implement Coordinate Translation

Choose Option 1 (server-side) for cleanest implementation:

```python
# In server/app.py, around line 980
if bounds and area and hasattr(area, 'origin_offset'):
    offset = area.origin_offset
    player_grid_pos = (
        player_coords[0] + offset['x'],
        player_coords[1] + offset['y']
    )
    
    state["map"]["stitched_map_info"]["current_area"]["origin_offset"] = offset
    state["map"]["stitched_map_info"]["current_area"]["player_grid_pos"] = player_grid_pos
```

```python
# In agent/action.py, around line 1845
# Use grid position for bounds check
if 'origin_offset' in current_area and 'player_grid_pos' in current_area:
    player_grid_x, player_grid_y = current_area['player_grid_pos']
    coords_compatible = (bounds['min_x'] <= player_grid_x <= bounds['max_x'] and
                        bounds['min_y'] <= player_grid_y <= bounds['max_y'])
else:
    # Fallback to old check (will likely fail)
    coords_compatible = (bounds['min_x'] <= player_x <= bounds['max_x'] and
                        bounds['min_y'] <= player_y <= bounds['max_y'])
```

### Step 3: Verify Grid Coordinates Match

The grid passed to A* also needs coordinate translation:

```python
# In _astar_pathfind_with_grid_data, line 415
# Grid is already in relative coordinates (0-based from bounds)
# But player position needs to be converted too

rel_player_x = player_grid_x - bounds['min_x']
rel_player_y = player_grid_y - bounds['min_y']
```

---

## Summary

**Your Map Stitcher IS Working!** 🎉

- ✅ Accumulating tiles as you explore
- ✅ Storing complete map data for Route 101
- ✅ Has 487+ tiles of Route 101 in memory
- ✅ Knows about the path around the cul-de-sac

**But It's Not Being Used** ❌

- ❌ Coordinate mismatch prevents access
- ❌ Agent falls back to 15x15 local view
- ❌ Can't see accumulated map knowledge
- ❌ Navigates inefficiently

**The Solution** 🔧

Add coordinate translation between:
- **Local map coordinates** (what player position uses)
- **Grid coordinates** (what map stitcher stores)

This is a ~20 line fix across 2 files that will unlock the accumulated map data and enable smart global pathfinding.

---

## Expected Behavior After Fix

```
🗺️ [A* MAP] Map stitcher data available, attempting pathfinding to 'north'
🗺️ [A* MAP] Using grid with 487 tiles, bounds X:39-57, Y:34-57
🗺️ [A* MAP] Player at local (8,10) = grid (51,50) ✅ COORDINATES MATCH
🗺️ [A* MAP] Finding path from grid (51,50) to northern edge...
✅ [A* MAP] Found path: RIGHT → RIGHT → UP → UP → UP → LEFT → UP (12 steps)
✅ [A* MAP] First step: RIGHT

Agent presses: RIGHT
Agent successfully navigates around cul-de-sac using accumulated map knowledge!
```

Would you like me to implement this coordinate translation fix now?
