#!/usr/bin/env python3
"""
Opener Bot Quick Start Example

This script demonstrates how to use the Opener Bot in your agent.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import using direct module loading to avoid dependencies
import importlib.util
spec = importlib.util.spec_from_file_location(
    "opener_bot",
    os.path.join(os.path.dirname(__file__), '..', 'agent', 'opener_bot.py')
)
opener_bot_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(opener_bot_module)

get_opener_bot = opener_bot_module.get_opener_bot

# ============================================================================
# EXAMPLE 1: Basic Usage in Action Step
# ============================================================================

def my_action_step(state_data, visual_data, current_plan, vlm):
    """Example integration of opener bot into action selection"""
    
    # Get the global opener bot instance
    opener_bot = get_opener_bot()
    
    # Check if opener bot should handle this state
    if opener_bot.should_handle(state_data, visual_data):
        # Get programmatic action (or None for VLM fallback)
        action = opener_bot.get_action(state_data, visual_data, current_plan)
        
        if action is not None:
            print(f"🤖 Opener Bot action: {action}")
            return action
        else:
            print(f"🤖 Opener Bot fallback to VLM")
    
    # Continue with VLM-based action selection
    # ... your existing VLM logic here ...
    # return your_vlm_action_function(state_data, visual_data, vlm)
    pass  # Placeholder


# ============================================================================
# EXAMPLE 2: Checking Bot State
# ============================================================================

def check_bot_status():
    """Example of monitoring opener bot status"""
    
    opener_bot = get_opener_bot()
    summary = opener_bot.get_state_summary()
    
    print(f"Current State: {summary['current_state']}")
    print(f"Description: {summary['state_description']}")
    print(f"Attempts: {summary['attempt_count']}/{summary['max_attempts']}")
    print(f"Elapsed Time: {summary['elapsed_seconds']:.1f}s / {summary['timeout_seconds']}s")
    print(f"Last Action: {summary['last_action']}")


# ============================================================================
# EXAMPLE 3: Testing State Detection
# ============================================================================

def test_state_detection():
    """Example of testing state detection"""
    
    opener_bot = get_opener_bot()
    
    # Example: Title screen state
    state_data = {
        'game': {'state': 'title'},
        'player': {'name': '', 'location': ''},
        'milestones': {}
    }
    visual_data = {}
    
    # Detect current state
    current_state = opener_bot._detect_current_state(state_data, visual_data)
    print(f"Detected state: {current_state}")
    
    # Check if bot should handle
    should_handle = opener_bot.should_handle(state_data, visual_data)
    print(f"Should handle: {should_handle}")
    
    # Get action
    action = opener_bot.get_action(state_data, visual_data)
    print(f"Action: {action}")


# ============================================================================
# EXAMPLE 4: Resetting Bot State
# ============================================================================

def reset_for_new_run():
    """Example of resetting bot state for a new run"""
    
    opener_bot = get_opener_bot()
    opener_bot.reset()
    print("✅ Opener Bot reset to IDLE state")


# ============================================================================
# EXAMPLE 5: State-Specific Behavior
# ============================================================================

def handle_moving_van_example():
    """Example of how moving van state works"""
    
    opener_bot = get_opener_bot()
    
    # Scenario 1: Dialogue active (red triangle visible)
    state_data = {
        'game': {'state': 'running'},
        'player': {'name': 'JOHNNY', 'location': 'MOVING_VAN'},
        'milestones': {'PLAYER_NAME_SET': True}
    }
    visual_data = {
        'visual_elements': {
            'continue_prompt_visible': True,  # Red triangle!
            'text_box_visible': True
        }
    }
    
    action = opener_bot.get_action(state_data, visual_data)
    print(f"Dialogue active → Action: {action}")  # ['A']
    
    # Scenario 2: No dialogue (ready to exit)
    visual_data = {
        'visual_elements': {
            'continue_prompt_visible': False,
            'text_box_visible': False
        }
    }
    
    action = opener_bot.get_action(state_data, visual_data)
    print(f"No dialogue → Action: {action}")  # ['DOWN']


# ============================================================================
# EXAMPLE 6: Integration with Existing Agent
# ============================================================================

def complete_action_step_example(memory_context, current_plan, latest_observation, 
                                 frame, state_data, recent_actions, vlm):
    """Complete example of action_step with opener bot"""
    
    # PRIORITY 0: Opener Bot
    try:
        opener_bot = get_opener_bot()
        visual_data = latest_observation.get('visual_data', {}) if isinstance(latest_observation, dict) else {}
        
        if opener_bot.should_handle(state_data, visual_data):
            opener_action = opener_bot.get_action(state_data, visual_data, current_plan)
            
            if opener_action is not None:
                bot_state = opener_bot.get_state_summary()
                print(f"🤖 [OPENER BOT] State: {bot_state['current_state']}")
                print(f"🤖 [OPENER BOT] Action: {opener_action}")
                return opener_action
    
    except Exception as e:
        print(f"🤖 [OPENER BOT] Error: {e}")
    
    # PRIORITY 1: Red triangle dialogue detection
    visual_elements = visual_data.get('visual_elements', {})
    if visual_elements.get('continue_prompt_visible'):
        print("🔺 [DIALOGUE] Red triangle detected")
        return ['A']
    
    # PRIORITY 2+: VLM action selection
    # return your_vlm_action_function(memory_context, current_plan, frame, vlm)
    pass  # Placeholder


# ============================================================================
# Run Examples
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("OPENER BOT QUICK START EXAMPLES")
    print("="*80)
    
    print("\n--- Example 3: Testing State Detection ---")
    test_state_detection()
    
    print("\n--- Example 4: Resetting Bot State ---")
    reset_for_new_run()
    
    print("\n--- Example 5: State-Specific Behavior ---")
    handle_moving_van_example()
    
    print("\n--- Example 2: Checking Bot Status ---")
    check_bot_status()
    
    print("\n="*80)
    print("✅ Examples complete!")
    print("="*80)
