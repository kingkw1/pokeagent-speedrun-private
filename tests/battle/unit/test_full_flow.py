#!/usr/bin/env python3
"""
Comprehensive test showing the full flow:
VLM misspelling → Fuzzy matching → Type effectiveness → Move selection
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
    all_known_species = list(ABSORB_EFFECTIVE | ABSORB_NOT_EFFECTIVE)
    matches = get_close_matches(species_upper, all_known_species, n=1, cutoff=0.6)
    
    if matches:
        if matches[0] != species_upper:
            print(f"   🔧 Fuzzy matched: '{species_upper}' → '{matches[0]}'")
        return matches[0]
    
    print(f"   ⚠️ No match found for '{species_upper}'")
    return species_upper

def should_use_absorb(species: str) -> bool:
    """Determine move based on type effectiveness."""
    if not species or species == 'Unknown':
        return False
    
    species_normalized = species.upper().strip()
    
    if species_normalized in ABSORB_NOT_EFFECTIVE:
        return False
    
    if species_normalized in ABSORB_EFFECTIVE:
        return True
    
    return False  # Unknown - default to Pound

# Simulate full battle flow
test_battles = [
    # (VLM_OUTPUT, EXPECTED_SPECIES, EXPECTED_MOVE)
    ("YOUNGSTER CALVIN sent out POOCHENNA!", "POOCHYENA", "ABSORB"),
    ("YOUNGSTER CALVIN sent out POOHVENA!", "POOCHYENA", "ABSORB"),
    ("Wild ZIGZAAGOON appeared!", "ZIGZAGOON", "ABSORB"),
    ("Wild TAILLO appeared!", "TAILLOW", "POUND"),
    ("LASS sent out SHROOMISH!", "SHROOMISH", "POUND"),
    ("Wild GEODUDE appeared!", "GEODUDE", "ABSORB"),
]

print("=" * 80)
print("FULL BATTLE FLOW SIMULATION")
print("=" * 80)

for dialogue, expected_species, expected_move in test_battles:
    print(f"\n📝 VLM says: '{dialogue}'")
    
    # Extract species from dialogue
    if 'sent out' in dialogue.lower():
        raw_species = dialogue.lower().split('sent out')[1].strip(' !.').upper().split()[0]
    elif 'wild' in dialogue.lower():
        raw_species = dialogue.lower().split('wild')[1].split('appeared')[0].strip(' !.').upper()
    else:
        raw_species = 'Unknown'
    
    print(f"   📤 Extracted: '{raw_species}'")
    
    # Fix spelling
    corrected_species = fix_species_name(raw_species)
    print(f"   ✅ Corrected: '{corrected_species}'")
    
    # Determine move
    use_absorb = should_use_absorb(corrected_species)
    move = "ABSORB" if use_absorb else "POUND"
    
    # Check results
    species_match = corrected_species == expected_species
    move_match = move == expected_move
    
    if species_match and move_match:
        print(f"   ✅ PASS: Species={corrected_species}, Move={move}")
    else:
        print(f"   ❌ FAIL: Got ({corrected_species}, {move}), Expected ({expected_species}, {expected_move})")

print("\n" + "=" * 80)
print("✅ SIMULATION COMPLETE")
print("=" * 80)
