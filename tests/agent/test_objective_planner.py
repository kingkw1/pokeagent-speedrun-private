#!/usr/bin/env python3
"""
Test script for the enhanced objective-driven planning system.

This script validates that the planning_step function correctly uses the ObjectiveManager
to generate milestone-driven strategic plans based on game progress.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.planning import planning_step
from agent.objective_manager import ObjectiveManager

def test_objective_manager_basic():
    """Test basic ObjectiveManager functionality"""
    print("🧪 Testing ObjectiveManager basic functionality...")
    
    obj_manager = ObjectiveManager()
    
    # Test initialization
    assert len(obj_manager.objectives) > 0, "ObjectiveManager should initialize with storyline objectives"
    print(f"✅ Initialized with {len(obj_manager.objectives)} storyline objectives")
    
    # Test getting active objectives (all should be active initially)
    active_objectives = obj_manager.get_active_objectives()
    assert len(active_objectives) == len(obj_manager.objectives), "All objectives should initially be active"
    print(f"✅ {len(active_objectives)} active objectives found")
    
    # Test objectives summary
    summary = obj_manager.get_objectives_summary()
    assert summary['completed_count'] == 0, "No objectives should be completed initially"
    assert summary['active_count'] > 0, "Should have active objectives"
    print(f"✅ Objectives summary: {summary['active_count']} active, {summary['completed_count']} completed")
    
    return obj_manager

def test_milestone_completion():
    """Test milestone-based objective completion"""
    print("\n🧪 Testing milestone-based objective completion...")
    
    obj_manager = ObjectiveManager()
    
    # Create mock state data with some completed milestones
    mock_state_data = {
        "milestones": {
            "GAME_RUNNING": {
                "completed": True,
                "timestamp": 1697286482.900101,
                "first_completed": 1697286482.900101
            },
            "LITTLEROOT_TOWN": {
                "completed": True, 
                "timestamp": 1697286483.123456,
                "first_completed": 1697286483.123456
            },
            "ROUTE_101": {
                "completed": False  # This milestone is NOT completed yet
            }
        }
    }
    
    # Check milestone completion
    completed_ids = obj_manager.check_storyline_milestones(mock_state_data)
    print(f"✅ Auto-completed {len(completed_ids)} objectives based on milestones")
    
    # Verify the right objectives were completed
    completed_objectives = obj_manager.get_completed_objectives()
    completed_milestone_ids = [obj.milestone_id for obj in completed_objectives]
    
    assert "GAME_RUNNING" in completed_milestone_ids, "GAME_RUNNING objective should be completed"
    assert "LITTLEROOT_TOWN" in completed_milestone_ids, "LITTLEROOT_TOWN objective should be completed" 
    print(f"✅ Verified completion of objectives: {completed_milestone_ids}")
    
    # Get current strategic objective (should be Route 101)
    current_obj = obj_manager.get_current_strategic_objective(mock_state_data)
    assert current_obj is not None, "Should have a current strategic objective"
    assert current_obj.milestone_id == "ROUTE_101", f"Current objective should be ROUTE_101, got {current_obj.milestone_id}"
    print(f"✅ Current strategic objective: {current_obj.description}")
    
    return obj_manager, mock_state_data

def test_strategic_planning():
    """Test strategic plan generation"""
    print("\n🧪 Testing strategic plan generation...")
    
    obj_manager = ObjectiveManager()
    
    # Test with no milestones (beginning of game)
    empty_state_data = {"milestones": {}}
    plan = obj_manager.get_strategic_plan_description(empty_state_data)
    assert plan is not None, "Should generate a strategic plan"
    assert "STRATEGIC GOAL" in plan, "Plan should contain 'STRATEGIC GOAL'"
    print(f"✅ Strategic plan for new game: {plan}")
    
    # Test with some progress
    progress_state_data = {
        "milestones": {
            "GAME_RUNNING": {"completed": True},
            "LITTLEROOT_TOWN": {"completed": True}
        }
    }
    plan_with_progress = obj_manager.get_strategic_plan_description(progress_state_data)
    assert plan_with_progress is not None, "Should generate a strategic plan with progress"
    assert "Route 101" in plan_with_progress, "Plan should mention Route 101 as next objective"
    print(f"✅ Strategic plan with progress: {plan_with_progress}")
    
    return obj_manager

def test_planning_step_integration():
    """Test integration with the main planning_step function"""
    print("\n🧪 Testing planning_step integration...")
    
    # Create mock state data matching the expected format
    mock_state_data = {
        "player": {
            "location": "Littleroot Town",
            "money": 3000,
            "position": {"x": 10, "y": 15}
        },
        "game": {
            "state": "overworld",
            "in_battle": False,
            "party_count": 1,
            "party": [
                {"species": "Treecko", "hp_current": 22, "hp_max": 22}
            ]
        },
        "milestones": {
            "GAME_RUNNING": {"completed": True},
            "LITTLEROOT_TOWN": {"completed": True}
            # ROUTE_101 is not completed, so this should be the next objective
        }
    }
    
    # Call planning_step function (with dummy parameters for unused args)
    plan = planning_step(
        memory_context="", 
        current_plan=None,
        slow_thinking_needed=False, 
        state_data=mock_state_data,
        vlm=None  # VLM not used in enhanced planning
    )
    
    assert plan is not None, "planning_step should return a plan"
    assert isinstance(plan, str), "Plan should be a string"
    assert len(plan) > 10, "Plan should be substantial"
    
    # Should contain strategic objective for Route 101
    assert "Route 101" in plan or "STRATEGIC GOAL" in plan, f"Plan should contain strategic objective, got: {plan}"
    print(f"✅ planning_step integration successful")
    print(f"   Generated plan: {plan}")
    
    # Test fallback behavior with no milestones
    empty_state_data = {
        "player": {"location": "Unknown"},
        "game": {"state": "overworld", "in_battle": False},
        "milestones": {}  # No milestone data
    }
    
    fallback_plan = planning_step("", None, False, empty_state_data, None)
    assert fallback_plan is not None, "Should generate fallback plan"
    print(f"✅ Fallback plan generation: {fallback_plan}")
    
    return True

def test_tactical_context():
    """Test tactical context generation"""
    print("\n🧪 Testing tactical context generation...")
    
    from agent.planning import get_tactical_context
    
    # Test low health scenario
    low_health_state = {
        "game": {
            "in_battle": True,
            "battle_info": {
                "player_pokemon": {
                    "hp_current": 5,
                    "hp_max": 25
                }
            }
        },
        "player": {"money": 100}
    }
    
    tactical = get_tactical_context(low_health_state)
    assert "critical" in tactical.lower() or "healing" in tactical.lower(), f"Should suggest healing for low health, got: {tactical}"
    print(f"✅ Low health tactical context: {tactical}")
    
    # Test low money scenario  
    low_money_state = {
        "game": {"in_battle": False},
        "player": {"money": 200}
    }
    
    tactical_money = get_tactical_context(low_money_state)
    assert "funds" in tactical_money.lower() or "money" in tactical_money.lower(), f"Should mention money issues, got: {tactical_money}"
    print(f"✅ Low money tactical context: {tactical_money}")
    
    return True

def run_all_tests():
    """Run all tests in sequence"""
    print("🚀 Starting Enhanced Planning System Tests")
    print("=" * 60)
    
    try:
        # Test 1: Basic ObjectiveManager functionality
        obj_manager = test_objective_manager_basic()
        
        # Test 2: Milestone completion logic
        obj_manager_2, mock_state = test_milestone_completion()
        
        # Test 3: Strategic plan generation
        obj_manager_3 = test_strategic_planning()
        
        # Test 4: planning_step integration
        integration_success = test_planning_step_integration()
        
        # Test 5: Tactical context
        tactical_success = test_tactical_context()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Enhanced planning system is working correctly.")
        print("\n📊 Test Summary:")
        print(f"   ✅ ObjectiveManager initialization and basic functionality")
        print(f"   ✅ Milestone-based objective completion")
        print(f"   ✅ Strategic plan generation")
        print(f"   ✅ planning_step integration with four-module architecture")
        print(f"   ✅ Tactical context generation")
        print("\n🚀 The enhanced planning system is ready for use!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)