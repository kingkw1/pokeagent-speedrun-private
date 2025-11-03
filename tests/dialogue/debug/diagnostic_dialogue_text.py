#!/usr/bin/env python3
"""
Diagnostic: What dialogue text is in dialog.state?

This will load dialog.state and read the actual dialogue text from memory.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pokemon_env.emulator import EmeraldEmulator
import time

print("="*80)
print("DIAGNOSTIC: Dialogue Text in dialog.state")
print("="*80)

# Initialize emulator
env = EmeraldEmulator('Emerald-GBAdvance/rom.gba', headless=True)
env.initialize()

# Load dialog.state
print("\n⏳ Loading dialog.state...")
env.load_state('tests/save_states/dialog.state')

# Let it settle
env.tick(30)

# Get state
state = env.get_comprehensive_state()
game = state['game']
player = state['player']

print(f"\n📊 Game State:")
print(f"   in_dialog: {game.get('in_dialog')}")
print(f"   movement_enabled: {game.get('movement_enabled')}")
print(f"   game_state: {game.get('game_state')}")
print(f"   position: ({player['position']['x']}, {player['position']['y']})")

# Read dialogue text
dialogue_text = env.memory_reader.read_dialog()
print(f"\n💬 Dialogue Text:")
if dialogue_text:
    print(f"   Length: {len(dialogue_text)} characters")
    print(f"   Text: '{dialogue_text}'")
else:
    print(f"   (No dialogue text)")

# Try pressing A and see what happens
print(f"\n🎮 Pressing A...")
for i in range(5):
    print(f"\n   Press {i+1}:")
    env.run_frame_with_buttons(["A"])
    # Hold for 12 frames
    for _ in range(11):
        env.run_frame_with_buttons(["A"])
    # Release for 24 frames
    for _ in range(24):
        env.run_frame_with_buttons([])
    
    # Check state
    state = env.get_comprehensive_state()
    in_dialog = state['game'].get('in_dialog')
    dialogue_text = env.memory_reader.read_dialog()
    
    print(f"      in_dialog: {in_dialog}")
    if dialogue_text:
        print(f"      dialogue: '{dialogue_text[:50]}...'")
    else:
        print(f"      dialogue: (none)")
    
    if not in_dialog:
        print(f"\n   ✅ Dialogue cleared after press {i+1}!")
        break
else:
    print(f"\n   ❌ Dialogue still active after 5 A presses")
    print(f"   This state may have infinite dialogue or require specific actions")

# Cleanup
env.stop()
print(f"\n✅ Done")
