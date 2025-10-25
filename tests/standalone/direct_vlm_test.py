#!/usr/bin/env python3
"""
Direct VLM text generation test to validate prompt format fix.

Tests the simplified prompt format against the old chat format
to confirm we've eliminated hallucination patterns.
"""

import sys
import os
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

def test_prompt_formats():
    """Compare old vs new prompt formats"""
    
    print("🧪 Testing VLM Prompt Formats Directly...")
    
    try:
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        import torch
        
        # Load model
        model_name = "Qwen/Qwen2-VL-2B-Instruct"
        print(f"📦 Loading {model_name}...")
        
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto"
        )
        processor = AutoProcessor.from_pretrained(model_name)
        
        # Test prompts - using actual agent prompt format
        base_text = """You are controlling a character in Pokemon Emerald.
Current step: 5
Recent actions (most recent first): A, A, DOWN, LEFT, UP

Based on the current state, choose the BEST single action.

Available actions: UP, DOWN, LEFT, RIGHT, A, B

Response format: Return ONLY the action word, nothing else.
Example responses:
- UP
- A
- RIGHT

Your response:"""

        # Old format (problematic)
        old_prompt = f"<|user|>\n{base_text}<|end|>\n<|assistant|>\n"
        
        # New format (fixed)
        new_prompt = f"Task: {base_text}\nResponse:"
        
        print(f"\n🔍 Testing OLD format:")
        print(f"Prompt: {old_prompt[:100]}...")
        
        # Test old format
        old_inputs = processor(text=old_prompt, return_tensors="pt")
        
        # Move inputs to model device
        device = next(model.parameters()).device
        old_inputs_on_device = {k: v.to(device) for k, v in old_inputs.items()}
        
        with torch.no_grad():
            old_outputs = model.generate(
                **old_inputs_on_device,
                max_new_tokens=256,  # Match actual backend
                do_sample=False,     # Match actual backend 
                pad_token_id=processor.tokenizer.eos_token_id
            )
        old_response = processor.decode(old_outputs[0], skip_special_tokens=True)
        old_response = old_response[len(old_prompt):].strip()
        print(f"OLD Response: '{old_response}'")
        
        print(f"\n🔍 Testing NEW format:")
        print(f"Prompt: {new_prompt[:100]}...")
        
        # Test new format  
        new_inputs = processor(text=new_prompt, return_tensors="pt")
        
        # Move inputs to model device
        new_inputs_on_device = {k: v.to(device) for k, v in new_inputs.items()}
        
        with torch.no_grad():
            new_outputs = model.generate(
                **new_inputs_on_device,
                max_new_tokens=256,  # Match actual backend
                do_sample=False,     # Match actual backend
                pad_token_id=processor.tokenizer.eos_token_id
            )
        new_response = processor.decode(new_outputs[0], skip_special_tokens=True)
        new_response = new_response[len(new_prompt):].strip()
        print(f"NEW Response: '{new_response}'")
        
        # Analyze responses
        old_has_chat_tokens = any(token in old_response for token in ['<|user|>', '<|assistant|>', '<|end|>'])
        new_has_chat_tokens = any(token in new_response for token in ['<|user|>', '<|assistant|>', '<|end|>'])
        
        old_is_short = len(old_response) <= 20
        new_is_short = len(new_response) <= 20
        
        # Clean up responses to extract just the action
        old_clean = old_response.split('\n')[0].split('<')[0].strip().upper()
        new_clean = new_response.split('\n')[0].strip().upper()
        
        old_is_valid_action = old_clean in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'A', 'B']
        new_is_valid_action = new_clean in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'A', 'B']
        
        print(f"\n📊 Analysis:")
        print(f"OLD format - Chat tokens: {old_has_chat_tokens}, Short: {old_is_short}, Valid action: {old_is_valid_action}, Clean: '{old_clean}'")
        print(f"NEW format - Chat tokens: {new_has_chat_tokens}, Short: {new_is_short}, Valid action: {new_is_valid_action}, Clean: '{new_clean}'")
        
        if not new_has_chat_tokens and new_is_short:
            print("✅ SUCCESS: New format eliminates chat token hallucination!")
            return True
        else:
            print("❌ New format still has issues")
            return False
            
    except Exception as e:
        print(f"❌ Direct test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Direct VLM Prompt Format Test\n")
    
    success = test_prompt_formats()
    
    if success:
        print(f"\n✅ PROMPT FORMAT FIX VALIDATED!")
        print(f"   Ready to test in full agent system")
    else:
        print(f"\n❌ PROMPT FORMAT STILL HAS ISSUES")
        print(f"   Need further investigation")