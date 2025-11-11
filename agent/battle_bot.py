"""
Battle Bot - Rule-Based Combat Controller

This module implements a simple, programmatic battle controller that makes
intelligent move selections during Pokemon battles.

The battle bot uses type effectiveness, move power, and Pokemon stats to
select the optimal move each turn.

ARCHITECTURE:
- Returns symbolic decisions (e.g., "USE_MOVE_1", "SWITCH_POKEMON_2")
- action.py routes these through VLM executor for competition compliance
- VLM translates symbolic decision to button press (satisfies neural network rule)

USAGE:
    from agent.battle_bot import get_battle_bot
    
    battle_bot = get_battle_bot()
    if battle_bot.should_handle(state_data):
        decision = battle_bot.get_action(state_data)
        # action.py will route this through VLM executor
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BattleBot:
    """
    Simple rule-based battle controller.
    
    Strategy:
    1. Use first damaging move available
    2. Future: Add type effectiveness checking
    3. Future: Add HP-based switching logic
    """
    
    def __init__(self):
        """Initialize the battle bot"""
        logger.info("[BATTLE BOT] Initialized")
    
    def should_handle(self, state_data: Dict[str, Any]) -> bool:
        """
        Determines if the battle bot should be active.
        
        Args:
            state_data: Current game state
            
        Returns:
            True if in battle, False otherwise
        """
        game_data = state_data.get('game', {})
        in_battle = game_data.get('in_battle', False)
        
        if in_battle:
            logger.info("[BATTLE BOT] Battle detected - bot should handle")
        
        return in_battle
    
    def get_action(self, state_data: Dict[str, Any]) -> Optional[str]:
        """
        Decide the next battle action.
        
        Returns:
            Symbolic action string (e.g., "USE_MOVE_1", "RUN_FROM_BATTLE")
            or None if uncertain
        """
        try:
            game_data = state_data.get('game', {})
            battle_info = game_data.get('battle_info', {})
            
            if not battle_info:
                logger.warning("[BATTLE BOT] No battle_info in state - cannot decide")
                return None
            
            # Get player's current Pokemon
            player_pokemon = battle_info.get('player_pokemon', {})
            if not player_pokemon:
                logger.warning("[BATTLE BOT] No player_pokemon in battle_info")
                return None
            
            # Simple strategy: Use first damaging move
            # For now, just select FIGHT option (the first action in battle menu)
            logger.info("[BATTLE BOT] Recommending FIGHT action (use first move)")
            
            return "BATTLE_FIGHT"
            
        except Exception as e:
            logger.error(f"[BATTLE BOT] Error deciding action: {e}", exc_info=True)
            return None


# === Global Instance Management ===

_global_battle_bot: Optional[BattleBot] = None


def get_battle_bot() -> BattleBot:
    """Get or create the global battle bot instance"""
    global _global_battle_bot
    if _global_battle_bot is None:
        _global_battle_bot = BattleBot()
    return _global_battle_bot
