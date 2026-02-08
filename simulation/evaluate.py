import time
import gymnasium as gym
import numpy as np
import stable_retro as retro
import pygame
import sys
import os

# SB3 Contrib for Masking
from sb3_contrib import MaskablePPO
from pokedex import MOVES_DATA, SPECIES_DATA

# Reuse wrapper and config from train.py
# Ensure train.py is in the same folder or python path
try:
    from train import EmeraldBattleWrapper, GAME_ID, BTN_INDICES, TRAIN_STATES
except ImportError:
    # Fallback if TRAIN_STATES isn't found (if you haven't fully updated train.py yet)
    from train import EmeraldBattleWrapper, GAME_ID, BTN_INDICES
    TRAIN_STATES = ['BattleLevel5', 'State_Advantage', 'State_Disadvantage']

# ==================================================================================
# ⚙️  EVALUATION CONFIG
# ==================================================================================
# Model to Load
MODEL_PATH = "models/PPO_Masked/emerald_curriculum_v1"

# Visual Timing
MENU_SLIDE_WAIT_FRAMES = 30
BUTTON_HOLD_FRAMES = 6
BUTTON_RELEASE_FRAMES = 6
CURSOR_WAIT_FRAMES = 6
# ==================================================================================

class VisualEvaluationWrapper(EmeraldBattleWrapper):
    """
    Wraps the environment to DRAW the game to a window while the Agent plays.
    """
    def __init__(self, env, screen, scenario_name):
        super().__init__(env)
        self.screen = screen
        self.scenario_name = scenario_name
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18, bold=True)
        self.hud_font = pygame.font.SysFont("Arial", 14, bold=True)

    def step(self, action):
        # Visual Check for Invalid Moves (Debug only)
        # We peek at data before the step to see if the agent messed up
        info = {
            'move_1_pp': self.env.data.lookup_value('move_1_pp'),
            'move_2_pp': self.env.data.lookup_value('move_2_pp'),
            'move_3_pp': self.env.data.lookup_value('move_3_pp'),
            'move_4_pp': self.env.data.lookup_value('move_4_pp'),
        }

        # --- LOGGING: Move & Enemy ---
        move_id_key = f'move_{action+1}'
        move_id = self.env.data.lookup_value(move_id_key)
        enemy_id = self.env.data.lookup_value('enemy_species')
        
        move_name = MOVES_DATA.get(move_id, {}).get('name', f"Unknown Move {move_id}")
        enemy_name = SPECIES_DATA.get(enemy_id, {}).get('name', f"Unknown Mon {enemy_id}")
        
        print(f"   > Action Used: {move_name} | vs Enemy: {enemy_name}")
        # -----------------------------
        
        move_pp = 0
        if action == 0: move_pp = info['move_1_pp']
        elif action == 1: move_pp = info['move_2_pp']
        elif action == 2: move_pp = info['move_3_pp']
        elif action == 3: move_pp = info['move_4_pp']

        if move_pp <= 0:
            print(f"⚠️ AGENT ERROR: Selected Action {action} with 0 PP!")

        return super().step(action)

    def _perform_move_macro(self, move_index):
        # Override to visualize button presses
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
        action_arr = np.zeros(12, dtype=np.int8)
        action_arr[BTN_INDICES[btn_name]] = 1
        
        for _ in range(BUTTON_HOLD_FRAMES):
            self.env.step(action_arr)
            self._render_frame(action_name=f"PRESS {btn_name}")
            
        no_op = np.zeros(12, dtype=np.int8)
        for _ in range(BUTTON_RELEASE_FRAMES):
            self.env.step(no_op)
            self._render_frame(action_name="...")

    def _wait(self, frames):
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
        
        # 4. HUD Overlay
        # Scenario Name
        scen_text = self.hud_font.render(f"SCENARIO: {self.scenario_name}", True, (0, 255, 255))
        self.screen.blit(scen_text, (10, 290))

        # Agent Action
        text = self.font.render(f"ACTION: {action_name}", True, (255, 255, 0))
        self.screen.blit(self.font.render(f"ACTION: {action_name}", True, (0,0,0)), (12, 12)) # Shadow
        self.screen.blit(text, (10, 10))

        pygame.display.flip()
        
        # 5. Cap FPS
        self.clock.tick(120) 

def main():
    # 1. Setup Pygame
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((480, 320))
    pygame.display.set_caption("Pokemon Emerald - Curriculum Evaluation")

    # 2. Load Model
    print(f"Loading Model from: {MODEL_PATH}")
    try:
        model = MaskablePPO.load(MODEL_PATH)
    except FileNotFoundError:
        print("❌ Model not found! Ensure you have trained 'emerald_curriculum_v1'.")
        return

    print(f"\n🚀 STARTING EVALUATION LOOP")
    print(f"Scenarios: {TRAIN_STATES}\n")

    # 3. Main Loop (Cycles through states)
    state_index = 0
    battles_total = 0
    wins_total = 0

    while True:
        # A. Pick Scenario
        current_state = TRAIN_STATES[state_index % len(TRAIN_STATES)]

        # B. Init Environment (Re-make to load new state)
        # Note: We must use render_mode='rgb_array' for get_screen() to work in wrapper
        try:
            raw_env = retro.make(game=GAME_ID, state=current_state, render_mode='rgb_array')
        except FileNotFoundError:
            print(f"⚠️  State '{current_state}' not found. Skipping.")
            state_index += 1
            continue

        env = VisualEvaluationWrapper(raw_env, screen, current_state)
        
        # C. Run Episode
        obs, info = env.reset()

        # Print Battle Header with Enemy Name
        # Note: env is VisualEvaluationWrapper -> env.env is RetroEnv
        enemy_id = env.env.data.lookup_value('enemy_species')
        enemy_name = SPECIES_DATA.get(enemy_id, {}).get('name', f'Unknown_{enemy_id}')
        
        print(f"--- Battle {battles_total + 1} | Scenario: {current_state} vs {enemy_name} ---")
        terminated = False
        
        while not terminated:
            # Action Masking is CRITICAL for MaskablePPO
            action_masks = env.action_masks()
            
            # Predict
            action, _ = model.predict(obs, action_masks=action_masks, deterministic=True)
            
            # Step
            obs, reward, terminated, truncated, info = env.step(action)
            
            if terminated:
                battles_total += 1
                if info.get('enemy_hp') == 0:
                    print(f"   Result: VICTORY 🏆")
                    wins_total += 1
                else:
                    print(f"   Result: DEFEAT 💀")
                
                # Show result for a moment
                env._wait(120)

        # D. Cleanup & Next
        env.close()
        state_index += 1
        
        # Optional: Print Stats
        print(f"   Session Win Rate: {wins_total}/{battles_total} ({wins_total/battles_total*100:.1f}%)")

if __name__ == "__main__":
    main()