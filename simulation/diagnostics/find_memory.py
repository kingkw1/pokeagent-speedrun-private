import stable_retro as retro
import pygame
import struct

GAME = 'PokemonEmerald-GBA'
STATE = 'BattleLevel5'

def main():
    # Load with NO VARIABLES to avoid crashes
    # Write empty data.json first
    import json
    with open('simulation/data/PokemonEmerald-GBA/data.json', 'w') as f:
        json.dump({"info": {}}, f)

    env = retro.make(game=GAME, state=STATE, render_mode='rgb_array')
    env.reset()

    pygame.init()
    screen = pygame.display.set_mode((480, 320))
    clock = pygame.time.Clock()
    
    # Initialize Search
    # We will search in the System WRAM (Block 0 usually)
    # env.data.memory.blocks is a dict of {address_start: bytearray}
    print("Memory Blocks found:", env.data.memory.blocks.keys())
    
    # We flatten all blocks into a list of (global_address, value) checking
    # But for speed, we keep candidates as (block_addr, offset)
    candidates = []
    
    # Initial population: Add EVERY byte in EVERY block to candidates
    for base_addr, block in env.data.memory.blocks.items():
        print(f"Indexing Block {base_addr} (Size: {len(block)})...")
        # Optimization: Only add indices, don't copy data
        for i in range(len(block)):
            candidates.append((base_addr, i))
            
    print(f"Total Search Space: {len(candidates)} bytes")

    running = True
    while running:
        # Input Handling
        keys = pygame.key.get_pressed()
        buttons = [0] * 12
        if keys[pygame.K_z]: buttons[8] = 1 # A
        if keys[pygame.K_x]: buttons[0] = 1 # B
        if keys[pygame.K_UP]: buttons[4] = 1
        if keys[pygame.K_DOWN]: buttons[5] = 1
        if keys[pygame.K_LEFT]: buttons[6] = 1
        if keys[pygame.K_RIGHT]: buttons[7] = 1
        if keys[pygame.K_SPACE]: buttons[3] = 1 # Start
        
        obs, _, _, _, _ = env.step(buttons)
        
        # Render
        surf = pygame.surfarray.make_surface(obs.swapaxes(0, 1))
        surf = pygame.transform.scale(surf, (480, 320))
        screen.blit(surf, (0, 0))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    try:
                        val_str = input(f"\n[Filtering {len(candidates)} addrs] Enter current HP: ")
                        if not val_str: continue
                        target_val = int(val_str)
                        
                        print("Scanning...")
                        new_candidates = []
                        
                        # Refresh memory view
                        blocks = env.data.memory.blocks
                        
                        for base_addr, offset in candidates:
                            # Read current value
                            try:
                                # Access buffer directly
                                val = blocks[base_addr][offset]
                                if val == target_val:
                                    new_candidates.append((base_addr, offset))
                            except:
                                pass # Block might have shifted/resized (unlikely)
                        
                        candidates = new_candidates
                        print(f"Found {len(candidates)} matches.")
                        
                        if len(candidates) < 20:
                            print("Matches Found!")
                            for base, off in candidates:
                                global_addr = base + off
                                print(f"  Decimal: {global_addr} (Base {base} + {off})")
                                print(f"  Hex: {hex(global_addr)}")
                            
                    except ValueError:
                        print("Invalid input.")

        clock.tick(60)
    env.close()

if __name__ == "__main__":
    main()
