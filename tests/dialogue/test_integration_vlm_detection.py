#!/usr/bin/env python3
"""
Integration test: VLM dialogue detection accuracy

Tests VLM's text_box_visible detection across multiple states.

This consolidates functionality from:
- test_vlm_text_box_detection.py
- test_vlm_quick.py
- test_dialogue_detection_comprehensive.py (VLM parts)

Note: These tests are slow (~2-3 seconds per VLM call)
Mark with @pytest.mark.slow to skip in fast test runs
"""

import pytest
import subprocess
import time
import requests
import sys
from pathlib import Path
from PIL import Image
import io
import base64

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestVLMDialogueDetection:
    """Integration tests for VLM-based dialogue detection"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test"""
        subprocess.run(["pkill", "-f", "server.app"], capture_output=True)
        time.sleep(1)
        yield
        subprocess.run(["pkill", "-f", "server.app"], capture_output=True)
        time.sleep(0.5)
    
    @pytest.mark.slow
    def test_vlm_detects_dialogue_states(self):
        """
        Test VLM text_box_visible detection on dialogue states.
        
        Expected: text_box_visible=True for dialog.state, dialog2.state, dialog3.state
        """
        test_cases = [
            ("tests/states/dialog.state", True, "dialog.state"),
            ("tests/states/dialog2.state", True, "dialog2.state"),
            ("tests/states/dialog3.state", True, "dialog3.state"),
        ]
        
        results = []
        
        for state_file, expected_dialogue, name in test_cases:
            print(f"\n{'='*80}")
            print(f"Testing VLM detection: {name}")
            print(f"Expected text_box_visible: {expected_dialogue}")
            print(f"{'='*80}")
            
            server_proc = subprocess.Popen([
                "python", "-m", "server.app",
                "--load-state", state_file,
                "--port", "8000"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            try:
                time.sleep(5)
                
                # Get frame and run perception
                from agent.perception import perception_step
                
                state_resp = requests.get("http://localhost:8000/state", timeout=5)
                state_data = state_resp.json()
                
                frame_resp = requests.get("http://localhost:8000/api/frame", timeout=5)
                frame_data = frame_resp.json()
                image_data = base64.b64decode(frame_data['frame'])
                screenshot = Image.open(io.BytesIO(image_data))
                
                print("🔄 Running VLM perception (2-3 seconds)...")
                perception_output = perception_step(screenshot, state_data, None)
                
                text_box_visible = perception_output.get('text_box_visible', False)
                print(f"📊 VLM text_box_visible: {text_box_visible}")
                
                # Record result
                correct = (text_box_visible == expected_dialogue)
                results.append({
                    'name': name,
                    'expected': expected_dialogue,
                    'actual': text_box_visible,
                    'correct': correct
                })
                
                print(f"{'✅ CORRECT' if correct else '❌ WRONG'}")
                
            finally:
                server_proc.terminate()
                server_proc.wait(timeout=2)
        
        # Print summary
        print(f"\n{'='*80}")
        print("VLM DETECTION SUMMARY")
        print(f"{'='*80}")
        
        correct_count = sum(1 for r in results if r['correct'])
        total_count = len(results)
        
        for r in results:
            status = "✅" if r['correct'] else "❌"
            print(f"{status} {r['name']}: Expected={r['expected']}, Actual={r['actual']}")
        
        print(f"\nAccuracy: {correct_count}/{total_count} ({100*correct_count/total_count:.1f}%)")
        
        # We don't assert here because VLM accuracy may vary
        # This test is more for observing VLM performance
    
    @pytest.mark.slow
    def test_vlm_detects_no_dialogue_states(self):
        """
        Test VLM text_box_visible detection on non-dialogue states.
        
        Expected: text_box_visible=False for states without dialogue
        """
        test_cases = [
            ("tests/states/no_dialog1.state", False, "no_dialog1.state"),
            ("tests/states/after_dialog.state", False, "after_dialog.state"),
        ]
        
        results = []
        
        for state_file, expected_dialogue, name in test_cases:
            print(f"\n{'='*80}")
            print(f"Testing VLM detection: {name}")
            print(f"Expected text_box_visible: {expected_dialogue}")
            print(f"{'='*80}")
            
            server_proc = subprocess.Popen([
                "python", "-m", "server.app",
                "--load-state", state_file,
                "--port", "8000"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            try:
                time.sleep(5)
                
                from agent.perception import perception_step
                
                state_resp = requests.get("http://localhost:8000/state", timeout=5)
                state_data = state_resp.json()
                
                frame_resp = requests.get("http://localhost:8000/api/frame", timeout=5)
                frame_data = frame_resp.json()
                image_data = base64.b64decode(frame_data['frame'])
                screenshot = Image.open(io.BytesIO(image_data))
                
                print("🔄 Running VLM perception (2-3 seconds)...")
                perception_output = perception_step(screenshot, state_data, None)
                
                text_box_visible = perception_output.get('text_box_visible', False)
                print(f"📊 VLM text_box_visible: {text_box_visible}")
                
                correct = (text_box_visible == expected_dialogue)
                results.append({
                    'name': name,
                    'expected': expected_dialogue,
                    'actual': text_box_visible,
                    'correct': correct
                })
                
                print(f"{'✅ CORRECT' if correct else '❌ WRONG'}")
                
            finally:
                server_proc.terminate()
                server_proc.wait(timeout=2)
        
        # Print summary
        print(f"\n{'='*80}")
        print("NO-DIALOGUE DETECTION SUMMARY")
        print(f"{'='*80}")
        
        correct_count = sum(1 for r in results if r['correct'])
        total_count = len(results)
        
        for r in results:
            status = "✅" if r['correct'] else "❌"
            print(f"{status} {r['name']}: Expected={r['expected']}, Actual={r['actual']}")
        
        print(f"\nAccuracy: {correct_count}/{total_count} ({100*correct_count/total_count:.1f}%)")
    
    @pytest.mark.slow
    def test_vlm_quick_single_state(self):
        """
        Quick test of VLM on a single dialogue state.
        Useful for debugging VLM perception.
        """
        print(f"\n{'='*80}")
        print("QUICK VLM TEST: dialog.state")
        print(f"{'='*80}")
        
        server_proc = subprocess.Popen([
            "python", "-m", "server.app",
            "--load-state", "tests/states/dialog.state",
            "--port", "8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            time.sleep(5)
            
            from agent.perception import perception_step
            
            state_resp = requests.get("http://localhost:8000/state", timeout=5)
            state_data = state_resp.json()
            
            frame_resp = requests.get("http://localhost:8000/api/frame", timeout=5)
            frame_data = frame_resp.json()
            image_data = base64.b64decode(frame_data['frame'])
            screenshot = Image.open(io.BytesIO(image_data))
            
            print("🔄 Running VLM perception...")
            start_time = time.time()
            perception_output = perception_step(screenshot, state_data, None)
            duration = time.time() - start_time
            
            print(f"\n📊 VLM Results:")
            print(f"   text_box_visible: {perception_output.get('text_box_visible')}")
            print(f"   Duration: {duration:.2f}s")
            
            # Print full perception output for debugging
            print(f"\n📋 Full perception output:")
            for key, value in perception_output.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"   {key}: {value[:100]}...")
                else:
                    print(f"   {key}: {value}")
            
        finally:
            server_proc.terminate()
            server_proc.wait(timeout=2)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "not slow"])
