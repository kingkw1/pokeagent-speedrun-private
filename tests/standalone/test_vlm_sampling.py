#!/usr/bin/env python3
"""
Test VLM with sampling enabled instead of greedy decoding.
"""

import sys
import os
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

def test_sampling_vlm():
    """Test VLM with do_sample=True and temperature"""
    
    print("🧪 Testing VLM with Sampling Enabled...")
    
    try:
        # First, let's patch the VLM to use sampling
        from utils.vlm import LocalHuggingFaceBackend
        import time
        from PIL import Image
        import numpy as np
        
        # Create a simplified version of the generation method without logging
        def patched_get_query(self, img, text, module_name="Unknown"):
            """Modified version with sampling enabled"""
            
            # Handle both PIL Images and numpy arrays
            if isinstance(img, np.ndarray):
                img = Image.fromarray(img)
            
            # Prepare the text prompt - using the same format as before
            conversation = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "image": img,
                        },
                        {"type": "text", "text": text},
                    ],
                }
            ]
            
            # Apply chat template
            text_prompt = self.processor.apply_chat_template(
                conversation, tokenize=False, add_generation_prompt=True
            )
            
            with self.device_context():
                device = next(self.model.parameters()).device
                
                # Prepare inputs
                inputs = self.processor(text_prompt, img, return_tensors="pt")
                
                # Move inputs to device if needed
                inputs_on_device = {k: v.to(device) for k, v in inputs.items()}

                # Set termination condition for generation
                eos_token_id = self.processor.tokenizer.eos_token_id
                
                # MODIFIED: Enable sampling with temperature
                generated_ids = self.model.generate(
                    **inputs_on_device,
                    max_new_tokens=256,
                    do_sample=True,  # Enable sampling!
                    temperature=0.7,  # Add some randomness
                    top_p=0.9,       # Nucleus sampling
                    eos_token_id=eos_token_id,
                    pad_token_id=self.processor.tokenizer.pad_token_id
                )
                
                # Decode the response, removing the prompt part
                input_token_len = inputs_on_device["input_ids"].shape[1]
                generated_text = self.processor.batch_decode(
                    generated_ids[:, input_token_len:],
                    skip_special_tokens=True
                )[0]
                
                # Clean up the output
                result = generated_text.strip()
            
            return result
        
        # Monkey patch the method
        LocalHuggingFaceBackend.get_query = patched_get_query
        
        from utils.vlm import VLM
        vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")
        
        # Create a simple test image
        test_image = Image.new('RGB', (100, 100), color='blue')
        
        # Test simple navigation scenario multiple times
        navigation_prompt = """You are playing Pokemon Emerald.

SITUATION: You are in the overworld. You need to move UP to go north.

AVAILABLE ACTIONS: UP, DOWN, LEFT, RIGHT, A, B

CONTEXT: No dialogue or menus visible. Character can move freely.

INSTRUCTION: Choose the single best action to move north.

Respond with only ONE action:"""
        
        print("Testing navigation prompt with sampling...")
        responses = []
        
        for i in range(10):
            response = vlm.get_query(test_image, navigation_prompt, "sampling_test")
            clean_response = response.strip().upper()
            responses.append(clean_response)
            print(f"Response {i+1}: '{clean_response}'")
        
        print(f"\nAnalysis:")
        print(f"Total responses: {len(responses)}")
        print(f"Unique responses: {len(set(responses))} ({set(responses)})")
        print(f"Distribution: {dict([(r, responses.count(r)) for r in set(responses)])}")
        
        if len(set(responses)) > 1:
            print(f"✅ Sampling enabled variety! Got {len(set(responses))} different responses")
            return True
        else:
            print(f"❌ Still no variety even with sampling")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sampling_vlm()
    print(f"\n{'='*60}")
    if success:
        print("✅ SAMPLING VLM TEST PASSED")
    else:
        print("❌ SAMPLING VLM TEST FAILED")