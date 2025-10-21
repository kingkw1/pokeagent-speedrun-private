#!/usr/bin/env python3
"""
Test to isolate the system prompt issue
"""

import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

from utils.vlm import VLM

def test_system_prompt_impact():
    """Test how different system prompts affect VLM behavior"""
    
    vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")
    
    # Simple navigation prompt
    navigation_prompt = """Playing Pokemon Emerald. Current screen: overworld

MOVEMENT PREVIEW:
  UP   : ( 10, 14) [.] WALKABLE
  DOWN : ( 10, 16) [.] WALKABLE
  LEFT : (  9, 15) [.] WALKABLE
  RIGHT: ( 11, 15) [.] WALKABLE

🚨 CRITICAL NAVIGATION INSTRUCTIONS 🚨

**YOU ARE ON A ROUTE - MOVE WITH DIRECTIONAL BUTTONS, NOT 'A'!**

Choose UP, DOWN, LEFT, or RIGHT based on your goal to travel north.

RESPOND WITH ONLY ONE BUTTON NAME: A, B, UP, DOWN, LEFT, RIGHT, START

NO explanations. NO extra text. Just one direction that's WALKABLE.
"""

    # Test different system prompts
    test_cases = [
        {
            "name": "No System Prompt",
            "system_prompt": ""
        },
        {
            "name": "Current Agent System Prompt", 
            "system_prompt": """
You are an AI agent playing Pokémon Emerald on a Game Boy Advance emulator. Your goal is to analyze the current game frame, understand the game state, and make intelligent decisions to progress efficiently. Use your perception, memory, planning, and action modules to interact with the game world. Always provide detailed, context-aware responses and consider the current situation in the game.
"""
        },
        {
            "name": "Simple System Prompt",
            "system_prompt": "You are playing Pokemon Emerald. Follow the instructions carefully."
        },
        {
            "name": "Action-Focused System Prompt",
            "system_prompt": "You are playing Pokemon Emerald. Respond with only the single button name requested."
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print("=" * 50)
        
        responses = []
        for i in range(3):
            complete_prompt = test_case['system_prompt'] + navigation_prompt
            response = vlm.get_text_query(complete_prompt, f"system_prompt_test_{i}")
            responses.append(response.strip().upper())
            print(f"   Response {i+1}: '{response.strip()}'")
        
        # Analyze
        response_counts = {}
        for response in responses:
            response_counts[response] = response_counts.get(response, 0) + 1
        
        appropriate_count = sum(1 for r in responses if r in ['UP', 'DOWN', 'LEFT', 'RIGHT'])
        inappropriate_count = sum(1 for r in responses if r == 'A')
        
        print(f"   📊 Results: {response_counts}")
        print(f"   ✅ Appropriate: {appropriate_count}/3")
        print(f"   ❌ Inappropriate (A): {inappropriate_count}/3")
        
        if inappropriate_count > 0:
            print(f"   ⚠️  SYSTEM PROMPT CAUSES 'A' BIAS!")
        else:
            print(f"   ✅ System prompt is OK")

if __name__ == "__main__":
    print("🚨 SYSTEM PROMPT ISOLATION TEST")
    print("Testing how different system prompts affect VLM navigation behavior")
    test_system_prompt_impact()