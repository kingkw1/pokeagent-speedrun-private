import stable_retro as retro
import pygame
import time
import sys
import os
import gzip
from datetime import datetime

# Add the project root to sys.path to ensure we can import simulation.pokedex
# Assuming this script is in simulation/diagnostics/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir)) # Up 2 levels
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from simulation.pokedex import MOVES_DATA, SPECIES_DATA
except ImportError:
    # Fallback if running from simulation dir directly
    sys.path.append(os.path.dirname(current_dir))
    from pokedex import MOVES_DATA, SPECIES_DATA

# --- LOOKUP TABLES (INTERNAL GEN 3 IDS) ---

LOAD_STATE = 'wingull'  # IGNORE

def get_name(data_dict, internal_id):
    entry = data_dict.get(internal_id)
    if entry and isinstance(entry, dict):
        return entry.get("name", f"Unknown Name ({internal_id})")
    return f"Unknown ({internal_id})"

def main():
    # Load Environment with Render Mode (RGB Array) for Pygame
    print("Loading Pokemon Emerald...")
    env = retro.make(game='PokemonEmerald-GBA', state=LOAD_STATE, render_mode='rgb_array')
    obs = env.reset()

    # Setup Pygame Window
    pygame.init()
    screen = pygame.display.set_mode((480, 320))
    pygame.display.set_caption("Pokemon Emerald - Sensor Verification")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 16)
    
    # --- STATE TRACKING ---
    # We store the entire sensor state to detect ANY change
    prev_state = {}

    print("\n" + "="*50)
    print("👀  SENSOR MONITOR ACTIVE")
    print("="*50)
    print("Play using arrow keys + Z(A) + X(B).")
    print("Press 'M' to save state.")
    print("Console will log whenever internal memory changes.\n")

    running = True
    while running:
        # 1. INPUT HANDLING
        keys = pygame.key.get_pressed()
        buttons = [0] * 12
        if keys[pygame.K_z]: buttons[8] = 1 # A
        if keys[pygame.K_x]: buttons[0] = 1 # B
        if keys[pygame.K_UP]: buttons[4] = 1
        if keys[pygame.K_DOWN]: buttons[5] = 1
        if keys[pygame.K_LEFT]: buttons[6] = 1
        if keys[pygame.K_RIGHT]: buttons[7] = 1
        
        # 2. STEP SIMULATION
        obs, _, _, _, info = env.step(buttons)
        
        # 3. EXTRACT CURRENT STATE
        # We grab everything relevant from data.json
        curr_state = {
            "my_hp":         info.get('my_hp', 0),
            "enemy_hp":      info.get('enemy_hp', 0),
            "my_species":    info.get('my_species', 0),
            "enemy_species": info.get('enemy_species', 0),
            
            "move_1":        info.get('move_1', 0),
            "move_2":        info.get('move_2', 0),
            "move_3":        info.get('move_3', 0),
            "move_4":        info.get('move_4', 0),
            
            "pp_1":          info.get('move_1_pp', 0),
            "pp_2":          info.get('move_2_pp', 0),
            "pp_3":          info.get('move_3_pp', 0),
            "pp_4":          info.get('move_4_pp', 0),
        }

        # 4. DETECT CHANGES
        # If this is the first frame, or if anything changed:
        if curr_state != prev_state:
            # Clear previous print block visually if you prefer, or just append
            print("-" * 60)
            
            # HP & SPECIES
            my_name = get_name(SPECIES_DATA, curr_state['my_species'])
            en_name = get_name(SPECIES_DATA, curr_state['enemy_species'])
            
            print(f"MY POKEMON:    {my_name:<15} | HP: {curr_state['my_hp']}")
            print(f"ENEMY POKEMON: {en_name:<15} | HP: {curr_state['enemy_hp']}")
            
            # MOVES & PP
            print("MOVES:")
            for i in range(1, 5):
                m_id = curr_state[f'move_{i}']
                pp   = curr_state[f'pp_{i}']
                if m_id != 0:
                    m_name = get_name(MOVES_DATA, m_id)
                    print(f"  [{i}] {m_name:<15} (PP: {pp})")
            
            prev_state = curr_state.copy()

        # 5. RENDER
        surf = pygame.surfarray.make_surface(obs.swapaxes(0, 1))
        surf = pygame.transform.scale(surf, (480, 320))
        screen.blit(surf, (0, 0))
        
        # Optional: Draw simple HUD on screen
        hp_text = f"HP: {curr_state['my_hp']} vs {curr_state['enemy_hp']}"
        screen.blit(font.render(hp_text, True, (255, 255, 255)), (10, 10))

        pygame.display.flip()

        # 6. QUIT HANDLING
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    this_state_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    print(f"SAVING STATE TO: {this_state_name}.state")
                    content = env.em.get_state()
                    
                    # We know the game is PokemonEmerald-GBA from the retro.make call
                    save_path = os.path.join(
                        os.path.dirname(retro.data.get_romfile_path('PokemonEmerald-GBA')),
                        f"{this_state_name}.state"
                    )
                    
                    with gzip.open(save_path, 'wb') as f:
                        f.write(content)
                        
                    print(f"Saved (compressed) successfully to {save_path}")
                
        clock.tick(60)

    env.close()
    pygame.quit()

if __name__ == "__main__":
    main()