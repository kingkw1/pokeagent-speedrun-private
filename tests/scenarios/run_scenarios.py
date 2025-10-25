#!/usr/bin/env python3
"""
Scenario-based end-to-end testing using save states.
Each test loads a save state, runs the agent for N steps, and checks success criteria.

Usage:
    python tests/test_scenario_runner.py                    # Run all tests
    python tests/test_scenario_runner.py "exit van"         # Run specific test
    python tests/test_scenario_runner.py --list             # List all tests
"""

import subprocess
import time
import requests
import signal
import os
import sys
import argparse
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ScenarioTest:
    """Represents a single scenario test with save state and success criteria"""
    
    def __init__(self, name, save_state, max_steps, success_fn, description=""):
        self.name = name
        self.save_state = save_state
        self.max_steps = max_steps
        self.success_fn = success_fn
        self.description = description
    
    def run(self, port=8001, verbose=False):
        """
        Run the scenario test
        
        Args:
            port: Port to use for the server (avoid conflicts with running instances)
            verbose: Show detailed output from subprocess
            
        Returns:
            bool: True if test passed, False otherwise
        """
        print(f"\n{'='*70}")
        print(f"🧪 TEST: {self.name}")
        if self.description:
            print(f"📝 {self.description}")
        print(f"📁 Save state: {self.save_state}")
        print(f"🎯 Max steps: {self.max_steps}")
        print(f"{'='*70}")
        
        # Verify save state exists
        if not os.path.exists(self.save_state):
            print(f"❌ ERROR: Save state file not found: {self.save_state}")
            return False
        
        # Start run.py as subprocess
        cmd = [
            sys.executable,  # Use same Python as test runner
            "run.py",
            "--load-state", self.save_state,
            "--agent-auto",
            "--headless",
            "--port", str(port)
        ]
        
        print(f"🚀 Starting agent: {' '.join(cmd)}")
        
        # Redirect output based on verbose flag
        if verbose:
            stdout = None
            stderr = None
        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE
        
        process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, cwd=os.getcwd())
        
        try:
            # Wait for server to start (longer initial wait)
            print("⏳ Waiting for server to initialize...")
            time.sleep(8)
            
            # Poll state endpoint for up to max_steps
            start_time = time.time()
            last_location = None
            steps_checked = 0
            consecutive_timeouts = 0
            max_consecutive_timeouts = 5
            
            # Use tqdm for progress tracking
            with tqdm(total=self.max_steps, desc="Test Progress", unit="step") as pbar:
                for step in range(self.max_steps):
                    try:
                        # Get current state from server with generous timeout for VLM calls
                        # VLM inference can take 3-5s, plus overhead = 15s is safer
                        response = requests.get(f"http://127.0.0.1:{port}/state", timeout=15)
                        
                        if response.status_code == 200:
                            state_data = response.json()
                            steps_checked += 1
                            consecutive_timeouts = 0  # Reset timeout counter on success
                            
                            # Extract current location for progress tracking
                            current_location = state_data.get('player', {}).get('location', 'unknown')
                            current_pos = state_data.get('player', {}).get('position', {})
                            pos_str = f"({current_pos.get('x', '?')}, {current_pos.get('y', '?')})"
                            
                            # Update progress bar
                            pbar.update(1)
                            pbar.set_postfix({
                                'location': current_location[:20],
                                'pos': pos_str,
                                'checks': steps_checked
                            })
                            
                            # Show location changes
                            if current_location != last_location:
                                elapsed = time.time() - start_time
                                tqdm.write(f"   📍 Location changed: {current_location} {pos_str} [{elapsed:.1f}s]")
                                last_location = current_location
                            
                            # Check success condition
                            if self.success_fn(state_data):
                                elapsed = time.time() - start_time
                                tqdm.write(f"\n✅ PASS: {self.name}")
                                tqdm.write(f"   ⏱️  Completed in {steps_checked} checks ({elapsed:.1f}s)")
                                tqdm.write(f"   📍 Final location: {current_location} {pos_str}")
                                return True
                        
                        # Wait before next check - adjust based on step time
                        # If steps are taking 5s each, no need for extra wait
                        time.sleep(1)  # Brief pause to avoid hammering the server
                        
                    except requests.exceptions.ConnectionError:
                        # Server not ready yet or crashed
                        if step < 3:  # Give it a few tries at the start
                            tqdm.write(f"   ⏳ Waiting for server (attempt {step+1})...")
                            time.sleep(2)
                            continue
                        else:
                            tqdm.write(f"\n❌ FAIL: {self.name} - Server connection lost")
                            return False
                            
                    except requests.exceptions.Timeout:
                        consecutive_timeouts += 1
                        tqdm.write(f"   ⚠️  Request timeout at step {step} (consecutive: {consecutive_timeouts}/{max_consecutive_timeouts})")
                        
                        # If too many consecutive timeouts, agent is probably stuck
                        if consecutive_timeouts >= max_consecutive_timeouts:
                            tqdm.write(f"\n❌ FAIL: {self.name} - Too many consecutive timeouts")
                            tqdm.write(f"   Agent appears to be hanging on VLM calls")
                            return False
                        continue
                        
                    except Exception as e:
                        tqdm.write(f"   ⚠️  Error at step {step}: {e}")
                        continue
            
            # Test timed out
            elapsed = time.time() - start_time
            print(f"\n❌ FAIL: {self.name} - Timeout")
            print(f"   ⏱️  Ran for {self.max_steps} steps ({elapsed:.1f}s)")
            print(f"   📍 Final location: {last_location if last_location else 'unknown'}")
            return False
            
        finally:
            # Cleanup subprocess
            print(f"🧹 Cleaning up process (PID {process.pid})...")
            process.terminate()
            try:
                process.wait(timeout=5)
                print("   ✅ Process terminated cleanly")
            except subprocess.TimeoutExpired:
                print("   ⚠️  Force killing process...")
                process.kill()
                process.wait()


# =============================================================================
# TEST DEFINITIONS
# =============================================================================

def check_exit_moving_van(state_data):
    """
    Success: Player exits the moving van and enters the house
    Expected location change: MOVING_VAN -> LITTLEROOT_TOWN_BRENDANS_HOUSE_2F
    """
    location = state_data.get('player', {}).get('location', '')
    
    # Accept either the exact house location or Littleroot Town (outside)
    success_locations = [
        'LITTLEROOT_TOWN_BRENDANS_HOUSE_2F',
        'LITTLEROOT_TOWN_BRENDANS_HOUSE_1F',
        'LITTLEROOT_TOWN'
    ]
    
    return location in success_locations


def check_navigate_route_101(state_data):
    """
    Success: Player reaches Route 101
    Expected: Location contains 'ROUTE 101' or 'ROUTE_101'
    """
    location = state_data.get('player', {}).get('location', '').upper()
    return 'ROUTE 101' in location or 'ROUTE_101' in location


def check_exit_house(state_data):
    """
    Success: Player exits house to Littleroot Town
    Expected: Location changes from house to LITTLEROOT_TOWN
    """
    location = state_data.get('player', {}).get('location', '')
    return location == 'LITTLEROOT_TOWN' and 'HOUSE' not in location.upper()


def check_dialogue_complete(state_data):
    """
    Success: Active dialogue box closes
    Expected: dialogue.active becomes False
    """
    game_data = state_data.get('game', {})
    dialogue = game_data.get('dialogue', {})
    return not dialogue.get('active', False)


# =============================================================================
# TEST SUITE
# =============================================================================

TESTS = [
    ScenarioTest(
        name="Exit Moving Van",
        save_state="Emerald-GBAdvance/truck_start.state",
        max_steps=10,  # Small room - should exit quickly if working
        success_fn=check_exit_moving_van,
        description="Agent should exit the moving van and successfully enter Brendan's house"
    ),
    
    # TODO: Add more tests as you create save states
    # 
    # ScenarioTest(
    #     name="Navigate Out of House",
    #     save_state="Emerald-GBAdvance/inside_house.state",
    #     max_steps=30,
    #     success_fn=check_exit_house,
    #     description="Agent should navigate from inside the house to outside in Littleroot Town"
    # ),
    #
    # ScenarioTest(
    #     name="Reach Route 101",
    #     save_state="Emerald-GBAdvance/littleroot_start.state",
    #     max_steps=100,
    #     success_fn=check_navigate_route_101,
    #     description="Agent should navigate from Littleroot Town to Route 101"
    # ),
]


# =============================================================================
# TEST RUNNER
# =============================================================================

def list_tests():
    """Display all available tests"""
    print("\n📋 Available Tests:")
    print("=" * 70)
    for i, test in enumerate(TESTS, 1):
        print(f"{i}. {test.name}")
        print(f"   📝 {test.description}")
        print(f"   📁 {test.save_state}")
        print(f"   🎯 Max steps: {test.max_steps}")
        print()


def run_tests(test_filter=None, verbose=False):
    """
    Run all tests or filtered tests
    
    Args:
        test_filter: String to filter test names (case-insensitive)
        verbose: Show detailed subprocess output
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Filter tests if requested
    tests_to_run = TESTS
    if test_filter:
        tests_to_run = [t for t in TESTS if test_filter.lower() in t.name.lower()]
        
        if not tests_to_run:
            print(f"❌ No tests found matching filter: '{test_filter}'")
            return False
        
        print(f"🔍 Running tests matching: '{test_filter}'")
    
    print(f"\n🧪 Running {len(tests_to_run)} test(s)...")
    
    # Run each test with different port to avoid conflicts
    results = []
    for i, test in enumerate(tests_to_run, 1):
        # Use different port for each test to avoid conflicts with any running servers
        port = 8001 + i
        passed = test.run(port=port, verbose=verbose)
        results.append((test.name, passed))
        
        # Brief pause between tests to ensure clean shutdown
        if i < len(tests_to_run):
            print("\n⏸️  Pausing 3 seconds before next test...")
            time.sleep(3)
    
    # Print summary
    print(f"\n{'='*70}")
    print("📊 TEST SUMMARY")
    print(f"{'='*70}")
    
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n🎯 Results: {passed_count}/{total} tests passed")
    
    if passed_count == total:
        print("✅ All tests passed! 🎉")
    else:
        print(f"❌ {total - passed_count} test(s) failed")
    
    print(f"{'='*70}\n")
    
    return passed_count == total


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Run scenario-based end-to-end tests for Pokemon Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/test_scenario_runner.py                  # Run all tests
  python tests/test_scenario_runner.py "exit van"       # Run tests matching "exit van"
  python tests/test_scenario_runner.py --list           # List all available tests
  python tests/test_scenario_runner.py -v               # Run with verbose output
        """
    )
    
    parser.add_argument(
        'filter',
        nargs='?',
        default=None,
        help='Filter tests by name (case-insensitive substring match)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available tests and exit'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed subprocess output (useful for debugging)'
    )
    
    args = parser.parse_args()
    
    # Handle --list
    if args.list:
        list_tests()
        return 0
    
    # Run tests
    success = run_tests(test_filter=args.filter, verbose=args.verbose)
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user")
        sys.exit(1)
