# Door Detection and Map Corruption Investigation

**Date:** November 12, 2025  
**Status:** UNRESOLVED - Documented for future investigation  
**Decision:** Skip Pokemon Center entry for now, not critical for progression

## Problem Summary

Attempted to enable pathfinding to Pokemon Center in Oldale Town. Encountered two major issues:

1. **Door tiles not being detected as walkable** - Position (6,16) with tile_id=97, behavior=105 (ANIMATED_DOOR) rendering as '#' instead of 'D'
2. **Severe map corruption near Pokemon Center entrance** - Spurious terrain symbols (Ice, Sand, Water, PCs) appearing when player approaches (6,17)

## Technical Details

### Door Tile Structure (Pokemon Emerald)

Pokemon Centers use a 2x2 building pattern with tile IDs 96-99:

```
Row 7 (y=15): [88, 89, 90, 91] - Top of building
Row 8 (y=16): [96, 97, 98, 99] - Bottom with door
```

**Critical Discovery:**
- Tile 96: behavior=0 (NORMAL), collision=1 → Wall
- **Tile 97: behavior=105 (ANIMATED_DOOR), collision=1 → Door (should be walkable)**
- Tile 98: behavior=0 (NORMAL), collision=1 → Wall  
- Tile 99: behavior=0 (NORMAL), collision=1 → Wall

**Key Insight:** Door tiles with behavior=105 are WALKABLE despite collision=1 because you walk INTO them to trigger warps. They act as goal tiles for pathfinding.

### Attempted Fixes (All Failed)

#### Fix Attempt 1: Add Tile ID Range Check
**Approach:** Check `if tile_id in range(96, 100)` to convert building tiles to 'D'

**Result:** WORSE - Made ALL building tiles (96, 98, 99) appear walkable, agent tried to walk through walls

**Code:**
```python
# In _tile_to_symbol()
elif tile_id in range(96, 100):  # Door tile IDs 96-99
    return 'D'  # WRONG - marks walls as doors
```

#### Fix Attempt 2: Behavior-Only Detection
**Approach:** Remove tile_id checks, only use behavior values

**Code:**
```python
elif behavior_val == 105:  # ANIMATED_DOOR
    return 'D'
```

**Result:** STILL BROKEN - tile still renders as '#'

**Debug Evidence:**
```
🚪 [TILE DEBUG] Door/Warp tile: tile_id=97, behavior=105, collision=1
🚪 [DOOR DEBUG] Oldale (6, 16): tile=(99, <MetatileBehavior.NORMAL: 0>, 1), symbol='#'
```

**Analysis:** Map stitcher detects tile_id=97 with behavior=105, but at position (6,16) it shows tile_id=99 with behavior=0. **Coordinate mapping is broken.**

#### Fix Attempt 3: Change Target Coordinates
**Approach:** Try targeting (6,17) or (5,16) instead of (6,16)

**Result:** REJECTED by user - "6,16 is the warp tile that takes us into the building"

**Evidence from logs:**
```
📍 Position change detected: (6, 17), map: (0, 10)  # Player on threshold
🎮 Server processing action: UP
📍 Position change detected: (6, 17), map: (2, 2)  # Warp triggered!
🔄 Creating warp connection: (6, 17) -> (6, 17) (maps 10 -> 514)
```

User is correct - walking UP from (6,17) triggers warp, suggesting (6,16) is the entry tile.

## Map Corruption Issue

### Observed Corruption Pattern

When player moves from (8,18) to (6,17), map rendering becomes severely corrupted:

**Clean Map (Player at 8,18):**
```
Normal terrain: . # ~ D
Consistent layout
No anomalies
```

**Corrupted Map (Player at 6,17):**
```
Spurious symbols: I (Ice), s (Sand), W (Water), C (PC)
Extra doors (D) appearing
Impossible terrain combinations
Corruption localized around Pokemon Center
```

### Corruption Evidence

```
Map at (6,17):
? . . # # # . # # . . . . # . # #
? . . # # # # # # . . . . # . # #
? . . . . D D . . . . . # # . . .  ← Extra doors
  # # # # # # # # C # # # # . . .  ← Computer symbol outdoors
? . . . . . . . . C . . . # . . .  ← Another computer
? I s s . . . . . . . . . # . . .  ← Ice and Sand in town
? . . . I s . . . . . . . # . . #
? . . . I s . . . . . . s # . . #  ← More sand/ice
```

**Normal outdoor town should only have:** `.` `#` `~` `D` (maybe ledges)  
**Should NOT have:** `I` `s` `W` `C` - these are interior/special area tiles

### Root Cause Hypotheses

1. **Door Preservation Gone Wrong**
   - Preservation logic caching tiles from Pokemon Center INTERIOR (map_id=514)
   - Incorrectly placing them on Oldale Town exterior (map_id=10)
   - PCs, special terrain from interior bleeding into outdoor map

2. **Map Buffer Corruption**
   - Game memory has multiple map layers loaded near buildings
   - Reading from wrong buffer when player approaches entrances
   - Memory reader getting confused between active map and adjacent maps

3. **Coordinate Transformation Error**
   - Local coordinates being incorrectly converted to global grid positions
   - Tiles from map (2,2) [Pokemon Center] being placed at wrong coords in map (0,10) [Oldale]
   - Coordinate offset calculations failing near warp points

4. **Cache Poisoning**
   - Old data from previous explorations (when inside Pokemon Center)
   - Being merged with current outdoor map data
   - Preservation logic unable to distinguish which tiles belong to which map

### Timing of Corruption

Corruption appears specifically when:
- Player position is (6,17) - **right at the warp threshold**
- Map stitcher processes tiles near the Pokemon Center entrance
- Distance to building entrance < 3 tiles

This strongly suggests the preservation/warp logic is confusing tiles from the **destination map** with tiles on the **source map**.

## Attempted Debugging

### Memory Read Analysis

Consistent warnings in logs:
```
WARNING: Map buffer corruption detected: dimensions changed from 35x34 to 0x0
Outdoor map has 90.2% unknown tiles, retrying with cache invalidation
📊 PRE-PROCESSING TILES: 90.2% unknown (203/225), 0 corrupted
```

**Implication:** Tile data from memory is unreliable. When >90% tiles are unknown, should we even trust the remaining 10%?

### Coordinate Mapping Mystery

From raw map data array (row 6, y=16):
```python
[(468, ...), (469, ...), (468, ...), (471, ...), (1, ...), 
 (96, ...), (97, <ANIMATED_DOOR: 105>, ...), (98, ...), (99, ...), ...]
 #           #           #           #          #
 Index 0     Index 1     Index 2     Index 3    Index 4
                                                Index 5: tile 96
                                                Index 6: tile 97 ← THE DOOR
                                                Index 7: tile 98
                                                Index 8: tile 99
```

But position (6,16) in world coordinates shows tile 99, not tile 97.

**This means:** Either the array indexing is wrong, OR the world coordinate → array index conversion is broken.

## Proposed Solutions (Not Implemented)

### 1. Map Integrity Validation
- Scan for impossible tile combinations before rendering
- Flag when >5 terrain types appear in small area
- Reject tiles with symbols (I, s, W, C) in outdoor town maps

### 2. Disable Preservation Near Buildings
- Turn off door preservation within 3-tile radius of buildings
- Force fresh reads instead of cached/preserved tiles
- Test if corruption disappears

### 3. Map Layer Separation
- Track source map_id for each tile
- Never allow map_id=514 tiles to persist on map_id=10
- Clear all cached tiles on map_id changes

### 4. Coordinate Audit Trail
- Log: "Tile X at position Y came from map_data[row][col] in map_id Z"
- Trace where corrupted tiles originate
- Verify local_x/local_y calculations

### 5. Use Warp Data Directly
- Instead of inferring doors from tiles, use game memory warp positions
- Render 'D' at known warp coordinates regardless of tile_id
- Bypass tile detection entirely for doors

### 6. Hardcode Building Positions
- Static Pokemon Center door at (6,16) = 'D'
- Don't run map stitcher within 5-tile radius
- Use predefined layouts for town centers

### 7. Memory Read Validation
- Don't trust tile data when >50% tiles are unknown
- Wait for memory to stabilize (multiple consistent reads)
- Add retry logic with exponential backoff

### 8. Dual Map System
- Maintain "raw observed tiles" separate from "interpreted map"
- Only apply door detection to interpreted copy
- Compare both to detect interpretation failures

## Why Position (6,16) is Correct

User provided clear evidence:

```
Player at (6,18) → moves LEFT → (6,17)
Player at (6,17) → moves UP → warp triggers
After warp: map changed from (0,10) to (2,2)
```

The warp activates when moving UP from (6,17), which means stepping onto (6,16). Therefore **(6,16) is definitively the warp tile**.

## Decision: Skip Pokemon Center Entry

**Rationale:**
1. Pokemon Center is not critical for immediate progression
2. Healing can be done via potions or other Pokemon Centers
3. Map corruption issue is deep and would require significant refactoring
4. Time better spent on core gameplay progression (Route 102, battles, etc.)

**Workaround:**
- Update objective manager to skip "heal at Pokemon Center" step
- Go directly to Route 102 exploration
- Revisit Pokemon Center functionality when time permits

## Files Affected

- `utils/map_stitcher.py` - Door detection logic in `_tile_to_symbol()` and preservation logic
- `agent/objective_manager.py` - Pokemon Center navigation target
- `agent/action.py` - Walkability checks (already includes 'D' in walkable tiles)

## Code References

### Current Door Detection (Broken)
```python
# utils/map_stitcher.py line ~1645
elif behavior_val == 96:  # NON_ANIMATED_DOOR
    return 'D'
elif behavior_val == 105:  # ANIMATED_DOOR
    return 'D'  # Should work but tile shows wrong behavior at (6,16)
```

### Current Preservation Logic
```python
# utils/map_stitcher.py line ~220
is_door_behavior = existing_behavior in [96, 105, 97, 98, 99, 100, 101, 106, 107]
if is_door_behavior:
    new_is_door = new_behavior in [96, 105, 97, 98, 99, 100, 101, 106, 107]
    if new_collision == 1 and not new_is_door:
        should_preserve_existing = True
```

### Current Walkability Check
```python
# agent/action.py
def is_walkable(pos: Tuple[int, int]) -> bool:
    if pos not in location_grid:
        return False
    tile = location_grid[pos]
    return tile in ['.', '_', '~', 'D', 'S']  # 'D' already included
```

## Lessons Learned

1. **Behavior values are not sufficient** - Tile at (6,16) reports wrong behavior value
2. **Coordinate mapping is unreliable** - Array indices don't match world coordinates
3. **Memory reads are unstable** - 90% unknown tiles suggests fundamental memory reading issue
4. **Preservation logic is too aggressive** - Caching tiles from multiple maps causes cross-contamination
5. **Door detection is context-dependent** - Same tile_id can have different behaviors in different contexts

## Future Work

If revisiting this issue:

1. Start with memory reading stability - fix the "90% unknown tiles" problem first
2. Add comprehensive logging for coordinate transformations
3. Implement map_id tracking to prevent cross-map tile pollution
4. Consider using game warp data directly instead of inferring from tiles
5. Add validation/sanity checks for impossible terrain combinations
6. Test door detection in simpler locations (Route buildings) before Pokemon Centers

## Related Issues

- Memory corruption warnings in `pokemon_env/memory_reader.py`
- Map buffer dimension changes (35x34 → 0x0)
- Warp connection logic in `utils/map_stitcher.py`
- Grid coordinate system in map stitcher vs local player coordinates

## References

- Game: Pokemon Emerald (GBA)
- Metatile system: 2-byte tile IDs with associated behaviors
- Behavior 105 = ANIMATED_DOOR (should trigger warp on entry)
- Map IDs: 0x000A (Oldale Town), 0x0202 (Pokemon Center 1F)
