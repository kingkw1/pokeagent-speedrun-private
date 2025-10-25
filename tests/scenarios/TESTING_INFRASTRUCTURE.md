# Testing Infrastructure Overview

## Two Types of Testing

Your project has **two complementary testing approaches**:

### 1. **Unit/Component Tests** (`tests/*.py`)
**Purpose:** Test specific features and components in isolation

**Location:** `/tests/` (root level test files)

**Save States Used:** `tests/states/*.state` (16 different states)

**Examples:**
- `test_dialogue_detection.py` - Tests dialogue detection logic
- `test_map_ground_truth_comparison.py` - Validates map reading accuracy
- `test_navigation_vlm.py` - Tests VLM navigation decisions
- `test_perception_integration.py` - Tests perception module
- `test_battle_state_formatting.py` - Tests battle state parsing
- Many more specialized tests...

**Characteristics:**
- ✅ Fast execution (seconds)
- ✅ Test specific features
- ✅ Use pytest framework
- ✅ Focus on correctness of individual components
- ❌ Don't test full agent behavior end-to-end

### 2. **Scenario/Integration Tests** (`tests/scenarios/run_scenarios.py`)
**Purpose:** Test complete agent behavior in real game scenarios

**Location:** `/tests/scenarios/`

**Save States Used:** `tests/scenarios/save_states/*.state`

**Examples:**
- "Exit Moving Van" - Full navigation from van → house → outside
- (More to be added)

**Characteristics:**
- ✅ Test complete agent behavior
- ✅ Validate real-world performance
- ✅ Catch integration issues
- ✅ Progress tracking with tqdm
- ❌ Slower execution (10-30 seconds per test)
- ❌ Require VLM inference

---

## Save State Organization

### `tests/states/` (16 states - Used by unit tests)
```
tests/states/
├── house.state              # Inside Brendan's house
├── house2_upstairs.state    # Upstairs in house
├── upstairs.state           # Another upstairs state
├── truck.state              # Moving van
├── dialog.state             # Active dialogue
├── dialog2.state            # Another dialogue state
├── dialog3.state            # Third dialogue state
├── after_dialog.state       # Post-dialogue
├── no_dialog1.state         # No dialogue (variant 1)
├── no_dialog2.state         # No dialogue (variant 2)
├── no_dialog3.state         # No dialogue (variant 3)
├── npc.state                # Near NPC
├── npc1.state               # Another NPC state
├── torchic.state            # Torchic-related
├── wild_battle.state        # In wild battle
└── simple_test.state        # Simple test case
```

**Purpose:** Quick states for testing specific features (dialogue detection, map reading, NPC interaction, etc.)

### `tests/scenarios/save_states/` (Currently 4 states - For integration tests)
```
tests/scenarios/save_states/
├── truck_start.state               # ✅ Moving van (exit test)
├── truck_start_save_milestones.json
├── mom_dialog_manual_save.state    # Mom dialogue scenario
├── mom_dialog_manual_save_milestones.json
├── set_clock_save.state            # Clock setting scenario
├── set_clock_save_milestones.json
├── mudkip_start_battle_save.state  # Battle scenario
└── mudkip_start_battle_save_milestones.json
```

**Purpose:** Game scenario checkpoints for end-to-end agent testing

### `Emerald-GBAdvance/` (7 states - Legacy/development)
```
Emerald-GBAdvance/
├── truck_start.state          # Original moving van state
├── quick_start_save.state     # Quick development start
├── start.state                # Game start
├── simple_test.state          # Simple test
├── hackathon.state            # Hackathon demo
└── (associated .json files)
```

**Purpose:** Development and manual testing states

---

## Recommendation: Use Both Testing Approaches

### Keep the Unit Tests (`tests/*.py`)
**Why:** They're valuable for:
- Quick validation of specific features
- Regression testing after code changes
- Debugging specific components
- Already written and working

**What to do:** Leave them as-is. They use `tests/states/` and work independently.

### Expand Scenario Tests (`tests/scenarios/`)
**Why:** They're essential for:
- Validating complete agent behavior
- Testing real game progression
- Catching integration issues
- Performance benchmarking

**What to do:** Continue building scenario tests using save states from `tests/scenarios/save_states/`

---

## Available Scenario Ideas

Based on existing save states, you can create these scenario tests:

### Easy Scenarios (Already have save states)
1. ✅ **Exit Moving Van** - `truck_start.state` (DONE!)
2. 🔲 **Handle Mom Dialogue** - `mom_dialog_manual_save.state`
   - Test dialogue detection and advancement
3. 🔲 **Set Clock** - `set_clock_save.state`
   - Test menu navigation and selection
4. 🔲 **Battle with Mudkip** - `mudkip_start_battle_save.state`
   - Test battle move selection

### Medium Scenarios (Can create from `tests/states/`)
5. 🔲 **Exit House to Town** - Use `house.state` or `upstairs.state`
   - Navigate from inside house to outside
6. 🔲 **Talk to NPC** - Use `npc.state` or `npc1.state`
   - Approach and interact with NPCs
7. 🔲 **Handle Wild Battle** - Use `wild_battle.state`
   - Complete a wild Pokemon battle

### Advanced Scenarios (Need new save states)
8. 🔲 **Get Starter Pokemon** - Need save state at lab
9. 🔲 **Navigate to Route 101** - Need Littleroot Town state
10. 🔲 **Reach Oldale Town** - Multi-step navigation

---

## How to Add New Scenario Tests

### Step 1: Create or Copy Save State
```bash
# Option A: Copy existing state
cp tests/states/house.state tests/scenarios/save_states/

# Option B: Create new state (play manually to desired point)
python run.py --manual
# Then save the state in tests/scenarios/save_states/
```

### Step 2: Define Success Function
Edit `tests/scenarios/run_scenarios.py`:

```python
def check_my_scenario(state_data):
    """Success: Description of goal"""
    location = state_data.get('player', {}).get('location', '')
    # Add your success logic
    return location == 'TARGET_LOCATION'
```

### Step 3: Add to TESTS List
```python
TESTS = [
    # ... existing tests ...
    ScenarioTest(
        name="My New Test",
        save_state="tests/scenarios/save_states/my_save.state",
        max_steps=50,
        success_fn=check_my_scenario,
        description="What this test validates"
    ),
]
```

### Step 4: Run
```bash
./run_scenario_tests.sh
```

---

## Running Tests

⚠️ **IMPORTANT: Always activate the virtual environment first!**

```bash
# Activate the virtual environment
source .venv/bin/activate

# Or use the full path to the venv Python
.venv/bin/python -m pytest tests/
```

### Run Unit Tests
```bash
# ✅ CORRECT: Activate venv first
source .venv/bin/activate
python -m pytest tests/

# ✅ ALTERNATIVE: Use venv Python directly
.venv/bin/python -m pytest tests/

# ❌ WRONG: Don't use system Python (missing mgba!)
python -m pytest tests/

# Specific test file
.venv/bin/python -m pytest tests/test_dialogue_detection.py

# Specific test
.venv/bin/python -m pytest tests/test_navigation_vlm.py::test_vlm_navigation

# Or use the helper script
./tests/run_pytest.sh tests/test_dialogue_detection.py
```

### Run Scenario Tests
```bash
# ✅ Activate venv first
source .venv/bin/activate

# All scenarios
./run_scenario_tests.sh

# Specific scenario
python tests/scenarios/run_scenarios.py "exit van"

# List available scenarios
python tests/scenarios/run_scenarios.py --list

# Verbose output
python tests/scenarios/run_scenarios.py -v
```

### Common Issues

**Problem:** `ModuleNotFoundError: No module named 'mgba'`

**Solution:** You're not using the virtual environment!
```bash
# Check which Python you're using
which python

# Should show: /home/kevin/Documents/pokeagent-speedrun/.venv/bin/python
# If not, activate venv:
source .venv/bin/activate
```

**Problem:** `SystemExit` or tests crash during collection

**Solution:** Some test files are standalone scripts, not pytest tests. They've been moved to `tests/standalone/`. Run them directly:
```bash
python tests/standalone/test_vlm_understanding.py
```

---

## Summary

✅ **Keep both testing approaches** - they serve different purposes

✅ **Unit tests (`tests/*.py`)** = Fast, focused, component validation

✅ **Scenario tests (`tests/scenarios/`)** = Slow, comprehensive, end-to-end validation

✅ **You have ~20 save states available** to create new scenario tests from

✅ **Start with easy scenarios** using existing saves (dialogue, battle, navigation)

✅ **Save states are now organized:**
- `tests/states/` → Unit tests
- `tests/scenarios/save_states/` → Scenario tests
- `Emerald-GBAdvance/` → Development/manual testing
