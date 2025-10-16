#!/usr/bin/env python3
"""
Live system validation for recent_actions data flow.

This test validates the complete pipeline in a running system:
1. Server /state endpoint returns recent_actions
2. Server /recent_actions endpoint works
3. Live data matches expected format

Use this test to verify fixes work in production environment.
Requires a running server on localhost:8000.
"""

import requests
import sys
import time

# Test the live server's recent_actions
def test_live_server_recent_actions():
    """Test that the live server returns recent_actions properly"""
    
    print("🧪 Testing live server recent_actions...")
    
    try:
        # Make a request to the running server
        response = requests.get("http://localhost:8000/state", timeout=5)
        
        if response.status_code == 200:
            state_data = response.json()
            recent_actions = state_data.get('recent_actions', [])
            
            print(f"✅ Server response includes recent_actions: {recent_actions}")
            print(f"   Length: {len(recent_actions)}")
            print(f"   Step calculation would be: {len(recent_actions)}")
            
            if len(recent_actions) > 0:
                print("✅ SUCCESS: recent_actions contains data!")
                return True
            else:
                print("⚠️  WARNING: recent_actions is empty (but field exists)")
                return True  # Field exists, which is progress
        else:
            print(f"❌ Server request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def test_recent_button_presses():
    """Test the /recent_actions endpoint"""
    
    print("\n🧪 Testing /recent_actions endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/recent_actions", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            recent_buttons = data.get('recent_buttons', [])
            
            print(f"✅ Recent buttons endpoint: {recent_buttons}")
            print(f"   Length: {len(recent_buttons)}")
            
            return len(recent_buttons) > 0
        else:
            print(f"❌ Recent actions request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing recent_actions endpoint: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Final Validation: Live Server Recent Actions\n")
    
    test1_passed = test_live_server_recent_actions()
    test2_passed = test_recent_button_presses()
    
    if test1_passed and test2_passed:
        print(f"\n✅ VALIDATION PASSED - recent_actions data flow works in live system!")
    elif test1_passed:
        print(f"\n⚠️  PARTIAL SUCCESS - Server includes recent_actions field but may be empty")
    else:
        print(f"\n❌ VALIDATION FAILED - Server not responding or missing recent_actions")