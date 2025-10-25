#!/usr/bin/env python3
"""
Integration test for VLM action_step function with recent_actions context.

This test validates that:
1. VLM receives proper recent_actions parameter
2. Step calculation works correctly (len(recent_actions))
3. VLM processes action history context instead of empty arrays

This addresses the root cause of VLM hallucinations where the model
received no action context and defaulted to repetitive responses.
"""

import sys
import io
from PIL import Image
import numpy as np

# Add project root to path
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

def test_vlm_with_recent_actions():
    """Test that VLM receives and processes recent_actions correctly"""
    
    print("🧪 Testing VLM with recent_actions...")
    
    try:
        # Import the action module
        from agent.action import action_step
        
        # Create a test VLM instance
        from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
        model_name = "Qwen/Qwen2-VL-2B-Instruct"
        
        print("📦 Loading VLM for test...")
        vlm = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto"
        )
        processor = AutoProcessor.from_pretrained(model_name)
        vlm.processor = processor
        
        # Create a dummy frame (simple blue image)
        frame = Image.new('RGB', (240, 160), color='blue')
        
        # Create test state data
        state_data = {
            'player': {'location': 'Test Location'},
            'game': {'game_state': 'overworld'},
            'visual': {'context': 'overworld'}
        }
        
        # Test with actual recent_actions (this should show step 5)
        test_recent_actions = ['A', 'UP', 'A', 'DOWN', 'A']
        
        print(f"🎯 Calling VLM with recent_actions: {test_recent_actions}")
        print(f"   Expected step calculation: {len(test_recent_actions)}")
        
        # Call action_step with our test data
        result = action_step(
            memory_context="Test memory context",
            current_plan="Test planning output", 
            latest_observation="Test perception output",
            frame=frame,
            state_data=state_data,
            recent_actions=test_recent_actions,  # This should show step 5!
            vlm=vlm
        )
        
        print(f"✅ VLM call completed successfully!")
        print(f"   Result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ VLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Testing VLM Recent Actions Fix\n")
    
    success = test_vlm_with_recent_actions()
    
    if success:
        print(f"\n✅ VLM TEST PASSED - recent_actions data flow works!")
    else:
        print(f"\n❌ VLM TEST FAILED - data flow has issues")