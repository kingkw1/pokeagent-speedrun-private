import stable_retro as retro
import gymnasium as gym
import numpy as np
import os
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.monitor import Monitor

# Define the custom environment wrapper
class EmeraldBattleWrapper(gym.Wrapper):
    def __init__(self, env):
        super().__init__(env)
        # Observation: [MyHP, EnemyHP] normalized
        self.observation_space = gym.spaces.Box(low=0, high=1, shape=(2,), dtype=np.float32)
        
        # Action: Discrete(12) matches Retro, but we only need a few buttons
        # Mapping: 0=B, 1=A, 4=Up, 5=Down, 6=Left, 7=Right
        # We can mask this or just let PPO learn to press only useful ones.
        # For simplicity, let's keep full action space for now to avoid remapping bugs.

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self.prev_my_hp = info.get('my_hp', 0)
        self.prev_enemy_hp = info.get('enemy_hp', 0)
        return self._get_obs(info), info

    def step(self, action):
        # 1. Step the env
        obs, reward, terminated, truncated, info = self.env.step(action)
        
        # 2. Extract HP
        my_hp = info.get('my_hp', 0)
        enemy_hp = info.get('enemy_hp', 0)
        
        # 3. Custom Reward Function
        # Reward = (Damage Dealt * 2) - (Damage Taken)
        damage_dealt = self.prev_enemy_hp - enemy_hp
        damage_taken = self.prev_my_hp - my_hp
        
        # Handle resets/healing (negative damage)
        if damage_dealt < 0: damage_dealt = 0
        if damage_taken < 0: damage_taken = 0
        
        reward = (damage_dealt * 2.0) - (damage_taken * 1.0)
        
        # Bonus for winning
        if enemy_hp == 0 and self.prev_enemy_hp > 0:
            reward += 10.0
            
        # Update tracking
        self.prev_my_hp = my_hp
        self.prev_enemy_hp = enemy_hp
        
        # 4. Construct Observation
        custom_obs = self._get_obs(info)
        
        return custom_obs, reward, terminated, truncated, info

    def _get_obs(self, info):
        # Normalize assuming max HP ~20 (Level 5)
        # In production, you might read MaxHP dynamically, but this works for Sim-to-Real PoC
        my_hp = info.get('my_hp', 0)
        enemy_hp = info.get('enemy_hp', 0)
        return np.array([my_hp / 20.0, enemy_hp / 20.0], dtype=np.float32)

def make_env():
    env = retro.make(game='PokemonEmerald-GBA', state='BattleLevel5')
    env = EmeraldBattleWrapper(env)
    return Monitor(env)

def main():
    # Create Directories
    models_dir = "models/PPO"
    log_dir = "logs"
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # Parallelize for speed (4 cores)
    # Windows/Mac might need num_envs=1 if SubprocVecEnv crashes
    env = SubprocVecEnv([make_env for _ in range(4)]) 
    
    # Initialize PPO
    model = PPO(
        "MlpPolicy", 
        env, 
        verbose=1, 
        tensorboard_log=log_dir,
        learning_rate=0.0003,
        n_steps=2048,
    )
    
    print("Starting Training...")
    # Train for 100k steps (short run to verify)
    model.learn(total_timesteps=100_000, progress_bar=True)
    
    # Save the artifact
    model.save(f"{models_dir}/emerald_battle_v1")
    print("Training Complete. Model saved.")

if __name__ == "__main__":
    main()
