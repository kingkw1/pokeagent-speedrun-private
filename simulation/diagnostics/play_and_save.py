import retro
import pygame
import sys
import os
import gzip

import json
from datetime import datetime

# Configuration
GAME = 'PokemonEmerald-GBA'
# LOAD_STATE_NAME = 'starter'
LOAD_STATE_NAME = 'BattleLevel5'  # IGNORE

# Load custom buttons if exists
BUTTONS_JSON_PATH = os.path.join(os.path.dirname(__file__), 'data', GAME, 'buttons.json')
CUSTOM_BUTTON_MAPPING = None
if os.path.exists(BUTTONS_JSON_PATH):
    try:
        with open(BUTTONS_JSON_PATH, 'r') as f:
            CUSTOM_BUTTON_MAPPING = json.load(f)
        print(f"Loaded custom button mapping from {BUTTONS_JSON_PATH}")
    except Exception as e:
        print(f"Failed to load custom buttons: {e}")

# Helper function (Place this above main() or inside main() before the loop)
def force_button_test(env, idx, screen, btn_name):
    print(f"TESTING BUTTON {idx} ({btn_name}) - HOLDING 1 SEC...")
    
    # Hold for 60 frames (1 second)
    for i in range(60):
        test_btns = [0] * 12
        test_btns[idx] = 1
        env.step(test_btns)
        
        # Keep window alive/rendering so you can see the result
        if i % 5 == 0: # Render every 5th frame to save speed
            surf = pygame.surfarray.make_surface(env.get_screen().swapaxes(0, 1))
            # Scale up (assuming 2x scale from your config)
            surf = pygame.transform.scale(surf, (480, 320)) 
            screen.blit(surf, (0, 0))
            pygame.display.flip()
            pygame.event.pump() # Prevent 'Not Responding' freeze
            
    print(f"RELEASED BUTTON {idx}")


def main():
    # Initialize Retro with NO state (boot from ROM)
    # render_mode='rgb_array' tells Retro: "Don't open a window, just give me the pixels"
    env = retro.make(game=GAME, state=LOAD_STATE_NAME, render_mode='rgb_array')

    obs = env.reset()

    # Initialize Pygame for display and input
    pygame.init()
    screen_width, screen_height = env.observation_space.shape[1], env.observation_space.shape[0]
    # Scale up 2x for visibility
    scale = 2
    screen = pygame.display.set_mode((screen_width * scale, screen_height * scale))
    pygame.display.set_caption(f"Playing {GAME} - Press S to Save '{LOAD_STATE_NAME}'")
    
    clock = pygame.time.Clock()
    
    print(f"Controls: Arrows = D-Pad, Z=A, X=B, Enter=Start, Shift=Select")
    print(f"PRESS 'S' TO SAVE STATE: {LOAD_STATE_NAME}.state")
    print(f"PRESS 'ESC' TO QUIT")
    
    # Define our Pygame -> Retro mapping for clarity
    controls_map = {
        "A": "Z",
        "B": "X",
        "START": "Enter",
        "SELECT": "Right Shift",
        "D-Pad": "Arrow Keys",
        "L Trigger": "A",
        "R Trigger": "S",
        "SAVE STATE": "M",
        "QUIT": "ESC"
    }

    print("\n" + "="*45)
    print(f"🎮  CONTROLS FOR {GAME}")
    print("="*45)
    print(f" {'GBA BUTTON':<12} | {'KEYBOARD KEY':<15}")
    print("-" * 30)
    for btn, key in controls_map.items():
        print(f" {btn:<12} | {key:<15}")
    print("="*45 + "\n")
    
    print(f"DEBUG: Core Button Mapping: {env.unwrapped.buttons}")
    # output:   DEBUG: Core Button Mapping: ['B', None, 'SELECT', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'A', None, 'L', 'R']
    print(f"Target Save File: {LOAD_STATE_NAME}.state")

    running = True
    while running:
        # 1. Handle Input
        keys = pygame.key.get_pressed()
        
        # Map Pygame keys to Retro buttons (B, Y, SEL, STA, UP, DN, LF, RT, A, X, L, R)
        # GBA Layout in Retro: [B, A, Mode, Start, Up, Down, Left, Right, L, R, Select, Power]
        # Note: Mapping varies, this is a common guess. Adjust if buttons feel wrong.
        # Standard Retro GBA: [A, B, Select, Start, Right, Left, Up, Down, R, L]
        
        # Let's try a standard mapping array (12 buttons max usually)
        # Action space is usually MultiBinary(10) or similar for GBA

        # [B, None, SELECT, START, UP, DOWN, LEFT, RIGHT, A, None, L, R]
        buttons = [0] * 12
        
        if CUSTOM_BUTTON_MAPPING:
             # Use JSON mapping
            if keys[pygame.K_z] and "A" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["A"]] = 1
            if keys[pygame.K_x] and "B" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["B"]] = 1
            if keys[pygame.K_RSHIFT] and "SELECT" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["SELECT"]] = 1
            if (keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER]) and "START" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["START"]] = 1
            if keys[pygame.K_UP] and "UP" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["UP"]] = 1
            if keys[pygame.K_DOWN] and "DOWN" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["DOWN"]] = 1
            if keys[pygame.K_LEFT] and "LEFT" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["LEFT"]] = 1
            if keys[pygame.K_RIGHT] and "RIGHT" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["RIGHT"]] = 1
            if keys[pygame.K_a] and "L" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["L"]] = 1
            if keys[pygame.K_s] and "R" in CUSTOM_BUTTON_MAPPING: buttons[CUSTOM_BUTTON_MAPPING["R"]] = 1
            
        else:
            # Fallback hardcoded mapping
            # Face Buttons
            if keys[pygame.K_z]: buttons[8] = 1      # A is Index 8
            if keys[pygame.K_x]: buttons[0] = 1      # B is Index 0
            
            # Menu
            if keys[pygame.K_RSHIFT]: buttons[2] = 1  # SELECT is Index 2
            if keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER]: buttons[3] = 1  # START is Index 3
            
            # D-Pad
            if keys[pygame.K_UP]: buttons[4] = 1     # UP Index 4
            if keys[pygame.K_DOWN]: buttons[5] = 1   # DOWN Index 5
            if keys[pygame.K_LEFT]: buttons[6] = 1   # LEFT Index 6
            if keys[pygame.K_RIGHT]: buttons[7] = 1  # RIGHT Index 7
            
            # Triggers
            if keys[pygame.K_a]: buttons[10] = 1     # L Index 10
            if keys[pygame.K_s]: buttons[11] = 1     # R Index 11
        
        # 2. Step Environment
        # if any(buttons):
        #      print(f"Buttons pressed: {[i for i, x in enumerate(buttons) if x]}")
             
        obs, rew, terminated, truncated, info = env.step(buttons)
        done = terminated or truncated
        
        # 3. Render
        # Convert numpy array to surface
        surf = pygame.surfarray.make_surface(obs.swapaxes(0, 1))
        surf = pygame.transform.scale(surf, (screen_width * scale, screen_height * scale))
        screen.blit(surf, (0, 0))
        pygame.display.flip()

        # 4. Event Loop (Quit / Save)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_m:

                    this_state_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    print(f"SAVING STATE TO: {this_state_name}.state")
                    content = env.em.get_state()
                    
                    save_path = os.path.join(
                        os.path.dirname(retro.data.get_romfile_path(GAME)),
                        f"{this_state_name}.state"
                    )
                    
                    # CHANGED: Use gzip.open instead of open
                    with gzip.open(save_path, 'wb') as f:
                        f.write(content)
                        
                    print(f"Saved (compressed) successfully to {save_path}")

                # Debug Scanner: Press 0-9, -, = to fire specific indices manually
                # 0-9 for indices 0-9
                # - for index 10
                # = for index 11
                elif event.key >= pygame.K_0 and event.key <= pygame.K_9:
                    idx = event.key - pygame.K_0
                    force_button_test(env, idx, screen, env.unwrapped.buttons[idx])
                    
                elif event.key == pygame.K_MINUS:
                    force_button_test(env, 10, screen, "Index 10")
                    
                elif event.key == pygame.K_EQUALS:
                    force_button_test(env, 11, screen, "Index 11")


        clock.tick(60)

    env.close()
    pygame.quit()

if __name__ == "__main__":
    main()
