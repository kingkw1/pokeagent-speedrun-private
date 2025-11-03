# Navigation Test Suite

Tests for navigation, pathfinding, and movement in Pokemon Emerald.

---

## 🎯 Test Overview

### ✅ Active Tests

#### `test_exit_moving_van.py` ⭐ **Primary Test**
**Purpose**: Verify agent can navigate out of the initial moving van  
**Start State**: `tests/save_states/truck_start.state`  
**Success Criteria**: Agent presses RIGHT 3 times to exit van and reach Littleroot Town  
**Max Steps**: 20 (manual completion: 3 steps)

**What it tests:**
- Basic directional movement
- Dialogue detection doesn't interfere with navigation
- Agent follows simple spatial instructions

**Expected Output:**
```
Step 1: ['RIGHT']  ← First RIGHT press
Step 2: ['RIGHT']  ← Second RIGHT press  
Step 3: ['RIGHT']  ← Third RIGHT press
✅ SUCCESS! Agent exited MOVING_VAN and reached LITTLEROOT TOWN in 3 steps!
```

**Run it:**
```bash
# Activate venv first!
source /home/kevin/Documents/pokeagent-speedrun/.venv/bin/activate

# Run test
python tests/navigation/test_exit_moving_van.py

# Or with pytest
pytest tests/navigation/test_exit_moving_van.py -v
```

---

#### `test_route_101_north.py`
**Purpose**: Navigate north through Route 101  
**Start State**: `tests/save_states/route101_start.state` (if exists)  
**Success Criteria**: Move from starting position to Y≤5 (northern area)  
**Max Steps**: 100

**What it tests:**
- Longer navigation sequences
- Handling obstacles/grass
- Maintaining directional consistency

---

#### `test_navigation_enhanced.py`
**Purpose**: Enhanced navigation with obstacles  
**Features**: Tests pathfinding around barriers

---

#### `test_navigation_integration.py`
**Purpose**: Full navigation system integration  
**Features**: Tests complete navigation pipeline

---

#### `test_route_101_navigation.py`
**Purpose**: Route 101 specific navigation tests  
**Features**: Detailed Route 101 scenarios

---

## 🚀 Running Navigation Tests

### Run All Navigation Tests
```bash
# Activate venv
source /home/kevin/Documents/pokeagent-speedrun/.venv/bin/activate

# Run all
pytest tests/navigation/ -v

# Or individually
python tests/navigation/test_exit_moving_van.py
python tests/navigation/test_route_101_north.py
```

### Quick Test (Moving Van)
```bash
# Fastest way to verify navigation works
/home/kevin/Documents/pokeagent-speedrun/.venv/bin/python tests/navigation/test_exit_moving_van.py
```

---

## 📊 What Success Looks Like

### Moving Van Test (Primary)
```
🎮 Step 1: ['RIGHT']
🎮 Step 2: ['RIGHT']
🎮 Step 3: ['RIGHT']
🎯 SUCCESS! Agent pressed RIGHT 3 times to exit van!
✅ SUCCESS - Agent exited MOVING_VAN and reached LITTLEROOT TOWN in 3 steps!
```

**Interpretation:**
- ✅ Agent correctly identified RIGHT as exit direction
- ✅ Agent moved consistently in one direction
- ✅ Agent reached target location efficiently
- ✅ Matched manual performance (3 steps)

### Common Issues

#### Agent Presses A Instead of Moving
**Symptom:** Agent keeps pressing A, no movement
**Cause:** Dialogue detection false positive
**Fix:** Check HUD filtering in `agent/perception.py`

#### Agent Oscillates Between Positions
**Symptom:** Agent moves UP then DOWN repeatedly
**Cause:** Objective/navigation logic conflict
**Fix:** Check objective planner output

#### Agent Doesn't Move at All
**Symptom:** No actions taken
**Cause:** Action selection returns None
**Fix:** Check VLM action decision logs

---

## 🧪 Testing Strategy

### 1. Start Simple (Moving Van)
The moving van test is intentionally simple:
- Only one correct direction (RIGHT)
- Short sequence (3 steps)
- Clear success condition (location change)

**Why this matters:** If the agent can't exit the van, more complex navigation won't work.

### 2. Progress to Routes
Route tests add complexity:
- Multiple valid paths
- Longer sequences
- Obstacles and terrain

### 3. Integration Testing
Full navigation system tests:
- Pathfinding algorithms
- Obstacle avoidance
- Multi-room navigation

---

## 📝 Adding New Navigation Tests

### Template
```python
#!/usr/bin/env python3
"""
Navigation Test: [Test Name]

Objective: [Clear objective description]
Start: [Start location/state]
Target: [Target location/condition]
Manual completion: [X steps]
Max allowed: [Y steps]
"""

import subprocess
import time
import re

def test_[test_name]():
    print("="*80)
    print("NAVIGATION TEST: [Test Name]")
    print("="*80)
    
    # Start agent
    process = subprocess.Popen([
        "/home/kevin/Documents/pokeagent-speedrun/.venv/bin/python",
        "run.py",
        "--agent-auto",
        "--load-state", "tests/save_states/[state].state",
        "--headless"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    # Track progress
    start_location = "[START]"
    target_location = "[TARGET]"
    steps_seen = 0
    max_steps = 50
    success = False
    
    try:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            
            # Check for success condition
            if target_location in line:
                success = True
                print(f"✅ SUCCESS! Reached {target_location} in {steps_seen} steps")
                break
            
            # Count steps
            if line.startswith('🎮 Step '):
                steps_seen += 1
                if steps_seen > max_steps:
                    print(f"❌ FAILED - Exceeded max steps ({max_steps})")
                    break
    
    finally:
        process.terminate()
        process.wait(timeout=5)
    
    assert success, f"Navigation failed: didn't reach {target_location}"

if __name__ == "__main__":
    test_[test_name]()
```

### Best Practices
1. **Use descriptive names**: `test_route_101_north.py` not `test_nav1.py`
2. **Set realistic max steps**: 2-3x manual completion time
3. **Clear success criteria**: Location change, position threshold, etc.
4. **Helpful logging**: Show progress, not just pass/fail
5. **Always use venv**: Include full Python path in subprocess calls

---

## 🐛 Debugging Navigation Tests

### Enable Verbose Logging
```bash
# See all navigation decisions
python tests/navigation/test_exit_moving_van.py 2>&1 | grep -E "Step|Position|Action"
```

### Check Specific Components
```bash
# View map data
grep "MAP DEBUG" output.log

# View movement options
grep "MOVEMENT" output.log

# View VLM decisions
grep "VLM" output.log
```

### Common Debug Patterns
```bash
# Agent stuck?
grep "STUCK" output.log

# Wrong direction?
grep "Position\|Action" output.log | tail -20

# Dialogue interference?
grep "DIALOGUE\|Triangle" output.log
```

---

## 📈 Test Metrics

### Current Performance
- **Moving Van Exit**: ✅ 3 steps (matches manual)
- **Route 101 North**: 🔄 In development
- **Enhanced Navigation**: 🔄 In development

### Target Goals
- All tests should complete within 2x manual steps
- 95%+ success rate on repeated runs
- No false positive dialogue detection during navigation

---

## 🔗 Related Documentation

- **Main Testing Guide**: `tests/TESTING_GUIDE.md`
- **Dialogue Tests**: `tests/dialogue/README.md`
- **Agent Action Logic**: `agent/action.py`
- **Navigation System**: `docs/NAVIGATION_REDESIGN.md`

---

**Last Updated**: November 3, 2025  
**Status**: Moving van test working, other tests in development
**Primary Test**: `test_exit_moving_van.py` - Use this to verify navigation basics
