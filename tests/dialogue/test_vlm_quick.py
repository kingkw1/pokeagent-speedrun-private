#!/usr/bin/env python3
"""
Quick single-state test of VLM text_box_visible detection
"""

import subprocess
import time
import requests
import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

print("="*80)
print("QUICK VLM TEXT_BOX_VISIBLE TEST")
print("="*80)

# Test dialog.state (should have text_box_visible=True)
state_file = "tests/states/dialog.state"
expected = True

print(f"\nTesting: {state_file}")
print(f"Expected text_box_visible: {expected}")
print("-"*80)

# Start server
cmd = ["python", "-m", "server.app", "--load-state", state_file]
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    print("⏳ Waiting for server to start (5s)...")
    time.sleep(5)
    
    from agent.perception import perception_step
    from utils.vlm import VLM
    from PIL import Image
    import io
    import base64
    
    print("� Initializing VLM...")
    vlm = VLM(backend="gemini", model_name="gemini-2.0-flash-exp")
    
    print("�📥 Getting state and frame...")
    state_resp = requests.get("http://localhost:8000/state", timeout=5)
    state_data = state_resp.json()
    
    frame_resp = requests.get("http://localhost:8000/api/frame", timeout=5)
    frame_data = frame_resp.json()
    image_data = base64.b64decode(frame_data['frame'])
    screenshot = Image.open(io.BytesIO(image_data))
    
    print("🔄 Running VLM perception (~2-3 seconds)...")
    start_time = time.time()
    perception_output = perception_step(screenshot, state_data, vlm)
    elapsed = time.time() - start_time
    
    print(f"✅ Perception completed in {elapsed:.2f}s")
    
    if perception_output:
        visual_data = perception_output.get('visual_data', {})
        visual_elements = visual_data.get('visual_elements', {})
        text_box_visible = visual_elements.get('text_box_visible', None)
        dialogue = visual_data.get('on_screen_text', {}).get('dialogue', None)
        screen_context = visual_data.get('screen_context', None)
        
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        print(f"text_box_visible: {text_box_visible}")
        print(f"dialogue: '{dialogue}'")
        print(f"screen_context: {screen_context}")
        
        correct = (text_box_visible == expected)
        
        print("\n" + "="*80)
        print("EVALUATION")
        print("="*80)
        if correct:
            print(f"✅ CORRECT - Expected {expected}, got {text_box_visible}")
            print("\n🎯 CONCLUSION: VLM text_box_visible detection works!")
            print("   You can safely use it for dialogue detection.")
        else:
            print(f"❌ WRONG - Expected {expected}, got {text_box_visible}")
            print("\n⚠️  CONCLUSION: VLM text_box_visible may need tuning")
            print("   Check the perception prompt or test with more states.")
    else:
        print("\n❌ Perception returned None")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    process.terminate()
    process.wait(timeout=5)
    print("\n✅ Server stopped")
