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
        self._run_nav_step = 0  # Track position in RUN navigation sequence
        self._dialogue_history = []  # Track recent dialogue to detect trainer battles
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
            if battle_type != BattleType.UNKNOWN:
                logger.info(f"🥊 [BATTLE BOT] New battle detected - Type: {battle_type.value}")
            else:
                logger.info(f"🥊 [BATTLE BOT] New battle detected - Type not yet determined (early phase)")
        elif not in_battle and self._battle_started:
            # Battle ended - reset state
            logger.info(f"🥊 [BATTLE BOT] Battle ended - Type was: {self._current_battle_type.value}")
            self._battle_started = False
            self._current_battle_type = BattleType.UNKNOWN
            self._run_nav_step = 0  # Reset navigation sequence
            self._dialogue_history = []  # Clear dialogue history for next battle
        
        return in_battle
    
    def _detect_battle_type(self, state_data: Dict[str, Any]) -> BattleType:
        """
        Detect whether this is a wild or trainer battle.
        
        Uses multiple detection methods:
        1. Dialogue patterns: "Trainer sent out" vs "Wild X appeared"
        2. Pre-battle dialogue: Trainer challenges contain "TRAINER" keyword
        3. Memory flags: battle_type_flags (unreliable during early phases)
        
        Args:
            state_data: Current game state
            
        Returns:
            BattleType enum value
        """
        game_data = state_data.get('game', {})
        battle_info = game_data.get('battle_info', {})
        
        if not battle_info:
            logger.warning("⚠️ [BATTLE TYPE] No battle_info - cannot detect")
            return BattleType.UNKNOWN
        
        # METHOD 1: Check dialogue text for trainer battle indicators
        latest_observation = state_data.get('latest_observation', {})
        visual_data = latest_observation.get('visual_data', {})
        on_screen_text = visual_data.get('on_screen_text', {})
        dialogue_text = on_screen_text.get('raw_dialogue', '') or on_screen_text.get('dialogue', '')
        
        # Add to dialogue history (keep last 5 messages)
        if dialogue_text and dialogue_text not in self._dialogue_history:
            self._dialogue_history.append(dialogue_text)
            if len(self._dialogue_history) > 5:
                self._dialogue_history.pop(0)
        
        # Check BOTH current dialogue and dialogue history for battle type patterns
        # This catches "Wild POOCHYENA appeared!" immediately when it appears
        dialogue_combined = ' '.join(self._dialogue_history).lower()
        current_dialogue_lower = dialogue_text.lower() if dialogue_text else ''
        
        # Combine current + history for comprehensive check
        all_dialogue = (current_dialogue_lower + ' ' + dialogue_combined).strip()
        
        # Trainer battle indicators in dialogue
        trainer_keywords = [
            "trainer",           # "Trainer sent out"
            "being a trainer",   # "I'll give you a taste of what being a TRAINER is like"
            "sent out",          # Trainers "send out" Pokemon
        ]
        
        wild_keywords = [
            "wild",              # "Wild POOCHYENA appeared"
            "appeared",          # Wild Pokemon "appear"
        ]
        
        has_trainer_keywords = any(keyword in all_dialogue for keyword in trainer_keywords)
        has_wild_keywords = any(keyword in all_dialogue for keyword in wild_keywords)
        
        # Log what we're checking
        if dialogue_text:
            logger.info(f"🔍 [BATTLE TYPE] Checking dialogue: current='{dialogue_text[:80]}', combined='{all_dialogue[:100]}'")
        
        if has_trainer_keywords and not has_wild_keywords:
            self._current_battle_type = BattleType.TRAINER
            logger.info(f"✅ [BATTLE TYPE] TRAINER BATTLE detected via dialogue: '{dialogue_combined[:100]}'")
            print(f"⚔️ [BATTLE TYPE] TRAINER BATTLE - Fighting to win! (detected from dialogue)")
            return BattleType.TRAINER
        elif has_wild_keywords and not has_trainer_keywords:
            self._current_battle_type = BattleType.WILD
            logger.info(f"✅ [BATTLE TYPE] WILD BATTLE detected via dialogue: '{dialogue_combined[:100]}'")
            print(f"🏃 [BATTLE TYPE] WILD BATTLE - Will run away! (detected from dialogue)")
            return BattleType.WILD
        
        # METHOD 2: Check battle phase and memory flags (fallback)
        battle_phase = battle_info.get('battle_phase', 0)
        battle_phase_name = battle_info.get('battle_phase_name', 'unknown')
        
        # Battle type flags are only valid after initialization
        if battle_phase >= 2:
            battle_type_flags = battle_info.get('battle_type_flags', 0)
            is_trainer = battle_info.get('is_trainer_battle', False)
            is_wild = battle_info.get('is_wild_battle', False)
            
            logger.info(f"🔍 [BATTLE TYPE DETECTION] Phase: {battle_phase_name}, Flags: 0x{battle_type_flags:04X}, Trainer: {is_trainer}, Wild: {is_wild}")
            print(f"🔍 [BATTLE TYPE] Phase: {battle_phase_name}, Flags: 0x{battle_type_flags:04X}, Trainer: {is_trainer}, Wild: {is_wild}")
            
            if is_trainer:
                self._current_battle_type = BattleType.TRAINER
                logger.info(f"✅ [BATTLE TYPE] TRAINER BATTLE detected via memory flags")
                print(f"⚔️ [BATTLE TYPE] TRAINER BATTLE - Fighting to win!")
                return BattleType.TRAINER
            elif is_wild:
                self._current_battle_type = BattleType.WILD
                logger.info(f"✅ [BATTLE TYPE] WILD BATTLE detected via memory flags")
                print(f"🏃 [BATTLE TYPE] WILD BATTLE - Will run away!")
                return BattleType.WILD
        else:
            logger.info(f"⏳ [BATTLE TYPE] Battle phase {battle_phase} ({battle_phase_name}) - waiting for flags or dialogue")
            print(f"⏳ [BATTLE TYPE] Phase {battle_phase_name} - waiting for detection")
        
        # Still unknown
        self._current_battle_type = BattleType.UNKNOWN
        logger.warning(f"⚠️ [BATTLE TYPE] Could not determine battle type yet")
        return BattleType.UNKNOWN
    
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
            
            # If still UNKNOWN (e.g., early battle phase), wait for next turn
            if self._current_battle_type == BattleType.UNKNOWN:
                logger.info("⏳ [BATTLE BOT] Battle type not yet determined - waiting")
                return None
            
            # CRITICAL: Check if we're at the action selection menu
            # Battle intro shows "Wild X appeared!" and "Go! POKEMON!" dialogues
            # The menu is ready when we see:
            # 1. "What will [POKEMON] do?" - action prompt
            # 2. Move names like "POUND", "LEER" - move selection menu visible
            
            # Get dialogue text from latest_observation (perception module output)
            # Use raw_dialogue (unfiltered) because hallucination filter clears dialogue field
            latest_observation = state_data.get('latest_observation', {})
            visual_data = latest_observation.get('visual_data', {})
            on_screen_text = visual_data.get('on_screen_text', {})
            
            # Try raw_dialogue first (unfiltered), fallback to dialogue if not available
            dialogue_text = on_screen_text.get('raw_dialogue', '') or on_screen_text.get('dialogue', '')
            
            # Look for indicators that the battle menu is ready
            action_prompt_ready = False
            if dialogue_text:
                dialogue_lower = dialogue_text.lower()
                
                # Method 1: "What will POKEMON do?" action prompt
                if "what will" in dialogue_lower and "do?" in dialogue_lower:
                    action_prompt_ready = True
                    logger.info(f"✅ [BATTLE BOT] Action prompt detected: '{dialogue_text}'")
                    print(f"✅ [BATTLE BOT] Menu ready (action prompt): '{dialogue_text}'")
                
                # Method 2: Treecko's move names visible (means we're in move selection)
                # Treecko starts with POUND and LEER
                elif ("pound" in dialogue_lower or "leer" in dialogue_lower) and \
                     ("pp" in dialogue_lower or "type" in dialogue_lower):
                    action_prompt_ready = True
                    logger.info(f"✅ [BATTLE BOT] Move menu detected: '{dialogue_text[:50]}'")
                    print(f"✅ [BATTLE BOT] Menu ready (move list): '{dialogue_text[:50]}'")
            
            if not action_prompt_ready:
                # Still in intro dialogue or attack animations - press A to advance
                logger.info(f"💬 [BATTLE BOT] Battle dialogue/animation - pressing A to advance (dialogue: '{dialogue_text[:80] if dialogue_text else 'none'}')")
                print(f"💬 [BATTLE BOT] Advancing battle (current: '{dialogue_text[:50] if dialogue_text else 'none'}')")
                # Reset navigation sequence since we're not at menu yet
                self._run_nav_step = 0
                return "ADVANCE_BATTLE_DIALOGUE"
            
            # Menu is ready - proceed with strategy
            if self._current_battle_type == BattleType.WILD:
                # Navigate to RUN option in battle menu (2x2 grid, no wraparound)
                # Menu layout:  FIGHT    BAG
                #               POKEMON  RUN
                # 
                # Navigation sequence (from default FIGHT position):
                # 1. B (exit any sub-menu we might have entered)
                # 2. B (ensure we're at main battle menu)
                # 3. DOWN (move from FIGHT to POKEMON)
                # 4. RIGHT (move from POKEMON to RUN)
                # 5. A (select RUN)
                
                nav_sequence = ["B", "B", "DOWN", "RIGHT", "A"]
                
                if self._run_nav_step >= len(nav_sequence):
                    # Sequence complete - reset for next time
                    logger.info("🏃 [BATTLE BOT] RUN navigation sequence complete, resetting")
                    self._run_nav_step = 0
                    return "RUN_FROM_WILD"  # Fallback (should not reach here)
                
                current_button = nav_sequence[self._run_nav_step]
                self._run_nav_step += 1
                
                logger.info(f"🏃 [BATTLE BOT] Wild battle - RUN nav step {self._run_nav_step}/{len(nav_sequence)}: {current_button}")
                print(f"🏃 [BATTLE BOT] Navigating to RUN ({self._run_nav_step}/{len(nav_sequence)}): {current_button}")
                
                # Return special code that action.py will handle
                return f"NAV_RUN_STEP_{current_button}"
            
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
