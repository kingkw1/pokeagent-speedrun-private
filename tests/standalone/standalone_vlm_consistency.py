"""
Test: Does the VLM give consistent responses when called multiple times?
"""

import sys
sys.path.insert(0, '/home/kevin/Documents/pokeagent-speedrun')

from utils.vlm import VLM

# Load the model
print("Loading VLM...")
vlm = VLM(model_name="Qwen/Qwen2-VL-2B-Instruct", backend="local")
print("✅ VLM loaded!\n")

# Test the EXACT prompt that works standalone but fails in agent
prompt = """You are playing Pokemon Emerald. Follow the instructions exactly and respond with only the requested button name.
Navigate to Oldale Town (NORTH).

Position: (10, 15)
Goal: Oldale Town is NORTH. Choose the option that moves NORTH (look for UP).

Options:
1. UP - ( 10, 14) [.] WALKABLE
2. DOWN - ( 10, 16) [.] WALKABLE
3. LEFT - (  9, 15) [.] WALKABLE
4. RIGHT - ( 11, 15) [.] WALKABLE

Which number moves NORTH/UP? Answer with just the number:"""

print("Testing the same prompt 5 times in a row...\n")
for i in range(5):
    print(f"{'='*60}")
    print(f"CALL #{i+1}")
    print(f"{'='*60}")
    response = vlm.get_text_query(prompt, "test")
    print(f"RESPONSE: '{response}'")
    print()

print("\n" + "="*60)
print("ANALYSIS:")
print("If all responses are '1' or '2' (the correct answer), VLM is fine.")
print("If responses vary wildly, there may be a temperature/sampling issue.")
print("="*60)
