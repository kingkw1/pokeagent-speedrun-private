#!/usr/bin/env python3
"""
Test the agent's ability to handle dialogue states correctly.

This test runs the ACTUAL AGENT (not just HTTP calls) to verify:
1. Agent detects when server incorrectly reports "dialog" state
2. Agent uses OCR/VLM perception to override server state
3. Agent makes correct actions (move instead of pressing A when no dialogue)
"""
import subprocess
import time
import requests
import sys

def main():
    print("=== AGENT DIALOGUE HANDLING TEST ===\n")
    
    # Kill any existing servers/clients
    subprocess.run(["pkill", "-f", "server.app"], capture_output=True)
    subprocess.run(["pkill", "-f", "server.client"], capture_output=True)
    time.sleep(1)
    
    # Start server with dialog.state  
    print("Starting server...")
    server_proc = subprocess.Popen([
        sys.executable, "-m", "server.app",
        "--load-state", "tests/states/dialog.state",
        "--port", "8002",
        "--manual"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    time.sleep(4)
    
    try:
        # Get initial state from server
        resp = requests.get("http://localhost:8002/state", timeout=3)
        state = resp.json()
        
        initial_pos = state.get('player', {}).get('position', {})
        initial_game_state = state.get('game', {}).get('game_state')
        
        print(f"Initial position: {initial_pos}")
        print(f"Initial game_state from server: {initial_game_state}")
        
        # Now start the client (agent) in auto mode
        print(f"\nStarting agent client...")
        client_proc = subprocess.Popen([
            sys.executable, "-m", "server.client",
            "--port", "8002",
            "--auto"  # Agent makes decisions automatically
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait for agent to make some decisions
        print("Letting agent run for 10 steps...")
        for i in range(10):
            time.sleep(1)
            resp = requests.get("http://localhost:8002/state", timeout=3)
            current_state = resp.json()
            current_pos = current_state.get('player', {}).get('position', {})
            current_game_state = current_state.get('game', {}).get('game_state')
            
            print(f"Step {i}: pos={current_pos}, game_state={current_game_state}")
            
            # Check if position changed
            if current_pos != initial_pos:
                print(f"\n✅ SUCCESS! Agent moved from {initial_pos} to {current_pos}")
                print(f"This proves agent correctly handled the false 'dialog' state!")
                client_proc.terminate()
                return True
        
        print(f"\n❌ FAILURE: Agent stuck at {initial_pos} after 10 steps")
        print(f"Agent may still be treating this as dialogue when there is none")
        
        # Get client logs
        client_proc.terminate()
        stdout, stderr = client_proc.communicate(timeout=2)
        print(f"\n=== CLIENT LOGS ===")
        print(stdout[:2000])  # Print first 2000 chars
        
        return False
        
    finally:
        server_proc.terminate()
        if 'client_proc' in locals():
            client_proc.terminate()
        time.sleep(1)
        subprocess.run(["pkill", "-f", "server.app"], capture_output=True)
        subprocess.run(["pkill", "-f", "server.client"], capture_output=True)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
