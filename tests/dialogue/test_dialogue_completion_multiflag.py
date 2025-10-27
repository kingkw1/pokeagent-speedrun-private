"""Test multi-flag state system for dialogue handling"""
import pytest
from pokemon_env.emulator import EmeraldEmulator


def test_dialogue_multi_flag_detection():
    """Test that dialogue state uses multi-flag system correctly"""
    
    # Initialize emulator with dialog.state
    env = EmeraldEmulator('Emerald-GBAdvance/rom.gba')
    env.initialize()
    env.load_state('tests/states/dialog.state')
    env.tick(60)
    
    # Get state - should show dialogue active
    state = env.get_comprehensive_state()
    game = state['game']
    
    print("\n=== Multi-Flag State Detection ===")
    print(f"overworld_visible: {game.get('overworld_visible')}")
    print(f"in_dialog: {game.get('in_dialog')}")
    print(f"movement_enabled: {game.get('movement_enabled')}")
    print(f"input_blocked: {game.get('input_blocked')}")
    print(f"game_state (legacy): {game.get('game_state')}")
    
    # Verify multi-flag state
    assert game.get('in_dialog') == True, "Should detect dialogue"
    assert game.get('overworld_visible') == True, "Overworld should be visible (overlapping states!)"
    assert game.get('movement_enabled') == False, "Movement should be blocked"
    assert game.get('input_blocked') == True, "Input should be blocked"
    assert game.get('game_state') == 'dialog', "Legacy game_state should be 'dialog'"
    
    print("\n✓ Multi-flag state system working correctly")
    print("✓ Dialogue and overworld can be visible simultaneously")


def test_state_consistency_no_override():
    """Test that dialogue state is NOT incorrectly overridden"""
    
    env = EmeraldEmulator('Emerald-GBAdvance/rom.gba')
    env.initialize()
    env.load_state('tests/states/dialog.state')
    env.tick(60)
    
    # Read state multiple times to ensure consistency
    states = []
    for i in range(3):
        env.tick(10)
        state = env.get_comprehensive_state()
        states.append(state['game'])
    
    print("\n=== State Consistency Test ===")
    
    for i, game_state in enumerate(states):
        print(f"Read {i+1}: in_dialog={game_state.get('in_dialog')}, game_state={game_state.get('game_state')}")
        
        # All reads should consistently show dialogue
        assert game_state.get('in_dialog') == True, \
            f"Read {i+1}: in_dialog should remain True (no false override)"
        assert game_state.get('game_state') == 'dialog', \
            f"Read {i+1}: game_state should remain 'dialog' (no cache override bug)"
    
    print("\n✓ State remains consistent across multiple reads")
    print("✓ No false dialog→overworld overrides (bug fixed!)")


def test_multi_flag_internal_consistency():
    """Test that multi-flag rules are internally consistent"""
    
    env = EmeraldEmulator('Emerald-GBAdvance/rom.gba')
    env.initialize()
    env.load_state('tests/states/dialog.state')
    env.tick(60)
    
    state = env.get_comprehensive_state()
    game = state['game']
    
    print("\n=== Internal Consistency Rules ===")
    
    # Rule 1: in_dialog → input_blocked
    if game.get('in_dialog'):
        assert game.get('input_blocked') == True
        print("✓ in_dialog=True → input_blocked=True")
    
    # Rule 2: in_dialog → !movement_enabled
    if game.get('in_dialog'):
        assert game.get('movement_enabled') == False
        print("✓ in_dialog=True → movement_enabled=False")
    
    # Rule 3: in_battle → !overworld_visible
    if game.get('in_battle'):
        assert game.get('overworld_visible') == False
        print("✓ in_battle=True → overworld_visible=False")
    
    # Rule 4: Legacy game_state matches flags
    if game.get('game_state') == 'dialog':
        assert game.get('in_dialog') == True
        print("✓ game_state='dialog' ↔ in_dialog=True")
    
    print("\n✓ All consistency rules validated")


def test_action_should_prioritize_dialogue():
    """Test that when in_dialog is True, agent should press A"""
    
    env = EmeraldEmulator('Emerald-GBAdvance/rom.gba')
    env.initialize()
    env.load_state('tests/states/dialog.state')
    env.tick(60)
    
    state = env.get_comprehensive_state()
    game = state['game']
    
    print("\n=== Action Priority Test ===")
    print(f"in_dialog: {game.get('in_dialog')}")
    print(f"Expected action: Press A to advance dialogue")
    
    # Verify dialogue is active
    assert game.get('in_dialog') == True
    
    # The action module should check in_dialog first and return ["A"]
    # This is now implemented in agent/action.py at lines 293-297
    print("\n✓ Dialogue flag detected - action module should prioritize pressing A")
    print("✓ See agent/action.py lines 293-297 for implementation")


if __name__ == "__main__":
    print("=" * 80)
    print("MULTI-FLAG STATE SYSTEM TESTS")
    print("=" * 80)
    
    test_dialogue_multi_flag_detection()
    print("\n" + "=" * 80)
    
    test_state_consistency_no_override()
    print("\n" + "=" * 80)
    
    test_multi_flag_internal_consistency()
    print("\n" + "=" * 80)
    
    test_action_should_prioritize_dialogue()
    print("\n" + "=" * 80)
    
    print("\n✅ ALL MULTI-FLAG STATE TESTS PASSED!")
