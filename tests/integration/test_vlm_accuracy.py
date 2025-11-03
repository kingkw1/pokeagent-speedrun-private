#!/usr/bin/env python3
"""
Test VLM text_box_visible on both dialog and no-dialog states
"""

import subprocess
import time
import requests
import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

def test_state(state_file, expected, name):
    print("\n" + "="*80)
    print(f"Testing: {name}")
    print(f"Expected text_box_visible: {expected}")
    print("="*80)
    
    cmd = ["python", "-m", "server.app", "--load-state", state_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        time.sleep(5)
        
        from agent.perception import perception_step
        from utils.vlm import VLM
        from PIL import Image
        import io
        import base64
        
        vlm = VLM(backend="gemini", model_name="gemini-2.0-flash-exp")
        
        state_resp = requests.get("http://localhost:8000/state", timeout=5)
        state_data = state_resp.json()
        
        frame_resp = requests.get("http://localhost:8000/api/frame", timeout=5)
        frame_data = frame_resp.json()
        image_data = base64.b64decode(frame_data['frame'])
        screenshot = Image.open(io.BytesIO(image_data))
        
        print("🔄 Running VLM perception...")
        start = time.time()
        perception_output = perception_step(screenshot, state_data, vlm)
        elapsed = time.time() - start
        
        if perception_output:
            visual_data = perception_output.get('visual_data', {})
            visual_elements = visual_data.get('visual_elements', {})
            text_box_visible = visual_elements.get('text_box_visible', None)
            dialogue = visual_data.get('on_screen_text', {}).get('dialogue', None)
            
            correct = (text_box_visible == expected)
            status = "✅ PASS" if correct else "❌ FAIL"
            
            print(f"\n   text_box_visible: {text_box_visible}")
            print(f"   dialogue: '{dialogue}'")
            print(f"   Time: {elapsed:.2f}s")
            print(f"   {status}")
            
            return {'name': name, 'expected': expected, 'result': text_box_visible, 'correct': correct}
        else:
            print("   ❌ Perception failed")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None
    finally:
        process.terminate()
        process.wait(timeout=5)

print("="*80)
print("VLM TEXT_BOX_VISIBLE DETECTION - ACCURACY TEST")
print("="*80)

results = []

# Dialog states (should have text_box_visible=True)
results.append(test_state("tests/save_states/dialog.state", True, "dialog.state"))
results.append(test_state("tests/save_states/dialog2.state", True, "dialog2.state"))
results.append(test_state("tests/save_states/dialog3.state", True, "dialog3.state"))

# No dialog states (should have text_box_visible=False)
results.append(test_state("tests/save_states/no_dialog1.state", False, "no_dialog1.state"))
results.append(test_state("tests/save_states/no_dialog2.state", False, "no_dialog2.state"))
results.append(test_state("tests/save_states/no_dialog3.state", False, "no_dialog3.state"))
results.append(test_state("tests/save_states/after_dialog.state", False, "after_dialog.state"))

# Summary
results = [r for r in results if r is not None]

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

if results:
    correct = sum(1 for r in results if r['correct'])
    total = len(results)
    accuracy = (correct/total)*100
    
    print(f"\nAccuracy: {correct}/{total} ({accuracy:.1f}%)")
    
    print(f"\n{'State':<25} {'Expected':<12} {'Result':<12} {'Status'}")
    print("-"*65)
    for r in results:
        status = "✅ PASS" if r['correct'] else "❌ FAIL"
        print(f"{r['name']:<25} {str(r['expected']):<12} {str(r['result']):<12} {status}")
    
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    if accuracy >= 95:
        print("\n✅ VLM text_box_visible is HIGHLY ACCURATE")
        print("   PROCEED with Gemini's implementation plan:")
        print("   1. Extract text_box_visible from perception output")
        print("   2. Pass it to action_step as visual_dialogue_active")
        print("   3. Prioritize pressing A when visual_dialogue_active=True")
    elif accuracy >= 75:
        print(f"\n⚠️  VLM text_box_visible is {accuracy:.1f}% accurate - acceptable but could improve")
        print("   Consider testing more edge cases before full deployment")
    else:
        print(f"\n❌ VLM text_box_visible is only {accuracy:.1f}% accurate")
        print("   Needs improvement before deployment")
else:
    print("\n❌ No valid results")
