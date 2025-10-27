#!/usr/bin/env python3
"""
Test if dialogue actually clears when agent presses A

Manually press A and monitor in_dialog flag
"""

import subprocess
import time
import requests

def main():
    print("Starting server with dialog.state...")
    
    # Start just the server (not the full agent)
    cmd = ["python", "-m", "server.app", "--load-state", "tests/states/dialog.state"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # Wait for startup
        print("Waiting 5 seconds for server to initialize...")
        time.sleep(5)
        
        print("\n📊 Initial state:")
        resp = requests.get("http://localhost:8000/state", timeout=2)
        state = resp.json()
        print(f"  in_dialog: {state['game'].get('in_dialog')}")
        print(f"  position: ({state['player']['position']['x']}, {state['player']['position']['y']})")
        
        # Press A multiple times
        for i in range(5):
            print(f"\n🎮 Pressing A (attempt {i+1})...")
            resp = requests.post("http://localhost:8000/action", json={"buttons": ["A"]}, timeout=2)
            print(f"  API response: {resp.status_code}")
            
            # Wait for action to process
            time.sleep(3)
            
            # Check state
            resp = requests.get("http://localhost:8000/state", timeout=2)
            state = resp.json()
            in_dialog = state['game'].get('in_dialog')
            pos = state['player']['position']
            
            print(f"  in_dialog: {in_dialog}")
            print(f"  position: ({pos['x']}, {pos['y']})")
            
            if not in_dialog:
                print(f"\n✅ Dialogue cleared after {i+1} A presses!")
                
                # Try moving UP
                print("\n🎮 Trying to move UP...")
                resp = requests.post("http://localhost:8000/action", json={"buttons": ["UP"]}, timeout=2)
                time.sleep(3)
                
                resp = requests.get("http://localhost:8000/state", timeout=2)
                state = resp.json()
                new_pos = state['player']['position']
                
                if (new_pos['x'], new_pos['y']) != (pos['x'], pos['y']):
                    print(f"  ✅ MOVED to ({new_pos['x']}, {new_pos['y']})")
                else:
                    print(f"  ❌ Did not move, still at ({new_pos['x']}, {new_pos['y']})")
                break
        else:
            print("\n❌ Dialogue did not clear after 5 A presses")
        
    finally:
        print("\n🛑 Stopping server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()

if __name__ == "__main__":
    main()
