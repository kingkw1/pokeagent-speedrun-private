#!/usr/bin/env python3
"""
FPS Adjustment System Integration Tests

Purpose:
    Verify emulator FPS adjustment system works correctly:
    - 30 FPS during normal gameplay
    - 120 FPS (4x speed) during dialogue
    - Automatic FPS reversion after dialogue ends

Test Cases:
    - Base overworld: simple_test.state → 30 FPS expected
    - Dialog state: dialog.state → 120 FPS expected
    - Dialog state 2: dialog2.state → 120 FPS expected
    - After dialog: after_dialog.state → 30 FPS expected

Dependencies:
    - Save states: simple_test.state, dialog.state, dialog2.state, after_dialog.state
    - External services: Spawns server for each state

Runtime:
    ~5-8 seconds per test case (server startup + FPS measurement)
"""

import pytest
import subprocess
import time
import requests
import os
import sys

# Test data
TEST_CASES = [
    {
        "state_file": "tests/save_states/simple_test.state",
        "expected_fps": 30,
        "test_name": "Base Overworld State"
    },
    {
        "state_file": "tests/save_states/dialog.state", 
        "expected_fps": 120,
        "test_name": "Dialog State"
    },
    {
        "state_file": "tests/save_states/dialog2.state",
        "expected_fps": 120,
        "test_name": "Dialog State 2"
    },
    {
        "state_file": "tests/save_states/after_dialog.state",
        "expected_fps": 30,
        "test_name": "After Dialog Ends"
    }
]

class ServerManager:
    """Manages server startup and shutdown for tests"""
    
    def __init__(self):
        self.server_process = None
    
    def start_server(self, state_file):
        """Start the server with a specific state file"""
        print(f"🚀 Starting server with state: {state_file}")
        cmd = ["python", "-m", "server.app", "--manual", "--load-state", state_file]
        
        try:
            self.server_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            # Wait for server to start
            print("⏳ Waiting for server to start...")
            time.sleep(5)
            
            # Test if server is responding
            response = requests.get("http://localhost:8000/status", timeout=5)
            if response.status_code == 200:
                print("✅ Server started successfully")
                return True
            else:
                print(f"❌ Server not responding: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the server cleanly"""
        if self.server_process:
            print("🛑 Stopping server...")
            try:
                # Try graceful shutdown first
                requests.post("http://localhost:8000/stop", timeout=2)
                time.sleep(1)
            except:
                pass
            
            # Force terminate if still running
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print("✅ Server stopped gracefully")
            except subprocess.TimeoutExpired:
                print("⚠️  Server didn't stop gracefully, force killing...")
                self.server_process.kill()
                self.server_process.wait()
                print("✅ Server force killed")

def check_fps(expected_fps, test_name):
    """Check if the current FPS matches the expected value"""
    try:
        response = requests.get("http://localhost:8000/status", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not responding: {response.status_code}")
            return False
        
        status = response.json()
        base_fps = status.get('base_fps')
        current_fps = status.get('current_fps')
        is_dialog = status.get('is_dialog')
        fps_multiplier = status.get('fps_multiplier')
        
        print(f"   Base FPS: {base_fps}")
        print(f"   Current FPS: {current_fps}")
        print(f"   Is Dialog: {is_dialog}")
        print(f"   FPS Multiplier: {fps_multiplier}")
        
        if current_fps == expected_fps:
            print(f"✅ {test_name}: {current_fps} FPS (expected: {expected_fps}) - PASS")
            return True
        else:
            print(f"❌ {test_name}: {current_fps} FPS (expected: {expected_fps}) - FAIL")
            return False
            
    except Exception as e:
        print(f"❌ Error checking FPS: {e}")
        return False

@pytest.fixture(scope="session", autouse=True)
def check_environment():
    """Check that we're in the right environment before running tests"""
    # Check if we're in the right directory
    if not os.path.exists("server/app.py"):
        pytest.fail("❌ Error: This test must be run from the project root directory")
    
    # Check if state files exist
    required_files = [
        "tests/save_states/simple_test.state",
        "tests/save_states/dialog.state", 
        "tests/save_states/dialog2.state",
        "tests/save_states/after_dialog.state"
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        pytest.fail(f"❌ Error: Missing required state files: {missing_files}")

@pytest.mark.parametrize("test_case", TEST_CASES)
def test_fps_adjustment(test_case):
    """Test FPS adjustment for a specific state"""
    state_file = test_case["state_file"]
    expected_fps = test_case["expected_fps"]
    test_name = test_case["test_name"]
    
    print(f"\n🎮 Testing {test_name}")
    print("=" * 50)
    print(f"State file: {state_file}")
    print(f"Expected FPS: {expected_fps}")
    
    # Check if state file exists
    if not os.path.exists(state_file):
        pytest.fail(f"❌ State file not found: {state_file}")
    
    # Start server
    server = ServerManager()
    if not server.start_server(state_file):
        pytest.fail("Failed to start server")
    
    try:
        # For after_dialog state, wait for the 5-second timeout to expire
        if "after_dialog" in state_file:
            print("⏳ Waiting 6 seconds for dialog FPS timeout to expire...")
            time.sleep(6)
        
        # Check FPS
        result = check_fps(expected_fps, test_name)
        
        # Assert the result
        assert result, f"FPS check failed for {test_name}"
        
    finally:
        # Stop server
        server.stop_server()
        
        # Wait between tests
        time.sleep(2)

def test_fps_adjustment_summary():
    """Test summary - this will run after all individual tests"""
    print("\n📋 FPS Adjustment System Test Summary")
    print("=" * 50)
    print("This test verifies the FPS adjustment system:")
    print("1. Base overworld state: 30 FPS")
    print("2. Dialog state: 120 FPS (4x speedup)")
    print("3. Dialog state 2: 120 FPS (4x speedup) - Currently failing, needs investigation")
    print("4. After dialog ends: 30 FPS (reverted)")
    print()
    print("🎉 All individual FPS tests completed!")
    print("Note: Dialog State 2 is expected to fail until the dialog detection is improved") 