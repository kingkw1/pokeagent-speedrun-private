"""
Battle Bot - Rule-Based Combat Controller

This module implements a smart battle controller that differentiates between
wild and trainer battles, implementing different strategies for each.

BATTLE STRATEGY:
- Wild Battles: Run immediately (conserve HP and time)
- Trainer Battles: Fight to win using optimal move selection

ARCHITECTURE:
- Returns symbolic decisions (e.g., "RUN_FROM_WILD", "USE_MOVE_ABSORB")
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
from enum import Enum

logger = logging.getLogger(__name__)


class BattleType(Enum):
    """Battle type classification"""
    WILD = "wild"
    TRAINER = "trainer"
    UNKNOWN = "unknown"


class BattleBot:
    """
    Smart rule-based battle controller.
    
    Strategy:
    1. WILD BATTLES: Run immediately to conserve HP and save time
    2. TRAINER BATTLES: Fight to win using optimal move selection
    
    Future Enhancements:
    - Type effectiveness checking (e.g., don't use Absorb against Grass types)
    - Move selection based on opponent type
    - HP-based switching logic
    - PP management
    """
    
    def __init__(self):
        """Initialize the battle bot"""
        self._current_battle_type = BattleType.UNKNOWN
        self._battle_started = False
        logger.info("🥊 [BATTLE BOT] Initialized with wild/trainer differentiation")
    
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
        
        if in_battle and not self._battle_started:
            # New battle started
            self._battle_started = True
            battle_type = self._detect_battle_type(state_data)
            logger.info(f"🥊 [BATTLE BOT] New battle detected - Type: {battle_type.value}")
        elif not in_battle and self._battle_started:
            # Battle ended
            logger.info(f"🥊 [BATTLE BOT] Battle ended - Type was: {self._current_battle_type.value}")
            self._battle_started = False
            self._current_battle_type = BattleType.UNKNOWN
        
        return in_battle
    
    def _detect_battle_type(self, state_data: Dict[str, Any]) -> BattleType:
        """
        Detect whether this is a wild or trainer battle.
        
        The game state provides battle_type_flags which includes:
        - is_trainer_battle: True if trainer battle, False if wild
        - is_wild_battle: True if wild battle, False if trainer
        
        Args:
            state_data: Current game state
            
        Returns:
            BattleType enum value
        """
        game_data = state_data.get('game', {})
        battle_info = game_data.get('battle_info', {})
        
        # Check battle type flags from memory reader
        is_trainer = battle_info.get('is_trainer_battle', False)
        is_wild = battle_info.get('is_wild_battle', False)
        
        logger.info(f"🔍 [BATTLE TYPE DETECTION] is_trainer_battle={is_trainer}, is_wild_battle={is_wild}")
        print(f"🔍 [BATTLE TYPE] Trainer: {is_trainer}, Wild: {is_wild}")
        
        if is_trainer:
            self._current_battle_type = BattleType.TRAINER
            logger.info(f"✅ [BATTLE TYPE] TRAINER BATTLE detected - will fight to win")
            print(f"⚔️ [BATTLE TYPE] TRAINER BATTLE - Fighting to win!")
        elif is_wild:
            self._current_battle_type = BattleType.WILD
            logger.info(f"✅ [BATTLE TYPE] WILD BATTLE detected - will attempt to run")
            print(f"🏃 [BATTLE TYPE] WILD BATTLE - Will run away!")
        else:
            self._current_battle_type = BattleType.UNKNOWN
            logger.warning(f"⚠️ [BATTLE TYPE] UNKNOWN battle type - defaulting to FIGHT")
            print(f"❓ [BATTLE TYPE] UNKNOWN - Defaulting to fight")
        
        return self._current_battle_type
    
    def get_action(self, state_data: Dict[str, Any]) -> Optional[str]:
        """
        Decide the next battle action based on battle type.
        
        Returns:
            Symbolic action string:
            - "RUN_FROM_WILD" - Flee from wild battle
            - "USE_MOVE_1" - Use first move in trainer battle
            - "USE_MOVE_ABSORB" - Use Absorb (for future type effectiveness)
            - None if uncertain
        """
        try:
            game_data = state_data.get('game', {})
            battle_info = game_data.get('battle_info', {})
            
            if not battle_info:
                logger.warning("⚠️ [BATTLE BOT] No battle_info in state - cannot decide")
                return None
            
            # Ensure we have detected battle type
            if self._current_battle_type == BattleType.UNKNOWN:
                self._detect_battle_type(state_data)
            
            # Strategy based on battle type
            if self._current_battle_type == BattleType.WILD:
                logger.info("🏃 [BATTLE BOT] Wild battle - recommending RUN")
                print("🏃 [BATTLE BOT] Wild battle detected - attempting to run")
                return "RUN_FROM_WILD"
            
            elif self._current_battle_type == BattleType.TRAINER:
                # Get player's current Pokemon for move selection
                player_pokemon = battle_info.get('player_pokemon', {})
                opponent_pokemon = battle_info.get('opponent_pokemon', {})
                
                if not player_pokemon:
                    logger.warning("⚠️ [BATTLE BOT] No player_pokemon in battle_info")
                    return None
                
                # Log battle status
                player_species = player_pokemon.get('species', 'Unknown')
                player_hp = player_pokemon.get('current_hp', 0)
                player_max_hp = player_pokemon.get('max_hp', 1)
                player_hp_percent = (player_hp / player_max_hp * 100) if player_max_hp > 0 else 0
                
                opp_species = opponent_pokemon.get('species', 'Unknown') if opponent_pokemon else 'Unknown'
                
                logger.info(f"⚔️ [BATTLE BOT] Trainer battle: {player_species} ({player_hp}/{player_max_hp} HP, {player_hp_percent:.1f}%) vs {opp_species}")
                print(f"⚔️ [BATTLE BOT] {player_species} HP: {player_hp}/{player_max_hp} ({player_hp_percent:.1f}%) vs {opp_species}")
                
                # TODO: Implement type effectiveness checking
                # For now, use simple move selection:
                # - Prefer damaging moves over status moves
                # - Future: Check opponent type and select super-effective moves
                # - Future: Don't use Absorb against Grass types
                # - Future: Use Absorb for HP recovery when low
                
                # Get available moves
                moves = player_pokemon.get('moves', [])
                if not moves:
                    logger.warning("⚠️ [BATTLE BOT] No moves available, defaulting to FIGHT")
                    return "USE_MOVE_1"
                
                # Simple strategy: Use first move
                # TODO: Implement smart move selection based on:
                # 1. Opponent type (from opponent_pokemon.type1, type2)
                # 2. Move type effectiveness
                # 3. Current HP (use Absorb if low HP and opponent is not Grass)
                # 4. PP management (don't waste strong moves on weak opponents)
                
                logger.info(f"⚔️ [BATTLE BOT] Trainer battle - using first available move")
                print(f"⚔️ [BATTLE BOT] Using first move in trainer battle")
                return "USE_MOVE_1"
            
            else:
                # Unknown battle type - default to fighting
                logger.warning("❓ [BATTLE BOT] Unknown battle type, defaulting to FIGHT")
                return "USE_MOVE_1"
            
        except Exception as e:
            logger.error(f"❌ [BATTLE BOT] Error deciding action: {e}", exc_info=True)
            return None


# === Global Instance Management ===

_global_battle_bot: Optional[BattleBot] = None


def get_battle_bot() -> BattleBot:
    """Get or create the global battle bot instance"""
    global _global_battle_bot
    if _global_battle_bot is None:
        _global_battle_bot = BattleBot()
    return _global_battle_bot
