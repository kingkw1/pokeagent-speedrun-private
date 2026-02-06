import time
import gymnasium as gym
import numpy as np
import stable_retro as retro
import pygame
import sys
from stable_baselines3 import PPO

# Reuse the wrapper structure from training to ensure inputs match exactly
from train import EmeraldBattleWrapper, STATE_NAME, GAME_ID, BTN_INDICES

# ==================================================================================
# ⚙️  EVALUATION CONFIG (Must match Training!)
# ==================================================================================
POST_ATTACK_WAIT_FRAMES = 250  # Matches train.py (or whatever you set it to)
MENU_SLIDE_WAIT_FRAMES = 30
BUTTON_HOLD_FRAMES = 6
BUTTON_RELEASE_FRAMES = 6
CURSOR_WAIT_FRAMES = 6
# ==================================================================================

class VisualEvaluationWrapper(EmeraldBattleWrapper):
    """
    Wraps the environment to DRAW the game to a window while the Agent plays.
    """
    def __init__(self, env, screen):
        super().__init__(env)
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18, bold=True)

    # --- OVERRIDE TIMING & RENDERING ---
    # We override these methods to inject "Rendering" into the wait loops
    
    def step(self, action):
        # 1. ACTION MASKING VISUALIZATION
        # (We duplicate the check here just to print it to the screen if needed)
        info = {
            'move_1_pp': self.env.data.lookup_value('move_1_pp'),
            'move_2_pp': self.env.data.lookup_value('move_2_pp'),
            'move_3_pp': self.env.data.lookup_value('move_3_pp'),
            'move_4_pp': self.env.data.lookup_value('move_4_pp'),
        }
        
        # Check for invalid move (visual feedback only)
        move_pp = 0
        if action == 0: move_pp = info['move_1_pp']
        elif action == 1: move_pp = info['move_2_pp']
        elif action == 2: move_pp = info['move_3_pp']
        elif action == 3: move_pp = info['move_4_pp']

        if move_pp <= 0:
            print(f"Agent tried Action {action} but had NO PP!")
            # The base wrapper handles the penalty, we just want to see it fail
        
        # Call the normal step, but it uses OUR _wait and _perform_move_macro
        return super().step(action)

    def _perform_move_macro(self, move_index):
        # We override this to ensure our visual _press_button is used
        # (Python inheritance usually handles this, but being explicit is safe)
        self._press_button('A')
        self._wait(MENU_SLIDE_WAIT_FRAMES)

        if move_index == 1: 
            self._press_button('RIGHT')
        elif move_index == 2: 
            self._press_button('DOWN')
        elif move_index == 3: 
            self._press_button('DOWN') 
            self._wait(CURSOR_WAIT_FRAMES) 
            self._press_button('RIGHT')

        if move_index != 0:
            self._wait(CURSOR_WAIT_FRAMES)

        self._press_button('A')

    def _press_button(self, btn_name):
        # LOGIC
        action_arr = np.zeros(12, dtype=np.int8)
        action_arr[BTN_INDICES[btn_name]] = 1
        
        # RENDER HOLD
        for _ in range(BUTTON_HOLD_FRAMES):
            self.env.step(action_arr)
            self._render_frame(action_name=f"PRESS {btn_name}")
            
        # RENDER RELEASE
        no_op = np.zeros(12, dtype=np.int8)
        for _ in range(BUTTON_RELEASE_FRAMES):
            self.env.step(no_op)
            self._render_frame(action_name="...")

    def _wait(self, frames):
        # RENDER WAIT
        no_op = np.zeros(12, dtype=np.int8)
        for _ in range(frames):
            self.env.step(no_op)
            self._render_frame(action_name="WAITING")

    def _render_frame(self, action_name=""):
        # 1. Event Pump
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # 2. Get Pixels
        raw_screen = self.env.get_screen()
        surf = pygame.surfarray.make_surface(raw_screen.swapaxes(0, 1))
        surf = pygame.transform.scale(surf, (480, 320))
        
        # 3. Draw
        self.screen.blit(surf, (0, 0))
        
        # 4. Overlay
        text = self.font.render(f"AGENT ACTION: {action_name}", True, (255, 255, 0))
        # Shadow
        self.screen.blit(self.font.render(f"AGENT ACTION: {action_name}", True, (0,0,0)), (12, 12))
        self.screen.blit(text, (10, 10))

        pygame.display.flip()
        
        # 5. Cap FPS (Run at 60 to look normal, or 120 to fast forward slightly)
        self.clock.tick(120) 

def main():
    # 1. Setup Pygame
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((480, 320))
    pygame.display.set_caption("Pokemon Emerald - PPO Agent Evaluation")

    # 2. Load Environment
    print("Loading Environment...")
    # render_mode='rgb_array' is required for get_screen()
    raw_env = retro.make(game=GAME_ID, state=STATE_NAME, render_mode='rgb_array')
    env = VisualEvaluationWrapper(raw_env, screen)

    # 3. Load Model
    model_path = "models/PPO/emerald_battle_v1"
    print(f"Loading Model from: {model_path}")
    
    try:
        model = PPO.load(model_path)
    except FileNotFoundError:
        print("❌ Model not found! Did you finish training?")
        return

    # 4. Evaluation Loop
    battles = 0
    wins = 0
    
    obs, info = env.reset()
    
    print("\n--- STARTING EVALUATION ---")
    
    while True:
        # GET ACTION FROM AI
        # deterministic=True means "Pick the absolute best move", no randomness
        action, _states = model.predict(obs, deterministic=True)
        
        # STEP ENV
        obs, reward, terminated, truncated, info = env.step(action)
        
        if terminated:
            battles += 1
            # Check Win Condition (Enemy HP = 0)
            if info.get('enemy_hp') == 0:
                print(f"Battle {battles}: VICTORY 🏆")
                wins += 1
            else:
                print(f"Battle {battles}: DEFEAT 💀")
            
            print(f"Win Rate: {wins}/{battles} ({wins/battles*100:.1f}%)")
            
            # Pause briefly to see the result screen
            env._wait(120)
            obs, info = env.reset()

if __name__ == "__main__":
    main()