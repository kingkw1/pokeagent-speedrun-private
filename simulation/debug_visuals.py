import time
import gymnasium as gym
import numpy as np
import stable_retro as retro
import pygame
import sys

# Import existing wrapper
from train import EmeraldBattleWrapper 

# ==================================================================================
# ⚙️  TUNING CONFIGURATION (Edit these values!)
# ==================================================================================

# 1. TURN DURATION
# How long to wait after confirming an attack for the animation to play out.
# If this is too short, the agent won't see the HP bar drop.
POST_ATTACK_WAIT_FRAMES = 900  

# 2. BUTTON TIMING
# How long to hold a button down (GBA needs ~4-8 frames to register reliably).
BUTTON_HOLD_FRAMES = 6
# How long to wait between presses (neutral input).
BUTTON_RELEASE_FRAMES = 6

# 3. MENU DELAYS
# How long to wait for the "Fight/Bag" menu to slide away after pressing 'Fight'.
MENU_SLIDE_WAIT_FRAMES = 30
# Small pause between cursor movements to ensure accuracy.
CURSOR_WAIT_FRAMES = 6

# ==================================================================================

class VisualBattleWrapper(EmeraldBattleWrapper):
    """
    A subclass specifically for visually debugging the macros.
    It takes a Pygame screen object to draw directly to the window.
    """
    def __init__(self, env, screen):
        super().__init__(env)
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)

    # --- OVERRIDES TO USE CONFIG VARIABLES ---
    
    def step(self, action):
        """
        Overriding step to use POST_ATTACK_WAIT_FRAMES from config
        """
        # (Standard PP Check omitted for visual debug simplicity, but we keep the logic)
        
        # 1. EXECUTE MACRO
        self._perform_move_macro(action)
        
        # 2. FAST FORWARD (Using our Tunable Variable)
        self._wait(POST_ATTACK_WAIT_FRAMES) 

        # 3. OBSERVE & REWARD (Standard Logic)
        info = {
            'my_hp': self.env.data.lookup_value('my_hp'),
            'enemy_hp': self.env.data.lookup_value('enemy_hp'),
        }
        
        # ... (We skip the full reward calculation for debug, we just want to see it run) ...
        obs = self._get_obs(info)
        return obs, 0, False, False, info

    def _perform_move_macro(self, move_index):
        """
        Overriding macro to use MENU variables from config
        """
        # Step 1: Select 'FIGHT'
        self._press_button('A')
        self._wait(MENU_SLIDE_WAIT_FRAMES)

        # Step 2: Navigate to Move
        if move_index == 1: # Top-Right
            self._press_button('RIGHT')
        elif move_index == 2: # Bottom-Left
            self._press_button('DOWN')
        elif move_index == 3: # Bottom-Right
            self._press_button('DOWN') 
            self._wait(CURSOR_WAIT_FRAMES) 
            self._press_button('RIGHT')

        self._wait(CURSOR_WAIT_FRAMES) 

        # Step 3: Confirm Move
        self._press_button('A')

    def _press_button(self, btn_name, hold_frames=None):
        """
        Overriding to use BUTTON_HOLD/RELEASE variables
        """
        if hold_frames is None: hold_frames = BUTTON_HOLD_FRAMES
        
        print(f"   [DEBUG] Pressing Button: {btn_name}")
        
        action_arr = np.zeros(12, dtype=np.int8)
        action_arr[self.btn_indices[btn_name]] = 1
        
        # Hold
        for _ in range(hold_frames):
            _, _, _, _, info = self.env.step(action_arr)
            self._render_frame(None, info, action_name=f"Press {btn_name}")
            
        # Release (Gap)
        no_op = np.zeros(12, dtype=np.int8)
        for _ in range(BUTTON_RELEASE_FRAMES):
            _, _, _, _, info = self.env.step(no_op)
            self._render_frame(None, info, action_name="Release")

    # --- RENDERING LOGIC ---

    def _render_frame(self, unused_obs, info, action_name="Wait"):
        # 1. Check for Quit
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # 2. Fetch RAW SCREEN
        raw_screen = self.env.get_screen()

        # 3. Convert & Scale
        surf = pygame.surfarray.make_surface(raw_screen.swapaxes(0, 1))
        surf = pygame.transform.scale(surf, (480, 320))
        
        # 4. Draw to Screen
        self.screen.blit(surf, (0, 0))
        
        # 5. Draw Debug Overlay (TOP RIGHT)
        hp_text = f"HP: {info.get('my_hp', '?')} vs {info.get('enemy_hp', '?')}"
        act_text = f"Action: {action_name}"
        
        # Create text surfaces
        hp_surf = self.font.render(hp_text, True, (255, 255, 255))
        act_surf = self.font.render(act_text, True, (255, 255, 255))
        hp_shadow = self.font.render(hp_text, True, (0, 0, 0))
        act_shadow = self.font.render(act_text, True, (0, 0, 0))

        # Calculate Positions (Right aligned with 10px padding)
        # Screen Width is 480
        hp_x = 480 - hp_surf.get_width() - 10
        act_x = 480 - act_surf.get_width() - 10
        
        # Draw Shadow then Text
        self.screen.blit(hp_shadow, (hp_x + 2, 12))
        self.screen.blit(hp_surf, (hp_x, 10))
        
        self.screen.blit(act_shadow, (act_x + 2, 32))
        self.screen.blit(act_surf, (act_x, 30))

        pygame.display.flip()
        self.clock.tick(60)

    def _wait(self, frames):
        print(f"   [DEBUG] Waiting {frames} frames (Animation)...")
        no_op = np.zeros(12, dtype=np.int8)
        
        for i in range(frames):
            _, _, _, _, info = self.env.step(no_op)
            self._render_frame(None, info, action_name="Waiting...")

def main():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((480, 320))
    pygame.display.set_caption("Pokemon Emerald - Macro Tuner")
    
    print("Loading Pokemon Emerald...")
    raw_env = retro.make(game='PokemonEmerald-GBA', state='BattleLevel5', render_mode='rgb_array')
    env = VisualBattleWrapper(raw_env, screen)
    
    obs, info = env.reset()
    env._render_frame(obs, info, "READY")
    
    print("Environment Ready.")
    print(f"Post-Attack Wait set to: {POST_ATTACK_WAIT_FRAMES} frames")

    try:
        while True:
            pygame.event.pump() 
            print(f"\n[TURN START] HP: {info.get('my_hp')} vs {info.get('enemy_hp')}")
            print("Select Move (1-4) or 'q' to quit:")
            
            try:
                user_input = input(">> ")
                if user_input.lower() == 'q': break
                action_idx = int(user_input) - 1
                if action_idx not in [0, 1, 2, 3]: raise ValueError
            except ValueError:
                print("Invalid input. Using Move 1.")
                action_idx = 0

            obs, reward, terminated, truncated, info = env.step(action_idx)
            
            if terminated:
                print("\n!!! BATTLE ENDED !!!")
                env._wait(120) 
                obs, info = env.reset()

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        env.close()
        pygame.quit()

if __name__ == "__main__":
    main()