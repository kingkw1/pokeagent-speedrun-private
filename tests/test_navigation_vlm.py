#!/usr/bin/env python3
"""
Test VLM responses during navigation phase to validate improvements.
"""

import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

from utils.vlm import VLM

def test_navigation_vlm():
    """Test VLM during navigation phase"""
    print("🧪 Testing VLM Navigation Phase Response...\n")
    
    vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")
    
    # Simulate a navigation prompt like the agent would send
    navigation_prompt = """You are controlling a character in Pokemon Emerald.
Current step: 25
Recent actions (most recent first): A, A, DOWN, UP, RIGHT

NAVIGATION MODE: You are currently navigating the overworld.
Current location: Route 101
Current goal: Travel north to find Professor Birch

Based on the current state, choose the BEST single action to continue progressing toward your goal.

Available actions: UP, DOWN, LEFT, RIGHT, A, B, START

RESPOND WITH ONLY ONE BUTTON NAME: A, B, UP, DOWN, LEFT, RIGHT, START

Your response:"""
    
    print(f"📤 Sending navigation prompt...")
    print(f"   Prompt preview: {navigation_prompt[:150]}...")
    
    try:
        response = vlm.get_text_query(navigation_prompt, "navigation_test")
        
        print(f"\n📥 VLM Response: '{response}'")
        print(f"   Response type: {type(response)}")
        print(f"   Response length: {len(response)} chars")
        
        # Check for hallucination patterns
        has_chat_tokens = any(token in response for token in ['<|user|>', '<|assistant|>', '<|end|>'])
        has_artifacts = any(token in response for token in ['</output>', '</OUTPUT>'])
        is_short = len(response) <= 50
        first_line = response.split('\n')[0].strip().upper()
        is_valid_action = first_line in ['A', 'B', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'START']
        
        print(f"\n📊 Analysis:")
        print(f"   Has chat tokens: {has_chat_tokens}")
        print(f"   Has artifacts: {has_artifacts}")
        print(f"   Is concise (≤50 chars): {is_short}")
        print(f"   First line: '{first_line}'")
        print(f"   Valid action: {is_valid_action}")
        
        if not has_chat_tokens and is_valid_action and is_short:
            print(f"\n✅ SUCCESS: VLM response is clean and actionable!")
            return True
        elif is_valid_action:
            print(f"\n⚠️ PARTIAL SUCCESS: Valid action but may be verbose")
            return True
        else:
            print(f"\n❌ ISSUES: Response has problems")
            return False
            
    except Exception as e:
        print(f"\n❌ VLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_navigation_vlm()
    print(f"\n{'='*50}")
    if success:
        print("✅ VLM NAVIGATION TEST PASSED")
    else:
        print("❌ VLM NAVIGATION TEST FAILED")