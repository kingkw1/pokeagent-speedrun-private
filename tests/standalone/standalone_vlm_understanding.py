#!/usr/bin/env python3
"""
Simple test to verify VLM can understand the state and make correct navigation decisions.

This test presents the VLM with:
1. The game screenshot
2. The formatted LLM state view (map + legend)
3. A simple question about what to do next

We'll verify if the VLM can correctly identify that it needs to move RIGHT to reach the stairs.
"""

import sys
import requests
import base64
from PIL import Image
import io

# Initialize VLM
print("Initializing VLM...")
from utils.vlm import VLM
vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")

# Get current game state
SERVER_URL = "http://localhost:8000"

print("\n" + "="*80)
print("🧪 VLM UNDERSTANDING TEST")
print("="*80)

try:
    # Get screenshot and state
    print("\n📸 Fetching current game state from server...")
    response = requests.get(f"{SERVER_URL}/state", timeout=5)
    if response.status_code != 200:
        print(f"❌ Failed to get state: {response.status_code}")
        sys.exit(1)
    
    state_data = response.json()
    
    # Get screenshot
    screenshot_b64 = state_data.get('visual', {}).get('screenshot_base64')
    if not screenshot_b64:
        print("❌ No screenshot in state data")
        sys.exit(1)
    
    # Decode screenshot for display
    image_data = base64.b64decode(screenshot_b64)
    image = Image.open(io.BytesIO(image_data))
    
    print(f"✅ Got screenshot: {image.size}")
    
    # Format the state as the LLM would see it
    from utils.state_formatter import format_state_for_llm
    llm_view = format_state_for_llm(state_data, include_debug_info=False, include_npcs=True)
    
    print("\n" + "="*80)
    print("📊 STATE AS LLM SEES IT:")
    print("="*80)
    print(llm_view)
    print("="*80)
    
    # Create a simple test prompt
    test_prompt = """You are looking at a Pokemon Emerald game screen.

Here is the current game state:

""" + llm_view + """

QUESTION: Looking at the map above, what direction(s) should the player (P) move to reach the stairs/warp (S) and exit the truck?

Analyze the map carefully:
- Player is at position (2, 2) marked with 'P'
- Stairs/warp tiles are marked with 'S'
- Find the shortest path from P to S

RESPOND WITH: A simple answer stating which direction(s) to move (UP, DOWN, LEFT, or RIGHT) and why.
"""

    print("\n" + "="*80)
    print("❓ TEST QUESTION:")
    print("="*80)
    print("What direction(s) should the player move to reach the stairs and exit?")
    print("="*80)
    
    # Call VLM
    print("\n🔍 Calling VLM for analysis...")
    
    # Use the VLM query method directly
    response = vlm.query(test_prompt, image)
    
    print("\n" + "="*80)
    print("🤖 VLM RESPONSE:")
    print("="*80)
    print(response)
    print("="*80)
    
    # Analyze the response
    print("\n" + "="*80)
    print("📊 ANALYSIS:")
    print("="*80)
    
    response_lower = response.lower()
    
    correct_mentions_right = 'right' in response_lower
    correct_mentions_down = 'down' in response_lower
    incorrect_mentions_up = 'up' in response_lower
    incorrect_mentions_left = 'left' in response_lower
    
    if correct_mentions_right and correct_mentions_down:
        print("✅ CORRECT: VLM identified both RIGHT and DOWN as needed directions")
    elif correct_mentions_right:
        print("🟡 PARTIAL: VLM identified RIGHT (correct) but may have missed DOWN")
    elif correct_mentions_down:
        print("🟡 PARTIAL: VLM identified DOWN (correct) but may have missed RIGHT")
    else:
        print("❌ INCORRECT: VLM did not identify the correct directions")
    
    if incorrect_mentions_up:
        print("⚠️  VLM incorrectly mentioned UP")
    if incorrect_mentions_left:
        print("⚠️  VLM incorrectly mentioned LEFT")
    
    print("\n" + "="*80)
    print("📝 EXPECTED ANSWER:")
    print("="*80)
    print("The player (P) at position (2,2) should move:")
    print("  1. RIGHT to position (3,2) - moves toward stairs column")
    print("  2. DOWN to position (3,3) or (3,4) - reaches the stairs (S)")
    print("\nThe stairs/warp (S) are located at positions along the right side.")
    print("="*80)
    
except requests.exceptions.ConnectionError:
    print("\n❌ ERROR: Could not connect to server at http://localhost:8000")
    print("Please start the server first with:")
    print("  python run.py --load-state Emerald-GBAdvance/truck_start.state")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
