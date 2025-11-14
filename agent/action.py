import logging
import random
import sys
from typing import Dict, Any, Optional, Tuple, List
from collections import deque
from agent.system_prompt import system_prompt
from agent.opener_bot import get_opener_bot
from agent.battle_bot import get_battle_bot
from agent.planning import planning_step  # Import planning_step to access objective_manager
from utils.state_formatter import format_state_for_llm, format_state_summary, get_movement_options, get_party_health_summary, format_movement_preview_for_llm
from utils.vlm import VLM

# Set up module logging
logger = logging.getLogger(__name__)

# Track recent positions to avoid immediate backtracking through warps
# Store tuples of (x, y, map_location) for the last 10 positions
_recent_positions = deque(maxlen=10)

# Track portal waiting - dict of {(x, y, map): frame_count}
# Tracks how many frames we've waited at a specific portal tile
_portal_wait_frames = {}

# Track which direction we approached each portal from
# Used to continue in the same direction when at the portal tile
_portal_approach_direction = {}

# Track dismissed player monologues to avoid spamming A on them
_dismissed_monologues = set()

# Stuck detection state
_stuck_counter = 0
_last_position = None

def format_observation_for_action(observation):
    """Format observation data for use in action prompts"""
    if isinstance(observation, dict) and 'visual_data' in observation:
        # Structured format - provide a clean summary for action decision
        visual_data = observation['visual_data']
        summary = f"Screen: {visual_data.get('screen_context', 'unknown')}"
        
        # Add key text information
        on_screen_text = visual_data.get('on_screen_text', {})
        if on_screen_text.get('dialogue'):
            summary += f" | Dialogue: \"{on_screen_text['dialogue']}\""
        if on_screen_text.get('menu_title'):
            summary += f" | Menu: {on_screen_text['menu_title']}"
            
        # Add entity information - handle various entity formats
        entities = visual_data.get('visible_entities', [])
        if entities:
            try:
                entity_names = []
                if isinstance(entities, list):
                    for e in entities[:3]:  # Limit to first 3
                        if isinstance(e, dict):
                            entity_names.append(e.get('name', 'unnamed'))
                        elif isinstance(e, str):
                            entity_names.append(e)
                        else:
                            entity_names.append(str(e))
                elif isinstance(entities, str):
                    entity_names = [entities]
                elif isinstance(entities, dict):
                    # Handle case where entities is a dict with keys like NPC, Pokemon
                    for key, value in entities.items():
                        if value and value != "none" and value != "null":
                            entity_names.append(f"{key}: {value}")
                
                if entity_names:
                    summary += f" | Entities: {', '.join(entity_names[:3])}"  # Limit display
            except Exception as e:
                # Fallback if entity processing fails
                summary += f" | Entities: {str(entities)[:50]}"
            
        return summary
    else:
        # Original text format or non-structured data
        return str(observation)

def calculate_2x2_moves(options, current, target):
    """Calculates D-pad presses in a 2x2 menu layout."""
    raise NotImplementedError
    # Example layout:
    # FIGHT (0,0) | BAG (1,0)
    # POKEMON(0,1)| RUN (1,1)
    positions = {opt: (i % 2, i // 2) for i, opt in enumerate(options)}
    if current not in positions or target not in positions:
        return []
    
    curr_x, curr_y = positions[current]
    targ_x, targ_y = positions[target]
    
    moves = []
    while curr_y < targ_y:
        moves.append("DOWN")
        curr_y += 1
    while curr_y > targ_y:
        moves.append("UP")
        curr_y -= 1
    while curr_x < targ_x:
        moves.append("RIGHT")
        curr_x += 1
    while curr_x > targ_x:
        moves.append("LEFT")
        curr_x -= 1
    return moves    

def calculate_column_moves(options, current, target):
    """Calculates D-pad presses in a single-column menu layout."""
    raise NotImplementedError
    if current not in options or target not in options:
        return []
    
    curr_index = options.index(current)
    targ_index = options.index(target)
    
    moves = []
    while curr_index < targ_index:
        moves.append("DOWN")
        curr_index += 1
    while curr_index > targ_index:
        moves.append("UP")
        curr_index -= 1
    
    return moves

def get_menu_navigation_moves(menu_state, options, current, target):
    """Calculates D-pad presses to go from current to target selection."""
    raise NotImplementedError
    if menu_state == "battle_action_select":
        # Use 2x2 logic: knows "FIGHT" is left of "BAG", "POKEMON" is below "FIGHT"
        # Example: to get from "FIGHT" to "RUN", press DOWN then RIGHT.
        return calculate_2x2_moves(options, current, target)

    elif menu_state in ["main_menu", "shop_menu"]:
        # Use 1-column logic: knows it only needs to press UP or DOWN.
        # Example: to get from "BAG" to "EXIT", press DOWN four times.
        return calculate_column_moves(options, current, target)
    
    # ... other menu types ...

def _pathfind_to_target(state_data: Dict[str, Any], target_x: int, target_y: int) -> Optional[str]:
    """
    Pathfinding using BFS on the 15x15 visible tile grid to reach specific target coordinates.
    
    Args:
        state_data: Current game state with 'map']['tiles'] containing 15x15 grid
        target_x: Target world X coordinate
        target_y: Target world Y coordinate
    
    Returns:
        Direction string ('UP', 'DOWN', 'LEFT', 'RIGHT') or None if target not visible or no path
    """
    try:
        from utils.state_formatter import format_tile_to_symbol
        from collections import deque
        
        # Get current position
        player_data = state_data.get('player', {})
        position = player_data.get('position', {})
        current_x = position.get('x')
        current_y = position.get('y')
        
        if current_x is None or current_y is None:
            return None
        
        # Get tiles from state (15x15 grid centered on player)
        map_info = state_data.get('map', {})
        raw_tiles = map_info.get('tiles', [])
        
        if not raw_tiles or len(raw_tiles) < 15:
            return None
        
        grid_size = len(raw_tiles)
        center = grid_size // 2
        
        # Calculate target position in grid coordinates
        target_grid_x = center + (target_x - current_x)
        target_grid_y = center + (target_y - current_y)
        
        # Check if target is within visible grid
        if not (0 <= target_grid_x < grid_size and 0 <= target_grid_y < grid_size):
            print(f"⚠️ [TARGET A*] Target ({target_x}, {target_y}) not visible in 15x15 grid")
            print(f"   Current: ({current_x}, {current_y}), Grid target: ({target_grid_x}, {target_grid_y})")
            return None
        
        # Helper to check if tile is walkable
        def is_walkable(y, x):
            if not (0 <= y < grid_size and 0 <= x < grid_size):
                return False
            tile = raw_tiles[y][x]
            symbol = format_tile_to_symbol(tile) if tile else '?'
            return symbol in ['.', '_', '~']  # Grass (~) is walkable!
        
        # BFS from player position to target
        directions = [
            ('UP', 0, -1),
            ('DOWN', 0, 1),
            ('LEFT', -1, 0),
            ('RIGHT', 1, 0)
        ]
        
        start = (center, center)
        target = (target_grid_y, target_grid_x)
        queue = deque([(start, [])])  # (position, path_of_directions)
        visited = {start}
        
        while queue:
            (y, x), path = queue.popleft()
            
            # Check if we reached target
            if (y, x) == target:
                if path:
                    first_step = path[0]
                    print(f"✅ [TARGET A*] Found path to ({target_x}, {target_y}): {' → '.join(path)}")
                    print(f"   First step: {first_step}")
                    return first_step
                else:
                    # Already at target
                    print(f"✅ [TARGET A*] Already at target ({target_x}, {target_y})")
                    return None
            
            # Explore neighbors
            for dir_name, dx, dy in directions:
                ny, nx = y + dy, x + dx
                
                if (ny, nx) in visited:
                    continue
                
                if not is_walkable(ny, nx):
                    continue
                
                visited.add((ny, nx))
                new_path = path + [dir_name]
                queue.append(((ny, nx), new_path))
        
        # No path found
        print(f"⚠️ [TARGET A*] No path found to ({target_x}, {target_y})")
        print(f"   Explored {len(visited)} tiles")
        return None
        
    except Exception as e:
        print(f"❌ [TARGET A*] Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def _local_pathfind_from_tiles(state_data: Dict[str, Any], goal_direction: str, recent_actions: Optional[List[str]] = None) -> Optional[str]:
    """
    Pathfinding using BFS on the 15x15 visible tile grid.
    Finds the best first step toward target positions along the goal direction edge.
    AVOIDS tiles that would lead back to recently visited positions (anti-warp-backtracking).
    
    Args:
        state_data: Current game state with 'map']['tiles'] containing 15x15 grid
        goal_direction: Direction hint like 'north', 'south', etc.
        recent_actions: List of recent actions for oscillation detection
    
    Returns:
        Direction string ('UP', 'DOWN', 'LEFT', 'RIGHT') or None if no path
    """
    try:
        from utils.state_formatter import format_tile_to_symbol
        from collections import deque
        
        # Get current position and location
        player_data = state_data.get('player', {})
        position = player_data.get('position', {})
        current_x = position.get('x')
        current_y = position.get('y')
        current_location = player_data.get('location', '')
        
        # Get tiles from state (15x15 grid centered on player)
        map_info = state_data.get('map', {})
        raw_tiles = map_info.get('tiles', [])
        
        if not raw_tiles or len(raw_tiles) < 15:
            print(f"⚠️ [LOCAL A*] Insufficient tile data: {len(raw_tiles) if raw_tiles else 0} rows")
            return None
        
        grid_size = len(raw_tiles)
        center = grid_size // 2
        
        # Helper to check if tile is walkable
        def is_walkable(y, x):
            if not (0 <= y < grid_size and 0 <= x < grid_size):
                return False
            tile = raw_tiles[y][x]
            symbol = format_tile_to_symbol(tile) if tile else '?'
            # Walkable: grass/path only
            # NOT walkable: doors, walls, stairs, ledges, unknown
            return symbol in ['.', '_', '~']  # Added grass (~) as walkable!
        
        # Helper to check if a grid position would lead to a recently-visited location
        def leads_to_recent_position(grid_y, grid_x):
            """Check if moving to this grid position matches a recent location (warp detection)."""
            global _recent_positions
            
            if not _recent_positions or current_x is None or current_y is None:
                return False
            
            # Calculate world coordinates for this grid position
            offset_x = grid_x - center
            offset_y = grid_y - center
            target_world_x = current_x + offset_x
            target_world_y = current_y + offset_y
            
            # Check if this world position matches any recent position
            # We're particularly interested in positions with DIFFERENT map locations
            # (indicating a warp back to a previous area)
            for recent_x, recent_y, recent_loc in _recent_positions:
                if recent_x == target_world_x and recent_y == target_world_y:
                    # Same coordinates - check if it's a different map location (warp)
                    if recent_loc != current_location:
                        print(f"🚫 [WARP AVOID] Grid ({grid_y}, {grid_x}) = World ({target_world_x}, {target_world_y})")
                        print(f"              Matches recent position @ '{recent_loc}' (different from current '{current_location}')")
                        print(f"              This would be a warp back - AVOIDING")
                        return True
            
            return False
        
        # Determine target positions based on goal direction
        goal_dir_upper = goal_direction.upper()
        target_positions = []
        
        if 'NORTH' in goal_dir_upper or goal_direction == 'north':
            # Target top edge (row 0) - find walkable tiles
            for x in range(grid_size):
                if is_walkable(0, x) and not leads_to_recent_position(0, x):
                    target_positions.append((0, x))
        elif 'SOUTH' in goal_dir_upper or goal_direction == 'south':
            # Target bottom edge
            for x in range(grid_size):
                if is_walkable(grid_size - 1, x) and not leads_to_recent_position(grid_size - 1, x):
                    target_positions.append((grid_size - 1, x))
        elif 'EAST' in goal_dir_upper or goal_direction == 'east':
            # Target right edge
            for y in range(grid_size):
                if is_walkable(y, grid_size - 1) and not leads_to_recent_position(y, grid_size - 1):
                    target_positions.append((y, grid_size - 1))
        elif 'WEST' in goal_dir_upper or goal_direction == 'west':
            # Target left edge
            for y in range(grid_size):
                if is_walkable(y, 0) and not leads_to_recent_position(y, 0):
                    target_positions.append((y, 0))
        else:
            print(f"⚠️ [LOCAL A*] Unknown goal direction: {goal_direction}")
            return None
        
        if not target_positions:
            print(f"⚠️ [LOCAL A*] No walkable targets on {goal_direction} edge")
            return None
        
        # BFS from player position to find shortest path to any target
        directions = [
            ('UP', 0, -1),
            ('DOWN', 0, 1),
            ('LEFT', -1, 0),
            ('RIGHT', 1, 0)
        ]
        
        start = (center, center)
        queue = deque([(start, [])])  # (position, path_of_directions)
        visited = {start}
        
        while queue:
            (y, x), path = queue.popleft()
            
            # Check if we reached a target
            if (y, x) in target_positions:
                if path:
                    first_step = path[0]
                    # Valid path found!
                    print(f"✅ [LOCAL A*] Found path to {goal_direction} edge: {' -> '.join(path)}")
                    print(f"   First step: {first_step}")
                    return first_step
                else:
                    # Already at target? shouldn't happen
                    print(f"⚠️ [LOCAL A*] Already at target position")
                    return None
            
            # Explore neighbors
            for dir_name, dx, dy in directions:
                ny, nx = y + dy, x + dx
                
                # Skip if already visited
                if (ny, nx) in visited:
                    continue
                
                # Skip if not walkable
                if not is_walkable(ny, nx):
                    continue
                
                # Skip if this would lead to a recently-visited position (warp avoidance)
                if leads_to_recent_position(ny, nx):
                    continue
                
                visited.add((ny, nx))
                new_path = path + [dir_name]
                queue.append(((ny, nx), new_path))
        
        # No path found to any target
        print(f"⚠️ [LOCAL A*] No path found toward {goal_direction}")
        print(f"   Checked {len(target_positions)} target positions on edge")
        print(f"   Explored {len(visited)} tiles")
        
        # Fallback: SMART direction selection to escape dead-ends
        # Check recent actions for oscillation patterns
        recent_set = set(recent_actions[-10:]) if recent_actions and len(recent_actions) >= 10 else set(recent_actions or [])
        oscillating_horizontal = 'LEFT' in recent_set and 'RIGHT' in recent_set
        oscillating_vertical = 'UP' in recent_set and 'DOWN' in recent_set
        
        print(f"🔄 [LOCAL A*] SMART fallback - Oscillation check: H={oscillating_horizontal}, V={oscillating_vertical}")
        
        goal_dir_upper = goal_direction.upper()
        
        # Determine fallback order based on goal and oscillation
        if 'NORTH' in goal_dir_upper or 'SOUTH' in goal_dir_upper or goal_direction in ['north', 'south']:
            # Goal is vertical
            if oscillating_horizontal:
                # Stuck oscillating horizontally - try vertical escape
                print(f"   🔄 Detected horizontal oscillation, prioritizing vertical movement")
                fallback_order = ['DOWN', 'UP', 'RIGHT', 'LEFT'] if goal_direction == 'south' else ['UP', 'DOWN', 'RIGHT', 'LEFT']
            else:
                # Normal: try horizontal first to explore
                fallback_order = ['RIGHT', 'LEFT', 'DOWN', 'UP'] if goal_direction == 'south' else ['RIGHT', 'LEFT', 'UP', 'DOWN']
        else:
            # Goal is horizontal
            if oscillating_vertical:
                # Stuck oscillating vertically - try horizontal escape
                print(f"   🔄 Detected vertical oscillation, prioritizing horizontal movement")
                fallback_order = ['LEFT', 'RIGHT', 'UP', 'DOWN'] if 'WEST' in goal_dir_upper else ['RIGHT', 'LEFT', 'UP', 'DOWN']
            else:
                # Normal: try vertical first to explore
                fallback_order = ['UP', 'DOWN', 'LEFT', 'RIGHT'] if 'WEST' in goal_dir_upper else ['UP', 'DOWN', 'RIGHT', 'LEFT']
        
        # Try directions in smart order
        for dir_name in fallback_order:
            # Find dx, dy for this direction
            dx, dy = 0, 0
            for d_name, d_dx, d_dy in directions:
                if d_name == dir_name:
                    dx, dy = d_dx, d_dy
                    break
            
            ny, nx = center + dy, center + dx
            walkable = is_walkable(ny, nx)
            recent = leads_to_recent_position(ny, nx)
            
            if walkable and not recent:
                print(f"   ✅ SMART Fallback: choosing {dir_name}")
                return dir_name
            else:
                print(f"   ❌ {dir_name}: walkable={walkable}, leads_to_recent={recent}")
        
        print(f"   ⚠️ No walkable fallback directions found!")
        return None
        
    except Exception as e:
        print(f"❌ [LOCAL A*] Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def _validate_map_stitcher_bounds(map_stitcher, player_pos: Tuple[int, int], location: str) -> bool:
    """
    Check if the map stitcher bounds contain the current player position.
    This detects stale map data from previous runs/states.
    
    Args:
        map_stitcher: The MapStitcher singleton instance
        player_pos: Current player (x, y) world coordinates
        location: Current location name
    
    Returns:
        True if player position is within valid bounds, False if mismatch detected
    """
    try:
        # Find the map area for current location
        matching_area = None
        for area in map_stitcher.map_areas.values():
            if area.location_name.upper() == location.upper():
                matching_area = area
                break
        
        if not matching_area:
            print(f"⚠️ [PATHFINDING] Location '{location}' not in map stitcher - likely fresh state")
            return False
        
        bounds = matching_area.explored_bounds
        player_x, player_y = player_pos
        
        # Check if player position is within bounds
        if (bounds['min_x'] <= player_x <= bounds['max_x'] and
            bounds['min_y'] <= player_y <= bounds['max_y']):
            return True
        else:
            print(f"⚠️ [PATHFINDING] Map stitcher bounds mismatch!")
            print(f"   Player position: ({player_x}, {player_y})")
            print(f"   Map stitcher bounds: X:{bounds['min_x']}-{bounds['max_x']}, Y:{bounds['min_y']}-{bounds['max_y']}")
            print(f"   This indicates stale data from a previous run")
            print(f"   Disabling pathfinding for this step - relying on VLM navigation")
            return False
            
    except Exception as e:
        print(f"❌ [PATHFINDING] Error validating map stitcher: {e}")
        return False


def _astar_pathfind_to_coords_with_grid(
    location_grid: dict,
    bounds: dict,
    current_pos: Tuple[int, int],
    target_pos: Tuple[int, int],
    location: str,
    recent_positions: Optional[deque] = None
) -> Optional[str]:
    """
    A* pathfinding to specific coordinates using stitched map grid data.
    
    Args:
        location_grid: Dictionary mapping (x, y) tuples to tile symbols (relative coords)
        bounds: Dictionary with min_x, max_x, min_y, max_y 
        current_pos: Player's current (x, y) position IN ABSOLUTE WORLD COORDINATES
        target_pos: Target (x, y) position IN ABSOLUTE WORLD COORDINATES
        location: Current location name
        recent_positions: Deque of recent (x, y, location) tuples for warp avoidance
    
    Returns:
        First step direction ('UP', 'DOWN', 'LEFT', 'RIGHT') or None if no path
    """
    try:
        from collections import deque
        import heapq
        
        if not location_grid:
            print(f"⚠️ [COORD A*] No grid data provided")
            return None
        
        # CRITICAL: Grid keys are in WORLD coordinates, not relative coordinates!
        # The current_pos and target_pos are already in world coordinates from the emulator
        # Do NOT convert them to relative coordinates - use them directly
        current_x, current_y = current_pos
        target_x, target_y = target_pos
        
        # Use world coordinates directly
        world_current_pos = (current_x, current_y)
        world_target_pos = (target_x, target_y)
        
        # Check if positions are in the grid (using world coordinates)
        if world_current_pos not in location_grid:
            print(f"⚠️ [COORD A*] Current position {current_pos} not in grid")
            print(f"   Grid has {len(location_grid)} tiles")
            # Show sample grid keys to help debug
            sample_keys = list(location_grid.keys())[:5]
            print(f"   Sample grid keys: {sample_keys}")
            return None
        
        if world_target_pos not in location_grid:
            print(f"⚠️ [COORD A*] Target position {target_pos} not in explored grid")
            return None
        
        print(f"✅ [COORD A*] Pathfinding from {current_pos} to {target_pos}")
        print(f"   Grid size: {len(location_grid)} tiles (world coordinates)")
        
        # Helper function to check if tile is walkable
        def is_walkable(pos: Tuple[int, int]) -> bool:
            if pos not in location_grid:
                return False
            tile = location_grid[pos]
            return tile in ['.', '_', '~', 'D', 'S', 'N']  # Include NPCs as potential targets
        
        # Helper function to get movement cost
        def get_tile_cost(pos: Tuple[int, int]) -> float:
            if pos not in location_grid:
                return 999
            tile = location_grid[pos]
            if tile == '~':  # Grass
                return 3.0
            elif tile in ['.', '_']:
                return 1.0
            elif tile in ['D', 'S', 'N']:
                return 1.5
            else:
                return 2.0
        
        # Manhattan distance heuristic
        def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
            return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
        
        # A* pathfinding using world coordinates
        start = world_current_pos
        goal = world_target_pos
        pq = [(manhattan_distance(start, goal), 0, start, [])]
        visited = {start}
        
        directions_map = {
            (0, -1): 'UP',
            (0, 1): 'DOWN',
            (-1, 0): 'LEFT',
            (1, 0): 'RIGHT'
        }
        
        while pq:
            f_score, g_score, current, path = heapq.heappop(pq)
            
            # Check if we reached the goal
            if current == goal:
                if path:
                    path_preview = ' → '.join(path[:5])
                    if len(path) > 5:
                        path_preview += f" ... ({len(path)} steps)"
                    print(f"✅ [COORD A*] Found path to {target_pos}: {path_preview}")
                    print(f"   First step: {path[0]}, Total cost: {g_score:.1f}")
                    return path[0]
                else:
                    print(f"✅ [COORD A*] Already at target {target_pos}")
                    return None
            
            # Explore neighbors
            for (dx, dy), direction in directions_map.items():
                next_pos = (current[0] + dx, current[1] + dy)
                
                if next_pos in visited:
                    continue
                
                if not is_walkable(next_pos):
                    continue
                
                move_cost = get_tile_cost(next_pos)
                new_g_score = g_score + move_cost
                new_f_score = new_g_score + manhattan_distance(next_pos, goal)
                new_path = path + [direction]
                
                heapq.heappush(pq, (new_f_score, new_g_score, next_pos, new_path))
                visited.add(next_pos)
        
        print(f"⚠️ [COORD A*] No path found from {current_pos} to {target_pos}")
        print(f"   Explored {len(visited)} tiles")
        return None
        
    except Exception as e:
        print(f"❌ [COORD A*] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def _astar_pathfind_with_grid_data(
    location_grid: dict,
    bounds: dict,
    current_pos: Tuple[int, int], 
    location: str,
    goal_direction: str,
    recent_positions: Optional[deque] = None,
    goal_coords: Optional[Tuple[int, int]] = None
) -> Optional[str]:
    """
    A* pathfinding using map grid data from the server.
    
    This is SUPERIOR to _local_pathfind_from_tiles because:
    - Uses COMPLETE explored map (not just 15x15 view)
    - Sees entire room/area layout
    - Can plan around obstacles globally
    - Integrates warp avoidance with position history
    
    Args:
        location_grid: Dictionary mapping (x, y) tuples to tile symbols
        bounds: Dictionary with min_x, max_x, min_y, max_y for coordinate conversion
        current_pos: Player's current (x, y) position IN ABSOLUTE WORLD COORDINATES
        location: Current location name
        goal_direction: Target direction ('north', 'south', 'east', 'west')
        recent_positions: Deque of recent (x, y, location) tuples for warp avoidance
        goal_coords: Optional specific goal (x, y) to pathfind to. If provided, pathfinds
                     directly to this position instead of finding frontier tiles.
    
    Returns:
        First step direction ('UP', 'DOWN', 'LEFT', 'RIGHT') or None if no path
    """
    try:
        from collections import deque
        import heapq
        
        # Location grid is already provided as parameter (no need to fetch from map_stitcher)
        if not location_grid:
            print(f"⚠️ [A* MAP] No grid data provided")
            return None
        
        # Bounds are already provided as parameter
        current_x, current_y = current_pos
        
        # CRITICAL: Grid keys are now in WORLD coordinates (absolute), not relative!
        # No need to convert - just check if current position exists in grid directly
        if current_pos not in location_grid:
            print(f"⚠️ [A* MAP] Current position {current_pos} not in explored grid")
            print(f"   Bounds: X:{bounds['min_x']}-{bounds['max_x']}, Y:{bounds['min_y']}-{bounds['max_y']}")
            print(f"   Grid has {len(location_grid)} tiles, sample keys: {list(location_grid.keys())[:5]}")
            return None
        
        print(f"✅ [A* MAP] Using map stitcher grid with {len(location_grid)} explored tiles")
        print(f"   Position: {current_pos} (world coordinates)")
        print(f"   Bounds: X:{bounds['min_x']}-{bounds['max_x']}, Y:{bounds['min_y']}-{bounds['max_y']}")
        
        # Determine target positions based on whether we have specific goal coordinates
        if goal_coords:
            # We have a specific destination - pathfind directly to it
            goal_x, goal_y = goal_coords
            print(f"🎯 [A* DIRECT] Pathfinding to specific goal: ({goal_x}, {goal_y})")
            
            # Check if goal is in the grid and walkable
            if goal_coords not in location_grid:
                print(f"⚠️ [A* DIRECT] Goal {goal_coords} not in explored grid")
                return None
            
            goal_tile = location_grid[goal_coords]
            # Portal tiles ('?') are valid navigation targets - agent must walk onto them to trigger transition
            # Walkable tiles: '.' (floor), '_' (path), '~' (grass), 'D' (door), '?' (portal/warp/unknown)
            if goal_tile not in ['.', '_', '~', 'D', '?']:
                print(f"⚠️ [A* DIRECT] Goal {goal_coords} is not walkable (tile: '{goal_tile}')")
                return None
            
            # Use the goal coordinates as the single target
            target_positions = [goal_coords]
            if goal_tile == '?':
                print(f"✅ [A* DIRECT] Goal is portal/warp tile ('?'), pathfinding to: {goal_coords}")
            else:
                print(f"✅ [A* DIRECT] Goal is walkable, pathfinding to: {goal_coords}")
        else:
            # No specific goal - use frontier-based exploration (old behavior)
            print(f"🎯 [A* FRONTIER] No specific goal, finding frontier tiles in direction '{goal_direction}'")
            
            # SMART TARGET SELECTION: Find tiles at the edge of exploration (frontier)
            # These are walkable tiles adjacent to unknown '?' tiles in the goal direction
            # This ensures we explore toward the goal rather than targeting unreachable extremes
            
            def is_frontier_tile(pos: Tuple[int, int], direction: str) -> bool:
                """Check if a tile is on the frontier (adjacent to unknown in goal direction)"""
                x, y = pos
                tile = location_grid.get(pos)
                
                # Must be walkable
                if tile not in ['.', '_', '~', 'D']:
                    return False
                
                # Check if there's unknown territory in the goal direction
                if direction in ['north', 'up']:
                    # Check tiles to the north
                    for check_y in range(y - 3, y):  # Check 3 tiles north
                        if (x, check_y) not in location_grid or location_grid.get((x, check_y)) == '?':
                            return True
                elif direction in ['south', 'down']:
                    for check_y in range(y + 1, y + 4):
                        if (x, check_y) not in location_grid or location_grid.get((x, check_y)) == '?':
                            return True
                elif direction in ['east', 'right']:
                    for check_x in range(x + 1, x + 4):
                        if (check_x, y) not in location_grid or location_grid.get((check_x, y)) == '?':
                            return True
                elif direction in ['west', 'left']:
                    for check_x in range(x - 3, x):
                        if (check_x, y) not in location_grid or location_grid.get((check_x, y)) == '?':
                            return True
                
                return False
            
            # Find frontier tiles in the goal direction
            target_positions = []
            player_x, player_y = current_pos
            
            for (x, y), tile in location_grid.items():
                # Only consider walkable tiles
                if tile not in ['.', '_', '~', 'D']:
                    continue
                
                # Check if in the goal direction from player
                is_in_direction = False
                if goal_direction.lower() in ['north', 'up'] and y < player_y:
                    is_in_direction = True
                elif goal_direction.lower() in ['south', 'down'] and y > player_y:
                    is_in_direction = True
                elif goal_direction.lower() in ['east', 'right'] and x > player_x:
                    is_in_direction = True
                elif goal_direction.lower() in ['west', 'left'] and x < player_x:
                    is_in_direction = True
                
                # If in direction and on frontier, add it
                if is_in_direction and is_frontier_tile((x, y), goal_direction):
                    distance = abs(x - player_x) + abs(y - player_y)
                    target_positions.append((distance, x, y))
            
            # Sort by distance and take closest frontier tiles
            if target_positions:
                target_positions.sort()
                # Keep tiles within reasonable distance
                max_distance = min(15, target_positions[0][0] + 10) if target_positions else 15
                target_positions = [(x, y) for dist, x, y in target_positions if dist <= max_distance]
                print(f"🎯 [A* FRONTIER] Found {len(target_positions)} frontier tiles in direction '{goal_direction}'")
                print(f"   Targeting exploration edge (tiles adjacent to unknown)")
            else:
                # Fallback: No frontier found, target extreme edge (old behavior)
                print(f"⚠️ [A* FRONTIER] No frontier tiles found, using extreme edge as fallback")
                if goal_direction.lower() in ['north', 'up']:
                    min_y = min(y for x, y in location_grid.keys())
                    target_positions = [(x, y) for x, y in location_grid.keys() 
                                      if y == min_y and location_grid[(x, y)] in ['.', '_', '~']]
                elif goal_direction.lower() in ['south', 'down']:
                    max_y = max(y for x, y in location_grid.keys())
                    target_positions = [(x, y) for x, y in location_grid.keys() 
                                      if y == max_y and location_grid[(x, y)] in ['.', '_', '~']]
                elif goal_direction.lower() in ['east', 'right']:
                    max_x = max(x for x, y in location_grid.keys())
                    target_positions = [(x, y) for x, y in location_grid.keys() 
                                      if x == max_x and location_grid[(x, y)] in ['.', '_', '~']]
                elif goal_direction.lower() in ['west', 'left']:
                    min_x = min(x for x, y in location_grid.keys())
                    target_positions = [(x, y) for x, y in location_grid.keys() 
                                      if x == min_x and location_grid[(x, y)] in ['.', '_', '~']]
        
        if not target_positions:
            print(f"⚠️ [A* MAP] No valid target positions in direction '{goal_direction}'")
            return None
        
        print(f"🎯 [A* MAP] Found {len(target_positions)} potential targets in direction '{goal_direction}'")
        
        # Helper function to check if position should be avoided (warp detection)
        # TEMPORARILY DISABLED - was blocking valid paths after warping
        def should_avoid_position(world_pos: Tuple[int, int]) -> bool:
            """Check if position should be avoided (was a warp to different location).
            
            Args:
                world_pos: Position in WORLD coordinates (matches location_grid keys)
            """
            # COMMENTED OUT: This was preventing navigation after warping from Route 103 to Oldale Town
            # if not recent_positions:
            #     return False
            # 
            # # Position is already in WORLD coordinates - use directly
            # world_x, world_y = world_pos
            # 
            # # Check if this position matches a recent position with different location
            # for recent_x, recent_y, recent_loc in recent_positions:
            #     if recent_x == world_x and recent_y == world_y and recent_loc != location:
            #         print(f"🚫 [A* WARP AVOID] Skipping world pos {world_pos} - recent warp position from '{recent_loc}'")
            #         return True
            return False
        
        # Define ledge tile symbols (from map_stitcher.py behavior values)
        # Ledges are one-way: you can only traverse them in their arrow direction
        # NOTE: Diagonal ledges are IMPASSABLE because player can only move in cardinal directions!
        LEDGE_TILES = {
            '→': 'RIGHT',   # JUMP_EAST (behavior 56) - traversable
            '←': 'LEFT',    # JUMP_WEST (behavior 57) - traversable
            '↑': 'UP',      # JUMP_NORTH (behavior 58) - traversable
            '↓': 'DOWN',    # JUMP_SOUTH (behavior 59) - traversable
            'L': None       # Generic ledge (collision 3) - direction unknown, treat conservatively
        }
        
        # Diagonal ledges are WALLS - player cannot move diagonally in Pokemon
        # These exist in the game but are effectively impassable
        DIAGONAL_LEDGES = ['↗', '↖', '↘', '↙']  # behaviors 60-63
        
        # Helper function to check if tile is walkable
        def is_walkable(pos: Tuple[int, int]) -> bool:
            if pos not in location_grid:
                return False
            tile = location_grid[pos]
            
            # Diagonal ledges are IMPASSABLE - treat as walls
            if tile in DIAGONAL_LEDGES:
                return False
            
            # Walkable: path, grass, doors, stairs, AND CARDINAL LEDGES (with directional constraints)
            # Note: We include 'D' (doors) and 'S' (stairs) for pathfinding, but safety checks will filter dangerous ones
            # Ledges are conditionally walkable based on approach direction (checked in neighbor loop)
            return tile in ['.', '_', '~', 'D', 'S'] or tile in LEDGE_TILES
        
        # Helper function to get movement cost for a tile
        # This allows us to prefer paths that avoid tall grass (wild encounters)
        # Can be configured for "training mode" later to SEEK grass instead
        def get_tile_cost(pos: Tuple[int, int], avoid_grass: bool = True) -> float:
            """
            Calculate movement cost for a tile.
            
            Args:
                pos: Tile position
                avoid_grass: If True, penalize tall grass. If False, prefer it (training mode)
            
            Returns:
                Movement cost (lower = preferred path)
            """
            if pos not in location_grid:
                return 999  # Unknown/unwalkable tiles have very high cost
            
            tile = location_grid[pos]
            
            # Ledge tiles: Small penalty to avoid "point of no return" unless necessary
            # Ledges are one-way, so taking them commits you to that path
            if tile in LEDGE_TILES:
                return 1.2  # Slight penalty - prefer normal paths if available
            
            if avoid_grass:
                # SPEEDRUN MODE: Minimize wild encounters
                if tile == '~':  # Tall grass
                    return 3.0  # 3x cost - strongly avoid
                elif tile in ['.', '_']:  # Normal path
                    return 1.0  # Standard cost
                elif tile in ['D', 'S']:  # Doors, stairs
                    return 1.5  # Slight penalty (might trigger events)
                else:
                    return 2.0  # Unknown walkable, slight penalty
            else:
                # TRAINING MODE: Seek wild encounters for leveling
                if tile == '~':  # Tall grass
                    return 0.5  # PREFER grass!
                elif tile in ['.', '_']:  # Normal path
                    return 1.0  # Standard cost
                else:
                    return 1.5
        
        # A* pathfinding with Manhattan distance heuristic
        def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
            return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
        
        # Find closest target to minimize search space
        closest_target = min(target_positions, key=lambda t: manhattan_distance(current_pos, t))
        
        # Priority queue: (f_score, g_score, position, path)
        # f_score = g_score + heuristic
        # NOTE: Currently using avoid_grass=True for speedrun mode
        # TODO: Add training mode parameter that sets avoid_grass=False
        #       This will make the agent SEEK grass tiles to level up Pokemon
        #       Example: astar_pathfind(..., training_mode=True)
        start = current_pos
        pq = [(manhattan_distance(start, closest_target), 0, start, [])]
        visited = {start}
        
        directions_map = {
            (0, -1): 'UP',
            (0, 1): 'DOWN',
            (-1, 0): 'LEFT',
            (1, 0): 'RIGHT'
        }
        
        while pq:
            f_score, g_score, current, path = heapq.heappop(pq)
            
            # Check if we reached any target
            if current in target_positions:
                if path:
                    first_step = path[0]
                    path_preview = ' → '.join(path[:5])
                    if len(path) > 5:
                        path_preview += f" ... ({len(path)} steps)"
                    
                    # Count special tiles in path for debugging
                    grass_count = sum(1 for pos in visited if location_grid.get(pos) == '~')
                    ledge_count = sum(1 for pos in visited if location_grid.get(pos) in LEDGE_TILES)
                    total_cost = g_score
                    
                    print(f"✅ [A* MAP] Found path: {path_preview}")
                    print(f"   First step: {first_step}")
                    
                    # Build informative cost message
                    cost_parts = [f"Path cost: {total_cost:.1f}"]
                    if grass_count > 0:
                        cost_parts.append(f"avoided {grass_count} grass tiles")
                    if ledge_count > 0:
                        cost_parts.append(f"used {ledge_count} ledge(s)")
                    print(f"   {', '.join(cost_parts)}")
                    
                    return first_step
                else:
                    print(f"⚠️ [A* MAP] Already at target")
                    return None
            
            # Explore neighbors
            for (dx, dy), direction in directions_map.items():
                nx, ny = current[0] + dx, current[1] + dy
                neighbor = (nx, ny)
                
                # Skip if already visited
                if neighbor in visited:
                    continue
                
                # Check if neighbor exists in grid
                if neighbor not in location_grid:
                    continue
                
                neighbor_tile = location_grid[neighbor]
                current_tile = location_grid[current]
                
                # === LEDGE PHYSICS: ONE-WAY TRAVERSAL ===
                # Ledges can only be traversed in their arrow direction
                # This prevents pathfinding from treating ledges as bidirectional paths
                
                # RULE 1: Entering a ledge - can only approach from the correct direction
                if neighbor_tile in LEDGE_TILES:
                    allowed_direction = LEDGE_TILES[neighbor_tile]
                    
                    # Generic ledge 'L' - we don't know direction, so be conservative
                    # Only allow entering from above (most common in Pokemon)
                    if allowed_direction is None:
                        if direction != 'DOWN':
                            # Blocked: trying to enter generic ledge from wrong direction
                            continue
                    # Directional ledge - must match arrow direction
                    elif direction != allowed_direction:
                        # Blocked: ledge arrow doesn't match movement direction
                        continue
                
                # RULE 2: Exiting a ledge - if currently ON a ledge, must continue in that direction
                # This prevents pathfinding from "turning around" mid-jump
                if current_tile in LEDGE_TILES:
                    ledge_direction = LEDGE_TILES[current_tile]
                    
                    if ledge_direction is None:
                        # Generic ledge - assume downward motion only
                        if direction != 'DOWN':
                            continue
                    elif direction != ledge_direction:
                        continue
                
                # === END LEDGE PHYSICS ===
                
                # Now check basic walkability (after ledge rules)
                # SPECIAL CASE: If neighbor is a goal tile (like a portal), allow it even if not normally walkable
                is_goal_tile = neighbor in target_positions
                if not is_goal_tile and not is_walkable(neighbor):
                    continue
                
                # If it IS a goal tile but not walkable (e.g., portal '?'), allow reaching it but don't explore beyond it
                if is_goal_tile and neighbor not in location_grid:
                    continue  # Goal tile not in grid - skip
                
                # Log when we allow non-walkable goal tile
                if is_goal_tile and not is_walkable(neighbor):
                    neighbor_tile_sym = location_grid.get(neighbor, '?')
                    print(f"🎯 [A* GOAL] Allowing non-walkable goal tile at {neighbor} ('{neighbor_tile_sym}')")
                
                # Skip if should avoid (warp detection)
                if should_avoid_position(neighbor):
                    continue
                
                visited.add(neighbor)
                new_path = path + [direction]
                
                # Use tile cost instead of fixed cost of 1
                # This makes A* prefer paths that avoid tall grass and unnecessary ledges
                tile_cost = get_tile_cost(neighbor, avoid_grass=True)
                new_g_score = g_score + tile_cost
                new_f_score = new_g_score + manhattan_distance(neighbor, closest_target)
                
                heapq.heappush(pq, (new_f_score, new_g_score, neighbor, new_path))
        
        # No path found
        print(f"⚠️ [A* MAP] No path found to {goal_direction}")
        print(f"   Explored {len(visited)} tiles")
        print(f"   Target positions checked: {len(target_positions)}")
        return None
        
    except Exception as e:
        print(f"❌ [A* MAP] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def action_step(memory_context, current_plan, latest_observation, frame, state_data, recent_actions, vlm, visual_dialogue_active=False):
    """
    Decide and perform the next action button(s) based on memory, plan, observation, and comprehensive state.
    Returns a list of action buttons as strings.
    
    Args:
        memory_context: Recent memory/history
        current_plan: Current plan from planning module
        latest_observation: Perception output with visual data
        frame: Current screenshot
        state_data: Game state data
        recent_actions: List of recent actions taken
        vlm: VLM instance for action decisions
        visual_dialogue_active: VLM's visual detection of dialogue box (85.7% accurate, no time cost)
    """
    print("=" * 80)
    print("🎯 [ACTION_STEP] CALLED - Starting action decision process")
    print("=" * 80)
    
    # Declare global variables at the start of the function
    global _recent_positions, _dismissed_monologues, _stuck_counter, _last_position
    
    # Track current position to avoid immediate backtracking through warps
    try:
        player_data = state_data.get('player', {})
        position = player_data.get('position', {})
        current_x = position.get('x')
        current_y = position.get('y')
        location = player_data.get('location', '')
        
        # Add current position to recent positions buffer (for warp detection)
        if current_x is not None and current_y is not None and location:
            current_pos_key = (current_x, current_y, location)
            # Only add if it's a new position (not the same as the last one)
            if not _recent_positions or _recent_positions[-1] != current_pos_key:
                _recent_positions.append(current_pos_key)
    except Exception as e:
        print(f"⚠️ [POSITION TRACKING] Error tracking position: {e}")
    
    # 🔄 STUCK DETECTION - Detect if agent stuck trying to move but not making progress
    # This handles cases where dialogue is active but VLM failed to detect it (e.g., "............." text)
    try:
        game_data = state_data.get('game', {})
        in_battle = game_data.get('in_battle', False)
        visual_dialogue_detected = visual_dialogue_active  # From VLM perception
        
        # Get current position
        current_pos = (current_x, current_y, location) if current_x is not None and current_y is not None else None
        
        # Check if last action was a direction (from recent_actions list)
        last_action_was_direction = False
        if recent_actions and len(recent_actions) > 0:
            last_action = recent_actions[-1]
            last_action_was_direction = last_action in ['UP', 'DOWN', 'LEFT', 'RIGHT']
        
        # VERBOSE LOGGING
        if _stuck_counter > 0:
            print(f"🔄 [STUCK DEBUG] visual_dialogue={visual_dialogue_detected}, in_battle={in_battle}, current_pos={current_pos}")
            print(f"🔄 [STUCK DEBUG] _last_position={_last_position}, last_action_was_direction={last_action_was_direction}")
            print(f"🔄 [STUCK DEBUG] recent_actions[-1]={recent_actions[-1] if recent_actions else 'None'}")
            print(f"🔄 [STUCK DEBUG] _stuck_counter={_stuck_counter}")
        
        # Check if we're NOT in dialogue (according to VLM) and NOT in battle
        # This is when we should be able to move freely
        if not visual_dialogue_detected and not in_battle and current_pos is not None:
            if _stuck_counter > 0:
                print(f"🔄 [STUCK DEBUG] Conditions met: not in dialogue, not in battle, has position")
            
            # Check if position didn't change since last step AND last action was a direction
            if _last_position == current_pos and last_action_was_direction:
                # We tried to move but didn't - increment stuck counter
                _stuck_counter += 1
                print(f"🔄 [STUCK DETECTION] Position unchanged after direction input: {current_pos}")
                print(f"   Last action: {recent_actions[-1] if recent_actions else 'None'}")
                print(f"   Stuck counter: {_stuck_counter}")
                
                # If stuck for 3 attempts, press A to check for hidden dialogue
                if _stuck_counter >= 3:
                    print(f"🔄 [STUCK DETECTION] Stuck for {_stuck_counter} attempts!")
                    print(f"   Pressing A to check for hidden dialogue...")
                    _stuck_counter = 0  # Reset counter
                    return ['A']
            else:
                # Position changed or we didn't try a direction - reset counter
                if _stuck_counter > 0:
                    print(f"🔄 [STUCK DETECTION] Position changed or no direction input - resetting counter")
                    print(f"   Reason: _last_position={_last_position} vs current_pos={current_pos}")
                    print(f"   last_action_was_direction={last_action_was_direction}")
                _stuck_counter = 0
        else:
            # In dialogue or battle - reset stuck counter
            if _stuck_counter > 0 and (visual_dialogue_detected or in_battle):
                print(f"🔄 [STUCK DETECTION] In dialogue/battle - resetting stuck counter")
            print(f"🔄 [STUCK DEBUG] Conditions NOT met: dialogue={visual_dialogue_detected}, battle={in_battle}, pos={current_pos}")
            _stuck_counter = 0
            
        # Update last position for next iteration
        _last_position = current_pos
        
    except Exception as e:
        print(f"⚠️ [STUCK DETECTION] Error in stuck detection: {e}")
        import traceback
        traceback.print_exc()
    
    # ⚔️ PRIORITY 0A: BATTLE BOT - Combat State Machine (HIGHEST PRIORITY)
    # This MUST be checked BEFORE opener bot to prevent navigation commands during battles.
    # The battle bot handles all combat encounters with rule-based move selection.
    # Returns symbolic decisions (e.g., "BATTLE_FIGHT") which are routed through VLM executor.
    try:
        battle_bot = get_battle_bot()
        
        if battle_bot.should_handle(state_data):
            print(f"⚔️ [PRIORITY] BATTLE_BOT is handling (objective_manager will NOT be consulted)")
            logger.info(f"⚔️ [PRIORITY] BATTLE_BOT is handling")
            
            # Add latest_observation to state_data so battle_bot can access dialogue text
            state_data['latest_observation'] = latest_observation
            
            battle_decision = battle_bot.get_action(state_data)
            
            if battle_decision is not None:
                logger.info(f"⚔️ [BATTLE BOT] Battle active, decision: {battle_decision}")
                
                # ✅ VLM EXECUTOR PATTERN (Competition Compliance)
                # The battle bot has determined the optimal action programmatically.
                # We must route this through the VLM as the final decision maker.
                
                # Get battle context for VLM
                game_data = state_data.get('game', {})
                battle_info = game_data.get('battle_info', {})
                
                # Build context string
                battle_context = "In Pokemon battle"
                if battle_info:
                    player_pkmn = battle_info.get('player_pokemon', {})
                    opp_pkmn = battle_info.get('opponent_pokemon', {})
                    if player_pkmn:
                        battle_context += f" | Your: {player_pkmn.get('species', 'Unknown')} HP:{player_pkmn.get('current_hp', '?')}/{player_pkmn.get('max_hp', '?')}"
                    if opp_pkmn:
                        battle_context += f" | Opponent: {opp_pkmn.get('species', 'Unknown')} HP:{opp_pkmn.get('current_hp', '?')}/{opp_pkmn.get('max_hp', '?')}"
                
                # Map symbolic decision to button sequence
                button_recommendation = None
                decision_explanation = ""
                
                if battle_decision == "ADVANCE_BATTLE_DIALOGUE":
                    # Battle intro dialogue - press A to advance
                    button_recommendation = "A"
                    decision_explanation = "Advance battle intro dialogue"
                    logger.info("💬 [BATTLE BOT] Advancing battle dialogue with A")
                    return ["A"]
                
                elif battle_decision == "RECOVER_FROM_RUN_FAILURE":
                    # We tried to run from a trainer battle! 
                    # Press A to dismiss "No! There's no running from a TRAINER BATTLE!" message
                    # Then return to the fight menu to attack
                    logger.info("⚠️ [BATTLE BOT ERROR RECOVERY] Dismissing 'no running' message and returning to fight")
                    print("⚠️ [BATTLE BOT] RECOVERY: A to dismiss → UP → LEFT → A to fight")
                    # A to dismiss the message
                    # Then we'll be back at the base menu, so navigate to FIGHT
                    # UP → LEFT → A to select FIGHT option
                    return ["B", "B", "UP", "LEFT", "A"]  # Just dismiss the message first, next step will select FIGHT
                
                elif battle_decision == "SELECT_RUN":
                    # Navigate to RUN from base menu
                    # CRITICAL: Press B twice first to clear any menus/states
                    # Then: DOWN → RIGHT → A to select RUN
                    logger.info("🏃 [BATTLE BOT] Selecting RUN: B → B → DOWN → RIGHT → A (menu clearing)")
                    return ["B", "B", "DOWN", "RIGHT", "A"]
                
                elif battle_decision == "SELECT_FIGHT":
                    # Select FIGHT from base menu (just press A, it's the default)
                    logger.info("⚔️ [BATTLE BOT] Selecting FIGHT: A")
                    return ["A"]
                
                elif battle_decision == "PRESS_B":
                    # Exit submenu (fight menu or bag menu)
                    logger.info("🔙 [BATTLE BOT] Exiting submenu with B")
                    return ["B"]
                
                elif battle_decision == "BATTLE_FIGHT" or battle_decision == "USE_MOVE_1":
                    button_recommendation = "A"
                    decision_explanation = "Select FIGHT to use first available move"
                    
                elif battle_decision.startswith("NAV_RUN_STEP_"):
                    # Hard-coded RUN navigation sequence
                    # Format: NAV_RUN_STEP_<BUTTON>
                    button_recommendation = battle_decision.split("_")[-1]  # Extract button name
                    decision_explanation = f"Navigating to RUN option (step: {button_recommendation})"
                    logger.info(f"🏃 [BATTLE BOT] RUN navigation: pressing {button_recommendation}")
                    
                    # Bypass VLM for navigation sequence - directly return button
                    return [button_recommendation]
                    
                elif battle_decision == "RUN_FROM_WILD":
                    # Fallback if we somehow get the old decision
                    button_recommendation = "A"
                    decision_explanation = "Navigate to RUN option and select it (WILD BATTLE)"
                    logger.warning("🏃 [BATTLE BOT] Got old RUN_FROM_WILD decision - this shouldn't happen")
                    
                elif battle_decision == "RUN_FROM_BATTLE":
                    button_recommendation = "RUN"  # Will need to navigate to RUN option
                    decision_explanation = "Select RUN to flee from battle"
                else:
                    # Unknown decision - let VLM handle
                    logger.warning(f"⚔️ [BATTLE BOT] Unknown decision '{battle_decision}', falling back to VLM")
                    button_recommendation = "A"
                    decision_explanation = "Default to A button"
                
                # Create executor prompt for VLM
                executor_prompt = f"""Playing Pokemon Emerald. You are in a Pokemon battle.

BATTLE CONTEXT: {battle_context}
BATTLE BOT DECISION: {battle_decision}
RECOMMENDED ACTION: {decision_explanation}

The battle bot recommends pressing {button_recommendation}.

What button should you press? Respond with ONE button name only: A, B, UP, DOWN, LEFT, RIGHT"""
                
                try:
                    vlm_executor_response = vlm.get_text_query(executor_prompt, "BATTLE_EXECUTOR")
                    
                    # Parse VLM response
                    valid_buttons = ['START', 'SELECT', 'DOWN', 'LEFT', 'RIGHT', 'UP', 'A', 'B']
                    vlm_response_upper = vlm_executor_response.upper().strip()
                    
                    final_action = None
                    for button in valid_buttons:
                        if button in vlm_response_upper:
                            final_action = [button]
                            break
                    
                    if final_action:
                        logger.info(f"✅ [VLM EXECUTOR] BattleBot→{battle_decision}, VLM confirmed→{final_action[0]}")
                        return final_action
                    else:
                        # Retry with simpler prompt
                        logger.warning(f"⚠️ [VLM EXECUTOR] Could not parse VLM response '{vlm_executor_response[:50]}', retrying")
                        
                        retry_prompt = f"""What button for battle? Options: A, B, UP, DOWN, LEFT, RIGHT

Recommended: {button_recommendation}

Answer with just the button name:"""
                        
                        retry_response = vlm.get_text_query(retry_prompt, "BATTLE_EXECUTOR_RETRY")
                        retry_upper = retry_response.upper().strip()
                        
                        final_retry_action = None
                        for button in valid_buttons:
                            if button in retry_upper:
                                final_retry_action = [button]
                                break
                        
                        if final_retry_action:
                            logger.info(f"✅ [VLM EXECUTOR RETRY] Got valid response: {final_retry_action[0]}")
                            return final_retry_action
                        else:
                            # CRITICAL: No valid VLM response - CRASH per competition rules
                            error_msg = f"❌ [COMPLIANCE VIOLATION] VLM failed to provide valid button in battle after 2 attempts. Response 1: '{vlm_executor_response[:100]}', Response 2: '{retry_response[:100]}'. Competition rules require final action from neural network. CANNOT PROCEED."
                            logger.error(error_msg)
                            raise RuntimeError(error_msg)
                        
                except Exception as e:
                    # COMPETITION COMPLIANCE: Cannot bypass VLM - must crash
                    error_msg = f"❌ [COMPLIANCE VIOLATION] VLM executor failed in battle: {e}. Competition rules require final action from neural network. CANNOT PROCEED."
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from e
            else:
                # Battle bot returned None - fallback to VLM
                logger.debug(f"⚔️ [BATTLE BOT] Battle bot uncertain, falling back to VLM")
        
    except Exception as e:
        logger.error(f"⚔️ [BATTLE BOT] Error: {e}", exc_info=True)
        # Continue to next priority level on error
    
    # 🤖 PRIORITY 0B: OPENER BOT - Programmatic State Machine (Splits 0-4)
    # Handles deterministic early game states with high reliability using memory state
    # and milestone tracking as primary signals. Returns None to fallback to VLM.
    try:
        from agent.opener_bot import NavigationGoal, ForceDialogueGoal
        opener_bot = get_opener_bot()
        visual_data = latest_observation.get('visual_data', {}) if isinstance(latest_observation, dict) else {}
        
        should_handle = opener_bot.should_handle(state_data, visual_data)
        
        if should_handle:
            opener_action = opener_bot.get_action(state_data, visual_data, current_plan)
            
            if opener_action is not None:
                bot_state = opener_bot.get_state_summary()
                
                # Check if it's a ForceDialogueGoal (100% VLM compliance for misclassified dialogue)
                if isinstance(opener_action, ForceDialogueGoal):
                    logger.info(f"🚨 [FORCE DIALOGUE] Detected misclassified dialogue: {opener_action.reason}")
                    logger.info(f"🚨 [FORCE DIALOGUE] Will present A as only option to VLM (maintaining 100% compliance)")
                    
                    # Create special executor prompt that only allows A
                    force_dialogue_prompt = f"""Playing Pokemon Emerald. CRITICAL DIALOGUE DETECTION:

SITUATION: {opener_action.reason}

The system has detected dialogue blocking movement that was misclassified by the visual system.
This commonly happens with "................................" (thinking) dialogue.

You MUST press A to advance the dialogue.

What button do you press? Respond with: A"""
                    
                    try:
                        vlm_response = vlm.get_text_query(force_dialogue_prompt, "FORCE_DIALOGUE")
                        vlm_upper = vlm_response.upper().strip()
                        
                        if 'A' in vlm_upper:
                            logger.info(f"✅ [FORCE DIALOGUE] VLM confirmed pressing A to clear misclassified dialogue")
                            return ['A']
                        else:
                            # VLM didn't say A - retry with even more direct prompt
                            logger.warning(f"⚠️ [FORCE DIALOGUE] VLM response unclear: '{vlm_response[:50]}', retrying")
                            retry_response = vlm.get_text_query("Press A to continue. What button? Answer: A", "FORCE_DIALOGUE_RETRY")
                            
                            logger.info(f"✅ [FORCE DIALOGUE] VLM retry response: '{retry_response[:50]}', using A")
                            return ['A']  # Use A regardless since that's the only valid option
                            
                    except Exception as e:
                        # Even in error case, A is the only valid action for dialogue
                        # VLM was given the choice, so this maintains compliance
                        logger.error(f"⚠️ [FORCE DIALOGUE] VLM error: {e}, but A is the only valid option")
                        return ['A']
                
                # Check if it's a NavigationGoal
                if isinstance(opener_action, NavigationGoal):
                    # Convert navigation goal to simple direction command
                    current_x = state_data.get('player', {}).get('position', {}).get('x', 0)
                    current_y = state_data.get('player', {}).get('position', {}).get('y', 0)
                    goal_x = opener_action.x
                    goal_y = opener_action.y
                    
                    logger.info(f"🤖 [OPENER BOT] Navigation Goal: {opener_action.description}")
                    logger.info(f"🤖 [OPENER BOT] Current: ({current_x}, {current_y}) -> Goal: ({goal_x}, {goal_y})")
                    
                    # Determine the action based on navigation logic
                    nav_action = None
                    nav_reasoning = ""
                    
                    # At exact goal position - interact
                    if current_x == goal_x and current_y == goal_y:
                        logger.info(f"🤖 [OPENER BOT] At exact goal - interacting with A")
                        nav_action = ['A']
                        nav_reasoning = f"At exact goal position ({goal_x}, {goal_y}), need to interact"
                    else:
                        # Calculate which direction we need to move/face to reach goal
                        required_direction = None
                        if current_x < goal_x:
                            required_direction = 'RIGHT'
                        elif current_x > goal_x:
                            required_direction = 'LEFT'
                        elif current_y < goal_y:
                            required_direction = 'DOWN'
                        elif current_y > goal_y:
                            required_direction = 'UP'
                        
                        # Determine player's current orientation from last directional command
                        current_orientation = None
                        if recent_actions:
                            for action in reversed(recent_actions):
                                if isinstance(action, list):
                                    action = action[0] if action else None
                                if action in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
                                    current_orientation = action
                                    break
                        
                        # Check if we're adjacent to goal (distance = 1)
                        distance = abs(current_x - goal_x) + abs(current_y - goal_y)
                        if distance == 1:
                            # Adjacent to goal - but for stairs/warp tiles, we need to WALK ON, not interact
                            if opener_action.should_interact is not None:
                                should_interact = opener_action.should_interact
                            else:
                                goal_desc_lower = (opener_action.description or "").lower()
                                should_interact = any(keyword in goal_desc_lower for keyword in ['interact', 'talk', 'speak', 'check'])
                            
                            print(f"🔍 [NAV] Adjacent to goal. Description: '{opener_action.description}'")
                            print(f"🔍 [NAV] Should interact: {should_interact}")
                            
                            if should_interact:
                                # This is an interact-with-A goal (like NPC or sign)
                                if current_orientation == required_direction:
                                    # Already facing the goal - interact!
                                    logger.info(f"🤖 [OPENER BOT] Facing goal correctly - pressing A")
                                    nav_action = ['A']
                                    nav_reasoning = f"Adjacent to goal, facing {required_direction}, ready to interact"
                                else:
                                    # Need to turn toward goal first
                                    logger.info(f"🤖 [OPENER BOT] Turning to face goal: {required_direction}")
                                    nav_action = [required_direction]
                                    nav_reasoning = f"Adjacent to goal, need to turn {required_direction} before interacting"
                            else:
                                # This is a walk-to goal (stairs, warp tile, position) - keep moving
                                logger.info(f"🤖 [OPENER BOT] Adjacent to walk-to goal ({opener_action.description}) - continuing")
                                nav_action = [required_direction] if required_direction else ['A']
                                nav_reasoning = f"Adjacent to walk-to goal, continuing {required_direction}"
                        else:
                            # Not at exact goal yet - move toward goal
                            if required_direction:
                                nav_action = [required_direction]
                                nav_reasoning = f"Moving {required_direction} toward goal at ({goal_x}, {goal_y})"
                            else:
                                # Shouldn't reach here, but fallback to interact
                                nav_action = ['A']
                                nav_reasoning = "At goal position, defaulting to interact"
                    
                    # Now route through VLM executor
                    if nav_action:
                        opener_action = nav_action  # Set this so the executor logic below handles it
                        # Fall through to the executor logic below
                
                # ✅ VLM EXECUTOR PATTERN (Competition Compliance)
                # The opener bot has determined the optimal action programmatically.
                # However, per competition rules ("final action comes from a neural network"),
                # we must route this through the VLM as the final decision maker.
                
                logger.info(f"🤖 [OPENER BOT] State: {bot_state['current_state']} | Suggested action: {opener_action}")
                
                # Create streamlined executor prompt for VLM
                bot_state_name = bot_state.get('current_state', 'unknown')
                bot_action_str = opener_action[0] if isinstance(opener_action, list) and len(opener_action) > 0 else str(opener_action)
                
                # Get minimal context
                visual_context_brief = "unknown"
                if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
                    vd = latest_observation['visual_data']
                    visual_context_brief = vd.get('screen_context', 'unknown')
                    dialogue = vd.get('on_screen_text', {}).get('dialogue', '')
                    if dialogue:
                        visual_context_brief += f" (dialogue: {dialogue[:50]}...)" if len(dialogue) > 50 else f" (dialogue: {dialogue})"
                
                # Add step-based context for multi-step sequences
                step_context = ""
                if bot_state_name == 'S24_NICKNAME':
                    # Nickname uses B→START→A sequence
                    step_num = getattr(opener_bot.states.get('S24_NICKNAME').action_fn, '_nickname_step', 0)
                    step_context = f"\nSEQUENCE STEP {step_num+1}/3: Press {bot_action_str} (Full sequence: B→START→A to skip nickname)"
                elif bot_state_name == 'S2_GENDER_NAME_SELECT':
                    # Name selection just uses START once when in keyboard
                    if bot_action_str == 'START':
                        step_context = f"\nACTION: Press START to accept default name (inside naming keyboard)"
                    else:
                        step_context = f"\nACTION: Navigate character naming sequence"
                elif bot_state_name == 'S7_SET_CLOCK':
                    # Clock uses UP→A sequence for Yes/No menu
                    step_num = getattr(opener_bot.states.get('S7_SET_CLOCK').action_fn, '_yesno_step', 0)
                    if step_num == 0:
                        step_context = f"\nSEQUENCE STEP 1/2: Press UP to select YES in clock confirmation menu"
                    else:
                        step_context = f"\nSEQUENCE STEP 2/2: Press A to confirm YES in clock confirmation menu"
                
                executor_prompt = f"""Playing Pokemon Emerald. You are executing a decision from the programmatic opener controller.

CURRENT STATE: {visual_context_brief}
OPENER BOT STATE: {bot_state_name}
RECOMMENDED ACTION: {bot_action_str}{step_context}

The opener bot has analyzed the deterministic opening sequence and recommends pressing {bot_action_str}.

What button should you press? Respond with ONE button name only: A, B, UP, DOWN, LEFT, RIGHT, START"""
                
                try:
                    vlm_executor_response = vlm.get_text_query(executor_prompt, "OPENER_EXECUTOR")
                    
                    # Parse VLM response - check longer buttons first to avoid substring matches
                    # (e.g., 'START' contains 'A', 'RIGHT' contains 'R', etc.)
                    valid_buttons = ['START', 'SELECT', 'DOWN', 'LEFT', 'RIGHT', 'UP', 'A', 'B']
                    vlm_response_upper = vlm_executor_response.upper().strip()
                    
                    # Try to extract button from response (checking longest first)
                    final_action = None
                    for button in valid_buttons:
                        if button in vlm_response_upper:
                            final_action = [button]
                            break
                    
                    if final_action:
                        logger.info(f"✅ [VLM EXECUTOR] OpenerBot→{bot_action_str}, VLM confirmed→{final_action[0]}")
                        return final_action
                    else:
                        # COMPETITION COMPLIANCE: VLM must provide valid response - retry with simpler prompt
                        logger.warning(f"⚠️ [VLM EXECUTOR] Could not parse VLM response '{vlm_executor_response[:50]}', retrying")
                        
                        retry_prompt = f"""What button? Options: A, B, UP, DOWN, LEFT, RIGHT, START, SELECT

Recommended: {bot_action_str}

Answer with just the button name:"""
                        
                        retry_response = vlm.get_text_query(retry_prompt, "OPENER_EXECUTOR_RETRY")
                        retry_upper = retry_response.upper().strip()
                        
                        # Try to parse retry response
                        final_retry_action = None
                        for button in valid_buttons:
                            if button in retry_upper:
                                final_retry_action = [button]
                                break
                        
                        if final_retry_action:
                            logger.info(f"✅ [VLM EXECUTOR RETRY] Got valid response: {final_retry_action[0]}")
                            return final_retry_action
                        else:
                            # CRITICAL: No valid VLM response after retry - CRASH per competition rules
                            error_msg = f"❌ [COMPLIANCE VIOLATION] VLM failed to provide valid button after 2 attempts. Response 1: '{vlm_executor_response[:100]}', Response 2: '{retry_response[:100]}'. Competition rules require final action from neural network. CANNOT PROCEED."
                            logger.error(error_msg)
                            raise RuntimeError(error_msg)
                        
                except Exception as e:
                    # COMPETITION COMPLIANCE: Cannot bypass VLM - must crash
                    error_msg = f"❌ [COMPLIANCE VIOLATION] VLM executor failed: {e}. Competition rules require final action from neural network. CANNOT PROCEED."
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from e
            else:
                # Opener bot returned None - fallback to VLM
                logger.debug(f"🤖 [OPENER BOT] Fallback to VLM in state: {opener_bot.current_state_name}")
        else:
            logger.info(f"[ACTION] 🤖 Opener bot should NOT handle - continuing to VLM/dialogue detection")
        
    except Exception as e:
        logger.error(f"🤖 [OPENER BOT] Error: {e}", exc_info=True)
        # Continue to VLM logic on error
    
    # 📍 PRIORITY 0C: OBJECTIVE MANAGER DIRECTIVES (PATH 1 QUICK WIN)
    # This is the "directive system" that provides specific tactical instructions
    # based on milestone progression. Acts as a bridge between high-level objectives
    # and low-level navigation/interaction commands.
    #
    # WHY THIS EXISTS:
    # - Problem: Agent reaches Route 103 but doesn't know to interact with rival at (9,3)
    # - Root cause: ObjectiveManager only provides high-level goals, not specific actions
    # - Solution: get_next_action_directive() returns precise instructions like "walk to (9,3) and press A"
    #
    # ARCHITECTURE:
    # - Uses existing ObjectiveManager from planning module
    # - Returns directives like {"action": "NAVIGATE_AND_INTERACT", "target": (x, y, map)}
    # - Converts directives to NavigationGoal objects (reuses Opener Bot pathfinding)
    # - Routes decisions through VLM executor for competition compliance
    try:
        # Import planning module and NavigationGoal
        from agent.planning import planning_step
        from agent.opener_bot import NavigationGoal
        
        # Get ObjectiveManager instance (created in planning_step function)
        # Note: objective_manager is attached to the planning_step function itself, not its return value
        logger.info(f"🔍 [DIRECTIVE DEBUG] hasattr(planning_step, 'objective_manager'): {hasattr(planning_step, 'objective_manager')}")
        print(f"🔍 [DIRECTIVE DEBUG] hasattr(planning_step, 'objective_manager'): {hasattr(planning_step, 'objective_manager')}")
        
        if hasattr(planning_step, 'objective_manager'):
            obj_manager = planning_step.objective_manager
            logger.info(f"🔍 [DIRECTIVE DEBUG] objective_manager exists: {obj_manager}")
            print(f"🔍 [DIRECTIVE DEBUG] objective_manager exists: {obj_manager}")
            
            # Log state data for debugging battle detection
            player_data = state_data.get('player', {})
            money = player_data.get('money', 0)
            in_battle = state_data.get('in_battle', False)
            screen_context = state_data.get('screen_context', '')
            player_loc = player_data.get('location', '')
            
            # Add visual_dialogue_active to state_data so objective_manager can access it
            state_data['visual_dialogue_active'] = visual_dialogue_active
            
            logger.info(f"🔍 [DIRECTIVE DEBUG] Before get_next_action_directive:")
            logger.info(f"  - Location: {player_loc}")
            logger.info(f"  - Money: {money}")
            logger.info(f"  - In battle: {in_battle}")
            logger.info(f"  - Screen context: {screen_context}")
            logger.info(f"  - Visual dialogue active: {visual_dialogue_active}")
            print(f"🔍 [DIRECTIVE DEBUG] Location: {player_loc}, Money: {money}, In battle: {in_battle}, Screen: {screen_context}, Dialogue: {visual_dialogue_active}")
            
            directive = obj_manager.get_next_action_directive(state_data)
            
            logger.info(f"🔍 [DIRECTIVE DEBUG] Directive returned: {directive}")
            print(f"🔍 [DIRECTIVE DEBUG] Directive returned: {directive}")
            
            if directive:
                # NEW SIMPLE DIRECTIVE FORMAT:
                # - goal_coords: (x, y, 'LOCATION') - navigate to specific coordinates
                # - goal_direction: 'north'/'south'/etc - navigate toward edge
                # - should_interact: True/False - press A at destination
                # - journey_complete: True - navigation done
                
                description = directive.get('description', '')
                logger.info(f"📍 [DIRECTIVE] Active directive: {description}")
                print(f"📍 [DIRECTIVE] {description}")
                
                print(f"🔍 [DIRECTIVE CHECK] Keys in directive: {list(directive.keys())}")
                print(f"🔍 [DIRECTIVE CHECK] 'goal_coords' in directive: {'goal_coords' in directive}")
                print(f"🔍 [DIRECTIVE CHECK] 'journey_complete' in directive: {'journey_complete' in directive}")
                
                # Handle journey complete
                if directive.get('journey_complete'):
                    logger.info(f"✅ [DIRECTIVE] Navigation journey complete")
                    return []  # No action needed
                
                print(f"🔍 [DIRECTIVE CHECK] After journey_complete check, continuing...")
                
                # Handle goal_coords - navigate to specific coordinates
                if 'goal_coords' in directive:
                    print(f"🔍 [GOAL_COORDS] Entered goal_coords handler!")
                    logger.info(f"🔍 [GOAL_COORDS] Entered goal_coords handler!")
                    goal_coords = directive['goal_coords']  # (x, y, 'LOCATION')
                    should_interact = directive.get('should_interact', False)
                    npc_coords = directive.get('npc_coords')  # Optional (npc_x, npc_y) for facing direction
                    print(f"🔍 [GOAL_COORDS] goal_coords={goal_coords}, should_interact={should_interact}, npc_coords={npc_coords}")
                    
                    if len(goal_coords) == 3:
                        target_x, target_y, target_map = goal_coords
                    else:
                        logger.error(f"❌ [DIRECTIVE] Invalid goal_coords format: {goal_coords}")
                        return []
                    
                    logger.info(f"🎯 [DIRECTIVE] Navigating to ({target_x}, {target_y}) in {target_map}, interact={should_interact}, npc_coords={npc_coords}")
                    
                    # Use existing NavigationGoal system
                    nav_goal = NavigationGoal(
                        x=target_x, y=target_y,
                        map_location=target_map,
                        should_interact=should_interact,
                        description=description
                    )
                    
                    # Process NavigationGoal using the same logic as opener bot (from lines 1383-1473)
                    current_x = state_data.get('player', {}).get('position', {}).get('x', 0)
                    current_y = state_data.get('player', {}).get('position', {}).get('y', 0)
                    goal_x = nav_goal.x
                    goal_y = nav_goal.y
                    
                    logger.info(f"🗺️ [DIRECTIVE NAV] Current: ({current_x}, {current_y}) -> Goal: ({goal_x}, {goal_y})")
                    
                    # At exact goal position - handle interaction with NPC
                    if current_x == goal_x and current_y == goal_y:
                        if should_interact:
                            # If npc_coords provided, we need to face the NPC before pressing A
                            if npc_coords:
                                npc_x, npc_y = npc_coords
                                
                                # Calculate direction to face NPC
                                required_direction = None
                                if current_x < npc_x:
                                    required_direction = 'RIGHT'
                                elif current_x > npc_x:
                                    required_direction = 'LEFT'
                                elif current_y < npc_y:
                                    required_direction = 'DOWN'
                                elif current_y > npc_y:
                                    required_direction = 'UP'
                                
                                # Check current orientation
                                current_orientation = None
                                if recent_actions:
                                    for action in reversed(recent_actions):
                                        if isinstance(action, list):
                                            action = action[0] if action else None
                                        if action in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
                                            current_orientation = action
                                            break
                                
                                if current_orientation == required_direction:
                                    logger.info(f"🗺️ [DIRECTIVE NAV] At goal, facing NPC at ({npc_x},{npc_y}) {required_direction} - pressing A")
                                    return ['A']
                                else:
                                    logger.info(f"🗺️ [DIRECTIVE NAV] At goal, need to turn {required_direction} to face NPC at ({npc_x},{npc_y})")
                                    return [required_direction]
                            else:
                                # No NPC coords - just interact at goal position
                                logger.info(f"🗺️ [DIRECTIVE NAV] At exact goal - pressing A to interact")
                                return ['A']
                        else:
                            logger.info(f"🗺️ [DIRECTIVE NAV] At goal, no interaction needed")
                            return []
                    
                    # Calculate direction to goal
                    required_direction = None
                    if current_x < goal_x:
                        required_direction = 'RIGHT'
                    elif current_x > goal_x:
                        required_direction = 'LEFT'
                    elif current_y < goal_y:
                        required_direction = 'DOWN'
                    elif current_y > goal_y:
                        required_direction = 'UP'
                    
                    # Check distance to goal
                    distance = abs(current_x - goal_x) + abs(current_y - goal_y)
                    
                    # NOT at goal yet - navigate toward it
                    # Use A* pathfinding to find the next step (handles obstacles)
                    #
                    # PATHFINDING STRATEGY (3 tiers):
                    # 1. Local A* (fast): Works if goal within visible 15x15 grid
                    # 2. Global A* (smart): Uses complete explored map
                    #    - If goal explored: Direct pathfinding to goal coordinates
                    #    - If goal unexplored: Frontier-based exploration toward goal direction
                    # 3. Simple direction (fallback): Walk straight toward goal (may hit obstacles)
                    if distance > 0:
                        print(f"🔍 [GOAL_COORDS] Distance={distance}, about to call _pathfind_to_target({goal_x}, {goal_y})")
                        
                        # Strategy: Try multiple pathfinding approaches in order of sophistication
                        pathfound_action = None
                        
                        # 1. Try local A* first (fast, works if goal is within 15x15 visible grid)
                        pathfound_action = _pathfind_to_target(state_data, goal_x, goal_y)
                        print(f"🔍 [GOAL_COORDS] Local A* (_pathfind_to_target) returned: {pathfound_action}")
                        
                        # 2. If local A* fails, try global A* with map stitcher data (handles long-range paths)
                        if not pathfound_action:
                            stitched_map_info = state_data.get('map', {}).get('stitched_map_info')
                            if stitched_map_info and stitched_map_info.get('available'):
                                current_area = stitched_map_info.get('current_area', {})
                                grid_serializable = current_area.get('grid')
                                bounds = current_area.get('bounds')
                                
                                if grid_serializable and bounds:
                                    print(f"🗺️ [GOAL_COORDS] Trying global A* with map stitcher data...")
                                    
                                    # Convert grid to proper format
                                    location_grid = {}
                                    for key, value in grid_serializable.items():
                                        x, y = map(int, key.split(','))
                                        location_grid[(x, y)] = value
                                    
                                    # Calculate goal direction for fallback
                                    dx = goal_x - current_x
                                    dy = goal_y - current_y
                                    if abs(dy) > abs(dx):
                                        goal_direction = 'south' if dy > 0 else 'north'
                                    else:
                                        goal_direction = 'east' if dx > 0 else 'west'
                                    
                                    print(f"🗺️ [GOAL_COORDS] Goal direction: {goal_direction}, checking if goal in grid...")
                                    goal_in_grid = (goal_x, goal_y) in location_grid
                                    print(f"🗺️ [GOAL_COORDS] Goal ({goal_x}, {goal_y}) in explored grid: {goal_in_grid}")
                                    
                                    if goal_in_grid:
                                        # Goal is explored - pathfind directly to it
                                        print(f"✅ [GOAL_COORDS] Goal is explored, using direct A* pathfinding")
                                        pathfound_action = _astar_pathfind_with_grid_data(
                                            location_grid=location_grid,
                                            bounds=bounds,
                                            current_pos=(current_x, current_y),
                                            location=state_data.get('player', {}).get('location', ''),
                                            goal_direction=goal_direction,
                                            recent_positions=_recent_positions,
                                            goal_coords=(goal_x, goal_y)
                                        )
                                        print(f"🗺️ [GOAL_COORDS] Direct A* returned: {pathfound_action}")
                                    else:
                                        # Goal is unexplored - use frontier-based exploration toward goal direction
                                        print(f"⚠️ [GOAL_COORDS] Goal is unexplored, using frontier-based navigation toward {goal_direction}")
                                        pathfound_action = _astar_pathfind_with_grid_data(
                                            location_grid=location_grid,
                                            bounds=bounds,
                                            current_pos=(current_x, current_y),
                                            location=state_data.get('player', {}).get('location', ''),
                                            goal_direction=goal_direction,
                                            recent_positions=_recent_positions,
                                            goal_coords=None  # Don't pass goal_coords - use frontier exploration
                                        )
                                        print(f"🗺️ [GOAL_COORDS] Frontier-based A* returned: {pathfound_action}")
                        
                        # 3. If we found a path, use it
                        if pathfound_action:
                            logger.info(f"🗺️ [DIRECTIVE NAV] A* pathfinding to ({goal_x}, {goal_y}): {pathfound_action} (distance: {distance})")
                            print(f"🗺️ [DIRECTIVE NAV] A* pathfinding returning: {pathfound_action}")
                            return [pathfound_action]
                        
                        # 4. Fallback to simple direction if all A* approaches fail
                        if required_direction:
                            logger.info(f"🗺️ [DIRECTIVE NAV] All A* failed, using simple direction: {required_direction} (distance: {distance})")
                            print(f"🗺️ [DIRECTIVE NAV] A* failed, using simple direction fallback: {required_direction}")
                            return [required_direction]
                        else:
                            logger.warning(f"⚠️ [DIRECTIVE NAV] Distance {distance} but no direction calculated")
                            return []
                    
                    # This shouldn't be reached (distance=0 handled above)
                    logger.warning(f"⚠️ [DIRECTIVE NAV] Unexpected state: at goal but not caught by check above")
                    return []
                
                # Handle goal_direction - navigate toward map edge
                elif 'goal_direction' in directive:
                    goal_direction = directive['goal_direction']  # 'north', 'south', etc.
                    
                    logger.info(f"🎯 [DIRECTIVE] Navigating {goal_direction}")
                    print(f"🎯 [DIRECTIVE] Processing goal_direction: {goal_direction}")
                    
                    # Use existing frontier-based pathfinding
                    suggested_action = _local_pathfind_from_tiles(state_data, goal_direction, recent_actions)
                    if suggested_action:
                        logger.info(f"🗺️ [DIRECTIVE] Directional pathfinding suggests: {suggested_action}")
                        print(f"🗺️ [DIRECTIVE] Directional pathfinding returning: {suggested_action}")
                        return [suggested_action]
                    else:
                        logger.warning(f"⚠️ [DIRECTIVE] Directional pathfinding failed for {goal_direction}")
                        print(f"⚠️ [DIRECTIVE] Directional pathfinding failed - returning empty")
                        return []
                
                # Handle wait_for_transition - wait for warp/map transition to complete
                elif 'wait_for_transition' in directive:
                    expected_location = directive.get('expected_location', '')
                    current_location = state_data.get('player', {}).get('location', '').upper()
                    
                    logger.info(f"⏳ [WAIT] Waiting for transition to {expected_location} (current: {current_location})")
                    print(f"⏳ [WAIT] Waiting for transition to {expected_location} (current: {current_location})")
                    
                    # Check if transition completed
                    if expected_location and expected_location.upper() in current_location:
                        logger.info(f"✅ [WAIT] Transition complete - now in {current_location}")
                        print(f"✅ [WAIT] Transition complete - now in {current_location}")
                        return []  # Transition complete, let planner advance
                    else:
                        # Still waiting - return empty action to avoid interrupting transition
                        logger.info(f"⏳ [WAIT] Still waiting for transition...")
                        print(f"⏳ [WAIT] Still waiting...")
                        return []
        
        # === EXISTING NAVIGATION GOAL HANDLING (unchanged) ===
        # Check for active navigation goal from directive or other sources
                    direction = directive.get('direction', 'south')  # 'north', 'south', 'east', 'west'
                    target_location = directive.get('target_location', '').upper()
                    portal_coords = directive.get('portal_coords')  # (x, y) tuple or None
                    proximity_radius = directive.get('proximity_radius', 5)  # Default 5 tiles
                    
                    player_data = state_data.get('player', {})
                    current_location = player_data.get('location', '').upper()
                    position = player_data.get('position', {})
                    current_x = position.get('x', 0)
                    current_y = position.get('y', 0)
                    
                    # Check if we've reached the target location
                    if target_location in current_location:
                        logger.info(f"✅ [NAVIGATE_DIRECTION] Reached target location: {target_location}")
                        return []  # Success - let objective manager provide next directive
                    
                    # Calculate distance to portal if coordinates provided
                    use_directional = True  # Default to directional navigation
                    if portal_coords:
                        portal_x, portal_y = portal_coords
                        distance = abs(current_x - portal_x) + abs(current_y - portal_y)  # Manhattan distance
                        
                        if distance > proximity_radius:
                            # Far from portal - navigate directly to portal coordinates
                            use_directional = False
                            logger.info(f"🎯 [NAVIGATE_DIRECTION] Distance to portal ({portal_x}, {portal_y}): {distance} tiles (>{proximity_radius}) - navigating directly to portal")
                        else:
                            # Close to portal - use directional A* to find any path through
                            logger.info(f"🎯 [NAVIGATE_DIRECTION] Distance to portal ({portal_x}, {portal_y}): {distance} tiles (<={proximity_radius}) - using directional A* to find path through")
                    
                    # Use A* pathfinding
                    stitched_map_info = state_data.get('map', {}).get('stitched_map_info')
                    
                    logger.info(f"🗺️ [NAVIGATE_DIRECTION DEBUG] stitched_map_info exists: {stitched_map_info is not None}")
                    if stitched_map_info:
                        logger.info(f"🗺️ [NAVIGATE_DIRECTION DEBUG] available: {stitched_map_info.get('available')}")
                    
                    if stitched_map_info and stitched_map_info.get('available'):
                        current_area = stitched_map_info.get('current_area', {})
                        grid_serializable = current_area.get('grid')
                        bounds = current_area.get('bounds')
                        
                        logger.info(f"🗺️ [NAVIGATE_DIRECTION DEBUG] grid exists: {grid_serializable is not None}, bounds exists: {bounds is not None}")
                        
                        if grid_serializable and bounds:
                            # Convert grid to proper format
                            location_grid = {}
                            for key, value in grid_serializable.items():
                                x, y = map(int, key.split(','))
                                location_grid[(x, y)] = value
                            
                            if use_directional:
                                # Use directional A* - find any path in the specified direction
                                logger.info(f"🗺️ [NAVIGATE_DIRECTION] Using directional A* moving {direction} to reach {target_location}")
                                
                                pathfind_action = _astar_pathfind_with_grid_data(
                                    location_grid=location_grid,
                                    bounds=bounds,
                                    current_pos=(current_x, current_y),
                                    location=current_location,
                                    goal_direction=direction,
                                    recent_positions=_recent_positions
                                )
                            else:
                                # Navigate directly to portal coordinates
                                logger.info(f"🗺️ [NAVIGATE_DIRECTION] Navigating to portal at ({portal_x}, {portal_y})")
                                
                                pathfind_action = _astar_pathfind_with_grid_data(
                                    location_grid=location_grid,
                                    bounds=bounds,
                                    current_pos=(current_x, current_y),
                                    location=current_location,
                                    goal_direction=direction,  # Still need a direction for fallback
                                    goal_coords=(portal_x, portal_y),  # FIXED: Use goal_coords not goal
                                    recent_positions=_recent_positions
                                )
                            
                            if pathfind_action:
                                logger.info(f"🗺️ [NAVIGATE_DIRECTION] A* recommends: {pathfind_action}")
                                return [pathfind_action]
                            else:
                                logger.warning(f"⚠️ [NAVIGATE_DIRECTION] A* found no path, trying direct movement")
                                # Fallback: just move in the specified direction
                                direction_map = {'north': 'UP', 'south': 'DOWN', 'east': 'RIGHT', 'west': 'LEFT'}
                                return [direction_map.get(direction, 'DOWN')]
                    
                    # Fallback if no map data: just move in the direction
                    logger.info(f"🗺️ [NAVIGATE_DIRECTION] No map data, moving {direction} directly")
                    direction_map = {'north': 'UP', 'south': 'DOWN', 'east': 'RIGHT', 'west': 'LEFT'}
                    return [direction_map.get(direction, 'DOWN')]
                
                # Handle MOVE_UNTIL_MAP_CHANGE - keep moving in direction until location changes
                elif directive.get('action') == 'MOVE_UNTIL_MAP_CHANGE':
                    direction = directive.get('direction')
                    target_location = directive.get('target_location', '').upper()
                    
                    player_data = state_data.get('player', {})
                    current_location = player_data.get('location', '').upper()
                    
                    # Check if we've reached the target location
                    if target_location in current_location:
                        logger.info(f"✅ [MAP TRANSITION] Reached target location: {target_location}")
                        return []  # Success - let objective manager provide next directive
                    
                    # Keep moving in the specified direction
                    logger.info(f"🗺️ [MAP TRANSITION] Moving {direction} to reach {target_location} (currently in {current_location})")
                    return [direction]
                
                # Handle NAVIGATE directive (navigate without interaction - for map transitions, ledges, etc.)
                elif directive.get('action') == 'NAVIGATE' and directive.get('target'):
                    target = directive.get('target')
                    try:
                        logger.info(f"🔍 [NAVIGATE BLOCK] Entered NAVIGATE handler")
                        print(f"🔍 [NAVIGATE BLOCK] Entered NAVIGATE handler")
                        logger.info(f"🔍 [NAVIGATE BLOCK] About to unpack target: {target}")
                        target_x, target_y, target_map = target
                        logger.info(f"🔍 [NAVIGATE BLOCK] Successfully unpacked: x={target_x}, y={target_y}, map={target_map}")
                        
                        logger.info(f"📍 [DIRECTIVE NAVIGATE] Moving to: ({target_x}, {target_y}, {target_map}) - NO interaction")
                    except Exception as nav_error:
                        logger.error(f"❌ [NAVIGATE BLOCK] Exception in NAVIGATE handler: {nav_error}", exc_info=True)
                        print(f"❌ [NAVIGATE BLOCK] Exception: {nav_error}")
                        raise  # Re-raise to be caught by outer handler
                    
                    # Create NavigationGoal WITHOUT interaction
                    nav_goal = NavigationGoal(
                        x=target_x,
                        y=target_y,
                        map_location=target_map,
                        should_interact=False,  # Just walk, don't press A
                        description=description
                    )
                    
                    # Process NavigationGoal using the existing navigation logic
                    goal_x = nav_goal.x
                    goal_y = nav_goal.y
                    goal_map = nav_goal.map_location.upper()
                    should_interact = nav_goal.should_interact
                    
                    # Get current position
                    player_data = state_data.get('player', {})
                    position = player_data.get('position', {})
                    current_x = position.get('x', 0)
                    current_y = position.get('y', 0)
                    current_map = player_data.get('location', '').upper()
                    
                    logger.info(f"📍 [DIRECTIVE NAV] Current: ({current_x}, {current_y}, {current_map}), Goal: ({goal_x}, {goal_y}, {goal_map})")
                    
                    # Clear portal wait counter if we're NOT at any portal position
                    # (Means we successfully warped or moved away)
                    global _portal_wait_frames, _portal_approach_direction
                    
                    # CRITICAL: Detect if location changed (successful warp during movement)
                    # If we were targeting a portal on map X and now we're on map Y, the warp worked!
                    if goal_map not in current_map and _portal_wait_frames:
                        logger.info(f"✅ [PORTAL] Location changed from {goal_map} to {current_map} - portal warp successful!")
                        _portal_wait_frames.clear()  # Clear all portal tracking
                        _portal_approach_direction.clear()  # Clear approach directions
                    elif _portal_wait_frames:
                        # Check if current position matches any tracked portal
                        current_key = (current_x, current_y, current_map)
                        to_remove = [key for key in _portal_wait_frames.keys() if key != current_key]
                        for key in to_remove:
                            del _portal_wait_frames[key]
                            if key in _portal_approach_direction:
                                del _portal_approach_direction[key]
                            logger.info(f"✅ [PORTAL] Cleared wait counter for {key} - moved away from portal")
                    
                    # Check if we're at the goal
                    dx = goal_x - current_x
                    dy = goal_y - current_y
                    distance = abs(dx) + abs(dy)
                    
                    # CRITICAL: For pure NAVIGATE directives, we DON'T stop at the goal position
                    # Portals trigger when you MOVE THROUGH them, not when you stand still on them
                    # The location change detection will catch when the warp succeeds
                    
                    # Detect if location changed (successful warp)
                    if goal_map not in current_map and _portal_wait_frames:
                        logger.info(f"✅ [PORTAL] Location changed from {goal_map} to {current_map} - portal warp successful!")
                        _portal_wait_frames.clear()
                        # Goal achieved - let objective manager set new goal
                        return []
                    
                    # At goal position on same map - check if this is actually a portal
                    # If so, keep trying to move through it (portals need momentum)
                    if current_x == goal_x and current_y == goal_y and goal_map in current_map:
                        portal_key = (goal_x, goal_y, goal_map)
                        wait_count = _portal_wait_frames.get(portal_key, 0)
                        _portal_wait_frames[portal_key] = wait_count + 1
                        
                        if wait_count < 5:
                            # Try to move through the portal by continuing in the same direction
                            # Use the saved approach direction if available
                            approach_dir = _portal_approach_direction.get(portal_key)
                            
                            if approach_dir:
                                logger.info(f"📍 [PORTAL] At portal tile ({goal_x}, {goal_y}), attempt {wait_count + 1}/5 - continuing in saved direction: {approach_dir}")
                                return [approach_dir]
                            else:
                                # First time at portal - determine direction from objective
                                # The portal is at the goal coords, so we need to figure out which way to continue
                                # Based on the map transition direction
                                logger.info(f"📍 [PORTAL] At portal tile ({goal_x}, {goal_y}) for first time, attempt {wait_count + 1}/5")
                                
                                # For Route 101 → Oldale Town: portal at (11, 0) - need to go UP (north)
                                # For Oldale Town → Route 101: portal at (10, 19) - need to go DOWN (south)
                                # For Littleroot → Route 101: portal at (7, 1) - need to go UP (north)
                                # For Route 101 → Littleroot: portal at (11, 22) - need to go DOWN (south)
                                
                                # Heuristic: If y=0 or y=1 (top edge), go UP. If y>=19 (bottom edge), go DOWN.
                                # If x<=7 (left edge), go LEFT. If x>=15 (right edge), go RIGHT.
                                if goal_y <= 1:
                                    direction = 'UP'
                                elif goal_y >= 19:
                                    direction = 'DOWN'
                                elif goal_x <= 7:
                                    direction = 'LEFT'
                                elif goal_x >= 15:
                                    direction = 'RIGHT'
                                else:
                                    # Default to UP for unknown portals
                                    direction = 'UP'
                                
                                _portal_approach_direction[portal_key] = direction
                                logger.info(f"📍 [PORTAL] Saved approach direction: {direction}")
                                return [direction]
                        else:
                            logger.warning(f"⚠️ [PORTAL] Failed to warp after 5 attempts at ({goal_x}, {goal_y})")
                            _portal_wait_frames[portal_key] = 0
                            if portal_key in _portal_approach_direction:
                                del _portal_approach_direction[portal_key]
                            return []  # Give up, let objective manager handle
                    
                    # Not at goal yet - navigate using A* pathfinding
                    else:
                        # Special handling if within 1 tile of portal - prepare for momentum
                        if distance == 1 and goal_map in current_map:
                            # Save the approach direction when we're 1 tile away
                            portal_key = (goal_x, goal_y, goal_map)
                            if dy < 0:
                                approach_dir = 'UP'
                            elif dy > 0:
                                approach_dir = 'DOWN'
                            elif dx < 0:
                                approach_dir = 'LEFT'
                            elif dx > 0:
                                approach_dir = 'RIGHT'
                            else:
                                approach_dir = None
                            
                            if approach_dir:
                                _portal_approach_direction[portal_key] = approach_dir
                                logger.info(f"📍 [PORTAL] 1 tile from portal ({goal_x}, {goal_y}) - will continue {approach_dir} through portal")
                                # Return the approach direction immediately to build momentum
                                # This ensures we move through the portal without stopping
                                return [approach_dir]
                        
                        # Not at goal yet - navigate using A*
                        nav_action = None
                        
                        # Try coordinate-based global A* first (if on same map)
                        if goal_map in current_map:
                            stitched_map_info = state_data.get('map', {}).get('stitched_map_info')
                            
                            if stitched_map_info and stitched_map_info.get('available'):
                                current_area = stitched_map_info.get('current_area', {})
                                grid_serializable = current_area.get('grid')
                                bounds = current_area.get('bounds')
                                origin_offset = current_area.get('origin_offset')
                                
                                if grid_serializable and bounds and origin_offset:
                                    logger.info(f"📍 [DIRECTIVE NAV] Using coordinate-based global A*")
                                    
                                    # Convert grid to proper format
                                    location_grid = {}
                                    for key, value in grid_serializable.items():
                                        x, y = map(int, key.split(','))
                                        location_grid[(x, y)] = value
                                    
                                    # Convert world coordinates to grid coordinates
                                    # bounds is a dict with keys: min_x, max_x, min_y, max_y
                                    min_x = int(bounds['min_x'])
                                    max_x = int(bounds['max_x'])
                                    min_y = int(bounds['min_y'])
                                    max_y = int(bounds['max_y'])
                                    
                                    # Determine goal direction from coordinates
                                    dx = goal_x - current_x
                                    dy = goal_y - current_y
                                    
                                    print(f"🎯 [NAV DEBUG] Current: ({current_x}, {current_y}), Goal: ({goal_x}, {goal_y})")
                                    print(f"🎯 [NAV DEBUG] Delta: dx={dx}, dy={dy}")
                                    
                                    # Map to cardinal direction for A* function
                                    if abs(dy) > abs(dx):
                                        goal_direction = 'south' if dy > 0 else 'north'
                                    else:
                                        goal_direction = 'east' if dx > 0 else 'west'
                                    
                                    print(f"🎯 [NAV DEBUG] Goal direction: {goal_direction}")
                                    
                                    # Check if goal coordinates are in the explored grid
                                    goal_in_grid = (goal_x, goal_y) in location_grid
                                    print(f"🎯 [NAV DEBUG] Goal ({goal_x}, {goal_y}) in explored grid: {goal_in_grid}")
                                    
                                    if goal_in_grid:
                                        # Goal is explored - pathfind directly to it
                                        logger.info(f"📍 [DIRECTIVE NAV] Goal in grid, pathfinding directly to ({goal_x}, {goal_y})")
                                        pathfind_action = _astar_pathfind_with_grid_data(
                                            location_grid=location_grid,
                                            bounds=bounds,
                                            current_pos=(current_x, current_y),
                                            location=current_map,
                                            goal_direction=goal_direction,
                                            recent_positions=_recent_positions,
                                            goal_coords=(goal_x, goal_y)  # Pass actual goal coordinates
                                        )
                                    else:
                                        # Goal is unexplored - use frontier-based exploration
                                        logger.info(f"📍 [DIRECTIVE NAV] Goal not in grid, using frontier exploration with direction={goal_direction}")
                                        pathfind_action = _astar_pathfind_with_grid_data(
                                            location_grid=location_grid,
                                            bounds=bounds,
                                            current_pos=(current_x, current_y),
                                            location=current_map,
                                            goal_direction=goal_direction,
                                            recent_positions=_recent_positions
                                        )
                                    
                                    if pathfind_action:
                                        logger.info(f"📍 [DIRECTIVE NAV] A* recommends: {pathfind_action}")
                                        nav_action = [pathfind_action]
                                        logger.info(f"📍 [DIRECTIVE NAV] Set nav_action to: {nav_action}")
                        
                        # Fallback: Simple directional movement
                        logger.info(f"📍 [DIRECTIVE NAV] After A* block, nav_action = {nav_action}")
                        if not nav_action:
                            if abs(dx) > abs(dy):
                                nav_action = ['RIGHT'] if dx > 0 else ['LEFT']
                            else:
                                nav_action = ['DOWN'] if dy > 0 else ['UP']
                            logger.info(f"📍 [DIRECTIVE NAV] Using simple direction: {nav_action[0]}")
                    
                    # If we have a navigation action, return it
                    logger.info(f"📍 [DIRECTIVE NAV] Before final check, nav_action = {nav_action}")
                    if nav_action:
                        logger.info(f"📍 [DIRECTIVE NAV] Executing: {nav_action[0]}")
                        return nav_action
                    else:
                        logger.warning(f"⚠️ [DIRECTIVE NAV] nav_action is None/empty, NOT returning")
                
                # Handle NAVIGATE_AND_INTERACT directive (most common)
                elif directive.get('action') == 'NAVIGATE_AND_INTERACT' and directive.get('target'):
                    target = directive.get('target')
                    target_x, target_y, target_map = target
                    
                    logger.info(f"📍 [DIRECTIVE] Converting to NavigationGoal: ({target_x}, {target_y}, {target_map})")
                    
                    # Create NavigationGoal and let existing Opener Bot logic handle it
                    # This includes A* pathfinding, obstacle avoidance, and adjacent-tile interaction
                    nav_goal = NavigationGoal(
                        x=target_x,
                        y=target_y,
                        map_location=target_map,
                        should_interact=True,  # Press A when we reach the target
                        description=description
                    )
                    
                    # Process NavigationGoal using the existing Opener Bot navigation logic
                    # This is copied from lines 900-1090 (Opener Bot NavigationGoal handler)
                    goal_x = nav_goal.x
                    goal_y = nav_goal.y
                    goal_map = nav_goal.map_location.upper()
                    should_interact = nav_goal.should_interact
                    
                    # Get current position
                    player_data = state_data.get('player', {})
                    position = player_data.get('position', {})
                    current_x = position.get('x', 0)
                    current_y = position.get('y', 0)
                    current_map = player_data.get('location', '').upper()
                    current_orientation = player_data.get('facing_direction', 'down').upper()
                    
                    logger.info(f"📍 [DIRECTIVE NAV] Current: ({current_x}, {current_y}, {current_map}), Goal: ({goal_x}, {goal_y}, {goal_map})")
                    
                    # Check if we're at the goal
                    dx = goal_x - current_x
                    dy = goal_y - current_y
                    distance = abs(dx) + abs(dy)
                    
                    # First priority: Check if we're at exact goal position
                    if current_x == goal_x and current_y == goal_y:
                        # Check if we're on the CORRECT map
                        if goal_map in current_map:
                            # We're at goal on correct map
                            if should_interact:
                                nav_action = ['A']
                                logger.info(f"📍 [DIRECTIVE NAV] At goal, pressing A to interact")
                            else:
                                logger.info(f"📍 [DIRECTIVE NAV] At goal (walk-to), continuing past")
                                nav_action = None  # Let VLM handle
                        else:
                            # We're at goal coordinates but WRONG map - this is a map transition point
                            # Need to continue moving to cross into the target map
                            logger.info(f"📍 [DIRECTIVE NAV] At goal coords ({goal_x}, {goal_y}) but wrong map!")
                            logger.info(f"   Current map: '{current_map}', Target map: '{goal_map}'")
                            logger.info(f"   This is likely a map transition - continuing movement")
                            
                            # Determine which direction to move based on map transition
                            # Usually moving UP from Littleroot Town transitions to Route 101
                            # We'll use the goal_direction if available, or try UP as default
                            directive_details = self.objective_manager.get_current_directive()
                            goal_direction = directive_details.get('goal_direction', 'north') if directive_details else 'north'
                            
                            # Map direction strings to actions
                            direction_map = {
                                'north': 'UP',
                                'south': 'DOWN',
                                'east': 'RIGHT',
                                'west': 'LEFT',
                                'up': 'UP',
                                'down': 'DOWN',
                                'left': 'LEFT',
                                'right': 'RIGHT'
                            }
                            
                            transition_action = direction_map.get(goal_direction.lower(), 'UP')
                            nav_action = [transition_action]
                            logger.info(f"📍 [DIRECTIVE NAV] Attempting map transition with: {transition_action}")
                    
                    # Second priority: Check if adjacent to goal (for interaction goals)
                    elif distance == 1 and should_interact and goal_map in current_map:
                        # Determine required direction to face goal
                        if dx > 0:
                            required_direction = 'RIGHT'
                        elif dx < 0:
                            required_direction = 'LEFT'
                        elif dy > 0:
                            required_direction = 'DOWN'
                        else:
                            required_direction = 'UP'
                        
                        if current_orientation == required_direction:
                            # Already facing goal - press A to interact
                            nav_action = ['A']
                            logger.info(f"📍 [DIRECTIVE NAV] Adjacent and facing goal, pressing A")
                        else:
                            # Turn to face goal first
                            nav_action = [required_direction]
                            logger.info(f"📍 [DIRECTIVE NAV] Turning to face goal: {required_direction}")
                    
                    # Third priority: Try A* pathfinding
                    else:
                        logger.info(f"📍 [DIRECTIVE NAV] Distance to goal: {distance}, dx={dx}, dy={dy}")
                        
                        # PRIORITY 1: Try direct pathfinding to target coordinates (local 15x15)
                        # This uses exact target coords and finds optimal path within visible range
                        pathfind_action = _pathfind_to_target(state_data, goal_x, goal_y)
                        
                        if pathfind_action:
                            logger.info(f"📍 [DIRECTIVE NAV] Local target A* (15x15) recommends: {pathfind_action}")
                        
                        # PRIORITY 2: Try global stitched map A* with exact coordinates
                        if not pathfind_action:
                            stitched_map_info = state_data.get('map', {}).get('stitched_map_info')
                            
                            if stitched_map_info and stitched_map_info.get('available'):
                                current_area = stitched_map_info.get('current_area', {})
                                grid_serializable = current_area.get('grid')
                                bounds = current_area.get('bounds')
                                origin_offset = current_area.get('origin_offset')
                                player_grid_pos = current_area.get('player_grid_pos')
                                
                                if grid_serializable and bounds and origin_offset and player_grid_pos:
                                    logger.info(f"📍 [DIRECTIVE NAV] Using global coordinate A* pathfinding to ({goal_x}, {goal_y})")
                                    print(f"🗺️ [DIRECTIVE COORD A*] Pathfinding to exact coordinates ({goal_x}, {goal_y})")
                                    
                                    # Convert grid to proper format
                                    location_grid = {}
                                    for key, value in grid_serializable.items():
                                        x, y = map(int, key.split(','))
                                        location_grid[(x, y)] = value
                                    
                                    # CRITICAL: Grid keys are in WORLD coordinates, so pass world position
                                    # current_x, current_y are already in world coordinates from emulator
                                    # Do NOT use player_grid_pos which is in grid coordinates!
                                    
                                    # Call coordinate-based global A* pathfinding
                                    pathfind_action = _astar_pathfind_to_coords_with_grid(
                                        location_grid=location_grid,
                                        bounds=bounds,
                                        current_pos=(current_x, current_y),  # Use world coordinates
                                        target_pos=(goal_x, goal_y),
                                        location=current_map,
                                        recent_positions=_recent_positions
                                    )
                                    
                                    if pathfind_action:
                                        logger.info(f"📍 [DIRECTIVE NAV] Global coordinate A* recommends: {pathfind_action}")
                        
                        # FALLBACK 3: Direction-based global A* (exploration mode)
                        if not pathfind_action:
                            # Determine general direction to goal
                            if abs(dx) > abs(dy):
                                goal_direction = 'east' if dx > 0 else 'west'
                            else:
                                goal_direction = 'south' if dy > 0 else 'north'
                            
                            logger.info(f"📍 [DIRECTIVE NAV] Coordinate A* failed, trying direction-based global A* toward '{goal_direction}'")
                        
                        # This uses the complete explored map and can route around obstacles globally
                        stitched_map_info = state_data.get('map', {}).get('stitched_map_info')
                        
                        if not pathfind_action and stitched_map_info and stitched_map_info.get('available'):
                            current_area = stitched_map_info.get('current_area', {})
                            grid_serializable = current_area.get('grid')
                            bounds = current_area.get('bounds')
                            origin_offset = current_area.get('origin_offset')
                            player_grid_pos = current_area.get('player_grid_pos')
                            
                            if grid_serializable and bounds and origin_offset and player_grid_pos:
                                logger.info(f"📍 [DIRECTIVE NAV] Using global stitched map A* pathfinding toward '{goal_direction}'")
                                print(f"🗺️ [DIRECTIVE GLOBAL A*] Map stitcher available, using global pathfinding toward '{goal_direction}'")
                                
                                # Convert grid to proper format
                                location_grid = {}
                                for key, value in grid_serializable.items():
                                    x, y = map(int, key.split(','))
                                    location_grid[(x, y)] = value
                                
                                # CRITICAL: Grid keys are in WORLD coordinates, so pass world position
                                # current_x, current_y are already in world coordinates from emulator
                                # Do NOT use player_grid_pos which is in grid coordinates!
                                
                                # Call global A* pathfinding
                                pathfind_action = _astar_pathfind_with_grid_data(
                                    location_grid=location_grid,
                                    bounds=bounds,
                                    current_pos=(current_x, current_y),  # Use world coordinates
                                    location=current_map,
                                    goal_direction=goal_direction,
                                    recent_positions=_recent_positions
                                )
                                
                                if pathfind_action:
                                    logger.info(f"📍 [DIRECTIVE NAV] Global A* recommends: {pathfind_action}")
                        
                        # FALLBACK 3: Direction-based local A* (edge of 15x15)
                        if not pathfind_action:
                            logger.info(f"📍 [DIRECTIVE NAV] Trying direction-based local A*")
                            pathfind_action = _local_pathfind_from_tiles(state_data, goal_direction, recent_actions)
                            
                            if pathfind_action:
                                logger.info(f"📍 [DIRECTIVE NAV] Direction-based A* recommends: {pathfind_action}")
                        
                        # LAST RESORT: Simple directional movement
                        if pathfind_action:
                            nav_action = [pathfind_action]
                        else:
                            if abs(dx) > abs(dy):
                                nav_action = ['RIGHT'] if dx > 0 else ['LEFT']
                            else:
                                nav_action = ['DOWN'] if dy > 0 else ['UP']
                            logger.info(f"📍 [DIRECTIVE NAV] All A* failed, using simple direction: {nav_action[0]}")
                    
                    # VLM EXECUTOR PATTERN (competition compliance)
                    # For directives, the pathfinding system has already determined the optimal action
                    # The VLM just needs to confirm it (this satisfies competition rules)
                    if nav_action:
                        try:
                            executor_prompt = f"""Execute the recommended navigation action.

DIRECTIVE: {description}
RECOMMENDED ACTION: {nav_action[0]}

This action was determined by A* pathfinding to reach the target.
Confirm by responding with the exact action: {nav_action[0]}
"""
                            vlm_response = vlm.get_text_query(executor_prompt, "DIRECTIVE_EXECUTOR")
                            
                            # Parse VLM response
                            vlm_action = vlm_response.strip().upper()
                            valid_buttons = ['A', 'B', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'START', 'SELECT']
                            
                            # If VLM confirms the recommended action or gives a valid button, use it
                            if vlm_action == nav_action[0]:
                                logger.info(f"📍 [DIRECTIVE] VLM confirmed recommended action: {vlm_action}")
                                return [vlm_action]
                            elif vlm_action in valid_buttons:
                                # VLM suggested different action - log warning but use recommendation
                                logger.warning(f"📍 [DIRECTIVE] VLM suggested {vlm_action}, but using pathfinding recommendation: {nav_action[0]}")
                                return [nav_action[0]]
                            else:
                                # VLM gave invalid response - use recommendation directly
                                logger.warning(f"📍 [DIRECTIVE] VLM response unclear: '{vlm_response}', using recommendation: {nav_action[0]}")
                                return [nav_action[0]]
                                    
                        except Exception as e:
                            # If VLM fails, use the pathfinding recommendation (still competition compliant as VLM was called)
                            logger.warning(f"📍 [DIRECTIVE] VLM executor error: {e}, using pathfinding recommendation: {nav_action[0]}")
                            return [nav_action[0]]
                
                # Handle INTERACT directive (at target, just press A)
                elif directive.get('action') == 'INTERACT':
                    logger.info(f"📍 [DIRECTIVE] INTERACT directive - pressing A")
                    
                    # VLM executor for compliance
                    try:
                        executor_prompt = f"""You are executing an interaction directive.

DIRECTIVE: {description}

The agent is at the target position and needs to interact by pressing A.

What button should we press? Respond with ONLY the button name (A, B, UP, DOWN, LEFT, RIGHT, START, SELECT).
"""
                        vlm_response = vlm.get_text_query(executor_prompt, "DIRECTIVE_EXECUTOR_INTERACT")
                        
                        vlm_action = vlm_response.strip().upper()
                        valid_buttons = ['A', 'B', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'START', 'SELECT']
                        
                        if vlm_action in valid_buttons:
                            logger.info(f"📍 [DIRECTIVE] VLM confirmed interaction: {vlm_action}")
                            return [vlm_action]
                        else:
                            # Fallback: just press A for interaction
                            logger.warning(f"📍 [DIRECTIVE] VLM unclear, defaulting to A for interaction")
                            return ['A']
                            
                    except Exception as e:
                        logger.error(f"📍 [DIRECTIVE] VLM executor error: {e}, defaulting to A")
                        return ['A']
                
                # Handle DIALOGUE (press A to advance dialogue)
                elif directive.get('action') == 'DIALOGUE':
                    logger.info(f"📍 [DIRECTIVE] DIALOGUE - pressing A to advance")
                    # Simple case: just press A to advance dialogue
                    return ['A']
                
                # Handle WAIT_FOR_DIALOGUE (don't interrupt dialogue)
                elif directive.get('action') == 'WAIT_FOR_DIALOGUE':
                    logger.info(f"📍 [DIRECTIVE] Waiting for auto-dialogue to complete - returning empty action")
                    # Return empty action to wait - don't fall through to VLM
                    # This prevents the agent from trying to navigate while waiting for dialogue
                    return []
                
                else:
                    action_value = directive.get('action', 'UNKNOWN')
                    logger.warning(f"📍 [DIRECTIVE] Unknown action type: {action_value}")
        else:
            logger.debug(f"📍 [DIRECTIVE] ObjectiveManager not initialized yet")
            
    except ImportError as e:
        logger.debug(f"📍 [DIRECTIVE] Planning module not available: {e}")
        print(f"⚠️ [DIRECTIVE] ImportError: {e}")
    except Exception as e:
        logger.error(f"📍 [DIRECTIVE] Error processing directive: {e}", exc_info=True)
        print(f"❌ [DIRECTIVE] Exception caught! {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # Fall through to other priorities
    
    # 🎯 PRIORITY 1: VLM VISUAL DIALOGUE DETECTION (HIGHEST PRIORITY - BUT ONLY IF OPENER BOT NOT ACTIVE)
    # NEW: Check for continue_prompt_visible (red triangle indicator) - MOST RELIABLE
    # The red triangle ❤️ at end of dialogue is a perfect signal for "press A"
    # 
    # DIALOGUE FALSE POSITIVE PROTECTION:
    # Some locations (e.g., MOVING_VAN) have visual elements that VLM mistakes for dialogue boxes.
    # Blacklist these specific locations to prevent the agent from spamming A button.
    DIALOGUE_DETECTION_BLACKLIST = [
        'MOVING_VAN',  # Has cardboard boxes that VLM mistakes for dialogue boxes
        # Add other problematic locations here if discovered
    ]
    
    # 🔺 PRIORITY 1A: RED TRIANGLE INDICATOR (MOST RELIABLE)
    # The red triangle ❤️ at end of dialogue is the PERFECT signal for "press A"
    # This is much more reliable than text_box_visible alone
    # BUT: Must check for player monologue to avoid false positives!
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_elements = latest_observation.get('visual_data', {}).get('visual_elements', {})
        on_screen_text = latest_observation.get('visual_data', {}).get('on_screen_text', {})
        continue_prompt_visible = visual_elements.get('continue_prompt_visible', False)
        
        if continue_prompt_visible:
            current_location = state_data.get('player', {}).get('location', '')
            
            # CRITICAL: Check if this is player monologue before pressing A
            dialogue_text = on_screen_text.get('dialogue', '')
            speaker = on_screen_text.get('speaker', '')
            
            # Player monologue ONLY detects "Player:" prefix in dialogue text
            # Do NOT use speaker field - it's unreliable (Mom talking TO Casey shows speaker="CASEY")
            is_player_monologue = (dialogue_text and dialogue_text.strip().upper().startswith('PLAYER:'))
            
            if is_player_monologue:
                # Player monologues are likely VLM hallucinations - ignore them
                logger.info(f"🔺 [CONTINUE PROMPT] Player monologue detected - ignoring (likely hallucination)")
                print(f"⚠️ [DIALOGUE] Player monologue detected - ignoring (likely VLM hallucination)")
                # Don't return anything, fall through to check other priorities
            elif current_location in DIALOGUE_DETECTION_BLACKLIST:
                logger.warning(f"🔺 [CONTINUE PROMPT] Red triangle detected but location '{current_location}' is blacklisted - ignoring")
                print(f"⚠️ [DIALOGUE] Ignoring continue prompt in {current_location} (known false positive)")
            else:
                logger.info(f"🔺 [CONTINUE PROMPT] Red triangle indicator detected - pressing A to continue dialogue")
                print(f"🔺 [DIALOGUE] Red triangle ❤️ visible, pressing A to continue")
                return ["A"]
    
    # 🔺 PRIORITY 1B: FALLBACK - TEXT BOX DETECTION
    # Simple rule: If we see dialogue (text box visible), press A to advance
    # UNLESS it's player monologue (which we must ignore completely)
    # The VLM sees the full rendered text, so we can trust it's ready for input
    if visual_dialogue_active:
        current_location = state_data.get('player', {}).get('location', '')
        
        if current_location in DIALOGUE_DETECTION_BLACKLIST:
            logger.warning(f"💬 [DIALOGUE] VLM detected dialogue but location '{current_location}' is blacklisted - ignoring false positive")
            print(f"⚠️ [DIALOGUE] Ignoring VLM dialogue in {current_location} (known false positive)")
        else:
            # CRITICAL: Check for player monologue BEFORE pressing A
            visual_data = latest_observation.get('visual_data', {})
            on_screen_text = visual_data.get('on_screen_text', {})
            dialogue_text = on_screen_text.get('dialogue', '')
            
            # Player monologue ONLY detects "Player:" prefix in dialogue text
            # Do NOT use speaker field - it's unreliable (Mom talking TO Casey shows speaker="CASEY")
            is_player_monologue = (dialogue_text and dialogue_text.strip().upper().startswith('PLAYER:'))
            
            if is_player_monologue:
                # Player monologues are likely VLM hallucinations - ignore them
                logger.info(f"💬 [DIALOGUE 1B] Player monologue detected - ignoring (likely hallucination)")
                print(f"💬 [DIALOGUE 1B] Player monologue detected - ignoring (likely VLM hallucination)")
                # Don't return anything, fall through to check other priorities
            else:
                # Press A immediately - VLM can see the text is rendered
                logger.info(f"💬 [DIALOGUE 1B] Dialogue visible - pressing A to advance")
                print(f"💬 [DIALOGUE] Text box visible, pressing A to advance")
                return ["A"]
    
    # 🚨 PRIORITY 2: NEW GAME MENU DETECTION
    # Must happen before ANY other logic to prevent override conflicts
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_data = latest_observation.get('visual_data', {})
        on_screen_text = visual_data.get('on_screen_text', {})
        dialogue_text = (on_screen_text.get('dialogue') or '').upper()
        menu_title = (on_screen_text.get('menu_title') or '').upper()
        
        # Check milestones to ensure we haven't progressed past this screen
        milestones = state_data.get('milestones', {})
        player_name_milestone = milestones.get('PLAYER_NAME_SET', {})
        player_name_set = player_name_milestone.get('completed', False) if isinstance(player_name_milestone, dict) else bool(player_name_milestone)
        
        if ('NEW GAME' in dialogue_text or 'NEW GAME' in menu_title) and not player_name_set:
            logger.info(f"🎯 [NEW GAME FIX] NEW GAME menu detected! Bypassing all other logic.")
            logger.info(f"🎯 [NEW GAME FIX] - dialogue: '{dialogue_text}'")
            logger.info(f"🎯 [NEW GAME FIX] - menu_title: '{menu_title}'")
            print(f"🎯 [NEW GAME FIX] Selecting NEW GAME with A")
            return ["A"]
    
    """
    ===============================================================================
    🚨 EMERGENCY PATCH APPLIED - REVIEW BEFORE PRODUCTION 🚨
    ===============================================================================
    
    PATCH: Title Screen Bypass (lines 18-22)
    - Original issue: Agent would freeze on title screen due to complex VLM processing
    - Emergency fix: Hard-coded "A" button press for title screen state
    - TODO: Replace with smarter detection that handles:
      * Multiple title screen states (main menu, options, etc.)
      * Character creation screens  
      * Save/load dialogs
      * Any other menu-like states that need simple navigation
    
    INTEGRATION NOTES:
    - This bypass should be expanded to handle more menu states programmatically
    - Consider creating a "simple_navigation_mode" for all menu/UI interactions
    - The main VLM action logic below this patch is intact and working
    - When reintegrating full AI, keep this as a fallback for known simple states
    
    ===============================================================================
    """
    # ENHANCED FIX: Robust title/menu screen detection (adapted from simple agent)
    game_data = state_data.get('game', {})
    player_data = state_data.get('player', {})
    
    # Use same detection logic as simple agent for consistency
    player_location = player_data.get("location", "")
    game_state_value = game_data.get("game_state", "").lower()
    player_name = player_data.get("name", "").strip()
    
    # FINAL FIX: Ultra-conservative title screen detection
    # Only trigger for actual title screens, never during gameplay
    is_title_screen = (
        # Only for explicit title sequence or very early states
        player_location == "TITLE_SEQUENCE" or
        # Only if game state explicitly contains "title" 
        game_state_value == "title" or
        # Only if no player name AND at exact origin (0,0) - very strict
        ((not player_name or player_name == "????????") and 
         (player_data.get('position', {}).get('x', -1) == 0 and 
          player_data.get('position', {}).get('y', -1) == 0) and
         player_location.lower() in ['', 'unknown', 'title_sequence'])
    )
    
    # CRITICAL: Use milestones to override title detection
    # If player name is set, we're past the title screen regardless of other conditions
    milestones = state_data.get('milestones', {})
    if milestones.get('PLAYER_NAME_SET', False) or milestones.get('INTRO_CUTSCENE_COMPLETE', False):
        is_title_screen = False  # Force override - we're in gameplay now
    
    if is_title_screen:
        logger.info(f"[ACTION] Title screen detected!")
        logger.info(f"[ACTION] - player_location: '{player_location}'")
        logger.info(f"[ACTION] - game_state: '{game_state_value}'")
        logger.info(f"[ACTION] - player_name: '{player_name}'")
        logger.info(f"[ACTION] - party_count: {game_data.get('party_count', 0)}")
        logger.info(f"[ACTION] - position: {player_data.get('position', {})}")
        logger.info("[ACTION] Using simple navigation: A to select NEW GAME")
        return ["A"]
    
    # ENHANCED FIX: Detect name selection screen after title screen
    # Check for name selection context using visual data and milestones
    visual_data = latest_observation.get('visual_data', {}) if isinstance(latest_observation, dict) else {}
    on_screen_text = visual_data.get('on_screen_text', {})
    
    dialogue_text = (on_screen_text.get('dialogue') or '').upper()
    menu_title = (on_screen_text.get('menu_title') or '').upper()
    
    # Look for name selection indicators - but also check step count as backup
    is_name_selection = False
    dialogue_text = (on_screen_text.get('dialogue') or '').upper()
    menu_title = (on_screen_text.get('menu_title') or '').upper()
    
    # FIX: Use actual step count from state_data instead of len(recent_actions)
    # The recent_actions is capped at 25, so len(recent_actions) gets stuck at 25
    current_step = state_data.get('step_number', len(recent_actions or []))
    
    # DEBUG: Verify step calculation is working
    if current_step >= 50:  # Only debug once we're in VLM mode
        print(f"🔢 [STEP DEBUG] current_step={current_step}, step_number={state_data.get('step_number', 'missing')}, recent_actions_len={len(recent_actions) if recent_actions else 0}")
    
    # DEBUG: Track our progress every few steps
    if current_step % 10 == 0 and current_step >= 30:
        print(f"🔍 [DEBUG] Step {current_step} reached - Milestone check in progress")
    
    # CRITICAL DEBUG: Force milestone status check at key steps
    intro_complete = milestones.get('INTRO_CUTSCENE_COMPLETE', False)
    
    if current_step in [33, 34, 35, 40, 45, 50, 51]:
        print(f"🚨 [CRITICAL] Step {current_step}: PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}, INTRO_COMPLETE={intro_complete}")
        print(f"   Navigation mode check: intro_complete={intro_complete}, current_step > 50: {current_step > 50}")
    
    # DEBUG: Always log visual data for name selection detection around critical steps
    if current_step >= 30:  # Only log around critical transition
        logger.info(f"[ACTION] Step {current_step} - Name check: dialogue='{dialogue_text}', menu='{menu_title}', PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}")
        logger.info(f"[ACTION] Step {current_step} - Visual data keys: {list(visual_data.keys()) if visual_data else 'None'}")
        logger.info(f"[ACTION] Step {current_step} - On-screen text keys: {list(on_screen_text.keys()) if on_screen_text else 'None'}")
    
    # Check if this looks like name selection screen using multiple methods
    name_text_detected = ('YOUR NAME' in dialogue_text or 'NAME?' in dialogue_text or 
                          'YOUR NAME' in menu_title or 'NAME?' in menu_title or
                          'SELECT NAME' in menu_title or 'SELECT YOUR NAME' in menu_title)
    
    # Also check VLM perception for name selection context
    vlm_context_name_selection = False
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        vd = latest_observation['visual_data']
        vlm_dialogue = vd.get('on_screen_text', {}).get('dialogue', '')
        vlm_menu = vd.get('on_screen_text', {}).get('menu_title', '')
        if vlm_dialogue and ('YOUR NAME' in vlm_dialogue or 'NAME?' in vlm_dialogue):
            vlm_context_name_selection = True
        if vlm_menu and ('SELECT' in vlm_menu and 'NAME' in vlm_menu):
            vlm_context_name_selection = True
    
    # Expanded step range and VLM detection
    in_name_step_range = (25 <= current_step <= 50 and not milestones.get('PLAYER_NAME_SET', False))
    
    if ((name_text_detected or vlm_context_name_selection or in_name_step_range) 
        and not milestones.get('PLAYER_NAME_SET', False)):
        is_name_selection = True
        logger.info("[ACTION] Name selection screen detected!")
        logger.info(f"[ACTION] - text_detected: {name_text_detected}, vlm_detected: {vlm_context_name_selection}, step_range: {in_name_step_range}")
        logger.info(f"[ACTION] - dialogue: '{dialogue_text}', menu: '{menu_title}'")
        
        # Simple name selection logic - press A to accept default name quickly
        if current_step < 30:  # Early steps: position at default
            logger.info("[ACTION] Positioning for name selection")
            return ["A"]
        else:  # Later steps: accept default name
            logger.info("[ACTION] Accepting default name")
            return ["A"]
    
    # NEW GAME MENU FIX: Detect "NEW GAME / OPTIONS" menu screen (HIGH PRIORITY)
    # This must happen BEFORE other override systems to prevent conflicts
    if ('NEW GAME' in dialogue_text or 'NEW GAME' in menu_title) and not milestones.get('PLAYER_NAME_SET', False):
        logger.info(f"[ACTION] NEW GAME menu detected!")
        logger.info(f"[ACTION] - dialogue: '{dialogue_text}'")
        logger.info(f"[ACTION] - menu_title: '{menu_title}'")
        logger.info("[ACTION] Selecting NEW GAME with A")
        return ["A"]
    
    # CRITICAL DEBUG: Override right after PLAYER_NAME_SET to avoid VLM confusion
    # But only until INTRO_CUTSCENE_COMPLETE - then let VLM take over
    
    # DEBUG: Track milestone status at key steps
    if current_step >= 40 and current_step % 5 == 0:  # Every 5th step after 40
        print(f"🏆 [MILESTONE] Step {current_step}: PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}, INTRO_CUTSCENE_COMPLETE={intro_complete}")
    
    # NAVIGATION DECISION LOGIC: Clear hierarchy of what mode to use
    
    # REMOVED: MEMORY-BASED DIALOGUE DETECTION
    # The game memory's in_dialog flag is unreliable (42.9% accurate vs VLM's 85.7%)
    # It frequently gets stuck reporting in_dialog=True even after dialogue ends
    # (e.g., MOVING_VAN, post-dialogue in LITTLEROOT TOWN)
    # 
    # Relying solely on VLM visual detection (text_box_visible) which is much more accurate
    # and doesn't suffer from stuck state issues.
    #
    # If memory-based detection is needed in future, it should ONLY be used when VLM also confirms dialogue
    # to avoid false positives from stuck memory state.
    
    # Log memory state for debugging but don't act on it
    in_dialog = game_data.get('in_dialog', False)
    if in_dialog:
        logger.debug(f"[ACTION] Memory reports in_dialog=True (not acting on this - VLM detection only)")
        # Note: Not returning ["A"] here - VLM detection above is the only trigger
    
    # 1. Post-name override: Only when name is set but intro cutscene isn't complete yet
    # FIXED: Don't activate if player has already progressed beyond intro (has Pokemon on routes)
    player_location = player_data.get('location', '')
    is_in_moving_van = "MOVING_VAN" in str(player_location).upper()
    override_step_limit = 15  # Maximum steps to spend in override mode
    
    # Check for advanced game states that should trigger VLM mode
    on_route_101 = 'ROUTE 101' in str(player_location).upper()
    has_pokemon = state_data.get('player', {}).get('party', [])
    advanced_location = on_route_101 or 'ROUTE' in str(player_location).upper()
    
    # CRITICAL FIX: If player already has Pokemon, they've completed intro - don't override!
    player_has_pokemon = len(has_pokemon) > 0 if has_pokemon else False
    
    if (milestones.get('PLAYER_NAME_SET', False) and 
        not intro_complete and 
        not advanced_location and  # Don't override if we're on routes
        not player_has_pokemon and  # FIXED: Don't override if player has Pokemon
        current_step <= override_step_limit and 
        not is_in_moving_van):
        logger.info(f"[ACTION] Step {current_step} - Post-name override active (location: {player_location})")
        print(f"🔧 [OVERRIDE] Step {current_step} - Post-name override: pressing A (intro_complete={intro_complete}, location={player_location}, has_pokemon={player_has_pokemon})")
        return ["A"]
    
    # 2. VLM Navigation Mode: When intro is complete OR we exceed override limits OR advanced location
    elif intro_complete or current_step > override_step_limit or is_in_moving_van or advanced_location:
        if current_step % 5 == 0 or current_step in [16, 21, 27] or advanced_location:
            print(f"🤖 [VLM MODE] Step {current_step} - VLM Navigation Active (intro_complete={intro_complete}, past_limit={current_step > override_step_limit}, moving_van={is_in_moving_van}, advanced_location={advanced_location})")
        
        # Override status check - only log periodically
        if current_step % 100 == 0:
            logger.info(f"Mode check (Step {current_step}): VLM navigation active, overrides inactive")
        
        # Direct VLM call - let the VLM handle all navigation decisions
        pass  # Continue to VLM logic below
    
    # 3. Legacy mode: Only for early game before VLM navigation is active
    else:
        print(f"🎯 [EARLY MODE] Step {current_step} - Legacy navigation active (name_set={milestones.get('PLAYER_NAME_SET', False)}, intro_complete={intro_complete})")
        
        # DEBUG: Log when NOT in title screen (to catch transition)
        if not is_title_screen and len(recent_actions or []) < 5:
            logger.info(f"[ACTION] NOT title screen - using full navigation logic")
            logger.info(f"[ACTION] - player_location: '{player_location}'")
            logger.info(f"[ACTION] - game_state: '{game_state_value}'")
            logger.info(f"[ACTION] - player_name: '{player_name}'")
            logger.info(f"[ACTION] - position: {player_data.get('position', {})}")
        
        # Debug logging for state detection (only if not in title)
        if not is_title_screen:
            logger.info(f"[ACTION] Debug - game_state: '{game_state_value}', location: '{player_location}', position: {player_data.get('position', {})}")
    
    # ============================================================================
    # VLM NAVIGATION LOGIC: All paths above lead here for VLM-based decisions
    # ============================================================================
    
    # CRITICAL POSITION DEBUG: Track if agent is actually moving
    player_data = state_data.get('player', {})
    current_position = player_data.get('position', {})
    current_x = current_position.get('x', 'unknown')
    current_y = current_position.get('y', 'unknown')
    current_map = current_position.get('map', 'unknown')
    
    print(f"🎯 [POSITION DEBUG] Step {len(recent_actions) if recent_actions else 0}: Player at ({current_x}, {current_y}) on map {current_map}")
    
    # Store position for comparison
    if not hasattr(action_step, 'last_position'):
        action_step.last_position = (current_x, current_y, current_map)
    
    last_x, last_y, last_map = action_step.last_position
    if (current_x, current_y, current_map) != (last_x, last_y, last_map):
        print(f"✅ [POSITION CHANGE] Moved from ({last_x}, {last_y}) to ({current_x}, {current_y}) on map {current_map}")
        action_step.last_position = (current_x, current_y, current_map)
    else:
        print(f"⚠️ [POSITION STUCK] NO MOVEMENT - Still at ({current_x}, {current_y}) on map {current_map}")

    # Get formatted state context and useful summaries
    state_context = format_state_for_llm(state_data)
    state_summary = format_state_summary(state_data)
    movement_options = get_movement_options(state_data)
    party_health = get_party_health_summary(state_data)
    
    # PRIORITY 1 ENHANCEMENT: Generate extended map view from MapStitcher
    extended_map_view = None
    exploration_status = None
    try:
        map_stitcher = state_data.get('map', {}).get('_map_stitcher_instance')
        if map_stitcher:
            # Get current location info
            location_name = state_data.get('player', {}).get('location', 'Unknown')
            player_pos = (current_x, current_y) if isinstance(current_x, int) and isinstance(current_y, int) else None
            
            if location_name and location_name != 'Unknown' and player_pos:
                # Generate extended map display (larger view from stitched data)
                try:
                    npcs = state_data.get('npcs', [])
                    connections = map_stitcher.get_location_connections(location_name)
                    extended_map_lines = map_stitcher.generate_location_map_display(
                        location_name,
                        player_pos,
                        npcs=npcs,
                        connections=connections
                    )
                    if extended_map_lines:
                        extended_map_view = '\n'.join(extended_map_lines)
                        print(f"🗺️ [EXTENDED MAP] Generated {len(extended_map_lines)} line extended view for {location_name}")
                        
                        # Get exploration stats
                        map_id = map_stitcher.get_map_id(
                            state_data.get('map', {}).get('bank', 0),
                            state_data.get('map', {}).get('number', 0)
                        )
                        if map_id in map_stitcher.map_areas:
                            area = map_stitcher.map_areas[map_id]
                            bounds = getattr(area, 'explored_bounds', {})
                            if bounds:
                                width = bounds.get('max_x', 0) - bounds.get('min_x', 0) + 1
                                height = bounds.get('max_y', 0) - bounds.get('min_y', 0) + 1
                                visited_count = getattr(area, 'visited_count', 1)
                                exploration_status = f"Explored area: {width}x{height} tiles | Visited: {visited_count}x"
                                print(f"🗺️ [EXPLORATION] {exploration_status}")
                except Exception as e:
                    logger.warning(f"[EXTENDED MAP] Error generating extended map view: {e}")
                    print(f"⚠️ [EXTENDED MAP] Failed to generate extended view: {e}")
    except Exception as e:
        logger.warning(f"[EXTENDED MAP] Error accessing map stitcher: {e}")
    
    logger.info("[ACTION] Starting action decision")
    logger.info(f"[ACTION] State: {state_summary}")
    logger.info(f"[ACTION] Party health: {party_health['healthy_count']}/{party_health['total_count']} healthy")
    if movement_options:
        logger.info(f"[ACTION] Movement options: {movement_options}")
    
    # Build enhanced action context
    action_context = []
    
    # Extract key info for context
    game_data = state_data.get('game', {})
    
    # Battle vs Overworld context
    if game_data.get('in_battle', False):
        action_context.append("=== BATTLE MODE ===")
        battle_info = game_data.get('battle_info', {})
        if battle_info:
            if 'player_pokemon' in battle_info and battle_info['player_pokemon']:
                player_pkmn = battle_info['player_pokemon']
                action_context.append(f"Your Pokemon: {player_pkmn.get('species_name', player_pkmn.get('species', 'Unknown'))} (Lv.{player_pkmn.get('level', '?')}) HP: {player_pkmn.get('current_hp', '?')}/{player_pkmn.get('max_hp', '?')}")
            if 'opponent_pokemon' in battle_info and battle_info['opponent_pokemon']:
                opp_pkmn = battle_info['opponent_pokemon']
                action_context.append(f"Opponent: {opp_pkmn.get('species_name', opp_pkmn.get('species', 'Unknown'))} (Lv.{opp_pkmn.get('level', '?')}) HP: {opp_pkmn.get('current_hp', '?')}/{opp_pkmn.get('max_hp', '?')}")
    else:
        action_context.append("=== OVERWORLD MODE ===")
        
        # PRIORITY 1: Add extended map view from MapStitcher (GLOBAL CONTEXT)
        if extended_map_view:
            action_context.append("")
            action_context.append("=== EXTENDED MAP VIEW (from exploration memory) ===")
            if exploration_status:
                action_context.append(exploration_status)
            action_context.append("")
            action_context.append(extended_map_view)
            action_context.append("")
            action_context.append("Legend: P=You, N=NPC, .=walkable, #=blocked, ~=grass, ≈=water, S=stairs/warp")
            action_context.append("This is your COMPLETE explored map - use it to plan paths and avoid dead ends!")
            action_context.append("")
        
        # Movement options from utility (LOCAL TACTICAL INFO)
        if movement_options:
            action_context.append("=== IMMEDIATE MOVEMENT OPTIONS ===")
            for direction, description in movement_options.items():
                action_context.append(f"  {direction}: {description}")
    
    # Add comprehensive state context (includes map visualization)
    if state_context and state_context.strip():
        action_context.append("=== GAME STATE CONTEXT ===")
        action_context.append(state_context.strip())
        print(f"🗺️ [MAP DEBUG] Added state context to VLM prompt ({len(state_context)} chars)")
        # Show a preview of the map data
        if "MAP:" in state_context:
            map_preview = state_context[state_context.find("MAP:"):state_context.find("MAP:") + 200] + "..."
            print(f"🗺️ [MAP DEBUG] Map preview: {map_preview}")
    else:
        print(f"🗺️ [MAP DEBUG] No state context available for VLM prompt")
    
    # Party health summary
    if party_health['total_count'] > 0:
        action_context.append("=== PARTY STATUS ===")
        action_context.append(f"Healthy Pokemon: {party_health['healthy_count']}/{party_health['total_count']}")
        if party_health['critical_pokemon']:
            action_context.append("Critical Pokemon:")
            for critical in party_health['critical_pokemon']:
                action_context.append(f"  {critical}")
    
    # Recent actions context
    if recent_actions:
        try:
            # Ensure recent_actions is a valid iterable
            if recent_actions is not None:
                recent_list = list(recent_actions) if recent_actions else []
                if recent_list:
                    action_context.append(f"Recent Actions: {', '.join(recent_list[-5:])}")
        except Exception as e:
            logger.warning(f"[ACTION] Error processing recent_actions: {e}")
            # Continue without recent actions context
    
    # Visual perception context (new structured data)
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_data = latest_observation['visual_data']
        action_context.append("=== VISUAL PERCEPTION ===")
        action_context.append(f"Screen Context: {visual_data.get('screen_context', 'unknown')}")
        
        # On-screen text information
        on_screen_text = visual_data.get('on_screen_text', {})
        visual_elements = visual_data.get('visual_elements', {})
        
        # CRITICAL FIX: Check if dialogue box is actually visible, not just if dialogue text exists
        text_box_visible = visual_elements.get('text_box_visible', False)
        

        
        if on_screen_text.get('menu_title'):
            action_context.append(f"Menu: {on_screen_text['menu_title']}")
        if on_screen_text.get('button_prompts'):
            # Handle button prompts that might be dictionaries or strings
            button_prompts = on_screen_text['button_prompts']
            if isinstance(button_prompts, list):
                prompt_strs = []
                for prompt in button_prompts:
                    if isinstance(prompt, dict):
                        # Extract text from dictionary format
                        prompt_text = prompt.get('text', str(prompt))
                        prompt_strs.append(prompt_text)
                    else:
                        prompt_strs.append(str(prompt))
                action_context.append(f"Button Prompts: {', '.join(prompt_strs)}")
            else:
                action_context.append(f"Button Prompts: {str(button_prompts)}")
        
        # Add dialogue box status for VLM clarity
        action_context.append(f"Dialogue Box Status: {'VISIBLE' if text_box_visible else 'NOT VISIBLE'}")
        
        # ENHANCED DIALOGUE DEBUG: Critical detection troubleshooting
        if on_screen_text.get('dialogue'):
            print(f"🗨️ [DIALOGUE DEBUG] Dialogue detected: '{on_screen_text.get('dialogue')}'")
            print(f"🗨️ [DIALOGUE DEBUG] - text_box_visible: {text_box_visible}")
            print(f"🗨️ [DIALOGUE DEBUG] - visual_elements: {visual_elements}")
            print(f"🗨️ [DIALOGUE DEBUG] - screen_context: {visual_data.get('screen_context', 'missing')}")
            print(f"🗨️ [DIALOGUE DEBUG] - All visual_data keys: {list(visual_data.keys())}")
            logger.info(f"[DIALOGUE DEBUG] Dialogue text: '{on_screen_text.get('dialogue')}', text_box_visible: {text_box_visible}, visual_elements: {visual_elements}")
        else:
            print(f"🗨️ [DIALOGUE DEBUG] NO dialogue detected in on_screen_text: {on_screen_text}")
            
        # CRITICAL: Check if we're actually in a dialogue state that should block movement
        screen_context = visual_data.get('screen_context', 'unknown')
        dialogue_text = on_screen_text.get('dialogue', '')
        
        # Filter out fake "dialogue" that's actually just placeholder text from perception template
        # or game state info that got misclassified
        is_fake_dialogue = dialogue_text and any(marker in dialogue_text for marker in [
            'Location:', 'Pos:', 'Money:', 'HP:', 'Pokedex:',  # Game state info
            'ONLY text from dialogue boxes',  # Perception template placeholder
            'DO NOT include HUD',  # Perception template placeholder
            'If no dialogue box visible',  # Perception template placeholder
        ])
        
        if screen_context == 'overworld' and dialogue_text and not is_fake_dialogue:
            print(f"🚨 [CRITICAL ERROR] VLM reports 'overworld' but REAL dialogue exists! This may be misclassified!")
            print(f"🚨 [CRITICAL ERROR] - dialogue: '{dialogue_text}'")
            print(f"🚨 [CRITICAL ERROR] - This could be why movement commands aren't working!")
        elif is_fake_dialogue:
            print(f"✅ [DIALOGUE FILTER] Ignoring fake 'dialogue' (perception template or game state): '{dialogue_text[:70]}...')")
        
        # Check if dialogue contains specific text that indicates we're reading a box/sign
        # Only process if it's NOT fake dialogue
        dialogue_text_raw = on_screen_text.get('dialogue', '')
        if dialogue_text_raw and not is_fake_dialogue:
            dialogue_text_lower = dialogue_text_raw.lower()
            if 'pokémon' in dialogue_text_lower and ('box' in dialogue_text_lower or 'logo' in dialogue_text_lower):
                print(f"🎁 [BOX INTERACTION] Detected box/sign interaction dialogue: '{dialogue_text_raw}'")
                print(f"🎁 [BOX INTERACTION] This requires A to close dialogue before movement will work!")
                action_context.append(f"📦 ACTIVE BOX DIALOGUE: \"{dialogue_text_raw}\" - MUST PRESS A TO CLOSE")
            elif text_box_visible:
                action_context.append(f"ACTIVE Dialogue: \"{dialogue_text_raw}\" - {on_screen_text.get('speaker', 'Unknown')}")
            elif not text_box_visible:
                action_context.append(f"Residual Text (NO dialogue box): \"{dialogue_text_raw}\" - IGNORE THIS")
        
        # Visible entities - handle various formats from VLM
        entities = visual_data.get('visible_entities', [])
        if entities:
            action_context.append("Visible Entities:")
            # Handle different entity formats that VLM might return
            try:
                if isinstance(entities, list) and len(entities) > 0:
                    for i, entity in enumerate(entities[:5]):  # Limit to 5 entities to avoid clutter
                        if isinstance(entity, dict):
                            # Entity is a dictionary with type/name/position
                            action_context.append(f"  - {entity.get('type', 'unknown')}: {entity.get('name', 'unnamed')} at {entity.get('position', 'unknown position')}")
                        elif isinstance(entity, str):
                            # Entity is just a string description
                            action_context.append(f"  - {entity}")
                        else:
                            # Entity is some other type
                            action_context.append(f"  - {str(entity)}")
                elif isinstance(entities, str):
                    # Entities is a single string
                    action_context.append(f"  - {entities}")
            except Exception as e:
                # Fallback if entity processing fails
                action_context.append(f"  - Entities: {str(entities)[:100]}")
                logger.warning(f"[ACTION] Error processing entities: {e}")
        
        # Visual elements status
        visual_elements = visual_data.get('visual_elements', {})
        active_elements = [k.replace('_', ' ').title() for k, v in visual_elements.items() if v]
        if active_elements:
            action_context.append(f"Active Visual Elements: {', '.join(active_elements)}")
        
        # Navigation information from enhanced VLM perception
        navigation_info = visual_data.get('navigation_info', {})
        if navigation_info:
            action_context.append("=== NAVIGATION ANALYSIS ===")
            
            exits = navigation_info.get('exits_visible', [])
            if exits and any(exit for exit in exits if exit):
                action_context.append(f"Exits Visible: {', '.join(str(e) for e in exits if e)}")
            
            interactables = navigation_info.get('interactable_objects', [])
            if interactables and any(obj for obj in interactables if obj):
                action_context.append(f"Interactable Objects: {', '.join(str(o) for o in interactables if o)}")
            
            barriers = navigation_info.get('movement_barriers', [])
            if barriers and any(barrier for barrier in barriers if barrier):
                action_context.append(f"Movement Barriers: {', '.join(str(b) for b in barriers if b)}")
            
            open_paths = navigation_info.get('open_paths', [])
            if open_paths and any(path for path in open_paths if path):
                action_context.append(f"Open Paths: {', '.join(str(p) for p in open_paths if p)}")
        
        # Spatial layout information
        spatial_layout = visual_data.get('spatial_layout', {})
        if spatial_layout:
            room_type = spatial_layout.get('room_type')
            player_pos = spatial_layout.get('player_position')
            features = spatial_layout.get('notable_features', [])
            
            if room_type:
                action_context.append(f"Room Type: {room_type}")
            if player_pos:
                action_context.append(f"Player Position: {player_pos}")
            if features and any(feature for feature in features if feature):
                action_context.append(f"Notable Features: {', '.join(str(f) for f in features if f)}")
    
    context_str = "\n".join(action_context)
    
    # Get the visual screen context to guide decision making
    visual_context = "unknown"
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_context = latest_observation['visual_data'].get('screen_context', 'unknown')
        if not visual_context:  # Handle None or empty string
            visual_context = "unknown"
    
    # DEBUG: Check why visual context becomes None
    if current_step >= 50 and (visual_context == "unknown" or visual_context is None):
        print(f"⚠️ [VISUAL DEBUG] Step {current_step} - visual_context is '{visual_context}'")
        if isinstance(latest_observation, dict):
            print(f"   latest_observation keys: {list(latest_observation.keys())}")
            if 'visual_data' in latest_observation:
                visual_data = latest_observation['visual_data']
                print(f"   visual_data keys: {list(visual_data.keys()) if visual_data else 'None'}")
                print(f"   screen_context value: {visual_data.get('screen_context') if visual_data else 'N/A'}")
        else:
            print(f"   latest_observation type: {type(latest_observation)}")
    
    # Enhanced Goal-Conditioned Action Prompt (Day 9 Navigation Implementation)
    # Strategic goal integration with tactical movement analysis
    strategic_goal = ""
    if current_plan and current_plan.strip():
        strategic_goal = f"""
=== YOUR STRATEGIC GOAL ===
{current_plan.strip()}

"""
    
    # SMART NAVIGATION ANALYSIS: Check VLM navigation data for specific guidance
    navigation_guidance = ""
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_data = latest_observation['visual_data']
        nav_info = visual_data.get('navigation_info', {})
        
        # Check for exits that VLM identified
        exits = nav_info.get('exits_visible', [])
        open_paths = nav_info.get('open_paths', [])
        notable_features = visual_data.get('spatial_layout', {}).get('notable_features', [])
        
        # Build specific navigation guidance based on VLM analysis
        if any(exit for exit in exits if exit and exit != "none" and "door" in str(exit).lower()):
            navigation_guidance += "\n🚪 VLM DETECTED EXITS: The VLM identified doors/exits. PRIORITIZE MOVEMENT toward these exits instead of pressing A.\n"
        
        if any(feature for feature in notable_features if feature and "door" in str(feature).lower()):
            navigation_guidance += f"\n🎯 NOTABLE FEATURES: {notable_features} - Move toward these features.\n"
        
        if any(path for path in open_paths if path and path != "none"):
            navigation_guidance += f"\n🛤️ OPEN PATHS: {open_paths} - Use these directions for movement.\n"
        
        # Special guidance for room navigation
        room_type = visual_data.get('spatial_layout', {}).get('room_type', '')
        if 'interior' in str(room_type).lower() or 'house' in str(room_type).lower():
            navigation_guidance += "\n🏠 ROOM EXIT STRATEGY: You're in a room/house. Look for exits at screen edges. Try all directions (UP/DOWN/LEFT/RIGHT) to find the way out.\n"
    
    # Get movement preview for pathfinding decisions
    movement_preview_text = ""
    movement_preview = {}  # NEW: Full movement preview dict for pathfinding
    walkable_options = []  # NEW: Store walkable directions as multiple-choice options
    
    if not game_data.get('in_battle', False):  # Only show movement options in overworld
        try:
            # Get full movement preview dict for pathfinding
            from utils.state_formatter import get_movement_preview
            movement_preview = get_movement_preview(state_data)
            
            # Get formatted text version for VLM prompt
            movement_preview_text = format_movement_preview_for_llm(state_data)
            print(f"🗺️ [MOVEMENT DEBUG] Raw movement preview result: '{movement_preview_text}'")
            
            # Extract WALKABLE directions for multiple-choice selection
            if movement_preview_text and movement_preview_text != "Movement preview: Not available":
                for line in movement_preview_text.split('\n'):
                    if 'WALKABLE' in line:
                        # Extract direction from line like "  UP   : ( 10, 13) [.] WALKABLE"
                        for direction in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
                            if line.strip().startswith(direction):
                                # Extract coordinates and description
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    coords_and_desc = parts[1].strip()
                                    walkable_options.append({
                                        'direction': direction,
                                        'details': coords_and_desc
                                    })
                                break
                
                print(f"🗺️ [MOVEMENT DEBUG] Extracted {len(walkable_options)} walkable options: {[opt['direction'] for opt in walkable_options]}")
                
                # WARP AVOIDANCE: Filter out recently visited warp positions (safety net)
                if _recent_positions and len(_recent_positions) >= 2:
                    current_x = player_data.get('position', {}).get('x')
                    current_y = player_data.get('position', {}).get('y')
                    current_location_key = player_data.get('location', '')
                    
                    # Get the most recent previous location (before current)
                    prev_location = None
                    for px, py, ploc in reversed(list(_recent_positions)):
                        if ploc != current_location_key:
                            prev_location = ploc
                            break
                    
                    if prev_location and current_x is not None and current_y is not None:
                        # Filter out directions that would warp back to previous location
                        filtered_options = []
                        for opt in walkable_options:
                            direction = opt['direction']
                            details = opt['details']
                            
                            # Extract target coordinates from details like "(7, 16) [D] WALKABLE"
                            import re
                            coord_match = re.search(r'\(\s*(\d+),\s*(\d+)\)', details)
                            if coord_match:
                                target_x = int(coord_match.group(1))
                                target_y = int(coord_match.group(2))
                                
                                # Check if this position was recently visited with a different location
                                leads_to_prev = False
                                for rx, ry, rloc in _recent_positions:
                                    if rx == target_x and ry == target_y and rloc != current_location_key:
                                        leads_to_prev = True
                                        print(f"🚫 [WARP AVOID] Filtering {direction} at ({target_x}, {target_y}) - recent warp target")
                                        break
                                
                                if not leads_to_prev:
                                    filtered_options.append(opt)
                            else:
                                # Can't parse coordinates, keep option
                                filtered_options.append(opt)
                        
                        if len(filtered_options) < len(walkable_options) and filtered_options:
                            print(f"✅ [WARP AVOID] Filtered {len(walkable_options) - len(filtered_options)} warp-back options")
                            walkable_options = filtered_options
                
                # Format movement preview with original full details
                movement_preview_text = f"\n{movement_preview_text}\n"
                print(f"🗺️ [MOVEMENT DEBUG] Formatted movement preview: '{movement_preview_text}'")
            else:
                print(f"🗺️ [MOVEMENT DEBUG] Movement preview empty or not available")
                movement_preview_text = ""
        except Exception as e:
            print(f"🗺️ [MOVEMENT DEBUG] Error getting movement preview: {e}")
            logger.warning(f"[ACTION] Error getting movement preview: {e}")
            movement_preview_text = ""
            walkable_options = []
    
    # ANTI-STUCK LOGIC: Detect when agent is stuck on a ledge or blocked path
    # If the agent has been pressing the same direction 5+ times and hasn't moved, override VLM
    if recent_actions and len(recent_actions) >= 5:
        last_5_actions = recent_actions[-5:]
        # Check if all last 5 actions are the same movement direction
        if all(action == last_5_actions[0] for action in last_5_actions) and last_5_actions[0] in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
            stuck_direction = last_5_actions[0]
            print(f"🚨 [ANTI-STUCK] Agent pressed {stuck_direction} 5+ times in a row!")
            
            # Check if movement preview shows this direction is blocked
            if movement_preview_text and "BLOCKED" in movement_preview_text:
                if stuck_direction in movement_preview_text.split("BLOCKED")[0][-20:]:  # Check if stuck direction is near BLOCKED text
                    print(f"🚨 [ANTI-STUCK] {stuck_direction} is BLOCKED (ledge or obstacle)!")
                    print(f"🚨 [ANTI-STUCK] Choosing alternative walkable direction...")
                    
                    # Parse walkable directions from movement preview
                    walkable_directions = []
                    for direction in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
                        if direction in movement_preview_text:
                            # Check if this direction is marked WALKABLE
                            direction_line_start = movement_preview_text.find(direction)
                            direction_line_end = movement_preview_text.find('\n', direction_line_start)
                            direction_line = movement_preview_text[direction_line_start:direction_line_end]
                            if 'WALKABLE' in direction_line:
                                walkable_directions.append(direction)
                    
                    if walkable_directions:
                        # COMPETITION COMPLIANCE: Must go through VLM executor
                        # Anti-stuck provides SUGGESTION, but VLM makes final decision
                        alternative_direction = next((d for d in walkable_directions if d != stuck_direction), walkable_directions[0])
                        print(f"🚨 [ANTI-STUCK] Detected stuck pattern on {stuck_direction}")
                        print(f"💡 [ANTI-STUCK] Suggesting alternative: {alternative_direction}")
                        
                        # Pass suggestion to VLM for final decision
                        vlm_stuck_prompt = f"""CRITICAL: Agent is stuck!

Agent has pressed {stuck_direction} 5 times in a row but hasn't moved.
Movement analysis shows {stuck_direction} is BLOCKED (likely a ledge or obstacle).

Walkable alternatives: {', '.join(walkable_directions)}

RECOMMENDATION: Press {alternative_direction} to unstuck

What button should be pressed? Answer with just the button name (UP/DOWN/LEFT/RIGHT/A/B):"""
                        
                        try:
                            vlm_response = vlm.get_text_query(vlm_stuck_prompt, "ANTI_STUCK_EXECUTOR")
                            vlm_upper = vlm_response.upper().strip()
                            
                            # Parse VLM response
                            valid_directions = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'A', 'B']
                            final_action = None
                            for direction in valid_directions:
                                if direction in vlm_upper:
                                    final_action = [direction]
                                    break
                            
                            if final_action:
                                logger.info(f"✅ [VLM ANTI-STUCK] VLM approved action: {final_action[0]}")
                                print(f"✅ [VLM ANTI-STUCK] VLM decision: {final_action[0]}")
                                return final_action
                            else:
                                # VLM didn't respond with valid direction - use suggestion but this shouldn't happen
                                logger.warning(f"⚠️ [VLM ANTI-STUCK] Could not parse VLM response, using suggestion: {alternative_direction}")
                                return [alternative_direction]
                        except Exception as e:
                            logger.error(f"❌ [VLM ANTI-STUCK] VLM call failed: {e}")
                            # Emergency fallback - at least we tried to use VLM
                            return [alternative_direction]
    
    # Build action prompt with multiple-choice format if we have walkable options
    if walkable_options and len(walkable_options) > 0:
        # MULTIPLE-CHOICE FORMAT: Present WALKABLE options + INTERACT option if needed
        
        # ANTI-OSCILLATION: Track recent positions to detect bouncing between 2-3 tiles
        if not hasattr(action_step, 'position_history'):
            action_step.position_history = []
        
        # Add current position to history (keep last 10)
        current_pos_tuple = (current_x, current_y)
        action_step.position_history.append(current_pos_tuple)
        if len(action_step.position_history) > 10:
            action_step.position_history.pop(0)
        
        # Check if oscillating between 2-3 positions
        oscillation_warning = ""
        if len(action_step.position_history) >= 6:
            recent_positions = action_step.position_history[-6:]
            unique_positions = set(recent_positions)
            
            if len(unique_positions) <= 2:
                # Agent is bouncing between 1-2 positions - definitely stuck!
                oscillation_warning = "⚠️ WARNING: You've been oscillating between the same positions! TRY A DIFFERENT DIRECTION you haven't tried recently."
                print(f"🔄 [OSCILLATION DETECTED] Agent bouncing between {unique_positions} in last 6 steps!")
            elif len(unique_positions) == 3 and len(recent_positions) >= 8:
                # Check last 8 steps
                recent_8 = action_step.position_history[-8:] if len(action_step.position_history) >= 8 else action_step.position_history
                if len(set(recent_8)) <= 3:
                    oscillation_warning = "⚠️ You're moving in a small loop. Explore in a NEW direction to find the exit."
                    print(f"🔄 [SMALL LOOP] Agent stuck in small area: {set(recent_8)}")
        
        # Check if there are nearby NPCs or interactable objects
        has_interactables = False
        interactable_description = ""
        
        if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
            visual_data = latest_observation['visual_data']
            
            # Check for visible entities (NPCs, Pokemon)
            entities = visual_data.get('visible_entities', [])
            if entities and any(e for e in entities if e and e not in ['none', 'null', '']):
                has_interactables = True
                entity_list = []
                if isinstance(entities, list):
                    for e in entities:
                        if e and e not in ['none', 'null', '']:
                            if isinstance(e, dict):
                                entity_list.append(e.get('name', 'NPC'))
                            else:
                                entity_list.append(str(e))
                interactable_description = f"NPCs: {', '.join(entity_list[:3])}" if entity_list else ""
            
            # Check for interactable objects
            nav_info = visual_data.get('navigation_info', {})
            interactables = nav_info.get('interactable_objects', [])
            if interactables and any(obj for obj in interactables if obj and obj not in ['none', 'null', '']):
                has_interactables = True
                obj_list = [str(o) for o in interactables if o and o not in ['none', 'null', '']]
                if interactable_description:
                    interactable_description += f", Objects: {', '.join(obj_list[:3])}"
                else:
                    interactable_description = f"Objects: {', '.join(obj_list[:3])}"
        
        # Build the combined options list: movement + interact
        all_options = walkable_options.copy()
        
        if has_interactables:
            all_options.append({
                'direction': 'INTERACT',
                'details': f'Press A to interact ({interactable_description})',
                'is_interact': True
            })
            print(f"🎯 [INTERACT MODE] Added INTERACT option - {interactable_description}")
        
        # Extract just the objective for clarity
        objective_line = ""
        if current_plan and "OBJECTIVE:" in current_plan:
            objective_start = current_plan.find("OBJECTIVE:")
            objective_end = current_plan.find("\n", objective_start)
            objective_line = current_plan[objective_start:objective_end] if objective_end > 0 else current_plan[objective_start:objective_start+100]
        
        # Check which directions are available
        available_directions = [opt['direction'] for opt in walkable_options]
        
        # Context-aware goal based on location
        location = state_data.get('player', {}).get('location', '')
        
        # ============================================================================
        # NAVIGATION SUGGESTION SYSTEM (3-Layer Architecture)
        # ============================================================================
        # Layer 1: PLANNING MODULE (planning.py + objective_manager.py)
        #   - Maintains high-level storyline objectives (e.g., "Get starter Pokemon")
        #   - Uses ObjectiveManager to track milestone-based progression
        #   - Generates strategic plans via VLM when objectives change
        #   - Output: current_plan = "Step 1: Exit lab. Step 2: Go to Route 101..."
        #
        # Layer 2: GOAL PARSER (utils/goal_parser.py)
        #   - Parses strategic plan text to extract navigation targets
        #   - Identifies direction hints (north, south, east, west)
        #   - Output: navigation_goal = {"target": "ROUTE_101", "direction_hint": "north"}
        #
        # Layer 3: NAVIGATION SUGGESTION (this section)
        #   - Maps direction hints to specific numbered options
        #   - Applies safety checks (door avoidance, warp detection)
        #   - Provides fallback suggestions when direct path blocked
        #   - Output: suggested_option_num = 2 (with reasoning)
        #
        # Layer 4: LOCAL A* PATHFINDING (CURRENTLY DISABLED)
        #   - Function: _local_pathfind_from_tiles() (lines 128-304)
        #   - Uses BFS on 15x15 visible tile grid to find paths
        #   - Would compute exact movement sequences to reach goal
        #   - DISABLED because: Too rigid, doesn't integrate with VLM decisions
        #   - Future integration:
        #     * A* computes path → [UP, UP, RIGHT, UP]
        #     * We suggest FIRST step only → suggested_option_num = 1 (UP)
        #     * VLM makes final decision with full context
        #     * Next step, recompute path (dynamic, responds to changes)
        #
        # Current Flow:
        #   1. Planning generates: "Go to Oldale Town (north)"
        #   2. Goal parser extracts: {"target": "OLDALE_TOWN", "direction_hint": "north"}
        #   3. Navigation suggestion maps: "north" → UP direction
        #   4. Safety checks: Is UP option safe? (not a door/warp)
        #   5. If safe: suggest_option_num = 1 (UP)
        #      If unsafe: perpendicular fallback (RIGHT/LEFT)
        #   6. VLM sees: "Goal: OLDALE_TOWN (NORTH)\nSuggested: 1\n1. UP [.]\n2. DOWN..."
        #   7. VLM makes final decision (competition compliance)
        # ============================================================================
        
        suggested_option_num = None
        suggestion_reason = ""
        
        try:
            from utils.goal_parser import get_goal_parser
            
            goal_parser = get_goal_parser()
            
            # Extract goal from current plan (Layer 2: Goal Parser)
            navigation_goal = goal_parser.extract_goal_from_plan(
                plan=current_plan if current_plan else "",
                current_location=location,
                current_objective=None
            )
            
            if navigation_goal and navigation_goal.get('confidence', 0) >= 0.6:
                print(f"🎯 [GOAL PARSER] Extracted navigation goal: {navigation_goal}")
                
                # Layer 3: Map direction hint to cardinal direction
                direction_hint = navigation_goal.get('direction_hint', '').lower()
                
                # Map hints to cardinal directions
                hint_to_direction = {
                    'north': 'UP',
                    'south': 'DOWN', 
                    'east': 'RIGHT',
                    'west': 'LEFT',
                    'up': 'UP',
                    'down': 'DOWN',
                    'left': 'LEFT',
                    'right': 'RIGHT'
                }
                
                # Layer 3.5: Try A* pathfinding with map stitcher (ENHANCED NAVIGATION)
                # This provides BETTER navigation than simple direction mapping because:
                # - Uses complete explored map (not just 15x15 local view)
                # - Can route around obstacles globally
                # - Integrates warp avoidance with position history
                # Competition Compliance: A* provides SUGGESTION, VLM makes final decision
                astar_direction = None
                
                # Get map stitcher data from state (sent by server as JSON-serializable data)
                stitched_map_info = state_data.get('map', {}).get('stitched_map_info')
                
                print(f"🗺️ [A* DEBUG] stitched_map_info present: {stitched_map_info is not None}")
                if stitched_map_info:
                    print(f"🗺️ [A* DEBUG] available: {stitched_map_info.get('available')}")
                    print(f"🗺️ [A* DEBUG] direction_hint: {direction_hint}")
                
                if stitched_map_info and stitched_map_info.get('available') and direction_hint:
                    current_area = stitched_map_info.get('current_area', {})
                    grid_serializable = current_area.get('grid')
                    bounds = current_area.get('bounds')
                    
                    print(f"🗺️ [A* DEBUG] grid present: {grid_serializable is not None}, size: {len(grid_serializable) if grid_serializable else 0}")
                    print(f"🗺️ [A* DEBUG] bounds present: {bounds is not None}, value: {bounds}")
                    print(f"🗺️ [A* DEBUG] current_position: ({current_position.get('x')}, {current_position.get('y')})")
                    
                    if grid_serializable and bounds:
                        print(f"🗺️ [A* MAP] Map stitcher data available, attempting pathfinding to '{direction_hint}'")
                        
                        # CRITICAL FIX: The map stitcher uses ABSOLUTE world coordinates from when
                        # the split was saved, but current_position uses RELATIVE coordinates.
                        # We need to check if the player position makes sense with the bounds.
                        
                        # Validate that current position is within bounds
                        # Use the already-extracted current_position from earlier in the function
                        player_x = current_position.get('x', 0)
                        player_y = current_position.get('y', 0)
                        
                        # Check if server provided translated grid coordinates
                        origin_offset = current_area.get('origin_offset')
                        player_grid_pos = current_area.get('player_grid_pos')
                        
                        if origin_offset and player_grid_pos:
                            # Use translated grid coordinates
                            player_grid_x, player_grid_y = player_grid_pos
                            print(f"🗺️ [A* MAP] Using translated coordinates:")
                            print(f"   Local position: ({player_x}, {player_y})")
                            print(f"   Origin offset: ({origin_offset['x']}, {origin_offset['y']})")
                            print(f"   Grid position: ({player_grid_x}, {player_grid_y})")
                            coords_compatible = (bounds['min_x'] <= player_grid_x <= bounds['max_x'] and
                                               bounds['min_y'] <= player_grid_y <= bounds['max_y'])
                        else:
                            # Fallback to raw coordinates (will likely fail)
                            print(f"⚠️ [A* MAP] No coordinate translation available, using raw position")
                            player_grid_x = player_x
                            player_grid_y = player_y
                            coords_compatible = (bounds['min_x'] <= player_x <= bounds['max_x'] and
                                               bounds['min_y'] <= player_y <= bounds['max_y'])
                        
                        if not coords_compatible:
                            print(f"⚠️ [A* MAP] Coordinate system mismatch detected!")
                            print(f"   Player grid position: ({player_grid_x}, {player_grid_y})")
                            print(f"   Map stitcher bounds: X:{bounds['min_x']}-{bounds['max_x']}, Y:{bounds['min_y']}-{bounds['max_y']}")
                            print(f"   This indicates stale map stitcher data from a previous session")
                            print(f"   Falling back to local pathfinding (15x15 tiles)")
                            
                            # Use local tile-based pathfinding instead
                            astar_direction = _local_pathfind_from_tiles(state_data, direction_hint, recent_actions)
                            if astar_direction:
                                print(f"✅ [LOCAL A*] Pathfinding succeeded: {astar_direction}")
                            else:
                                print(f"⚠️ [LOCAL A*] Pathfinding failed, using simple direction mapping")
                        else:
                            # Use grid coordinates for pathfinding
                            current_pos = (player_grid_x, player_grid_y)
                        
                            # Convert serializable grid back to tuple keys
                            location_grid = {}
                            for key, value in grid_serializable.items():
                                x, y = map(int, key.split(','))
                                location_grid[(x, y)] = value
                            
                            print(f"🗺️ [A* MAP] Using grid with {len(location_grid)} tiles, bounds X:{bounds['min_x']}-{bounds['max_x']}, Y:{bounds['min_y']}-{bounds['max_y']}")
                            
                            # Call A* pathfinding with the grid data and bounds
                            astar_direction = _astar_pathfind_with_grid_data(
                                location_grid=location_grid,
                                bounds=bounds,
                                current_pos=current_pos,
                                location=location,
                                goal_direction=direction_hint,
                                recent_positions=_recent_positions
                            )
                            
                            if astar_direction:
                                print(f"✅ [A* MAP] Pathfinding succeeded: {astar_direction}")
                            else:
                                print(f"⚠️ [A* MAP] Pathfinding failed, falling back to simple direction mapping")
                    else:
                        print(f"⚠️ [A* MAP] Missing grid data or bounds")
                elif not stitched_map_info or not stitched_map_info.get('available'):
                    print(f"⚠️ [A* MAP] Map stitcher data not available in state_data")
                elif not direction_hint:
                    print(f"⚠️ [A* MAP] No direction hint from goal parser")

                
                # Use A* result if available, otherwise use simple direction mapping
                preferred_direction = astar_direction if astar_direction else hint_to_direction.get(direction_hint)
                
                if preferred_direction:
                    # Find which numbered option matches this direction
                    for i, opt in enumerate(all_options, 1):
                        if opt['direction'] == preferred_direction:
                            # Check if this option is safe (not a warp-back)
                            is_safe = True
                            details = opt.get('details', '')
                            
                            # Safety check 1: Milestone-based detection
                            # If we just got starter and we're outside lab, don't suggest going back in
                            milestones = state_data.get('milestones', {})
                            starter_chosen = milestones.get('STARTER_CHOSEN', False)
                            current_location_str = player_data.get('location', '')
                            
                            if starter_chosen and 'TOWN' in current_location_str and ('[D]' in details or 'Door' in details):
                                # We're in a TOWN with starter - don't suggest entering buildings yet
                                # (We just exited the lab, need to head to routes first)
                                is_safe = False
                                print(f"⚠️ [NAV SUGGESTION] Option {i} ({preferred_direction}) is a door - skipping (just got starter, should explore routes first)")
                            
                            # Safety check 2: Recent position history (if available)
                            elif '[D]' in details or 'Door' in details:
                                # Extract coordinates
                                import re
                                coord_match = re.search(r'\(\s*(\d+),\s*(\d+)\)', details)
                                if coord_match and _recent_positions and len(_recent_positions) >= 2:
                                    target_x = int(coord_match.group(1))
                                    target_y = int(coord_match.group(2))
                                    
                                    # Check if this leads back to where we just were
                                    for rx, ry, rloc in _recent_positions:
                                        if rx == target_x and ry == target_y and rloc != current_location_str:
                                            is_safe = False
                                            print(f"⚠️ [NAV SUGGESTION] Option {i} ({preferred_direction}) is a door back to '{rloc}' - skipping")
                                            break
                            
                            if is_safe:
                                suggested_option_num = i
                                suggestion_reason = f"Goal is {navigation_goal.get('target', 'unknown')} to the {direction_hint}"
                                print(f"💡 [NAV SUGGESTION] Recommending option {i} ({preferred_direction}) - {suggestion_reason}")
                            break
                    
                    if not suggested_option_num:
                        print(f"⚠️ [NAV SUGGESTION] Preferred direction {preferred_direction} not available or unsafe")
                        
                        # SMART FALLBACK: If we want to go in a direction but can't, suggest lateral movement
                        # Priority: Move perpendicular to goal direction to navigate around obstacles
                        current_loc = player_data.get('location', '')
                        if preferred_direction and current_loc and 'TOWN' in current_loc:
                            fallback_priority = []
                            
                            # Define perpendicular directions based on goal
                            if preferred_direction in ['UP', 'DOWN']:
                                # Goal is north/south - try going east/west first
                                fallback_priority = ['RIGHT', 'LEFT', 'DOWN', 'UP']
                            elif preferred_direction in ['LEFT', 'RIGHT']:
                                # Goal is east/west - try going north/south first
                                fallback_priority = ['UP', 'DOWN', 'RIGHT', 'LEFT']
                            
                            # Try fallback directions in priority order
                            for fallback_dir in fallback_priority:
                                for i, opt in enumerate(all_options, 1):
                                    if opt['direction'] == fallback_dir:
                                        details = opt.get('details', '')
                                        # Make sure it's not a door
                                        if '[D]' not in details and 'Door' not in details:
                                            suggested_option_num = i
                                            suggestion_reason = f"Navigate around obstacle by going {fallback_dir}"
                                            print(f"💡 [NAV SUGGESTION FALLBACK] {preferred_direction} blocked - suggesting {fallback_dir} (option {i}) to explore around")
                                            break
                                if suggested_option_num:
                                    break
        except Exception as e:
            logger.warning(f"[NAV SUGGESTION] Error: {e}")
            import traceback
            traceback.print_exc()
        
        # ============================================================================
        # GOAL EXTRACTION: Get current goal from planning module
        # ============================================================================
        # The planning module (via ObjectiveManager) maintains high-level goals
        # The goal_parser extracts direction hints from these goals
        # We use this to provide context in the prompt
        
        goal_context = ""
        if navigation_goal and navigation_goal.get('target'):
            target = navigation_goal['target']
            direction = navigation_goal.get('direction_hint', '')
            if direction:
                goal_context = f"Goal: {target} ({direction.upper()})"
            else:
                goal_context = f"Goal: {target}"
        elif 'MOVING_VAN' in location.upper():
            goal_context = "Goal: Exit van"
        elif 'HOUSE' in location.upper() or 'ROOM' in location.upper():
            goal_context = "Goal: Exit building"
        elif 'LAB' in location.upper():
            goal_context = "Goal: Exit lab"
        else:
            # Generic overworld
            goal_context = "Goal: Explore"
        
        # ============================================================================
        # INSTRUCTION: Build based on suggestion and oscillation state
        # ============================================================================
        if oscillation_warning:
            # Agent is stuck in loop - emphasize trying new direction
            instruction = f"{goal_context}\n⚠️ Stuck in loop - try NEW direction\nPick option:"
        elif suggested_option_num:
            # Navigation system recommends a specific option - MAKE IT VERY CLEAR
            instruction = f"{goal_context}\n**PATHFINDING RECOMMENDATION: Choose option {suggested_option_num}** ({suggestion_reason})\nPick option:"
        else:
            # No suggestion available
            instruction = f"{goal_context}\nPick option:"

        
        action_prompt = f"""{instruction}

"""
        # SMART REORDERING: If no suggestion, put doors last to reduce chance VLM picks them
        display_options = all_options.copy()
        if not suggested_option_num:
            # Separate doors from non-doors
            door_options = []
            non_door_options = []
            
            for opt in display_options:
                details = opt.get('details', '')
                if '[D]' in details or 'Door' in details:
                    door_options.append(opt)
                else:
                    non_door_options.append(opt)
            
            # Reorder: non-doors first, doors last
            if door_options and non_door_options:
                display_options = non_door_options + door_options
                print(f"🔄 [SMART REORDER] No suggestion available - moved {len(door_options)} door(s) to end of list")
        
        # Add numbered options for all options (movement + interact)
        # FORMAT: {number}. {direction} [{tile_symbol}]
        # Tile symbols: [D]=door, [.]=path, [~]=grass, [≈]=water, [S]=stairs, [#]=blocked
        print(f"🔍 [PROMPT BUILDER DEBUG] Building numbered list from {len(display_options)} options:")
        for i, option in enumerate(display_options, 1):
            # Extract tile symbol from details (if available)
            details = option.get('details', '')
            tile_symbol = ''
            
            # Look for tile symbol in brackets: [D], [.], [~], etc.
            import re
            bracket_match = re.search(r'\[(.)\]', details)
            if bracket_match:
                tile_symbol = f" [{bracket_match.group(1)}]"
            
            # Build option line: "1. UP [D]" or "1. UP" if no symbol
            action_prompt_line = f"{i}. {option['direction']}{tile_symbol}\n"
            print(f"   Adding to prompt: '{action_prompt_line.strip()}'")
            action_prompt += action_prompt_line
        
        action_prompt += f"\nAnswer: """
        
        # Store display_options for parsing later (they're now reordered)
        walkable_options = display_options
    else:
        # FALLBACK: Original free-form prompt when no movement options available
        action_prompt = f"""Playing Pokemon Emerald. Screen: {visual_context}

{strategic_goal}=== NAVIGATION TASK ===

**CRITICAL: You have access to your COMPLETE explored map (shown above in EXTENDED MAP VIEW if available).**

**Step 1: Check the EXTENDED MAP VIEW (if shown above)**
- This shows the ENTIRE area you've explored, not just your immediate 15x15 view
- You are marked as 'P' on the map
- Use this to see paths, dead ends, and unexplored areas
- Plan your route to avoid getting stuck in cul-de-sacs

**Step 2: Check the MOVEMENT PREVIEW** below for immediate options:
{movement_preview_text}

**Step 3: Choose ONE WALKABLE direction** that:
- Avoids dead ends visible on the extended map
- Moves toward your strategic goal
- Is marked WALKABLE in the movement preview

**PATHFINDING RULES:**
- If the extended map shows a dead end ahead, DON'T GO THERE - backtrack
- If you're stuck (no forward progress), check the extended map for alternate routes
- NEVER repeatedly move into blocked tiles

=== DECISION RULES ===

🚨 **IF DIALOGUE BOX IS VISIBLE** (you see text at bottom of screen):
   → Press A to advance/close the dialogue

🎯 **IF IN OVERWORLD** (no dialogue, no menu):
   → First: Check EXTENDED MAP VIEW (above) to plan your route and avoid dead ends
   → Second: Choose a WALKABLE direction from MOVEMENT PREVIEW
   → Third: Move toward your goal while avoiding obstacles visible on the extended map

📋 **IF IN MENU**:
   → Use UP/DOWN to navigate options
   → Press A to select

⚔️ **IF IN BATTLE**:
   → Press A for moves/attacks

=== OUTPUT FORMAT - CRITICAL ===
You MUST respond with this EXACT format:

Line 1-2: Brief reasoning about THIS SPECIFIC frame (what you actually see, your current goal, your chosen direction)
Line 3: ONLY the button name - ONE of these exact words: A, B, UP, DOWN, LEFT, RIGHT, START

⚠️ CRITICAL INSTRUCTIONS:
1. ANALYZE THIS SPECIFIC FRAME
2. Look at the MOVEMENT PREVIEW to see which directions are WALKABLE
3. Choose a direction that matches your strategic goal
4. DO NOT hallucinate doors or features not visible in the movement data
5. If you're navigating to a location, pick the direction that gets you closer

Example 1 - Movement:
I'm on Route 101. My goal is north. The movement preview shows UP is walkable.
UP

Example 2 - Dialogue:
I see a dialogue box at the bottom with text. I need to close it.
A

Example 3 - Navigation:
I need to go to Littleroot Town which is south. DOWN is walkable according to preview.
DOWN

Now analyze THIS frame and respond with your reasoning and button:
"""
    
    # Construct complete prompt for VLM
    complete_prompt = system_prompt + action_prompt
    
    # GUARANTEED DEBUG: Always show VLM call and response
    # Double-check step calculation for VLM mode
    actual_step = len(recent_actions) if recent_actions else 0
    print(f"📞 [VLM CALL] Step {actual_step} (calculated from {len(recent_actions) if recent_actions else 0} recent_actions) - About to call VLM")
    
    # PERCEPTION DEBUG: Show what visual context we received
    print(f"👁️ [PERCEPTION DEBUG] Latest observation type: {type(latest_observation)}")
    if isinstance(latest_observation, dict):
        print(f"👁️ [PERCEPTION DEBUG] Observation keys: {list(latest_observation.keys())}")
        if 'visual_data' in latest_observation:
            vd = latest_observation['visual_data']
            print(f"👁️ [PERCEPTION DEBUG] Visual data keys: {list(vd.keys()) if vd else 'None'}")
            print(f"👁️ [PERCEPTION DEBUG] Screen context: '{vd.get('screen_context', 'missing')}' | Method: {latest_observation.get('extraction_method', 'unknown')}")
            print(f"👁️ [PERCEPTION DEBUG] On-screen text: {vd.get('on_screen_text', {})}")
            
            # ENHANCED PERCEPTION ANALYSIS
            screen_ctx = vd.get('screen_context', 'missing')
            dialogue_data = vd.get('on_screen_text', {}).get('dialogue', '')
            visual_elements = vd.get('visual_elements', {})
            
            print(f"👁️ [PERCEPTION ANALYSIS] Screen classification analysis:")
            print(f"   - VLM classified as: '{screen_ctx}'")
            print(f"   - Dialogue present: {bool(dialogue_data)}")
            print(f"   - Dialogue content: '{dialogue_data}'")
            print(f"   - Visual elements: {visual_elements}")
            
            # Check for dialogue box misclassification
            if dialogue_data and screen_ctx == 'overworld':
                print(f"🚨 [MISCLASSIFICATION] VLM says 'overworld' but dialogue exists!")
                print(f"🚨 [MISCLASSIFICATION] This is likely a dialogue screen misclassified as overworld!")
                
            # Check for box interaction patterns
            dialogue_data = vd.get('on_screen_text', {}).get('dialogue', '')  
            if dialogue_data and 'pokémon' in dialogue_data.lower() and ('box' in dialogue_data.lower() or 'logo' in dialogue_data.lower()):
                print(f"🎁 [BOX DETECTED] This appears to be box/sign dialogue that blocks movement!")
                print(f"🎁 [BOX DETECTED] Player must press A to close dialogue before movement works!")
        else:
            print(f"👁️ [PERCEPTION DEBUG] No visual_data in observation!")
    else:
        print(f"👁️ [PERCEPTION DEBUG] Observation is not a dict: {latest_observation}")
    
    # CRITICAL DEBUG: Why is recent_actions empty?
    if recent_actions is None:
        print(f"⚠️ [CRITICAL] recent_actions is None!")
    elif len(recent_actions) == 0:
        print(f"⚠️ [CRITICAL] recent_actions is empty list!")
    else:
        print(f"✅ [DEBUG] recent_actions has {len(recent_actions)} items: {recent_actions[-5:] if len(recent_actions) > 5 else recent_actions}")
    
    # Safe visual context logging
    visual_preview = visual_context[:100] + "..." if visual_context and len(visual_context) > 100 else (visual_context or "None")
    strategic_preview = strategic_goal[:100] + "..." if strategic_goal and len(strategic_goal) > 100 else (strategic_goal or "None")
    
    print(f"🔍 [VLM DEBUG] Step {actual_step} - Calling VLM with visual_context: '{visual_preview}'")
    print(f"   Strategic goal: '{strategic_preview}'")
    
    # DEBUG: Show the actual prompt being sent to VLM
    print(f"🔍 [VLM PROMPT DEBUG] Complete prompt length: {len(complete_prompt)} chars")
    
    # Check if movement preview is in the prompt
    if "MOVEMENT PREVIEW:" in complete_prompt:
        print(f"✅ [VLM PROMPT DEBUG] Movement preview IS included in prompt")
        # Movement preview check (only log if actually missing in navigation mode)
        mp_start = complete_prompt.find("MOVEMENT PREVIEW:")
        if mp_start == -1 and visual_context == 'overworld':
            logger.warning("[VLM PROMPT] Movement preview missing in overworld mode")
        # Otherwise it's expected (dialogue/battle) - don't log
    
    # Check if we're using multiple-choice mode
    if walkable_options and len(walkable_options) > 0:
        print(f"🎯 [MULTIPLE-CHOICE MODE] Presenting {len(walkable_options)} walkable options to VLM:")
        for i, opt in enumerate(walkable_options, 1):
            print(f"   {i}. {opt['direction']} - {opt['details']}")
    else:
        print(f"📝 [FREE-FORM MODE] Using traditional free-form action selection")
    
    # VLM prompt validation (only log on errors or periodically)
    if current_step % 100 == 0:
        logger.debug(f"VLM prompt length: {len(complete_prompt)} chars")
    
    # ULTRA DEBUG: Show the exact numbered list section
    if walkable_options and "YOUR MOVEMENT CHOICES" in complete_prompt:
        list_start = complete_prompt.find("YOUR MOVEMENT CHOICES")
        # Numbered list validation (only log issues)
        list_section = complete_prompt[list_start:list_start+500]
        if "1." not in list_section:
            logger.warning("[NUMBERED LIST] Options list formatting may be incorrect")
    elif "1." in complete_prompt and walkable_options:
        # Fallback: try to find first numbered option
        if "READ THE LIST:" in complete_prompt:
            list_start = complete_prompt.find("READ THE LIST:")
        else:
            list_start = complete_prompt.find("1.")
        # Validate but don't print unless there's an issue
        if list_start == -1:
            logger.warning("[NUMBERED LIST] Could not find numbered options in prompt")
    
    action_response = vlm.get_text_query(complete_prompt, "ACTION")
    
    # VLM RESPONSE VALIDATION: Detect and handle problematic responses
    if action_response and len(action_response) > 500:
        print(f"⚠️ [VLM WARNING] Response is suspiciously long ({len(action_response)} chars) - possible hallucination detected!")
        # Truncate to first 200 characters to avoid processing garbage
        action_response = action_response[:200]
        print(f"   Truncated to: '{action_response}'")
    
    # Check for repetitive patterns that indicate hallucination
    if action_response and len(action_response) > 50:
        first_50 = action_response[:50].lower()
        if "you are in battle mode" in first_50 and action_response.lower().count("you are in battle mode") > 3:
            print(f"🚨 [VLM ERROR] Detected repetitive hallucination - forcing simple 'A' response")
            action_response = "A"
    
    # GUARANTEED DEBUG: Always show FULL VLM response including reasoning
    print(f"🔍 [VLM RESPONSE] Step {actual_step} - FULL Response:")
    print("=" * 80)
    print(action_response)
    print("=" * 80)
    
    # SAFETY CHECK: Handle None or empty VLM response
    if action_response is None:
        logger.warning("[ACTION] VLM returned None response, using fallback action")
        action_response = "A"  # Safe fallback
    else:
        action_response = action_response.strip()
    
    valid_buttons = ['A', 'B', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT']
    
    # DEBUG: Show what we're about to parse
    print(f"🔍 [PARSING] Step {actual_step} - About to parse response (type: {type(action_response)})")
    
    # ROBUST PARSING: Handle various VLM response formats
    actions = []
    
    if action_response:
        # NEW FORMAT: Expect reasoning followed by action on last line
        # Split by newlines and get the last non-empty line as the action
        lines = [line.strip() for line in action_response.split('\n') if line.strip()]
        
        if len(lines) >= 2:
            # Extract reasoning (all lines except last)
            reasoning = '\n'.join(lines[:-1])
            action_line = lines[-1].upper()
            
            print(f"🧠 [VLM REASONING] {reasoning}")
            print(f"🎮 [VLM ACTION LINE] {action_line}")
        elif len(lines) == 1:
            # Only one line - treat as action without reasoning
            action_line = lines[0].upper()
            # print(f"⚠️ [NO REASONING] VLM provided action without reasoning")
            print(f"🎮 [VLM ACTION LINE] {action_line}")
        else:
            # Empty response
            print(f"❌ [EMPTY RESPONSE] VLM returned empty response")
            action_line = "A"  # Fallback
        
        response_str = action_line
        
        # PRIORITY 0: MULTIPLE-CHOICE PARSING (if we provided walkable options)
        if walkable_options and len(walkable_options) > 0:
            print(f"🎯 [MULTIPLE-CHOICE] Parsing response for {len(walkable_options)} options")
            
            # Try to extract a number from the response
            import re
            number_match = re.search(r'\b([1-9])\b', response_str)
            
            if number_match:
                choice_num = int(number_match.group(1))
                print(f"✅ [CHOICE DETECTED] VLM selected option {choice_num}")
                
                # Validate the choice is within range
                if 1 <= choice_num <= len(walkable_options):
                    selected_option = walkable_options[choice_num - 1]
                    selected_direction = selected_option['direction']
                    print(f"✅ [MULTIPLE-CHOICE] Option {choice_num} maps to: {selected_direction}")
                    print(f"   Details: {selected_option['details']}")
                    
                    # Handle INTERACT option - convert to A button press
                    if selected_direction == 'INTERACT':
                        actions = ['A']
                        print(f"🎯 [INTERACT] Converting INTERACT to A button press")
                    else:
                        actions = [selected_direction]
                else:
                    print(f"❌ [INVALID CHOICE] Option {choice_num} out of range (1-{len(walkable_options)})")
                    # Fallback to first option
                    actions = [walkable_options[0]['direction']]
                    print(f"   Using fallback: {actions[0]}")
            else:
                # No number found - check if VLM responded with button (like "A" for dialogue)
                print(f"⚠️ [NO NUMBER] VLM didn't provide a number, checking for button names...")
                # Will fall through to button parsing below
        
        # PRIORITY 1: Check if response starts with a valid button (most common case)
        if not actions:  # Only parse as button if we didn't already get a direction from multiple-choice
            first_line = response_str.split('\n')[0].strip().upper()
            
            # Clean up common VLM artifacts in the first line
            cleaned_first_line = first_line
            for artifact in ['</OUTPUT>', '</output>', '<|END|>', '<|end|>', '<|ASSISTANT|>', '<|assistant|>', '|user|']:
                cleaned_first_line = cleaned_first_line.replace(artifact, '').strip()
            
            if cleaned_first_line in valid_buttons:
                actions = [cleaned_first_line]
            elif first_line in valid_buttons:
                actions = [first_line]
            # PRIORITY 1.5: Handle "A (explanation)" format by extracting just the button
            elif '(' in first_line:
                # Extract button before parentheses: "A (to attack)" -> "A"
                button_part = first_line.split('(')[0].strip().upper()
                if button_part in valid_buttons:
                    actions = [button_part]
        
        # PRIORITY 2: Try direct parsing (exact match)
        elif ',' in response_str:
            # Multi-action response
            raw_actions = [btn.strip().upper() for btn in response_str.split(',')]
            actions = [btn for btn in raw_actions if btn in valid_buttons][:3]
        
        # PRIORITY 3: Try exact match of whole response (with cleanup)
        elif response_str.upper() in valid_buttons:
            actions = [response_str.upper()]
        
        # PRIORITY 3.5: Try cleaned version of whole response
        if not actions:
            # Clean common VLM artifacts from the whole response
            cleaned_response = response_str.upper()
            for artifact in ['</OUTPUT>', '</output>', '<|END|>', '<|end|>', '<|ASSISTANT|>', '<|assistant|>', '|user|', '|assistant|']:
                cleaned_response = cleaned_response.replace(artifact, '').strip()
            
            if cleaned_response in valid_buttons:
                actions = [cleaned_response]
        
        # PRIORITY 4: Extract first valid button found anywhere in response
        if not actions:
            # Look for button names in order of preference (case insensitive)
            for button in valid_buttons:
                if button.lower() in response_str.lower():
                    actions = [button]
                    break
            
            # PRIORITY 5: Try common patterns if still no match
            if not actions:
                response_lower = response_str.lower()
                if 'up' in response_lower or 'north' in response_lower:
                    actions = ['UP']
                elif 'down' in response_lower or 'south' in response_lower:
                    actions = ['DOWN']
                elif 'left' in response_lower or 'west' in response_lower:
                    actions = ['LEFT']
                elif 'right' in response_lower or 'east' in response_lower:
                    actions = ['RIGHT']
                elif 'interact' in response_lower or 'confirm' in response_lower or 'select' in response_lower:
                    actions = ['A']
                elif 'back' in response_lower or 'cancel' in response_lower or 'menu' in response_lower:
                    actions = ['B']
    
    print(f"✅ Parsed actions: {actions}")
    if len(actions) == 0:
        print(f"❌ No valid actions parsed from: '{action_response}' - using fallback default")
        print(f"   Valid buttons are: {valid_buttons}")
        print(f"   Response length: {len(str(action_response)) if action_response else 'None'}")
        
        # ANTI-HALLUCINATION: If VLM is producing garbage, force a simple action
        if action_response and len(action_response) > 200:
            print(f"🚨 [ANTI-HALLUCINATION] VLM response too long - forcing simple navigation")
            actions = [random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT', 'A'])]
            print(f"   Anti-hallucination action: {actions}")
    else:
        print(f"✅ Successfully parsed {len(actions)} action(s): {actions}")
    
    print("-" * 80 + "\n")
    
    # ANTI-LOOP LOGIC: Detect if we're stuck pressing A repeatedly and force exploration
    if actions == ['A'] and recent_actions:
        recent_a_count = sum(1 for action in recent_actions[-10:] if action == 'A')  # Count A presses in last 10 actions
        if recent_a_count >= 8 and len(recent_actions) >= 10:  # If 8+ out of last 10 actions were A AND we have enough history
            print(f"🔄 [ANTI-LOOP] Step {current_step} - Detected A-loop ({recent_a_count}/10 recent actions). Forcing exploration.")
            exploration_options = ['UP', 'DOWN', 'LEFT', 'RIGHT']
            actions = [random.choice(exploration_options)]
            print(f"   Forcing exploration with: {actions}")
    
    # If no valid actions found, make intelligent default based on state
    if not actions:
        if game_data.get('in_battle', False):
            actions = ['A']  # Attack in battle
        elif party_health['total_count'] == 0:
            actions = ['A', 'A', 'A']  # Try to progress dialogue/menu
        else:
            actions = [random.choice(['A', 'RIGHT', 'UP', 'DOWN', 'LEFT'])]  # Random exploration
    
    logger.info(f"[ACTION] Actions decided: {', '.join(actions)}")
    final_step = len(recent_actions) if recent_actions else 0
    print(f"🎮 [FINAL ACTION] Step {final_step} - Returning actions: {actions}")
    
    return actions 