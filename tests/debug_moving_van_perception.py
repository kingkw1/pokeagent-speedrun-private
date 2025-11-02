#!/usr/bin/env python3
"""
Diagnostic: Check what VLM sees in the moving van state

This will help us understand if the VLM is mistakenly detecting
the cardboard boxes as dialogue boxes.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.vlm import VLM
from PIL import Image

print("="*80)
print("DIAGNOSTIC: VLM Perception in Moving Van")
print("="*80)

# Load screenshot from data directory (save one manually first)
screenshot_path = "data/screenshots/moving_van_test.png"
if not os.path.exists(screenshot_path):
    print(f"\n❌ Screenshot not found at: {screenshot_path}")
    print("\nPlease run the game manually and save a screenshot:")
    print("  1. python run.py --manual --load-state Emerald-GBAdvance/truck_start.state")
    print("  2. Press 'S' to save screenshot")
    print("  3. Move it to: data/screenshots/moving_van_test.png")
    print("  4. Re-run this diagnostic")
    sys.exit(1)

frame = Image.open(screenshot_path)

print("\n📸 Screenshot captured from moving van state")

# Initialize VLM (Qwen-2B)
vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")
print(f"🤖 VLM initialized: {vlm.model_name}\n")

# Test 1: The secondary dialogue check question
print("="*80)
print("TEST 1: Secondary Dialogue Check (What agent uses)")
print("="*80)
prompt1 = "Look at the bottom of the screen. Do you see a text box with dialogue? Answer YES or NO."
print(f"Prompt: {prompt1}")
response1 = vlm.get_query(frame, prompt1, "TEST")
print(f"Response: '{response1}'")
print()

# Test 2: More specific question about dialogue
print("="*80)
print("TEST 2: Ask about dialogue with character text")
print("="*80)
prompt2 = "Is there any character dialogue or speech text visible on screen? Answer YES or NO."
response2 = vlm.get_query(frame, prompt2, "TEST")
print(f"Prompt: {prompt2}")
print(f"Response: '{response2}'")
print()

# Test 3: Ask what the VLM sees
print("="*80)
print("TEST 3: What does VLM see on screen?")
print("="*80)
prompt3 = "Describe what you see on the screen in 2-3 sentences. What is the player doing?"
response3 = vlm.get_query(frame, prompt3, "TEST")
print(f"Prompt: {prompt3}")
print(f"Response: '{response3}'")
print()

# Test 4: Ask specifically about boxes
print("="*80)
print("TEST 4: Ask about boxes on screen")
print("="*80)
prompt4 = "Do you see any cardboard boxes or furniture on screen? Answer YES or NO."
response4 = vlm.get_query(frame, prompt4, "TEST")
print(f"Prompt: {prompt4}")
print(f"Response: '{response4}'")
print()

# Test 5: Better phrasing for dialogue detection
print("="*80)
print("TEST 5: Better dialogue prompt (with NPC context)")
print("="*80)
prompt5 = "Is there a white text box at the bottom of the screen showing dialogue from an NPC or character? Answer YES or NO."
response5 = vlm.get_query(frame, prompt5, "TEST")
print(f"Prompt: {prompt5}")
print(f"Response: '{response5}'")
print()

# Analysis
print("="*80)
print("ANALYSIS")
print("="*80)
print("\nCurrent prompt used by agent:")
print(f'  "{prompt1}"')
print(f"\nVLM Response: {response1}")
print()

if 'YES' in response1.upper():
    print("❌ PROBLEM DETECTED: VLM thinks there's a dialogue box when there isn't!")
    print("\nPossible causes:")
    print("  1. VLM confusing cardboard boxes with dialogue boxes")
    print("  2. Prompt ambiguity - 'text box' could mean many things")
    print("  3. VLM hallucinating or misinterpreting game state")
    print("\nRecommended fix:")
    print("  - Use more specific prompt like Test 5")
    print("  - Add 'NPC' or 'character speaking' context to prompt")
    print("  - Check for white text box specifically (most dialogue boxes are white)")
else:
    print("✅ GOOD: VLM correctly detected no dialogue box")
