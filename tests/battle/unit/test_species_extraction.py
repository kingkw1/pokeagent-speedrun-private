#!/usr/bin/env python3
"""
Simple isolated test of species extraction logic.
"""

import re

# Test species fixing
def fix_species_name(species: str) -> str:
    corrections = {
        # Poochyena variants (most common errors)
        'POOHVENA': 'POOCHYENA',
        'POOCHIVIRA': 'POOCHYENA',
        'POOCHIWENA': 'POOCHYENA',
        'POOCHENNA': 'POOCHYENA',      # Missing Y
        'POOCHENA': 'POOCHYENA',       # Missing Y and I
        'POOCHEYNA': 'POOCHYENA',      # Transposed Y
        'ZIGZAAGOON': 'ZIGZAGOON',
    }
    species_upper = species.upper().strip()
    return corrections.get(species_upper, species_upper)

# Test extraction
def extract_species_from_dialogue(dialogue: str) -> str:
    dialogue_lower = dialogue.lower()
    
    # Pattern: "sent out POKEMON"
    if 'sent out' in dialogue_lower:
        try:
            after_sent = dialogue.lower().split('sent out')[1]
            species = after_sent.strip(' !.').upper()
            species_name = species.split()[0] if species.split() else 'Unknown'
            return fix_species_name(species_name)
        except:
            return 'Unknown'
    
    # Pattern: "Wild POKEMON appeared"
    if 'wild' in dialogue_lower and 'appeared' in dialogue_lower:
        try:
            parts = dialogue.lower().split('wild')[1].split('appeared')[0]
            species_name = parts.strip(' !.').upper()
            return fix_species_name(species_name)
        except:
            return 'Unknown'
    
    return 'Unknown'

# Test cases
test_dialogues = [
    ("YOUNGSTER CALVIN sent out POOCHYENA!", "POOCHYENA"),
    ("YOUNGESTER CALVIN sent out POOHVENA!", "POOCHYENA"),
    ("Wild ZIGZAGOON appeared!", "ZIGZAGOON"),
    ("Wild ZIGZAAGOON appeared!", "ZIGZAGOON"),
    ("Go! TREECKO!", "Unknown"),
    ("POOCHYENA used TACKLE!", "Unknown"),
]

print("=" * 70)
print("TESTING SPECIES EXTRACTION")
print("=" * 70)

all_pass = True
for dialogue, expected in test_dialogues:
    result = extract_species_from_dialogue(dialogue)
    status = "✅ PASS" if result == expected else "❌ FAIL"
    if result != expected:
        all_pass = False
    print(f"{status}: '{dialogue}'")
    print(f"   Expected: '{expected}', Got: '{result}'")

# Test type effectiveness lists
ABSORB_EFFECTIVE = {
    'ZIGZAGOON', 'WINGULL', 'POOCHYENA', 'LOTAD', 'NINCADA',
    'GEODUDE', 'NOSEPASS', 'RALTS', 'MAKUHITA', 'MEDITE',
    'MEDITITE', 'BARBOACH', 'WHISMUR', 'NUMEL',
}

ABSORB_NOT_EFFECTIVE = {
    'SHROOMISH', 'TAILLOW', 'WURMPLE', 'DUSTOX',
    'MASQUERAIN', 'SHEDINJA', 'TORCHIC',
}

def should_use_absorb(species: str) -> bool:
    if not species or species == 'Unknown':
        return False
    species_normalized = species.upper().strip()
    if species_normalized in ABSORB_NOT_EFFECTIVE:
        return False
    if species_normalized in ABSORB_EFFECTIVE:
        return True
    return False  # Unknown - default to Pound

print("\n" + "=" * 70)
print("TESTING TYPE EFFECTIVENESS")
print("=" * 70)

test_cases = [
    ("POOCHYENA", True),   # In EFFECTIVE list
    ("ZIGZAGOON", True),   # In EFFECTIVE list
    ("TAILLOW", False),    # In NOT_EFFECTIVE list
    ("SHROOMISH", False),  # In NOT_EFFECTIVE list
    ("Unknown", False),    # Default to Pound
    ("PIKACHU", False),    # Not in either list - default to Pound
]

for species, expected_absorb in test_cases:
    result = should_use_absorb(species)
    move = "ABSORB" if result else "POUND"
    expected_move = "ABSORB" if expected_absorb else "POUND"
    status = "✅ PASS" if result == expected_absorb else "❌ FAIL"
    if result != expected_absorb:
        all_pass = False
    print(f"{status}: '{species}' → {move} (expected {expected_move})")

print("\n" + "=" * 70)
if all_pass:
    print("✅ ALL TESTS PASSED")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 70)
