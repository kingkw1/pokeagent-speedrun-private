#!/usr/bin/env python3
"""
Quick Battle State Verification

Tests if we can detect battle state changes.
Run this manually to verify the test logic works.
"""

import subprocess
import time
import requests
import sys

print("="*80)
print("BATTLE STATE DETECTION VERIFICATION")
print("="*80)
print("\nThis test verifies the battle detection logic works correctly.")
print("The agent will start in a battle. You should see:")
print("  1. in_battle=True initially")
print("  2. Battle info displayed (if available)")
print("  3. Periodic status checks")
print("\nPress Ctrl+C when you want to stop.\n")

# Start the agent
process = subprocess.Popen(
    ["/home/kevin/Documents/pokeagent-speedrun/.venv/bin/python",
     "run.py",
     "--agent-auto",
     "--load-state", "tests/save_states/wild_battle.state"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Wait for server
time.sleep(5)

try:
    # Check initial state
    print("📊 INITIAL STATE:")
    response = requests.get("http://localhost:8000/state", timeout=5)
    game = response.json().get('game', {})
    
    print(f"   in_battle: {game.get('in_battle', False)}")
    print(f"   location: {game.get('location', 'Unknown')}")
    
    battle_info = game.get('battle_info')
    if battle_info:
        print(f"   battle_info present: Yes")
        player = battle_info.get('player_pokemon') or {}
        opponent = battle_info.get('opponent_pokemon') or {}
        if player:
            print(f"   player: {player.get('name', '?')} Lv.{player.get('level', '?')}")
        if opponent:
            print(f"   opponent: {opponent.get('name', '?')} Lv.{opponent.get('level', '?')}")
    else:
        print(f"   battle_info: None")
    
    print("\n📡 MONITORING (checking every 5 seconds, press Ctrl+C to stop):\n")
    
    check_count = 0
    while True:
        time.sleep(5)
        check_count += 1
        
        try:
            response = requests.get("http://localhost:8000/state", timeout=2)
            game = response.json().get('game', {})
            in_battle = game.get('in_battle', False)
            location = game.get('location', 'Unknown')
            
            status = "🔥 IN BATTLE" if in_battle else "✅ NOT IN BATTLE"
            print(f"Check {check_count}: {status} | location={location}")
            
            if not in_battle:
                print("\n" + "="*80)
                print("✅ BATTLE ENDED - Detection working correctly!")
                print("="*80)
                break
                
        except Exception as e:
            print(f"⚠️  Error checking state: {e}")

except KeyboardInterrupt:
    print("\n\n⚠️  Stopped by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    print("\n🛑 Stopping agent...")
    process.terminate()
    process.wait(timeout=5)

print("\n✅ Verification complete")
