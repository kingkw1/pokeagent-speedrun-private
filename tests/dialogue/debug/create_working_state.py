#!/usr/bin/env python3
"""
Create a working dialogue test state.

This will:
1. Load a clean state (no_dialog1.state)
2. Position player in front of Mom NPC in starting house
3. Press A to trigger dialogue
4. Save as dialog_working.state
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pokemon_env.emulator import EmeraldEmulator
import time

print("=" * 80)
print("Creating Working Dialogue State")
print("=" * 80)

# Initialize
env = EmeraldEmulator('Emerald-GBAdvance/rom.gba', headless=False)  # Show display
env.initialize()

print("\n⏳ Loading no_dialog1.state...")
env.load_state('tests/states/no_dialog1.state')
env.tick(60)  # Let it settle

# Check initial state
state = env.get_comprehensive_state()
game = state['game']
player = state['player']

print(f"\n📊 Initial State:")
print(f"   in_dialog: {game.get('in_dialog')}")
print(f"   position: ({player['position']['x']}, {player['position']['y']})")
print(f"   map: {game.get('map_name', 'unknown')}")

# The player should be in the starting house
# Mom is typically at a fixed position
# Let's explore to find her

print(f"\n🎮 Looking for Mom NPC...")
print(f"   Press A to interact when you see her")
print(f"   Waiting 10 seconds for manual interaction...")

# Wait for user to trigger dialogue manually
for i in range(10):
    env.tick(80)  # 1 second at 80 FPS
    state = env.get_comprehensive_state()
    if state['game'].get('in_dialog'):
        print(f"\n✅ Dialogue triggered!")
        dialogue = env.memory_reader.read_dialog()
        print(f"   Text: '{dialogue[:60]}...'")
        
        # Save this state
        print(f"\n💾 Saving as dialog_working.state...")
        env.save_state('tests/states/dialog_working.state')
        print(f"   ✅ Saved!")
        
        # Test if it can be cleared
        print(f"\n🧪 Testing if dialogue can be cleared...")
        for j in range(10):
            env.run_frame_with_buttons(["A"])
            for _ in range(11):
                env.run_frame_with_buttons(["A"])
            for _ in range(24):
                env.run_frame_with_buttons([])
            
            if not env.get_comprehensive_state()['game'].get('in_dialog'):
                print(f"   ✅ Dialogue cleared after {j+1} presses!")
                break
        else:
            print(f"   ❌ Dialogue didn't clear - this state won't work")
        
        break
    print(f"   {i+1}/10 - no dialogue yet")
else:
    print(f"\n⚠️  No dialogue triggered")
    print(f"   You may need to manually interact with an NPC")
    print(f"   Then run this script again")

print(f"\n✅ Done")
