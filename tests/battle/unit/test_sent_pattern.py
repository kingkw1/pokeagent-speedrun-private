#!/usr/bin/env python3
"""
Quick test for the new 'sent' pattern matching.
"""

# Test cases
test_cases = [
    "YOUNGSTER CALVIN sent out POOCHYENA!",     # Standard pattern
    "YOUNGESTER CALVIN sent POOCHYVA!",         # VLM dropping "out"
    "YOUNGSTER CALVIN sent POOCHENNA!",         # Another variant
    "Lass CASEY sent out ZIGZAGOON!",           # Different trainer
    "Lass CASEY sent ZIGZAAGOON!",              # Different trainer, no "out"
    "Player sent something",                    # Should NOT match (not a trainer)
]

print("=" * 80)
print("Testing 'sent' pattern matching")
print("=" * 80)

for dialogue in test_cases:
    dialogue_lower = dialogue.lower()
    
    # Check Pattern 1: "sent out"
    if 'sent out' in dialogue_lower:
        after_sent = dialogue.lower().split('sent out')[1]
        species = after_sent.strip(' !.').upper()
        species_name = species.split()[0] if species.split() else 'Unknown'
        print(f"✅ PATTERN 1 (sent out): '{dialogue[:40]}...' → {species_name}")
    
    # Check Pattern 2: "sent" (without "out")
    elif ' sent ' in dialogue_lower and 'sent out' not in dialogue_lower:
        # Trainer validation
        if any(trainer in dialogue_lower for trainer in ['youngster', 'lass', 'bug catcher', 'school kid', 'calvin', 'casey']):
            after_sent = dialogue.lower().split(' sent ')[1]
            species = after_sent.strip(' !.').upper()
            species_name = species.split()[0] if species.split() else 'Unknown'
            print(f"✅ PATTERN 2 (sent): '{dialogue[:40]}...' → {species_name}")
        else:
            print(f"⚠️  REJECTED (not trainer): '{dialogue[:40]}...'")
    else:
        print(f"❌ NO MATCH: '{dialogue[:40]}...'")

print("=" * 80)
