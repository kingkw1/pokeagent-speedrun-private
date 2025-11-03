#!/usr/bin/env python3
"""
Diagnostic: Understand dialog2.state - can we trigger dialogue from it?
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pokemon_env.emulator import EmeraldEmulator

print("=" * 80)
print("Dialog2.state Investigation")
print("=" * 80)

env = EmeraldEmulator('Emerald-GBAdvance/rom.gba', headless=True)
env.initialize()
env.load_state('tests/save_states/dialog2.state')
env.tick(30)

state = env.get_comprehensive_state()
game = state['game']
player = state['player']

print(f"\n📊 Initial State:")
print(f"   in_dialog: {game.get('in_dialog')}")
print(f"   movement_enabled: {game.get('movement_enabled')}")
print(f"   position: ({player['position']['x']}, {player['position']['y']})")

dialogue_text = env.memory_reader.read_dialog()
if dialogue_text:
    print(f"   dialogue text in memory: '{dialogue_text[:80]}...'")
    print(f"   (This is residual text from previous dialogue)")

print(f"\n🎮 Let's try to trigger NEW dialogue by moving and pressing A...")

# Try moving around and pressing A to find an NPC
directions = ['up', 'down', 'left', 'right']
for direction in directions:
    print(f"\n   Trying {direction}...")
    
    # Move in direction
    for _ in range(5):
        env.run_frame_with_buttons([direction])
    for _ in range(24):
        env.run_frame_with_buttons([])
    
    # Press A
    env.run_frame_with_buttons(["A"])
    for _ in range(11):
        env.run_frame_with_buttons(["A"])
    for _ in range(24):
        env.run_frame_with_buttons([])
    
    # Check if dialogue triggered
    state = env.get_comprehensive_state()
    if state['game'].get('in_dialog'):
        print(f"      ✅ Dialogue triggered!")
        new_text = env.memory_reader.read_dialog()
        print(f"      Text: '{new_text[:60]}...'")
        
        # Try to clear it
        print(f"      Clearing dialogue...")
        for i in range(10):
            env.run_frame_with_buttons(["A"])
            for _ in range(11):
                env.run_frame_with_buttons(["A"])
            for _ in range(24):
                env.run_frame_with_buttons([])
            
            if not env.get_comprehensive_state()['game'].get('in_dialog'):
                print(f"      ✅ Cleared after {i+1} presses!")
                break
        else:
            print(f"      ❌ Couldn't clear dialogue")
        
        break
    else:
        print(f"      No dialogue triggered")
else:
    print(f"\n❌ No dialogue triggered from any direction")

print(f"\n✅ Done")
