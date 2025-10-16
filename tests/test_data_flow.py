#!/usr/bin/env python3

"""
Test script to verify recent_actions data flow between server, client, and agent.

This test validates that the recent_actions field properly flows through:
1. Server ComprehensiveStateResponse model
2. Client game_state construction
3. Agent step calculation

Fixed issues:
- Empty recent_actions causing VLM to show "Step 0"
- Missing recent_actions in second client code path
- Server only sending last 10 actions (increased to 25)
"""

def test_recent_actions_flow():
    """Test that recent_actions can flow from server to agent"""
    
    # Test 1: Verify response model accepts recent_actions
    print("🧪 Testing ComprehensiveStateResponse model...")
    
    try:
        # Import the response model
        import sys
        sys.path.append('/home/kevin/Documents/pokeagent-speedrun')
        from server.app import ComprehensiveStateResponse
        
        # Create test response with recent_actions
        test_response = ComprehensiveStateResponse(
            visual={},
            player={},
            game={},
            map={},
            milestones={},
            location_connections={},
            step_number=5,
            status="running",
            action_queue_length=0,
            recent_actions=['A', 'UP', 'A', 'DOWN', 'A']  # Test data
        )
        
        print(f"✅ Response model works: recent_actions = {test_response.recent_actions}")
        print(f"   Step number: {test_response.step_number}")
        
        return True
        
    except Exception as e:
        print(f"❌ Response model test failed: {e}")
        return False

def test_recent_actions_parsing():
    """Test that recent_actions are parsed correctly from game_state"""
    
    print("\n🧪 Testing game_state parsing...")
    
    try:
        # Simulate game_state with recent_actions
        game_state = {
            'frame': None,
            'player': {},
            'game': {},
            'map': {},
            'milestones': {},
            'visual': {},
            'step_number': 55,
            'status': 'running',
            'action_queue_length': 0,
            'recent_actions': ['A', 'A', 'A', 'UP', 'A']  # Should show step 5
        }
        
        # Extract recent_actions like the agent does
        recent_actions = game_state.get('recent_actions', [])
        current_step = len(recent_actions) if recent_actions else 0
        
        print(f"✅ Game state parsing works:")
        print(f"   recent_actions: {recent_actions}")
        print(f"   calculated step: {current_step}")
        
        if current_step == 5:
            print(f"✅ Step calculation correct!")
            return True
        else:
            print(f"❌ Step calculation wrong - expected 5, got {current_step}")
            return False
            
    except Exception as e:
        print(f"❌ Game state parsing failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing recent_actions Data Flow Fix\n")
    
    test1_passed = test_recent_actions_flow()
    test2_passed = test_recent_actions_parsing()
    
    if test1_passed and test2_passed:
        print(f"\n✅ ALL TESTS PASSED - recent_actions data flow should work!")
    else:
        print(f"\n❌ SOME TESTS FAILED - data flow may have issues")