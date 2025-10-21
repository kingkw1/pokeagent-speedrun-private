# Navigation System Redesign - October 21, 2025

## 🚨 Critical Problem Identified

**Issue**: The VLM (Qwen/Qwen2-VL-2B-Instruct) **cannot reliably interpret ASCII text maps** for navigation decisions.

### Evidence

**Test 1: Simple ASCII Map Navigation** (`test_vlm_simple_map.py`)
```
Given Map:
# # # # # # # # # # # # # # #
# # # # # # N # # # # # # # #  <- N = NPC
# # # # # # . . . S # # # # #
# # # # # # . P . S # # # # #  <- P = Player, S = Stairs (EXIT)
# # # # # # # # . S # # # # #
# # # # # # # # # # # # # # #

VLM Response: "Move UP... Move LEFT... Move DOWN... Move RIGHT"
❌ INCORRECT: This path leads into walls and NPCs
✅ CORRECT: Should move RIGHT twice to reach stairs
```

**Result**: VLM provided a completely nonsensical navigation path despite clear ASCII map representation.

### Root Cause

The VLM struggles with:
1. **Spatial reasoning from text** - Cannot correctly interpret 2D ASCII grids
2. **Symbol interpretation** - Confuses NPC markers ('N') with directional hints ("North")
3. **Path planning from text** - Cannot determine shortest path from text representation

## ✅ Solution Implemented: Visual + Programmatic Navigation

### New 3-Step Navigation Strategy

Instead of asking the VLM to read and interpret ASCII maps, we now:

**Step 1: Visual Goal Identification**
- VLM looks at the actual game screenshot
- Task: "Find the visual goal" (stairs, door, exit, NPC to talk to)
- Leverages VLM's strength: computer vision, not text interpretation

**Step 2: Programmatic Movement Preview**
- System reads game memory to determine which tiles are walkable
- Provides 100% accurate `MOVEMENT PREVIEW`:
  ```
  UP   : (2, 1) [.] WALKABLE
  DOWN : (2, 3) [#] BLOCKED - Impassable
  LEFT : (1, 2) [.] WALKABLE
  RIGHT: (3, 2) [.] WALKABLE
  ```
- Ground truth data, no interpretation needed

**Step 3: Simple Direction Choice**
- VLM chooses ONE WALKABLE direction from the preview
- Direction should move player toward the visual goal from Step 1
- Removes burden of spatial reasoning and path planning

### Implementation Changes

**Before** (Old Complex Prompt - ~3000 characters):
```
- Full ASCII map display
- Complex navigation instructions
- Multiple decision rules
- Emphasis on interpreting the map layout
- Strategic goal context
- Recent action history
```

**After** (New Simplified Prompt - ~1500 characters):
```
Playing Pokemon Emerald. Screen: overworld

=== YOUR STRATEGIC GOAL ===
[Brief goal description]

=== NAVIGATION TASK ===

**Step 1: Look at the screenshot** to identify your visual goal

**Step 2: Check the MOVEMENT PREVIEW** below:
[Programmatic WALKABLE/BLOCKED for each direction]

**Step 3: Choose ONE WALKABLE direction** toward your goal

=== DECISION RULES ===
- IF DIALOGUE: Press A
- IF OVERWORLD: Use MOVEMENT PREVIEW + screenshot goal
- IF MENU: UP/DOWN to navigate, A to select
- IF BATTLE: A for moves

Respond with ONLY ONE button name: A, B, UP, DOWN, LEFT, RIGHT, START
```

### Benefits of New Approach

1. **Removes VLM Weakness**: No longer requires ASCII map interpretation
2. **Plays to VLM Strength**: Uses computer vision for goal identification
3. **100% Accurate Data**: Movement preview is programmatically determined
4. **Simpler Decision**: Choose from list of safe options, not complex pathfinding
5. **Reduced Prompt Size**: 50% shorter prompt = faster inference
6. **Clearer Instructions**: 3-step process is easier to follow

## 📊 Testing Results

### Test 1: ASCII Map Understanding (FAILED)
- **Test**: `test_vlm_simple_map.py`
- **Result**: VLM provided incorrect navigation path
- **Conclusion**: Cannot use ASCII maps for navigation

### Test 2: Simplified Prompt (IN PROGRESS)
- **Test**: Running agent with new prompt structure
- **Status**: Prompt successfully simplified, testing navigation behavior
- **Next**: Need clean save state without active dialogue

## 🔍 Key Insights

1. **VLM Capabilities vs Limitations**:
   - ✅ Strong: Visual recognition, object detection, scene understanding
   - ❌ Weak: Text-based spatial reasoning, ASCII grid interpretation

2. **Architectural Lesson**:
   - Don't ask AI to do what programmatic systems can do perfectly
   - Use AI for perception, use code for precise calculations
   - Hybrid approach: AI vision + programmatic safety checks

3. **Prompt Engineering Discovery**:
   - Shorter, focused prompts may work better than comprehensive ones
   - Breaking complex tasks into simple steps improves execution
   - Removing unreliable information sources improves decisions

## 📝 Next Steps

1. ✅ Implement simplified prompt (COMPLETED)
2. ⏳ Test with clean save state (IN PROGRESS)
3. ⏳ Validate navigation from moving van to outside
4. ⏳ Monitor if VLM correctly uses movement preview
5. ⏳ Measure success rate of navigation decisions

## 📚 Related Files

- `/agent/action.py` - Simplified action prompt implementation
- `/test_vlm_simple_map.py` - ASCII map interpretation test (demonstrates failure)
- `/test_vlm_with_screenshot.py` - Screenshot + preview test (for validation)
- `/utils/state_formatter.py` - Movement preview generation

## 🎯 Success Criteria

Navigation redesign will be considered successful when:
1. Agent can navigate out of moving van (initial room) consistently
2. Agent reaches outdoor areas without getting stuck
3. Navigation decisions align with movement preview recommendations
4. Less than 10% of moves are "incorrect" (blocked directions or random A presses)
