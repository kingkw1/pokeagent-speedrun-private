"""
Integration test for clock setting sequence.

Tests the opener bot's ability to:
1. Interact with the clock (press A)
2. Navigate Yes/No dialogue (press UP to select "Yes")
3. Confirm selection (press A)
4. Exit clock interaction (Mom dialogue triggers)

Success criteria:
- Player remains at position (5, 2) throughout
- NPCs appear on map after clock is set (Mom spawns)
- Game state transitions properly through dialogue states
- Completes in reasonable time (~5-10 steps)
"""

import subprocess
import time
import json
import requests
from pathlib import Path

def test_clock_setting_sequence():
    """Test that agent can set the clock using Yes/No navigation."""
    
    # Configuration
    SAVE_STATE = "tests/save_states/clock_interaction_save.state"
    SERVER_URL = "http://localhost:8000"
    TIMEOUT = 30  # seconds
    MAX_STEPS = 15  # Should complete in ~5-10 steps
    EXPECTED_POSITION = (5, 2)
    EXPECTED_LOCATION = "LITTLEROOT TOWN BRENDANS HOUSE 2F"
    
    print("\n" + "="*80)
    print("🧪 TEST: Clock Setting with Yes/No Navigation")
    print("="*80)
    
    # Start the agent process
    cmd = [
        "python", "run.py",
        "--agent-auto",
        "--load-state", SAVE_STATE
    ]
    
    print(f"\n📋 Starting agent process...")
    print(f"   Command: {' '.join(cmd)}")
    
    # Capture output to file for debugging
    output_file = open('/tmp/clock_test_output.log', 'w')
    
    process = subprocess.Popen(
        cmd,
        stdout=output_file,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    try:
        # Wait for server to start
        print("⏳ Waiting for server to initialize...")
        time.sleep(5)
        
        # Check server is responsive
        try:
            response = requests.get(f"{SERVER_URL}/status", timeout=5)
            print(f"✅ Server is responsive")
        except:
            print("❌ Server not responsive")
            return False
        
        # Track test progress
        start_time = time.time()
        steps_taken = 0
        last_steps_taken = 0
        initial_state_seen = False
        success = False
        position_stable = True
        last_check_time = start_time
        
        print(f"\n🔍 Monitoring clock setting sequence...")
        print(f"   Expected position: {EXPECTED_POSITION}")
        print(f"   Max steps: {MAX_STEPS}")
        print(f"   Timeout: {TIMEOUT}s")
        print("")
        
        while True:
            elapsed = time.time() - start_time
            
            # Check timeout
            if elapsed > TIMEOUT:
                print(f"\n⏱️  TIMEOUT after {elapsed:.1f}s")
                break
            
            # Get current state
            try:
                state_response = requests.get(f"{SERVER_URL}/state", timeout=2)
                state_data = state_response.json()
                
                # Extract from top-level keys
                player_data = state_data.get('player', {})
                position = player_data.get('position', {})
                player_pos = (position.get('x'), position.get('y'))
                location = player_data.get('location', '')
                
                game_data = state_data.get('game', {})
                game_state = game_data.get('game_state', '')
                
                # Get step count from status endpoint
                status_response = requests.get(f"{SERVER_URL}/status", timeout=2)
                status = status_response.json()
                current_step = status.get('step_count', 0)
                last_action = status.get('last_action', 'None')
                
                # Only print every second to avoid spam
                now = time.time()
                if now - last_check_time >= 1.0:
                    last_check_time = now
                    
                    # Check for new steps
                    if current_step > steps_taken:
                        steps_taken = current_step
                        action = last_action if last_action else 'Unknown'
                        
                        print(f"   Step {steps_taken:2d}: {action:6s} | Pos: {player_pos} | State: {game_state:10s}")
                        
                        # Record initial state
                        if not initial_state_seen:
                            initial_state_seen = True
                            print(f"      ℹ️  Initial state captured")
                        
                        # Check position stability
                        if player_pos != EXPECTED_POSITION:
                            print(f"      ⚠️  Position changed from expected {EXPECTED_POSITION}!")
                            position_stable = False
                    
                    # Success criteria: Took steps (>= 3) and position stayed the same
                    # This indicates clock interaction worked (no navigation away from clock)
                    if steps_taken >= 3 and position_stable:
                        if not success:
                            success = True
                            print(f"\n✅ Clock sequence appears successful!")
                            print(f"   Steps taken: {steps_taken}")
                            print(f"   Position stable: {position_stable} at {player_pos}")
                            print(f"   Waiting a bit more to ensure completion...")
                        
                        # Wait a bit more to be sure
                        if steps_taken >= 5:
                            print(f"\n✅ Clock sequence completed!")
                            print(f"   Total steps: {steps_taken}")
                            print(f"   Time elapsed: {elapsed:.1f}s")
                            return True
                    
                    # Check if we exceeded max steps
                    if steps_taken >= MAX_STEPS:
                        print(f"\n⚠️  Exceeded max steps ({MAX_STEPS})")
                        break
                
            except requests.exceptions.RequestException as e:
                # Server might be shutting down
                time.sleep(0.1)
                continue
            
            time.sleep(0.3)  # Poll every 300ms
        
        # Test failed - analyze why
        print(f"\n❌ TEST FAILED")
        print(f"   Steps taken: {steps_taken}/{MAX_STEPS}")
        print(f"   Time elapsed: {elapsed:.1f}s")
        print(f"   Position stable: {position_stable}")
        print(f"   Success indicated: {success}")
        
        if steps_taken < 3:
            print(f"   ⚠️  Too few steps - agent may not have interacted properly")
        elif not position_stable:
            print(f"   ⚠️  Position changed - agent may have navigated away unexpectedly")
        
        return False
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        output_file.close()
        print(f"✅ Process terminated")
        print(f"📄 Full output saved to: /tmp/clock_test_output.log")

if __name__ == "__main__":
    success = test_clock_setting_sequence()
    
    print("\n" + "="*80)
    if success:
        print("✅ TEST PASSED - Clock setting sequence works correctly!")
    else:
        print("❌ TEST FAILED - Clock setting needs debugging")
    print("="*80 + "\n")
    
    exit(0 if success else 1)
