#!/usr/bin/env python3
"""
Simple standalone test: Can the VLM understand a text map and navigate correctly?

This tests if the VLM can analyze a simple ASCII map and determine the correct direction to move.
"""

from utils.vlm import VLM

print("=" * 80)
print("🧪 VLM MAP UNDERSTANDING TEST (Standalone)")
print("=" * 80)

# Initialize VLM
print("\n📡 Initializing VLM...")
vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")
print("✅ VLM initialized\n")

# Create test prompt with map
test_prompt = """You are helping navigate a Pokemon Emerald game.

Here is the current map of the MOVING_VAN interior:

--- MAP: MOVING_VAN ---
# # # # # # # # # # # # # # #
# # # # # # N # # # # # # # #
# # # # # # . . . S # # # # #
# # # # # # . P . S # # # # #
# # # # # # # # . S # # # # #
# # # # # # # # # # # # # # #

Legend:
  P = Player (you are here)
  S = Stairs/Warp (exit points)
  N = NPC (non-player character)
  . = Walkable path
  # = Wall/Blocked

QUESTION: What direction should the player move to reach the stairs/warp and exit the truck?

Look at where P is located and where the S tiles are located.
Provide a clear, step-by-step navigation plan using only these directions: UP, DOWN, LEFT, RIGHT.

RESPOND WITH: Your navigation plan in plain text."""

print("=" * 80)
print("📋 TEST SCENARIO:")
print("=" * 80)
print("Player (P) is inside a moving van and needs to exit via the stairs (S).")
print("The map shows the interior layout with walls (#), walkable paths (.), and stairs (S).")
print("\n" + "="*80)
print("❓ QUESTION ASKED TO VLM:")
print("=" * 80)
print("What direction should the player move to reach the stairs and exit?")
print("=" * 80)

# Query VLM
print("\n🔍 Calling VLM...")
response = vlm.get_text_query(test_prompt, module_name="NavigationTest")  # Text-only query

print("\n" + "=" * 80)
print("🤖 VLM RESPONSE:")
print("=" * 80)
print(response)
print("=" * 80)

# Analyze response
print("\n" + "=" * 80)
print("📊 ANALYSIS:")
print("=" * 80)

response_lower = response.lower()

mentions_right = 'right' in response_lower
mentions_down = 'down' in response_lower
mentions_up = 'up' in response_lower and not 'not up' in response_lower
mentions_left = 'left' in response_lower and not 'not left' in response_lower

print(f"\n✓ Mentions RIGHT: {'Yes' if mentions_right else 'No'}")
print(f"✓ Mentions DOWN: {'Yes' if mentions_down else 'No'}")
print(f"✗ Mentions UP: {'Yes ⚠️' if mentions_up else 'No'}")
print(f"✗ Mentions LEFT: {'Yes ⚠️' if mentions_left else 'No'}")

print("\n" + "=" * 80)
print("✅ CORRECT ANSWER:")
print("=" * 80)
print("Looking at the map:")
print("  - Player (P) is at row 4, column 8")
print("  - Stairs (S) are at column 10, rows 3-5")
print("\nCorrect navigation:")
print("  Step 1: Move RIGHT (from column 8 to column 9)")
print("  Step 2: Move RIGHT again (from column 9 to column 10)")
print("  Step 3: Player is now at the stairs/warp!")
print("\nAlternatively:")
print("  Step 1: Move DOWN one tile")
print("  Step 2: Move RIGHT twice")
print("  Step 3: Reach stairs!")
print("=" * 80)

# Verdict
print("\n" + "=" * 80)
print("🎯 VERDICT:")
print("=" * 80)

if mentions_right:
    print("✅ VLM correctly identified RIGHT as a necessary direction")
else:
    print("❌ VLM failed to identify RIGHT as necessary - this is critical for navigation!")

if mentions_up or mentions_left:
    print("⚠️  VLM mentioned incorrect directions (UP or LEFT) - these lead to walls/NPC")
else:
    print("✅ VLM did not suggest incorrect directions")

print("=" * 80)
