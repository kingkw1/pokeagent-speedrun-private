# Battle Test Suite

Tests for Pokemon battle mechanics, including wild encounters, trainer battles, and battle completion detection.

---

## 🎯 Test Overview

### Battle Completion Detection

**Primary Method**: `game_data['in_battle']` flag from memory reader  
**Reliability**: High - Uses pokeemerald-based memory flag detection  
**Location**: `pokemon_env/memory_reader.py` lines 508-530

**Detection Logic**:
1. Checks `gMain.inBattle` flag (primary indicator)
2. Validates with `BATTLE_TYPE_FLAGS` (secondary check)
3. Returns `True` during battle, `False` when battle ends

**Success Criteria**:
- `in_battle=True` at start
- `in_battle=False` after battle completes (win, lose, run, capture)
- Player position restored to overworld
- Location visible (not "Currently in battle")

---

## ✅ Active Tests

### `test_wild_battle_completion.py` ⭐ **Primary Test**
**Purpose**: Verify agent can complete a wild battle through any means  
**Start State**: `tests/save_states/wild_battle.state`  
**Success Criteria**: 
- Battle starts with `in_battle=True`
- Battle ends with `in_battle=False`
- Agent returns to overworld (location visible, position shown)
- Max 200 steps (generous for any outcome)

**Accepts any outcome**:
- ✅ Defeat opponent Pokemon
- ✅ Run away successfully
- ✅ Capture Pokemon
- ✅ Use items/switch Pokemon (if applicable)

**Run it**:
```bash
source /home/kevin/Documents/pokeagent-speedrun/.venv/bin/activate
python tests/battle/test_wild_battle_completion.py
```

---

## 🔍 Battle State Detection

### Memory-Based Detection (Reliable)

**Flag Location**: `gMain.inBattle` at address `0x03005D8C` (bitmask `0x01`)

**Example from logs**:

**During Battle**:
```
=== BATTLE MODE ===
Currently in battle - map and dialogue information hidden

Battle Type: Unknown
--- YOUR POKÉMON ---
TORCHIC (Lv.5) HP: 19/19
```

**After Battle (Run Away)**:
```
=== PLAYER INFO ===
Position: X=14, Y=12
=== LOCATION & MAP INFO ===
Current Location: ROUTE 101
--- MAP: ROUTE 101 ---
  P = Player at (14, 12)
```

**Key Differences**:
- In battle: "Currently in battle" message, no map shown
- After battle: Location visible, map displayed, position shown

---

## 📁 Test Files

### Current Tests

1. **`test_wild_battle_completion.py`** - Basic battle completion test
2. **`test_battle_victory.py`** - *(Future)* Specific test for winning battles
3. **`test_battle_run.py`** - *(Future)* Specific test for running away
4. **`test_battle_capture.py`** - *(Future)* Test for catching Pokemon

---

## 🎮 Creating Battle Tests

### Template

```python
#!/usr/bin/env python3
"""
Battle Test: [Test Name]

Objective: [Clear objective]
Start: wild_battle.state (in battle with wild Wurmple)
Success: Battle completes (any outcome)
Max steps: 200
"""

import subprocess
import time
import requests
import json

def test_battle_completion():
    print("="*80)
    print("BATTLE TEST: Wild Battle Completion")
    print("="*80)
    
    # Start agent with battle state
    process = subprocess.Popen([
        "/home/kevin/Documents/pokeagent-speedrun/.venv/bin/python",
        "run.py",
        "--agent-auto",
        "--load-state", "tests/save_states/wild_battle.state",
        "--headless"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    # Wait for server to start
    time.sleep(5)
    
    # Check initial state
    initial_state = requests.get("http://localhost:8000/state").json()
    initial_in_battle = initial_state.get('game', {}).get('in_battle', False)
    
    print(f"\n📊 Initial state:")
    print(f"   in_battle: {initial_in_battle}")
    assert initial_in_battle == True, "Should start in battle"
    
    # Monitor until battle ends or timeout
    steps = 0
    max_steps = 200
    battle_ended = False
    
    try:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            
            # Check for step completion
            if "Step " in line and ":" in line:
                steps += 1
                
                # Check battle status every 10 steps
                if steps % 10 == 0:
                    try:
                        state = requests.get("http://localhost:8000/state", timeout=2).json()
                        in_battle = state.get('game', {}).get('in_battle', False)
                        location = state.get('game', {}).get('location', 'Unknown')
                        
                        print(f"\n📊 Step {steps}: in_battle={in_battle}, location={location}")
                        
                        if not in_battle:
                            print(f"\n✅ Battle ended at step {steps}!")
                            print(f"   Final location: {location}")
                            battle_ended = True
                            break
                    except:
                        pass
                
                if steps >= max_steps:
                    print(f"\n❌ Reached max steps ({max_steps})")
                    break
    
    finally:
        process.terminate()
        process.wait(timeout=5)
    
    assert battle_ended, f"Battle did not complete in {max_steps} steps"
    print(f"\n✅ TEST PASSED - Battle completed in {steps} steps")

if __name__ == "__main__":
    test_battle_completion()
```

---

## 🔧 Battle State Fields

### Key Fields to Monitor

**`game_data['in_battle']`** (bool)
- `True` = Currently in battle
- `False` = Not in battle (overworld)

**`game_data['battle_info']`** (dict or None)
- Present during battle
- Contains: `player_pokemon`, `opponent_pokemon`, `battle_type`
- `None` or empty when not in battle

**`game_data['location']`** (str)
- During battle: Often empty or "Unknown"
- After battle: Shows actual location ("ROUTE 101", etc.)

**State formatting**:
- During battle: "=== BATTLE MODE ===" header
- After battle: "=== PLAYER INFO ===" header with map

---

## 🎯 Success Criteria

A battle test should verify:

1. **Battle Start Detection**
   - `in_battle=True` at test start
   - Battle info present
   - "BATTLE MODE" in state formatting

2. **Battle Progression**
   - Agent makes valid battle decisions
   - HP changes detected
   - Battle continues without crashes

3. **Battle End Detection** ✅ **Most Important**
   - `in_battle=False` after completion
   - Location becomes visible
   - Map/position data restored
   - Player can move in overworld

4. **Any Outcome Accepted**
   - Victory (opponent faints)
   - Run away (escape successful)
   - Capture (throw pokeball)
   - Defeat (player faints - respawn)

---

## 📊 Test Results Format

```
================================================================================
BATTLE TEST RESULTS
================================================================================
Initial state: in_battle=True ✅
Battle duration: 47 steps
Outcome: Run away successful
Final state: in_battle=False ✅
Location: ROUTE 101 ✅
Position: (14, 12) ✅

✅ TEST PASSED - Battle completed successfully
================================================================================
```

---

## 🚀 Running Battle Tests

### Single Test
```bash
# Activate venv
source /home/kevin/Documents/pokeagent-speedrun/.venv/bin/activate

# Run specific test
python tests/battle/test_wild_battle_completion.py
```

### All Battle Tests
```bash
# Run with pytest
pytest tests/battle/ -v

# Or run all .py files
for test in tests/battle/test_*.py; do
    python "$test"
done
```

---

## 🐛 Troubleshooting

### Battle doesn't end
- Check if agent is stuck in a loop
- Verify RUN action is being selected
- Check if battle_info is being read correctly

### False positive - battle end detected too early
- Verify `in_battle` flag timing
- May need to add delay after detection
- Check if battle transition is complete

### Agent crashes during battle
- Check battle_info None handling (fixed in perception.py, action.py)
- Verify VLM fallback works for battle screens
- Check opponent_pokemon data availability

---

**Last Updated**: November 3, 2025  
**Status**: Battle completion detection working ✅  
**Primary Test**: `test_wild_battle_completion.py`
