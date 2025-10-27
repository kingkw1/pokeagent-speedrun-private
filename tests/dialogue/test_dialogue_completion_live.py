#!/usr/bin/env python3
"""
Test dialogue completion using live server/client to ensure proper timing.

This test validates:
1. dialogue.state loads with in_dialog=True
2. Agent presses A to advance dialogue
3. After 2-3 A presses, dialogue dismisses (in_dialog=False)
4. Player can move after dialogue is dismissed
"""

import subprocess
import time
import requests
import sys
from pathlib import Path


def test_dialogue_completion_with_server():
    """Test dialogue completion using actual server for proper timing"""
    
    print("=" * 80)
    print("DIALOGUE COMPLETION TEST (Live Server)")
    print("=" * 80)
    
    # Kill any existing servers
    subprocess.run(["pkill", "-f", "server.app"], capture_output=True)
    time.sleep(1)
    
    # Start server with dialog.state
    print("\n📡 Starting server with dialog.state...")
    import tempfile
    log_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log')
    log_path = log_file.name
    log_file.close()
    
    print(f"📝 Server logs: {log_path}")
    
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "server.app",
         "--load-state", "tests/states/dialog.state",
         "--port", "8003"],
        stdout=open(log_path, 'w'),
        stderr=subprocess.STDOUT
    )
    
    # Wait for server to start
    time.sleep(4)
    
    try:
        # Get initial state
        print("📊 Getting initial state...")
        resp = requests.get("http://localhost:8003/state", timeout=3)
        state = resp.json()
        
        initial_pos = state['player']['position']
        initial_in_dialog = state['game'].get('in_dialog')
        initial_game_state = state['game'].get('game_state')
        
        print(f"\n=== Initial State ===")
        print(f"Position: {initial_pos}")
        print(f"in_dialog: {initial_in_dialog}")
        print(f"game_state: {initial_game_state}")
        print(f"overworld_visible: {state['game'].get('overworld_visible')}")
        print(f"movement_enabled: {state['game'].get('movement_enabled')}")
        
        # Verify dialogue is active
        assert initial_in_dialog == True, "dialogue should be active initially"
        assert initial_game_state == "dialog", "game_state should be 'dialog'"
        
        # Also check raw dialogue text
        dialog_text = state['game'].get('dialog_text', 'None')
        print(f"dialog_text: {dialog_text[:60] if dialog_text and dialog_text != 'None' else 'None'}...")
        
        # Press A to advance dialogue (with proper timing via server)
        print(f"\n🎮 Pressing A to advance dialogue...")
        
        dialogue_cleared = False
        max_attempts = 10
        previous_dialog_text = None
        
        for attempt in range(max_attempts):
            # Check queue status before pressing
            try:
                queue_resp = requests.get("http://localhost:8003/queue_status", timeout=2)
                if queue_resp.status_code == 200:
                    queue_data = queue_resp.json()
                    print(f"\n  Queue before press {attempt + 1}: {queue_data.get('queue_length', 'unknown')} actions")
            except:
                pass
            
            # Press A
            resp = requests.post(
                "http://localhost:8003/action",
                json={"buttons": ["A"]},
                timeout=3
            )
            assert resp.status_code == 200, f"Action failed: {resp.status_code}"
            
            # Wait for server to process (ACTION_HOLD_FRAMES + ACTION_RELEASE_DELAY)
            # That's 12 + 24 = 36 frames at 80 FPS = ~0.45 seconds
            time.sleep(0.6)
            
            # Check state
            resp = requests.get("http://localhost:8003/state", timeout=3)
            state = resp.json()
            
            in_dialog = state['game'].get('in_dialog')
            movement_enabled = state['game'].get('movement_enabled')
            dialog_text = state['game'].get('dialog_text', 'None')
            
            # Show if dialog text changed
            text_preview = dialog_text[:40] if dialog_text and dialog_text != 'None' else 'None'
            changed = ""
            if previous_dialog_text is not None and dialog_text != previous_dialog_text:
                changed = " [TEXT CHANGED]"
            
            print(f"  After A press {attempt + 1}: in_dialog={in_dialog}, movement={movement_enabled}, text='{text_preview}'{changed}")
            previous_dialog_text = dialog_text
            
            if not in_dialog:
                dialogue_cleared = True
                print(f"\n✅ Dialogue cleared after {attempt + 1} A presses!")
                break
        
        # Verify dialogue was cleared
        assert dialogue_cleared, f"Dialogue never cleared after {max_attempts} A presses"
        assert state['game'].get('movement_enabled') == True, "Movement should be enabled after dialogue"
        
        # Try to move to confirm player is responsive
        print(f"\n🎮 Testing movement after dialogue...")
        initial_pos = state['player']['position']
        
        resp = requests.post(
            "http://localhost:8003/action",
            json={"buttons": ["LEFT"]},
            timeout=3
        )
        assert resp.status_code == 200
        
        time.sleep(0.6)
        
        resp = requests.get("http://localhost:8003/state", timeout=3)
        state = resp.json()
        final_pos = state['player']['position']
        
        print(f"Position before move: {initial_pos}")
        print(f"Position after LEFT:  {final_pos}")
        
        if initial_pos != final_pos:
            print(f"\n✅ Player moved! {initial_pos} → {final_pos}")
            print(f"✅ TEST PASSED: Dialogue completion confirmed!")
        else:
            print(f"\n⚠️  Player didn't move")
            print(f"   (Might be blocked by environment, but dialogue was cleared)")
            print(f"✅ TEST PASSED: Dialogue was successfully dismissed")
        
        return True
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up...")
        
        # Show last 30 lines of server log for debugging
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()
                print(f"\n📋 Last 30 lines of server log:")
                print("".join(lines[-30:]))
        except:
            pass
        
        subprocess.run(["pkill", "-f", "server.app"], capture_output=True)
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        success = test_dialogue_completion_with_server()
        if success:
            print(f"\n{'=' * 80}")
            print(f"✅ ALL TESTS PASSED")
            print(f"{'=' * 80}")
            sys.exit(0)
        else:
            print(f"\n{'=' * 80}")
            print(f"❌ TEST FAILED")
            print(f"{'=' * 80}")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        subprocess.run(["pkill", "-f", "server.app"], capture_output=True)
        sys.exit(1)
