#!/usr/bin/env python3
"""
COMPREHENSIVE DIALOGUE DETECTION TEST

Tests dialogue detection accuracy across ALL dialogue states in tests/states/:
- dialog.state, dialog2.state, dialog3.state (should have in_dialog=True)
- after_dialog.state (should have in_dialog=False - dialogue already dismissed)
- no_dialog1.state, no_dialog2.state, no_dialog3.state (should have in_dialog=False)

This validates that our fixed is_in_dialog() function correctly detects:
1. Active dialogue that blocks player movement
2. Dismissed/cleared dialogue (no longer blocking)
3. States with no dialogue at all

Pass criteria: All states correctly identified
"""

import subprocess
import time
import requests
import sys

# Test cases: (state_file, expected_in_dialog, description)
TEST_CASES = [
    # States that SHOULD have active dialogue (in_dialog=True)
    ("tests/states/dialog.state", True, "PC dialogue in player's house"),
    ("tests/states/dialog2.state", True, "Second dialogue state"),
    ("tests/states/dialog3.state", True, "Third dialogue state"),
    
    # States that should NOT have active dialogue (in_dialog=False)
    ("tests/states/after_dialog.state", False, "After dialogue was dismissed"),
    ("tests/states/no_dialog1.state", False, "No dialogue - first state"),
    ("tests/states/no_dialog2.state", False, "No dialogue - second state"),
    ("tests/states/no_dialog3.state", False, "No dialogue - third state"),
]

def test_state(state_file, expected_in_dialog, description):
    """Test a single state file for correct dialogue detection"""
    
    print(f"\n{'='*80}")
    print(f"Testing: {state_file}")
    print(f"Description: {description}")
    print(f"Expected in_dialog: {expected_in_dialog}")
    print(f"{'='*80}")
    
    # Start server with this state
    cmd = ["python", "-m", "server.app", "--load-state", state_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # Wait for server to initialize
        time.sleep(10)
        
        # Get state from server
        try:
            resp = requests.get("http://localhost:8000/state", timeout=2)
            if resp.status_code != 200:
                print(f"❌ FAIL: Server returned status {resp.status_code}")
                return False
                
            state = resp.json()
            
            # Extract dialogue detection info
            in_dialog = state['game'].get('in_dialog', False)
            overworld_visible = state['game'].get('overworld_visible', False)
            movement_enabled = state['game'].get('movement_enabled', False)
            
            # Get additional context
            position = state['player']['position']
            pos = (position['x'], position['y'])
            
            print(f"\n📊 Results:")
            print(f"   in_dialog:         {in_dialog}")
            print(f"   overworld_visible: {overworld_visible}")
            print(f"   movement_enabled:  {movement_enabled}")
            print(f"   position:          {pos}")
            
            # Validate
            if in_dialog == expected_in_dialog:
                print(f"\n✅ PASS - Dialogue detection is CORRECT")
                print(f"   Expected: in_dialog={expected_in_dialog}")
                print(f"   Got:      in_dialog={in_dialog}")
                return True
            else:
                print(f"\n❌ FAIL - Dialogue detection is WRONG")
                print(f"   Expected: in_dialog={expected_in_dialog}")
                print(f"   Got:      in_dialog={in_dialog}")
                
                # If we expected dialogue but didn't detect it, check if player can move
                if expected_in_dialog and not in_dialog:
                    print(f"\n🔍 Testing if player is actually frozen (dialogue blocking)...")
                    
                    # Try to move
                    resp = requests.post("http://localhost:8000/action", json={"buttons": ["UP"]}, timeout=2)
                    time.sleep(3)
                    
                    resp = requests.get("http://localhost:8000/state", timeout=2)
                    new_state = resp.json()
                    new_pos_data = new_state['player']['position']
                    new_pos = (new_pos_data['x'], new_pos_data['y'])
                    
                    if new_pos == pos:
                        print(f"   Player CANNOT move (still at {pos}) - dialogue IS blocking!")
                        print(f"   ⚠️  FALSE NEGATIVE: Dialogue exists but not detected!")
                    else:
                        print(f"   Player CAN move ({pos} → {new_pos}) - no active dialogue")
                        print(f"   ℹ️  State file may be mislabeled or dialogue already dismissed")
                
                return False
                
        except Exception as e:
            print(f"❌ FAIL: Error getting state from server: {e}")
            return False
            
    finally:
        # Stop server
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        # Small delay before next test
        time.sleep(2)

def main():
    """Run all test cases"""
    
    print("=" * 80)
    print("🧪 COMPREHENSIVE DIALOGUE DETECTION TEST")
    print("=" * 80)
    print(f"Testing {len(TEST_CASES)} states to validate is_in_dialog() accuracy")
    print("=" * 80)
    
    results = []
    
    for state_file, expected_in_dialog, description in TEST_CASES:
        result = test_state(state_file, expected_in_dialog, description)
        results.append((state_file, expected_in_dialog, result))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, _, result in results if result)
    failed = len(results) - passed
    
    for state_file, expected, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        expected_str = "Dialog" if expected else "No Dialog"
        print(f"{status} - {state_file:<35} (expected: {expected_str})")
    
    print("=" * 80)
    print(f"Results: {passed}/{len(results)} passed, {failed}/{len(results)} failed")
    print("=" * 80)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - Dialogue detection is working correctly!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed - Dialogue detection needs investigation")
        return 1

if __name__ == "__main__":
    sys.exit(main())
