# Grass Avoidance System

## Overview

The A* pathfinding system supports a `avoid_grass` parameter that controls whether the agent should path through tall grass tiles or avoid them.

## Default Behavior

**Default: `avoid_grass=True` (Speedrun Mode)**
- A* penalizes grass tiles with 3x cost
- Agent prefers normal paths (`.`, `_`) to minimize wild encounters
- Used for speedrunning to avoid random battles

## Trainer Avoidance Strategy

**Use: `avoid_grass=False` (Trainer Avoidance)**
- A* treats grass tiles as normal walkable tiles
- Agent will path through grass if it's the most efficient route
- Useful for avoiding trainer line-of-sight by taking grass detours

## How to Use

### In Directive System

Add `avoid_grass: False` to any directive that returns `goal_coords`:

```python
return {
    'goal_coords': (x, y, 'LOCATION'),
    'should_interact': False,
    'avoid_grass': False,  # Path through grass to avoid trainers
    'description': 'Navigate through grass to avoid trainer'
}
```

### Example: Route 102 Trainer Avoidance

```python
# Normal path (avoids grass, but trainers see you)
return {
    'goal_coords': (10, 8, 'ROUTE_102'),
    'should_interact': False,
    # avoid_grass defaults to True
    'description': 'Navigate west on normal path'
}

# Grass detour (trainers can't see through grass)
return {
    'goal_coords': (10, 8, 'ROUTE_102'),
    'should_interact': False,
    'avoid_grass': False,  # Take grass path instead
    'description': 'Navigate west through grass to avoid trainers'
}
```

## Cost System

### With `avoid_grass=True` (default):
- Normal path (`.`, `_`): cost = 1.0
- Tall grass (`~`): cost = 3.0 (strongly avoided)
- Ledges: cost = 1.2 (slight penalty)

### With `avoid_grass=False`:
- Normal path (`.`, `_`): cost = 1.0
- Tall grass (`~`): cost = 1.0 (treated equally)
- Ledges: cost = 1.2 (slight penalty)

## Technical Details

The `avoid_grass` parameter flows through:

1. **objective_manager.py**: Directive includes `'avoid_grass': False`
2. **action.py**: Extracts `avoid_grass = directive.get('avoid_grass', True)`
3. **_astar_pathfind_with_grid_data()**: Receives `avoid_grass` parameter
4. **get_tile_cost()**: Uses `avoid_grass` to calculate tile penalties

## When to Use Each Mode

### Use `avoid_grass=True` (default):
- General speedrunning navigation
- Minimizing wild encounter delays
- Racing toward objectives quickly

### Use `avoid_grass=False`:
- Specific routes where trainers block normal paths
- Areas where grass detour is shorter than trainer battle
- Strategic positioning for gym approaches

## Future Enhancements

Potential improvements:
- Dynamic trainer vision cone detection
- Cost-benefit analysis: grass encounters vs trainer battles
- Learning which routes minimize total time including battles
