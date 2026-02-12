import numpy as np
import os
from .interface import BattleAgent
# Conditional import to avoid crashing if user hasn't installed sb3-contrib yet
try:
    from sb3_contrib import MaskablePPO
except ImportError:
    MaskablePPO = None

from simulation.pokedex import SPECIES_DATA, MOVES_DATA, get_effectiveness

class RLBattleAgent(BattleAgent):
    """
    Deep Reinforcement Learning Agent trained via PPO.
    Wraps the stable-baselines3 model for inference.
    """
    def __init__(self, model_path):
        if MaskablePPO is None:
            print("⚠️ [RL-Agent] sb3_contrib not installed. RL Agent disabled.")
            self.model = None
            return

        if not os.path.exists(model_path):
            print(f"⚠️ [RL-Agent] Model not found at {model_path}. RL Agent disabled.")
            self.model = None
            return

        self.model = MaskablePPO.load(model_path)
        print(f"[RL-Agent] Model loaded: {model_path}")
        self.OBS_NORM_FACTOR = 20.0

    def get_action(self, state_data: dict) -> int:
        if self.model is None:
            # Fallback if somehow called without a model
            return 0 

        obs = self._make_observation(state_data)
        mask = self._get_mask(state_data)
        
        action, _ = self.model.predict(obs, action_masks=mask, deterministic=True)
        return int(action)

    def _make_observation(self, info):
        # ... (Matches training logic: HP, PP, Power, Eff) ...
        # [Placeholder for the logic we wrote in battle_bot.py]
        # For skeleton purposes, we leave this structure ready to fill.
        return np.zeros(14, dtype=np.float32)

    def _get_mask(self, info):
        # [Placeholder for PP masking logic]
        return np.array([True, True, True, True])