import stable_retro as retro
import pygame
import time

# --- LOOKUP TABLES (INTERNAL GEN 3 IDS) ---
SPECIES_MAP = {
    252: "Treecko",
    280: "Torchic",
    258: "Mudkip",
    286: "Poochyena",
    288: "Zigzagoon",
    290: "Wurmple",
}

MOVE_MAP = {
    1: "Pound",
    10: "Scratch",
    33: "Tackle",
    45: "Growl",
    39: "Tail Whip",
    43: "Leer",
    81: "String Shot",
    40: "Poison Sting"
}

def get_name(mapping, internal_id):
    return mapping.get(internal_id, f"Unknown ({internal_id})")

def main():
    # Load Environment with Render Mode (RGB Array) for Pygame
    print("Loading Pokemon Emerald...")
    env = retro.make(game='PokemonEmerald-GBA', state='BattleLevel5', render_mode='rgb_array')
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
            my_name = get_name(SPECIES_MAP, curr_state['my_species'])
            en_name = get_name(SPECIES_MAP, curr_state['enemy_species'])
            
            print(f"MY POKEMON:    {my_name:<15} | HP: {curr_state['my_hp']}")
            print(f"ENEMY POKEMON: {en_name:<15} | HP: {curr_state['enemy_hp']}")
            
            # MOVES & PP
            print("MOVES:")
            for i in range(1, 5):
                m_id = curr_state[f'move_{i}']
                pp   = curr_state[f'pp_{i}']
                if m_id != 0:
                    m_name = get_name(MOVE_MAP, m_id)
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
                
        clock.tick(60)

    env.close()
    pygame.quit()

if __name__ == "__main__":
    main()