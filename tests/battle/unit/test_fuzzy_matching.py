#!/usr/bin/env python3
"""
Test fuzzy string matching for Pokemon species names.
"""

from difflib import get_close_matches

# Known Pokemon species
ABSORB_EFFECTIVE = {
    'ZIGZAGOON', 'WINGULL', 'POOCHYENA', 'LOTAD', 'NINCADA',
    'GEODUDE', 'NOSEPASS', 'RALTS', 'MAKUHITA', 'MEDITE',
    'MEDITITE', 'BARBOACH', 'WHISMUR', 'NUMEL',
}

ABSORB_NOT_EFFECTIVE = {
    'SHROOMISH', 'TAILLOW', 'WURMPLE', 'DUSTOX',
    'MASQUERAIN', 'SHEDINJA', 'TORCHIC',
}

def fix_species_name(species: str) -> str:
    """Fix species name using fuzzy matching."""
    species_upper = species.upper().strip()
    
    # Combine all known Pokemon
    all_known_species = list(ABSORB_EFFECTIVE | ABSORB_NOT_EFFECTIVE)
    
    # Find closest match (cutoff=0.6 means 60% similarity)
    matches = get_close_matches(species_upper, all_known_species, n=1, cutoff=0.6)
    
    if matches:
        return matches[0]
    
    # No match found
    return species_upper

# Test cases - all the variants we've seen
test_cases = [
    # Poochyena variants
    ("POOCHENNA", "POOCHYENA"),      # Missing Y
    ("POOCHENA", "POOCHYENA"),       # Missing Y and I  
    ("POOHVENA", "POOCHYENA"),       # Missing C, I
    ("POOCHIVIRA", "POOCHYENA"),     # I→V, E→I, NA→RA
    ("POOCHIWENA", "POOCHYENA"),     # Y→W
    ("POOCHEYNA", "POOCHYENA"),      # Transposed Y
    ("POOOCHYENA", "POOCHYENA"),     # Extra O
    ("POCHYENA", "POOCHYENA"),       # Missing O
    ("POOCHYENA", "POOCHYENA"),      # Correct
    
    # Zigzagoon variants
    ("ZIGZAAGOON", "ZIGZAGOON"),     # Extra A
    ("ZIGZAGOO", "ZIGZAGOON"),       # Missing N
    ("ZIGZAGOON", "ZIGZAGOON"),      # Correct
    
    # Taillow variants
    ("TAILLO", "TAILLOW"),           # Missing W
    ("TAILLLOW", "TAILLOW"),         # Extra L
    ("TAILOW", "TAILLOW"),           # Missing L
    
    # Other species
    ("SHROOMISH", "SHROOMISH"),      # Correct
    ("WURMPLE", "WURMPLE"),          # Correct
    ("GEODUDE", "GEODUDE"),          # Correct
    ("RALTSS", "RALTS"),             # Extra S
    ("MEDITE", "MEDITITE"),          # Missing I, T (might not match due to length)
]

print("=" * 70)
print("TESTING FUZZY SPECIES MATCHING")
print("=" * 70)

all_pass = True
for input_name, expected_name in test_cases:
    result = fix_species_name(input_name)
    status = "✅ PASS" if result == expected_name else "❌ FAIL"
    
    if result != expected_name:
        all_pass = False
        print(f"{status}: '{input_name}' → '{result}' (expected '{expected_name}')")
    else:
        print(f"{status}: '{input_name}' → '{result}'")

print("\n" + "=" * 70)
if all_pass:
    print("✅ ALL TESTS PASSED")
else:
    print("❌ SOME TESTS FAILED - but fuzzy matching is best-effort")
    print("   Adjust cutoff parameter if needed (currently 0.6)")
print("=" * 70)

# Show some similarity scores for debugging
print("\n" + "=" * 70)
print("SIMILARITY ANALYSIS")
print("=" * 70)

from difflib import SequenceMatcher

interesting_cases = [
    ("POOCHENNA", "POOCHYENA"),
    ("POOHVENA", "POOCHYENA"),
    ("MEDITE", "MEDITITE"),
]

for misspell, correct in interesting_cases:
    ratio = SequenceMatcher(None, misspell, correct).ratio()
    print(f"'{misspell}' vs '{correct}': {ratio:.2%} similar")
