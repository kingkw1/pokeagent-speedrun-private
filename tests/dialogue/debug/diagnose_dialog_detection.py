#!/usr/bin/env python3
"""
Diagnose why in_dialog detection is behaving incorrectly

This test will:
1. Load dialog.state
2. Check in_dialog flag before any A presses
3. Press A a few times
4. Check in_dialog flag after each A press
5. Try to move
6. Show detailed memory values at each step
"""

import subprocess
import time
import requests
import sys

def get_detailed_state():
    """Get state with detailed dialogue detection info"""
    resp = requests.get("http://localhost:8000/state", timeout=2)
    state = resp.json()
    
    return {
        'in_dialog': state['game'].get('in_dialog'),
        'overworld_visible': state['game'].get('overworld_visible'),
        'movement_enabled': state['game'].get('movement_enabled'),
        'position': (state['player']['position']['x'], state['player']['position']['y']),
        'dialogue_detected': state['game'].get('dialogue_detected', {}),
    }

def main():
    print("=" * 80)
    print("DIALOGUE DETECTION DIAGNOSTIC")
    print("=" * 80)
    
    # Start server
    cmd = ["python", "-m", "server.app", "--load-state", "tests/states/dialog.state"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        print("\n⏳ Starting server (waiting 8 seconds)...")
        time.sleep(8)
        
        # Initial state
        print("\n" + "=" * 80)
        print("STEP 0: Initial State (no actions)")
        print("=" * 80)
        state = get_detailed_state()
        print(f"in_dialog:         {state['in_dialog']}")
        print(f"overworld_visible: {state['overworld_visible']}")
        print(f"movement_enabled:  {state['movement_enabled']}")
        print(f"position:          {state['position']}")
        print(f"dialogue_detected: {state['dialogue_detected']}")
        
        # Press A and monitor
        for i in range(1, 6):
            print(f"\n" + "=" * 80)
            print(f"STEP {i}: After pressing A (attempt #{i})")
            print("=" * 80)
            
            resp = requests.post("http://localhost:8000/action", json={"buttons": ["A"]}, timeout=2)
            print(f"API response: {resp.status_code}")
            
            # Wait for action to process
            time.sleep(3)
            
            state = get_detailed_state()
            print(f"in_dialog:         {state['in_dialog']}")
            print(f"overworld_visible: {state['overworld_visible']}")
            print(f"movement_enabled:  {state['movement_enabled']}")
            print(f"position:          {state['position']}")
            print(f"dialogue_detected: {state['dialogue_detected']}")
            
            # If dialogue cleared, try to move
            if not state['in_dialog']:
                print(f"\n✅ Dialogue cleared after {i} A presses!")
                print("\nTrying to move UP...")
                resp = requests.post("http://localhost:8000/action", json={"buttons": ["UP"]}, timeout=2)
                time.sleep(3)
                
                new_state = get_detailed_state()
                if new_state['position'] != state['position']:
                    print(f"✅ MOVED from {state['position']} to {new_state['position']}")
                else:
                    print(f"❌ Did not move, still at {new_state['position']}")
                break
        else:
            print(f"\n" + "=" * 80)
            print(f"Dialogue did not clear after 5 A presses")
            print("Trying to move anyway...")
            print("=" * 80)
            
            resp = requests.post("http://localhost:8000/action", json={"buttons": ["UP"]}, timeout=2)
            time.sleep(3)
            
            final_state = get_detailed_state()
            if final_state['position'] != state['position']:
                print(f"✅ MOVED from {state['position']} to {final_state['position']}")
                print(f"⚠️  Movement worked even though in_dialog={final_state['in_dialog']}")
            else:
                print(f"❌ Did not move, still at {final_state['position']}")
        
    finally:
        print("\n🛑 Stopping server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()

if __name__ == "__main__":
    main()
