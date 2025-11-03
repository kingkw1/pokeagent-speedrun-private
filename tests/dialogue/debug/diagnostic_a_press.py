#!/usr/bin/env python3
"""
Diagnostic: Does pressing A actually clear dialogue in dialog.state?

This will start a server, press A with proper timing, and monitor the in_dialog flag.
"""

import subprocess
import time
import requests

print("="*80)
print("DIAGNOSTIC: Manual A-Press Dialogue Clearing")
print("="*80)

# Start server
print("\n⏳ Starting server with dialog.state...")
server_proc = subprocess.Popen([
    "python", "-m", "server.app",
    "--load-state", "tests/save_states/dialog.state",
    "--port", "8000"
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    # Wait for server to start
    print("⏳ Waiting 8 seconds for server to fully initialize...")
    time.sleep(8)
    
    # Get initial state
    print("\n📊 Initial State:")
    resp = requests.get("http://localhost:8000/state", timeout=3)
    state = resp.json()
    print(f"   in_dialog: {state['game'].get('in_dialog')}")
    print(f"   movement_enabled: {state['game'].get('movement_enabled')}")
    print(f"   position: ({state['player']['position']['x']}, {state['player']['position']['y']})")
    
    # Press A and wait for it to fully process
    # At 80 FPS: 12 hold + 24 release = 36 frames = 0.45s
    # Let's wait 3 seconds to be VERY sure
    for i in range(5):
        print(f"\n🎮 Pressing A (attempt {i+1})...")
        requests.post("http://localhost:8000/action", json={"buttons": ["A"]}, timeout=3)
        
        # Wait LONG enough for action to fully process (3 seconds = 6x the action time)
        print(f"   ⏱️  Waiting 3 seconds for action to process...")
        time.sleep(3)
        
        # Check state
        resp = requests.get("http://localhost:8000/state", timeout=3)
        state = resp.json()
        in_dialog = state['game'].get('in_dialog')
        movement_enabled = state['game'].get('movement_enabled')
        pos = state['player']['position']
        
        print(f"   📊 After press:")
        print(f"      in_dialog: {in_dialog}")
        print(f"      movement_enabled: {movement_enabled}")
        print(f"      position: ({pos['x']}, {pos['y']})")
        
        if not in_dialog:
            print(f"\n✅ SUCCESS! Dialogue cleared after {i+1} A presses!")
            print(f"   Movement is now enabled: {movement_enabled}")
            break
    else:
        print(f"\n❌ FAILED: Dialogue did not clear after 5 A presses")
        print(f"   This suggests dialog.state has infinite/stuck dialogue")
        print(f"   OR the A-button press isn't advancing dialogue")

finally:
    print("\n🛑 Stopping server...")
    server_proc.terminate()
    server_proc.wait(timeout=2)
    print("✅ Done")
