import stable_retro as retro
import sys
import os
import time

# Ensure we can import from local folder
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from pokedex import MOVES_DATA, SPECIES_DATA, get_effectiveness, TYPE_MAP

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
STATE_FILE = 'torchic/seedot'  # Name of your .state file (must be in retro data folder)
GAME_ID = 'PokemonEmerald-GBA'
# ------------------------------------------------------------------

def main():
    print(f"--- TYPE EFFECTIVENESS DEBUGGER ---")
    print(f"Loading State: {STATE_FILE}...\n")
    
    try:
        env = retro.make(game=GAME_ID, state=STATE_FILE)
    except FileNotFoundError:
        print(f"❌ Error: State '{STATE_FILE}' not found.")
        print("Make sure the .state file is in your stable-retro data directory.")
        return

    obs = env.reset()
    data = env.data

    # 1. IDENTIFY ENEMY
    enemy_id = data.lookup_value('enemy_species') or 0
    enemy_info = SPECIES_DATA.get(enemy_id)
    
    if not enemy_info:
        print(f"❌ Enemy Species ID {enemy_id} not found in Pokedex!")
        return

    enemy_name = enemy_info['name']
    t1 = enemy_info['types'][0]
    t2 = enemy_info['types'][1]
    
    t1_name = TYPE_MAP.get(t1, "None")
    t2_name = TYPE_MAP.get(t2, "None") if t2 is not None else "None"
    
    print(f"ENEMY: {enemy_name} (ID: {enemy_id})")
    print(f"TYPES: {t1_name} / {t2_name}")
    print("-" * 60)
    print(f"{'MOVE NAME':<15} | {'TYPE':<10} | {'CALCULATION LOGIC':<30} | {'FINAL MULT'}")
    print("-" * 60)

    # 2. CHECK PLAYER MOVES
    for i in range(1, 5):
        move_id = data.lookup_value(f'move_{i}')
        if move_id == 0:
            continue
            
        move_info = MOVES_DATA.get(move_id, {'name': 'Unknown', 'type': 0, 'power': 0})
        move_name = move_info['name']
        move_type_id = move_info['type']
        move_type_name = TYPE_MAP.get(move_type_id, "Normal")
        
        # 3. PERFORM CALCULATION
        # We manually simulate the get_effectiveness logic here to show the "Why"
        mult = 1.0
        logic_str = "1.0"
        
        # Check Type 1
        eff1 = get_effectiveness(move_type_id, [t1])
        if eff1 != 1.0:
            mult *= eff1
            logic_str += f" * {eff1} ({t1_name})"
            
        # Check Type 2
        if t2 is not None:
            eff2 = get_effectiveness(move_type_id, [t2])
            if eff2 != 1.0:
                mult *= eff2
                logic_str += f" * {eff2} ({t2_name})"
        
        # Verify against the actual function
        real_result = get_effectiveness(move_type_id, [t1, t2])
        
        # Print Row
        print(f"{move_name:<15} | {move_type_name:<10} | {logic_str:<30} | x{real_result}")

    print("-" * 60)
    print("INTERPRETATION:")
    print(" x2.0 or x4.0 = GREEN (Super Effective)")
    print(" x1.0         = WHITE (Neutral)")
    print(" x0.5 or x0.25= RED   (Not Very Effective)")
    print(" x0.0         = GREY  (Immune)")

if __name__ == "__main__":
    main()