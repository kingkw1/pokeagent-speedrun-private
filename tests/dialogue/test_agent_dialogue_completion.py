#!/usr/bin/env python3
"""
AUTOMATED TEST: Agent can clear dialogue and move

Tests the full agent (with --agent-auto) to validate it can:
1. Detect dialogue
2. Press A to clear it  
3. Move after clearing

PASS criteria: Player position changes from (12, 12) within 60 seconds

NOTE: This test uses OCR for accurate dialogue monitoring (test-only),
      while the agent uses VLM-based dialogue detection.
"""

import subprocess
import time
import requests
import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

from utils.ocr_dialogue import create_ocr_detector
from PIL import Image
import io
import base64

def test_agent_dialogue_completion():
    """Test that agent can complete dialogue and move"""
    
    print("=" * 70)
    print("🤖 AUTOMATED AGENT TEST: Dialogue Completion")
    print("=" * 70)
    print("Mode: --agent-auto (full agent)")
    print("State: tests/states/dialog.state")
    print("Pass criteria: Player moves from (12, 12) within 60 seconds")
    print("Dialogue detection: OCR (for accurate test monitoring)")
    print("=" * 70)
    
    # Initialize OCR detector for test monitoring
    ocr_detector = create_ocr_detector()
    if not ocr_detector:
        print("\n⚠️  WARNING: OCR not available, falling back to memory-based detection")
    
    # Start agent with --agent-auto
    cmd = ["python", "run.py", "--agent-auto", "--load-state", "tests/states/dialog.state"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        print("\n⏳ Starting agent (waiting 15 seconds for initialization)...")
        time.sleep(15)
        
        # Get initial state
        try:
            resp = requests.get("http://localhost:8000/state", timeout=2)
            initial_state = resp.json()
            initial_pos = (initial_state["player"]["position"]["x"], initial_state["player"]["position"]["y"])
            print(f"\n📍 Initial position: {initial_pos}")
        except:
            print("\n⚠️  Failed to get initial state - server may not be ready")
            initial_pos = (12, 12)
        
        # Monitor agent for up to 60 seconds
        print("\n📊 Monitoring agent (checking every 3 seconds):")
        print(f"{'Time':<6} {'Position':<12} {'OCR Dialog':<12} {'Actions':<10} {'Status'}")
        print("-" * 70)
        
        start_time = time.time()
        timeout = 60
        step_count = 0
        
        while time.time() - start_time < timeout:
            try:
                # Get state
                resp = requests.get("http://localhost:8000/state", timeout=2)
                state = resp.json()
                
                pos = state["player"]["position"]
                current_pos = (pos["x"], pos["y"])
                
                # Use OCR to detect dialogue (accurate for test monitoring)
                ocr_dialog = False
                if ocr_detector:
                    try:
                        frame_resp = requests.get("http://localhost:8000/api/frame", timeout=2)
                        frame_data = frame_resp.json()
                        image_data = base64.b64decode(frame_data['frame'])
                        screenshot = Image.open(io.BytesIO(image_data))
                        ocr_dialog = ocr_detector.is_dialogue_box_visible(screenshot)
                    except Exception as e:
                        ocr_dialog = state["game"].get("in_dialog", False)  # Fallback
                else:
                    ocr_dialog = state["game"].get("in_dialog", False)
                
                elapsed = int(time.time() - start_time)
                dialog_str = "YES" if ocr_dialog else "no"
                
                # Get step count from game state
                current_step = state.get("step_number", step_count)
                step_count = current_step
                
                # Check if moved
                if current_pos != initial_pos:
                    print(f"{elapsed}s{'':<3} {str(current_pos):<12} {dialog_str:<12} {step_count:<10} 🎉 MOVED!")
                    
                    print("\n" + "=" * 70)
                    print("✅ TEST PASSED!")
                    print(f"   Agent moved from {initial_pos} to {current_pos}")
                    print(f"   Time taken: {elapsed} seconds")
                    print(f"   Steps taken: {step_count}")
                    print(f"   Dialogue cleared: {'Yes' if not ocr_dialog else 'Still active'}")
                    print("=" * 70)
                    return True
                else:
                    print(f"{elapsed}s{'':<3} {str(current_pos):<12} {dialog_str:<12} {step_count:<10}")
                
            except Exception as e:
                print(f"   (Failed to get state: {e})")
            
            time.sleep(3)
        
        # Timeout
        print("\n" + "=" * 70)
        print("❌ TEST FAILED")
        print(f"   Agent did not move from {initial_pos} within {timeout} seconds")
        print(f"   Final step count: {step_count}")
        print("=" * 70)
        return False
    
    finally:
        print("\n🛑 Stopping agent...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()

if __name__ == "__main__":
    success = test_agent_dialogue_completion()
    sys.exit(0 if success else 1)
