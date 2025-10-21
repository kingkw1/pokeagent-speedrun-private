# Map Stitcher System - Complete Guide

## 📍 What is the Map Stitcher?

The Map Stitcher is a **persistent world-building system** that creates a unified map of the Pokemon Emerald game world by stitching together the 15x15 tile views seen by the player as they explore.

### Core Concept

Pokemon Emerald doesn't give you a complete map - you only see a **15x15 tile window** around your character at any time. The Map Stitcher:

1. **Captures** each 15x15 view as you move
2. **Merges** these views into a growing complete map for each location
3. **Tracks** connections between different areas (warps, doors, route transitions)
4. **Persists** all this data to disk so it survives across runs

Think of it like Google Maps Street View stitching together individual photos into a complete navigable map.

## 🎯 Current Usage

Based on your logs, the map stitcher is currently:

```
📍 Position change detected: (10, 15), map: (0, 16)
🗺️ Triggering map stitcher update for position change
🗺️ Got 15 tiles, updating map stitcher
✅ Map stitcher update completed
```

**What's happening:**
- Every time the player moves to a new position, it triggers an update
- The system reads a 15x15 tile area around the player (7 radius = 15x15)
- These tiles are merged into the persistent map for Route 101 (map ID 0x0010)
- The updated map is saved to `.pokeagent_cache/map_stitcher_data.json`

## 🏗️ Architecture

### Key Components

**1. MapArea** - Represents a single location (Route 101, Oldale Town, etc.)
```python
@dataclass
class MapArea:
    map_id: int                          # Unique ID (0x0010 = Route 101)
    location_name: str                   # "ROUTE 101"
    map_data: List[List[Tuple]]          # 100x100 grid of tiles (starts empty)
    player_last_position: Tuple[int, int]  # Last seen position
    explored_bounds: Dict                # min_x, max_x, min_y, max_y
    origin_offset: Dict                  # How to map player coords to grid
    visited_count: int                   # Number of times visited
    first_seen: float                    # When first discovered
    last_seen: float                     # When last visited
```

**2. WarpConnection** - Represents transitions between areas
```python
@dataclass
class WarpConnection:
    from_map_id: int            # Source location
    to_map_id: int              # Destination location
    from_position: (x, y)       # Where you were
    to_position: (x, y)         # Where you ended up
    warp_type: str              # "door", "stairs", "exit", "route_transition"
    direction: str              # "north", "south", "east", "west", "up", "down"
```

**3. MapStitcher** - The main coordinator
- Manages all MapAreas
- Tracks WarpConnections
- Handles tile merging logic
- Saves/loads from disk

### How Tile Merging Works

```python
# Player is at position (10, 15) in game coordinates
# System captures 15x15 tile window centered on player
# Tiles are mapped to internal grid:

world_x = player_pos[0] - center_x + dx  # 10 - 7 + dx
world_y = player_pos[1] - center_y + dy  # 15 - 7 + dy

# Convert to stored grid position using origin offset
grid_x = world_x + area.origin_offset['x']
grid_y = world_y + area.origin_offset['y']

# Store tile in map_data[grid_y][grid_x]
area.map_data[grid_y][grid_x] = (tile_id, behavior, collision)
```

The origin offset is calculated when first visiting an area:
```python
# Place player at center (50, 50) of initial 100x100 grid
area.origin_offset = {'x': 50 - player_pos[0], 'y': 50 - player_pos[1]}
```

This allows the grid to expand dynamically as you explore while maintaining consistent coordinates.

## 📊 Current Capabilities

### What It Can Do

✅ **Automatic Map Building**
- Merges 15x15 tile views into complete maps
- Expands grid dynamically (up to 200x200 tiles per location)
- Tracks explored vs unexplored areas
- Handles revisits correctly (doesn't duplicate)

✅ **Location Tracking**
- Identifies each unique map area by ID
- Resolves location names (ROUTE 101, OLDALE TOWN, etc.)
- Stores first/last visit timestamps
- Counts how many times you've visited each location

✅ **Warp Detection**
- Detects when you transition between maps
- Records the connection (position + direction)
- Can find warp locations (stairs, doors)

✅ **Data Persistence**
- Saves to `.pokeagent_cache/map_stitcher_data.json`
- Compressed storage format to save space
- Loads previous exploration on restart

✅ **Map Visualization**
- Can generate ASCII art maps of explored areas
- Shows player position (P)
- Shows NPCs (N)
- Shows walkable tiles (.), grass (~), water (≈), etc.
- Shows connections (arrows: ←→↑↓)

✅ **Map Queries**
```python
# Get the grid for a specific location
grid = map_stitcher.get_location_grid("ROUTE 101", simplified=True)
# Returns: {(x, y): symbol, ...}

# Get all known locations
areas = map_stitcher.map_areas  # Dict[map_id, MapArea]

# Get connections from a location
connections = map_stitcher.get_location_connections("ROUTE 101")

# Get world map layout showing how areas connect
layout = map_stitcher.get_world_map_layout()

# Get statistics
stats = map_stitcher.get_stats()
# Returns: total areas, total tiles explored, connections found, etc.
```

## 🚀 Are You Using It to Full Potential?

### Currently Using: ⭐⭐ (2/5 stars)

**What you're doing:**
- ✅ Updating map stitcher on position changes
- ✅ Building up complete maps as agent explores
- ✅ Persisting data across runs

**What you're NOT using:**

❌ **Map Data for Navigation**
- The stitched maps could tell the VLM about larger areas beyond the 15x15 view
- "You've already explored north - there's grass for 20 tiles then a town"
- "There's water blocking east - you need to go around"

❌ **Warp Connection Intelligence**
- "You've been in this building before - the exit is south 5 tiles"
- "This route connects to Oldale Town (been there) and Route 103 (not explored)"

❌ **Return Path Planning**
- "To get back to the Pokemon Center, go south 30 tiles, take the door, then west 15 tiles"

❌ **Exploration Efficiency**
- "You've fully explored the eastern part of Route 101 - prioritize west"
- "This area has 45% unexplored tiles - good for new discoveries"

❌ **Strategic Location Awareness**
- "There are 3 NPCs in this town you haven't talked to yet"
- "You're currently in Route 101, which connects to: Oldale Town (S), Route 103 (N)"

## 💡 Recommended Enhancements

### 1. Add Map Context to VLM Prompts ⚡ HIGH VALUE

Instead of just showing the 15x15 immediate view, show a larger context from stitched data:

```python
# Current: 15x15 view
# Enhanced: 30x30 or larger from stitched map

def get_extended_map_view(location_name, player_pos, radius=15):
    """Get a larger view from stitched map data"""
    grid = map_stitcher.get_location_grid(location_name)
    # Extract area around player_pos with larger radius
    # Show "you are here" in center with 30x30 context
    return extended_view
```

**Benefit:** VLM can see patterns like "there's a town 20 tiles north" instead of just grass immediately around it.

### 2. Add "Exploration Status" to Action Context ⚡ HIGH VALUE

```python
def get_exploration_status(location_name):
    area = map_stitcher.map_areas[map_id]
    bounds = area.explored_bounds
    total_cells = (bounds['max_x'] - bounds['min_x']) * (bounds['max_y'] - bounds['min_y'])
    explored_cells = count_non_null_tiles(area.map_data)
    return {
        'percent_explored': explored_cells / total_cells,
        'unexplored_directions': find_unexplored_edges(area),
        'visited_count': area.visited_count
    }
```

Add to VLM prompt:
```
EXPLORATION STATUS:
- Route 101: 45% explored (visited 3x)
- Unexplored areas: North (large), West (small)
- Suggestion: Head north to discover new areas
```

**Benefit:** Agent can prioritize exploration strategically.

### 3. Use Warp Connections for Smart Navigation ⚡ MEDIUM VALUE

```python
def get_return_path(current_location, target_location):
    """Find path using known warp connections"""
    # Dijkstra's algorithm through warp graph
    path = find_shortest_path(warps, current_location, target_location)
    return path  # [(location, direction, distance), ...]
```

Add to VLM prompt when player wants to return somewhere:
```
KNOWN PATH TO POKEMON CENTER:
1. Head south 30 tiles
2. Take door (south exit)
3. Head west 15 tiles to Pokemon Center
```

**Benefit:** Agent can navigate back to important locations.

### 4. NPC and POI Tracking ⚡ MEDIUM VALUE

```python
# Enhance MapArea to track points of interest
area.npcs_seen = [(x, y, "Youngster Joey"), ...]
area.items_found = [(x, y, "Potion"), ...]
area.trainers_fought = [(x, y, "Bug Catcher Rick"), ...]
```

Add to VLM prompt:
```
POINTS OF INTEREST IN THIS AREA:
- NPC "Youngster Joey" at (5, 10) - not talked to yet
- Item "Potion" at (12, 8) - picked up
- Trainer "Bug Catcher Rick" at (15, 12) - defeated
```

**Benefit:** Agent can return to talk to NPCs, find items systematically.

### 5. Connection Suggestions ⚡ LOW VALUE (but cool)

```python
def suggest_next_area(current_location):
    """Suggest which connected area to explore next"""
    connections = map_stitcher.get_location_connections(current_location)
    unvisited = [c for c in connections if c.to_map_id not in visited_map_ids]
    return unvisited[0] if unvisited else connections[0]
```

Add to VLM prompt:
```
AVAILABLE CONNECTIONS:
- North: Route 103 (unexplored) ⭐ RECOMMENDED
- South: Oldale Town (visited 2x)
```

**Benefit:** Guide exploration to discover new areas.

## 📁 Data Storage

The map stitcher saves to `.pokeagent_cache/map_stitcher_data.json`:

```json
{
  "areas": {
    "16": {  // Map ID 0x0010 = Route 101
      "map_id": 16,
      "location_name": "ROUTE 101",
      "trimmed_map_data": [[row, col, [tile_id, behavior, collision]], ...],
      "trim_offsets": {"row_offset": 40, "col_offset": 43},
      "player_last_position": [7, 12],
      "explored_bounds": {"min_x": 43, "max_x": 57, "min_y": 40, "max_y": 54},
      "origin_offset": {"x": 43, "y": 35},
      "visited_count": 6,
      "first_seen": 1729536123.45,
      "last_seen": 1729536145.67
    }
  },
  "warp_connections": [
    {
      "from_map_id": 16,  // Route 101
      "to_map_id": 48,    // Oldale Town
      "from_position": [10, 30],
      "to_position": [15, 5],
      "warp_type": "route_transition",
      "direction": "south"
    }
  ]
}
```

## 🎮 Example Integration

Here's how you could enhance the action prompt with map context:

```python
# In action.py, before calling VLM:

# Get extended map view from stitcher
location_name = state_data.get('player', {}).get('location', 'Unknown')
player_pos = (current_x, current_y)

# Get larger context from stitched map
extended_map = map_stitcher.generate_location_map_display(
    location_name, 
    player_pos, 
    npcs=state_data.get('npcs', []),
    connections=map_stitcher.get_location_connections(location_name)
)

# Get exploration status
area_stats = get_exploration_stats(location_name)

# Add to action prompt:
action_context.append(f"""
=== EXTENDED MAP VIEW (from exploration memory) ===
{chr(10).join(extended_map)}

=== EXPLORATION STATUS ===
- Area explored: {area_stats['percent_explored']:.0%}
- Visited this area: {area_stats['visited_count']} times
- Unexplored directions: {', '.join(area_stats['unexplored_directions'])}
""")
```

## 🎯 Recommended Next Steps

**Priority 1:** Add extended map view to VLM prompts
- Show 30x30 from stitched data instead of just 15x15
- Include exploration boundaries
- Estimated effort: 2-3 hours
- High impact for navigation quality

**Priority 2:** Add exploration status to action context
- Show % explored, visited count
- Suggest unexplored directions
- Estimated effort: 1-2 hours
- Medium-high impact for strategic exploration

**Priority 3:** Track and display NPCs/POIs
- Remember NPC positions
- Show which NPCs haven't been talked to
- Estimated effort: 3-4 hours
- Medium impact for completionist gameplay

**Priority 4:** Build navigation path system
- Use warp connections for return paths
- "How to get back to Pokemon Center"
- Estimated effort: 4-6 hours
- Medium impact for long-term navigation

## Summary

The map stitcher is a **powerful but underutilized** system. You're currently using it as a passive logger (2/5 stars), but it could be an **active navigation assistant** (5/5 stars) that helps the VLM make much smarter decisions about where to go and how to get there.

The biggest quick win would be **showing the VLM a larger map context from stitched data** instead of just the immediate 15x15 view. This would dramatically improve navigation quality with minimal code changes.
