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

⚠️⚠️⚠️ CRITICAL WARNING - MEMORY READER LIMITATIONS ⚠️⚠️⚠️

The memory reader has SEVERE LIMITATIONS that have been proven through extensive testing:

1. opponent_pokemon: ALWAYS EMPTY {} - Never populated, not a bug, architectural limitation
   - Do NOT attempt to read opponent species from battle_info.get('opponent_pokemon')
   - Do NOT attempt to use opponent_pokemon.get('species')
   - Any code checking if opponent_pokemon is populated is DEAD CODE

2. BATTLE_COMMUNICATION: ALWAYS 175 - Never changes during entire battle
   - Do NOT attempt to use BATTLE_COMMUNICATION to detect battle phases
   - Do NOT attempt to use phase_name (always "phase_175")
   - Any code checking BATTLE_COMMUNICATION value is DEAD CODE

3. What DOES work from memory reader:
   - player_pokemon: Actually populated with HP, moves, species, status
   - in_battle: Boolean flag works correctly

4. How to get opponent information:
   - Extract from VLM dialogue: "YOUNGSTER CALVIN sent out POOCHYENA!"
   - Parse battle intro text for species name
   - Use dialogue history tracking (self._dialogue_history)
   - Cache extracted species (self._opponent_species_from_dialogue)
   - Use fuzzy string matching to handle VLM misspellings (difflib)

⚠️⚠️⚠️ END CRITICAL WARNING ⚠️⚠️⚠️

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
from difflib import get_close_matches

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
    2. TRAINER BATTLES: Fight to win using optimal move selection with type effectiveness
    
    Move Selection (Treecko):
    - ABSORB: Grass-type move - super effective vs Water/Ground/Rock
      - Use against: Zigzagoon, Wingull, Poochyena, Lotad, Nincada, Geodude, Nosepass, 
                     Ralts, Makuhita, Medite, Barboach, Whismur, Numel
      - DON'T use against: Shroomish, Taillow, Wurmple, Dustox, Masquerain, Shedinja, Torchic
    - POUND: Normal-type move - neutral damage, fallback when Absorb not effective
    
    Enhancements:
    - Type effectiveness checking based on opponent species
    - Automatic move selection (Absorb vs Pound)
    - HP-draining with Absorb reduces need for healing items
    - Fuzzy string matching to handle VLM misspellings (handles extra/missing/substituted letters)
    """
    
    # Pokemon species where Absorb is NOT effective (resistant or immune)
    # From ABSORB_EFFECTIVE_TYPES.md: Flying, Poison, Bug, Fire, Grass, Dragon, Steel types
    ABSORB_NOT_EFFECTIVE = {
        'SHROOMISH',    # Grass
        'TAILLOW',      # Flying/Normal
        'WURMPLE',      # Bug
        'DUSTOX',       # Bug/Poison
        'MASQUERAIN',   # Bug/Flying
        'SHEDINJA',     # Bug/Ghost
        'TORCHIC',      # Fire
        'CASCOON',       # Bug
        'SEEDOT',        # Grass/Normal
        'SILCOON',       # Bug
        'TREECKO',       # Grass

    }
    
    # Pokemon species where Absorb is EFFECTIVE (neutral or super effective)
    # Everything not in the above list - Water, Ground, Rock, Normal, Dark, Psychic, Fighting
    ABSORB_EFFECTIVE = {
        'ZIGZAGOON',    # Normal
        'WINGULL',      # Water/Flying (Water makes it effective despite Flying)
        'POOCHYENA',    # Dark
        'LOTAD',        # Water/Grass (Water makes it effective despite Grass)
        'NINCADA',      # Bug/Ground (Ground makes it effective despite Bug)
        'GEODUDE',      # Rock/Ground (SUPER EFFECTIVE)
        'NOSEPASS',     # Rock (SUPER EFFECTIVE)
        'RALTS',        # Psychic
        'MEDITE',       # Fighting (Meditite)
        'MEDITITE',     # Fighting (alternate spelling)
        'MARILL',       # Water/Fairy 
        'MAGIKARP',     # Water
        'MUDKIP',       # Water/Ground
        'SLAKOTH',      # Normal
    }

    def __init__(self):
        """Initialize the battle bot"""
        self._current_battle_type = BattleType.WILD  # Default to WILD - try to run, switch to TRAINER if can't
        self._battle_type_locked = False  # Lock battle type once confidently determined
        self._battle_started = False
        self._run_attempts = 0  # Track how many times we've tried to run (escape can fail)
        self._dialogue_history = []  # Track recent dialogue to detect trainer battles
        self._post_battle_dialogue = False  # Track if we're in post-battle dialogue
        self._battle_start_tile = None  # Track the tile type when battle started (for wild detection)
        self._last_overworld_tile = None  # Track the last tile we were on before battle (updated every non-battle step)
        self._was_in_battle_last_step = False  # Track previous battle state to detect transitions
        self._current_opponent = None  # Track current opponent to detect Pokemon switches
        self._unknown_state_count = 0  # Track consecutive unknown menu states (VLM hallucination detector)
        self._wild_battle_dialogue_turns = 0  # Track dialogue turns in wild battle (force base_menu after N turns)
        self._opponent_species_from_dialogue = None  # Cache opponent species extracted from "sent out" dialogue
        self._is_birch_rescue_battle = False  # Flag set ONCE at battle start for Birch rescue detection
        logger.info("🥊 [BATTLE BOT] Initialized with type-effective move selection")
    
    def should_handle(self, state_data: Dict[str, Any]) -> bool:
        """
        Determines if the battle bot should be active.
        
        Returns True if:
        - Currently in battle, OR
        - In post-battle dialogue (battle just ended but dialogue still showing)
        
        This method also tracks the last overworld tile on every step, so when a battle
        starts, we know what terrain the player was on (critical for wild vs trainer detection).
        
        Args:
            state_data: Current game state
            
        Returns:
            True if should handle, False otherwise
        """
        game_data = state_data.get('game', {})
        in_battle = game_data.get('in_battle', False)
        player_data = state_data.get('player', {})
        
        # 🔍 DEBUG: Track battle state transitions
        print(f"🔍 [BATTLE BOT SHOULD_HANDLE] in_battle={in_battle}, was_in_battle_last_step={self._was_in_battle_last_step}, _is_birch_rescue_battle={self._is_birch_rescue_battle}")
        
        # 🔍 TILE TRACKING: Update last overworld tile BEFORE checking battle state
        # This ensures we capture the tile from the step BEFORE battle started
        if not in_battle:
            # Get tile from map stitcher
            map_data = state_data.get('map', {})
            player_data = state_data.get('player', {})
            x = player_data.get('x')
            y = player_data.get('y')
            
            # Get player coordinates from map (they might be offset)
            player_coords = map_data.get('player_coords', {})
            map_x = player_coords.get('x', x)
            map_y = player_coords.get('y', y)
            
            # Try to get tile behavior from metatile_behaviors lookup
            current_tile = 'UNKNOWN'
            
            if 'tiles' in map_data and map_data['tiles'] and map_x is not None and map_y is not None:
                # tiles is a 2D list: tiles[row][col] = [tile_id, behavior, collision, elevation]
                tiles_grid = map_data['tiles']
                
                # Map coordinates might need adjustment - try to find player tile
                if 0 <= map_y < len(tiles_grid) and 0 <= map_x < len(tiles_grid[map_y]):
                    tile = tiles_grid[map_y][map_x]
                    
                    if len(tile) >= 2:
                        behavior_code = tile[1]  # behavior is at index 1
                        # Convert behavior code to name
                        try:
                            from pokemon_env.enums import MetatileBehavior
                            behavior_enum = MetatileBehavior(behavior_code)
                            current_tile = behavior_enum.name
                            logger.debug(f"✅ [TILE] At ({map_x}, {map_y}): {current_tile} (code={behavior_code})")
                        except (ValueError, ImportError) as e:
                            logger.warning(f"⚠️ [TILE] Error converting behavior code {behavior_code}: {e}")
            
            # Log tile value (only when it changes or is unknown)
            if current_tile != self._last_overworld_tile:
                logger.info(f"🌍 [TILE] Changed to: '{current_tile}' (was: '{self._last_overworld_tile}')")
            
            if current_tile != 'UNKNOWN':
                old_tile = self._last_overworld_tile
                self._last_overworld_tile = current_tile
            else:
                logger.debug(f"⚠️ [TILE] Could not determine tile behavior (map data unavailable)")
            
            # 💬 DIALOGUE TRACKING: Also track dialogue BEFORE battle starts
            # This captures important context like "I'll give you a taste of what being a TRAINER is like"
            latest_observation = state_data.get('latest_observation', {})
            visual_data = latest_observation.get('visual_data', {})
            on_screen_text = visual_data.get('on_screen_text', {})
            dialogue_text = on_screen_text.get('raw_dialogue', '') or on_screen_text.get('dialogue', '')
            
            if dialogue_text and dialogue_text not in self._dialogue_history:
                self._dialogue_history.append(dialogue_text)
                if len(self._dialogue_history) > 5:
                    self._dialogue_history.pop(0)
                logger.info(f"💬 [PRE-BATTLE DIALOGUE] Captured: '{dialogue_text[:60]}'...")
        else:
            # Also print when IN battle to see tile status
            current_tile = player_data.get('current_tile_behavior', 'UNKNOWN')
            print(f"🌍 [TILE TRACKING] IN BATTLE - current_tile_behavior: '{current_tile}', last_overworld_tile: '{self._last_overworld_tile}'")
            logger.info(f"🌍 [TILE TRACKING] IN BATTLE - not updating tile (last_overworld_tile='{self._last_overworld_tile}')")
        
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
        
        # 🆕 BATTLE START DETECTION: Check if battle just started (transition from False → True)
        if in_battle and not self._was_in_battle_last_step:
            # New battle started - use the tile from LAST STEP (before battle)
            self._battle_started = True
            self._post_battle_dialogue = False
            
            # Clear opponent species cache for new battle
            self._opponent_species_from_dialogue = None
            logger.info(f"🔄 [BATTLE START] Cleared opponent species cache")
            
            # Use the tile we were on BEFORE battle started (not current tile which is now battle screen)
            self._battle_start_tile = self._last_overworld_tile or 'UNKNOWN'
            
            # ⭐ CHECK BIRCH RESCUE BATTLE ONCE AT BATTLE START ⭐
            # This flag is set ONCE and never rechecked during the battle
            milestones_completed = game_data.get('milestones_completed', [])
            post_rescue_milestones = [
                'BIRCH_LAB_VISITED', 'OLDALE_TOWN', 'ROUTE_103', 'RIVAL_BATTLE_1',
                'RECEIVED_POKEDEX', 'ROUTE_102', 'PETALBURG_CITY', 'VISITED_DAD', 'ROUTE_104'
            ]
            has_post_rescue_milestone = any(m in milestones_completed for m in post_rescue_milestones)
            
            # CRITICAL FIX: If milestones list is empty, we can't determine if it's a rescue battle
            # Empty list likely means milestones aren't being tracked or we're past the opening.
            # Default to NOT a rescue battle (safer - allows running from wild battles).
            # Only mark as rescue battle if we have milestones AND none are post-rescue.
            if not milestones_completed:
                # No milestones data available - assume NOT rescue battle (default to WILD)
                self._is_birch_rescue_battle = False
                logger.warning(f"⚠️ [BIRCH RESCUE CHECK] Milestones list is empty - defaulting to normal battle")
                print(f"⚠️ [BATTLE START] No milestone data - treating as normal wild battle")
            else:
                # We have milestone data - check if we're in the rescue battle window
                self._is_birch_rescue_battle = not has_post_rescue_milestone
            
            # Detailed logging for debugging
            matching_milestones = [m for m in post_rescue_milestones if m in milestones_completed]
            
            logger.info(f"=" * 80)
            logger.info(f"🥊 [BATTLE START] New battle detected!")
            logger.info(f"   _last_overworld_tile: '{self._last_overworld_tile}'")
            logger.info(f"   _battle_start_tile: '{self._battle_start_tile}'")
            logger.info(f"   current_tile_behavior (in battle): '{player_data.get('current_tile_behavior', 'N/A')}'")
            logger.info(f"   All milestones completed: {milestones_completed}")
            logger.info(f"   Post-rescue milestones we check: {post_rescue_milestones}")
            logger.info(f"   Matching post-rescue milestones: {matching_milestones}")
            logger.info(f"   has_post_rescue_milestone: {has_post_rescue_milestone}")
            logger.info(f"   Is Birch rescue battle: {self._is_birch_rescue_battle}")
            logger.info(f"=" * 80)
            print(f"🥊 [BATTLE START DEBUG] Milestones: {milestones_completed}")
            print(f"🥊 [BATTLE START DEBUG] Matching: {matching_milestones}")
            print(f"🥊 [BATTLE START DEBUG] Is Birch rescue: {self._is_birch_rescue_battle}")
            
            # Log if we have no tile info (shouldn't happen, but good to catch)
            if self._battle_start_tile == 'UNKNOWN':
                logger.warning(f"⚠️ [BATTLE BOT] Battle started but no overworld tile tracked! This shouldn't happen.")
                logger.warning(f"   This likely means battle started before we captured any overworld tile.")
            
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
                self._current_battle_type = BattleType.WILD  # Reset to WILD for next battle
                self._battle_type_locked = False  # Reset lock for next battle
                self._run_attempts = 0
                self._dialogue_history = []
                self._is_birch_rescue_battle = False  # Reset for next battle
                self._battle_start_tile = None
                self._current_opponent = None  # Reset opponent tracking
                self._unknown_state_count = 0  # Reset VLM hallucination counter
                self._wild_battle_dialogue_turns = 0  # Reset wild battle dialogue counter
        elif self._post_battle_dialogue and not is_post_battle_dialogue:
            # Post-battle dialogue finished
            logger.info(f"🥊 [BATTLE BOT] Post-battle dialogue finished, releasing control")
            self._battle_started = False
            self._post_battle_dialogue = False
            self._current_battle_type = BattleType.WILD  # Reset to WILD for next battle
            self._run_attempts = 0
            self._dialogue_history = []
            self._battle_start_tile = None
            self._current_opponent = None  # Reset opponent tracking
        
        # Update battle state tracking for next step
        self._was_in_battle_last_step = in_battle
        
        # Handle if in battle OR in post-battle dialogue
        should_handle = in_battle or self._post_battle_dialogue
        if should_handle and not in_battle and self._post_battle_dialogue:
            logger.info(f"🥊 [BATTLE BOT] Handling post-battle dialogue")
        
        return should_handle
    
    def _detect_battle_type(self, state_data: Dict[str, Any]) -> BattleType:
        """
        Detect whether this is a wild or trainer battle.
        
        Detection Priority (Terrain-First Approach):
        1. SPECIAL CASE: Birch rescue battle (STARTER_CHOSEN but not BIRCH_LAB_VISITED) → FORCE FIGHT
        2. TERRAIN CHECK: If battle started in tall grass → assume WILD (guilty until proven innocent)
        3. DIALOGUE OVERRIDE: Check for trainer indicators ("TRAINER", "Foe", "can't escape") → switch to TRAINER
        4. MEMORY FLAGS: Fallback to battle type flags if still unknown
        
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
        
        # ⭐⭐⭐ SPECIAL CASE: BIRCH RESCUE BATTLE ⭐⭐⭐
        # In the opening sequence, Prof. Birch is attacked by a wild Zigzagoon on Route 101.
        # The player must battle it after choosing their starter - you CANNOT run from this battle.
        # Birch says "Don't leave me like this!" if you try to run.
        # 
        # Detection: Flag is set ONCE at battle start in should_handle() method
        # Checked using milestone completion: if no BIRCH_LAB_VISITED or later milestones, 
        # this MUST be the rescue battle (only battle possible before visiting lab).
        # 
        # The flag prevents re-checking milestones on every detection call, which was causing
        # wild battles to be incorrectly classified as trainer battles.
        
        if self._is_birch_rescue_battle:
            self._current_battle_type = BattleType.TRAINER  # Force fight
            player_data = game_data.get('player', {})
            player_loc = player_data.get('location', 'UNKNOWN')
            logger.info(f"=" * 80)
            logger.info(f"🆘 [BIRCH RESCUE BATTLE] Special scripted battle detected!")
            logger.info(f"   Location: {player_loc}")
            logger.info(f"   _is_birch_rescue_battle flag: {self._is_birch_rescue_battle}")
            logger.info(f"   This is the Zigzagoon attacking Prof. Birch - CANNOT RUN!")
            logger.info(f"   Forcing battle type to TRAINER (will fight instead of run)")
            logger.info(f"=" * 80)
            print(f"🆘 [BIRCH RESCUE] Cannot run from this battle - fighting to save Birch!")
            print(f"🆘 [BIRCH RESCUE DEBUG] Flag value: {self._is_birch_rescue_battle}")
            return BattleType.TRAINER
        else:
            # Log that this is NOT a Birch rescue battle
            logger.debug(f"✅ [BIRCH CHECK] Not Birch rescue battle (_is_birch_rescue_battle={self._is_birch_rescue_battle})")
        
        # PRIORITY 1: Check terrain - infer battle type from tile
        grass_tiles = ['TALL_GRASS', 'LONG_GRASS', 'SHORT_GRASS']
        water_tiles = ['WATER', 'POND', 'OCEAN', 'DIVE', 'SURF']
        
        logger.info(f"🔍 [BATTLE TYPE DETECT] Starting detection...")
        logger.info(f"   _battle_start_tile: '{self._battle_start_tile}'")
        
        # TILE LOGIC DISABLED - unreliable, defaults to WILD unless dialogue proves TRAINER
        assumed_type = BattleType.WILD  # SAFE DEFAULT: Try to run, fail if trainer
        logger.info(f"🌿 [BATTLE TYPE] Defaulting to WILD (tile logic disabled - safer to fail running than fight wild)")
        logger.info(f"   Tile was: '{self._battle_start_tile}' (ignored)")
        
        # PRIORITY 2: Check dialogue for TRAINER indicators (HIGHEST PRIORITY - overrides everything)
        latest_observation = state_data.get('latest_observation', {})
        visual_data = latest_observation.get('visual_data', {})
        on_screen_text = visual_data.get('on_screen_text', {})
        dialogue_text = on_screen_text.get('raw_dialogue', '') or on_screen_text.get('dialogue', '')
        
        # DEBUG: Always print what we got from perception
        print(f"🔍 [BATTLE TYPE DEBUG] dialogue_text from perception: '{dialogue_text}'")
        print(f"🔍 [BATTLE TYPE DEBUG] on_screen_text dict: {on_screen_text}")
        
        # Add to dialogue history (keep last 10 messages for Pokemon switch detection)
        # CRITICAL: Track ALL dialogue to detect when trainers switch Pokemon
        if dialogue_text:
            if dialogue_text not in self._dialogue_history:
                self._dialogue_history.append(dialogue_text)
                logger.info(f"💬 [DIALOGUE ADDED] '{dialogue_text}' (history now has {len(self._dialogue_history)} entries)")
                print(f"💬 [DIALOGUE ADDED] '{dialogue_text[:50]}'")
            else:
                logger.debug(f"💬 [DIALOGUE SKIP] Duplicate: '{dialogue_text[:50]}'")
            
            # Keep last 10 messages (increased from 5 to better track Pokemon switches)
            if len(self._dialogue_history) > 10:
                self._dialogue_history.pop(0)
        
        # Check BOTH current dialogue and dialogue history for battle type patterns
        dialogue_combined = ' '.join(self._dialogue_history).lower()
        current_dialogue_lower = dialogue_text.lower() if dialogue_text else ''
        all_dialogue = (current_dialogue_lower + ' ' + dialogue_combined).strip()
        
        logger.info(f"🔍 [BATTLE TYPE DETECT] Checking dialogue for battle type keywords...")
        logger.info(f"   Current dialogue: '{dialogue_text[:50] if dialogue_text else '(empty)'}...'")
        logger.info(f"   Dialogue history: {self._dialogue_history}")
        logger.info(f"   Combined (lowercase): '{all_dialogue[:100]}...'")
        print(f"🔍 [BATTLE TYPE DEBUG] all_dialogue: '{all_dialogue[:100]}'")
        
        # Trainer battle indicators (these OVERRIDE everything - terrain AND memory flags)
        trainer_keywords = [
            "trainer",           # "Trainer sent out" or "Trainer may sent out"
            "sent out",          # Trainers "send out" Pokemon (e.g., "Trainer may sent out Torchic!")
            "sent ",             # VLM sometimes says "sent poochyena" without "out"
            "no running from",   # "No! There's no running from a TRAINER BATTLE!"
            "can't escape",      # Alternative phrasing
            "foe ",              # "Foe TORCHIC" (trainer battles use "Foe" prefix)
        ]
        
        # Wild battle indicators (override everything if present - MOST DEFINITIVE)
        wild_keywords = [
            "wild ",             # "Wild WURMPLE appeared!" - NOTE: Space after "wild" to avoid "wildly"
        ]
        
        # CHECK WILD FIRST - most definitive indicator
        has_wild_evidence = any(keyword in all_dialogue for keyword in wild_keywords)
        print(f"🔍 [BATTLE TYPE DEBUG] Checking wild keywords: {wild_keywords}")
        print(f"🔍 [BATTLE TYPE DEBUG] has_wild_evidence: {has_wild_evidence}")
        
        if has_wild_evidence:
            self._current_battle_type = BattleType.WILD
            logger.info(f"🌿 [BATTLE TYPE] WILD BATTLE detected via dialogue (HIGHEST PRIORITY)")
            logger.info(f"   Dialogue evidence: '{all_dialogue[:100]}'")
            print(f"🏃 [BATTLE TYPE] WILD BATTLE detected from dialogue: '{dialogue_text[:50]}'")
            return BattleType.WILD
        
        # Check for trainer evidence (second priority)
        has_trainer_evidence = any(keyword in all_dialogue for keyword in trainer_keywords)
        
        if has_trainer_evidence:
            matching_keywords = [kw for kw in trainer_keywords if kw in all_dialogue]
            logger.info(f"✅ [BATTLE TYPE] Trainer keywords matched: {matching_keywords}")
            logger.info(f"   All dialogue: '{all_dialogue[:100]}...'")
            print(f"🔍 [BATTLE TYPE DEBUG] Trainer keywords matched: {matching_keywords}")
        
        if has_trainer_evidence:
            self._current_battle_type = BattleType.TRAINER
            logger.info(f"⚔️ [BATTLE TYPE] TRAINER BATTLE detected via dialogue")
            logger.info(f"   Dialogue evidence: '{all_dialogue[:100]}'")
            print(f"⚔️ [BATTLE TYPE] TRAINER BATTLE - Fighting to win! (dialogue detected)")
            return BattleType.TRAINER
        
        # If no trainer evidence found, use default assumption (WILD)
        if assumed_type != BattleType.UNKNOWN:
            self._current_battle_type = assumed_type
            logger.info(f"✅ [BATTLE TYPE] {assumed_type.value.upper()} BATTLE (default - no trainer dialogue found)")
            logger.info(f"   Tile was: '{self._battle_start_tile}' (ignored - tile logic disabled)")
            if assumed_type == BattleType.WILD:
                print(f"🏃 [BATTLE TYPE] WILD BATTLE - Will run away! (default)")
            return assumed_type
        
        # PRIORITY 3: Check memory flags (fallback if terrain + dialogue inconclusive)
        logger.info(f"🔍 [BATTLE TYPE DETECT] No terrain assumption, checking memory flags...")
        
        # Check battle type flags (if available)
        battle_type_flags = battle_info.get('battle_type_flags', 0)
        is_trainer = battle_info.get('is_trainer_battle', False)
        is_wild = battle_info.get('is_wild_battle', False)
        
        logger.info(f"🔍 [BATTLE TYPE] Checking memory flags - Flags: 0x{battle_type_flags:04X}, Trainer: {is_trainer}, Wild: {is_wild}")
        
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
        
        # No evidence found - default to WILD (try to run, will switch to TRAINER if we can't escape)
        self._current_battle_type = BattleType.WILD
        logger.warning(f"⚠️ [BATTLE TYPE] Could not determine battle type - defaulting to WILD (will run)")
        print(f"🏃 [BATTLE TYPE] WILD (default) - Will try to run!")
        return BattleType.WILD
    
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
        # First, check memory for reliable battle state info
        game_data = state_data.get('game', {})
        battle_info = game_data.get('battle_info', {})
        player_pokemon = battle_info.get('player_pokemon', {})
        opponent_pokemon = battle_info.get('opponent_pokemon', {})
        
        # Log available battle info from memory
        logger.info(f"🔍 [MENU DETECT] Memory battle_info available: player={bool(player_pokemon)}, opponent={bool(opponent_pokemon)}")
        if player_pokemon:
            player_species = player_pokemon.get('species', 'Unknown')
            player_hp = player_pokemon.get('current_hp', 0)
            player_max_hp = player_pokemon.get('max_hp', 1)
            logger.info(f"🔍 [MENU DETECT] Player: {player_species} HP={player_hp}/{player_max_hp}")
        if opponent_pokemon:
            opp_species = opponent_pokemon.get('species', 'Unknown')
            opp_hp = opponent_pokemon.get('current_hp', 0)
            opp_max_hp = opponent_pokemon.get('max_hp', 1)
            logger.info(f"🔍 [MENU DETECT] Opponent: {opp_species} HP={opp_hp}/{opp_max_hp}")
        
        # Extract dialogue text from latest_observation (where VLM perception puts it)
        latest_observation = state_data.get('latest_observation', {})
        visual_data = latest_observation.get('visual_data', {})
        on_screen_text = visual_data.get('on_screen_text', {})
        
        # Safely get dialogue text
        dialogue_text = on_screen_text.get('raw_dialogue', '') or on_screen_text.get('dialogue', '')
        dialogue_lower = dialogue_text.lower() if dialogue_text else ''
        
        # DEBUG: Log what we're checking
        logger.info(f"🔍 [MENU DETECT] VLM dialogue_text='{dialogue_text[:80] if dialogue_text else 'EMPTY'}...'")
        print(f"🔍 [MENU DETECT] dialogue='{dialogue_text[:30] if dialogue_text else 'EMPTY'}'")
        
        # Check for base battle menu prompt FIRST (most reliable)
        # Matches: "What will TREECKO do?" or "What will I do with TREECKO?" (VLM variations)
        if "what will" in dialogue_lower and ("do?" in dialogue_lower or "do with" in dialogue_lower):
            logger.info(f"✅ [MENU STATE] BASE_MENU detected: '{dialogue_text[:60]}'")
            print(f"✅ [MENU STATE] BASE_MENU - selecting FIGHT")
            return "base_menu"
        
        # Check for fight menu (move selection with PP displayed)
        # This is CRITICAL - needs to happen BEFORE general dialogue check
        # Pattern 1: Traditional "POUND PP 35/35" format
        # Pattern 2: VLM might report as "POOCHYENA: POUND, LEER, ABSORB" (listing moves)
        has_pp_display = "pp" in dialogue_lower or "type/" in dialogue_lower
        has_move_names = any(move in dialogue_lower for move in ["pound", "leer", "absorb", "tackle", "scratch"])
        # DEFENSIVE: dialogue_text might be None if VLM fails
        has_move_list_format = (dialogue_text and ":" in dialogue_text and "," in dialogue_text and has_move_names)
        
        if (has_pp_display and has_move_names) or has_move_list_format:
            logger.info(f"✅ [MENU STATE] FIGHT_MENU detected: '{dialogue_text[:60] if dialogue_text else 'N/A'}'")
            print(f"✅ [MENU STATE] FIGHT_MENU - selecting move")
            return "fight_menu"
        
        # Alternative: If we have battle_info from memory BUT VLM shows generic text,
        # we might be in the action selection phase
        # Look for visual_elements that indicate menu is showing
        visual_elements = visual_data.get('visual_elements', {})
        menu_visible = visual_elements.get('menu_visible', False)
        
        # IMPORTANT: opponent_pokemon from memory is ALWAYS EMPTY (proven useless)
        # So we check for player_pokemon ONLY (which works) + menu_visible
        # This fallback is critical when VLM hallucinates during battle animations
        if player_pokemon and menu_visible:
            logger.info(f"🔍 [MENU STATE] Have player_pokemon + menu_visible - checking for fight menu")
            # Check if we can see move names in entities or other fields
            visible_entities = visual_data.get('visible_entities', [])
            logger.info(f"🔍 [MENU DETECT] visible_entities: {visible_entities}")
            
            # If we see move-like entities, we're in fight menu
            move_indicators = ['POUND', 'LEER', 'ABSORB', 'TACKLE', 'GROWL', 'SCRATCH']
            if any(move.upper() in str(visible_entities).upper() for move in move_indicators):
                logger.info(f"✅ [MENU STATE] FIGHT_MENU detected via entities: {visible_entities}")
                print(f"✅ [MENU STATE] FIGHT_MENU - selecting move via entities")
                return "fight_menu"
        
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
            print(f"� [MENU STATE] DIALOGUE - pressing A to continue")
            return "dialogue"
        
        # Check for bag menu
        if "cancel" in dialogue_lower or "close bag" in dialogue_lower:
            logger.info(f"🔍 [MENU STATE] BAG_MENU detected: '{dialogue_text[:60]}'")
            return "bag_menu"
        
        # Unknown state - return unknown instead of guessing
        logger.warning(f"❓ [MENU STATE] UNKNOWN: dialogue='{dialogue_text[:60] if dialogue_text else 'EMPTY'}'")
        print(f"❓ [MENU STATE] UNKNOWN - pressing A as fallback")
        return "unknown"
    
    def _extract_species_from_visible_entities(self, visual_data: Dict[str, Any]) -> str:
        """
        Extract opponent species from VLM's visible_entities field.
        
        This is a FALLBACK when dialogue parsing fails. The VLM can often see
        the opponent Pokemon's name on screen even if dialogue doesn't contain it.
        
        Looks for:
        - visible_entities list containing Pokemon names
        - Filters out our own Pokemon (TREECKO, etc.)
        - Returns the first non-player Pokemon found
        
        Args:
            visual_data: VLM perception data with visible_entities
            
        Returns:
            Species name or 'Unknown' if not found
        """
        visible_entities = visual_data.get('visible_entities', [])
        
        if not visible_entities:
            logger.info("🔍 [VLM FALLBACK] No visible_entities in visual data")
            return 'Unknown'
        
        logger.info(f"🔍 [VLM FALLBACK] Checking visible_entities: {visible_entities}")
        print(f"🔍 [VLM FALLBACK] visible_entities: {visible_entities}")
        
        # Get our Pokemon species to filter out
        our_species = set()
        if hasattr(self, '_state_data'):
            party = self._state_data.get('party', [])
            our_species = {p.get('species', '').upper() for p in party if p.get('species')}
        
        # Common player Pokemon we should ignore
        player_pokemon = {'TREECKO', 'TORCHIC', 'MUDKIP', 'GROVYLE', 'COMBUSKEN', 'MARSHTOMP'}
        our_species.update(player_pokemon)
        
        # Parse visible_entities (can be list of strings or list of dicts)
        for entity in visible_entities:
            if isinstance(entity, str):
                # Simple string: "ZIGZAGOON", "ZIGZAGOON Lv4", etc.
                species = entity.upper().strip()
                # Remove level info if present
                species = species.split('LV')[0].strip()
                
                # Skip player Pokemon
                if species in our_species:
                    continue
                
                # Skip generic labels
                if species in {'PLAYER', 'TRAINER', 'YOUNGSTER', 'LASS', 'BUG', 'CATCHER'}:
                    continue
                
                # Found opponent Pokemon!
                logger.info(f"✅ [VLM FALLBACK] Found opponent from visible_entities: '{species}'")
                print(f"✅ [VLM FALLBACK] Opponent: {species}")
                return self._fix_species_name(species)
            
            elif isinstance(entity, dict):
                # Dict with name/type: {"type": "pokemon", "name": "ZIGZAGOON"}
                entity_name = entity.get('name', '').upper().strip()
                entity_type = entity.get('type', '').lower()
                
                # Remove level info
                entity_name = entity_name.split('LV')[0].strip()
                
                # Skip player Pokemon
                if entity_name in our_species:
                    continue
                
                # Skip non-Pokemon
                if entity_type in {'player', 'trainer', 'npc'}:
                    continue
                
                # Skip generic labels
                if entity_name in {'PLAYER', 'TRAINER', 'YOUNGSTER', 'LASS', 'BUG', 'CATCHER', ''}:
                    continue
                
                # Found opponent!
                logger.info(f"✅ [VLM FALLBACK] Found opponent from entity dict: '{entity_name}'")
                print(f"✅ [VLM FALLBACK] Opponent: {entity_name}")
                return self._fix_species_name(entity_name)
        
        logger.warning("⚠️ [VLM FALLBACK] No opponent Pokemon found in visible_entities")
        return 'Unknown'
    
    def _extract_opponent_species_from_dialogue(self) -> str:
        """
        Extract opponent Pokemon species from dialogue history.
        
        Looks for patterns like:
        - "YOUNGSTER CALVIN sent out POOCHYENA!"
        - "Wild ZIGZAGOON appeared!"
        - "Go! TREECKO!" (ignore - this is our pokemon)
        
        Returns:
            Species name (e.g., "POOCHYENA") or "Unknown" if not found
        
        CRITICAL: Always check the MOST RECENT dialogue first to detect Pokemon switches.
        If trainer sends out a new Pokemon, we must update the cache immediately.
        
        NEWLINE HANDLING: VLM often returns dialogue with newlines (e.g., "sent\nout").
        We normalize all dialogue by replacing newlines with spaces before pattern matching.
        """
        logger.info(f"🔍 [SPECIES EXTRACT] Searching dialogue history ({len(self._dialogue_history)} entries)")
        print(f"🔍 [SPECIES EXTRACT] Dialogue history: {[d[:40] for d in self._dialogue_history]}")
        print(f"🔍 [SPECIES EXTRACT] Cached opponent: '{self._opponent_species_from_dialogue}'")
        
        # CRITICAL: Check the most recent 3 dialogue entries FIRST for Pokemon switches
        # This ensures we detect when trainers send out new Pokemon (e.g., Zigzagoon → Shroomish)
        for i, dialogue_entry in enumerate(list(reversed(self._dialogue_history))[:3]):
            # NORMALIZE: Replace newlines with spaces to handle "sent\nout" patterns
            dialogue_normalized = dialogue_entry.replace('\n', ' ')
            dialogue_lower = dialogue_normalized.lower()
            
            # Check for "sent out" pattern (trainer switching Pokemon)
            if 'sent out' in dialogue_lower:
                logger.info(f"🔍 [SPECIES RECENT] Found 'sent out' in recent dialogue: '{dialogue_entry}'")
                
                try:
                    # Extract species name after "sent out"
                    after_sent = dialogue_normalized.lower().split('sent out')[1]
                    species = after_sent.strip(' !.').upper()
                    species_name = species.split()[0] if species.split() else 'Unknown'
                    
                    # Fix common VLM misspellings
                    species_name = self._fix_species_name(species_name)
                    
                    # Update cache with new Pokemon
                    if species_name != self._opponent_species_from_dialogue:
                        logger.info(f"🔄 [SPECIES SWITCH] Opponent changed: '{self._opponent_species_from_dialogue}' → '{species_name}'")
                        print(f"🔄 [SPECIES SWITCH] Opponent changed: '{self._opponent_species_from_dialogue}' → '{species_name}'")
                    
                    self._opponent_species_from_dialogue = species_name
                    logger.info(f"✅ [SPECIES] Current opponent: '{species_name}'")
                    print(f"✅ [SPECIES] Found opponent: {species_name}")
                    return species_name
                except Exception as e:
                    logger.warning(f"⚠️ [SPECIES] Failed to parse 'sent out' dialogue: {e}")
                    continue
        
        # If no recent "sent out", use cached value if available
        if self._opponent_species_from_dialogue:
            logger.info(f"🔍 [SPECIES CACHE] Using cached opponent: '{self._opponent_species_from_dialogue}'")
            return self._opponent_species_from_dialogue
        
        logger.info(f"🔍 [SPECIES EXTRACT] No recent 'sent out', searching full history ({len(self._dialogue_history)} entries)")
        
        # Search recent dialogue for "sent out" or "sent" pattern (trainer battles)
        for i, dialogue_entry in enumerate(reversed(self._dialogue_history)):
            # NORMALIZE: Replace newlines with spaces
            dialogue_normalized = dialogue_entry.replace('\n', ' ')
            dialogue_lower = dialogue_normalized.lower()
            logger.debug(f"  [{i}] Checking: '{dialogue_entry[:60]}'")
            
            # Pattern 1: "YOUNGSTER CALVIN sent out POOCHYENA!" (standard)
            if 'sent out' in dialogue_lower:
                logger.info(f"🔍 [SPECIES] Found 'sent out' in: '{dialogue_entry}'")
                
                # Extract species name after "sent out"
                try:
                    # Split on "sent out" and take the part after
                    after_sent = dialogue_normalized.lower().split('sent out')[1]
                    # Remove punctuation and whitespace
                    species = after_sent.strip(' !.').upper()
                    # Take first word (species name)
                    species_name = species.split()[0] if species.split() else 'Unknown'
                    
                    logger.info(f"✅ [SPECIES] Extracted: '{species_name}' from '{dialogue_entry}'")
                    print(f"✅ [SPECIES] Found opponent: {species_name}")
                    
                    # Fix common VLM misspellings
                    species_name = self._fix_species_name(species_name)
                    
                    # Cache the result
                    self._opponent_species_from_dialogue = species_name
                    return species_name
                except Exception as e:
                    logger.warning(f"⚠️ [SPECIES] Failed to parse 'sent out' dialogue: {e}")
                    continue
            
            # Pattern 2: "YOUNGSTER CALVIN sent POOCHYENA!" (VLM sometimes drops "out")
            elif ' sent ' in dialogue_lower and 'sent out' not in dialogue_lower:
                # VLM sometimes drops "out" from "sent out"
                # Just look for "sent" - trainers send out Pokemon, no need to validate trainer names
                logger.info(f"🔍 [SPECIES] Found 'sent' (without out) in: '{dialogue_entry}'")
                
                try:
                    # Split on "sent" and take the part after
                    after_sent = dialogue_normalized.lower().split(' sent ')[1]
                    # Remove punctuation and whitespace
                    species = after_sent.strip(' !.').upper()
                    # Take first word (species name)
                    species_name = species.split()[0] if species.split() else 'Unknown'
                    
                    logger.info(f"✅ [SPECIES] Extracted (no 'out'): '{species_name}' from '{dialogue_entry}'")
                    print(f"✅ [SPECIES] Found opponent: {species_name}")
                    
                    # Fix common VLM misspellings
                    species_name = self._fix_species_name(species_name)
                    
                    # Cache the result
                    self._opponent_species_from_dialogue = species_name
                    return species_name
                except Exception as e:
                    logger.warning(f"⚠️ [SPECIES] Failed to parse 'sent' dialogue: {e}")
                    continue
            
            # Pattern: "Wild ZIGZAGOON appeared!"
            if 'wild' in dialogue_lower and 'appeared' in dialogue_lower:
                logger.info(f"🔍 [SPECIES] Found 'wild appeared' in: '{dialogue_entry}'")
                
                try:
                    # Extract word between "wild" and "appeared"
                    parts = dialogue_normalized.lower().split('wild')[1].split('appeared')[0]
                    species_name = parts.strip(' !.').upper()
                    
                    logger.info(f"✅ [SPECIES] Extracted wild: '{species_name}' from '{dialogue_entry}'")
                    print(f"✅ [SPECIES] Found wild: {species_name}")
                    
                    # Fix common VLM misspellings
                    species_name = self._fix_species_name(species_name)
                    
                    # Cache the result
                    self._opponent_species_from_dialogue = species_name
                    return species_name
                except Exception as e:
                    logger.warning(f"⚠️ [SPECIES] Failed to parse 'wild appeared' dialogue: {e}")
                    continue
        
        logger.warning(f"⚠️ [SPECIES] No 'sent out' or 'wild appeared' found in dialogue history")
        logger.warning(f"   Recent dialogue: {[d[:40] for d in self._dialogue_history[-5:]]}")
        return 'Unknown'
    
    def _fix_species_name(self, species: str) -> str:
        """
        Fix VLM misspellings using fuzzy string matching.
        
        Uses similarity matching to find the closest Pokemon name from our
        known lists (ABSORB_EFFECTIVE + ABSORB_NOT_EFFECTIVE).
        
        This handles:
        - Extra/missing letters: "POOOCHIENYA" vs "POOCHYENA"
        - Substituted letters: "POECHIENYA" vs "POOCHYENA"  
        - Transposed letters: "POOCHEYNA" vs "POOCHYENA"
        
        Args:
            species: Raw species name from VLM (e.g., "POOCHENNA", "POOHVENA")
            
        Returns:
            Closest matching Pokemon name from our known lists
        """
        species_upper = species.upper().strip()
        
        # Combine all known Pokemon species
        all_known_species = list(self.ABSORB_EFFECTIVE | self.ABSORB_NOT_EFFECTIVE)
        
        # Use difflib to find closest match
        # cutoff=0.6 means at least 60% similarity required
        matches = get_close_matches(species_upper, all_known_species, n=1, cutoff=0.6)
        
        if matches:
            corrected = matches[0]
            if corrected != species_upper:
                logger.info(f"🔧 [SPECIES FIX] Fuzzy matched '{species_upper}' → '{corrected}'")
                print(f"🔧 [SPELL FIX] '{species_upper}' → '{corrected}'")
            return corrected
        
        # No close match found - return original
        logger.warning(f"⚠️ [SPECIES FIX] No fuzzy match found for '{species_upper}' (tried {len(all_known_species)} known species)")
        logger.warning(f"   Known species: {sorted(all_known_species)}")
        return species_upper
    
    def _should_use_absorb(self, species: str, player_pokemon: Dict[str, Any] = None) -> bool:
        """
        Determine if Absorb should be used against this opponent.
        
        Strategy:
        - Only use ABSORB if player Pokemon is level 6+ (Treecko learns Absorb at level 6)
        - Use ABSORB against Pokemon where it's effective (neutral or super effective)
        - Use POUND against Pokemon where Absorb is not very effective
        
        Args:
            species: Name of opponent Pokemon (e.g., "POOCHYENA")
            player_pokemon: Player's Pokemon data (for level check)
            
        Returns:
            True if should use Absorb, False if should use Pound
        """
        logger.info(f"=" * 60)
        logger.info(f"🔍 [MOVE SELECT] _should_use_absorb() called with species='{species}'")
        print(f"=" * 50)
        print(f"🔍 [ANALYZING] Species = '{species}'")
        
        # Check if player Pokemon has learned Absorb (level 6+)
        if player_pokemon:
            player_level = player_pokemon.get('level', 0)
            logger.info(f"🔍 [LEVEL CHECK] Player Pokemon level: {player_level}")
            print(f"🔍 [LEVEL CHECK] Player level: {player_level}")
            
            if player_level < 6:
                logger.warning(f"⚠️ [MOVE SELECT] Player level {player_level} < 6 - Absorb not learned yet!")
                print(f"⚠️ [MOVE SELECT] Level {player_level} < 6 → No Absorb yet → POUND")
                logger.info(f"=" * 60)
                print(f"=" * 50)
                return False
            else:
                logger.info(f"✅ [LEVEL CHECK] Level {player_level} >= 6 - Absorb available")
                print(f"✅ [LEVEL CHECK] Level {player_level} - Absorb learned!")
            
            # Check if Absorb has PP remaining
            # Absorb is typically move slot 2 for Treecko (Pound is slot 1)
            moves = player_pokemon.get('moves', [])
            move_pp = player_pokemon.get('move_pp', [])
            
            logger.info(f"🔍 [PP CHECK] Moves: {moves}")
            logger.info(f"🔍 [PP CHECK] Move PP: {move_pp}")
            print(f"🔍 [PP CHECK] Moves: {moves}, PP: {move_pp}")
            
            # Find Absorb in move list
            absorb_index = -1
            for i, move in enumerate(moves):
                if move and 'ABSORB' in move.upper():
                    absorb_index = i
                    break
            
            if absorb_index >= 0 and absorb_index < len(move_pp):
                absorb_pp = move_pp[absorb_index]
                logger.info(f"🔍 [PP CHECK] Found ABSORB at index {absorb_index}, PP = {absorb_pp}")
                print(f"🔍 [PP CHECK] ABSORB PP: {absorb_pp}")
                
                if absorb_pp == 0:
                    logger.warning(f"⚠️ [MOVE SELECT] ABSORB has 0 PP - cannot use!")
                    print(f"⚠️ [MOVE SELECT] ABSORB depleted (0 PP) → POUND")
                    logger.info(f"=" * 60)
                    print(f"=" * 50)
                    return False
                else:
                    logger.info(f"✅ [PP CHECK] ABSORB has {absorb_pp} PP remaining")
                    print(f"✅ [PP CHECK] ABSORB PP: {absorb_pp} (available!)")
            else:
                logger.warning(f"⚠️ [PP CHECK] Could not find ABSORB in move list (index={absorb_index}, moves={moves})")
                print(f"⚠️ [PP CHECK] ABSORB not found in moves - using POUND")
                logger.info(f"=" * 60)
                print(f"=" * 50)
                return False
        else:
            logger.warning("⚠️ [LEVEL CHECK] No player_pokemon data - cannot verify Absorb availability")
            print("⚠️ [LEVEL CHECK] No player data - assuming Absorb not available")
            logger.info(f"=" * 60)
            print(f"=" * 50)
            return False
        
        if not species or species == 'Unknown':
            logger.warning("⚠️ [MOVE SELECT] No opponent species - defaulting to POUND")
            print(f"⚠️ [MOVE SELECT] No opponent → POUND (safe default)")
            logger.info(f"=" * 60)
            print(f"=" * 50)
            return False
        
        # Normalize species name (uppercase, strip whitespace)
        species_normalized = species.upper().strip()
        logger.info(f"🔍 [MOVE SELECT] Normalized: '{species}' → '{species_normalized}'")
        logger.info(f"🔍 [MOVE SELECT] Checking against type-effectiveness lists...")
        print(f"🔍 [NORMALIZED] '{species}' → '{species_normalized}'")
        
        # Check if in "not effective" list (use Pound instead)
        logger.info(f"🔍 [MOVE SELECT] Checking ABSORB_NOT_EFFECTIVE list: {self.ABSORB_NOT_EFFECTIVE}")
        print(f"🔍 [CHECK 1] Is '{species_normalized}' in NOT_EFFECTIVE list?")
        
        if species_normalized in self.ABSORB_NOT_EFFECTIVE:
            logger.info(f"🟡 [MOVE SELECT] ✅ MATCH! {species_normalized} in ABSORB_NOT_EFFECTIVE list → Use POUND")
            logger.info(f"   Reason: This Pokemon resists Grass-type moves")
            print(f"🥊 [RESULT] YES! {species_normalized} resists Grass → POUND")
            logger.info(f"=" * 60)
            print(f"=" * 50)
            return False
        else:
            logger.info(f"🔍 [MOVE SELECT] ❌ NOT in ABSORB_NOT_EFFECTIVE list")
            print(f"🔍 [CHECK 1] NO - not in NOT_EFFECTIVE list")
        
        # Check if in "effective" list (use Absorb)
        logger.info(f"🔍 [MOVE SELECT] Checking ABSORB_EFFECTIVE list: {self.ABSORB_EFFECTIVE}")
        print(f"🔍 [CHECK 2] Is '{species_normalized}' in EFFECTIVE list?")
        
        if species_normalized in self.ABSORB_EFFECTIVE:
            logger.info(f"🟢 [MOVE SELECT] ✅ MATCH! {species_normalized} in ABSORB_EFFECTIVE list → Use ABSORB")
            logger.info(f"   Reason: Absorb is effective against this Pokemon + HP drain")
            print(f"🌿 [RESULT] YES! {species_normalized} weak to Grass → ABSORB (heal!)")
            logger.info(f"=" * 60)
            print(f"=" * 50)
            return True
        else:
            logger.info(f"🔍 [MOVE SELECT] ❌ NOT in ABSORB_EFFECTIVE list")
            print(f"🔍 [CHECK 2] NO - not in EFFECTIVE list")
        
        # Unknown Pokemon - default to Pound (conservative choice)
        logger.warning(f"⚠️ [MOVE SELECT] Unknown Pokemon '{species_normalized}' - not in either list")
        logger.warning(f"   ABSORB_NOT_EFFECTIVE ({len(self.ABSORB_NOT_EFFECTIVE)} species): {self.ABSORB_NOT_EFFECTIVE}")
        logger.warning(f"   ABSORB_EFFECTIVE ({len(self.ABSORB_EFFECTIVE)} species): {self.ABSORB_EFFECTIVE}")
        print(f"⚠️ [RESULT] Unknown Pokemon '{species_normalized}' → POUND (safe choice)")
        logger.info(f"=" * 60)
        print(f"=" * 50)
        return False
    
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
            
            # 💬 CRITICAL: Track dialogue on EVERY battle step (not just when detecting battle type)
            # This ensures we capture Pokemon switch messages like "LASS TIANA sent out SHROOMISH!"
            # Must happen BEFORE battle type lock check, so it runs regardless of lock status
            latest_observation = state_data.get('latest_observation', {})
            visual_data = latest_observation.get('visual_data', {})
            on_screen_text = visual_data.get('on_screen_text', {})
            dialogue_text = on_screen_text.get('raw_dialogue', '') or on_screen_text.get('dialogue', '')
            
            if dialogue_text:
                if dialogue_text not in self._dialogue_history:
                    self._dialogue_history.append(dialogue_text)
                    logger.info(f"💬 [DIALOGUE ADDED] '{dialogue_text}' (history now has {len(self._dialogue_history)} entries)")
                    print(f"💬 [DIALOGUE ADDED] '{dialogue_text[:50]}'")
                else:
                    logger.debug(f"💬 [DIALOGUE SKIP] Duplicate: '{dialogue_text[:50]}'")
                
                # Keep last 10 messages (increased from 5 to better track Pokemon switches)
                if len(self._dialogue_history) > 10:
                    self._dialogue_history.pop(0)
            
            # If we're in post-battle dialogue (not in_battle but should_handle returned True),
            # just advance dialogue
            if not in_battle and self._post_battle_dialogue:
                logger.info("💬 [BATTLE BOT] Post-battle dialogue - pressing A to advance")
                print("💬 [BATTLE BOT] Advancing post-battle dialogue")
                return "ADVANCE_BATTLE_DIALOGUE"
            
            if not battle_info:
                logger.warning("⚠️ [BATTLE BOT] No battle_info in state - cannot decide")
                return None
            
            # CRITICAL: Re-detect battle type ONLY if not yet locked
            # Lock ONLY when we detect TRAINER (prevents dialogue history aging from reverting TRAINER → WILD)
            # Never lock on WILD - allow WILD → TRAINER upgrade at any time
            # (Reason: WILD is default/fallback, TRAINER requires explicit evidence)
            if not self._battle_type_locked:
                logger.info("🔍 [BATTLE BOT] Battle type not locked yet - re-checking...")
                latest_battle_type = self._detect_battle_type(state_data)
                
                # Always update the current type (unless locked)
                if latest_battle_type != self._current_battle_type and latest_battle_type != BattleType.UNKNOWN:
                    logger.warning(f"⚠️ [BATTLE TYPE DETERMINATION] Type changed: {self._current_battle_type.value} → {latest_battle_type.value}")
                    print(f"⚠️ [BATTLE TYPE] Changed to {latest_battle_type.value}")
                    self._current_battle_type = latest_battle_type
                elif latest_battle_type != BattleType.UNKNOWN:
                    # Type confirmed again
                    logger.debug(f"✅ [BATTLE TYPE] Confirmed as {latest_battle_type.value}")
                    self._current_battle_type = latest_battle_type
                
                # LOCK ONLY if TRAINER detected (never lock on WILD)
                # This allows WILD (default) to upgrade to TRAINER when trainer dialogue appears
                if latest_battle_type == BattleType.TRAINER:
                    self._battle_type_locked = True
                    logger.info(f"� [BATTLE TYPE] LOCKED as TRAINER - will not change for this battle")
                    print(f"🔒 [BATTLE TYPE] Locked as TRAINER")
            else:
                logger.debug(f"🔒 [BATTLE TYPE] Locked as {self._current_battle_type.value} - skipping re-detection")
            
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
                self._battle_type_locked = True  # Lock it
                # Need to dismiss this message first, then we'll fight
                return "RECOVER_FROM_RUN_FAILURE"
            
            # CRITICAL: Check for Birch rescue battle failure message (recovery from misdetection)
            if "don't leave me" in dialogue_lower or "dont leave me" in dialogue_lower:
                # We tried to run from the Birch rescue battle! Correct the battle type
                logger.warning("⚠️ [BIRCH RESCUE ERROR RECOVERY] Detected Birch's plea - this is the scripted rescue battle!")
                print("🆘 [BIRCH RESCUE] ERROR RECOVERY: Cannot run from this battle - switching to fight mode!")
                self._current_battle_type = BattleType.TRAINER
                self._battle_type_locked = True  # Lock it
                # Need to dismiss this message first, then we'll fight
                return "RECOVER_FROM_RUN_FAILURE"
            
            # CRITICAL: Re-check for wild battle indicators in dialogue
            # Battle type might have been set to TRAINER initially (terrain=NORMAL), 
            # but dialogue now says "Wild X appeared!" - override to WILD
            if self._current_battle_type == BattleType.TRAINER and "wild " in dialogue_lower:
                logger.warning("⚠️ [BATTLE TYPE CORRECTION] Dialogue says 'Wild X' but type was TRAINER - correcting to WILD")
                print(f"🏃 [BATTLE TYPE CORRECTION] Dialogue '{dialogue_text[:50]}' indicates WILD battle - switching to RUN mode!")
                self._current_battle_type = BattleType.WILD
                # Re-detect battle type to get proper logging
                self._detect_battle_type(state_data)
            
            # Handle dialogue states - just advance with A
            # BUT: In wild battles, force base_menu assumption after seeing intro dialogue
            # (VLM often hallucinates after "Go! TREECKO!" preventing us from detecting base_menu)
            if menu_state == "dialogue":
                if self._current_battle_type == BattleType.WILD:
                    self._wild_battle_dialogue_turns += 1
                    logger.info(f"💬 [WILD BATTLE] Dialogue turn #{self._wild_battle_dialogue_turns}")
                    
                    # After 3 dialogue turns in wild battle, assume we're at base_menu
                    # Typical sequence: "Wild X appeared!" → "Go! POKEMON!" → <VLM hallucination>
                    # Force RUN attempt after intro is done
                    if self._wild_battle_dialogue_turns >= 3:
                        logger.warning(f"⚠️ [WILD BATTLE] {self._wild_battle_dialogue_turns} dialogue turns - forcing base_menu assumption")
                        print(f"🏃 [WILD BATTLE] Intro done, forcing RUN (dialogue turn #{self._wild_battle_dialogue_turns})")
                        # Override menu_state to base_menu to trigger RUN logic below
                        menu_state = "base_menu"
                    else:
                        logger.info("💬 [WILD BATTLE] Advancing intro dialogue")
                        print(f"💬 [WILD BATTLE] Advancing dialogue (turn {self._wild_battle_dialogue_turns})")
                        return "ADVANCE_BATTLE_DIALOGUE"
                else:
                    # Trainer battle - just advance dialogue normally
                    logger.info("💬 [BATTLE BOT] In dialogue - pressing A to advance")
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
                    self._unknown_state_count = 0  # Reset counter
                    logger.info("🏃 [BATTLE BOT] At base menu - navigating to RUN")
                    print(f"🏃 [BATTLE BOT] Selecting RUN (attempt #{self._run_attempts + 1})")
                    return "SELECT_RUN"  # Special action for navigating DOWN → RIGHT → A
                
                elif menu_state == "fight_menu":
                    # Accidentally entered fight menu - press B to go back
                    self._unknown_state_count = 0  # Reset counter
                    logger.info("🏃 [BATTLE BOT] In fight menu - pressing B to return")
                    print("🏃 [BATTLE BOT] Exiting fight menu")
                    return "PRESS_B"
                
                elif menu_state == "bag_menu":
                    # Accidentally entered bag menu - press B to go back
                    self._unknown_state_count = 0  # Reset counter
                    logger.info("🏃 [BATTLE BOT] In bag menu - pressing B to return")
                    print("🏃 [BATTLE BOT] Exiting bag menu")
                    return "PRESS_B"
                
                else:
                    # Unknown state - increment counter and decide strategy
                    self._unknown_state_count += 1
                    logger.warning(f"❓ [WILD BATTLE] Unknown menu state '{menu_state}' (count: {self._unknown_state_count})")
                    print(f"❓ [WILD BATTLE] Unknown state '{menu_state}' (#{self._unknown_state_count})")
                    
                    # CRITICAL: If we've been in "unknown" state for many turns AND made run attempts,
                    # this is likely a TRAINER battle misdetected as WILD
                    # (Trainer battles can't escape, so we get stuck)
                    if self._unknown_state_count >= 9 and self._run_attempts >= 2:
                        logger.error(f"🚨 [BATTLE TYPE CORRECTION] Stuck for {self._unknown_state_count} turns with {self._run_attempts} run attempts!")
                        logger.error("   This is likely a TRAINER battle misdetected as WILD - switching to FIGHT mode!")
                        print(f"🚨 [BATTLE TYPE CORRECTION] Can't escape after {self._run_attempts} attempts - this is a TRAINER battle!")
                        self._current_battle_type = BattleType.TRAINER
                        self._battle_type_locked = True
                        self._unknown_state_count = 0
                        # Now fight - will be handled on next iteration
                        return "PRESS_A_ONLY"
                    
                    # If stuck for 3+ turns, force RUN attempt (VLM likely failed)
                    if self._unknown_state_count >= 3:
                        logger.warning(f"⚠️ [WILD BATTLE] Stuck in unknown state for {self._unknown_state_count} turns!")
                        logger.warning("   VLM stuck - forcing SELECT_RUN")
                        print(f"⚠️ [WILD BATTLE] VLM broken! Forcing RUN attempt (#{self._unknown_state_count})")
                        # Increment run attempts when forcing RUN
                        self._run_attempts += 1
                        # Reset counter and force RUN selection
                        self._unknown_state_count = 0
                        return "SELECT_RUN"
                    else:
                        # First 2 unknown states - press A only (might be battle animation)
                        logger.info("❓ [WILD BATTLE] Unknown state - pressing A only (animation?)")
                        print(f"❓ [WILD BATTLE] Unknown #{self._unknown_state_count} - pressing A")
                        return "PRESS_A_ONLY"
            
            # TRAINER BATTLE STRATEGY: Fight to win
            elif self._current_battle_type == BattleType.TRAINER:
                logger.info(f"⚔️ [BATTLE BOT] Trainer battle - menu_state={menu_state}")
                print(f"⚔️ [BATTLE BOT] Trainer battle - menu_state={menu_state}")
                
                # Navigate based on current menu state
                if menu_state == "base_menu" or menu_state == "fight_menu":
                    # At "What will [POKEMON] do?" (base_menu) OR in the fight menu
                    # In both cases, we want to select a move based on type effectiveness
                    # The move selection commands (USE_MOVE_ABSORB/POUND) include full navigation from any state
                    logger.info("⚔️ [BATTLE BOT] At base/fight menu - selecting move based on type effectiveness")
                    print("⚔️ [BATTLE BOT] Selecting move")
                    self._unknown_state_count = 0  # Reset counter
                    # In fight menu - select move based on type effectiveness
                    # 
                    # ⚠️⚠️⚠️ CRITICAL WARNING - DO NOT USE MEMORY READER FOR OPPONENT DATA ⚠️⚠️⚠️
                    # Memory reader's opponent_pokemon is ALWAYS EMPTY and NEVER populated.
                    # BATTLE_COMMUNICATION is always 175 and never changes.
                    # These have been proven useless through extensive testing and logging.
                    # DO NOT attempt to use battle_info.get('opponent_pokemon') - it will ALWAYS be {}.
                    # DO NOT attempt to use BATTLE_COMMUNICATION - it's stuck at 175 forever.
                    # Any code relying on these values is DEAD CODE and will never execute.
                    # ⚠️⚠️⚠️ END CRITICAL WARNING ⚠️⚠️⚠️
                    
                    player_pokemon = battle_info.get('player_pokemon', {})
                    
                    if not player_pokemon:
                        logger.warning("⚠️ [BATTLE BOT] No player_pokemon in battle_info")
                        print("⚠️ [BATTLE BOT] No player_pokemon - defaulting to POUND")
                        return "USE_MOVE_POUND"  # Safe default
                    
                    # Log battle status
                    player_species = player_pokemon.get('species', 'Unknown')
                    player_hp = player_pokemon.get('current_hp', 0)
                    player_max_hp = player_pokemon.get('max_hp', 1)
                    player_hp_percent = (player_hp / player_max_hp * 100) if player_max_hp > 0 else 0
                    
                    # PRIORITY 1: Try VLM visible_entities (most current, reflects Pokemon switches)
                    opp_species = self._extract_species_from_visible_entities(visual_data)
                    
                    # PRIORITY 2: If VLM didn't find it, extract from dialogue history
                    if opp_species == 'Unknown':
                        logger.info("⚠️ [SPECIES] VLM visible_entities didn't find opponent - checking dialogue")
                        print("⚠️ [SPECIES] Not in visible_entities - checking dialogue")
                        opp_species = self._extract_opponent_species_from_dialogue()
                    else:
                        # VLM found the opponent - update dialogue cache to match
                        if self._opponent_species_from_dialogue != opp_species:
                            logger.info(f"🔄 [SPECIES UPDATE] VLM sees '{opp_species}', updating cache from '{self._opponent_species_from_dialogue}'")
                            print(f"🔄 [SPECIES UPDATE] VLM sees '{opp_species}' (was '{self._opponent_species_from_dialogue}')")
                            self._opponent_species_from_dialogue = opp_species
                    
                    logger.info(f"🔍 [SPECIES EXTRACTION] Final opponent: '{opp_species}'")
                    print(f"🔍 [SPECIES] Opponent = '{opp_species}'")
                    
                    logger.info(f"⚔️ [BATTLE BOT] In fight menu: {player_species} ({player_hp_percent:.1f}% HP) vs {opp_species}")
                    print(f"⚔️ [BATTLE BOT] Fight menu: {player_species} ({player_hp_percent:.0f}% HP) vs {opp_species}")
                    
                    # Log dialogue history for debugging
                    logger.info(f"📜 [DIALOGUE HISTORY] {len(self._dialogue_history)} entries:")
                    for i, d in enumerate(self._dialogue_history):
                        logger.info(f"   [{i}] {d[:80]}")
                    print(f"📜 [DIALOGUE] Last 3: {[d[:30] for d in self._dialogue_history[-3:]]}")
                    
                    # Check if opponent changed (trainer switched Pokemon)
                    if self._current_opponent != opp_species:
                        if self._current_opponent is not None:
                            logger.info(f"🔄 [BATTLE BOT] Opponent changed: {self._current_opponent} → {opp_species}")
                            print(f"🔄 [BATTLE BOT] New Pokemon! {self._current_opponent} → {opp_species}")
                        self._current_opponent = opp_species
                    
                    self._unknown_state_count = 0  # Reset counter
                    
                    # Type-effectiveness based move selection
                    logger.info(f"🎯 [MOVE DECISION] Determining move for opponent: '{opp_species}'")
                    print(f"🎯 [DECIDING] Should we use Absorb vs '{opp_species}'?")
                    
                    use_absorb = self._should_use_absorb(opp_species, player_pokemon)
                    logger.info(f"🎯 [MOVE DECISION] _should_use_absorb('{opp_species}') = {use_absorb}")
                    print(f"🎯 [DECISION] Use Absorb? {use_absorb}")
                    
                    if use_absorb:
                        logger.info(f"🌿 [BATTLE BOT] Using ABSORB vs {opp_species} (effective + HP drain)")
                        print(f"🌿 [BATTLE BOT] ABSORB → {opp_species} (drain HP!)")
                        return "USE_MOVE_ABSORB"
                    else:
                        logger.info(f"🥊 [BATTLE BOT] Using POUND vs {opp_species} (Absorb not effective)")
                        print(f"🥊 [BATTLE BOT] POUND → {opp_species} (Absorb resisted)")
                        return "USE_MOVE_POUND"
                
                elif menu_state == "bag_menu":
                    # Accidentally entered bag - go back
                    logger.info("⚔️ [BATTLE BOT] In bag menu - pressing B to return")
                    print("⏪ [BATTLE BOT] Exiting bag menu")
                    self._unknown_state_count = 0  # Reset counter
                    return "PRESS_B"
                
                elif menu_state == "dialogue":
                    # Battle dialogue - advance
                    logger.info("💬 [BATTLE BOT] Advancing battle dialogue")
                    print("💬 [BATTLE BOT] Advancing dialogue")
                    self._unknown_state_count = 0  # Reset counter
                    return "ADVANCE_BATTLE_DIALOGUE"
                
                else:
                    # Unknown state - increment counter and decide strategy
                    self._unknown_state_count += 1
                    logger.warning(f"❓ [BATTLE BOT] Unknown menu state '{menu_state}' (count: {self._unknown_state_count})")
                    print(f"❓ [BATTLE BOT] Unknown state '{menu_state}' (#{self._unknown_state_count})")
                    
                    # If we've been stuck in unknown state for 3+ turns, VLM is likely hallucinating
                    # Force navigation to fight menu as fallback
                    if self._unknown_state_count >= 5:
                        logger.warning(f"⚠️ [BATTLE BOT] Stuck in unknown state for {self._unknown_state_count} turns!")
                        logger.warning("   VLM completely stuck - forcing MOVE selection blindly")
                        print(f"⚠️ [BATTLE BOT] VLM broken! Forcing move selection (attempt #{self._unknown_state_count - 4})")
                        
                        # PRIORITY 1: Try VLM visible_entities (most current)
                        opp_species = self._extract_species_from_visible_entities(visual_data)
                        
                        # PRIORITY 2: Extract from dialogue if VLM didn't find it
                        if opp_species == 'Unknown':
                            logger.warning("⚠️ [BLIND] VLM entities failed - trying dialogue")
                            opp_species = self._extract_opponent_species_from_dialogue()
                        
                        logger.info(f"🔍 [BLIND DECISION] Opponent species: '{opp_species}'")
                        print(f"🔍 [BLIND] Opponent = '{opp_species}'")
                        
                        # Get player_pokemon for level check
                        player_pokemon = battle_info.get('player_pokemon', {})
                        
                        use_absorb = self._should_use_absorb(opp_species, player_pokemon)
                        logger.info(f"🎯 [BLIND DECISION] _should_use_absorb('{opp_species}') = {use_absorb}")
                        
                        if use_absorb:
                            logger.info(f"🌿 [BLIND SELECT] Using ABSORB vs {opp_species}")
                            print(f"🌿 [BLIND] ABSORB → {opp_species}")
                            return "USE_MOVE_ABSORB"
                        else:
                            logger.info(f"🥊 [BLIND SELECT] Using POUND vs {opp_species}")
                            print(f"🥊 [BLIND] POUND → {opp_species}")
                            return "USE_MOVE_POUND"
                    elif self._unknown_state_count >= 3:
                        logger.warning(f"⚠️ [BATTLE BOT] Stuck in unknown state for {self._unknown_state_count} turns!")
                        logger.warning("   VLM may be hallucinating - forcing move selection")
                        print(f"⚠️ [BATTLE BOT] VLM stuck! Forcing move selection (attempt #{self._unknown_state_count - 2})")
                        
                        # Get player_pokemon for level check
                        player_pokemon = battle_info.get('player_pokemon', {})
                        
                        # PRIORITY 1: Try VLM visible_entities (most current)
                        opp_species = self._extract_species_from_visible_entities(visual_data)
                        
                        # PRIORITY 2: Extract from dialogue if VLM didn't find it
                        if opp_species == 'Unknown':
                            logger.warning("⚠️ [RECOVERY] VLM entities failed - trying dialogue")
                            opp_species = self._extract_opponent_species_from_dialogue()
                        
                        use_absorb = self._should_use_absorb(opp_species, player_pokemon)
                        
                        if use_absorb:
                            logger.info(f"🌿 [RECOVERY] Using ABSORB vs {opp_species}")
                            print(f"🌿 [RECOVERY] ABSORB → {opp_species}")
                            return "USE_MOVE_ABSORB"
                        else:
                            logger.info(f"🥊 [RECOVERY] Using POUND vs {opp_species}")
                            print(f"🥊 [RECOVERY] POUND → {opp_species}")
                            return "USE_MOVE_POUND"
                    else:
                        # First 2 unknown states - just press A only (might be battle animation)
                        # DO NOT use B-A-B here - it backs out of menus!
                        logger.info("❓ [BATTLE BOT] Unknown state - pressing A only (animation?)")
                        print(f"❓ [BATTLE BOT] Unknown #{self._unknown_state_count} - pressing A")
                        return "PRESS_A_ONLY"
            
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
