#!/usr/bin/env python3
"""
Navigation Test: Exit Moving Van

Objective: Navigate out of the MOVING_VAN to reach LITTLEROOT TOWN
This is a simple navigation test - the player just needs to move right
to exit the van and enter Littleroot Town.

Manual completion: 3 steps
Max allowed: 20 steps (gives agent room for exploration/dialogue handling)
"""

import subprocess
import time
import re

print("="*80)
print("NAVIGATION TEST: Exit Moving Van")
print("="*80)
print("\nObjective: Navigate from MOVING_VAN to LITTLEROOT TOWN")
print("Starting agent on truck_start.state...")
print("Max steps: 20\n")

# Start agent
process = subprocess.Popen([
    "python", "run.py",
    "--agent-auto",
    "--load-state", "Emerald-GBAdvance/truck_start.state",
    "--headless"
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

start_location = "MOVING_VAN"
target_location = "LITTLEROOT TOWN"
current_location = start_location
steps_seen = 0
max_steps = 20
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
        
        # Track location from memory reader logs
        # Format: "Current Location: LITTLEROOT TOWN" or similar in state output
        if 'Current Location:' in line or 'current_location' in line.lower():
            # Extract location name
            if 'LITTLEROOT TOWN' in line.upper() or 'LITTLEROOT_TOWN' in line.upper():
                current_location = "LITTLEROOT TOWN"
                print(f"  → Location changed to: {current_location}")
                success = True
                print(f"\n🎯 TARGET REACHED! Exited {start_location} to {current_location}")
                break
            elif 'MOVING VAN' in line.upper() or 'MOVING_VAN' in line.upper():
                current_location = "MOVING_VAN"
        
        # Also check map transitions which indicate location change
        # Format: "🗺️ Triggering map stitcher update for position change"
        # followed by map data that might show new location
        if '🔄 Creating warp connection' in line and 'Littleroot Town' in line:
            print(f"  → Detected warp to Littleroot Town!")
            current_location = "LITTLEROOT TOWN"
            success = True
            print(f"\n🎯 TARGET REACHED! Exited {start_location} to {current_location}")
            # Give it a moment to complete the transition
            time.sleep(2)
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
    print(f"Starting location: {start_location}")
    print(f"Final location: {current_location}")
    print(f"Target: {target_location}")
    print(f"Steps taken: {steps_seen}/{max_steps}")
    
    print("\n" + "="*80)
    if success:
        print(f"✅ SUCCESS - Agent exited {start_location} and reached {current_location} in {steps_seen} steps!")
        print(f"   (Manual best: 3 steps, Agent: {steps_seen} steps)")
        exit(0)
    else:
        print(f"❌ FAILED - Agent still in {current_location}, target was {target_location}")
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
