#!/usr/bin/env python3
"""
Simple scripted test: Press A twice to dismiss dialogue, then try movement.

This bypasses the agent entirely and just sends button presses to verify:
1. The emulator processes button presses correctly
2. Dialogue dismisses after 2 A presses
3. Player can move after dialogue clears
"""

import subprocess
import time
import requests
import sys

STATE_FILE = "tests/states/dialog.state"
INITIAL_POSITION = (12, 12)

def send_action(action):
    """Send a button press to the server"""
    try:
        response = requests.post(
            "http://localhost:8000/action",
            json={"action": action},
            timeout=2
        )
        return response.status_code == 200
    except:
        return False

def get_state():
    """Get current game state"""
    try:
        response = requests.get("http://localhost:8000/state", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def main():
    print("=" * 70)
    print("🧪 SCRIPTED BUTTON TEST: Manual Input Sequence")
    print("=" * 70)
    print(f"Sequence: A, A, UP, LEFT, DOWN, RIGHT")
    print(f"Expected: Dialogue dismisses, player moves from {INITIAL_POSITION}")
    print("=" * 70)
    
    # Start server only (no agent)
    cmd = ["python", "-m", "server.app", "--port", "8000", "--load-state", STATE_FILE]
    print(f"\n🚀 Starting server: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for server to start
        print("\n⏳ Waiting for server to start...")
        time.sleep(5)
        
        # Get initial state
        print("\n📊 Checking initial state...")
        state = get_state()
        if not state:
            print("❌ Failed to get initial state")
            return False
        
        pos_data = state["player"]["position"]
        if isinstance(pos_data, dict):
            position = (pos_data["x"], pos_data["y"])
        else:
            position = tuple(pos_data[:2])
        
        in_dialog = state["game"].get("in_dialog", False)
        movement_enabled = state["game"].get("movement_enabled", True)
        
        print(f"   Position: {position}")
        print(f"   in_dialog: {in_dialog}")
        print(f"   movement_enabled: {movement_enabled}")
        
        if not in_dialog:
            print("   ⚠️  WARNING: Dialogue not active initially!")
        
        # Scripted sequence
        sequence = [
            ("A", "Dismiss dialogue (page 1)", 2.0),
            ("A", "Dismiss dialogue (page 2)", 2.0),
            ("UP", "Try moving up", 1.5),
            ("LEFT", "Try moving left", 1.5),
            ("DOWN", "Try moving down", 1.5),
            ("RIGHT", "Try moving right", 1.5),
        ]
        
        print("\n" + "=" * 70)
        print("EXECUTING BUTTON SEQUENCE")
        print("=" * 70)
        
        for i, (button, description, wait_time) in enumerate(sequence, 1):
            print(f"\n[{i}/{len(sequence)}] {button} - {description}")
            
            # Send button
            success = send_action(button)
            if not success:
                print(f"   ❌ Failed to send {button}")
                continue
            
            print(f"   ✓ Sent {button}")
            
            # Wait for game to process
            time.sleep(wait_time)
            
            # Check state
            state = get_state()
            if state:
                pos_data = state["player"]["position"]
                if isinstance(pos_data, dict):
                    new_position = (pos_data["x"], pos_data["y"])
                else:
                    new_position = tuple(pos_data[:2])
                
                in_dialog = state["game"].get("in_dialog", False)
                movement_enabled = state["game"].get("movement_enabled", True)
                game_state = state["game"].get("game_state", "unknown")
                
                print(f"   Position: {position} → {new_position}", end="")
                if new_position != position:
                    print(" ✅ MOVED!")
                else:
                    print()
                
                print(f"   in_dialog: {in_dialog}")
                print(f"   movement_enabled: {movement_enabled}")
                print(f"   game_state: {game_state}")
                
                # Check for success
                if new_position != INITIAL_POSITION:
                    print("\n" + "=" * 70)
                    print("✅ TEST PASSED!")
                    print(f"   Player moved from {INITIAL_POSITION} to {new_position}")
                    print(f"   After {i} button presses: {[b for b,_,_ in sequence[:i]]}")
                    print("=" * 70)
                    return True
                
                position = new_position
        
        # Check final state
        print("\n" + "=" * 70)
        if position != INITIAL_POSITION:
            print("✅ TEST PASSED!")
            print(f"   Player moved from {INITIAL_POSITION} to {position}")
        else:
            print("❌ TEST FAILED!")
            print(f"   Player never moved from {INITIAL_POSITION}")
            print(f"   Final state:")
            print(f"     in_dialog: {in_dialog}")
            print(f"     movement_enabled: {movement_enabled}")
            print(f"     game_state: {game_state}")
        print("=" * 70)
        
        return position != INITIAL_POSITION
        
    finally:
        # Stop the server
        print("\n🛑 Stopping server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("✅ Server stopped")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
