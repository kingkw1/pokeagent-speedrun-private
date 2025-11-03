# Pokemon Emerald AI Agent - Test Suite# Tests Directory



**Quick Start**: Run `pytest` from project root or tests directory**Quick Start**: `pytest` from this directory



**📖 For detailed guides, see:****📖 For detailed documentation, see [TESTING_GUIDE.md](TESTING_GUIDE.md)**

- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Comprehensive testing documentation

- [dialogue/README.md](dialogue/README.md) - Dialogue system testing---

- [navigation/README.md](navigation/README.md) - Navigation testing

## Directory Structure

---

### Test Categories

## 🎯 Current Test Status (Updated: 2025-11-03)- **`dialogue/`** - Dialogue detection, completion, agent interaction + **`debug/`** subdirectory

- **`navigation/`** - Navigation and pathfinding tests

### ✅ Working & Up-to-Date- **`agent/`** - Agent behavior, modules, objective planning

- **Dialogue Tests** (`dialogue/`) - Red triangle detection, HUD filtering- **`integration/`** - Full system integration tests

- **Navigation Tests** (`navigation/`) - Moving van exit, Route 101- **`manual/`** - Manual/interactive testing scripts

- **Integration Tests** (`integration/`) - Full system validation- **`scripts/`** - Automated test runners

- **`utils/`** - Test utilities and helpers

### 🔧 Recently Updated

- Dialogue detection now uses **red triangle indicator** (❤️) for precise A-button timing### Support

- **HUD filtering** prevents false positives from "Player: NAME" status text- **`scenarios/`** - Scenario-based tests

- VLM perception simplified to prevent template hallucinations- **`standalone/`** - Independent test files

- **`states/`** - Saved emulator states

---- **`ground_truth/`** - Ground truth validation data



## 📁 Directory Structure### Core Files

- `conftest.py` - Pytest configuration

```- `run_tests.py` - Main test runner

tests/- `test_integration.py`, `test_data_flow.py`, `test_default_config.py` - Core tests

├── save_states/          # All emulator save states (47 files)- `validate_live_system.py` - Live system validator

├── dialogue/             # Dialogue detection & handling tests

│   ├── debug/           # Debugging scripts---

│   └── README.md        # Dialogue test documentation

├── navigation/           # Navigation & pathfinding tests## Quick Commands

│   └── README.md        # Navigation test documentation

├── agent/                # Agent behavior & module tests```bash

├── integration/          # Full system integration tests# Run all tests

├── manual/               # Manual/interactive testing scriptspytest

├── scenarios/            # Scenario-based tests

├── standalone/           # Independent test scripts# Run specific category

├── utils/                # Test utilities & helperspytest dialogue/

├── ground_truth/         # Validation datapytest agent/

└── archive/              # Deprecated testspytest navigation/

```

# Run single test

---pytest dialogue/test_dialogue_detection.py



## 🚀 Quick Commands# Stop on first failure

pytest -x

### Run All Tests```

```bash

# From project root---

pytest tests/

## Save States

# From tests directory

pytest- **`tests/states/`** - General test states (35+ files) - used by most tests

```- **`tests/scenarios/save_states/`** - Scenario-specific states - used by scenario tests



### Run Specific Categories---

```bash

pytest tests/dialogue/           # Dialogue detection & handling**📖 See [TESTING_GUIDE.md](TESTING_GUIDE.md) for:**

pytest tests/navigation/         # Navigation & pathfinding- Detailed test categories

pytest tests/agent/              # Agent behavior- Best practices

pytest tests/integration/        # Full system tests- Troubleshooting

```- Adding new tests

- CI integration

### Run Single Test
```bash
pytest tests/navigation/test_exit_moving_van.py
pytest tests/dialogue/test_unit_multiflag_state.py -v
```

### With Options
```bash
pytest -v                        # Verbose output
pytest -x                        # Stop on first failure
pytest --lf                      # Run last failed tests
pytest --cov=agent               # With coverage
```

---

## 💾 Save States

**Location**: `tests/save_states/` (consolidated from multiple directories)

**Key States:**
- `truck_start.state` - Starting point, inside moving van
- `dialog*.state` - Various dialogue scenarios
- `no_dialog*.state` - No dialogue present
- `house*.state` - Inside player's house
- `route101_*.state` - Route 101 scenarios

**Usage in Tests:**
```python
from pokemon_env.emulator import EmeraldEmulator

env = EmeraldEmulator('Emerald-GBAdvance/rom.gba', headless=True)
env.load_state('tests/save_states/dialog2.state')
```

---

## 🎮 Testing Philosophy

### Dialogue Detection (Critical Update)

**✅ Current Approach (November 2025):**
- **Red Triangle Indicator** (❤️) - Most reliable signal for "press A"
- **HUD Filtering** - Prevents false positives from status text
- **VLM Perception** - Simplified prompts prevent hallucinations
- **Priority System**: Red triangle → Text box → Fallback

**❌ Deprecated:**
- Memory-based `in_dialog` flag (42.9% accurate, unreliable)
- Long VLM prompts (caused template echoing)
- Multiple conflicting detection systems

**See [dialogue/README.md](dialogue/README.md) for details**

### Test Organization

Tests are organized by **functionality** not complexity:
- **`dialogue/`** - Everything dialogue-related
- **`navigation/`** - Everything navigation-related
- **`agent/`** - Agent behavior & modules
- **`integration/`** - Multi-component tests

---

## 📝 Environment Setup

**CRITICAL**: Always activate the virtual environment before running tests!

```bash
# Activate venv
source /home/kevin/Documents/pokeagent-speedrun/.venv/bin/activate

# Or use the full path in commands
/home/kevin/Documents/pokeagent-speedrun/.venv/bin/python -m pytest tests/
```

**Why?** The system Python environment doesn't have the required dependencies (mgba, torch, etc.)

---

## 🔍 Debugging Tests

### Dialogue Issues
```bash
# Check dialogue detection
pytest tests/dialogue/test_unit_multiflag_state.py -v

# Debug with scripts
cd tests/dialogue/debug/
python debug_dialogue_states.py
```

### Navigation Issues
```bash
# Test moving van exit
pytest tests/navigation/test_exit_moving_van.py -v

# Check navigation logs
python tests/navigation/test_exit_moving_van.py | grep "Step\|Position"
```

### Integration Issues
```bash
# Full system validation
pytest tests/integration/ -v

# Live system check
python tests/validate_live_system.py
```

---

## 📊 Test Coverage

### By Category
- **Dialogue**: 10+ tests (unit, integration, debug scripts)
- **Navigation**: 5 tests (moving van, Route 101, pathfinding)
- **Agent**: 8+ tests (perception, action, planning, objectives)
- **Integration**: 6+ tests (full system, data flow, ground truth)

### By Type
- **Unit Tests**: Fast, isolated, no external dependencies
- **Integration Tests**: Multi-component, requires emulator
- **Scenario Tests**: Real gameplay scenarios, full agent runs

---

## 🛠️ Adding New Tests

1. **Choose correct directory** based on functionality
2. **Use existing save states** from `tests/save_states/`
3. **Follow naming convention**: `test_<functionality>_<specifics>.py`
4. **Add documentation** if creating new test category
5. **Update this README** if adding significant new functionality

Example:
```python
# tests/navigation/test_new_route.py
def test_route_102_navigation():
    """Test navigation through Route 102"""
    env = EmeraldEmulator('Emerald-GBAdvance/rom.gba', headless=True)
    env.load_state('tests/save_states/route102_start.state')
    # ... test code ...
```

---

## 🐛 Common Issues

### Import Errors
**Problem**: `ModuleNotFoundError: No module named 'mgba'`  
**Solution**: Activate venv or use full Python path

### Save State Not Found
**Problem**: `FileNotFoundError: tests/states/dialog.state`  
**Solution**: Update to `tests/save_states/dialog.state` (states directory was reorganized)

### Test Hangs
**Problem**: Test doesn't complete  
**Solution**: Use `--timeout=60` or check if server process is running

### VLM Errors
**Problem**: VLM returns template text or errors  
**Solution**: Check if model is loaded, try smaller test first

---

## 📚 Additional Resources

- **Dialogue Tests**: See [dialogue/README.md](dialogue/README.md)
- **Navigation Tests**: See [navigation/README.md](navigation/README.md)
- **Testing Guide**: See [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Project Docs**: See `docs/` directory in project root

---

## 📈 Recent Improvements

**November 2025:**
- ✅ Implemented red triangle indicator detection for dialogue
- ✅ Added HUD filtering to prevent false positives
- ✅ Simplified VLM prompts to prevent hallucinations
- ✅ Consolidated all save states to `tests/save_states/`
- ✅ Updated all documentation to reflect current approaches
- ✅ Created navigation test README

**Key Achievement:** Dialogue detection now uses the red triangle (❤️) as the primary signal for when to press A, making it much more reliable than previous approaches.

---

**Last Updated**: November 3, 2025  
**Status**: All tests updated to use consolidated `tests/save_states/` directory
