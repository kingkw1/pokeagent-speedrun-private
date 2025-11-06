"""
Test: Opener Bot Clock Setting Sequence (Unit Tests)

This test verifies the opener bot can handle the clock-setting sequence from
a mid-sequence save state, demonstrating it can "jump into" the middle of 
the state machine rather than needing to run from the beginning.

Test Scenario: house_set_clock_save state
- Player in house (1F) with Mom's dialogue visible
- Milestones: PLAYER_NAME_SET=True, LITTLEROOT_TOWN=True
- Goal: Clear dialogue → Navigate to stairs → Go to 2F → Navigate to clock
"""

import pytest
from agent.opener_bot import OpenerBot, NavigationGoal


class TestOpenerClockSequence:
    """Unit tests for opener bot clock sequence handling"""
    
    def test_should_handle_in_house(self):
        """Test that opener bot recognizes it should handle when in player's house"""
        state_data = {
            'player': {
                'location': 'LITTLEROOT TOWN BRENDANS HOUSE 1F',
                'position': {'x': 8, 'y': 8}
            },
            'milestones': {
                'PLAYER_NAME_SET': True,
                'LITTLEROOT_TOWN': True,
            },
            'game': {'game_state': 'dialog', 'in_battle': False}
        }
        
        visual_data = {
            'visual_elements': {'text_box_visible': True},
            'on_screen_text': {'dialogue': "MOM: See, TRUCK?"}
        }
        
        bot = OpenerBot()
        assert bot.should_handle(state_data, visual_data), \
            "Bot should take control when in player's house with dialogue"
    
    def test_state_detection_with_dialogue(self):
        """Test that bot detects S4_MOM_DIALOG_1F when dialogue is visible"""
        state_data = {
            'player': {
                'location': 'LITTLEROOT TOWN BRENDANS HOUSE 1F',
                'position': {'x': 8, 'y': 8}
            },
            'milestones': {'PLAYER_NAME_SET': True},
            'game': {'game_state': 'dialog'}
        }
        
        visual_data = {
            'visual_elements': {'text_box_visible': True}
        }
        
        bot = OpenerBot()
        state = bot._detect_current_state(state_data, visual_data)
        
        assert state == 'S4_MOM_DIALOG_1F', \
            f"Should detect S4_MOM_DIALOG_1F, got: {state}"
    
    def test_dialogue_clearing_action(self):
        """Test that bot returns ['A'] to clear Mom's dialogue"""
        state_data = {
            'player': {
                'location': 'LITTLEROOT TOWN BRENDANS HOUSE 1F',
                'position': {'x': 8, 'y': 8}
            },
            'milestones': {'PLAYER_NAME_SET': True},
            'game': {'game_state': 'dialog'}
        }
        
        visual_data = {
            'visual_elements': {'text_box_visible': True}
        }
        
        bot = OpenerBot()
        action = bot.get_action(state_data, visual_data)
        
        assert action == ['A'], \
            f"Should return ['A'] to clear dialogue, got: {action}"
    
    def test_state_transition_after_dialogue(self):
        """Test that bot transitions to S5_NAV_TO_STAIRS after dialogue is cleared"""
        state_data = {
            'player': {
                'location': 'LITTLEROOT TOWN BRENDANS HOUSE 1F',
                'position': {'x': 8, 'y': 7}
            },
            'milestones': {'PLAYER_NAME_SET': True},
            'game': {'game_state': 'overworld'}  # No dialogue
        }
        
        visual_data = {
            'visual_elements': {'text_box_visible': False}
        }
        
        bot = OpenerBot()
        state = bot._detect_current_state(state_data, visual_data)
        
        assert state == 'S5_NAV_TO_STAIRS', \
            f"Should detect S5_NAV_TO_STAIRS after dialogue cleared, got: {state}"
    
    def test_navigation_goal_to_stairs(self):
        """Test that bot returns NavigationGoal to stairs after dialogue"""
        state_data = {
            'player': {
                'location': 'LITTLEROOT TOWN BRENDANS HOUSE 1F',
                'position': {'x': 8, 'y': 7}
            },
            'milestones': {'PLAYER_NAME_SET': True},
            'game': {'game_state': 'overworld'}
        }
        
        visual_data = {
            'visual_elements': {'text_box_visible': False}
        }
        
        bot = OpenerBot()
        action = bot.get_action(state_data, visual_data)
        
        assert isinstance(action, NavigationGoal), \
            f"Should return NavigationGoal, got: {type(action)}"
        assert action.description == "Go to Stairs", \
            f"Should navigate to stairs, got: {action.description}"
        assert action.x == 7 and action.y == 1, \
            f"Stairs should be at (7, 1), got: ({action.x}, {action.y})"
    
    def test_state_detection_on_2f(self):
        """Test that bot detects S6_NAV_TO_CLOCK when on 2F"""
        state_data = {
            'player': {
                'location': 'LITTLEROOT TOWN BRENDANS HOUSE 2F',
                'position': {'x': 7, 'y': 2}
            },
            'milestones': {'PLAYER_NAME_SET': True, 'PLAYER_BEDROOM': True},
            'game': {'game_state': 'overworld'}
        }
        
        visual_data = {
            'visual_elements': {'text_box_visible': False}
        }
        
        bot = OpenerBot()
        state = bot._detect_current_state(state_data, visual_data)
        
        assert state == 'S6_NAV_TO_CLOCK', \
            f"Should detect S6_NAV_TO_CLOCK on 2F, got: {state}"
    
    def test_navigation_goal_to_clock(self):
        """Test that bot returns NavigationGoal to clock on 2F"""
        state_data = {
            'player': {
                'location': 'LITTLEROOT TOWN BRENDANS HOUSE 2F',
                'position': {'x': 7, 'y': 2}
            },
            'milestones': {'PLAYER_NAME_SET': True},
            'game': {'game_state': 'overworld'}
        }
        
        visual_data = {
            'visual_elements': {'text_box_visible': False}
        }
        
        bot = OpenerBot()
        action = bot.get_action(state_data, visual_data)
        
        assert isinstance(action, NavigationGoal), \
            f"Should return NavigationGoal, got: {type(action)}"
        assert action.description == "Go to Clock", \
            f"Should navigate to clock, got: {action.description}"
        # Clock position from Gemini's design (may need adjustment)
        assert action.x == 1 and action.y == 1, \
            f"Clock should be at (1, 1), got: ({action.x}, {action.y})"
    
    def test_full_sequence_simulation(self):
        """Test the complete state progression: dialogue → stairs → 2F → clock"""
        bot = OpenerBot()
        
        # Step 1: In house with dialogue
        state1 = {
            'player': {'location': 'LITTLEROOT TOWN BRENDANS HOUSE 1F', 'position': {'x': 8, 'y': 8}},
            'milestones': {'PLAYER_NAME_SET': True},
            'game': {'game_state': 'dialog'}
        }
        visual1 = {'visual_elements': {'text_box_visible': True}}
        
        detected_state1 = bot._detect_current_state(state1, visual1)
        action1 = bot.get_action(state1, visual1)
        
        assert detected_state1 == 'S4_MOM_DIALOG_1F', "Step 1: Should be in dialogue state"
        assert action1 == ['A'], "Step 1: Should clear dialogue"
        
        # Step 2: Dialogue cleared, ready to navigate
        state2 = {
            'player': {'location': 'LITTLEROOT TOWN BRENDANS HOUSE 1F', 'position': {'x': 8, 'y': 7}},
            'milestones': {'PLAYER_NAME_SET': True},
            'game': {'game_state': 'overworld'}
        }
        visual2 = {'visual_elements': {'text_box_visible': False}}
        
        detected_state2 = bot._detect_current_state(state2, visual2)
        action2 = bot.get_action(state2, visual2)
        
        assert detected_state2 == 'S5_NAV_TO_STAIRS', "Step 2: Should navigate to stairs"
        assert isinstance(action2, NavigationGoal), "Step 2: Should return navigation goal"
        assert action2.description == "Go to Stairs", "Step 2: Should target stairs"
        
        # Step 3: On 2F, ready to find clock
        state3 = {
            'player': {'location': 'LITTLEROOT TOWN BRENDANS HOUSE 2F', 'position': {'x': 7, 'y': 2}},
            'milestones': {'PLAYER_NAME_SET': True},
            'game': {'game_state': 'overworld'}
        }
        visual3 = {'visual_elements': {'text_box_visible': False}}
        
        detected_state3 = bot._detect_current_state(state3, visual3)
        action3 = bot.get_action(state3, visual3)
        
        assert detected_state3 == 'S6_NAV_TO_CLOCK', "Step 3: Should navigate to clock"
        assert isinstance(action3, NavigationGoal), "Step 3: Should return navigation goal"
        assert action3.description == "Go to Clock", "Step 3: Should target clock"
        
        print("\n✓✓✓ Full sequence simulation passed!")
        print(f"  1. {detected_state1} → {action1}")
        print(f"  2. {detected_state2} → {action2.description}")
        print(f"  3. {detected_state3} → {action3.description}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
