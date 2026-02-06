import stable_retro as retro
import gymnasium as gym
import numpy as np
import os
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.monitor import Monitor

# Define the custom environment wrapper
class EmeraldBattleWrapper(gym.Wrapper):
    def __init__(self, env):
        super().__init__(env)
        
        # Action Space: 4 Discrete Actions (Move 1, Move 2, Move 3, Move 4)
        self.action_space = gym.spaces.Discrete(4)
        
        # Observation Space: [MyHP, EnemyHP, PP1, PP2, PP3, PP4]
        # Normalized 0.0 to 1.0
        self.observation_space = gym.spaces.Box(low=0, high=1, shape=(6,), dtype=np.float32)

        # RETRO BUTTON MAP (Corrected based on play_and_save.py)
        # 0=B, 1=Y/Mode, 2=Select, 3=Start, 4=Up, 5=Down, 6=Left, 7=Right, 8=A, 9=X, 10=L, 11=R
        self.btn_indices = {
            'B': 0, 
            'A': 8,      # FIXED: 'A' is Index 8, not 1
            'SELECT': 2,
            'START': 3, 
            'UP': 4, 
            'DOWN': 5, 
            'LEFT': 6, 
            'RIGHT': 7,
            'L': 10,
            'R': 11
        }

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self.prev_my_hp = info.get('my_hp', 0)
        self.prev_enemy_hp = info.get('enemy_hp', 0)
        return self._get_obs(info), info

    def step(self, action):
        # Retrieve current state for validation
        # Check keys against your data.json
        current_pp = 0
        if action == 0: current_pp = self.env.data.lookup_value('move_1_pp') or 0
        elif action == 1: current_pp = self.env.data.lookup_value('move_2_pp') or 0
        elif action == 2: current_pp = self.env.data.lookup_value('move_3_pp') or 0
        elif action == 3: current_pp = self.env.data.lookup_value('move_4_pp') or 0

        # --- PP CHECK ---
        # If the agent tries to use a move with 0 PP, penalize it and do NOT press buttons.
        if current_pp <= 0:
            # FIXED: Create a dictionary manually because env.data is not a dict
            temp_info = {
                'my_hp': self.env.data.lookup_value('my_hp'),
                'enemy_hp': self.env.data.lookup_value('enemy_hp'),
                'move_1_pp': self.env.data.lookup_value('move_1_pp'),
                'move_2_pp': self.env.data.lookup_value('move_2_pp'),
                'move_3_pp': self.env.data.lookup_value('move_3_pp'),
                'move_4_pp': self.env.data.lookup_value('move_4_pp'),
            }
            obs = self._get_obs(temp_info) 
            self._wait(1) 
            return obs, -5.0, False, False, {}

        # --- 1. EXECUTE MACRO ---
        # Perform the button sequence to select the move
        self._perform_move_macro(action)
        
        # --- 2. FAST FORWARD (The "Wait") ---
        # Wait 4 seconds (240 frames) for animations/text to finish
        self._wait(240) 

        # --- 3. OBSERVE & REWARD ---
        # Get fresh info after the turn
        info = {
            'my_hp': self.env.data.lookup_value('my_hp'),
            'enemy_hp': self.env.data.lookup_value('enemy_hp'),
            'move_1_pp': self.env.data.lookup_value('move_1_pp'),
            'move_2_pp': self.env.data.lookup_value('move_2_pp'),
            'move_3_pp': self.env.data.lookup_value('move_3_pp'),
            'move_4_pp': self.env.data.lookup_value('move_4_pp'),
        }

        # Calculate HP change
        my_hp = info.get('my_hp', 0)
        enemy_hp = info.get('enemy_hp', 0)
        
        damage_dealt = self.prev_enemy_hp - enemy_hp
        damage_taken = self.prev_my_hp - my_hp
        
        if damage_dealt < 0: damage_dealt = 0
        if damage_taken < 0: damage_taken = 0
        
        reward = (damage_dealt * 2.0) - (damage_taken * 1.0)
        
        if enemy_hp == 0 and self.prev_enemy_hp > 0:
            reward += 20.0 
            
        self.prev_my_hp = my_hp
        self.prev_enemy_hp = enemy_hp
        
        terminated = enemy_hp == 0 or my_hp == 0
        truncated = False
        
        obs = self._get_obs(info)
        return obs, reward, terminated, truncated, info

    def _get_obs(self, info):
        # Normalize assuming max HP ~20 (Level 5)
        my_hp = info.get('my_hp', 0) or 0
        enemy_hp = info.get('enemy_hp', 0) or 0
        
        pp1 = info.get('move_1_pp', 0) or 0
        pp2 = info.get('move_2_pp', 0) or 0
        pp3 = info.get('move_3_pp', 0) or 0
        pp4 = info.get('move_4_pp', 0) or 0

        return np.array([
            my_hp / 20.0, 
            enemy_hp / 20.0,
            pp1 / 20.0,
            pp2 / 20.0,
            pp3 / 20.0,
            pp4 / 20.0
        ], dtype=np.float32)

    def _perform_move_macro(self, move_index):
        """
        Navigates the Battle Menu.
        Assumes cursor starts at 'FIGHT' (Top-Left of main menu).
        """
        # Step 1: Select 'FIGHT'
        self._press_button('A')
        self._wait(30) # Wait for "Fight/Bag" menu to slide away

        # Step 2: Navigate to Move
        if move_index == 1: # Top-Right
            self._press_button('RIGHT')
        elif move_index == 2: # Bottom-Left
            self._press_button('DOWN')
        elif move_index == 3: # Bottom-Right
            self._press_button('DOWN') 
            self._wait(5) 
            self._press_button('RIGHT')

        self._wait(5) 

        # Step 3: Confirm Move
        self._press_button('A')

    def _press_button(self, btn_name, hold_frames=4):
        """
        Presses a button for `hold_frames` and then releases.
        """
        action_arr = np.zeros(12, dtype=np.int8)
        action_arr[self.btn_indices[btn_name]] = 1
        
        for _ in range(hold_frames):
            self.env.step(action_arr)
            
        no_op = np.zeros(12, dtype=np.int8)
        for _ in range(4):
            self.env.step(no_op)

    def _wait(self, frames):
        no_op = np.zeros(12, dtype=np.int8)
        for _ in range(frames):
            self.env.step(no_op)

def make_env():
    env = retro.make(game='PokemonEmerald-GBA', state='BattleLevel5')
    env = EmeraldBattleWrapper(env)
    return Monitor(env)

def main():
    models_dir = "models/PPO"
    log_dir = "logs"
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    env = SubprocVecEnv([make_env for _ in range(4)]) 
    
    model = PPO(
        "MlpPolicy", 
        env, 
        verbose=1, 
        tensorboard_log=log_dir,
        learning_rate=0.0003,
        n_steps=512,
        batch_size=64
    )
    
    print("Starting Training...")
    model.learn(total_timesteps=50_000, progress_bar=True)
    model.save(f"{models_dir}/emerald_battle_v1")
    print("Training Complete. Model saved.")

if __name__ == "__main__":
    main()