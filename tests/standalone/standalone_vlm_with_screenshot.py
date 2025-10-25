#!/usr/bin/env python3
"""
Test: Can VLM navigate using BOTH the screenshot AND movement preview?

This is the key test - can the VLM make correct decisions when given:
1. The actual game screenshot (visual)
2. Movement preview showing what each direction leads to

This matches what the agent actually receives during gameplay.
"""

import sys
import os
from PIL import Image

# Load a test screenshot from the moving van
screenshot_path = "screenshots/moving_van_test.png"

# If screenshot doesn't exist, create instructions for manual test
if not os.path.exists(screenshot_path):
    print("=" * 80)
    print("📸 SCREENSHOT NEEDED")
    print("=" * 80)
    print("\nTo run this test, we need a screenshot from inside the moving van.")
    print("\nSteps:")
    print("  1. Start the game: python run.py --load-state Emerald-GBAdvance/truck_start.state")
    print("  2. Take a screenshot and save it to: screenshots/moving_van_test.png")
    print("  3. Run this test again")
    print("\n" + "=" * 80)
    sys.exit(0)

# Initialize VLM
print("=" * 80)
print("🧪 VLM NAVIGATION TEST (Screenshot + Movement Preview)")
print("=" * 80)

from utils.vlm import VLM
print("\n📡 Initializing VLM...")
vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")
print("✅ VLM initialized\n")

# Load screenshot
image = Image.open(screenshot_path)
print(f"✅ Loaded screenshot: {image.size}\n")

# Create prompt with movement preview (simulating what agent sees)
test_prompt = """You are playing Pokemon Emerald. You are inside a MOVING_VAN and need to exit.

Current Position: (2, 2)

MOVEMENT PREVIEW:
  UP   : (  2,  1) [.] WALKABLE
  DOWN : (  2,  3) [#] BLOCKED - Impassable
  LEFT : (  1,  2) [.] WALKABLE  
  RIGHT: (  3,  2) [.] WALKABLE

Your goal: Exit the truck by reaching the stairs/warp.

QUESTION: Based on the screenshot and movement preview, which direction should you move?

Think step-by-step:
1. Look at the screenshot - where are the stairs/exit?
2. Check the movement preview - which directions are WALKABLE?
3. Choose the direction that moves you toward the exit

RESPOND WITH: Only one direction (UP, DOWN, LEFT, or RIGHT) that moves you toward the exit."""

print("=" * 80)
print("📋 TEST PROMPT:")
print("=" * 80)
print(test_prompt)
print("=" * 80)

# Query VLM with image
print("\n🔍 Calling VLM with screenshot + movement preview...")
response = vlm.get_query(image, test_prompt, module_name="NavigationTest")

print("\n" + "=" * 80)
print("🤖 VLM RESPONSE:")
print("=" * 80)
print(response)
print("=" * 80)

# Analyze
print("\n" + "=" * 80)
print("📊 ANALYSIS:")
print("=" * 80)

response_lower = response.lower()
print(f"\nResponse mentions:")
print(f"  RIGHT: {'✅ Yes' if 'right' in response_lower else '❌ No'}")
print(f"  DOWN: {'⚠️ Yes' if 'down' in response_lower else '✅ No (correct - DOWN is blocked)'}")
print(f"  LEFT: {'⚠️ Yes' if 'left' in response_lower else '✅ No'}")
print(f"  UP: {'⚠️ Yes' if 'up' in response_lower and 'not up' not in response_lower else '✅ No'}")

print("\n" + "=" * 80)
print("✅ CORRECT ANSWER: RIGHT")
print("=" * 80)
print("The player needs to move RIGHT to approach the stairs on the right side of the truck.")
print("=" * 80)
