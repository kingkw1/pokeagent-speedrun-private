from .heuristic_agent import HeuristicBattleAgent
from .rl_agent import RLBattleAgent

class BattleManager:
    """
    The Router that decides WHICH brain controls the fight.
    """
    def __init__(self, config=None):
        self.use_rl = False  # <--- THE TOGGLE (Default: False)
        
        if config and config.get('use_rl_combat'):
            self.use_rl = True
            
        self.heuristic = HeuristicBattleAgent()
        
        # Initialize RL agent (lazy load or eager load)
        self.rl_bot = None
        if self.use_rl:
            self.rl_bot = RLBattleAgent("agent/combat/models/emerald_curriculum_v1")

    def get_action(self, state_data: dict) -> int:
        """
        Delegates the decision to the active agent.
        """
        # Safety Check: If RL is requested but failed to load, fallback
        if self.use_rl and self.rl_bot and self.rl_bot.model:
            return self.rl_bot.get_action(state_data)
            
        # Default Fallback
        return self.heuristic.get_action(state_data)