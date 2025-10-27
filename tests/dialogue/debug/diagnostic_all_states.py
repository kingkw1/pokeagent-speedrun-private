#!/usr/bin/env python3
"""
Diagnostic: Test all dialog*.state files to find one that works
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pokemon_env.emulator import EmeraldEmulator

def test_state(state_file):
    """Test if a dialogue state can be cleared."""
    print("=" * 80)
    print(f"Testing: {state_file}")
    print("=" * 80)
    
    env = EmeraldEmulator('Emerald-GBAdvance/rom.gba', headless=True)
    env.initialize()
    env.load_state(f'tests/states/{state_file}')
    env.tick(30)
    
    # Get initial state
    state = env.get_comprehensive_state()
    game = state['game']
    
    print(f"\n📊 Initial State:")
    print(f"   in_dialog: {game.get('in_dialog')}")
    print(f"   movement_enabled: {game.get('movement_enabled')}")
    
    dialogue_text = env.memory_reader.read_dialog()
    if dialogue_text:
        print(f"   dialogue: '{dialogue_text[:60]}...'")
    else:
        print(f"   dialogue: (none)")
        return False
    
    # Try pressing A
    print(f"\n🎮 Pressing A (max 10 times)...")
    for i in range(10):
        # Press A with proper timing
        env.run_frame_with_buttons(["A"])
        for _ in range(11):
            env.run_frame_with_buttons(["A"])
        for _ in range(24):
            env.run_frame_with_buttons([])
        
        # Check if cleared
        state = env.get_comprehensive_state()
        in_dialog = state['game'].get('in_dialog')
        
        if not in_dialog:
            print(f"   ✅ Dialogue cleared after press {i+1}!")
            return True
        
        # Check if text changed
        new_text = env.memory_reader.read_dialog()
        if new_text != dialogue_text:
            print(f"   📝 Press {i+1}: Text changed")
            print(f"      New: '{new_text[:60]}...'")
            dialogue_text = new_text
        else:
            print(f"   ⏸️  Press {i+1}: Text unchanged")
    
    print(f"   ❌ Dialogue didn't clear after 10 presses")
    return False

# Test all dialog states
states = ['dialog.state', 'dialog2.state', 'dialog3.state']

for state_file in states:
    result = test_state(state_file)
    print(f"\nResult: {'PASS' if result else 'FAIL'}")
    print()
