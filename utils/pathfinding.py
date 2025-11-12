#!/usr/bin/env python3
"""
A* Pathfinding System for Pokemon Emerald Agent

Uses Map Stitcher data to plan routes within and between map areas.
Avoids warps/doors unless they are the goal, preventing accidental re-entry.
"""

import heapq
import logging
from typing import Tuple, List, Optional, Dict, Set
from utils.map_stitcher import MapStitcher

logger = logging.getLogger(__name__)


def _parse_goal_string(goal: str) -> Tuple[str, any]:
    """
    Parse goal string into type and data.
    
    Args:
        goal: Goal string like "NORTH_EDGE", "COORDINATES:15,20", "LOCATION:ROUTE_101", etc.
    
    Returns:
        Tuple of (goal_type, goal_data)
        - "EDGE", "NORTH" for "NORTH_EDGE"
        - "COORDINATES", (15, 20) for "COORDINATES:15,20"
        - "LOCATION", "ROUTE_101" for "LOCATION:ROUTE_101"
        - "EXPLORE", None for "EXPLORE"
    """
    if not goal:
        return ("UNKNOWN", None)
    
    goal = goal.strip().upper()
    
    # Edge goals
    if goal.endswith("_EDGE"):
        direction = goal.replace("_EDGE", "")
        return ("EDGE", direction)
    
    # Coordinate goals: "COORDINATES:x,y"
    if goal.startswith("COORDINATES:"):
        coords_str = goal.replace("COORDINATES:", "")
        try:
            x, y = map(int, coords_str.split(','))
            return ("COORDINATES", (x, y))
        except (ValueError, IndexError):
            logger.warning(f"[PATHFINDING] Invalid COORDINATES format: {goal}")
            return ("UNKNOWN", None)
    
    # Location goals: "LOCATION:NAME"
    if goal.startswith("LOCATION:"):
        location = goal.replace("LOCATION:", "")
        return ("LOCATION", location)
    
    # NPC goals: "NPC:NAME"
    if goal.startswith("NPC:"):
        npc = goal.replace("NPC:", "")
        return ("NPC", npc)
    
    # Simple goals
    if goal == "EXPLORE":
        return ("EXPLORE", None)
    
    # Unknown
    logger.warning(f"[PATHFINDING] Unknown goal format: {goal}")
    return ("UNKNOWN", None)


def heuristic(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
    """Manhattan distance heuristic for A*."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


def is_walkable(symbol: str, avoid_warps: bool = True) -> bool:
    """
    Check if a tile symbol is walkable.
    
    Args:
        symbol: Tile symbol from map stitcher ('.', '#', 'D', 'S', etc.)
        avoid_warps: If True, treat doors/stairs as obstacles
        
    Returns:
        True if the tile can be walked on
    """
    # Walls and water are never walkable
    if symbol in ['#', 'W', '?']:
        return False
    
    # Warps (doors/stairs) - walkable only if not avoiding them
    if symbol in ['D', 'S']:
        return not avoid_warps
    
    # Walkable terrain
    if symbol in ['.', '^', '~', 's', 'I']:  # Grass, sand, ice, etc.
        return True
    
    # Ledges - walkable (A* will handle direction restrictions)
    if symbol in ['↓', '↑', '←', '→', '↗', '↖', '↘', '↙']:
        return True
    
    # Default: treat unknown symbols as obstacles for safety
    return False


def get_neighbors(pos: Tuple[int, int], grid: Dict[Tuple[int, int], str], 
                  avoid_warps: bool = True) -> List[Tuple[int, int]]:
    """
    Get walkable neighboring positions with ledge support.
    
    Ledges are one-way: you can only traverse them in the direction they point.
    - '↓' ledge: can only move FROM this tile going DOWN (south)
    - '↑' ledge: can only move FROM this tile going UP (north)  
    - '→' ledge: can only move FROM this tile going RIGHT (east)
    - '←' ledge: can only move FROM this tile going LEFT (west)
    - Diagonal ledges ('↗', '↖', '↘', '↙'): treated as walls (impassable)
    
    Args:
        pos: Current (x, y) position
        grid: Map grid from map stitcher {(x, y): symbol}
        avoid_warps: If True, don't return warp tiles as neighbors
        
    Returns:
        List of walkable neighbor positions
    """
    x, y = pos
    neighbors = []
    current_symbol = grid.get(pos, '?')
    
    # Ledge direction mappings: ledge_symbol -> (allowed_dx, allowed_dy)
    ledge_exits = {
        '↓': (0, 1),   # Can only exit going DOWN
        '↑': (0, -1),  # Can only exit going UP
        '→': (1, 0),   # Can only exit going RIGHT
        '←': (-1, 0),  # Can only exit going LEFT
    }
    
    # If we're standing ON a ledge, we can only move in the ledge's direction
    if current_symbol in ledge_exits:
        allowed_dx, allowed_dy = ledge_exits[current_symbol]
        new_pos = (x + allowed_dx, y + allowed_dy)
        
        if new_pos in grid:
            next_symbol = grid[new_pos]
            # The landing tile must be walkable (not a wall)
            if is_walkable(next_symbol, avoid_warps=avoid_warps):
                neighbors.append(new_pos)
        
        return neighbors  # Can ONLY move in ledge direction
    
    # Not on a ledge - check all 4 cardinal directions
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:  # DOWN, UP, RIGHT, LEFT
        new_pos = (x + dx, y + dy)
        
        # Check if position exists in grid
        if new_pos not in grid:
            continue
        
        symbol = grid[new_pos]
        
        # CANNOT move ONTO diagonal ledges - they are treated as walls
        if symbol in ['↗', '↖', '↘', '↙']:
            continue
        
        # CANNOT move onto a ledge from the wrong direction
        # e.g., cannot move UP onto a '↓' ledge (it points down, not up)
        if symbol == '↓' and dy == -1:  # Can't approach from south (moving up)
            continue
        if symbol == '↑' and dy == 1:   # Can't approach from north (moving down)
            continue
        if symbol == '→' and dx == -1:  # Can't approach from east (moving left)
            continue
        if symbol == '←' and dx == 1:   # Can't approach from west (moving right)
            continue
        
        # Check if walkable
        if is_walkable(symbol, avoid_warps=avoid_warps):
            neighbors.append(new_pos)
    
    return neighbors


def reconstruct_path(came_from: Dict[Tuple[int, int], Tuple[int, int]], 
                     start: Tuple[int, int], 
                     goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    """
    Reconstruct path from A* came_from mapping.
    
    Returns:
        List of positions from start to goal (inclusive)
    """
    path = [goal]
    current = goal
    
    while current != start:
        current = came_from[current]
        path.append(current)
    
    path.reverse()
    return path


def path_to_directions(path: List[Tuple[int, int]]) -> List[str]:
    """
    Convert a path of positions to a list of directions.
    
    Args:
        path: List of (x, y) positions
        
    Returns:
        List of directions ['UP', 'RIGHT', 'DOWN', etc.]
    """
    if len(path) < 2:
        return []
    
    directions = []
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 1:
            directions.append('RIGHT')
        elif dx == -1:
            directions.append('LEFT')
        elif dy == 1:
            directions.append('DOWN')
        elif dy == -1:
            directions.append('UP')
    
    return directions


def astar(start: Tuple[int, int], goal: Tuple[int, int], 
          grid: Dict[Tuple[int, int], str], 
          avoid_warps: bool = True) -> Optional[List[Tuple[int, int]]]:
    """
    A* pathfinding algorithm.
    
    Args:
        start: Starting (x, y) position
        goal: Goal (x, y) position
        grid: Map grid {(x, y): symbol}
        avoid_warps: If True, treat warps as obstacles (except if goal)
        
    Returns:
        List of positions from start to goal, or None if no path exists
    """
    # Check if start and goal are in grid
    if start not in grid or goal not in grid:
        logger.debug(f"[A*] Start {start} or goal {goal} not in grid")
        return None
    
    # Check if goal is walkable (warps allowed if goal)
    goal_symbol = grid[goal]
    if not is_walkable(goal_symbol, avoid_warps=False):
        logger.debug(f"[A*] Goal {goal} is not walkable (symbol: {goal_symbol})")
        return None
    
    # Priority queue: (f_score, counter, position)
    counter = 0
    open_set = [(0, counter, start)]
    came_from = {}
    
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    
    in_open_set = {start}
    
    while open_set:
        _, _, current = heapq.heappop(open_set)
        in_open_set.discard(current)
        
        # Reached goal
        if current == goal:
            return reconstruct_path(came_from, start, goal)
        
        # Check neighbors
        # If current is the goal, allow warps; otherwise follow avoid_warps
        current_avoid_warps = avoid_warps and (current != goal)
        neighbors = get_neighbors(current, grid, avoid_warps=current_avoid_warps)
        
        for neighbor in neighbors:
            # Tentative g_score
            tentative_g = g_score[current] + 1
            
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                # This path is better
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                
                if neighbor not in in_open_set:
                    counter += 1
                    heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
                    in_open_set.add(neighbor)
    
    # No path found
    logger.debug(f"[A*] No path from {start} to {goal}")
    return None


def find_path_in_area(map_stitcher: MapStitcher, 
                      location_name: str,
                      start_pos: Tuple[int, int], 
                      goal_pos: Tuple[int, int],
                      avoid_warps: bool = True) -> Optional[List[str]]:
    """
    Find A* path within a single map area.
    
    Args:
        map_stitcher: MapStitcher instance
        location_name: Current location (e.g., "LITTLEROOT TOWN")
        start_pos: Starting (x, y) in world coordinates
        goal_pos: Goal (x, y) in world coordinates
        avoid_warps: If True, avoid doors/stairs unless they're the goal
        
    Returns:
        List of directions ['UP', 'RIGHT', ...] or None if no path
    """
    # Get location grid from map stitcher
    grid = map_stitcher.get_location_grid(location_name, simplified=True)
    
    if not grid:
        logger.debug(f"[PATHFINDING] No grid data for {location_name}")
        return None
    
    # Get the map area to understand coordinate system
    map_area = None
    for area in map_stitcher.map_areas.values():
        if area.location_name and location_name and \
           area.location_name.lower() == location_name.lower():
            map_area = area
            break
    
    if not map_area:
        logger.debug(f"[PATHFINDING] Could not find map area for {location_name}")
        return None
    
    # Convert world coordinates to grid coordinates
    # The grid from get_location_grid uses relative coordinates (0-based from min bounds)
    bounds = getattr(map_area, 'explored_bounds', None)
    if not bounds:
        logger.debug(f"[PATHFINDING] No explored bounds for {location_name}")
        return None
    
    # Convert world coords to relative grid coords
    start_grid = (start_pos[0] - bounds['min_x'], start_pos[1] - bounds['min_y'])
    goal_grid = (goal_pos[0] - bounds['min_x'], goal_pos[1] - bounds['min_y'])
    
    # ENHANCED DEBUG LOGGING
    print(f"\n{'='*80}")
    print(f"🔍 [PATHFINDING DEBUG] Detailed Coordinate Analysis")
    print(f"{'='*80}")
    print(f"Location: {location_name}")
    print(f"World coordinates:")
    print(f"  Start (player): {start_pos}")
    print(f"  Goal (target):  {goal_pos}")
    print(f"Explored bounds:")
    print(f"  X: {bounds['min_x']} to {bounds['max_x']} (width: {bounds['max_x'] - bounds['min_x'] + 1})")
    print(f"  Y: {bounds['min_y']} to {bounds['max_y']} (height: {bounds['max_y'] - bounds['min_y'] + 1})")
    print(f"Grid coordinates (relative to bounds):")
    print(f"  Start: {start_grid}")
    print(f"  Goal:  {goal_grid}")
    print(f"Grid data:")
    print(f"  Total tiles: {len(grid)}")
    print(f"  Grid keys sample: {list(grid.keys())[:10]}")
    print(f"  Start tile: {grid.get(start_grid, 'NOT IN GRID')}")
    print(f"  Goal tile:  {grid.get(goal_grid, 'NOT IN GRID')}")
    
    # Validate coordinates are in grid
    if start_grid not in grid:
        print(f"❌ ERROR: Start position {start_grid} not in grid!")
        print(f"   Player world pos {start_pos} → grid {start_grid} is outside explored area")
        print(f"{'='*80}\n")
        return None
    
    if goal_grid not in grid:
        print(f"❌ ERROR: Goal position {goal_grid} not in grid!")
        print(f"   Target world pos {goal_pos} → grid {goal_grid} is outside explored area")
        print(f"   This goal is unreachable (beyond explored bounds)")
        print(f"{'='*80}\n")
        return None
    
    print(f"✅ Both start and goal are in grid - proceeding with A*")
    print(f"{'='*80}\n")
    
    logger.info(f"[PATHFINDING] {location_name}: World {start_pos} → {goal_pos}")
    logger.info(f"[PATHFINDING] Grid coords: {start_grid} → {goal_grid}")
    logger.info(f"[PATHFINDING] Grid size: {len(grid)} tiles, avoid_warps={avoid_warps}")
    
    # Run A*
    path = astar(start_grid, goal_grid, grid, avoid_warps=avoid_warps)
    
    if not path:
        return None
    
    # Convert path to directions
    directions = path_to_directions(path)
    
    logger.info(f"[PATHFINDING] Found path with {len(directions)} moves: {directions[:5]}...")
    
    return directions


def find_direction_to_goal(map_stitcher: MapStitcher,
                           current_location: str,
                           current_pos: Tuple[int, int],
                           goal: str,
                           movement_preview: Optional[Dict] = None) -> Optional[str]:
    """
    Find best direction for strategic goals.
    
    Args:
        map_stitcher: MapStitcher instance
        current_location: Current location name
        current_pos: Current (x, y) world position
        goal: Goal string - supports multiple formats:
            - Edge goals: "NORTH_EDGE", "SOUTH_EDGE", "EAST_EDGE", "WEST_EDGE"
            - Coordinate goals: "COORDINATES:x,y" (e.g., "COORDINATES:15,20")
            - Location goals: "LOCATION:NAME" (e.g., "LOCATION:ROUTE_101")
            - NPC goals: "NPC:NAME" (e.g., "NPC:PROFESSOR_BIRCH")
            - Simple: "EXPLORE"
        movement_preview: Optional real-time movement data for validation
        
    Returns:
        Single direction ('UP', 'DOWN', etc.) or None
    """
    # Parse goal format
    goal_type, goal_data = _parse_goal_string(goal)
    
    # Get map area
    map_area = None
    for area in map_stitcher.map_areas.values():
        if area.location_name and current_location and \
           area.location_name.lower() == current_location.lower():
            map_area = area
            break
    
    if not map_area:
        logger.debug(f"[PATHFINDING] No map area for goal {goal} in {current_location}")
        return None
    
    bounds = getattr(map_area, 'explored_bounds', None)
    if not bounds:
        logger.debug(f"[PATHFINDING] No bounds for goal {goal}")
        return None
    
    # Determine target position based on goal type
    target_pos = None
    
    if goal_type == "EDGE":
        # Edge-based navigation
        # Calculate target in GRID coordinates (relative to bounds)
        edge_direction = goal_data
        
        # Convert current world position to grid coordinates
        current_grid_x = current_pos[0] - bounds['min_x']
        current_grid_y = current_pos[1] - bounds['min_y']
        
        if edge_direction == "NORTH":
            # Navigate to northern edge (minimum Y in grid = 0)
            target_grid = (current_grid_x, 0)
        elif edge_direction == "SOUTH":
            # Navigate to southern edge (maximum Y in grid)
            target_grid = (current_grid_x, bounds['max_y'] - bounds['min_y'])
        elif edge_direction == "EAST":
            # Navigate to eastern edge (maximum X in grid)
            target_grid = (bounds['max_x'] - bounds['min_x'], current_grid_y)
        elif edge_direction == "WEST":
            # Navigate to western edge (minimum X in grid = 0)
            target_grid = (0, current_grid_y)
        else:
            logger.warning(f"[PATHFINDING] Unknown edge direction: {edge_direction}")
            return None
        
        # Convert back to world coordinates for find_path_in_area
        target_pos = (target_grid[0] + bounds['min_x'], target_grid[1] + bounds['min_y'])
        logger.info(f"[PATHFINDING] {edge_direction}_EDGE goal: grid {target_grid} → world {target_pos}")
    
    elif goal_type == "COORDINATES":
        # Direct coordinate navigation
        target_pos = goal_data  # Already a tuple (x, y)
        logger.info(f"[PATHFINDING] COORDINATES goal: target={target_pos}")
    
    elif goal_type == "LOCATION":
        # Location-based navigation (TODO: enhance with location database)
        # For now, try to find the location in map_areas
        target_location = goal_data
        target_area = None
        for area in map_stitcher.map_areas.values():
            if area.location_name and target_location.upper() in area.location_name.upper():
                target_area = area
                break
        
        if target_area:
            # Navigate to center of target location
            target_bounds = getattr(target_area, 'explored_bounds', None)
            if target_bounds:
                target_x = (target_bounds['min_x'] + target_bounds['max_x']) // 2
                target_y = (target_bounds['min_y'] + target_bounds['max_y']) // 2
                target_pos = (target_x, target_y)
                logger.info(f"[PATHFINDING] LOCATION:{target_location} goal: target={target_pos}")
            else:
                logger.warning(f"[PATHFINDING] Target location {target_location} has no bounds")
                return None
        else:
            logger.warning(f"[PATHFINDING] Target location {target_location} not found in map areas")
            return None
    
    elif goal_type == "NPC":
        # NPC-based navigation (TODO: enhance with NPC tracking)
        npc_name = goal_data
        logger.warning(f"[PATHFINDING] NPC:{npc_name} goal not yet implemented")
        return None
    
    elif goal_type == "EXPLORE":
        # Find nearest unexplored tile
        grid = map_stitcher.get_location_grid(current_location, simplified=True)
        unknown_tiles = [(x + bounds['min_x'], y + bounds['min_y']) 
                        for (x, y), sym in grid.items() if sym == '?']
        
        if unknown_tiles:
            target_pos = min(unknown_tiles, 
                           key=lambda p: heuristic(current_pos, p))
            logger.info(f"[PATHFINDING] EXPLORE goal: target={target_pos} (nearest ?)")
        else:
            logger.debug(f"[PATHFINDING] No unexplored tiles found")
            return None
    
    else:
        logger.warning(f"[PATHFINDING] Unknown goal type: {goal_type}")
        return None
    
    if not target_pos:
        return None
    
    # Find path to target (avoid warps by default)
    directions = find_path_in_area(
        map_stitcher, 
        current_location, 
        current_pos, 
        target_pos,
        avoid_warps=True  # Don't accidentally warp
    )
    
    if not directions or len(directions) == 0:
        logger.debug(f"[PATHFINDING] No path found to {goal}")
        return None
    
    # Get first direction
    next_direction = directions[0]
    
    # Optional: Validate with movement preview
    if movement_preview:
        direction_data = movement_preview.get(next_direction, {})
        if direction_data.get('blocked', True):
            logger.warning(f"[PATHFINDING] A* suggested {next_direction} but movement preview shows BLOCKED!")
            logger.warning(f"[PATHFINDING] Movement preview: {movement_preview}")
            # Try next direction in path if available
            if len(directions) > 1:
                logger.info(f"[PATHFINDING] Trying alternate direction: {directions[1]}")
                return directions[1]
            return None
    
    logger.info(f"[PATHFINDING] Recommended direction: {next_direction} (path length: {len(directions)})")
    return next_direction
