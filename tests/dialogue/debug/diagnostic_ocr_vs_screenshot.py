#!/usr/bin/env python3
"""
Diagnostic: Check OCR detection on dialog2.state screenshot
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pokemon_env.emulator import EmeraldEmulator
from utils.ocr_dialogue import create_ocr_detector

print("="*80)
print("Diagnostic: OCR on dialog2.state")
print("="*80)

# Initialize
env = EmeraldEmulator('Emerald-GBAdvance/rom.gba', headless=False)  # Show display
env.initialize()
env.load_state('tests/save_states/dialog2.state')
env.tick(60)

# Save screenshot
screenshot = env.get_screenshot()
screenshot.save('tests/dialogue/debug/dialog2_screenshot.png')
print(f"\n💾 Saved screenshot to tests/dialogue/debug/dialog2_screenshot.png")

# Try OCR
detector = create_ocr_detector()
dialogue_text = detector.detect_dialogue_from_screenshot(screenshot)

print(f"\n📊 Results:")
print(f"   OCR detected: {dialogue_text is not None}")
if dialogue_text:
    print(f"   Text: '{dialogue_text}'")
    print(f"   Length: {len(dialogue_text)}")
else:
    print(f"   Text: None")

# Check if dialogue_box is detected
has_box = detector.has_dialogue_box(screenshot)
print(f"   Has dialogue box (pixel detection): {has_box}")

print(f"\n✅ Check the screenshot manually to see what OCR sees")
