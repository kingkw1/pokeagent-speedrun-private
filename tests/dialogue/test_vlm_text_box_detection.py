#!/usr/bin/env python3
"""
Test VLM perception's text_box_visible detection accuracy

This will help us understand if the VLM can reliably detect dialogue boxes
without needing additional OCR.
"""

import subprocess
import time
import requests
import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

def test_vlm_text_box_detection(state_file, expected_text_box, name):
    """Test VLM's text_box_visible detection"""
    
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"Expected text_box_visible: {expected_text_box}")
    print(f"{'='*80}")
    
    # Start server
    cmd = ["python", "-m", "server.app", "--load-state", state_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        time.sleep(10)
        
        # Get state and frame
        from agent.perception import perception_step
        from PIL import Image
        import io
        import base64
        
        state_resp = requests.get("http://localhost:8000/state", timeout=5)
        state_data = state_resp.json()
        
        frame_resp = requests.get("http://localhost:8000/api/frame", timeout=5)
        frame_data = frame_resp.json()
        image_data = base64.b64decode(frame_data['frame'])
        screenshot = Image.open(io.BytesIO(image_data))
        
        # Run perception directly
        print("🔄 Running VLM perception (this may take ~2-3 seconds)...")
        perception_output = perception_step(
            screenshot,
            state_data,
            None  # vlm - will use default
        )
        
        if perception_output:
            visual_data = perception_output.get('visual_data', {})
            visual_elements = visual_data.get('visual_elements', {})
            text_box_visible = visual_elements.get('text_box_visible', None)
            dialogue = visual_data.get('on_screen_text', {}).get('dialogue', None)
            screen_context = visual_data.get('screen_context', None)
            
            print(f"\n📊 VLM Perception Results:")
            print(f"   text_box_visible: {text_box_visible}")
            print(f"   dialogue: '{dialogue}'")
            print(f"   screen_context: {screen_context}")
            
            # Check accuracy
            correct = (text_box_visible == expected_text_box)
            
            print(f"\n✅/❌ Evaluation:")
            print(f"   VLM detection: {'✅ CORRECT' if correct else '❌ WRONG'}")
            print(f"   Expected: {expected_text_box}, Got: {text_box_visible}")
            
            return {
                'name': name,
                'expected': expected_text_box,
                'vlm_result': text_box_visible,
                'correct': correct,
                'dialogue': dialogue
            }
        else:
            print(f"❌ Perception returned None")
            return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        process.terminate()
        process.wait(timeout=5)
        time.sleep(2)

# Test all states
print("="*80)
print("VLM TEXT_BOX_VISIBLE DETECTION TEST")
print("="*80)

results = []

# Dialog states (should have text_box_visible=True)
results.append(test_vlm_text_box_detection("tests/states/dialog.state", True, "dialog.state"))
results.append(test_vlm_text_box_detection("tests/states/dialog2.state", True, "dialog2.state"))
results.append(test_vlm_text_box_detection("tests/states/dialog3.state", True, "dialog3.state"))

# No dialog states (should have text_box_visible=False)
results.append(test_vlm_text_box_detection("tests/states/no_dialog1.state", False, "no_dialog1.state"))
results.append(test_vlm_text_box_detection("tests/states/no_dialog2.state", False, "no_dialog2.state"))
results.append(test_vlm_text_box_detection("tests/states/no_dialog3.state", False, "no_dialog3.state"))

# After dialog (should have text_box_visible=False)
results.append(test_vlm_text_box_detection("tests/states/after_dialog.state", False, "after_dialog.state"))

# Filter out None results
results = [r for r in results if r is not None]

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

if results:
    correct_count = sum(1 for r in results if r['correct'])
    total = len(results)
    
    print(f"\nVLM text_box_visible accuracy: {correct_count}/{total} correct ({correct_count/total*100:.1f}%)")
    
    print(f"\n{'State':<25} {'Expected':<15} {'VLM Result':<15} {'Status'}")
    print("-"*80)
    for r in results:
        exp_str = str(r['expected'])
        vlm_str = str(r['vlm_result'])
        status = "✅ PASS" if r['correct'] else "❌ FAIL"
        print(f"{r['name']:<25} {exp_str:<15} {vlm_str:<15} {status}")
    
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    if correct_count == total:
        print("\n✅ VLM text_box_visible is 100% ACCURATE")
        print("   RECOMMENDATION: Use VLM perception for dialogue detection")
        print("   - No extra time cost (perception already runs)")
        print("   - Visual ground truth (sees actual dialogue box)")
        print("   - Simple implementation (just check the boolean)")
    elif correct_count >= total * 0.8:
        print(f"\n⚠️  VLM text_box_visible is {correct_count/total*100:.1f}% accurate")
        print("   RECOMMENDATION: Use VLM but add validation for edge cases")
    else:
        print(f"\n❌ VLM text_box_visible is only {correct_count/total*100:.1f}% accurate")
        print("   RECOMMENDATION: Need to improve VLM prompt or use hybrid approach")
else:
    print("\n❌ No valid test results")
