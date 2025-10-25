#!/usr/bin/env python3
"""
Debug VLM prompt construction to see what the model is actually receiving.
"""

import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

def test_vlm_prompt():
    """Test what prompt the VLM is actually receiving"""
    
    print("🔍 Testing VLM Prompt Construction...")
    
    try:
        from agent.system_prompt import system_prompt
        
        # Simulate typical state data 
        visual_context = "overworld"
        strategic_goal = """
=== YOUR STRATEGIC GOAL ===
STRATEGIC GOAL: Travel north to Route 101 to find Professor Birch. Navigate through Littleroot Town and head towards the tall grass area where Professor Birch is conducting research.

"""
        
        latest_observation = {
            'dialogue': '',
            'menu_title': '',
            'pokemon_menu': {}
        }
        
        def format_observation_for_action(obs):
            if not obs:
                return "No observation data available"
            return f"Dialogue: '{obs.get('dialogue', '')}', Menu: '{obs.get('menu_title', '')}'"
        
        recent_actions = ['A', 'A', 'A', 'A', 'A']
        context_str = f"Recent actions (most recent first): {', '.join(reversed(recent_actions[-5:]))}\n\n"
        
        action_prompt = f"""Playing Pokemon Emerald. Current screen: {visual_context}

{strategic_goal}Situation: {format_observation_for_action(latest_observation)}

{context_str}

=== DECISION LOGIC ===
Based on your STRATEGIC GOAL and current situation:

1. **If DIALOGUE/TEXT visible**: Press A to advance
2. **If MENU open**: Use UP/DOWN to navigate, A to select
3. **If BATTLE**: Use A to attack or select moves
4. **If OVERWORLD with STRATEGIC GOAL**: 
   - Analyze the MOVEMENT PREVIEW above
   - Choose the single best direction (UP/DOWN/LEFT/RIGHT) that moves you closer to your goal
   - Consider obstacles, doors, and terrain in your pathfinding
5. **If uncertain or no clear goal**: Use A or explore with single direction

RESPOND WITH ONLY ONE BUTTON NAME: A, B, UP, DOWN, LEFT, RIGHT, START

NO explanations. NO extra text. NO repetition. Just one button name.
"""
        
        complete_prompt = system_prompt + action_prompt
        
        print(f"📄 Complete Prompt:")
        print(f"{'='*60}")
        print(complete_prompt)
        print(f"{'='*60}")
        
        print(f"\n📊 Prompt Analysis:")
        print(f"   Total length: {len(complete_prompt)} characters")
        print(f"   Visual context: '{visual_context}'")
        print(f"   Has strategic goal: {bool(strategic_goal.strip())}")
        print(f"   Recent actions: {recent_actions}")
        
        # Test with VLM
        from utils.vlm import VLM
        vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")
        
        print(f"\n🤖 Testing VLM Response...")
        response = vlm.get_text_query(complete_prompt, "ACTION")
        print(f"   VLM Response: '{response}'")
        print(f"   Response length: {len(response)} chars")
        
        # Check if it's always A
        print(f"\n🔄 Testing Multiple Responses...")
        responses = []
        for i in range(5):
            resp = vlm.get_text_query(complete_prompt, "ACTION")
            responses.append(resp.strip())
            print(f"   Response {i+1}: '{resp.strip()}'")
        
        unique_responses = set(responses)
        print(f"\n📈 Analysis:")
        print(f"   Unique responses: {len(unique_responses)}")
        print(f"   Response variety: {unique_responses}")
        
        if len(unique_responses) == 1:
            print(f"🚨 ISSUE: VLM always returns the same response!")
            print(f"   This suggests the prompt may be too constraining or the model is stuck.")
        else:
            print(f"✅ VLM shows response variety - prompt is working!")
        
        return len(unique_responses) > 1
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vlm_prompt()
    print(f"\n{'='*50}")
    if success:
        print("✅ VLM PROMPT TEST PASSED - Variety detected")
    else:
        print("❌ VLM PROMPT TEST FAILED - No variety")