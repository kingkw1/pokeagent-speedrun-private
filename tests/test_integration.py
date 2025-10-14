#!/usr/bin/env python3
"""
Integration test for the enhanced planning system with the actual agent.
This script tests the four-module architecture with the new ObjectiveManager integration.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_agent_integration():
    """Test that the Agent class can use the enhanced planning system"""
    print("🧪 Testing Agent integration with enhanced planning...")
    
    try:
        from agent import Agent
        
        # Create a mock args object for agent initialization
        class MockArgs:
            def __init__(self):
                self.backend = "local"
                self.model_name = "Qwen/Qwen2-VL-2B-Instruct"
                self.simple = False  # Use four-module architecture
                
        mock_args = MockArgs()
        
        # Initialize the agent (this should work without errors)
        agent = Agent(mock_args)
        print("✅ Agent initialized successfully with four-module architecture")
        
        # Create mock game state for testing
        mock_game_state = {
            "frame": None,  # No actual frame needed for planning test
            "player": {
                "location": "Littleroot Town", 
                "money": 3000,
                "position": {"x": 10, "y": 15}
            },
            "game": {
                "state": "overworld",
                "in_battle": False,
                "party_count": 1,
                "party": [{"species": "Treecko", "hp_current": 22, "hp_max": 22}]
            },
            "milestones": {
                "GAME_RUNNING": {"completed": True},
                "LITTLEROOT_TOWN": {"completed": True}
            },
            "map": {},
            "visual": {},
            "step_number": 42,
            "status": "running",
            "action_queue_length": 0
        }
        
        # Test planning step specifically (without full agent.step which needs VLM)
        print("🧪 Testing enhanced planning integration...")
        
        # Access the planning function directly to test integration
        from agent.planning import planning_step
        
        plan = planning_step(
            memory_context="Test memory context",
            current_plan=None,
            slow_thinking_needed=False,
            state_data=mock_game_state,
            vlm=None
        )
        
        print(f"✅ Enhanced planning generated plan: {plan}")
        assert "STRATEGIC GOAL" in plan, "Plan should contain strategic goal"
        assert "Route 101" in plan, "Plan should mention Route 101 as next objective"
        
        # Test that the agent's context gets updated properly
        if hasattr(agent, 'context'):
            print("✅ Agent has context attribute for four-module architecture")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_compatibility():
    """Test that all imports work correctly"""
    print("🧪 Testing import compatibility...")
    
    try:
        # Test individual imports
        from agent.objective_manager import ObjectiveManager, Objective
        print("✅ ObjectiveManager imports successfully")
        
        from agent.planning import planning_step, get_tactical_context  
        print("✅ Enhanced planning functions import successfully")
        
        from agent import Agent, planning_step as agent_planning_step
        print("✅ Agent module exports planning_step correctly")
        
        # Test that ObjectiveManager can be imported in planning module
        import agent.planning
        assert hasattr(agent.planning, 'ObjectiveManager'), "ObjectiveManager should be available in planning module"
        print("✅ ObjectiveManager available in planning module")
        
        return True
        
    except Exception as e:
        print(f"❌ Import compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_integration_tests():
    """Run all integration tests"""
    print("🔗 Starting Integration Tests for Enhanced Planning System")
    print("=" * 65)
    
    success = True
    
    # Test 1: Import compatibility
    if not test_import_compatibility():
        success = False
    
    print()
    
    # Test 2: Agent integration  
    if not test_agent_integration():
        success = False
        
    print("\n" + "=" * 65)
    if success:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("\n📋 Integration Summary:")
        print("   ✅ All imports work correctly")
        print("   ✅ Agent initialization with enhanced planning")  
        print("   ✅ Enhanced planning generates strategic goals")
        print("   ✅ Four-module architecture compatibility maintained")
        print("\n🚀 The enhanced planning system is fully integrated and ready!")
    else:
        print("❌ SOME INTEGRATION TESTS FAILED")
        print("   Please check the errors above and fix any issues")
    
    return success

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)