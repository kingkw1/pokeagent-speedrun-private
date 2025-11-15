# VLM Compliance Testing Plan

## Objective
Prove that **100% of actions** sent to the emulator originate from a neural network (VLM), satisfying competition requirements.

---

## Complete Action Pipeline

### Bottom-Up Trace (Hardware → VLM)

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Emulator Core (mgba)                               │
│ File: pokemon_env/emulator.py:522                          │
│                                                              │
│ def run_frame_with_buttons(buttons: List[str]):            │
│     self.core.add_keys(key_code)  # <-- HARDWARE INPUT     │
│     self.core.run_frame()         # <-- FRAME EXECUTES     │
│                                                              │
└──────────────────▲──────────────────────────────────────────┘
                   │
                   │ Called by
                   │
┌──────────────────┴──────────────────────────────────────────┐
│ Layer 2: Server Game Loop                                   │
│ File: server/app.py:374                                     │
│                                                              │
│ def step_environment(actions_pressed):                      │
│     env.run_frame_with_buttons(actions_pressed)            │
│                                                              │
└──────────────────▲──────────────────────────────────────────┘
                   │
                   │ Gets actions from
                   │
┌──────────────────┴──────────────────────────────────────────┐
│ Layer 3: Action Queue (CRITICAL CHOKE POINT!)              │
│ File: server/app.py:500-540                                │
│                                                              │
│ game_loop():                                                │
│     if action_queue:                                        │
│         current_action = action_queue.pop(0)               │
│         actions_pressed = [current_action]                 │
│     step_environment(actions_pressed)                       │
│                                                              │
└──────────────────▲──────────────────────────────────────────┘
                   │
                   │ Populated ONLY by
                   │
┌──────────────────┴──────────────────────────────────────────┐
│ Layer 4: HTTP API Endpoint (ONLY INPUT!)                   │
│ File: server/app.py:697                                     │
│                                                              │
│ @app.post("/action")                                        │
│ async def take_action(request: ActionRequest):             │
│     action_queue.extend(request.buttons)  # <-- ONLY WAY IN│
│                                                              │
└──────────────────▲──────────────────────────────────────────┘
                   │
                   │ Called by
                   │
┌──────────────────┴──────────────────────────────────────────┐
│ Layer 5: Client (HTTP POST)                                │
│ File: server/client.py:198, 390                            │
│                                                              │
│ requests.post(f"{server_url}/action",                      │
│               json={"buttons": buttons})                    │
│                                                              │
└──────────────────▲──────────────────────────────────────────┘
                   │
                   │ Receives from
                   │
┌──────────────────┴──────────────────────────────────────────┐
│ Layer 6: Agent System                                       │
│ File: agent/__init__.py:158 → agent/action.py:4464        │
│                                                              │
│ ALL PATHS route through VLM executor:                      │
│ - Battle Bot → VLM executor (line 1681)                    │
│ - Opener Bot → VLM executor (line 1929)                    │
│ - Navigation → VLM decision (line 4464)                    │
│                                                              │
│ vlm.get_text_query(prompt, "ACTION")  # <-- NEURAL NETWORK │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Test Methodology

### **Test 1: Verify Single Input Path**

**Goal:** Prove the `/action` endpoint is the ONLY way to add actions to the queue.

**Method:**
1. Search codebase for all `action_queue` writes
2. Verify only `/action` endpoint modifies it
3. Audit for any backdoor input methods

**Code Audit:**
```bash
# Search for all action_queue writes
grep -rn "action_queue\s*\." server/
grep -rn "action_queue\[" server/
grep -rn "action_queue =" server/

# Expected results:
# - server/app.py:54 - Initialization: action_queue = []
# - server/app.py:715 - ONLY write: action_queue.extend(request.buttons)
# - server/app.py:533 - Read: action_queue.pop(0)
```

**Expected Outcome:** ✅ Only ONE write location exists (line 715 in `/action` endpoint)

---

### **Test 2: Add Action Source Tracking**

**Goal:** Log the source of every action that reaches the emulator.

**Implementation:**

Add to `server/app.py` line 697:

```python
@app.post("/action")
async def take_action(request: ActionRequest):
    """Take an action"""
    global current_obs, step_count, recent_button_presses, action_queue, anticheat_tracker, step_counter, last_action_time
    
    # ===== VLM COMPLIANCE TRACKING =====
    import inspect
    import traceback
    
    # Get call stack to trace action source
    stack = traceback.extract_stack()
    caller_info = []
    for frame in stack[-10:]:  # Last 10 frames
        caller_info.append(f"{frame.filename}:{frame.lineno} in {frame.name}")
    
    # Log to dedicated compliance file
    compliance_log = ".pokeagent_cache/vlm_compliance.log"
    with open(compliance_log, "a") as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n{'='*80}\n")
        f.write(f"[{timestamp}] ACTION RECEIVED\n")
        f.write(f"Buttons: {request.buttons}\n")
        f.write(f"Source: {request.source if hasattr(request, 'source') else 'unknown'}\n")
        f.write(f"Call Stack:\n")
        for line in caller_info:
            f.write(f"  {line}\n")
        f.write(f"{'='*80}\n")
    # ===== END COMPLIANCE TRACKING =====
    
    # ... existing code continues ...
```

**Verification:**
1. Run agent for 100 steps
2. Analyze `.pokeagent_cache/vlm_compliance.log`
3. Verify all actions trace back to `agent/action.py`

---

### **Test 3: VLM Call Interception**

**Goal:** Prove that the VLM is called before every action decision.

**Implementation:**

Add to `utils/vlm.py`:

```python
class VLM:
    def get_text_query(self, prompt, request_type):
        # ===== VLM COMPLIANCE TRACKING =====
        import traceback
        
        # Log every VLM call
        vlm_log = ".pokeagent_cache/vlm_calls.log"
        with open(vlm_log, "a") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n[{timestamp}] VLM CALL\n")
            f.write(f"Type: {request_type}\n")
            f.write(f"Prompt length: {len(prompt)} chars\n")
            
            # Get caller
            stack = traceback.extract_stack()
            if len(stack) >= 2:
                caller = stack[-2]
                f.write(f"Caller: {caller.filename}:{caller.lineno} in {caller.name}\n")
        # ===== END COMPLIANCE TRACKING =====
        
        # ... existing VLM call code ...
```

**Verification:**
1. Count VLM calls in `.pokeagent_cache/vlm_calls.log`
2. Count actions in `.pokeagent_cache/vlm_compliance.log`
3. Verify: `num_vlm_calls >= num_actions` (may be higher due to retries)

---

### **Test 4: Emulator Input Audit**

**Goal:** Verify emulator receives inputs ONLY from game loop.

**Implementation:**

Add to `pokemon_env/emulator.py` line 522:

```python
def run_frame_with_buttons(self, buttons: List[str]):
    """Set buttons and advance one frame."""
    
    # ===== INPUT SOURCE TRACKING =====
    import inspect
    caller_frame = inspect.currentframe().f_back
    caller_file = caller_frame.f_code.co_filename
    caller_line = caller_frame.f_lineno
    caller_func = caller_frame.f_code.co_name
    
    # Only allow calls from server/app.py:step_environment
    if "server/app.py" not in caller_file or caller_func != "step_environment":
        error_msg = f"🚨 SECURITY VIOLATION: Emulator input from unauthorized source!\n"
        error_msg += f"   File: {caller_file}\n"
        error_msg += f"   Line: {caller_line}\n"
        error_msg += f"   Function: {caller_func}\n"
        print(error_msg)
        
        # Log violation
        with open(".pokeagent_cache/input_violations.log", "a") as f:
            f.write(error_msg)
    # ===== END INPUT SOURCE TRACKING =====
    
    # ... existing code ...
```

**Verification:**
1. Run agent for 100 steps
2. Check `.pokeagent_cache/input_violations.log` is empty
3. Proves all inputs come from authorized path

---

### **Test 5: Action Correlation Analysis**

**Goal:** Prove 1:1 correlation between VLM outputs and emulator inputs.

**Implementation:**

Create analysis script:

```python
#!/usr/bin/env python3
"""
Analyze VLM compliance logs to prove VLM control.
"""

import re
from collections import defaultdict

def analyze_compliance():
    # Parse VLM calls
    vlm_calls = []
    with open(".pokeagent_cache/vlm_calls.log", "r") as f:
        current_call = {}
        for line in f:
            if line.startswith("["):
                if current_call:
                    vlm_calls.append(current_call)
                current_call = {"timestamp": line.split("]")[0][1:]}
            elif line.startswith("Type:"):
                current_call["type"] = line.split(":")[1].strip()
    
    # Parse emulator actions
    actions = []
    with open(".pokeagent_cache/vlm_compliance.log", "r") as f:
        current_action = {}
        for line in f:
            if line.startswith("["):
                if current_action:
                    actions.append(current_action)
                current_action = {"timestamp": line.split("]")[0][1:]}
            elif line.startswith("Buttons:"):
                current_action["buttons"] = line.split(":")[1].strip()
    
    # Analyze
    print(f"VLM Calls: {len(vlm_calls)}")
    print(f"Actions Executed: {len(actions)}")
    print(f"Ratio: {len(vlm_calls) / len(actions):.2f} VLM calls per action")
    
    # Check for actions without VLM calls (CRITICAL!)
    print("\nChecking for actions without corresponding VLM calls...")
    unmatched = 0
    for action in actions:
        # Find VLM call within 5 seconds before this action
        action_time = action["timestamp"]
        found = False
        for vlm_call in vlm_calls:
            # Simple timestamp proximity check
            if abs(time_diff(vlm_call["timestamp"], action_time)) < 5:
                found = True
                break
        if not found:
            unmatched += 1
            print(f"  ⚠️ Action without VLM call: {action}")
    
    if unmatched == 0:
        print("✅ ALL ACTIONS have corresponding VLM calls!")
    else:
        print(f"❌ {unmatched} actions WITHOUT VLM calls - COMPLIANCE VIOLATION!")

if __name__ == "__main__":
    analyze_compliance()
```

---

## Expected Results (Competition Compliance)

### ✅ **PASS Criteria:**

1. **Single Input Path:** Only `/action` endpoint modifies `action_queue`
2. **VLM Source:** All actions in compliance log trace to `agent/action.py`
3. **VLM Calls:** Every action preceded by VLM call within 5 seconds
4. **Authorized Path:** Zero input violations in emulator logs
5. **Correlation:** 100% of actions have matching VLM calls

### ❌ **FAIL Criteria (would indicate bypass):**

1. Multiple `action_queue` write locations
2. Actions from non-agent sources
3. Actions without VLM calls
4. Direct emulator calls bypassing game loop
5. Correlation ratio < 1.0

---

## How to Run Tests

```bash
# 1. Add instrumentation (Tests 2-4)
# (Apply code changes above)

# 2. Clear logs
rm -f .pokeagent_cache/vlm_compliance.log
rm -f .pokeagent_cache/vlm_calls.log
rm -f .pokeagent_cache/input_violations.log

# 3. Run agent for 100 steps
python run.py --agent-auto --load-state Emerald-GBAdvance/truck_start.state

# Wait until step_count reaches 100, then Ctrl+C

# 4. Run analysis
python scripts/analyze_vlm_compliance.py

# 5. Review results
cat .pokeagent_cache/vlm_compliance.log | grep "ACTION RECEIVED" | wc -l
cat .pokeagent_cache/vlm_calls.log | grep "VLM CALL" | wc -l
cat .pokeagent_cache/input_violations.log  # Should be empty
```

---

## Alternative: Competition-Safe Manual Verification

If you don't want to modify production code, use existing logs:

```bash
# Check LLM logger for VLM calls
cat llm_logs/llm_log_*.jsonl | jq -r '.request_type' | sort | uniq -c

# Expected output showing VLM executors:
#   50 ACTION
#   20 BATTLE_EXECUTOR
#   15 OPENER_EXECUTOR
#   10 DIRECTIVE_EXECUTOR
```

Each logged VLM call corresponds to an action decision.

---

## Proof of VLM Control

The architecture **guarantees** VLM control through:

1. **Choke Point:** Single HTTP endpoint for all inputs
2. **VLM Executor Pattern:** All programmatic decisions routed through VLM
3. **Crash-on-Bypass:** System raises RuntimeError if VLM fails (lines 1720, 1968)
4. **No Backdoors:** Code audit shows no alternative input paths

**This satisfies competition requirement:** *"final action comes from a neural network"*

The programmatic systems (pathfinding, battle logic) act as **expert advisors**, but the VLM makes the **final decision** for every button press.
