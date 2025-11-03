#!/usr/bin/env python3
"""
Battle Completion Test

Verifies agent can complete wild battle encounters through any method:
- Defeating opponent
- Running away
- Catching pokemon

Success criteria: in_battle flag transitions from True → False
"""

import subprocess
import time
import requests
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_wild_battle_completion():
    """
    Test that agent can complete a wild battle through any means.
    
    Success = battle ends (in_battle: True → False) regardless of outcome.
    """
    print("="*80)
    print("BATTLE TEST: Wild Battle Completion")
    print("="*80)
    print("\nObjective: Complete wild battle encounter")
    print("Start State: tests/save_states/wild_battle.state")
    print("Success: Battle ends (any outcome accepted)")
    print("Max Steps: 200")
    print("Note: This test verifies battle DETECTION, not agent battle skill\n")
    
    # Path to Python executable and run.py
    venv_python = "/home/kevin/Documents/pokeagent-speedrun/.venv/bin/python"
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    run_script = os.path.join(project_root, "run.py")
    state_file = os.path.join(project_root, "tests/save_states/wild_battle.state")
    
    # Verify state file exists
    if not os.path.exists(state_file):
        print(f"❌ ERROR: State file not found: {state_file}")
        sys.exit(1)
    
    print(f"📂 Loading state: {state_file}")
    print(f"🐍 Using Python: {venv_python}")
    print(f"🎮 Running: {run_script}\n")
    
    # Start agent with battle state
    print("🚀 Starting agent...")
    process = subprocess.Popen(
        [venv_python, run_script, "--agent-auto", "--load-state", state_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=project_root
    )
    
    # Wait for server to initialize
    print("⏳ Waiting for server to start...")
    time.sleep(5)
    
    # Verify server is up
    server_ready = False
    for _ in range(10):
        try:
            response = requests.get("http://localhost:8000/state", timeout=2)
            if response.status_code == 200:
                server_ready = True
                print("✅ Server ready\n")
                break
        except:
            time.sleep(1)
    
    if not server_ready:
        print("❌ ERROR: Server did not start properly")
        process.terminate()
        process.wait(timeout=5)
        sys.exit(1)
    
    # Check initial state
    print("="*80)
    print("INITIAL STATE CHECK")
    print("="*80)
    
    try:
        initial_state = requests.get("http://localhost:8000/state", timeout=5).json()
        game_data = initial_state.get('game', {})
        initial_in_battle = game_data.get('in_battle', False)
        initial_location = game_data.get('location', 'Unknown')
        
        print(f"📊 in_battle: {initial_in_battle}")
        print(f"📍 location: {initial_location}")
        
        # Get battle info if present
        battle_info = game_data.get('battle_info')
        if battle_info:
            player_poke = battle_info.get('player_pokemon') or {}
            opponent_poke = battle_info.get('opponent_pokemon') or {}
            if player_poke or opponent_poke:
                player_name = player_poke.get('name', 'Unknown') if player_poke else 'Unknown'
                player_level = player_poke.get('level', '?') if player_poke else '?'
                opponent_name = opponent_poke.get('name', 'Unknown') if opponent_poke else 'Unknown'
                opponent_level = opponent_poke.get('level', '?') if opponent_poke else '?'
                print(f"\n🔥 Your Pokemon: {player_name} (Lv.{player_level})")
                print(f"🐛 Opponent: {opponent_name} (Lv.{opponent_level})")
        
        if not initial_in_battle:
            print("\n❌ FAIL: Battle should be active at start (in_battle should be True)")
            process.terminate()
            process.wait(timeout=5)
            sys.exit(1)
        
        print("\n✅ Battle is active - test can proceed\n")
        
    except Exception as e:
        print(f"\n❌ ERROR checking initial state: {e}")
        process.terminate()
        process.wait(timeout=5)
        sys.exit(1)
    
    # Monitor battle progress
    print("="*80)
    print("BATTLE PROGRESS MONITORING")
    print("="*80)
    print("(Checking every 2 seconds)\n")
    
    max_steps = 50  # Should complete in ~18 steps
    max_time = 120  # 2 minutes timeout
    battle_ended = False
    final_location = "Unknown"
    start_time = time.time()
    
    try:
        while True:
            # Check if process died
            if process.poll() is not None:
                print(f"\n⚠️  Agent process exited unexpectedly")
                break
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_time:
                print(f"\n{'='*80}")
                print(f"TIME LIMIT REACHED ({max_time}s)")
                print("="*80)
                break
            
            # Check battle status
            try:
                state = requests.get("http://localhost:8000/state", timeout=2).json()
                game_data = state.get('game', {})
                in_battle = game_data.get('in_battle', False)
                location = game_data.get('location', 'Unknown')
                position = game_data.get('position', {})
                x, y = position.get('x', '?'), position.get('y', '?')
                
                # Get step count - try multiple sources
                agent_data = state.get('agent', {})
                steps = (agent_data.get('step_count') or 
                        len(agent_data.get('recent_actions', [])) or
                        int(elapsed / 3.5))  # Rough estimate: ~3.5s per step
                
                status_icon = "🔥" if in_battle else "✅"
                print(f"{status_icon} Time {elapsed:5.1f}s | Step ~{steps:2d} | in_battle={str(in_battle):5} | location={location:20}")
                
                # Check if battle ended
                if not in_battle:
                    print(f"\n{'='*80}")
                    print("BATTLE ENDED!")
                    print("="*80)
                    print(f"✅ Battle completed after ~{steps} steps in {elapsed:.1f}s")
                    print(f"📍 Final location: {location if location != 'Unknown' else 'Returning to overworld...'}")
                    if x != '?' and y != '?':
                        print(f"📌 Position: ({x}, {y})")
                    battle_ended = True
                    final_location = location
                    break
                
                # Check step limit
                if steps >= max_steps:
                    print(f"\n{'='*80}")
                    print(f"MAX STEPS REACHED (~{steps})")
                    print("="*80)
                    break
            
            except Exception as e:
                print(f"⚠️  Warning: Could not check state: {e}")
            
            # Wait before next check
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    
    finally:
        # Clean shutdown
        print("\n🛑 Stopping agent...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    
    # Final results
    print("\n" + "="*80)
    print("BATTLE TEST RESULTS")
    print("="*80)
    
    if battle_ended:
        print(f"\n✅ TEST PASSED - Battle completed successfully")
        print(f"   Final location: {final_location}")
        print(f"   Outcome accepted (win/run/catch/lose - any outcome is valid)")
        print("="*80)
        sys.exit(0)
    else:
        print(f"\n❌ TEST FAILED - Battle did not complete")
        print(f"   Final location: {final_location}")
        print("="*80)
        sys.exit(1)


if __name__ == "__main__":
    test_wild_battle_completion()
