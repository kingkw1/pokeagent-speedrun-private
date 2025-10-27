#!/usr/bin/env python3
"""
Quick test to show VLM perception output with improved Pokemon-specific prompts.
"""

import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

def test_perception_output():
    """Test the VLM perception with debug output"""
    
    print("🧪 Testing VLM Perception Output...")
    
    try:
        from agent import Agent
        from PIL import Image
        import time
        import argparse
        
        # Create args object
        args = argparse.Namespace()
        args.backend = "local"
        args.model_name = "Qwen/Qwen2-VL-2B-Instruct"
        args.simple = False
        
        # Create agent
        agent = Agent(args)
        
        # Create a test image (dummy for now)
        test_image = Image.new('RGB', (240, 160), color='blue')
        
        # Mock state data
        state_data = {
            'game': {'state': 'running', 'in_battle': False},
            'player': {'location': 'LITTLEROOT TOWN', 'name': 'BRENDAN'},
            'party': []
        }
        
        print("🔍 Calling perception_step...")
        
        # Import and call perception directly
        from agent.perception import perception_step
        
        result = perception_step(test_image, state_data, agent.vlm)
        
        print("\n✅ Perception Result:")
        print(f"   Extraction method: {result.get('extraction_method', 'unknown')}")
        if 'visual_data' in result:
            vd = result['visual_data']
            print(f"   Screen context: {vd.get('screen_context', 'missing')}")
            print(f"   On-screen text: {vd.get('on_screen_text', {})}")
            print(f"   Visible entities: {vd.get('visible_entities', [])}")
            print(f"   Visual elements: {vd.get('visual_elements', {})}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_perception_output()
    print(f"\n{'='*60}")
    if success:
        print("✅ PERCEPTION OUTPUT TEST COMPLETED")
    else:
        print("❌ PERCEPTION OUTPUT TEST FAILED")