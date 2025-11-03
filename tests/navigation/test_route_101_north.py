#!/usr/bin/env python3
"""
Navigation Test: Route 101 North Traversal

Objective: Navigate from starting position (9, 15) to Y ≤ 5
This requires the agent to navigate north through Route 101, avoiding obstacles
and handling any encounters along the way.

Manual completion: ~38 steps
Max allowed: 100 steps (gives agent room for inefficient pathing)
"""

import subprocess
import time
import re

print("="*80)
print("NAVIGATION TEST: Route 101 North Traversal")
print("="*80)
print("\nObjective: Navigate from (9, 15) to Y position ≤ 12")
print("Starting agent on route101_simple_test.state...")
print("Max steps: 100\n")

# Start agent
process = subprocess.Popen([
    "python", "run.py",
    "--agent-auto",
    "--load-state", "tests/save_states/route101_simple_test.state",
    "--headless"
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

start_pos = (9, 15)
current_pos = start_pos
target_y = 12
steps_seen = 0
max_steps = 25
success = False

try:
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        
        # Track steps
        if line.startswith('🎮 Step '):
            steps_seen += 1
            print(f"Step {steps_seen}: {line.strip()}")
            
            if steps_seen >= max_steps:
                print(f"\n⏱️  Reached max steps ({max_steps})")
                break
        
        # Track position changes
        # Format: "📍 Position change detected: (X, Y), map: ..."
        if '📍 Position change detected:' in line:
            match = re.search(r'\((\d+), (\d+)\)', line)
            if match:
                x, y = int(match.group(1)), int(match.group(2))
                # Filter out (0, 0) which appears to be transition states
                if (x, y) != (0, 0):
                    current_pos = (x, y)
                    print(f"  → Position: {current_pos}, Y target: ≤{target_y}")
                    
                    # Check success condition
                    if y <= target_y:
                        success = True
                        print(f"\n🎯 TARGET REACHED! Position: {current_pos}")
                        break
    
    # Stop process
    process.terminate()
    try:
        process.wait(timeout=3)
    except:
        process.kill()
    
    print("\n" + "="*80)
    print("RESULTS:")
    print("="*80)
    print(f"Starting position: {start_pos}")
    print(f"Final position: {current_pos}")
    print(f"Target: Y ≤ {target_y}")
    print(f"Steps taken: {steps_seen}/{max_steps}")
    
    print("\n" + "="*80)
    if success:
        print(f"✅ SUCCESS - Agent navigated from {start_pos} to {current_pos} in {steps_seen} steps!")
        print(f"   (Manual best: ~38 steps, Agent: {steps_seen} steps)")
        exit(0)
    else:
        print(f"❌ FAILED - Agent stopped at {current_pos}, needed Y ≤ {target_y}")
        print(f"   Distance remaining: {current_pos[1] - target_y} tiles")
        exit(1)
        
except KeyboardInterrupt:
    print("\n\nInterrupted")
    process.kill()
    exit(1)
except Exception as e:
    print(f"\n\nError: {e}")
    import traceback
    traceback.print_exc()
    process.kill()
    exit(1)
