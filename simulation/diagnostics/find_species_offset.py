import stable_retro as retro
import json
import struct

def fix_species():
    # 1. Load the working anchors from data.json
    with open('simulation/data/PokemonEmerald-GBA/data.json', 'r') as f:
        data = json.load(f)

    # We know 'move_1' is correct (Address ends in ...90 based on previous logs)
    move_1_addr = data['info']['move_1']['address']
    
    print(f"ANCHOR: Move 1 Address is {move_1_addr}")
    
    # 2. Load Env
    env = retro.make(game='PokemonEmerald-GBA', state='BattleLevel5')
    env.reset()
    
    WRAM_START = 0x02000000
    try:
        wram = env.data.memory.blocks[WRAM_START]
    except KeyError:
        print("Error: WRAM not found.")
        return

    # 3. Scan nearby for the Species ID
    # We expect Torchic (255) to be roughly -12 bytes from Move 1.
    # Let's check the 30 bytes BEFORE Move 1.
    
    start_scan = (move_1_addr - WRAM_START) - 30
    end_scan   = (move_1_addr - WRAM_START) + 10
    
    print("\n--- SCANNING FOR TORCHIC (255) NEAR MOVE 1 ---")
    print(f"{'OFFSET':<10} | {'VAL':<5} | {'NOTE'}")
    print("-" * 45)

    found_offset = None

    for i in range(start_scan, end_scan, 2):
        global_addr = WRAM_START + i
        val = struct.unpack('<H', wram[i:i+2])[0]
        
        rel_dist = i - (move_1_addr - WRAM_START)
        
        note = ""
        if global_addr == move_1_addr:
            note = "<-- MOVE 1 (Scratch)"
        elif val == 255:
            note = "✅ TORCHIC FOUND!"
            found_offset = rel_dist # Expected to be -12, might be different
        elif val == 280:
            note = "⚠️ The 'Wrong' Value (280)"
            
        print(f"{rel_dist:<10} | {val:<5} | {note}")

    if found_offset is not None:
        print(f"\n🎉 SOLUTION FOUND: Species is at Move1 {found_offset} bytes")
        
        # CALCULATE NEW SPECIES ADDRESSES
        # Player Species = Player Move 1 + Offset
        # Enemy Species  = Enemy Move 1 + Offset (Assuming symmetry)
        
        # We need to update data.json
        print("Updating data.json automatically...")
        
        # Get current Move 1 addresses
        p_m1 = data['info']['move_1']['address']
        e_m1 = data['info']['enemy_species']['address'] + 12 # Reverse eng from previous assume
        # Actually, let's just grab the Enemy Anchor from the file if possible, 
        # but we might have calculated it wrong previously. 
        # Let's rely on the Player calc and apply the same logic to Enemy.
        
        # Update Player
        data['info']['my_species']['address'] = p_m1 + found_offset
        
        # Update Enemy (We assume the same structure)
        # We previously set Enemy Species at EnemyBase + 0.
        # We need to find Enemy Move 1 to apply the offset, OR just apply the difference.
        # Current Enemy Species is at EnemyBase + 0. 
        # If the offset is indeed different, we adjust it.
        # Let's assume the previous Base calc was "Move 1 - 12".
        # If found_offset is different, we adjust by (found_offset - (-12)).
        
        # Safer: Just re-calculate from the HP anchor using the new confirmed structure
        # If Species is at Move1 + X. 
        # And Move1 is at HP - 28.
        # Then Species is at HP - 28 + X.
        
        # Let's just patch the species entry directly based on the Move 1 anchor we trust.
        new_species_addr = p_m1 + found_offset
        data['info']['my_species']['address'] = new_species_addr
        
        # Enemy Adjustment
        # We need to find the Enemy Move 1 address to do this perfectly, 
        # but we can infer it from the Enemy HP address we trust (33702148).
        # Enemy Move 1 = Enemy HP - 28
        e_m1_inferred = 33702148 - 28
        data['info']['enemy_species']['address'] = e_m1_inferred + found_offset
        
        with open('simulation/data/PokemonEmerald-GBA/data.json', 'w') as f:
            json.dump(data, f, indent=4)
        print("✅ Fixed data.json!")
        
    else:
        print("\n❌ Torchic not found in the immediate vicinity.")

if __name__ == "__main__":
    fix_species()