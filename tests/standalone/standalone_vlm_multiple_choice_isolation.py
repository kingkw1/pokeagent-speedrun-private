"""
Bare bones test: Can the VLM choose from a numbered list?
Progressive complexity to identify the exact failure point.
"""

import sys
sys.path.insert(0, '/home/kevin/Documents/pokeagent-speedrun')

from utils.vlm import VLM

# Load the model using the same code as the agent
print("Loading VLM (this may take a moment)...")
vlm = VLM(model_name="Qwen/Qwen2-VL-2B-Instruct", backend="local")
print("✅ VLM loaded!\n")

def test_vlm(prompt: str, test_name: str):
    """Test the VLM with a given prompt."""
    print(f"{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"PROMPT:\n{prompt}")
    print(f"{'-'*60}")
    
    response = vlm.get_text_query(prompt, "test")
    
    print(f"RESPONSE: '{response}'")
    print()
    return response


# TEST 1: Absolute simplest - just pick a number
test_vlm(
    prompt="Pick a number: 1, 2, or 3. Answer with just the number:",
    test_name="TEST 1: Pick any number"
)

# TEST 2: Pick the second number
test_vlm(
    prompt="Choose the SECOND number: 1, 2, or 3. Answer with just the number:",
    test_name="TEST 2: Pick second number"
)

# TEST 3: Simple word matching
test_vlm(
    prompt="""Which number has APPLE?
1. BANANA
2. APPLE
3. ORANGE

Answer with just the number:""",
    test_name="TEST 3: Simple word matching"
)

# TEST 4: Direction matching (no context)
test_vlm(
    prompt="""Which number is UP?
1. UP
2. DOWN
3. LEFT

Answer with just the number:""",
    test_name="TEST 4: Find UP in list"
)

# TEST 5: Direction with instruction
test_vlm(
    prompt="""Find UP in this list:
1. DOWN
2. LEFT
3. UP

Answer with just the number:""",
    test_name="TEST 5: Find UP (not first option)"
)

# TEST 6: Match direction to goal
test_vlm(
    prompt="""Goal: Go NORTH.
Which option moves NORTH?
1. DOWN
2. UP
3. LEFT

Answer with just the number:""",
    test_name="TEST 6: Match UP to NORTH"
)

# TEST 7: With coordinates (like real prompt)
test_vlm(
    prompt="""Navigate NORTH.

Options:
1. DOWN - ( 10, 15) WALKABLE
2. UP - ( 10, 14) WALKABLE
3. LEFT - (  9, 15) WALKABLE

Which number moves NORTH? Answer with just the number:""",
    test_name="TEST 7: With coordinates"
)

# TEST 8: Exact real prompt format
test_vlm(
    prompt="""Navigate to Oldale Town (NORTH).

Position: (10, 15)
Goal: Oldale Town is NORTH. Choose the option that moves NORTH (look for UP).

Options:
1. DOWN - ( 10, 16) [.] WALKABLE
2. UP - ( 10, 14) [.] WALKABLE
3. LEFT - (  9, 15) [.] WALKABLE
4. RIGHT - ( 11, 15) [.] WALKABLE

Which number moves NORTH/UP? Answer with just the number:""",
    test_name="TEST 8: Exact real prompt"
)

print(f"\n{'='*60}")
print("ANALYSIS:")
print("If VLM always says '1', the model is too simple.")
print("If it works on simple tests but fails on complex ones,")
print("we can identify where the prompt becomes confusing.")
print(f"{'='*60}")
