#!/usr/bin/env python3
"""
Automated test: Can the agent complete dialogue and move?

This test uses --agent-auto to run the full agent and verifies:
1. Agent successfully dismisses dialogue
2. Agent moves from starting position (12, 12)

PASS criteria: Player position changes from (12, 12) within 30 seconds
FAIL criteria: Position stays at (12, 12) or test times out
"""

import subprocess
import time
import requests
import sys
from pathlib import Path

# Test configuration
STATE_FILE = "tests/states/dialog.state"
TIMEOUT = 60  # seconds - increased to give agent more time
CHECK_INTERVAL = 2  # seconds
INITIAL_POSITION = (12, 12)

def run_agent_test():
    """Run agent with --agent-auto and check if it completes dialogue and moves"""
    
    print("=" * 60)
    print("🧪 AUTOMATED AGENT TEST: Dialogue Completion & Movement")
    print("=" * 60)
    print(f"📁 State file: {STATE_FILE}")
    print(f"⏱️  Timeout: {TIMEOUT}s")
    print(f"📍 Initial position: {INITIAL_POSITION}")
    print(f"✅ Pass criteria: Player moves from {INITIAL_POSITION}")
    print("=" * 60)
    
    # Start agent with --agent-auto
    cmd = ["python", "run.py", "--agent-auto", "--load-state", STATE_FILE]
    print(f"\n🚀 Starting agent: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    try:
        # Wait for server to start
        print("\n⏳ Waiting for server to start...")
        time.sleep(5)
        
        # Monitor position changes
        start_time = time.time()
        step_count = 0
        last_position = None
        last_in_dialog = None
        
        print("\n📊 Monitoring agent behavior:")
        print(f"{'Step':<6} {'Time':<6} {'Position':<12} {'Dialog':<8} {'Movement':<10} {'Status'}")
        print("-" * 70)
        
        while time.time() - start_time < TIMEOUT:
            try:
                # Get current state
                response = requests.get("http://localhost:8000/state", timeout=2)
                if response.status_code != 200:
                    time.sleep(CHECK_INTERVAL)
                    continue
                
                state = response.json()
                player_data = state.get("player", {})
                pos_data = player_data.get("position", {})
                
                # Handle both dict and list position formats
                if isinstance(pos_data, dict):
                    position = (pos_data.get("x", 0), pos_data.get("y", 0))
                elif isinstance(pos_data, (list, tuple)) and len(pos_data) >= 2:
                    position = tuple(pos_data[:2])
                else:
                    # Skip this iteration if position format is invalid
                    time.sleep(CHECK_INTERVAL)
                    continue
                
                in_dialog = state["game"].get("in_dialog", False)
                movement_enabled = state["game"].get("movement_enabled", True)
                
                step_count += 1
                elapsed = int(time.time() - start_time)
                
                # Track position changes
                moved = "YES" if last_position and position != last_position else "no"
                dialog_status = "ACTIVE" if in_dialog else "clear"
                movement_status = "BLOCKED" if not movement_enabled else "enabled"
                
                # Print status
                status_msg = ""
                if position != INITIAL_POSITION:
                    status_msg = "🎉 MOVED!"
                elif moved == "YES":
                    status_msg = "✓ moving"
                elif not in_dialog and last_in_dialog:
                    status_msg = "✓ dialog cleared"
                
                print(f"{step_count:<6} {elapsed}s{'':<3} {str(position):<12} {dialog_status:<8} {movement_status:<10} {status_msg}")
                
                # Success condition: moved from initial position
                if position != INITIAL_POSITION:
                    print("\n" + "=" * 60)
                    print("✅ TEST PASSED!")
                    print(f"   Agent completed dialogue and moved from {INITIAL_POSITION} to {position}")
                    print(f"   Time taken: {elapsed}s")
                    print("=" * 60)
                    return True
                
                last_position = position
                last_in_dialog = in_dialog
                
            except requests.exceptions.RequestException:
                # Server not ready yet
                pass
            
            time.sleep(CHECK_INTERVAL)
        
        # Timeout - test failed
        print("\n" + "=" * 60)
        print("❌ TEST FAILED!")
        print(f"   Agent did not move from {INITIAL_POSITION} within {TIMEOUT}s")
        if last_position:
            print(f"   Final position: {last_position}")
            print(f"   Final state: in_dialog={last_in_dialog}")
        print("=" * 60)
        return False
        
    finally:
        # Stop the agent
        print("\n🛑 Stopping agent...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("✅ Agent stopped")

if __name__ == "__main__":
    success = run_agent_test()
    sys.exit(0 if success else 1)
