# Files Recommended for Archive Review

**Date**: November 3, 2025  
**Purpose**: List of test files that may be candidates for archiving

---

## ✅ Already Archived

These files were moved to `tests/archive/` because they break pytest collection:

1. **`test_direct_vlm_dialogue.py.bak`** - Module-level env.close() causing AttributeError
2. **`test_unit_multiflag_state.py.bak`** - Module-level subprocess calls requiring server
3. **`test_unit_ocr_vs_memory.py.bak`** - Module-level server connection attempts

---

## 🤔 Candidates for Future Archive (Optional)

### **Integration Tests with Potential Issues**

#### `tests/integration/test_vlm_accuracy.py`
- **Issue**: Has module-level print statements that execute on import
- **Status**: May interfere with pytest collection
- **Action**: Consider wrapping in functions or moving to standalone/

#### `tests/integration/verify_vlm_integration.py`
- **Issue**: Module-level print statements
- **Status**: Looks like a verification script, not a test
- **Action**: Consider moving to standalone/ or scripts/

### **Navigation Tests**

#### `tests/navigation/test_exit_moving_van.py`
- **Issue**: Has module-level execution and exits with sys.exit(1)
- **Status**: Causes pytest collection to fail (SystemExit: 1)
- **Action**: **SHOULD BE ARCHIVED** - Refactor to use proper pytest functions
- **Note**: This is a runnable script, not a pytest test

#### `tests/navigation/test_route_101_north.py`
- **Status**: Uses `tests/save_states/` correctly ✅
- **Action**: Keep if properly formatted for pytest

### **Standalone Tests (Keep As-Is)**

These files in `tests/standalone/` are **intentionally runnable scripts**, not pytest tests:
- `standalone_vlm_simple_map.py`
- `standalone_vlm_understanding.py`
- `standalone_vlm_consistency.py`
- `standalone_vlm_simple_state.py`
- `standalone_perception_gpu.py`
- `standalone_perception_integration.py`
- `standalone_all_models.py`
- `standalone_vlm_with_screenshot.py`
- `direct_vlm_test.py`
- `test_navigation_vlm.py`

**Action**: Leave these alone - they're designed to run directly with `python tests/standalone/xxx.py`

### **Manual Tests (Keep As-Is)**

Files in `tests/manual/` are manual testing scripts:
- `test_button_sequence.py`

**Action**: Keep - these are for manual/interactive testing

---

## 📋 Recommended Actions

### **High Priority - Archive Now**
```bash
# Navigation test with sys.exit() that breaks pytest
mv tests/navigation/test_exit_moving_van.py tests/archive/test_exit_moving_van.py.bak
```

### **Medium Priority - Review Later**
1. Check if `tests/integration/test_vlm_accuracy.py` can be converted to proper pytest test
2. Check if `tests/integration/verify_vlm_integration.py` should move to scripts/

### **Low Priority - Leave As-Is**
- All files in `tests/standalone/` - they're working as intended
- All files in `tests/manual/` - they're for manual testing
- Most files in `tests/scenarios/` - they're runnable scenario scripts

---

## 🎯 Archive Criteria

A file should be archived if:
1. ❌ It breaks pytest collection (SystemExit, module-level exceptions)
2. ❌ It requires external services at import time (server connections)
3. ❌ It has syntax errors or missing dependencies at import
4. ❌ It's deprecated and replaced by newer tests

A file should **NOT** be archived if:
1. ✅ It's a standalone script with `if __name__ == "__main__"` (keep in standalone/)
2. ✅ It's a manual testing script (keep in manual/)
3. ✅ It's a scenario runner (keep in scenarios/)
4. ✅ It's a properly formatted pytest test that can be collected

---

## 🚀 Quick Archive Command

If you want to archive the navigation test that breaks pytest:
```bash
cd /home/kevin/Documents/pokeagent-speedrun
mv tests/navigation/test_exit_moving_van.py tests/archive/test_exit_moving_van.py.bak
```

This will allow `pytest tests/navigation/` to run cleanly.

---

**Note**: The most important cleanup has already been done. The remaining candidates are optional and can be addressed as needed during future development.
