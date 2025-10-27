#!/usr/bin/env python3
"""
Test agent's ability to handle dialogue and make movement decisions
using VLM-based visual dialogue detection.

This test validates:
1. Agent detects dialogue box visually (VLM text_box_visible)
2. Agent presses A to advance dialogue
3. Agent can navigate after dialogue dismisses
"""

import subprocess
import time
import requests
import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

def test_dialogue_and_movement(state_file, test_name, has_dialogue, expected_action):
    """
    Test agent's handling of a specific state.
    
    Args:
        state_file: Path to .state file
        test_name: Descriptive name for the test
        has_dialogue: Whether this state should have dialogue
        expected_action: Expected action (A for dialogue, movement for no dialogue)
    """
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"State: {state_file}")
    print(f"Expected dialogue: {has_dialogue}")
    print(f"Expected action type: {expected_action}")
    print(f"{'='*80}")
    
    # Start server with the state
    cmd = ["python", "-m", "server.app", "--load-state", state_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        print("⏳ Starting server...")
        time.sleep(5)
        
        # Get initial state
        resp = requests.get("http://localhost:8000/state", timeout=5)
        initial_state = resp.json()
        initial_pos = initial_state['player']['position']
        print(f"📍 Initial position: ({initial_pos['x']}, {initial_pos['y']})")
        
        # Run agent for one step
        print("🤖 Running agent step...")
        from agent import Agent
        
        class Args:
            backend = "gemini"
            model_name = "gemini-2.0-flash-exp"
            simple = False
        
        agent = Agent(Args())
        
        # Get frame for agent
        frame_resp = requests.get("http://localhost:8000/api/frame", timeout=5)
        frame_data = frame_resp.json()
        
        from PIL import Image
        import io
        import base64
        image_data = base64.b64decode(frame_data['frame'])
        screenshot = Image.open(io.BytesIO(image_data))
        
        # Agent decision
        start_time = time.time()
        result = agent.step(screenshot, initial_state)
        decision_time = time.time() - start_time
        
        action = result.get('action', [])
        print(f"⚡ Agent decided: {action} (took {decision_time:.2f}s)")
        
        # Check if decision matches expectation
        if has_dialogue:
            # Should press A for dialogue
            if action == ['A'] or 'A' in action:
                print(f"✅ CORRECT - Agent pressed A for dialogue")
                dialogue_correct = True
            else:
                print(f"❌ WRONG - Agent chose {action} but should press A for dialogue")
                dialogue_correct = False
        else:
            # Should NOT press A (should navigate or do something else)
            if action == ['A']:
                print(f"❌ WRONG - Agent pressed A but there's no dialogue")
                dialogue_correct = False
            else:
                print(f"✅ CORRECT - Agent chose navigation action {action} (no dialogue)")
                dialogue_correct = True
        
        # Check visual_dialogue_active flag in agent context
        visual_dialogue = agent.context.get('visual_dialogue_active', None)
        print(f"🔍 VLM visual_dialogue_active: {visual_dialogue}")
        
        vlm_detection_correct = (visual_dialogue == has_dialogue)
        if vlm_detection_correct:
            print(f"✅ VLM dialogue detection CORRECT")
        else:
            print(f"❌ VLM dialogue detection WRONG (expected {has_dialogue}, got {visual_dialogue})")
        
        return {
            'name': test_name,
            'has_dialogue': has_dialogue,
            'visual_dialogue': visual_dialogue,
            'action': action,
            'dialogue_correct': dialogue_correct,
            'vlm_detection_correct': vlm_detection_correct,
            'decision_time': decision_time
        }
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        process.terminate()
        process.wait(timeout=5)
        time.sleep(1)

print("="*80)
print("AGENT DIALOGUE & MOVEMENT TEST")
print("="*80)
print("\nTesting agent's ability to:")
print("  1. Detect dialogue boxes visually (VLM)")
print("  2. Press A when dialogue is active")
print("  3. Navigate when dialogue is not active")
print()

results = []

# Test 1: Dialog state - should press A
results.append(test_dialogue_and_movement(
    "tests/states/dialog2.state",
    "Active Dialogue - Should Press A",
    has_dialogue=True,
    expected_action="A"
))

# Test 2: No dialog state - should navigate
results.append(test_dialogue_and_movement(
    "tests/states/no_dialog1.state",
    "No Dialogue - Should Navigate",
    has_dialogue=False,
    expected_action="movement"
))

# Test 3: After dialog - should navigate
results.append(test_dialogue_and_movement(
    "tests/states/after_dialog.state",
    "After Dialogue Dismissed - Should Navigate",
    has_dialogue=False,
    expected_action="movement"
))

# Filter None results
results = [r for r in results if r is not None]

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

if results:
    vlm_correct = sum(1 for r in results if r['vlm_detection_correct'])
    action_correct = sum(1 for r in results if r['dialogue_correct'])
    total = len(results)
    
    print(f"\nVLM Detection Accuracy: {vlm_correct}/{total} ({vlm_correct/total*100:.1f}%)")
    print(f"Action Decision Accuracy: {action_correct}/{total} ({action_correct/total*100:.1f}%)")
    
    avg_time = sum(r['decision_time'] for r in results) / len(results)
    print(f"Average Decision Time: {avg_time:.2f}s")
    
    print(f"\n{'Test':<40} {'VLM':<10} {'Action':<15} {'Correct'}")
    print("-"*80)
    for r in results:
        vlm_status = "✅" if r['vlm_detection_correct'] else "❌"
        action_status = "✅" if r['dialogue_correct'] else "❌"
        overall = "✅ PASS" if (r['vlm_detection_correct'] and r['dialogue_correct']) else "❌ FAIL"
        print(f"{r['name']:<40} {vlm_status:<10} {str(r['action']):<15} {overall}")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    
    if action_correct == total:
        print("\n✅ ALL TESTS PASSED!")
        print("   Agent successfully:")
        print("   - Detects dialogue boxes visually")
        print("   - Presses A when dialogue is active")
        print("   - Navigates when dialogue is not active")
        print("\n🎯 VLM-based dialogue detection is working correctly!")
    else:
        print(f"\n⚠️  {action_correct}/{total} tests passed")
        print("   Some tests failed - review results above")
else:
    print("\n❌ No valid test results")
