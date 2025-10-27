# Tests Directory

**Quick Start**: `pytest` from this directory

**📖 For detailed documentation, see [TESTING_GUIDE.md](TESTING_GUIDE.md)**

---

## Directory Structure

### Test Categories
- **`dialogue/`** - Dialogue detection, completion, agent interaction + **`debug/`** subdirectory
- **`navigation/`** - Navigation and pathfinding tests
- **`agent/`** - Agent behavior, modules, objective planning
- **`integration/`** - Full system integration tests
- **`manual/`** - Manual/interactive testing scripts
- **`scripts/`** - Automated test runners
- **`utils/`** - Test utilities and helpers

### Support
- **`scenarios/`** - Scenario-based tests
- **`standalone/`** - Independent test files
- **`states/`** - Saved emulator states
- **`ground_truth/`** - Ground truth validation data

### Core Files
- `conftest.py` - Pytest configuration
- `run_tests.py` - Main test runner
- `test_integration.py`, `test_data_flow.py`, `test_default_config.py` - Core tests
- `validate_live_system.py` - Live system validator

---

## Quick Commands

```bash
# Run all tests
pytest

# Run specific category
pytest dialogue/
pytest agent/
pytest navigation/

# Run single test
pytest dialogue/test_dialogue_detection.py

# Stop on first failure
pytest -x
```

---

## Save States

- **`tests/states/`** - General test states (35+ files) - used by most tests
- **`tests/scenarios/save_states/`** - Scenario-specific states - used by scenario tests

---

**📖 See [TESTING_GUIDE.md](TESTING_GUIDE.md) for:**
- Detailed test categories
- Best practices
- Troubleshooting
- Adding new tests
- CI integration
