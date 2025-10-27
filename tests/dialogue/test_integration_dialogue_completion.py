#!/usr/bin/env python3
"""
Integration test: Dialogue completion mechanics

Tests the dialogue clearing mechanism:
1. Dialogue detection (in_dialog flag)
2. A-press sequence advances/dismisses dialogue
3. Movement becomes enabled after dialogue clears
4. State transitions correctly

This consolidates functionality from:
- test_dialogue_completion.py
- test_dialogue_completion_live.py
- test_clearing_sequence.py
- test_scripted_dialogue_simple.py
"""

import pytest
import subprocess
import time
import requests


class TestDialogueCompletion:
    """Integration tests for dialogue completion mechanics"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test"""
        subprocess.run(["pkill", "-f", "server.app"], capture_output=True)
        time.sleep(1)
        yield
        subprocess.run(["pkill", "-f", "server.app"], capture_output=True)
        time.sleep(0.5)
    
    def test_dialogue_clears_with_a_presses(self):
        """
        Test that pressing A clears dialogue.
        
        Success criteria:
        - Initial: in_dialog=True
        - After 2-3 A presses: in_dialog=False
        - movement_enabled becomes True
        """
        print("\n" + "="*80)
        print("TEST: A-Press Dialogue Clearing")
        print("="*80)
        
        server_proc = subprocess.Popen([
            "python", "-m", "server.app",
            "--load-state", "tests/states/dialog.state",
            "--port", "8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            print("⏳ Starting server...")
            time.sleep(5)
            
            # Get initial state
            resp = requests.get("http://localhost:8000/state", timeout=3)
            initial_state = resp.json()
            
            print(f"\n📊 Initial State:")
            print(f"   in_dialog: {initial_state['game'].get('in_dialog')}")
            print(f"   movement_enabled: {initial_state['game'].get('movement_enabled')}")
            print(f"   position: ({initial_state['player']['position']['x']}, "
                  f"{initial_state['player']['position']['y']})")
            
            # Press A to clear dialogue
            for i in range(3):
                print(f"\n🎮 Pressing A (attempt {i+1})...")
                requests.post("http://localhost:8000/action",
                            json={"buttons": ["A"]}, timeout=3)
                time.sleep(2)
                
                resp = requests.get("http://localhost:8000/state", timeout=3)
                state = resp.json()
                in_dialog = state['game'].get('in_dialog', False)
                movement_enabled = state['game'].get('movement_enabled', True)
                
                print(f"   in_dialog: {in_dialog}, movement_enabled: {movement_enabled}")
                
                if not in_dialog:
                    print(f"\n✅ Dialogue cleared after {i+1} A presses!")
                    assert movement_enabled, "Movement should be enabled when dialogue clears"
                    return
            
            # If we get here, dialogue didn't clear
            pytest.fail("Dialogue should clear within 3 A presses")
            
        finally:
            server_proc.terminate()
            server_proc.wait(timeout=2)
    
    def test_movement_after_dialogue_clearing(self):
        """
        Test that player can move after dialogue is cleared.
        
        Success criteria:
        - Clear dialogue with A presses
        - Movement command succeeds
        - Position changes OR movement_enabled=True
        """
        print("\n" + "="*80)
        print("TEST: Movement After Dialogue Clears")
        print("="*80)
        
        server_proc = subprocess.Popen([
            "python", "-m", "server.app",
            "--load-state", "tests/states/dialog.state",
            "--port", "8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            time.sleep(5)
            
            # Get initial position
            resp = requests.get("http://localhost:8000/state", timeout=3)
            initial_state = resp.json()
            initial_pos = (initial_state['player']['position']['x'],
                          initial_state['player']['position']['y'])
            
            print(f"📍 Initial position: {initial_pos}")
            
            # Clear dialogue
            print("\n🎮 Clearing dialogue with A presses...")
            for i in range(3):
                requests.post("http://localhost:8000/action",
                            json={"buttons": ["A"]}, timeout=3)
                time.sleep(2)
            
            # Try movement
            print("\n🎮 Attempting movement (LEFT)...")
            requests.post("http://localhost:8000/action",
                        json={"buttons": ["LEFT"]}, timeout=3)
            time.sleep(2)
            
            # Check result
            resp = requests.get("http://localhost:8000/state", timeout=3)
            final_state = resp.json()
            final_pos = (final_state['player']['position']['x'],
                        final_state['player']['position']['y'])
            movement_enabled = final_state['game'].get('movement_enabled', True)
            
            print(f"📍 Final position: {final_pos}")
            print(f"✓ Movement enabled: {movement_enabled}")
            
            # Movement should be enabled (position may not change due to walls)
            assert movement_enabled, "Movement should be enabled after dialogue clears"
            
            if final_pos != initial_pos:
                print(f"✅ Position changed: {initial_pos} → {final_pos}")
            else:
                print(f"⚠️  Position unchanged (may be blocked by collision)")
            
        finally:
            server_proc.terminate()
            server_proc.wait(timeout=2)
    
    def test_state_transitions_correctly(self):
        """
        Test that dialogue state transitions are consistent.
        
        Success criteria:
        - in_dialog and movement_enabled are inverse
        - input_blocked matches in_dialog
        - game_state reflects primary state
        """
        print("\n" + "="*80)
        print("TEST: State Transition Consistency")
        print("="*80)
        
        server_proc = subprocess.Popen([
            "python", "-m", "server.app",
            "--load-state", "tests/states/dialog.state",
            "--port", "8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            time.sleep(5)
            
            # Check initial state consistency
            resp = requests.get("http://localhost:8000/state", timeout=3)
            state = resp.json()['game']
            
            print("\n📊 Initial State:")
            print(f"   in_dialog: {state.get('in_dialog')}")
            print(f"   movement_enabled: {state.get('movement_enabled')}")
            print(f"   input_blocked: {state.get('input_blocked')}")
            print(f"   game_state: {state.get('game_state')}")
            
            # Validate consistency
            if state.get('in_dialog'):
                assert not state.get('movement_enabled', True), \
                    "movement_enabled should be False when in_dialog is True"
                assert state.get('input_blocked', False), \
                    "input_blocked should be True when in_dialog is True"
            
            # Press A to clear dialogue
            print("\n🎮 Clearing dialogue...")
            for i in range(3):
                requests.post("http://localhost:8000/action",
                            json={"buttons": ["A"]}, timeout=3)
                time.sleep(2)
            
            # Check state after clearing
            resp = requests.get("http://localhost:8000/state", timeout=3)
            state = resp.json()['game']
            
            print("\n📊 After Clearing:")
            print(f"   in_dialog: {state.get('in_dialog')}")
            print(f"   movement_enabled: {state.get('movement_enabled')}")
            print(f"   input_blocked: {state.get('input_blocked')}")
            print(f"   game_state: {state.get('game_state')}")
            
            # Validate cleared state
            if not state.get('in_dialog', True):
                assert state.get('movement_enabled', False), \
                    "movement_enabled should be True when in_dialog is False"
                assert not state.get('input_blocked', True), \
                    "input_blocked should be False when in_dialog is False"
                print("\n✅ State transitions are consistent!")
            
        finally:
            server_proc.terminate()
            server_proc.wait(timeout=2)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
