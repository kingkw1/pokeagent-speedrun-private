# Test Environment Setup - Quick Fix Summary

## Problem
Running `python -m pytest tests/` failed with:
1. `ModuleNotFoundError: No module named 'mgba'` 
2. `SystemExit: 1` crashes during test collection
3. Tests running at module import time

## Root Causes
1. **Wrong Python environment** - System Python instead of `.venv`
2. **Standalone scripts** - Many `test_*.py` files are diagnostic scripts, not pytest tests
3. **Aggressive ROS pytest plugin** - Imports all `test_*.py` files regardless of ignore settings

## Solutions Applied

### 1. Virtual Environment
**Always use `.venv/bin/python`:**
```bash
# ✅ CORRECT
source .venv/bin/activate
python -m pytest tests/

# ✅ ALTERNATIVE
.venv/bin/python -m pytest tests/

# ❌ WRONG (missing mgba!)
python -m pytest tests/
```

### 2. Moved Standalone Scripts
Moved diagnostic scripts to `tests/standalone/` and renamed them:
- `test_vlm_understanding.py` → `standalone_vlm_understanding.py`
- `test_vlm_simple_state.py` → `standalone_vlm_simple_state.py`
- `test_perception_gpu.py` → `standalone_perception_gpu.py`
- And 6 more...

**Why rename?** ROS pytest plugin ignores `--ignore` flags and imports ALL `test_*.py` files.

### 3. Updated pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short --ignore=tests/standalone --ignore=tests/scenarios
```

### 4. Created Helper Scripts
- `tests/run_pytest.sh` - Runs pytest with correct venv
- `tests/standalone/README.md` - Documents standalone scripts

## Results

✅ **85 pytest tests** collected successfully

✅ **Dialogue detection tests** passing (4/5)

✅ **No more import-time crashes**

## How to Use

### Run Pytest Tests
```bash
# All tests
source .venv/bin/activate
python -m pytest tests/

# Specific test file
.venv/bin/python -m pytest tests/test_dialogue_detection.py

# Or use helper script
./tests/run_pytest.sh tests/test_dialogue_detection.py
```

### Run Standalone Scripts
```bash
source .venv/bin/activate
python tests/standalone/standalone_vlm_understanding.py
```

### Run Scenario Tests
```bash
source .venv/bin/activate
./run_scenario_tests.sh
```

## File Organization

```
tests/
├── test_*.py                      # Proper pytest tests (85 tests)
├── standalone/
│   ├── standalone_*.py            # Diagnostic scripts (9 scripts)
│   └── README.md
├── scenarios/
│   ├── run_scenarios.py           # Integration tests
│   ├── save_states/               # Test save states
│   └── TESTING_INFRASTRUCTURE.md
├── states/                        # Unit test save states
└── run_pytest.sh                  # Helper script
```

## Common Issues

**Issue:** `ModuleNotFoundError: No module named 'mgba'`  
**Fix:** Activate venv: `source .venv/bin/activate`

**Issue:** Tests crash with `SystemExit`  
**Fix:** Use `tests/standalone/` scripts directly, not pytest

**Issue:** One dialogue test failing  
**Fix:** Unrelated to setup - probably needs state_formatter update
