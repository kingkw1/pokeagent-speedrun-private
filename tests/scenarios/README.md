# Scenario-Based Testing Guide

## Overview

The `test_scenario_runner.py` script provides automated end-to-end testing for the Pokemon agent using save states. Each test loads a specific game state, runs the agent for a limited number of steps, and validates that a success condition is met.

## Quick Start

```bash
# Run all tests
python tests/test_scenario_runner.py

# Run a specific test
python tests/test_scenario_runner.py "exit van"

# List available tests
python tests/test_scenario_runner.py --list

# Run with verbose output (see agent logs)
python tests/test_scenario_runner.py -v
```

## Current Tests

### 1. Exit Moving Van
- **Save State**: `Emerald-GBAdvance/truck_start.state`
- **Goal**: Agent exits the moving van and enters Brendan's house
- **Success**: Location changes from `MOVING_VAN` to `LITTLEROOT_TOWN_BRENDANS_HOUSE_2F`
- **Max Steps**: 50

## Adding New Tests

To add a new scenario test:

### 1. Create a Save State

Play the game manually to the desired starting point and save the state:
```python
# In the emulator or during manual testing
env.save_state("Emerald-GBAdvance/my_test_scenario.state")
```

### 2. Define Success Criteria

Add a success function in `test_scenario_runner.py`:

```python
def check_my_scenario(state_data):
    """
    Success: Description of what constitutes success
    Expected: What should change in the state
    """
    # Example: Check location
    location = state_data.get('player', {}).get('location', '')
    return location == 'TARGET_LOCATION'
    
    # Example: Check milestone
    milestones = state_data.get('milestones', {})
    return milestones.get('MY_MILESTONE', {}).get('completed', False)
    
    # Example: Check position
    pos = state_data.get('player', {}).get('position', {})
    return pos.get('x', 0) > 20 and pos.get('y', 0) > 15
```

### 3. Add to Test Suite

Add your test to the `TESTS` list:

```python
TESTS = [
    # ... existing tests ...
    
    ScenarioTest(
        name="My New Test",
        save_state="Emerald-GBAdvance/my_test_scenario.state",
        max_steps=30,
        success_fn=check_my_scenario,
        description="Description of what this test validates"
    ),
]
```

## Available State Data

The success function receives a `state_data` dictionary with the following structure:

```python
{
    "player": {
        "location": "LITTLEROOT_TOWN",
        "position": {"x": 10, "y": 15, "map": 0},
        "name": "Brendan",
        "money": 3000,
        "party": [...]
    },
    "game": {
        "state": "overworld",
        "in_battle": False,
        "party_count": 1,
        "dialogue": {"active": False, "text": ""}
    },
    "milestones": {
        "PLAYER_NAME_SET": {"completed": True, "timestamp": ...},
        "INTRO_CUTSCENE_COMPLETE": {"completed": False}
    },
    "map": {...},
    "npcs": [...]
}
```

## Test Scenarios to Consider

Here are suggested test scenarios based on common agent tasks:

### Navigation Tests
- ✅ **Exit Moving Van** - Basic movement and transition
- 🔲 **Exit House** - Navigate from inside to outside
- 🔲 **Navigate to Route 101** - Multi-step pathfinding
- 🔲 **Navigate Around Obstacle** - Pathfinding with blocked paths
- 🔲 **Enter PokeCenter** - Navigate to specific building

### Interaction Tests
- 🔲 **Talk to NPC** - Approach and interact with character
- 🔲 **Complete Dialogue** - Advance through conversation
- 🔲 **Use PokeCenter** - Full healing interaction sequence
- 🔲 **Pick Up Item** - Interact with ground items

### Battle Tests
- 🔲 **Win Simple Battle** - Complete a low-level wild battle
- 🔲 **Use Appropriate Move** - Select effective move type
- 🔲 **Heal in Battle** - Use potion when needed

### Menu Tests
- 🔲 **Open and Close Menu** - Navigate menus correctly
- 🔲 **Use Item from Bag** - Access and use items
- 🔲 **Check Pokemon Stats** - Navigate party menu

## Performance Notes

- **Startup Time**: ~8 seconds for server initialization
- **VLM Calls**: ~3 seconds per decision
- **Typical Test**: 50 steps = ~2-4 minutes
- **Recommendation**: Run tests manually after significant changes, not continuously

## Troubleshooting

### Test Fails with "Connection Lost"
- Check that the save state file exists
- Verify no other server is running on the port
- Try running with `-v` flag to see agent output

### Test Times Out
- Increase `max_steps` if the task is legitimately complex
- Check agent logs to see where it's getting stuck
- Verify success criteria is achievable from the save state

### Port Conflicts
- Tests automatically use different ports (8002, 8003, etc.)
- If conflicts persist, close any running `run.py` instances

## Integration with Development Workflow

```bash
# 1. Make changes to agent code
vim agent/action.py

# 2. Run relevant tests to verify
python tests/test_scenario_runner.py "van"

# 3. If passing, run full suite
python tests/test_scenario_runner.py

# 4. Commit if all tests pass
git add .
git commit -m "fix: improved van exit navigation"
```

## Future Enhancements

- [ ] Parallel test execution (with port management)
- [ ] Test result persistence (track regressions)
- [ ] Video recording of test runs
- [ ] Benchmark mode (track performance over time)
- [ ] CI/CD integration
