#!/usr/bin/env python3
"""
Opener Bot Test Suite

Tests the programmatic opener bot state machine for Pokemon Emerald opening sequence.

This is a standalone test that imports only the opener_bot module directly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import directly from the module file to avoid circular dependencies
import importlib.util
spec = importlib.util.spec_from_file_location(
    "opener_bot",
    os.path.join(os.path.dirname(__file__), '..', 'agent', 'opener_bot.py')
)
opener_bot_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(opener_bot_module)

OpenerBot = opener_bot_module.OpenerBot
get_opener_bot = opener_bot_module.get_opener_bot


def test_state_detection():
    """Test that opener bot correctly detects game states"""
    print("="*80)
    print("TEST: State Detection")
    print("="*80)
    
    bot = OpenerBot()
    
    # Test 1: Title screen detection
    print("\n1. Testing TITLE_SCREEN detection...")
    state_data = {
        'game': {'state': 'title'},
        'player': {'name': '', 'location': ''},
        'milestones': {}
    }
    visual_data = {}
    
    detected_state = bot._detect_current_state(state_data, visual_data)
    assert detected_state == 'TITLE_SCREEN', f"Expected TITLE_SCREEN, got {detected_state}"
    print(f"   ✅ Detected: {detected_state}")
    
    # Test 2: Name selection detection
    print("\n2. Testing NAME_SELECTION detection...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': '????????', 'location': ''},
        'milestones': {'GAME_RUNNING': True}
    }
    
    detected_state = bot._detect_current_state(state_data, visual_data)
    assert detected_state == 'NAME_SELECTION', f"Expected NAME_SELECTION, got {detected_state}"
    print(f"   ✅ Detected: {detected_state}")
    
    # Test 3: Moving van detection
    print("\n3. Testing MOVING_VAN detection...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'MOVING_VAN'},
        'milestones': {'PLAYER_NAME_SET': True}
    }
    
    detected_state = bot._detect_current_state(state_data, visual_data)
    assert detected_state == 'MOVING_VAN', f"Expected MOVING_VAN, got {detected_state}"
    print(f"   ✅ Detected: {detected_state}")
    
    # Test 4: Player's house detection
    print("\n4. Testing PLAYERS_HOUSE detection...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'PLAYERS_HOUSE_2F'},
        'milestones': {'PLAYER_NAME_SET': True}
    }
    
    detected_state = bot._detect_current_state(state_data, visual_data)
    assert detected_state == 'PLAYERS_HOUSE', f"Expected PLAYERS_HOUSE, got {detected_state}"
    print(f"   ✅ Detected: {detected_state}")
    
    # Test 5: Littleroot Town detection
    print("\n5. Testing LITTLEROOT_TOWN detection...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'LITTLEROOT_TOWN'},
        'milestones': {'PLAYER_NAME_SET': True, 'LITTLEROOT_TOWN': True}
    }
    
    detected_state = bot._detect_current_state(state_data, visual_data)
    assert detected_state == 'LITTLEROOT_TOWN', f"Expected LITTLEROOT_TOWN, got {detected_state}"
    print(f"   ✅ Detected: {detected_state}")
    
    # Test 6: Route 101 detection
    print("\n6. Testing ROUTE_101 detection...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'ROUTE_101'},
        'milestones': {'PLAYER_NAME_SET': True, 'ROUTE_101': True}
    }
    
    detected_state = bot._detect_current_state(state_data, visual_data)
    assert detected_state == 'ROUTE_101', f"Expected ROUTE_101, got {detected_state}"
    print(f"   ✅ Detected: {detected_state}")
    
    print("\n✅ All state detection tests passed!")


def test_action_generation():
    """Test that opener bot generates correct actions"""
    print("\n" + "="*80)
    print("TEST: Action Generation")
    print("="*80)
    
    bot = OpenerBot()
    
    # Test 1: Title screen action
    print("\n1. Testing TITLE_SCREEN action...")
    state_data = {
        'game': {'state': 'title'},
        'player': {'name': '', 'location': ''},
        'milestones': {}
    }
    visual_data = {}
    
    action = bot.get_action(state_data, visual_data)
    assert action == ['A'], f"Expected ['A'], got {action}"
    print(f"   ✅ Action: {action}")
    
    # Test 2: Moving van with dialogue (red triangle)
    print("\n2. Testing MOVING_VAN action with dialogue...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'MOVING_VAN'},
        'milestones': {'PLAYER_NAME_SET': True}
    }
    visual_data = {
        'visual_elements': {
            'continue_prompt_visible': True,
            'text_box_visible': True
        }
    }
    
    action = bot.get_action(state_data, visual_data)
    assert action == ['A'], f"Expected ['A'], got {action}"
    print(f"   ✅ Action: {action} (dialogue detected)")
    
    # Test 3: Moving van without dialogue (exit)
    print("\n3. Testing MOVING_VAN action without dialogue...")
    visual_data = {
        'visual_elements': {
            'continue_prompt_visible': False,
            'text_box_visible': False
        }
    }
    
    action = bot.get_action(state_data, visual_data)
    assert action == ['DOWN'], f"Expected ['DOWN'], got {action}"
    print(f"   ✅ Action: {action} (exit van)")
    
    # Test 4: Player's house 2F
    print("\n4. Testing PLAYERS_HOUSE_2F action...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'PLAYERS_HOUSE_2F'},
        'milestones': {'PLAYER_NAME_SET': True}
    }
    visual_data = {
        'visual_elements': {
            'continue_prompt_visible': False,
            'text_box_visible': False
        }
    }
    
    action = bot.get_action(state_data, visual_data)
    assert action == ['DOWN'], f"Expected ['DOWN'], got {action}"
    print(f"   ✅ Action: {action} (go downstairs)")
    
    # Test 5: Route 101 (should return None - VLM takeover)
    print("\n5. Testing ROUTE_101 action (VLM takeover)...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'ROUTE_101'},
        'milestones': {'PLAYER_NAME_SET': True, 'ROUTE_101': True}
    }
    
    action = bot.get_action(state_data, visual_data)
    assert action is None, f"Expected None (VLM takeover), got {action}"
    print(f"   ✅ Action: None (VLM takes over)")
    
    print("\n✅ All action generation tests passed!")


def test_should_handle():
    """Test that opener bot correctly decides when to take control"""
    print("\n" + "="*80)
    print("TEST: Should Handle Decision")
    print("="*80)
    
    bot = OpenerBot()
    
    # Test 1: Should handle title screen
    print("\n1. Testing should_handle for TITLE_SCREEN...")
    state_data = {
        'game': {'state': 'title'},
        'player': {'name': '', 'location': ''},
        'milestones': {}
    }
    visual_data = {}
    
    should_handle = bot.should_handle(state_data, visual_data)
    assert should_handle == True, f"Expected True, got {should_handle}"
    print(f"   ✅ Should handle: {should_handle}")
    
    # Test 2: Should NOT handle after Route 101 milestone
    print("\n2. Testing should_handle after ROUTE_101 milestone...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'ROUTE_101'},
        'milestones': {'ROUTE_101': True}
    }
    
    should_handle = bot.should_handle(state_data, visual_data)
    assert should_handle == False, f"Expected False, got {should_handle}"
    print(f"   ✅ Should handle: {should_handle} (handed off to VLM)")
    
    # Test 3: Should handle moving van
    print("\n3. Testing should_handle for MOVING_VAN...")
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'MOVING_VAN'},
        'milestones': {'PLAYER_NAME_SET': True}
    }
    
    should_handle = bot.should_handle(state_data, visual_data)
    assert should_handle == True, f"Expected True, got {should_handle}"
    print(f"   ✅ Should handle: {should_handle}")
    
    print("\n✅ All should_handle tests passed!")


def test_safety_limits():
    """Test that safety limits work correctly"""
    print("\n" + "="*80)
    print("TEST: Safety Limits")
    print("="*80)
    
    bot = OpenerBot()
    
    # Test 1: Attempt count limit
    print("\n1. Testing attempt count limit...")
    state_data = {
        'game': {'state': 'title'},
        'player': {'name': '', 'location': ''},
        'milestones': {}
    }
    visual_data = {}
    
    # Force state to title screen
    bot._transition_to_state('TITLE_SCREEN')
    
    # Simulate max attempts (title screen has max_attempts=5)
    # After 5 actions, the 6th should return None (fallback)
    actions_taken = []
    for i in range(10):  # Try up to 10 times
        action = bot.get_action(state_data, visual_data)
        if action is None:
            print(f"   ✅ Fallback triggered after {len(actions_taken)} successful actions")
            assert len(actions_taken) == 5, f"Expected 5 actions before fallback, got {len(actions_taken)}"
            break
        actions_taken.append(action)
    else:
        print(f"   ❌ Fallback should have triggered, but got {len(actions_taken)} actions")
        assert False, "Safety limit not triggered"
    
    # Test 2: Time limit (simulate by setting old entry time)
    print("\n2. Testing time limit...")
    bot.reset()
    bot._transition_to_state('TITLE_SCREEN')
    bot.state_entry_time = bot.state_entry_time - 25  # 25 seconds ago (limit is 20s)
    
    action = bot.get_action(state_data, visual_data)
    assert action is None, f"Expected None (timeout), got {action}"
    print(f"   ✅ Timeout triggered correctly")
    
    print("\n✅ All safety limit tests passed!")


def test_global_instance():
    """Test that global instance works correctly"""
    print("\n" + "="*80)
    print("TEST: Global Instance")
    print("="*80)
    
    bot1 = get_opener_bot()
    bot2 = get_opener_bot()
    
    assert bot1 is bot2, "Global instances should be the same object"
    print("   ✅ Global instance works correctly")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("OPENER BOT TEST SUITE")
    print("="*80)
    
    try:
        test_state_detection()
        test_action_generation()
        test_should_handle()
        test_safety_limits()
        test_global_instance()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        return 0
    
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
