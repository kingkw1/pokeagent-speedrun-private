# RL Battle Bot Implementation Plan

**Status:** Paused (Skeleton Implemented)
**Current Mode:** Heuristic (Rule-Based)

## Overview
We have trained a prototype PPO agent (`emerald_curriculum_v1`) capable of winning basic battles. To ensure stability for the immediate "Memory Layer" sprint, we are currently running on a `HeuristicBattleAgent`. The architecture supports hot-swapping to the `RLBattleAgent` via a config toggle.

## Architecture: The "Battle Router"
The system uses a Strategy Pattern in `agent/combat/battle_manager.py`:
- **Heuristic Agent:** Rule-based logic (Type matching, HP checks). Reliable, deterministic.
- **RL Agent:** Neural network (Masked PPO). Adaptive, potentially optimal.

## Remaining Steps to Activation

### 0. Updating the Main Agent (`agent/__init__.py`)

Update the `Agent` class to initialize this system and use the "Early Exit."

**In `agent/__init__.py`:**

```python
# ... imports ...
from .combat.battle_manager import BattleManager  # <--- NEW IMPORT

class Agent:
    def __init__(self, args=None):
        # ... existing init ...
        
        # Initialize Combat System
        # We pass a config dict to toggle RL if needed
        combat_config = {'use_rl_combat': False} 
        self.battle_manager = BattleManager(combat_config)
        print(f"   Combat System: Initialized (Mode: { 'RL' if combat_config['use_rl_combat'] else 'Heuristic' })")

    def step(self, game_state):
        # ... existing setup ...
        
        state_data = { ... } # (Your existing state extraction)
        
        # ============================================================
        # ⚔️ BATTLE FAST LANE (EARLY EXIT)
        # ============================================================
        # Check if we are in battle. If so, bypass VLM entirely.
        in_battle = state_data.get('game', {}).get('in_battle', False)
        
        if in_battle:
            # print("⚔️ BATTLE MODE: Using BattleManager (No VLM)")
            
            # 1. Get Move Index (0-3)
            action_idx = self.battle_manager.get_action(state_data)
            
            # 2. Map Index to Button (Simple mapping for now)
            # 0=TopLeft, 1=TopRight, 2=BotLeft, 3=BotRight
            # You will need your macro logic here to navigate the menu
            # For now, we return the abstract action index, or map it if simple
            
            # NOTE: To fully implement 60FPS battles, you need the 
            # 'macro' logic to navigate the menu. 
            # For now, we can return a placeholder or the raw button if your 
            # client supports it.
            
            # Let's assume we return a special flag or the raw button if mapped
            return {'action': ['A'], 'battle_move_index': action_idx} 

        # ... proceed to perception_step ...

```

### 1. Model Deployment
- **Task:** Move the trained model file.
- **Source:** `models/PPO_Masked/emerald_curriculum_v1.zip`
- **Destination:** `agent/combat/models/emerald_curriculum_v1.zip`
- **Action:** Ensure the file is tracked (or git-ignored if large) and accessible to the package.

### 2. Observation Alignment
- **Task:** Verify `RLBattleAgent._make_observation()` matches `train.py`.
- **Critical Check:** Ensure normalization factors (e.g., `/ 20.0`) and Pokedex IDs match exactly between Training and Inference.
- **Validation:** Run `agent/combat/rl_agent.py` as a standalone script to unit test the observation builder against mock inputs.

### 3. The Toggle Switch
- **File:** `run.py` or `agent/__init__.py`
- **Action:** Change `use_rl=False` to `use_rl=True` in `BattleManager` initialization.

### 4. Advanced: Hybrid Routing
- **Future Goal:** Use RL for wild encounters, Heuristic for Gym Leaders.
- **Implementation:** Update `BattleManager.get_action()` to check `state_data['enemy_species']` or `state_data['is_trainer_battle']` before delegating.