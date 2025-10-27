#!/usr/bin/env python3
"""
Agent Module Basic Validation Tests

Purpose:
    Validate that agent modules can be called without errors and return expected types.
    Tests basic functionality, not prompt structure (which has changed to be simpler).

Test Cases:
    - test_action_returns_list: Action module returns list of actions
    - test_memory_extraction_works: Memory module extracts key state info
    - test_memory_context_generation: Memory module generates context string
    - test_perception_returns_dict: Perception returns observation dict
    - test_planning_returns_string: Planning returns plan string
    - test_modules_handle_battle_state: All modules work with battle states

Dependencies:
    - State fixtures: Uses mock state data (no emulator/server)
    - External services: None (mocked VLM)

Runtime:
    <2 seconds (all tests, no server startup)

Note:
    This replaces test_agent_prompts.py which spawned servers (2-3 min runtime).
    Focuses on module interfaces and basic functionality, not prompt details.
"""

import pytest
from unittest.mock import Mock
from typing import Dict, Any

# Import agent modules
from agent.action import action_step
from agent.memory import memory_step, extract_key_state_info
from agent.perception import perception_step
from agent.planning import planning_step
from utils.vlm import VLM


class TestAgentModules:
    """Test suite for validating agent module basic functionality"""
    
    @pytest.fixture
    def mock_vlm(self):
        """Create a mock VLM that returns reasonable responses"""
        mock_vlm = Mock(spec=VLM)
        
        def mock_get_query(frame, prompt, context=""):
            """Mock VLM image query - returns JSON for perception"""
            if "perception" in context.lower() or "screen_context" in prompt.lower():
                # Return a valid JSON response for perception
                return '''{
                    "screen_context": "overworld",
                    "on_screen_text": {"dialogue": null, "speaker": null, "menu_title": null, "button_prompts": []},
                    "visible_entities": [],
                    "navigation_info": {"exits_visible": [], "interactable_objects": [], "movement_barriers": [], "open_paths": []},
                    "spatial_layout": {"player_position": "center", "room_type": "outdoor route", "notable_features": []},
                    "menu_state": "closed",
                    "visual_elements": {"health_bars_visible": false, "pokemon_sprites_visible": false, "overworld_map_visible": true, "text_box_visible": false}
                }'''
            return "UP"  # Default action response
        
        def mock_get_text_query(prompt, context=""):
            """Mock VLM text-only query"""
            return "Continue exploring and look for items."
        
        mock_vlm.get_query = mock_get_query
        mock_vlm.get_text_query = mock_get_text_query
        
        return mock_vlm
    
    @pytest.fixture
    def sample_state_overworld(self):
        """Sample game state - overworld exploration"""
        return {
            'player': {
                'name': 'Red',
                'position': {'x': 10, 'y': 15, 'map': 0},
                'location': 'LITTLEROOT_TOWN',
                'facing': 'North',
                'money': 3000,
                'party': [
                    {
                        'species_name': 'Treecko',
                        'level': 5,
                        'current_hp': 20,
                        'max_hp': 20,
                        'status': 'Normal',
                        'moves': ['Pound', 'Leer']
                    }
                ]
            },
            'game': {
                'game_state': 'overworld',
                'is_in_battle': False,
                'dialog_text': '',
                'dialogue_detected': {'has_dialogue': False, 'confidence': 0.0},
                'money': 3000,
                'party_count': 1,
                'pokedex_seen': 1,
                'pokedex_caught': 1,
                'badges': 0
            },
            'map': {
                'current_map': 'LITTLEROOT_TOWN',
                'tiles': [
                    [(1, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0)],
                    [(1, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0)],
                    [(1, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0)]
                ]
            }
        }
    
    @pytest.fixture
    def sample_state_battle(self):
        """Sample game state - in battle"""
        return {
            'player': {
                'name': 'Red',
                'position': {'x': 10, 'y': 15, 'map': 0},
                'location': 'ROUTE_101',
                'money': 3000,
                'party': [
                    {
                        'species_name': 'Treecko',
                        'level': 5,
                        'current_hp': 15,
                        'max_hp': 20,
                        'status': 'Normal',
                        'moves': ['Pound', 'Leer', 'Absorb']
                    }
                ]
            },
            'game': {
                'game_state': 'battle',
                'is_in_battle': True,
                'battle_info': {
                    'player_pokemon': {
                        'species': 'Treecko',
                        'level': 5,
                        'current_hp': 15,
                        'max_hp': 20,
                        'moves': ['Pound', 'Leer', 'Absorb']
                    },
                    'opponent_pokemon': {
                        'species': 'Poochyena',
                        'level': 3,
                        'current_hp': 12,
                        'max_hp': 15
                    },
                    'battle_type': 'wild',
                    'is_capturable': True,
                    'can_escape': True
                }
            },
            'map': {
                'current_map': 'ROUTE_101',
                'tiles': []  # Hidden during battle
            }
        }
    
    def test_action_returns_list(self, mock_vlm, sample_state_overworld):
        """Test that action module returns a list of actions"""
        memory_context = "Player is exploring Littleroot Town."
        current_plan = "Exit house and explore the town."
        latest_observation = {"screen_context": "overworld"}
        frame = None
        recent_actions = ["UP", "A", "RIGHT"]
        
        actions = action_step(
            memory_context, 
            current_plan, 
            latest_observation, 
            frame, 
            sample_state_overworld, 
            recent_actions, 
            mock_vlm
        )
        
        assert isinstance(actions, list), "Action module should return a list"
        assert len(actions) > 0, "Action module should return at least one action"
        assert all(isinstance(action, str) for action in actions), "All actions should be strings"
    
    def test_memory_extraction_works(self, sample_state_overworld):
        """Test that memory module can extract key state info"""
        key_info = extract_key_state_info(sample_state_overworld)
        
        assert isinstance(key_info, dict), "Key info should be a dict"
        
        # Check for important fields
        required_fields = ['state_summary', 'player_name', 'money', 'current_map', 'in_battle']
        for field in required_fields:
            assert field in key_info, f"Key info missing field: {field}"
    
    def test_memory_context_generation(self, mock_vlm, sample_state_overworld):
        """Test that memory module generates a memory context string"""
        memory_context = "Starting exploration."
        current_plan = "Explore Littleroot Town."
        recent_actions = ["UP", "A", "RIGHT"]
        observation_buffer = [
            {
                "frame_id": 1,
                "observation": {"screen_context": "overworld"},
                "state": sample_state_overworld
            }
        ]
        
        updated_memory = memory_step(
            memory_context,
            current_plan,
            recent_actions,
            observation_buffer,
            mock_vlm
        )
        
        assert isinstance(updated_memory, str), "Memory context should be a string"
        assert len(updated_memory) > 0, "Memory context should not be empty"
    
    def test_perception_returns_dict(self, mock_vlm, sample_state_overworld):
        """Test that perception returns an observation dictionary"""
        frame = None
        
        result = perception_step(frame, sample_state_overworld, mock_vlm)
        
        # perception_step returns just the observation dict
        assert isinstance(result, dict), "Perception should return a dict"
    
    def test_planning_returns_string(self, mock_vlm, sample_state_overworld):
        """Test that planning returns a plan string"""
        memory_context = "Player is exploring Littleroot Town."
        current_plan = None  # Start with no plan
        slow_thinking_needed = True
        
        plan = planning_step(
            memory_context,
            current_plan,
            slow_thinking_needed,
            sample_state_overworld,
            mock_vlm
        )
        
        assert isinstance(plan, str), "Plan should be a string"
        assert len(plan) > 0, "Plan should not be empty"
    
    def test_modules_handle_battle_state(self, mock_vlm, sample_state_battle):
        """Test that all modules can handle battle states without errors"""
        memory_context = "In battle on Route 101."
        current_plan = "Defeat wild Pokemon."
        frame = None
        recent_actions = ["A", "A"]
        
        # All modules should work without raising exceptions
        observation = perception_step(frame, sample_state_battle, mock_vlm)
        assert isinstance(observation, dict)
        
        observation_buffer = [{"frame_id": 1, "observation": observation, "state": sample_state_battle}]
        updated_memory = memory_step(memory_context, current_plan, recent_actions, observation_buffer, mock_vlm)
        assert isinstance(updated_memory, str)
        
        plan = planning_step(updated_memory, current_plan, True, sample_state_battle, mock_vlm)
        assert isinstance(plan, str)
        
        actions = action_step(updated_memory, plan, observation, frame, sample_state_battle, recent_actions, mock_vlm)
        assert isinstance(actions, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

    """Test suite for validating agent module prompt generation"""
    
    @pytest.fixture
    def mock_vlm(self):
        """Create a mock VLM that captures prompts and returns reasonable responses"""
        mock_vlm = Mock(spec=VLM)
        
        # Storage for captured prompts
        mock_vlm.captured_prompts = []
        
        def mock_get_query(frame, prompt, context=""):
            """Mock VLM image query"""
            mock_vlm.captured_prompts.append({
                'context': context,
                'prompt': prompt,
                'frame': frame is not None,
                'type': 'image'
            })
            
            # Return reasonable responses based on context
            if "PERCEPTION" in context:
                return "I can see the player character on a grassy route with trees and paths."
            elif "ACTION" in context:
                return "UP"
            elif "PLANNING" in context:
                return "Continue exploring the route and look for items or trainers."
            elif "MEMORY" in context:
                return "Updated memory context with current observations."
            else:
                return "Default response"
        
        def mock_get_text_query(prompt, context=""):
            """Mock VLM text-only query"""
            mock_vlm.captured_prompts.append({
                'context': context,
                'prompt': prompt,
                'frame': False,
                'type': 'text'
            })
            
            # Return reasonable responses
            if "ACTION" in context:
                return "UP"
            elif "PLANNING" in context:
                return "Continue exploring the route and look for items or trainers."
            elif "MEMORY" in context:
                return "Updated memory context with current observations."
            else:
                return "Default response"
        
        mock_vlm.get_query = mock_get_query
        mock_vlm.get_text_query = mock_get_text_query
        
        return mock_vlm
    
    @pytest.fixture
    def sample_state_overworld(self):
        """Sample game state - overworld exploration"""
        return {
            'player': {
                'name': 'Red',
                'position': {'x': 10, 'y': 15, 'map': 0},
                'location': 'LITTLEROOT_TOWN',
                'facing': 'North',
                'money': 3000,
                'party': [
                    {
                        'species_name': 'Treecko',
                        'level': 5,
                        'current_hp': 20,
                        'max_hp': 20,
                        'status': 'Normal',
                        'moves': ['Pound', 'Leer']
                    }
                ]
            },
            'game': {
                'game_state': 'overworld',
                'is_in_battle': False,
                'dialog_text': '',
                'dialogue_detected': {'has_dialogue': False, 'confidence': 0.0},
                'money': 3000,
                'party_count': 1,
                'pokedex_seen': 1,
                'pokedex_caught': 1,
                'badges': 0
            },
            'map': {
                'current_map': 'LITTLEROOT_TOWN',
                'tiles': [
                    [(1, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0)],
                    [(1, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0)],
                    [(1, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0)]
                ]
            }
        }
    
    @pytest.fixture
    def sample_state_battle(self):
        """Sample game state - in battle"""
        return {
            'player': {
                'name': 'Red',
                'position': {'x': 10, 'y': 15, 'map': 0},
                'location': 'ROUTE_101',
                'money': 3000,
                'party': [
                    {
                        'species_name': 'Treecko',
                        'level': 5,
                        'current_hp': 15,
                        'max_hp': 20,
                        'status': 'Normal',
                        'moves': ['Pound', 'Leer', 'Absorb']
                    }
                ]
            },
            'game': {
                'game_state': 'battle',
                'is_in_battle': True,
                'battle_info': {
                    'player_pokemon': {
                        'species': 'Treecko',
                        'level': 5,
                        'current_hp': 15,
                        'max_hp': 20,
                        'moves': ['Pound', 'Leer', 'Absorb']
                    },
                    'opponent_pokemon': {
                        'species': 'Poochyena',
                        'level': 3,
                        'current_hp': 12,
                        'max_hp': 15
                    },
                    'battle_type': 'wild',
                    'is_capturable': True,
                    'can_escape': True
                }
            },
            'map': {
                'current_map': 'ROUTE_101',
                'tiles': []  # Hidden during battle
            }
        }
    
    def test_action_prompts_structure(self, mock_vlm, sample_state_overworld):
        """Test that action module generates well-structured prompts"""
        # Call action_step with mock data
        memory_context = "Player is exploring Littleroot Town."
        current_plan = "Exit house and explore the town."
        latest_observation = "Standing outside Brendan's house."
        frame = None
        recent_actions = ["UP", "A", "RIGHT"]
        
        actions = action_step(
            memory_context, 
            current_plan, 
            latest_observation, 
            frame, 
            sample_state_overworld, 
            recent_actions, 
            mock_vlm
        )
        
        # Check that prompts were captured
        action_prompts = [p for p in mock_vlm.captured_prompts if "ACTION" in p.get('context', '')]
        assert action_prompts, "No action prompts were captured"
        
        # Analyze prompt structure
        action_prompt = action_prompts[0]['prompt']
        
        # Required sections for action prompts
        required_sections = [
            "COMPREHENSIVE GAME STATE DATA",
            "ENHANCED ACTION CONTEXT",
            "ACTION DECISION TASK"
        ]
        
        for section in required_sections:
            assert section in action_prompt, f"Action prompt missing required section: {section}"
        
        # Check that actions were returned
        assert actions, "Action module returned no actions"
        assert isinstance(actions, list), "Action module should return a list"
    
    def test_memory_extraction_no_unknown(self, sample_state_overworld):
        """Test that memory module doesn't produce 'Unknown' values"""
        # Test key info extraction
        key_info = extract_key_state_info(sample_state_overworld)
        
        # Convert to string and check for "Unknown"
        key_info_str = str(key_info)
        assert "Unknown" not in key_info_str, "Memory key_info contains 'Unknown' values"
        
        # Check for required fields
        required_fields = [
            'state_summary',
            'player_name', 
            'money',
            'current_map',
            'in_battle',
            'party_health'
        ]
        
        for field in required_fields:
            assert field in key_info, f"Memory key_info missing field: {field}"
            assert key_info[field] is not None, f"Memory key_info has None value for: {field}"
    
    def test_memory_prompts_completeness(self, mock_vlm, sample_state_overworld):
        """Test that memory module generates complete prompts"""
        memory_context = "Starting exploration."
        current_plan = "Explore Littleroot Town."
        recent_actions = ["UP", "A", "RIGHT"]
        observation_buffer = [
            {
                "frame_id": 1,
                "observation": "Player standing outside house",
                "state": sample_state_overworld
            }
        ]
        
        # Call memory_step
        updated_memory = memory_step(
            memory_context,
            current_plan,
            recent_actions,
            observation_buffer,
            mock_vlm
        )
        
        # Check for "Unknown" values
        assert "Unknown" not in updated_memory, "Memory context contains 'Unknown' values"
        
        # Check for required sections
        required_sections = [
            "COMPREHENSIVE MEMORY CONTEXT",
            "CURRENT STATE",
            "CURRENT PLAN"
        ]
        
        for section in required_sections:
            assert section in updated_memory, f"Memory context missing section: {section}"
        
        # Memory should be substantive
        assert len(updated_memory.strip()) > 100, "Memory context seems too short"
    
    def test_perception_prompts_analysis_keywords(self, mock_vlm, sample_state_overworld):
        """Test that perception prompts include proper analysis instructions"""
        frame = None
        
        # Call perception_step
        observation, slow_thinking = perception_step(
            frame,
            sample_state_overworld,
            mock_vlm
        )
        
        # Check captured prompts
        perception_prompts = [p for p in mock_vlm.captured_prompts if "PERCEPTION" in p.get('context', '')]
        assert perception_prompts, "No perception prompts captured"
        
        perception_prompt = perception_prompts[0]['prompt']
        
        # Check for "Unknown" values
        assert "Unknown" not in perception_prompt, "Perception prompt contains 'Unknown' values"
        
        # Required sections
        required_sections = [
            "COMPREHENSIVE GAME STATE DATA",
            "VISUAL ANALYSIS TASK"
        ]
        
        for section in required_sections:
            assert section in perception_prompt, f"Perception prompt missing section: {section}"
        
        # Should mention different game modes
        analysis_keywords = ["CUTSCENE", "MAP", "BATTLE", "DIALOGUE", "MENU"]
        found_keywords = [kw for kw in analysis_keywords if kw in perception_prompt]
        assert len(found_keywords) >= 3, f"Perception prompt missing analysis keywords. Found: {found_keywords}"
        
        # Check return values
        assert observation, "Perception returned empty observation"
        assert isinstance(observation, dict), "Observation should be a dict"
        assert isinstance(slow_thinking, bool), "slow_thinking should be boolean"
    
    def test_planning_prompts_strategic_sections(self, mock_vlm, sample_state_overworld):
        """Test that planning prompts include strategic planning sections"""
        memory_context = "Player is exploring Littleroot Town."
        current_plan = None  # Start with no plan
        slow_thinking_needed = True
        
        # Call planning_step
        plan = planning_step(
            memory_context,
            current_plan,
            slow_thinking_needed,
            sample_state_overworld,
            mock_vlm
        )
        
        # Check captured prompts
        planning_prompts = [p for p in mock_vlm.captured_prompts if "PLANNING" in p.get('context', '')]
        assert planning_prompts, "No planning prompts captured"
        
        planning_prompt = planning_prompts[0]['prompt']
        
        # Check for "Unknown" values
        assert "Unknown" not in planning_prompt, "Planning prompt contains 'Unknown' values"
        
        # Required sections
        required_sections = [
            "COMPREHENSIVE GAME STATE DATA",
            "STRATEGIC PLANNING TASK"
        ]
        
        for section in required_sections:
            assert section in planning_prompt, f"Planning prompt missing section: {section}"
        
        # Should include planning structure keywords
        planning_keywords = [
            "IMMEDIATE GOAL",
            "SHORT-TERM OBJECTIVES", 
            "LONG-TERM STRATEGY",
            "EFFICIENCY NOTES"
        ]
        found_keywords = [kw for kw in planning_keywords if kw in planning_prompt]
        assert len(found_keywords) >= 3, f"Planning prompt missing structure keywords. Found: {found_keywords}"
        
        # Check return value
        assert plan, "Planning returned empty plan"
        assert isinstance(plan, str), "Plan should be a string"
    
    def test_battle_state_prompts_no_unknown(self, mock_vlm, sample_state_battle):
        """Test that battle states don't produce 'Unknown' values in prompts"""
        # Test all modules with battle state
        memory_context = "In battle on Route 101."
        current_plan = "Defeat wild Pokemon."
        frame = None
        recent_actions = ["A", "A"]
        
        # 1. Perception
        observation, slow_thinking = perception_step(frame, sample_state_battle, mock_vlm)
        
        # 2. Memory
        observation_buffer = [{"frame_id": 1, "observation": observation, "state": sample_state_battle}]
        updated_memory = memory_step(memory_context, current_plan, recent_actions, observation_buffer, mock_vlm)
        
        # 3. Planning
        plan = planning_step(updated_memory, current_plan, slow_thinking, sample_state_battle, mock_vlm)
        
        # 4. Action
        actions = action_step(updated_memory, plan, observation, frame, sample_state_battle, recent_actions, mock_vlm)
        
        # Check all captured prompts for "Unknown"
        for prompt_data in mock_vlm.captured_prompts:
            prompt_text = prompt_data['prompt']
            assert "Unknown" not in prompt_text, f"Found 'Unknown' in {prompt_data['context']} prompt during battle"
    
    def test_all_modules_integration(self, mock_vlm, sample_state_overworld):
        """Test that all modules work together producing valid prompts"""
        # Simulate a full agent step
        memory_context = "Starting adventure."
        current_plan = "Explore the town."
        frame = None
        recent_actions = []
        
        # Full pipeline
        observation, slow_thinking = perception_step(frame, sample_state_overworld, mock_vlm)
        
        observation_buffer = [
            {"frame_id": 1, "observation": observation, "state": sample_state_overworld}
        ]
        updated_memory = memory_step(memory_context, current_plan, recent_actions, observation_buffer, mock_vlm)
        
        plan = planning_step(updated_memory, current_plan, slow_thinking, sample_state_overworld, mock_vlm)
        
        actions = action_step(updated_memory, plan, observation, frame, sample_state_overworld, recent_actions, mock_vlm)
        
        # Validate all outputs
        assert observation and isinstance(observation, dict)
        assert "Unknown" not in updated_memory
        assert plan and isinstance(plan, str)
        assert actions and isinstance(actions, list)
        
        # Check that we got prompts from all modules
        prompt_contexts = [p['context'] for p in mock_vlm.captured_prompts]
        assert any("PERCEPTION" in ctx for ctx in prompt_contexts), "Missing perception prompts"
        assert any("MEMORY" in ctx for ctx in prompt_contexts), "Missing memory prompts"
        assert any("PLANNING" in ctx for ctx in prompt_contexts), "Missing planning prompts"
        assert any("ACTION" in ctx for ctx in prompt_contexts), "Missing action prompts"
        
        # No prompt should contain "Unknown"
        for prompt_data in mock_vlm.captured_prompts:
            assert "Unknown" not in prompt_data['prompt'], \
                f"Found 'Unknown' in {prompt_data['context']} prompt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
