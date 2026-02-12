#!/usr/bin/env python3
"""
Quick verification that VLM dialogue detection is integrated into agent
"""

import subprocess
import time
import requests
import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

print("="*80)
print("VLM DIALOGUE DETECTION - INTEGRATION VERIFICATION")
print("="*80)

# Start server with dialog state
# Using dialog2.state which is known to work well with VLM
cmd = ["python", "-m", "server.app", "--load-state", "tests/save_states/dialog2.state"]
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    print("\n⏳ Starting server...")
    time.sleep(5)
    
    # Create agent
    from agent import Agent
    
    class Args:
        backend = "gemini"
        model_name = "gemini-2.0-flash"
        simple = False
    
    print("🤖 Initializing agent...")
    agent = Agent(Args())
    
    # Get state
    resp = requests.get("http://localhost:8000/state", timeout=5)
    game_state = resp.json()
    
    # Get frame
    from PIL import Image
    import io
    import base64
    
    frame_resp = requests.get("http://localhost:8000/api/frame", timeout=5)
    frame_data = frame_resp.json()
    image_data = base64.b64decode(frame_data['frame'])
    screenshot = Image.open(io.BytesIO(image_data))
    
    # Prepare game_state for agent
    game_state_with_frame = {
        'frame': screenshot,
        'game_state': game_state.get('game', {}),
        'player': game_state.get('player', {}),
        'visual': {},
        'audio': {},
        'progress': game_state.get('milestones', {})
    }
    
    print("🔄 Running agent.step()...")
    print()
    result = agent.step(game_state_with_frame)
    print()
    
    # Check results
    print("="*80)
    print("RESULTS")
    print("="*80)
    
    action = result.get('action', [])
    visual_dialogue = agent.context.get('visual_dialogue_active', None)
    perception_output = agent.context.get('perception_output', {})
    
    print(f"\n📊 Agent Decision:")
    print(f"   Action: {action}")
    print(f"   visual_dialogue_active: {visual_dialogue}")
    
    if perception_output:
        visual_data = perception_output.get('visual_data', {})
        visual_elements = visual_data.get('visual_elements', {})
        text_box_visible = visual_elements.get('text_box_visible', None)
        screen_context = visual_data.get('screen_context', None)
        
        print(f"\n📊 VLM Perception:")
        print(f"   text_box_visible: {text_box_visible}")
        print(f"   screen_context: {screen_context}")
    
    print("\n" + "="*80)
    print("EVALUATION")
    print("="*80)
    
    checks_passed = 0
    checks_total = 3
    
    # Check 1: VLM detected dialogue
    if visual_dialogue:
        print(f"✅ VLM detected dialogue box (visual_dialogue_active=True)")
        checks_passed += 1
    else:
        print(f"❌ VLM did NOT detect dialogue (visual_dialogue_active={visual_dialogue})")
    
    # Check 2: Agent chose A action
    if action == ['A'] or 'A' in action:
        print(f"✅ Agent decided to press A")
        checks_passed += 1
    else:
        print(f"❌ Agent chose {action} instead of A")
    
    # Check 3: Integration working
    if visual_dialogue and (action == ['A'] or 'A' in action):
        print(f"✅ VLM dialogue detection integrated into agent action decision")
        checks_passed += 1
    else:
        print(f"❌ VLM detection not properly integrated")
    
    print(f"\n{'='*80}")
    if checks_passed == checks_total:
        print("✅ ALL CHECKS PASSED - VLM dialogue detection working!")
    else:
        print(f"⚠️  {checks_passed}/{checks_total} checks passed - needs debugging")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    process.terminate()
    process.wait(timeout=5)
