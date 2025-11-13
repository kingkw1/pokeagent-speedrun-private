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
        self._run_attempts = 0  # Track how many times we've tried to run (escape can fail)
        self._dialogue_history = []  # Track recent dialogue to detect trainer battles
        self._post_battle_dialogue = False  # Track if we're in post-battle dialogue
        self._battle_start_tile = None  # Track the tile type when battle started (for wild detection)
        logger.info("🥊 [BATTLE BOT] Initialized with wild/trainer differentiation")
    
    def should_handle(self, state_data: Dict[str, Any]) -> bool:
        """
        Determines if the battle bot should be active.
        
        Returns True if:
        - Currently in battle, OR
        - In post-battle dialogue (battle just ended but dialogue still showing)
        
        Args:
            state_data: Current game state
            
        Returns:
            True if should handle, False otherwise
        """
        game_data = state_data.get('game', {})
        in_battle = game_data.get('in_battle', False)
        
        # Check if we're in post-battle dialogue
        latest_observation = state_data.get('latest_observation', {})
        visual_data = latest_observation.get('visual_data', {})
        on_screen_text = visual_data.get('on_screen_text', {})
        dialogue_text = on_screen_text.get('raw_dialogue', '') or on_screen_text.get('dialogue', '')
        dialogue_lower = dialogue_text.lower() if dialogue_text else ''
        
        post_battle_indicators = [
            "fainted",        # "Foe TORCHIC fainted!"
            "gained",         # "TREECKO gained 69 EXP Points!"
            "grew to",        # "TREECKO grew to LV. 6!"
            "learned",        # "TREECKO learned ABSORB!"
            "defeated",       # "Player defeated TRAINER MAY!"
            "got 300",        # "CASEY got 300 for winning!"
            "got away",       # "Got away safely!"
        ]
        
        is_post_battle_dialogue = any(indicator in dialogue_lower for indicator in post_battle_indicators)
        
        if in_battle and not self._battle_started:
            # New battle started - capture the tile we were on when battle began
            self._battle_started = True
            self._post_battle_dialogue = False
            
            # Store the tile type when battle started (for wild battle detection)
            player_data = state_data.get('player', {})
            self._battle_start_tile = player_data.get('current_tile_behavior', 'UNKNOWN')
            logger.info(f"🥊 [BATTLE BOT] New battle started on tile: {self._battle_start_tile}")
            
            battle_type = self._detect_battle_type(state_data)
            if battle_type != BattleType.UNKNOWN:
                logger.info(f"🥊 [BATTLE BOT] New battle detected - Type: {battle_type.value}")
            else:
                logger.info(f"🥊 [BATTLE BOT] New battle detected - Type not yet determined (early phase)")
        elif not in_battle and self._battle_started:
            # Battle flag cleared but we might still be in post-battle dialogue
            if is_post_battle_dialogue:
                self._post_battle_dialogue = True
                logger.info(f"🥊 [BATTLE BOT] Battle ended, now in post-battle dialogue")
            else:
                # Fully out of battle
                logger.info(f"🥊 [BATTLE BOT] Battle completely done - Type was: {self._current_battle_type.value}, Run attempts: {self._run_attempts}")
                self._battle_started = False
                self._post_battle_dialogue = False
                self._current_battle_type = BattleType.UNKNOWN
                self._run_attempts = 0
                self._dialogue_history = []
                self._battle_start_tile = None
        elif self._post_battle_dialogue and not is_post_battle_dialogue:
            # Post-battle dialogue finished
            logger.info(f"🥊 [BATTLE BOT] Post-battle dialogue finished, releasing control")
            self._battle_started = False
            self._post_battle_dialogue = False
            self._current_battle_type = BattleType.UNKNOWN
            self._run_attempts = 0
            self._dialogue_history = []
            self._battle_start_tile = None
        
        # Handle if in battle OR in post-battle dialogue
        should_handle = in_battle or self._post_battle_dialogue
        if should_handle and not in_battle and self._post_battle_dialogue:
            logger.info(f"🥊 [BATTLE BOT] Handling post-battle dialogue")
        
        return should_handle
    
    def _detect_battle_type(self, state_data: Dict[str, Any]) -> BattleType:
        """
        Detect whether this is a wild or trainer battle.
        
        Detection Priority (Terrain-First Approach):
        1. TERRAIN CHECK: If battle started in tall grass → assume WILD (guilty until proven innocent)
        2. DIALOGUE OVERRIDE: Check for trainer indicators ("TRAINER", "Foe", "can't escape") → switch to TRAINER
        3. MEMORY FLAGS: Fallback to battle type flags if still unknown
        
        This implements a "default to wild in grass" strategy with trainer override.
        
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
        
        # PRIORITY 1: Check if battle started in tall grass → assume WILD
        grass_tiles = ['TALL_GRASS', 'LONG_GRASS', 'SHORT_GRASS']
        if self._battle_start_tile in grass_tiles:
            # Default assumption: battle in grass = wild battle
            assumed_type = BattleType.WILD
            logger.info(f"🌿 [BATTLE TYPE] Battle started in {self._battle_start_tile} → assuming WILD (will check for trainer override)")
        else:
            # Not in grass - unknown until we find evidence
            assumed_type = BattleType.UNKNOWN
            logger.info(f"📍 [BATTLE TYPE] Battle started on {self._battle_start_tile} → type unknown (waiting for evidence)")
        
        # PRIORITY 2: Check dialogue for TRAINER indicators (overrides terrain assumption)
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
        dialogue_combined = ' '.join(self._dialogue_history).lower()
        current_dialogue_lower = dialogue_text.lower() if dialogue_text else ''
        all_dialogue = (current_dialogue_lower + ' ' + dialogue_combined).strip()
        
        # Trainer battle indicators (these OVERRIDE terrain assumption)
        trainer_keywords = [
            "trainer",           # "Trainer sent out" or "Trainer may sent out"
            "being a trainer",   # "I'll give you a taste of what being a TRAINER is like"
            "sent out",          # Trainers "send out" Pokemon (e.g., "Trainer may sent out Torchic!")
            "no running from",   # "No! There's no running from a TRAINER BATTLE!"
            "can't escape",      # Alternative phrasing
            "foe ",              # "Foe TORCHIC" (trainer battles use "Foe" prefix)
        ]
        
        # CRITICAL: If we see trainer indicators, override terrain assumption
        has_trainer_evidence = any(keyword in all_dialogue for keyword in trainer_keywords)
        
        if has_trainer_evidence:
            self._current_battle_type = BattleType.TRAINER
            logger.info(f"⚔️ [BATTLE TYPE] TRAINER BATTLE detected via dialogue (overriding terrain assumption)")
            logger.info(f"   Dialogue evidence: '{all_dialogue[:100]}'")
            print(f"⚔️ [BATTLE TYPE] TRAINER BATTLE - Fighting to win! (dialogue override)")
            return BattleType.TRAINER
        
        # If we have a terrain-based assumption and no trainer evidence, use it
        if assumed_type != BattleType.UNKNOWN:
            self._current_battle_type = assumed_type
            logger.info(f"✅ [BATTLE TYPE] {assumed_type.value.upper()} BATTLE (based on terrain: {self._battle_start_tile})")
            if assumed_type == BattleType.WILD:
                print(f"🏃 [BATTLE TYPE] WILD BATTLE - Will run away! (in grass)")
            return assumed_type
        
        # PRIORITY 3: Check memory flags (fallback if terrain + dialogue inconclusive)
        battle_phase = battle_info.get('battle_phase', 0)
        battle_phase_name = battle_info.get('battle_phase_name', 'unknown')
        
        # Battle type flags are only valid after initialization
        if battle_phase >= 2:
            battle_type_flags = battle_info.get('battle_type_flags', 0)
            is_trainer = battle_info.get('is_trainer_battle', False)
            is_wild = battle_info.get('is_wild_battle', False)
            
            logger.info(f"🔍 [BATTLE TYPE] Checking memory flags - Phase: {battle_phase_name}, Flags: 0x{battle_type_flags:04X}, Trainer: {is_trainer}, Wild: {is_wild}")
            
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
            logger.info(f"⏳ [BATTLE TYPE] Battle phase {battle_phase} ({battle_phase_name}) - waiting for flags")
        
        # Still unknown
        self._current_battle_type = BattleType.UNKNOWN
        logger.warning(f"⚠️ [BATTLE TYPE] Could not determine battle type yet")
        return BattleType.UNKNOWN
    
    def _detect_battle_menu_state(self, state_data: Dict[str, Any]) -> str:
        """
        Detect which battle menu/state we're in.
        
        Returns:
            - "dialogue": In battle dialogue (need to press A)
            - "base_menu": At main battle menu (FIGHT/BAG/POKEMON/RUN)
            - "fight_menu": In move selection
            - "bag_menu": In bag menu
            - "unknown": Cannot determine
        """
        # Extract dialogue text from latest_observation (where VLM perception puts it)
        latest_observation = state_data.get('latest_observation', {})
        visual_data = latest_observation.get('visual_data', {})
        on_screen_text = visual_data.get('on_screen_text', {})
        
        # Safely get dialogue text
        dialogue_text = on_screen_text.get('raw_dialogue', '') or on_screen_text.get('dialogue', '')
        dialogue_lower = dialogue_text.lower() if dialogue_text else ''
        
        # Get battle phase info
        game_data = state_data.get('game', {})
        battle_info = game_data.get('battle_info', {})
        battle_phase = battle_info.get('battle_phase', 0)
        battle_phase_name = battle_info.get('battle_phase_name', 'unknown')
        
        # DEBUG: Log what we're checking
        logger.debug(f"🔍 [MENU DETECT] dialogue_text='{dialogue_text[:50] if dialogue_text else 'EMPTY'}...', phase={battle_phase}, phase_name={battle_phase_name}")
        print(f"🔍 [MENU DETECT] dialogue='{dialogue_text[:30] if dialogue_text else 'EMPTY'}', phase={battle_phase}, name={battle_phase_name}")
        
        # Check for dialogue indicators (battle intro/outro, move effects, etc.)
        dialogue_indicators = [
            "wild",           # "Wild POOCHYENA appeared!"
            "appeared",       # Wild Pokemon appear
            "go!",            # "Go! TREECKO!"
            "sent out",       # "Trainer sent out..."
            "used",           # "POOCHYENA used TACKLE!"
            "fainted",        # "Foe POOCHYENA fainted!"
            "got away",       # "Got away safely!"
            "can't escape",   # "Can't escape!" (trainer battle)
            "couldn't get",   # "Couldn't get away!" (failed wild escape)
            "gained",         # EXP gained
            "grew to",        # Level up
            "learned",        # Learned new move
        ]
        
        if any(indicator in dialogue_lower for indicator in dialogue_indicators):
            logger.info(f"🔍 [MENU STATE] DIALOGUE detected: '{dialogue_text[:60]}'")
            return "dialogue"
        
        # Check for fight menu (move selection with PP displayed)
        if ("pp" in dialogue_lower or "type/" in dialogue_lower) and \
           ("pound" in dialogue_lower or "leer" in dialogue_lower or "absorb" in dialogue_lower):
            logger.info(f"🔍 [MENU STATE] FIGHT_MENU detected: '{dialogue_text[:60]}'")
            return "fight_menu"
        
        # Check for base battle menu prompt
        if "what will" in dialogue_lower and "do?" in dialogue_lower:
            logger.info(f"🔍 [MENU STATE] BASE_MENU detected: '{dialogue_text[:60]}'")
            return "base_menu"
        
        # Check for bag menu
        if "cancel" in dialogue_lower or "close bag" in dialogue_lower:
            logger.info(f"🔍 [MENU STATE] BAG_MENU detected: '{dialogue_text[:60]}'")
            return "bag_menu"
        
        # ENHANCED FALLBACK: If battle phase >= 3 and no dialogue, assume base menu
        # This handles cases where VLM doesn't return the "What will X do?" text
        if battle_phase >= 3 and not dialogue_text:
            logger.info(f"🔍 [MENU STATE] BASE_MENU (fallback) - Phase {battle_phase}, no dialogue")
            return "base_menu"
        
        # Check battle phase name for action selection
        if battle_phase_name and 'action' in battle_phase_name.lower():
            logger.info(f"🔍 [MENU STATE] BASE_MENU detected via phase name: {battle_phase_name}")
            return "base_menu"
        
        # Unknown state
        logger.info(f"🔍 [MENU STATE] UNKNOWN: dialogue='{dialogue_text[:60]}', phase={battle_phase_name}")
        return "unknown"
    
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
            in_battle = game_data.get('in_battle', False)
            
            # If we're in post-battle dialogue (not in_battle but should_handle returned True),
            # just advance dialogue
            if not in_battle and self._post_battle_dialogue:
                logger.info("💬 [BATTLE BOT] Post-battle dialogue - pressing A to advance")
                print("💬 [BATTLE BOT] Advancing post-battle dialogue")
                return "ADVANCE_BATTLE_DIALOGUE"
            
            if not battle_info:
                logger.warning("⚠️ [BATTLE BOT] No battle_info in state - cannot decide")
                return None
            
            # Ensure we have detected battle type
            if self._current_battle_type == BattleType.UNKNOWN:
                self._detect_battle_type(state_data)
            
            # If still UNKNOWN (e.g., early battle phase), advance dialogue to gather more info
            if self._current_battle_type == BattleType.UNKNOWN:
                logger.info("⏳ [BATTLE BOT] Battle type not yet determined - advancing dialogue")
                print("⏳ [BATTLE BOT] Type unknown - advancing dialogue")
                return "ADVANCE_BATTLE_DIALOGUE"
            
            # Detect which menu/state we're in
            menu_state = self._detect_battle_menu_state(state_data)
            
            # DEBUG: Log what we detected
            logger.info(f"🔍 [BATTLE BOT DEBUG] Battle type: {self._current_battle_type.name}, Menu state: {menu_state}")
            print(f"🔍 [BATTLE BOT] Type={self._current_battle_type.name}, Menu={menu_state}")
            
            # CRITICAL: Check for "no running from a trainer" message (recovery from misdetection)
            latest_observation = state_data.get('latest_observation', {})
            visual_data = latest_observation.get('visual_data', {})
            on_screen_text = visual_data.get('on_screen_text', {})
            dialogue_text = on_screen_text.get('raw_dialogue', '') or on_screen_text.get('dialogue', '')
            dialogue_lower = dialogue_text.lower() if dialogue_text else ''

            if "no! there's" in dialogue_lower:
                # We tried to run from a trainer battle! Correct the battle type
                logger.warning("⚠️ [BATTLE BOT ERROR RECOVERY] Detected 'no running from' message - correcting to TRAINER battle")
                print("⚠️ [BATTLE BOT] ERROR RECOVERY: This is a TRAINER battle, switching to fight mode!")
                self._current_battle_type = BattleType.TRAINER
                # Need to dismiss this message first, then we'll fight
                return "RECOVER_FROM_RUN_FAILURE"
            
            # If in dialogue, advance it
            if menu_state == "dialogue":
                logger.info("💬 [BATTLE BOT] In battle dialogue - pressing A to advance")
                print("💬 [BATTLE BOT] Advancing dialogue")
                return "ADVANCE_BATTLE_DIALOGUE"
            
            # WILD BATTLE STRATEGY: Keep trying to run
            if self._current_battle_type == BattleType.WILD:
                # Check if we got the "Couldn't get away!" message
                
                if "couldn't get" in dialogue_lower or "can't escape" in dialogue_lower:
                    self._run_attempts += 1
                    logger.info(f"⚠️ [BATTLE BOT] Escape failed! Attempt #{self._run_attempts} - will try again")
                    print(f"⚠️ [BATTLE BOT] Escape failed (attempt #{self._run_attempts}) - trying again")
                
                # Navigate based on current menu state
                if menu_state == "base_menu":
                    # At "What will [POKEMON] do?" - navigate to RUN
                    # From FIGHT (default): DOWN → RIGHT → A
                    logger.info("🏃 [BATTLE BOT] At base menu - navigating to RUN")
                    print(f"🏃 [BATTLE BOT] Selecting RUN (attempt #{self._run_attempts + 1})")
                    return "SELECT_RUN"  # Special action for navigating DOWN → RIGHT → A
                
                elif menu_state == "fight_menu":
                    # Accidentally entered fight menu - press B to go back
                    logger.info("🏃 [BATTLE BOT] In fight menu - pressing B to return")
                    print("🏃 [BATTLE BOT] Exiting fight menu")
                    return "PRESS_B"
                
                elif menu_state == "bag_menu":
                    # Accidentally entered bag menu - press B to go back
                    logger.info("🏃 [BATTLE BOT] In bag menu - pressing B to return")
                    print("🏃 [BATTLE BOT] Exiting bag menu")
                    return "PRESS_B"
                
                else:
                    # Unknown state - press A to advance (might be dialogue we didn't detect)
                    logger.info(f"🏃 [BATTLE BOT] Unknown menu state - pressing A")
                    print("🏃 [BATTLE BOT] Advancing (unknown state)")
                    return "ADVANCE_BATTLE_DIALOGUE"
            
            # TRAINER BATTLE STRATEGY: Fight to win
            elif self._current_battle_type == BattleType.TRAINER:
                # Navigate based on current menu state
                if menu_state == "base_menu":
                    # At "What will [POKEMON] do?" - select FIGHT
                    logger.info("⚔️ [BATTLE BOT] At base menu - selecting FIGHT")
                    print("⚔️ [BATTLE BOT] Selecting FIGHT")
                    return "SELECT_FIGHT"  # Just press A (FIGHT is default selection)
                
                elif menu_state == "fight_menu":
                    # In fight menu - select first move
                    player_pokemon = battle_info.get('player_pokemon', {})
                    opponent_pokemon = battle_info.get('opponent_pokemon', {})
                    
                    if not player_pokemon:
                        logger.warning("⚠️ [BATTLE BOT] No player_pokemon in battle_info")
                        return "USE_MOVE_1"
                    
                    # Log battle status
                    player_species = player_pokemon.get('species', 'Unknown')
                    player_hp = player_pokemon.get('current_hp', 0)
                    player_max_hp = player_pokemon.get('max_hp', 1)
                    player_hp_percent = (player_hp / player_max_hp * 100) if player_max_hp > 0 else 0
                    
                    opp_species = opponent_pokemon.get('species', 'Unknown') if opponent_pokemon else 'Unknown'
                    
                    logger.info(f"⚔️ [BATTLE BOT] In fight menu: {player_species} ({player_hp_percent:.1f}% HP) vs {opp_species}")
                    print(f"⚔️ [BATTLE BOT] Selecting move vs {opp_species}")
                    
                    # TODO: Implement type effectiveness checking
                    # For now, use simple move selection: first damaging move
                    return "USE_MOVE_1"
                
                elif menu_state == "bag_menu":
                    # Accidentally entered bag - go back
                    logger.info("⚔️ [BATTLE BOT] In bag menu - pressing B to return")
                    return "PRESS_B"
                
                else:
                    # Unknown state or dialogue - advance
                    logger.info("⚔️ [BATTLE BOT] Advancing dialogue/unknown state")
                    return "ADVANCE_BATTLE_DIALOGUE"
            
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
