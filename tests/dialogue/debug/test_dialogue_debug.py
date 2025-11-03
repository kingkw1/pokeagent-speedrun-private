#!/usr/bin/env python3
"""
Debug script to test dialogue advancement in dialog.state
"""
import sys
sys.path.insert(0, '.')

from pokemon_env.emulator import EmeraldEmulator
from utils.ocr_dialogue import create_ocr_detector
import time

def main():
    print("=== DIALOGUE DEBUG TEST ===\n")
    
    # Initialize emulator
    print("Initializing emulator...")
    env = EmeraldEmulator('Emerald-GBAdvance/rom.gba')
    env.initialize()
    
    # Load dialog state
    print("Loading dialog.state...")
    env.load_state('tests/save_states/dialog.state')
    env.tick(30)  # Let it settle
    
    # Get initial state
    state = env.get_comprehensive_state()
    print(f"\n=== INITIAL STATE ===")
    print(f"Game state: {state.get('game', {}).get('state', 'unknown')}")
    print(f"Position: {state.get('player', {}).get('position', {})}")
    print(f"Location: {state.get('player', {}).get('location', 'unknown')}")
    
    # Check OCR
    detector = create_ocr_detector()
    frame = env.get_screenshot()
    if frame:
        dialogue = detector.detect_dialogue_from_screenshot(frame)
        print(f"OCR Dialogue: '{dialogue}'")
        print(f"Dialogue detected: {bool(dialogue and dialogue.strip())}")
    
    # Press A and wait for text
    print(f"\n=== PRESSING A (1st time) ===")
    env.press_buttons(['a'], hold_frames=10, release_frames=10)
    env.tick(150)  # Wait for text to appear (2.5 seconds at 60 FPS)
    
    state2 = env.get_comprehensive_state()
    frame2 = env.get_screenshot()
    if frame2:
        dialogue2 = detector.detect_dialogue_from_screenshot(frame2)
        print(f"After 1st A:")
        print(f"  State: {state2.get('game', {}).get('state')}")
        print(f"  Position: {state2.get('player', {}).get('position', {})}")
        print(f"  Dialogue: '{dialogue2}'")
    
    # Press A again
    print(f"\n=== PRESSING A (2nd time) ===")
    env.press_buttons(['a'], hold_frames=10, release_frames=10)
    env.tick(150)
    
    state3 = env.get_comprehensive_state()
    frame3 = env.get_screenshot()
    if frame3:
        dialogue3 = detector.detect_dialogue_from_screenshot(frame3)
        print(f"After 2nd A:")
        print(f"  State: {state3.get('game', {}).get('state')}")
        print(f"  Position: {state3.get('player', {}).get('position', {})}")
        print(f"  Dialogue: '{dialogue3}'")
    
    # Try to move LEFT
    print(f"\n=== PRESSING LEFT ===")
    env.press_buttons(['left'], hold_frames=10, release_frames=10)
    env.tick(30)
    
    state4 = env.get_comprehensive_state()
    print(f"After LEFT:")
    print(f"  Position: {state4.get('player', {}).get('position', {})}")
    print(f"  State: {state4.get('game', {}).get('state')}")
    
    # Check if position changed
    initial_pos = state.get('player', {}).get('position', {})
    final_pos = state4.get('player', {}).get('position', {})
    
    print(f"\n=== RESULT ===")
    print(f"Initial position: {initial_pos}")
    print(f"Final position: {final_pos}")
    print(f"Position changed: {initial_pos != final_pos}")
    
    if initial_pos != final_pos:
        print("✅ SUCCESS: Dialogue completed and player moved!")
    else:
        print("❌ FAILURE: Player stuck at same position")
    
    env.close()

if __name__ == "__main__":
    main()
