# Testing Guide

**Quick Start**: Run `.venv/bin/python -m pytest tests/` for fast unit tests (<20s)

---

## Test Organization

```
tests/
├── test_*.py (32 tests)         # Unit tests - Fast (<20s), always run
├── integration/ (4 tests)       # Integration tests - Medium (30-120s)
├── scenarios/ (6+ tests)        # Scenario tests - Slow (1-5min)
├── states/                      # Test save states for all tests
└── standalone/                  # Manual diagnostic scripts
```

### Unit Tests (Main Suite)
**Runtime**: <20 seconds for all 32 tests  
**Run**: `.venv/bin/python -m pytest tests/`

Core functionality tests with no external dependencies (mocked). Includes:
- `test_agent_modules.py` - Agent module validation (action, memory, perception, planning)
- `test_dialogue_detection.py` - Dialogue detection logic  
- `test_navigation_*.py` - Navigation systems
- `test_objective_planner.py` - Planning logic
- `test_battle_state_formatting.py` - Battle formatting
- And 27 more...

### Integration Tests
**Runtime**: 30-120 seconds per test  
**Run**: `.venv/bin/python -m pytest tests/integration/`

Test emulator memory reading, map transitions, OCR systems (direct emulator, no server):
- `test_memory_reading.py` - Emulator memory reading
- `test_map_transitions.py` - Location transitions  
- `test_ground_truth.py` - Regression testing
- `test_dialogue_detection.py` - OCR dialogue detection across multiple states

### Scenario Tests
**Runtime**: 1-5 minutes per test  
**Run**: `python tests/scenarios/run_scenarios.py`

End-to-end workflows and performance monitoring (may spawn servers):
- `test_fps_adjustment_pytest.py` - FPS switching
- `test_torchic_state.py` - Save state validation
- `test_map_stitcher_fix.py` - Performance monitoring
- `run_scenarios.py` - Scenario test framework (exit van, navigation, etc.)

---

## Common Commands

```bash
# Fast unit tests (recommended for prompt/agent changes)
.venv/bin/python -m pytest tests/ -q

# Integration tests (before major changes)
.venv/bin/python -m pytest tests/integration/ -v

# Specific test
.venv/bin/python -m pytest tests/test_agent_modules.py -v

# With print output
.venv/bin/python -m pytest tests/test_file.py -v -s

# Stop on first failure
.venv/bin/python -m pytest tests/ -x
```

---

## Testing Agent Behavior (Prompts/Agent Changes)

**Recommended workflow when modifying prompts or agent code:**

### 1. Quick Unit Tests (Run First - 18s)
```bash
.venv/bin/python -m pytest tests/ -q
```
Validates core logic without spawning emulators.

### 2. Dialogue Handling Tests (30-60s)
```bash
# Unit test - dialogue detection logic
.venv/bin/python -m pytest tests/test_dialogue_detection.py -v

# Integration test - OCR dialogue detection on real states
.venv/bin/python -m pytest tests/integration/test_dialogue_detection.py -v
```
Tests if agent can detect and handle dialogue properly.

### 3. Navigation Tests (30-60s)
```bash
# Navigation logic tests
.venv/bin/python -m pytest tests/test_navigation_enhanced.py -v
.venv/bin/python -m pytest tests/test_navigation_integration.py -v
.venv/bin/python -m pytest tests/test_route_101_navigation.py -v

# Map transition test
.venv/bin/python -m pytest tests/integration/test_map_transitions.py -v
```
Tests if agent can navigate between locations.

### 4. End-to-End Scenario Tests (1-5min)
```bash
# Run scenario framework (exit van, etc.)
python tests/scenarios/run_scenarios.py

# FPS adjustment in dialogue
.venv/bin/python -m pytest tests/scenarios/test_fps_adjustment_pytest.py -v
```
Tests complete workflows like exiting the van, handling dialogues at correct FPS.

### 5. Manual Testing (As Needed)
```bash
# Load a specific state and watch agent behavior
python run.py --agent-auto --load-state tests/states/dialog.state

# Test from torchic selection state
python run.py --agent-auto --load-state tests/states/torchic.state
```

**Key Test States for Manual Testing:**
- `tests/states/dialog.state` - Test dialogue handling
- `tests/states/house.state` - Test indoor navigation
- `tests/states/torchic.state` - Test Pokemon selection
- `tests/states/simple_test.state` - Basic overworld state

---

## Save State Locations

### tests/states/ (Used by ALL tests)
Contains states used by unit, integration, and most scenario tests:
- `dialog.state`, `dialog2.state`, `dialog3.state` - Dialogue states
- `house.state`, `upstairs.state` - Indoor locations
- `truck.state` - Moving van state
- `torchic.state` - Pokemon selection
- `simple_test.state` - Basic overworld
- `wild_battle.state` - Battle state
- And more... (35 total states)

### tests/scenarios/save_states/ (Scenario-specific)
Contains states specifically for scenario tests:
- `truck_start.state` - Exit van scenario
- `set_clock_save.state` - Clock setting scenario  
- `mudkip_start_battle_save.state` - Battle scenario

**Note**: The two directories serve different purposes:
- `tests/states/` = General test states (shared)
- `tests/scenarios/save_states/` = Scenario-specific states (workflow tests)

**Do NOT combine them** - they're organized this way intentionally.

---

## Architecture Note

**You're using server mode correctly!** ✅

Your command: `python run.py --agent-auto --load-state "state.state"`

This spawns:
- **Server process**: Runs emulator, provides HTTP API
- **Client process**: Runs agent, communicates via HTTP

This is the **correct architecture** for the competition. Keep using it!

**Important**: Don't spawn servers in tests (tests use direct emulator for speed).

---

## Adding Tests

**Unit Test**:
```python
def test_feature():
    """Test description"""
    result = my_function(input_data)
    assert result == expected_value
```

**Integration Test**:
```python
import pytest
from pokemon_env.emulator import EmeraldEmulator

class TestFeature:
    @pytest.fixture
    def emulator(self):
        emu = EmeraldEmulator("Emerald-GBAdvance/rom.gba", headless=True)
        emu.initialize()
        yield emu
        emu.stop()
    
    def test_feature(self, emulator):
        emulator.load_state("tests/states/test.state")
        result = emulator.memory_reader.read_something()
        assert result is not None
```

---

## Troubleshooting

**Tests hang**: `pkill -f mgba` then rerun  
**Import errors**: Run from project root: `cd /path/to/pokeagent-speedrun`  
**ROM not found**: Ensure `Emerald-GBAdvance/rom.gba` exists  
**State not found**: Check `tests/states/` or `tests/scenarios/save_states/`

---

## Best Practices

✅ Run unit tests before every commit  
✅ Use descriptive test names  
✅ Clean up resources (stop emulator)  
✅ Mock external dependencies  
✅ Test one thing per test

❌ Don't spawn servers in unit tests  
❌ Don't leave emulators running  
❌ Don't use hardcoded paths  
❌ Don't make tests depend on each other

---

## Summary

| Type | Count | Runtime | When to Run |
|------|-------|---------|-------------|
| Unit | 32 | <20s | Every commit / After prompt changes |
| Integration | 4 | 30-120s | Before major changes |
| Scenarios | 6+ | 1-5min | End-to-end validation |

**Current Status**: 32 passed, 6 skipped, 0 failed ✅
