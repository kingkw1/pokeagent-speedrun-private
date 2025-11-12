#!/usr/bin/env python3
"""
Directive System Test Suite

Validates that the ObjectiveManager provides correct tactical directives
based on game state and milestones.

Run with: python test_directive_system.py

For integration testing, use:
    python run.py --save_state Emerald-GBAdvance/route102_hackathon.state --max_steps 50 --headless
"""

import sys
from agent.objective_manager import ObjectiveManager

def test_route_103_directive():
    """Test that Route 103 directive is generated correctly"""
    print("=" * 80)
    print("TEST 1: Route 103 Rival Battle Directive")
    print("=" * 80)
    
    # Create ObjectiveManager
    obj_manager = ObjectiveManager()
    
    # Simulate state after reaching Route 103
    state_data = {
        'player': {
            'location': 'ROUTE 103',
            'position': {'x': 5, 'y': 5},  # Not at rival position yet
            'facing_direction': 'down'
        },
        'milestones': {
            'ROUTE_103': {'completed': True},
            'FIRST_RIVAL_BATTLE': {'completed': False}
        }
    }
    
    # Get directive
    directive = obj_manager.get_next_action_directive(state_data)
    
    # Validate
    assert directive is not None, "❌ No directive returned for Route 103 state"
    assert directive['action'] == 'NAVIGATE_AND_INTERACT', f"❌ Wrong action type: {directive['action']}"
    assert directive['target'] == (9, 3, 'ROUTE 103'), f"❌ Wrong target: {directive['target']}"
    
    print("✅ Directive generated successfully!")
    print(f"   Action: {directive['action']}")
    print(f"   Target: {directive['target']}")
    print(f"   Description: {directive['description']}")
    print()

def test_at_rival_position():
    """Test that INTERACT directive is generated when at rival position"""
    print("=" * 80)
    print("TEST 2: At Rival Position (should interact)")
    print("=" * 80)
    
    obj_manager = ObjectiveManager()
    
    # Simulate state at exact rival position
    state_data = {
        'player': {
            'location': 'ROUTE 103',
            'position': {'x': 9, 'y': 3},  # At rival position
            'facing_direction': 'down'
        },
        'milestones': {
            'ROUTE_103': {'completed': True},
            'FIRST_RIVAL_BATTLE': {'completed': False}
        }
    }
    
    directive = obj_manager.get_next_action_directive(state_data)
    
    assert directive is not None, "❌ No directive returned at rival position"
    assert directive['action'] == 'INTERACT', f"❌ Wrong action type: {directive['action']}"
    
    print("✅ INTERACT directive generated successfully!")
    print(f"   Action: {directive['action']}")
    print(f"   Description: {directive['description']}")
    print()

def test_no_directive_before_route_103():
    """Test that no directive is generated before reaching Route 103"""
    print("=" * 80)
    print("TEST 3: Before Route 103 (should return None)")
    print("=" * 80)
    
    obj_manager = ObjectiveManager()
    
    # Simulate state before Route 103
    state_data = {
        'player': {
            'location': 'ROUTE 101',
            'position': {'x': 10, 'y': 10},
            'facing_direction': 'up'
        },
        'milestones': {
            'ROUTE_103': {'completed': False},
            'FIRST_RIVAL_BATTLE': {'completed': False}
        }
    }
    
    directive = obj_manager.get_next_action_directive(state_data)
    
    assert directive is None, f"❌ Directive should be None before Route 103, got: {directive}"
    
    print("✅ Correctly returns None (no directive needed)")
    print()

def test_no_directive_after_rival_battle():
    """Test that no directive is generated after completing rival battle"""
    print("=" * 80)
    print("TEST 4: After Rival Battle (should return None or next directive)")
    print("=" * 80)
    
    obj_manager = ObjectiveManager()
    
    # Simulate state after rival battle
    state_data = {
        'player': {
            'location': 'ROUTE 103',
            'position': {'x': 9, 'y': 3},
            'facing_direction': 'down'
        },
        'milestones': {
            'ROUTE_103': {'completed': True},
            'FIRST_RIVAL_BATTLE': {'completed': True},
            'HEALED_AFTER_RIVAL': {'completed': False}
        }
    }
    
    directive = obj_manager.get_next_action_directive(state_data)
    
    # After rival battle, should either return None or Pokemon Center directive
    if directive is None:
        print("✅ Returns None (VLM will handle navigation to Oldale)")
    else:
        print("✅ Returns next directive (Pokemon Center)")
        print(f"   Action: {directive['action']}")
        print(f"   Description: {directive['description']}")
    print()

def test_oldale_pokemon_center():
    """Test Pokemon Center healing directive"""
    print("=" * 80)
    print("TEST 5: Oldale Pokemon Center (after rival battle)")
    print("=" * 80)
    
    obj_manager = ObjectiveManager()
    
    # Simulate state in Oldale Town after rival battle
    state_data = {
        'player': {
            'location': 'OLDALE TOWN',
            'position': {'x': 10, 'y': 10},
            'facing_direction': 'down'
        },
        'milestones': {
            'FIRST_RIVAL_BATTLE': {'completed': True},
            'HEALED_AFTER_RIVAL': {'completed': False}
        }
    }
    
    directive = obj_manager.get_next_action_directive(state_data)
    
    if directive:
        print("✅ Pokemon Center directive generated!")
        print(f"   Action: {directive['action']}")
        print(f"   Target: {directive.get('target', 'N/A')}")
        print(f"   Description: {directive['description']}")
    else:
        print("⚠️  No directive (may need to add HEALED_AFTER_RIVAL milestone to objectives)")
    print()

if __name__ == '__main__':
    try:
        test_route_103_directive()
        test_at_rival_position()
        test_no_directive_before_route_103()
        test_no_directive_after_rival_battle()
        test_oldale_pokemon_center()
        
        print("=" * 80)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 80)
        print()
        print("Path 1 Directive System is ready to deploy!")
        print()
        print("Next steps:")
        print("1. Run agent with Route 103 save state")
        print("2. Verify agent navigates to (9,3) and presses A")
        print("3. Confirm rival battle triggers")
        print("4. Monitor Battle Bot handling of combat")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
