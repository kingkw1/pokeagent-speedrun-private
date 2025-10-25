#!/usr/bin/env python3
"""
Test improved VLM prompting with more specific contexts.
"""

import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

def test_improved_prompts():
    """Test VLM with more specific and varied prompts"""
    
    print("🧪 Testing Improved VLM Prompts...")
    
    try:
        from utils.vlm import VLM
        vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")
        
        # Test different scenarios with clear context
        test_scenarios = [
            {
                "name": "Navigation North",
                "prompt": """You are playing Pokemon Emerald.

SITUATION: You are in the overworld standing in front of your house. Your goal is to go NORTH to find Professor Birch.

AVAILABLE ACTIONS: UP, DOWN, LEFT, RIGHT, A, B

CONTEXT: No dialogue visible. No menus open. Character is standing in overworld facing a clear path northward.

INSTRUCTION: Choose the single best action to move toward your goal of going north.

Respond with only ONE action:"""
            },
            {
                "name": "Menu Navigation", 
                "prompt": """You are playing Pokemon Emerald.

SITUATION: A menu is open on screen. The cursor is currently on "BAG" but you want to select "POKEMON".

AVAILABLE ACTIONS: UP, DOWN, LEFT, RIGHT, A, B

CONTEXT: Menu is visible. Need to navigate UP to reach POKEMON option.

INSTRUCTION: Choose the action to navigate to POKEMON in the menu.

Respond with only ONE action:"""
            },
            {
                "name": "Dialogue Advance",
                "prompt": """You are playing Pokemon Emerald.

SITUATION: Text dialogue is displayed on screen from an NPC. The text says "Welcome to the world of Pokemon!"

AVAILABLE ACTIONS: UP, DOWN, LEFT, RIGHT, A, B

CONTEXT: Dialogue box is visible. Need to advance the text.

INSTRUCTION: Choose the action to advance the dialogue.

Respond with only ONE action:"""
            },
            {
                "name": "Exploration",
                "prompt": """You are playing Pokemon Emerald.

SITUATION: You are in an open area with paths in multiple directions. You need to explore westward.

AVAILABLE ACTIONS: UP, DOWN, LEFT, RIGHT, A, B

CONTEXT: No dialogue or menus. Character can move freely in overworld. West path is clear.

INSTRUCTION: Choose the action to move west for exploration.

Respond with only ONE action:"""
            }
        ]
        
        print(f"Testing {len(test_scenarios)} different scenarios...\n")
        
        results = {}
        for scenario in test_scenarios:
            print(f"🎯 Testing: {scenario['name']}")
            
            # Test this scenario 3 times to check consistency
            responses = []
            for i in range(3):
                response = vlm.get_text_query(scenario['prompt'], "ACTION")
                clean_response = response.strip().upper()
                responses.append(clean_response)
                print(f"   Response {i+1}: '{clean_response}'")
            
            results[scenario['name']] = responses
            print()
        
        # Analyze results
        print("📊 Analysis:")
        print("="*50)
        
        all_responses = []
        for scenario_name, responses in results.items():
            unique = set(responses)
            all_responses.extend(responses)
            print(f"{scenario_name}:")
            print(f"   Responses: {responses}")
            print(f"   Unique: {len(unique)} ({unique})")
        
        print(f"\nOverall Analysis:")
        print(f"   Total responses: {len(all_responses)}")
        print(f"   Unique responses: {len(set(all_responses))} ({set(all_responses)})")
        print(f"   Response distribution: {dict([(r, all_responses.count(r)) for r in set(all_responses)])}")
        
        # Expected responses for each scenario
        expected = {
            "Navigation North": "UP",
            "Menu Navigation": "UP", 
            "Dialogue Advance": "A",
            "Exploration": "LEFT"
        }
        
        print(f"\nExpected vs Actual:")
        correct = 0
        for scenario_name, responses in results.items():
            expected_action = expected[scenario_name]
            most_common = max(set(responses), key=responses.count)
            is_correct = most_common == expected_action
            if is_correct:
                correct += 1
            print(f"   {scenario_name}: Expected {expected_action}, Got {most_common} {'✅' if is_correct else '❌'}")
        
        success_rate = correct / len(test_scenarios)
        print(f"\nSuccess Rate: {correct}/{len(test_scenarios)} ({success_rate:.1%})")
        
        if len(set(all_responses)) > 1:
            print(f"\n✅ VLM shows response variety!")
            if success_rate >= 0.5:
                print(f"✅ VLM responses are contextually appropriate!")
                return True
            else:
                print(f"⚠️ VLM variety exists but responses may need prompt tuning")
                return True
        else:
            print(f"\n❌ VLM still shows no variety - all responses are: {list(set(all_responses))}")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_improved_prompts()
    print(f"\n{'='*60}")
    if success:
        print("✅ IMPROVED VLM PROMPTING TEST PASSED")
    else:
        print("❌ IMPROVED VLM PROMPTING TEST FAILED")