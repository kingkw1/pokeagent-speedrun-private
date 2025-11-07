"""
Location Database - Emerald world map relationships

Provides directional relationships between locations to enable intelligent pathfinding.
This allows the agent to know "Oldale Town is NORTH of Littleroot Town" without
hardcoding location-specific navigation logic.
"""

from typing import Dict, Optional, Tuple

# Location connectivity graph
# Format: {location: {neighbor_location: direction_to_neighbor}}
LOCATION_GRAPH = {
    'LITTLEROOT_TOWN': {
        'ROUTE_101': 'north',
        'PROFESSOR_BIRCHS_LAB': 'internal',  # Inside town
    },
    'ROUTE_101': {
        'LITTLEROOT_TOWN': 'south',
        'OLDALE_TOWN': 'north',
    },
    'OLDALE_TOWN': {
        'ROUTE_101': 'south',
        'ROUTE_102': 'west',
        'ROUTE_103': 'north',
    },
    'ROUTE_102': {
        'OLDALE_TOWN': 'east',
        'PETALBURG_CITY': 'west',
    },
    'ROUTE_103': {
        'OLDALE_TOWN': 'south',
    },
    'PETALBURG_CITY': {
        'ROUTE_102': 'east',
        'ROUTE_104': 'north',
    },
    'PROFESSOR_BIRCHS_LAB': {
        'LITTLEROOT_TOWN': 'outside',
    },
}


def get_direction_to_location(from_location: str, to_location: str) -> Optional[str]:
    """
    Find the direction to travel from one location to another.
    
    Args:
        from_location: Starting location (e.g., "LITTLEROOT_TOWN")
        to_location: Target location (e.g., "OLDALE_TOWN")
        
    Returns:
        Direction string ("north", "south", "east", "west") or None if not adjacent
    """
    # Normalize location names
    from_loc = from_location.upper().replace(' ', '_')
    to_loc = to_location.upper().replace(' ', '_')
    
    # Check if locations are directly connected
    if from_loc in LOCATION_GRAPH:
        neighbors = LOCATION_GRAPH[from_loc]
        if to_loc in neighbors:
            return neighbors[to_loc]
    
    # Not directly connected - would need pathfinding through intermediate locations
    # For now, just return None (could implement BFS here in future)
    return None


def get_edge_goal_for_direction(direction: str) -> Optional[str]:
    """
    Convert a compass direction to an edge goal for pathfinding.
    
    Args:
        direction: Compass direction ("north", "south", "east", "west")
        
    Returns:
        Edge goal string (e.g., "NORTH_EDGE") or None
    """
    direction_map = {
        'north': 'NORTH_EDGE',
        'south': 'SOUTH_EDGE',
        'east': 'EAST_EDGE',
        'west': 'WEST_EDGE',
        'outside': None,  # Exit building (no specific edge)
        'internal': None,  # Move within area
    }
    
    return direction_map.get(direction.lower())


def location_name_variants(location: str) -> list:
    """
    Generate possible variants of a location name for matching.
    
    Args:
        location: Location string
        
    Returns:
        List of possible variants
    """
    base = location.upper().replace(' ', '_')
    variants = [
        base,
        base.replace('_', ' '),
        base.replace('_', ''),
    ]
    return variants
