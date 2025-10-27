#!/usr/bin/env python3
"""
Test script for Day 9 Navigation Integration
Validates that the goal-conditioned action system is working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.action import action_step
from agent.planning import planning_step
from agent.objective_manager import ObjectiveManager
from utils.state_formatter import format_movement_preview_for_llm

def test_goal_conditioned_navigation():
    """Test that strategic goals are properly integrated into action decisions"""
    
    print("🧪 Testing Day 9 Goal-Conditioned Navigation Integration")
    print("=" * 60)
    
    # Mock state data representing an overworld situation
    mock_state_data = {
        'game': {
            'in_battle': False,
            'party_count': 1,
            'game_state': 'overworld'
        },
        'player': {
            'location': 'LITTLEROOT_TOWN',
            'position': {'x': 10, 'y': 10},
            'name': 'RED'
        },
        'map': {
            'tiles': [
                [[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]],
                [[1, 0, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 0, 0, 0]],
                [[1, 0, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 0, 0, 0]], 
                [[1, 0, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 0, 0, 0]],
                [[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]]
            ],
            'traversability': [
                ['#', '#', '#', '#', '#'],
                ['#', '.', '.', '.', '#'],
                ['#', '.', '.', '.', '#'],
                ['#', '.', '.', '.', '#'], 
                ['#', '#', '#', '#', '#']
            ]
        }
    }
    
    # Mock observation with overworld context
    mock_observation = {
        'visual_data': {
            'screen_context': 'overworld',
            'on_screen_text': {},
            'visible_entities': [],
            'visual_elements': {}
        }
    }
    
    # Test 1: Strategic goal generation
    print("\n📋 Test 1: Strategic Goal Generation")
    obj_manager = ObjectiveManager()
    strategic_goal = obj_manager.get_strategic_plan_description(mock_state_data)
    print(f"Strategic Goal: {strategic_goal}")
    
    # Test 2: Movement preview generation  
    print("\n🗺️  Test 2: Movement Preview Generation")
    try:
        movement_preview = format_movement_preview_for_llm(mock_state_data)
        print("Movement Preview:")
        print(movement_preview)
    except Exception as e:
        print(f"Movement preview error: {e}")
    
    # Test 3: Goal-conditioned action prompt integration
    print("\n🎯 Test 3: Goal-Conditioned Action Integration")
    print("This test verifies our enhanced action_step function includes strategic goals")
    
    # Mock VLM that returns a directional action
    class MockVLM:
        def get_text_query(self, prompt, category):
            print(f"\n📝 VLM Received Prompt for {category}:")
            print("-" * 40)
            
            # Show relevant parts of the prompt
            lines = prompt.split('\n')
            goal_section_started = False
            movement_section_started = False
            
            for line in lines:
                if "=== YOUR STRATEGIC GOAL ===" in line:
                    goal_section_started = True
                    print(line)
                elif goal_section_started and line.strip():
                    print(line)
                    if "===" in line and "GOAL" not in line:
                        goal_section_started = False
                        
                if "MOVEMENT PREVIEW:" in line:
                    movement_section_started = True
                    print(line)
                elif movement_section_started and line.strip():
                    print(line)
                    if "===" in line:
                        movement_section_started = False
                        
            print("-" * 40)
            
            # Return a mock directional response
            if "Route 101" in prompt:
                return "UP"  # Strategic response to go toward Route 101
            else:
                return "A"   # Default action
    
    mock_vlm = MockVLM()
    
    # Test with strategic goal
    print(f"\nTesting action_step with goal: '{strategic_goal}'")
    
    try:
        actions = action_step(
            memory_context="Test memory context",
            current_plan=strategic_goal,  # This is our strategic goal
            latest_observation=mock_observation,
            frame=None,
            state_data=mock_state_data,
            recent_actions=['A', 'A'],
            vlm=mock_vlm
        )
        
        print(f"\n✅ Action Decision Result: {actions}")
        
        # Validate integration success
        if strategic_goal and "Route 101" in strategic_goal and "UP" in actions:
            print("🎉 SUCCESS: Strategic goal influenced action decision!")
        elif not strategic_goal:
            print("⚠️  NOTICE: No strategic goal generated (expected early in game)")
        else:
            print(f"ℹ️  INFO: Action '{actions}' made with goal '{strategic_goal}'")
            
    except Exception as e:
        print(f"❌ ERROR in action_step: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🏁 Day 9 Navigation Integration Test Complete")
    
if __name__ == "__main__":
    test_goal_conditioned_navigation()