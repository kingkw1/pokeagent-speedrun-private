#!/usr/bin/env python3
"""
Simple test: Run agent on dialog2.state and verify it handles dialogue
"""

import subprocess
import time
import signal

print("="*80)
print("AGENT DIALOGUE HANDLING VERIFICATION")
print("="*80)
print("\nStarting agent on dialog2.state for 10 steps...")
print("Looking for evidence of dialogue detection and A-presses...\n")

# Start agent
process = subprocess.Popen([
    "python", "run.py",
    "--agent-auto",
    "--load-state", "tests/save_states/dialog2.state",
    "--headless"
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

dialogue_detected_count = 0
a_press_count = 0
movement_detected = False
steps_seen = 0
max_steps = 10

try:
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
            
        # Count steps
        if line.startswith('🎮 Step '):
            steps_seen += 1
            if steps_seen > max_steps:
                break
        
        # Count dialogue detections
        if 'text_box_visible=True' in line or 'QWEN-2B FIX] Secondary check complete: text_box_visible=True' in line:
            dialogue_detected_count += 1
            
        # Count A presses
        if "Step" in line and "['A']" in line:
            a_press_count += 1
            print(f"✓ {line.strip()}")
        
        # Detect movement
        if any(f"['{d}']" in line for d in ['UP', 'DOWN', 'LEFT', 'RIGHT']) and "Step" in line:
            if dialogue_detected_count > 0 and a_press_count > 0:
                movement_detected = True
                print(f"✓ {line.strip()}")
    
    # Stop process
    process.terminate()
    try:
        process.wait(timeout=3)
    except:
        process.kill()
    
    print("\n" + "="*80)
    print("RESULTS:")
    print("="*80)
    print(f"Steps observed: {steps_seen}")
    print(f"Dialogue detected (text_box_visible=True): {dialogue_detected_count} times")
    print(f"A button presses: {a_press_count} times")
    print(f"Movement after dialogue+A: {'YES' if movement_detected else 'NO'}")
    
    print("\n" + "="*80)
    if a_press_count >= 2:
        print("✅ SUCCESS - Agent is pressing A when dialogue is detected!")
        if movement_detected:
            print("✅ BONUS - Agent returned to movement after clearing dialogue!")
        exit(0)
    elif dialogue_detected_count > 0:
        print("⚠️  PARTIAL - Agent detected dialogue but didn't press A enough")
        exit(1)
    else:
        print("❌ FAILED - Agent didn't detect dialogue")
        exit(1)
        
except KeyboardInterrupt:
    print("\n\nInterrupted")
    process.kill()
    exit(1)
except Exception as e:
    print(f"\n\nError: {e}")
    process.kill()
    exit(1)
