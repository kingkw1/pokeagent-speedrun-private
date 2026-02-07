import stable_retro as retro
import gymnasium as gym
import numpy as np
import os
import sys

# Add the current directory to sys.path to ensure we can import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from pokedex import MOVES_DATA, SPECIES_DATA, get_effectiveness
except ImportError:
    # Fallback if running from root without package structure
    from simulation.pokedex import MOVES_DATA, SPECIES_DATA, get_effectiveness

from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.monitor import Monitor

# ==================================================================================
# ⚙️  TUNING CONFIGURATION
# ==================================================================================

# 1. ENVIRONMENT & CURRICULUM
GAME_ID = 'PokemonEmerald-GBA'
# The agent will cycle through these states in parallel
TRAIN_STATES = [
    'BattleLevel5',       # Original (Torchic vs Wurmple)
    'State_Advantage',    # e.g., Fire vs Grass (Should learn Ember)
    'State_Disadvantage'  # e.g., Fire vs Water (Should learn Scratch)
]
NUM_ENVS = 4 # Must be at least len(TRAIN_STATES) to see all scenarios

# 2. TIMING (Frames)
POST_ATTACK_WAIT_FRAMES = 900 # Reduced from 900 for speed (900 is ~15s, too slow)
MENU_SLIDE_WAIT_FRAMES = 30
BUTTON_HOLD_FRAMES = 6
BUTTON_RELEASE_FRAMES = 6
CURSOR_WAIT_FRAMES = 6

# 3. REWARDS
REWARD_WIN_BONUS = 20.0
REWARD_DMG_MULTIPLIER = 2.0
PENALTY_DMG_TAKEN = 1.0
PENALTY_INVALID_MOVE = -5.0

# 4. TRAINING HYPERPARAMETERS
TOTAL_TIMESTEPS = 100000 # Increased for multi-scenario learning
PPO_LEARNING_RATE = 0.0003
PPO_N_STEPS = 128
PPO_BATCH_SIZE = 64
MODELS_DIR = "models/PPO_Masked"
LOG_DIR = "simulation/data/logs"
MODEL_SAVE_NAME = "emerald_curriculum_v1"

# 5. BUTTON MAPPING
BTN_INDICES = {'B': 0, 'A': 8, 'SELECT': 2, 'START': 3, 'UP': 4, 'DOWN': 5, 'LEFT': 6, 'RIGHT': 7, 'L': 10, 'R': 11}
OBS_NORM_FACTOR = 20.0

# ==================================================================================

class EmeraldBattleWrapper(gym.Wrapper):
    def __init__(self, env):
        super().__init__(env)
        
        # Action Space: 4 Discrete Actions (Move 1, Move 2, Move 3, Move 4)
        self.action_space = gym.spaces.Discrete(4)
        
        # Observation Space: 
        # [MyHP, EnemyHP] + 4 * [PP, Power, Effectiveness]
        # Total = 2 + 12 = 14
        self.observation_space = gym.spaces.Box(low=0, high=1, shape=(14,), dtype=np.float32)

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self.prev_my_hp = info.get('my_hp', 0)
        self.prev_enemy_hp = info.get('enemy_hp', 0)
        return self._get_obs(info), info

    def action_masks(self):
        """
        Returns a boolean mask of valid actions based on PP.
        True = Valid, False = Invalid (Masked).
        """
        # We need direct access to data here because this is called by the Agent 
        # before the step() function.
        # Note: data.lookup_value is a direct RAM read.
        data = self.env.data
        
        # Read PP values (default to 0 if missing)
        pp_values = [
            data.lookup_value('move_1_pp') or 0,
            data.lookup_value('move_2_pp') or 0,
            data.lookup_value('move_3_pp') or 0,
            data.lookup_value('move_4_pp') or 0
        ]
        
        # Create mask: True if PP > 0
        mask = [pp > 0 for pp in pp_values]
        
        # FAILSAFE: If all moves have 0 PP (Struggle), allow all actions? 
        # Or maybe just Action 0? 
        # In Gen 3, if you have no PP, you automatically Struggle when you select Fight.
        # But we are selecting Move 1, 2, 3, 4 menus.
        # If we mask ALL, the agent crashes. So if all 0, unmask all.
        if not any(mask):
            return np.array([True, True, True, True], dtype=bool)
            
        return np.array(mask, dtype=bool)

    def step(self, action):
        # 1. GET DATA (Robust Lookup)
        # We perform a manual lookup because env.data is not a standard dict
        data = self.env.data
        info = {
            'my_hp': data.lookup_value('my_hp') or 0,
            'enemy_hp': data.lookup_value('enemy_hp') or 0,
            'move_1_pp': data.lookup_value('move_1_pp') or 0,
            'move_2_pp': data.lookup_value('move_2_pp') or 0,
            'move_3_pp': data.lookup_value('move_3_pp') or 0,
            'move_4_pp': data.lookup_value('move_4_pp') or 0,
            # Extended Data for Pokedex
            'move_1': data.lookup_value('move_1') or 0,
            'move_2': data.lookup_value('move_2') or 0,
            'move_3': data.lookup_value('move_3') or 0,
            'move_4': data.lookup_value('move_4') or 0,
            'enemy_species': data.lookup_value('enemy_species') or 0,
        }

        # 2. ACTION MASKING (Soft Mask / Penalty)
        # Check if the chosen move has PP
        move_pp = 0
        if action == 0: move_pp = info['move_1_pp']
        elif action == 1: move_pp = info['move_2_pp']
        elif action == 2: move_pp = info['move_3_pp']
        elif action == 3: move_pp = info['move_4_pp']

        if move_pp <= 0:
            # INVALID MOVE: Penalize and skip turn logic to prevent getting stuck
            obs = self._get_obs(info)
            # We step 1 frame just to tick the clock slightly
            self._wait(1) 
            return obs, PENALTY_INVALID_MOVE, False, False, info

        # 3. EXECUTE MACRO
        self._perform_move_macro(action)
        
        # 4. FAST FORWARD (Wait for animation)
        self._wait(POST_ATTACK_WAIT_FRAMES) 

        # 5. CALCULATE REWARD
        # Refresh info after the turn to see the damage result
        new_my_hp = data.lookup_value('my_hp') or 0
        new_enemy_hp = data.lookup_value('enemy_hp') or 0
        
        damage_dealt = self.prev_enemy_hp - new_enemy_hp
        damage_taken = self.prev_my_hp - new_my_hp
        
        # Clamp negative damage (healing/reset noise)
        if damage_dealt < 0: damage_dealt = 0
        if damage_taken < 0: damage_taken = 0
        
        reward = (damage_dealt * REWARD_DMG_MULTIPLIER) - (damage_taken * PENALTY_DMG_TAKEN)
        
        # Win Bonus
        terminated = False
        if new_enemy_hp == 0 and self.prev_enemy_hp > 0:
            reward += REWARD_WIN_BONUS
            terminated = True
        elif new_my_hp == 0:
            terminated = True
            
        # Update tracking
        self.prev_my_hp = new_my_hp
        self.prev_enemy_hp = new_enemy_hp
        
        # Update Info for return
        info['my_hp'] = new_my_hp
        info['enemy_hp'] = new_enemy_hp

        return self._get_obs(info), reward, terminated, False, info

    def _get_obs(self, info):
            # 1. Base Stats
            obs = [
                info.get('my_hp', 0) / OBS_NORM_FACTOR, 
                info.get('enemy_hp', 0) / OBS_NORM_FACTOR,
            ]

            # 2. Parse Enemy Types (The "Eye")
            enemy_id = info.get('enemy_species', 0)
            enemy_data = SPECIES_DATA.get(enemy_id, {"types": [None, None]})
            enemy_types = enemy_data.get("types", [None, None])

            # 3. Enriched Move Data (The "Brain")
            for i in range(1, 5):
                # PP Norm
                pp = info.get(f'move_{i}_pp', 0)
                norm_pp = 1.0 if pp > 0 else 0.0 # Binary availability is clearer for the AI than 0.35
                
                # Pokedex Info
                move_id = info.get(f'move_{i}', 0)
                move_info = MOVES_DATA.get(move_id, {"type": 0, "power": 0})
                
                # Power Norm
                power = move_info.get("power", 0)
                norm_power = power / 100.0 
                
                # Effectiveness Norm
                move_type = move_info.get("type", 0)
                eff = get_effectiveness(move_type, enemy_types)
                norm_eff = eff / 4.0 # Normalize so 4.0x becomes 1.0
                
                obs.extend([norm_pp, norm_power, norm_eff])

            return np.array(obs, dtype=np.float32)

    def _perform_move_macro(self, move_index):
        """
        Navigates the Battle Menu.
        Assumes cursor starts at 'FIGHT' (Top-Left).
        """
        # Select 'FIGHT'
        self._press_button('A')
        self._wait(MENU_SLIDE_WAIT_FRAMES)

        # Navigate Grid
        if move_index == 1: # TR
            self._press_button('RIGHT')
        elif move_index == 2: # BL
            self._press_button('DOWN')
        elif move_index == 3: # BR
            self._press_button('DOWN') 
            self._wait(CURSOR_WAIT_FRAMES) 
            self._press_button('RIGHT')

        if move_index != 0:
            self._wait(CURSOR_WAIT_FRAMES)

        # Confirm Move
        self._press_button('A')

    def _press_button(self, btn_name):
        action_arr = np.zeros(12, dtype=np.int8)
        action_arr[BTN_INDICES[btn_name]] = 1
        
        for _ in range(BUTTON_HOLD_FRAMES):
            self.env.step(action_arr)
            
        no_op = np.zeros(12, dtype=np.int8)
        for _ in range(BUTTON_RELEASE_FRAMES):
            self.env.step(no_op)

    def _wait(self, frames):
        no_op = np.zeros(12, dtype=np.int8)
        for _ in range(frames):
            self.env.step(no_op)
            
def mask_fn(env):
    return env.action_masks()

def make_env(rank):
    """
    Factory function that assigns a DIFFERENT state to each environment rank.
    Rank 0 -> BattleLevel5
    Rank 1 -> State_Advantage
    Rank 2 -> State_Disadvantage
    """
    def _init():
        # Cycle through the available states based on the Rank ID
        state_to_load = TRAIN_STATES[rank % len(TRAIN_STATES)]
        # print(f"Worker {rank} loading scenario: {state_to_load}")
        
        env = retro.make(game=GAME_ID, state=state_to_load, render_mode='rgb_array')
        env = EmeraldBattleWrapper(env)
        env = ActionMasker(env, mask_fn) # Apply Safety Mask
        return Monitor(env)
    return _init

def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    # Parallel Environments with Curriculum
    # We pass the index 'i' to make_env so it knows which State to load
    env = SubprocVecEnv([make_env(i) for i in range(NUM_ENVS)]) 
    
    model = MaskablePPO(
        "MlpPolicy", 
        env, 
        verbose=1, 
        tensorboard_log=LOG_DIR,
        learning_rate=PPO_LEARNING_RATE,
        n_steps=PPO_N_STEPS,
        batch_size=PPO_BATCH_SIZE,
        device="cpu"
    )
    
    print(f"🚀 Starting Curriculum Training on {len(TRAIN_STATES)} Scenarios...")
    model.learn(total_timesteps=TOTAL_TIMESTEPS, progress_bar=True)
    
    model.save(f"{MODELS_DIR}/{MODEL_SAVE_NAME}")
    print("Training Complete. Model saved.")

if __name__ == "__main__":
    main()