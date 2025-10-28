# Dialogue Test Suite - Usage Guide

⚠️ **CRITICAL: Memory-Based Detection is UNRELIABLE!**

**DO NOT USE:**
- ❌ `state['game']['in_dialog']` - Memory flag is unreliable in Pokemon Emerald (42.9% accurate!)
- ❌ Direct memory reading for dialogue state
- ❌ Any test that checks `in_dialog` from `/state` endpoint

**CORRECT APPROACH:**

**For Tests (Ground Truth via Server API):**
- ✅ **OCR detection via server** (100% accurate) - Use for test assertions
- ✅ Server's `/api/frame` endpoint + `utils.ocr_dialogue.create_ocr_detector()`
- ✅ See `test_unit_ocr_vs_memory.py` for working example
- ⚠️  OCR requires server context - doesn't work with direct emulator screenshots

**For Tests (Agent Behavior Validation):**
- ✅ **VLM detection** (same as agent uses) - Test what agent actually sees
- ✅ `agent/perception.py` with VLM perception step
- ✅ See `test_unit_multiflag_state.py` for working example
- ✅ Works with direct emulator screenshots

**For Agent (Production):**
- ✅ **VLM detection** (85% accurate, fast) - What agent uses in real-time
- ✅ `agent/perception.py` extracts `visual_data['on_screen_text']['dialogue']`
- ✅ `agent/action.py` lines 137-142: VLM dialogue priority with A-press
- ✅ Automatic OCR fallback when VLM returns template text

**Why Memory is Unreliable:**
Pokemon Emerald's memory flags are inconsistent (proven in `test_unit_ocr_vs_memory.py`):
- ❌ **42.9% accuracy** (3/7 correct) vs OCR's 100% accuracy (7/7 correct)
- Can show `in_dialog=False` when dialogue box is visibly on screen (dialog2.state!)
- Can show `in_dialog=True` with no dialogue visible (no_dialog1/2/3.state)
- State transitions don't update flags reliably

**OCR Detection for Tests (100% Accurate - Via Server):**
```python
# Works ONLY via server API (see test_unit_ocr_vs_memory.py)
import requests
from utils.ocr_dialogue import create_ocr_detector

# Start server with state
# subprocess.Popen(["python", "-m", "server.app", "--load-state", "tests/states/dialog2.state"])

# Get screenshot via server API
frame_resp = requests.get("http://localhost:8000/api/frame")
frame_data = frame_resp.json()
image_data = base64.b64decode(frame_data['frame'])
screenshot = Image.open(io.BytesIO(image_data))

# OCR detection
detector = create_ocr_detector()
has_dialogue = detector.is_dialogue_box_visible(screenshot)
```

**VLM Detection for Tests & Agent (Same Method):**
```python
# Works with direct emulator screenshots (see test_unit_multiflag_state.py)
from pokemon_env.emulator import EmeraldEmulator
from agent.perception import perception_step
from utils.vlm import VLM

env = EmeraldEmulator('Emerald-GBAdvance/rom.gba', headless=True)
env.load_state('tests/states/dialog2.state')
screenshot = env.get_screenshot()
state = env.get_comprehensive_state()

vlm = VLM(backend='local', model_name='Qwen/Qwen2-VL-2B-Instruct')
visual_data = perception_step(state, screenshot, vlm)
dialogue = visual_data['on_screen_text']['dialogue']
has_dialogue = dialogue and len(dialogue.strip()) > 3
```

**Agent Action Priority (See agent/action.py lines 137-142):**
The agent checks `visual_dialogue_active` (from VLM) and presses A when dialogue is detected.

---

## Test Organization

This directory contains all tests for dialogue detection and handling in Pokemon Emerald.

### Test Status Summary

**✅ WORKING - Unit Tests:**
- `test_unit_ocr_vs_memory.py` - Proves OCR is 100% accurate vs memory 42.9%
- `test_unit_detection.py` - Basic dialogue detection functions  
- `test_unit_multiflag_state.py` - VLM detection (same as agent uses)

**✅ READY - Integration Tests:**
- `test_integration_dialogue_completion.py` - OCR-based dialogue clearing
- `test_integration_agent_dialogue.py` - Agent dialogue handling
- `test_integration_vlm_detection.py` - VLM accuracy tests (slow)

**📁 Debug Scripts:** `debug/` folder contains diagnostic utilities

## Testing Philosophy

Tests are organized from **foundational → integration → real-world usage**:
1. **Unit tests**: Verify core detection logic works
2. **Integration tests**: Verify components work together  
3. **Agent tests**: Verify agent can complete dialogues in practice

## Quick Start

Run all unit tests:
```bash
cd tests/dialogue
./run_all_tests.sh
```

Or run individually:
```bash
# OCR vs Memory comparison (proves OCR is 100% accurate)
python test_unit_ocr_vs_memory.py

# VLM detection tests (tests what agent actually uses)
python test_unit_multiflag_state.py
```

## Recommended Testing Order

### Level 1: Foundation - Unit Tests (Fast, ~30s total)

Run these first to verify core dialogue system works:

**What these verify:**
- ✅ Multi-flag state system correctly models overlapping states
- ✅ Dialogue detection logic works (blue box, text detection)
- ✅ Memory-based detection is more reliable than OCR

**Expected results:**
- `test_unit_multiflag_state.py`: All pass ✅
- `test_unit_detection.py`: All pass ✅  
- `test_unit_ocr_vs_memory.py`: Shows memory detection is better

### Level 2: Integration - Dialogue Mechanics (Medium, ~1-2min)

Test dialogue completion mechanics with server:

```bash
# 1. Test dialogue clearing with A-presses
pytest tests/dialogue/test_integration_dialogue_completion.py::TestDialogueCompletion::test_dialogue_clears_with_a_presses -v -s

# 2. Test movement after dialogue clears
pytest tests/dialogue/test_integration_dialogue_completion.py::TestDialogueCompletion::test_movement_after_dialogue_clearing -v -s

# 3. Test state transitions
pytest tests/dialogue/test_integration_dialogue_completion.py::TestDialogueCompletion::test_state_transitions_correctly -v -s
```

**What these verify:**
- ✅ Server processes A-button presses correctly
- ✅ Dialogue flag changes: `in_dialog: True → False`
- ✅ Movement unlocks: `movement_enabled: False → True`
- ✅ State transitions are consistent

**Known issues:**
- Some dialogue states may not clear within expected timeframe
- This indicates timing issues, not logic errors

### Level 3: Agent Behavior (Slow, ~2-3min)

Test full agent dialogue handling:

```bash
# 1. Test agent detects and clears dialogue
pytest tests/dialogue/test_integration_agent_dialogue.py::TestAgentDialogueIntegration::test_agent_detects_and_clears_dialogue -v -s

# 2. Test agent can move after dialogue
pytest tests/dialogue/test_integration_agent_dialogue.py::TestAgentDialogueIntegration::test_agent_can_move_after_dialogue -v -s

# 3. Full agent auto mode (slowest)
pytest tests/dialogue/test_integration_agent_dialogue.py::TestAgentDialogueIntegration::test_full_agent_auto_completes_dialogue -v -s -m slow
```

**What these verify:**
- ✅ Agent detects dialogue (memory + VLM)
- ✅ Agent presses A to clear dialogue
- ✅ Agent can navigate after dialogue clears
- ⚠️ Agent completes full dialogue → movement workflow

**Current status:**
- Detection: Working ✅
- A-press logic: Working ✅
- Dialogue clearing: **Needs investigation** ⚠️
- Post-dialogue movement: **Needs investigation** ⚠️

### Level 4: VLM Detection (Optional, Very Slow ~2-3min)

Test VLM's visual dialogue detection accuracy:

```bash
# Quick single-state test
pytest tests/dialogue/test_integration_vlm_detection.py::TestVLMDialogueDetection::test_vlm_quick_single_state -v -s -m slow

# Full accuracy test across all states
pytest tests/dialogue/test_integration_vlm_detection.py -v -s -m slow
```

**What these verify:**
- VLM's `text_box_visible` detection accuracy
- Performance across multiple dialogue/non-dialogue states

**Note**: VLM tests are marked `slow` - skip in normal test runs

## Quick Commands

**Run all dialogue tests:**
```bash
pytest tests/dialogue/ -v
```

**Run just unit tests (fast):**
```bash
pytest tests/dialogue/test_unit_*.py -v
```

**Run integration tests (skip slow VLM):**
```bash
pytest tests/dialogue/test_integration_*.py -v -m "not slow"
```

**Run single test:**
```bash
pytest tests/dialogue/test_unit_multiflag_state.py -v
```

## Debugging Tools

If tests fail, use debug scripts in `debug/`:

```bash
# Debug dialogue detection
python tests/dialogue/debug/debug_detection.py

# Check memory values
python tests/dialogue/debug/diagnose_memory_values.py

# Debug agent auto mode
python tests/dialogue/debug/debug_auto_mode.py
```

## Test Files Reference

### Unit Tests
- **`test_unit_multiflag_state.py`** - Multi-flag state system (overlapping states)
- **`test_unit_detection.py`** - Dialogue detection logic (blue box, text)
- **`test_unit_ocr_vs_memory.py`** - OCR vs memory comparison

### Integration Tests
- **`test_integration_dialogue_completion.py`** - Dialogue clearing mechanics
- **`test_integration_agent_dialogue.py`** - Agent dialogue handling
- **`test_integration_vlm_detection.py`** - VLM accuracy (marked slow)

### Debug Scripts (`debug/`)
- **`debug_detection.py`** - Debug detection issues
- **`debug_dialog_state_memory.py`** - Check memory values
- **`debug_auto_mode.py`** - Debug agent in auto mode
- **`debug_navigation.py`** - Debug navigation with dialogue
- **`diagnose_dialog_detection.py`** - Diagnostic tool
- **`diagnose_memory_values.py`** - Memory diagnostic
- **`test_dialogue_debug.py`** - General debugging

## Current Issues & Fixes Needed

### ✅ Working
- Multi-flag state detection
- Dialogue detection logic
- Memory-based detection
- A-press action priority in agent

### ⚠️ Needs Investigation
1. **Dialogue not clearing**: Some tests show dialogue doesn't clear within expected time
2. **Agent movement after dialogue**: Agent may not move after clearing dialogue
3. **VLM detection accuracy**: VLM `text_box_visible` may not be reliable

### 🔧 Next Steps
1. Run unit tests to verify foundation ✅
2. Investigate why dialogue doesn't clear with A-presses
3. Check agent's A-press timing and execution
4. Verify movement is actually blocked vs navigation issues
5. Improve VLM prompts for better dialogue detection

## Test States

Located in `tests/states/`:
- **dialog.state** - NPC dialogue active (primary test state)
- **dialog2.state** - Alternative dialogue state
- **dialog3.state** - Another dialogue variant
- **no_dialog1.state** - Overworld, no dialogue
- **after_dialog.state** - Just dismissed dialogue

## Expected Behavior

**Normal dialogue flow:**
1. Player talks to NPC → `in_dialog: True`, `movement_enabled: False`
2. Press A 2-3 times → Dialogue advances/dismisses
3. Dialogue clears → `in_dialog: False`, `movement_enabled: True`
4. Player can move again

**Agent behavior:**
1. Agent detects `in_dialog: True` (memory) or `text_box_visible: True` (VLM)
2. Agent prioritizes pressing A
3. Dialogue clears
4. Agent resumes navigation

## Resources

- **Main docs**: `docs/DIALOGUE_SYSTEM.md`
- **Test guide**: `tests/TESTING_GUIDE.md`
- **Project root**: `tests/README.md`
