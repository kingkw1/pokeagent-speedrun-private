import stable_retro as retro
import pygame

def main():
    env = retro.make(game='PokemonEmerald-GBA', state='BattleLevel5', render_mode='rgb_array')
    obs = env.reset()

    pygame.init()
    screen = pygame.display.set_mode((480, 320))
    clock = pygame.time.Clock()
    
    # Store previous values to detect change
    prev_my_hp = 0
    prev_enemy_hp = 0

    print("--- SENSOR LIVE MONITOR ---")
    print("Play the game. Logs will appear when HP changes in memory.")

    running = True
    while running:
        # Input handling (Standard)
        keys = pygame.key.get_pressed()
        buttons = [0] * 12
        if keys[pygame.K_z]: buttons[8] = 1 # A
        if keys[pygame.K_x]: buttons[0] = 1 # B
        if keys[pygame.K_UP]: buttons[4] = 1
        if keys[pygame.K_DOWN]: buttons[5] = 1
        if keys[pygame.K_LEFT]: buttons[6] = 1
        if keys[pygame.K_RIGHT]: buttons[7] = 1
        
        obs, _, _, _, info = env.step(buttons)
        
        # SENSOR CHECK
        curr_my_hp = info.get('my_hp', 0)
        curr_enemy_hp = info.get('enemy_hp', 0)
        
        if curr_my_hp != prev_my_hp or curr_enemy_hp != prev_enemy_hp:
            print(f"Update -> My HP: {curr_my_hp} | Enemy HP: {curr_enemy_hp}")
            prev_my_hp = curr_my_hp
            prev_enemy_hp = curr_enemy_hp
            
        # Render
        surf = pygame.surfarray.make_surface(obs.swapaxes(0, 1))
        surf = pygame.transform.scale(surf, (480, 320))
        screen.blit(surf, (0, 0))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
        clock.tick(60)
    env.close()

if __name__ == "__main__":
    main()
