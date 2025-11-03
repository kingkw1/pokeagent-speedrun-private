#!/usr/bin/env python3
"""
Quick test: Does the agent successfully clear dialogue in dialog2.state?

This will:
1. Load dialog2.state (has visible dialogue)
2. Run agent for a few steps
3. Check if dialogue clears
4. Check if agent returns to navigation
"""

import subprocess
import time
import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

print("="*80)
print("AGENT DIALOGUE CLEARING TEST")
print("="*80)

print("\n🚀 Starting agent with dialog2.state...")
print("   Agent should:")
print("   1. Detect dialogue using VLM (text_box_visible)")
print("   2. Press A to clear dialogue")  
print("   3. Return to navigation once dialogue is gone")
print("")

# Start agent with dialog2.state
process = subprocess.Popen([
    "python", "run.py",
    "--agent-auto",
    "--load-state", "tests/save_states/dialog2.state",
    "--headless"  # Run headless for faster testing
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

try:
    dialogue_detected = False
    dialogue_cleared = False
    a_presses = 0
    step_count = 0
    max_steps = 30  # Monitor for 30 steps then stop
    
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        print(line, end='')
        
        # Count steps
        if 'Step' in line or 'Action:' in line:
            step_count += 1
            if step_count >= max_steps:
                print(f"\n⏰ Reached {max_steps} steps, stopping test...")
                break
        
        # Look for dialogue detection
        if 'VLM detected dialogue box visible' in line or 'text_box_visible' in line or 'DIALOGUE' in line:
            dialogue_detected = True
            
        # Look for A presses
        if 'pressing A' in line or 'Action: A' in line or 'Action: [\'A\']' in line:
            a_presses += 1
            
        # Look for navigation/movement actions
        if any(direction in line for direction in ['UP', 'DOWN', 'LEFT', 'RIGHT']):
            if dialogue_detected and a_presses > 0:
                dialogue_cleared = True
                print("\n" + "="*80)
                print(f"✅ SUCCESS! Agent cleared dialogue after {a_presses} A presses!")
                print("✅ Agent returned to navigation (detected movement action)")
                print("="*80)
                break
    
    # Stop the process
    process.terminate()
    process.wait(timeout=5)
    
    print("\n" + "="*80)
    print("TEST RESULTS:")
    print("="*80)
    print(f"Dialogue detected by VLM: {dialogue_detected}")
    print(f"A button presses: {a_presses}")
    print(f"Dialogue cleared & returned to navigation: {dialogue_cleared}")
    
    if dialogue_cleared:
        print("\n🎉 TEST PASSED - Agent successfully handles dialogues!")
    elif dialogue_detected and a_presses > 0:
        print("\n⚠️  PARTIAL SUCCESS - Agent detected and pressed A, but didn't return to navigation yet")
        print("   (May need more steps, or dialogue not fully cleared)")
    elif dialogue_detected:
        print("\n❌ TEST FAILED - Agent detected dialogue but didn't press A")
    else:
        print("\n❌ TEST FAILED - Agent didn't detect dialogue")
    
except KeyboardInterrupt:
    print("\n\n⚠️  Test interrupted by user")
    process.terminate()
except subprocess.TimeoutExpired:
    print("\n\n⚠️  Test timed out after 30 seconds")
    process.kill()
except Exception as e:
    print(f"\n\n❌ Error: {e}")
    process.terminate()
finally:
    try:
        process.wait(timeout=2)
    except:
        process.kill()
