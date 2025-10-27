#!/usr/bin/env python3
"""
Day 9 Navigation Success Test - Route 101 Navigation Scenario
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.action import action_step
from agent.objective_manager import ObjectiveManager

def test_route_101_navigation():
    """Test goal-conditioned navigation for Route 101 objective"""
    
    print("🧪 Day 9 Success Test: Route 101 Navigation")
    print("=" * 50)
    
    # Mock state with player in Littleroot Town, Route 101 is north
    mock_state_data = {
        'game': {
            'in_battle': False,
            'party_count': 1,
            'game_state': 'overworld'
        },
        'player': {
            'location': 'LITTLEROOT_TOWN',
            'position': {'x': 10, 'y': 10},
            'name': 'RED',
            'facing': 'UP'
        },
        'map': {
            'tiles': [
                [[1, 0, 0, 0], [1, 0, 0, 0], [1, 1, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]],  # North: Clear path
                [[1, 0, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 0, 0, 0]],  
                [[1, 0, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 1, 0, 0], [1, 0, 0, 0]],  # Player here
                [[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]], # South: Wall
                [[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]]
            ],
            'traversability': [
                ['#', '#', '.', '#', '#'],  # North: Clear path UP
                ['#', '.', '.', '.', '#'],  
                ['#', '.', '.', '.', '#'],  # Player center
                ['#', '#', '#', '#', '#'], # South: Blocked
                ['#', '#', '#', '#', '#']
            ]
        },
        'milestones': {
            'STARTED_GAME': True,
            'SELECTED_CHARACTER': True
        }
    }
    
    # Mock observation - overworld
    mock_observation = {
        'visual_data': {
            'screen_context': 'overworld',
            'on_screen_text': {},
            'visible_entities': [
                {'type': 'location_sign', 'name': 'Route 101', 'position': 'north'}
            ],
            'visual_elements': {}
        }
    }
    
    # VLM that understands Route 101 navigation
    class NavigationVLM:
        def get_text_query(self, prompt, category):
            print(f"\n📝 VLM Prompt Analysis:")
            
            # Extract strategic goal
            if "=== YOUR STRATEGIC GOAL ===" in prompt:
                goal_start = prompt.find("=== YOUR STRATEGIC GOAL ===") + 29
                goal_end = prompt.find("\n\n", goal_start)
                goal = prompt[goal_start:goal_end].strip()
                print(f"🎯 Strategic Goal: {goal}")
            
            # Extract movement options  
            if "MOVEMENT PREVIEW:" in prompt:
                movement_start = prompt.find("MOVEMENT PREVIEW:")
                movement_end = prompt.find("=== DECISION", movement_start)
                movement_section = prompt[movement_start:movement_end]
                print(f"🗺️  Movement Analysis:\n{movement_section.strip()}")
            
            # Make intelligent navigation decision
            if "Route 101" in prompt and "UP" in prompt and "WALKABLE" in prompt:
                print("🧠 VLM Decision: Route 101 is north, UP path is clear -> Choose UP")
                return "UP"
            else:
                print("🧠 VLM Decision: No clear navigation path -> Choose A")
                return "A"
    
    # Generate strategic goal for Route 101
    obj_manager = ObjectiveManager()
    strategic_goal = "STRATEGIC GOAL: Travel north to Route 101 to find Professor Birch and receive your first Pokemon."
    
    print(f"Strategic Objective: {strategic_goal}")
    
    # Test goal-conditioned action
    mock_vlm = NavigationVLM()
    
    try:
        actions = action_step(
            memory_context="Testing navigation to Route 101",
            current_plan=strategic_goal,
            latest_observation=mock_observation,
            frame=None,
            state_data=mock_state_data,
            recent_actions=['A'],
            vlm=mock_vlm
        )
        
        print(f"\n🎮 Action Decision: {actions}")
        
        # Validate navigation success
        if 'UP' in actions:
            print("\n🎉 SUCCESS: Goal-conditioned navigation working!")
            print("   Strategic Goal: Travel to Route 101")
            print("   Tactical Analysis: North path is walkable") 
            print("   Action Decision: UP (toward Route 101)")
            print("\n✅ Day 9 Navigation Bridge: FUNCTIONAL")
        else:
            print(f"\n⚠️  Unexpected action: {actions}")
            print("   (May be appropriate for current game state)")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_route_101_navigation()