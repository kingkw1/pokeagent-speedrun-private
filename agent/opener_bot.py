"""
Opener Bot - STATEFUL State Machine for Game Opening (Splits 0-4)

This module implements a STATEFUL rule-based controller that reliably handles
the deterministic opening sequence of Pokemon Emerald, from title screen through
starter selection.

===============================================================================
ARCHITECTURE OVERVIEW
===============================================================================

**State Machine Design:**
- STATEFUL: Bot remembers current state (self.current_state_name)
- Each frame, only checks transition conditions from current state
- Prevents state oscillation (e.g., S6_NAV_TO_CLOCK ↔ S8_NAV_OUT_OF_HOUSE)
- States use explicit next_state_fn to define completion criteria

**Signal Hierarchy:**
1. PRIMARY: Memory state (milestones, game_state) - 100% reliable
2. SECONDARY: Visual elements (text_box_visible) - 85% reliable  
3. TERTIARY: VLM text parsing - 60% reliable (hint only)

**State Lifecycle:**
```
Title Screen → Name Selection → House Interior → Exit House → 
Choose Starter → Exit Lab → COMPLETED
```

**COMPLETED State Behavior:**
Once STARTER_CHOSEN milestone is achieved AND player exits Birch's Lab,
the bot transitions to COMPLETED state and PERMANENTLY hands off to VLM.

The bot will NOT re-activate even if player returns to lab later. This is
intentional to prevent interference with normal gameplay after the opening.

===============================================================================
USAGE
===============================================================================

The opener_bot is called from action.py as Priority 0 (before all other logic):

```python
# In action_step():
opener_bot = get_opener_bot()
if opener_bot.should_handle(state_data, visual_data):
    action = opener_bot.get_action(state_data, visual_data)
    if action:
        return action  # Bot handles this step
# Otherwise, fall through to VLM navigation
```

Once COMPLETED, should_handle() always returns False, permanently handing off
control to the VLM-based agent.

===============================================================================
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)

# Global tracker for dismissed player monologues (shared across all functions)
# This prevents VLM hallucinations from causing infinite loops
_dismissed_monologues = set()

@dataclass
class NavigationGoal:
    """A data class to represent a navigation sub-goal for the A* Navigator."""
    x: int
    y: int
    map_location: str
    description: str
    should_interact: bool = None  # If None, infer from description keywords

@dataclass
class BotState:
    """Represents a state in the stateful opener bot state machine"""
    name: str
    description: str
    
    # Action or Goal to execute while in this state
    action_fn: Callable[[Dict[str, Any], Dict[str, Any]], Union[List[str], NavigationGoal, None]]
    
    # Transition logic - returns NEXT STATE NAME when complete, None to stay
    next_state_fn: Callable[[Dict[str, Any], Dict[str, Any]], Optional[str]]
    
    # Safety limits
    max_attempts: int = 60
    timeout_seconds: float = 180.0


class OpenerBot:
    """
    A STATEFUL state machine for the Pokemon Emerald opening sequence.
    It remembers its current state and only checks transition conditions from that state.
    """
    
    def __init__(self):
        """Initialize the stateful opener bot"""
        self.states = self._build_state_machine()
        self.current_state_name: str = 'S0_TITLE_SCREEN'  # Start at first state
        self.state_entry_time: float = time.time()
        self.state_attempt_count: int = 0
        self.last_action: Any = None
        self.state_history: List[tuple] = []
        self.initialized_state: bool = False  # Track if we've auto-detected state
        
        logger.info("[OPENER BOT] Initialized STATEFUL at state: S0_TITLE_SCREEN")
    
    def get_current_state(self) -> str:
        """Get the current state name"""
        return self.current_state_name

    def _transition_to_state(self, new_state: str):
        """Transition to a new state, resetting counters"""
        if new_state not in self.states:
            logger.error(f"[OPENER BOT] Unknown state transition: {new_state}")
            new_state = 'COMPLETED'
            
        old_state = self.current_state_name
        self.current_state_name = new_state
        self.state_entry_time = time.time()
        self.state_attempt_count = 0
        self.last_action = None
        
        logger.info(f"[OPENER BOT] 🔄 State Transition: {old_state} -> {new_state}")
        self.state_history.append((self.current_state_name, time.time(), "TRANSITION"))

    def should_handle(self, state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> bool:
        """
        Determines if the opener bot should be active.
        STATEFUL: Just checks if we're in COMPLETED state or if opener sequence is done.
        """
        print(f"🤖 [OPENER BOT SHOULD_HANDLE] Current state: {self.current_state_name}")
        
        # Check if we've completed the opener sequence
        milestones = state_data.get('milestones', {})
        starter_chosen = milestones.get('STARTER_CHOSEN', {}).get('completed', False)
        player_loc = state_data.get('player', {}).get('location', '')
        
        print(f"🤖 [OPENER BOT SHOULD_HANDLE] Starter chosen: {starter_chosen}, Player location: '{player_loc}'")
        print(f"🤖 [OPENER BOT DEBUG] 'PROFESSOR BIRCHS LAB' in player_loc: {'PROFESSOR BIRCHS LAB' in player_loc}")
        print(f"🤖 [OPENER BOT DEBUG] player_loc repr: {repr(player_loc)}")
        
        # CRITICAL FIX: Even if we're in COMPLETED state, re-activate if we're still in lab with starter
        # This handles the nicknaming sequence which happens AFTER starter is chosen
        if self.current_state_name == 'COMPLETED' and starter_chosen and 'PROFESSOR BIRCHS LAB' in player_loc:
            print(f"[OPENER BOT] REACTIVATING - In lab with starter, need to complete nickname/exit sequence!")
            # Re-detect state to handle nickname screen
            detected_state = self._detect_starting_state(state_data)
            print(f"[OPENER BOT] Re-detected state: {detected_state}")
            self._transition_to_state(detected_state)
            return True
        
        # If COMPLETED and not in the special case above, stay completed
        if self.current_state_name == 'COMPLETED':
            print(f"[OPENER BOT SHOULD_HANDLE] COMPLETED - OpenerBot permanently done. VLM will handle everything now. (Location: {player_loc})")
            return False
        
        # Check if we should transition to COMPLETED (outside lab after getting starter)
        if starter_chosen:
            if 'PROFESSOR BIRCHS LAB' not in player_loc:
                print(f"[OPENER BOT] Starter chosen and outside lab (PROFESSOR BIRCHS LAB not in '{player_loc}'). Handing off to VLM.")
                self._transition_to_state('COMPLETED')
                return False
            else:
                print(f"[OPENER BOT] Starter chosen but STILL IN LAB ('{player_loc}'). Continuing opener sequence.")
        
        print(f"🤖 [OPENER BOT SHOULD_HANDLE] Bot is ACTIVE, will handle action")
        return True  # Bot is active

    def get_action(self, state_data: Dict[str, Any], visual_data: Dict[str, Any], 
                   current_plan: str = "") -> Union[List[str], NavigationGoal, None]:
        """
        Main stateful logic loop:
        1. Check for dialogue override (yield to dialogue system)
        2. Get current state
        3. Check safety fallbacks
        4. Check if state's transition condition is met (if yes, transition)
        5. Execute current state's action
        """
        # CRITICAL: Check for active NPC dialogue FIRST
        # If dialogue is active, YIELD to dialogue detection system (Priority 1)
        # This prevents the opener bot from spamming A during actual NPC conversations
        visual_elements = visual_data.get('visual_elements', {})
        on_screen_text = visual_data.get('on_screen_text', {})
        
        # Check for REAL dialogue indicators (not player's internal monologue)
        continue_prompt_visible = visual_elements.get('continue_prompt_visible', False)
        text_box_visible = visual_elements.get('text_box_visible', False)
        dialogue_text = on_screen_text.get('dialogue', '')
        speaker = on_screen_text.get('speaker', '')
        
        # Player monologue detection - ONLY check dialogue text prefix
        # Do NOT use speaker field - unreliable (Mom talking TO Casey shows speaker="CASEY")
        is_player_monologue = (dialogue_text and dialogue_text.strip().upper().startswith('PLAYER:'))
        
        # CLOCK DIALOGUE DETECTION: Special case - don't yield on clock dialogue
        # The clock needs special handling (UP then A for Yes/No menu)
        # Let state machine transition to S7_SET_CLOCK which uses action_special_clock
        dialogue_upper = dialogue_text.upper()
        is_clock_dialogue = (
            "THE CLOCK" in dialogue_upper or
            "SET IT AND START IT" in dialogue_upper or
            "IS THIS" in dialogue_upper and "CORRECT TIME" in dialogue_upper
        )
        
        # DIALOGUE DETECTION: Yield to dialogue system if we see dialogue (and it's NOT player monologue)
        # EXCEPTION: Don't yield on clock dialogue - let state machine handle it
        is_real_dialogue = (continue_prompt_visible or text_box_visible) and not is_player_monologue and not is_clock_dialogue
        
        # DEBUG: Always log dialogue detection
        print(f"🤖 [OPENER BOT DIALOGUE CHECK] text_box={text_box_visible}, continue_prompt={continue_prompt_visible}, player_mono={is_player_monologue}, clock={is_clock_dialogue}, is_real={is_real_dialogue}")
        if dialogue_text:
            print(f"🤖 [OPENER BOT DIALOGUE CHECK] Dialogue: '{dialogue_text[:60]}'...")
        
        if is_real_dialogue:
            print(f"🤖 [OPENER BOT] YIELDING to dialogue system (speaker: {speaker}, continue_prompt: {continue_prompt_visible})")
            logger.info(f"[OPENER BOT] Dialogue active, yielding to Priority 1 dialogue detection")
            return None  # Let dialogue detection (Priority 1) handle this
        elif is_player_monologue:
            print(f"🤖 [OPENER BOT] Player monologue detected - ignoring and continuing with state logic")
        elif is_clock_dialogue:
            print(f"🤖 [OPENER BOT] Clock dialogue detected - letting state machine handle it")
            logger.info(f"[OPENER BOT] Player monologue ignored (likely VLM hallucination)")
        
        # Debug: Show what data we received
        player_pos = state_data.get('player', {}).get('position', {})
        player_loc = state_data.get('player', {}).get('location', '')
        print(f"🤖 [OPENER BOT GET_ACTION] ========================================")
        print(f"🤖 [OPENER BOT GET_ACTION] Current state: {self.current_state_name}")
        print(f"🤖 [OPENER BOT GET_ACTION] Player position: ({player_pos.get('x', '?')}, {player_pos.get('y', '?')})")
        print(f"🤖 [OPENER BOT GET_ACTION] Player location: {player_loc}")
        print(f"🤖 [OPENER BOT GET_ACTION] Attempt: {self.state_attempt_count + 1}")
        
        # AUTO-DETECT STARTING STATE on first call OR if party data just became available
        party = state_data.get('party', [])
        has_party = len(party) > 0 if party else False
        print(f"🤖 [OPENER BOT DEBUG] Party check: party={party}, has_party={has_party}, current_state={self.current_state_name}")
        force_redetect = (has_party and self.current_state_name == 'S20_INTERACT_BAG')  # Party appeared after being in S20
        print(f"🤖 [OPENER BOT DEBUG] Force redetect: {force_redetect}")
        
        if not self.initialized_state or force_redetect:
            if force_redetect:
                print(f"🤖 [OPENER BOT REDETECT] Party data now available ({len(party)} Pokemon), re-detecting state from S20")
            detected_state = self._detect_starting_state(state_data)
            if detected_state and detected_state != self.current_state_name:
                print(f"🤖 [OPENER BOT INIT] Auto-detected starting state: {detected_state}")
                self._transition_to_state(detected_state)
            self.initialized_state = True
        
        state = self.states.get(self.current_state_name)
        if not state:
            logger.error(f"[OPENER BOT] In unknown state {self.current_state_name}, completing.")
            self._transition_to_state('COMPLETED')
            return None

        logger.info(f"[OPENER BOT GET_ACTION] State description: {state.description}")

        # 1. Check Safety Fallbacks
        self.state_attempt_count += 1
        elapsed = time.time() - self.state_entry_time
        logger.info(f"[OPENER BOT GET_ACTION] Safety check: {self.state_attempt_count}/{state.max_attempts} attempts, {elapsed:.1f}/{state.timeout_seconds}s elapsed")
        
        if self.state_attempt_count > state.max_attempts or elapsed > state.timeout_seconds:
            logger.warning(f"[OPENER BOT] ⚠️ SAFETY FALLBACK: State {state.name} timed out! Handing off to VLM.")
            self._transition_to_state('COMPLETED')
            return None

        # 2. Check for State Transition
        if state.next_state_fn:
            try:
                print(f"🔍 [OPENER BOT] Checking transition for {state.name}...")
                next_state_name = state.next_state_fn(state_data, visual_data)
                print(f"🔍 [OPENER BOT] Transition result: {next_state_name}")
                if next_state_name:
                    logger.info(f"[OPENER BOT] ✅ State {state.name} transition condition MET. Moving to {next_state_name}.")
                    print(f"✅ [OPENER BOT] Transitioning from {state.name} to {next_state_name}")
                    self._transition_to_state(next_state_name)
                    # Get the NEW state after transition
                    state = self.states[self.current_state_name]
                    logger.info(f"[OPENER BOT GET_ACTION] Now in new state: {state.name} - {state.description}")
                else:
                    logger.info(f"[OPENER BOT GET_ACTION] Transition condition NOT met, staying in {state.name}")
            except Exception as e:
                logger.error(f"[OPENER BOT] Error in next_state_fn for {state.name}: {e}")
                import traceback
                traceback.print_exc()
                self._transition_to_state('COMPLETED')
                return None
        else:
            print(f"🔍 [OPENER BOT] No transition function defined for {state.name}")

        # 3. Execute Current State's Action
        action_or_goal = None
        if state.action_fn:
            try:
                logger.info(f"[OPENER BOT GET_ACTION] Executing action_fn for {state.name}...")
                action_or_goal = state.action_fn(state_data, visual_data)
                self.last_action = action_or_goal
                if isinstance(action_or_goal, NavigationGoal):
                    logger.info(f"[OPENER BOT] State: {state.name} | Goal: {action_or_goal.description} to ({action_or_goal.x}, {action_or_goal.y})")
                else:
                    logger.info(f"[OPENER BOT] State: {state.name} | Action: {action_or_goal} | Attempt: {self.state_attempt_count}")
            except Exception as e:
                logger.error(f"[OPENER BOT] Error in action_fn for {state.name}: {e}")
                import traceback
                traceback.print_exc()
        
        logger.info(f"[OPENER BOT GET_ACTION] Returning: {action_or_goal}")
        logger.info(f"[OPENER BOT GET_ACTION] ========================================")
        return action_or_goal
    
    def _detect_starting_state(self, state_data: Dict[str, Any]) -> Optional[str]:
        """
        Auto-detect which state we should start in based on game progress.
        Used when loading from save states.
        
        IMPORTANT: Check LOCATION first (ground truth), then milestones.
        Location tells us WHERE we are, milestones tell us WHAT we've done.
        """
        milestones = state_data.get('milestones', {})
        player_loc = state_data.get('player', {}).get('location', '')
        player_pos = state_data.get('player', {}).get('position', {})
        x, y = player_pos.get('x', 0), player_pos.get('y', 0)
        
        print(f"🔍 [STATE DETECTION] Location: {player_loc}, Position: ({x}, {y})")
        print(f"🔍 [STATE DETECTION] Milestones: {list(milestones.keys())}")
        
        # ========================================
        # LOCATION CHECKS (Ground Truth - Check First!)
        # ========================================
        
        # Route 101 - heading to Birch or already there
        if 'ROUTE 101' in player_loc or 'ROUTE_101' in player_loc or 'ROUTE101' in player_loc:
            print(f"🔍 [STATE DETECTION] On Route 101!")
            # Check if starter already chosen (battle or post-battle)
            if milestones.get('STARTER_CHOSEN', {}).get('completed', False):
                print(f"🔍 [STATE DETECTION] Starter chosen - in battle or post-battle")
                return 'S22_FIRST_BATTLE'  # Battle state or after
            # On Route 101 but no starter yet - heading to Birch/bag
            if y > 10:  # Near bag location (y=14)
                print(f"🔍 [STATE DETECTION] Near bag location (y={y})")
                return 'S19_NAV_TO_BAG'
            else:  # Just entered from town
                print(f"🔍 [STATE DETECTION] Just entered Route 101 (y={y})")
                return 'S18_BIRCH_DIALOG'
        
        # Birch's Lab
        if 'PROFESSOR BIRCHS LAB' in player_loc or 'BIRCH' in player_loc:
            print(f"🔍 [STATE DETECTION] In Birch's Lab!")
            # Check if we have a starter Pokemon in party
            party = state_data.get('party', [])
            has_starter = len(party) > 0 if party else False
            print(f"🔍 [STATE DETECTION] Party data: {party}")
            print(f"🔍 [STATE DETECTION] Party count: {len(party) if party else 0}, has_starter: {has_starter}")
            
            if has_starter:
                print(f"🔍 [STATE DETECTION] Has starter - returning S23_BIRCH_DIALOG_2")
                return 'S23_BIRCH_DIALOG_2'  # After getting starter
            else:
                print(f"🔍 [STATE DETECTION] No starter yet - returning S20_INTERACT_BAG")
                return 'S20_INTERACT_BAG'  # Interacting with bag
        
        # Check for May's house BEFORE Littleroot Town check (both contain "LITTLEROOT TOWN")
        if 'MAYS HOUSE' in player_loc or ('MAY' in player_loc and 'HOUSE' in player_loc):
            print(f"🔍 [STATE DETECTION] In May's house!")
            if '2F' in player_loc:
                return 'S11B_NAV_TO_POKEBALL'  # On 2F
            else:
                return 'S10_MAYS_MOTHER_DIALOG'  # On 1F
        
        # Check if we're in player's house (Brendan's house) BEFORE Littleroot Town check
        if ('PLAYERS_HOUSE' in player_loc or 'BRENDANS_HOUSE' in player_loc or 
            ('BRENDAN' in player_loc and 'HOUSE' in player_loc)):
            print(f"🔍 [STATE DETECTION] In player's house!")
            if '2F' in player_loc:
                # On 2nd floor - setting clock or leaving
                return 'S6_NAV_TO_CLOCK'
            else:
                # On 1st floor - Mom dialogue or navigating to stairs
                return 'S4_MOM_DIALOG_1F'
        
        # Littleroot Town (OVERWORLD) - only matches if NOT in a specific building
        # This check must come AFTER house checks since location names include "LITTLEROOT TOWN"
        if 'LITTLEROOT' in player_loc and 'TOWN' in player_loc:
            print(f"🔍 [STATE DETECTION] In Littleroot Town overworld!")
            
            # Check what we've completed to determine next step
            if milestones.get('RIVAL_BEDROOM', {}).get('completed', False):
                # We've been to May's room - now heading to NPC
                print(f"🔍 [STATE DETECTION] Visited rival's bedroom, heading to NPC")
                if y < 8:  # Near north edge of town
                    print(f"🔍 [STATE DETECTION] Near north edge (y={y}), at NPC or heading to Route 101")
                    return 'S16_NPC_DIALOG'  # At NPC or just passed
                else:
                    print(f"🔍 [STATE DETECTION] South part of town (y={y}), navigating to NPC")
                    return 'S15_NAV_TO_NPC_NORTH'
            elif milestones.get('RIVAL_HOUSE', {}).get('completed', False):
                # We've been to rival house but not bedroom - probably navigating to May's room
                print(f"🔍 [STATE DETECTION] Visited rival's house, heading to May's room or already there")
                return 'S9_NAV_TO_MAYS_HOUSE'
            elif milestones.get('PLAYER_BEDROOM', {}).get('completed', False):
                # Been to our bedroom - heading to or inside rival's house
                print(f"🔍 [STATE DETECTION] Been to our bedroom, heading to rival's house")
                return 'S9_NAV_TO_MAYS_HOUSE'
            else:
                # In Littleroot but haven't done much - probably just started
                print(f"🔍 [STATE DETECTION] Early in Littleroot Town")
                return 'S4_MOM_DIALOG_1F'

        
        # Moving Van / Truck
        if 'MOVING_VAN' in player_loc or 'VAN' in player_loc or 'TRUCK' in player_loc:
            print(f"🔍 [STATE DETECTION] In moving van/truck!")
            return 'S3_TRUCK_RIDE'
        
        # ========================================
        # MILESTONE-ONLY CHECKS (Fallback if location unclear)
        # ========================================
        
        if milestones.get('PLAYER_NAME_SET', {}).get('completed', False):
            print(f"🔍 [STATE DETECTION] Name set but unclear location - defaulting to house")
            return 'S4_MOM_DIALOG_1F'
        
        # Default to title screen if no milestones
        print(f"🔍 [STATE DETECTION] No clear state detected - defaulting to title screen")
        return 'S0_TITLE_SCREEN'
        
    def _build_state_machine(self) -> Dict[str, BotState]:
        """
        Builds the STATEFUL state machine.
        Each state has an action_fn (what to do) and next_state_fn (when to transition).
        """
        
        # --- Helper Action Functions ---

        def action_press_a(s, v):
            return ['A']

        def action_press_start(s, v):
            return ['START']
            
        def action_press_b(s, v):
            return ['B']

        def action_clear_dialogue(s, v):
            """
            Press A if dialogue is detected, OR handle naming keyboard with B→START→A sequence.
            This handles the intro naming screen that appears during Prof Birch dialogue.
            
            Naming keyboard sequence (like nicknaming):
            1. Press B to clear any existing text
            2. Press START to jump cursor to OK button
            3. Press A to confirm and exit
            
            IMPORTANT: Does NOT rely solely on game_state='dialog' because it can get stuck.
            Requires visual confirmation (text_box or screen_context) to keep pressing A.
            """
            screen_context = v.get('screen_context', '').lower()
            text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
            continue_prompt_visible = v.get('visual_elements', {}).get('continue_prompt_visible', False)
            game_state = s.get('game', {}).get('game_state', '').lower()
            dialogue = (v.get('on_screen_text', {}).get('dialogue', '') or '').upper()
            menu_title = (v.get('on_screen_text', {}).get('menu_title', '') or '').upper()
            
            # CRITICAL: Check if this is player monologue BEFORE pressing A
            # Player's internal thoughts have "Player:" prefix in dialogue text
            # Do NOT use speaker field - it's unreliable (Mom talking TO Casey shows speaker="CASEY")
            dialogue_text = v.get('on_screen_text', {}).get('dialogue', '')
            is_player_monologue = (dialogue_text and dialogue_text.strip().upper().startswith('PLAYER:'))
            
            if is_player_monologue:
                # Player monologues - don't press A, likely VLM hallucination
                # Let stuck detection in action_nav handle it if navigation is blocked
                print("💬 [CLEAR_DIALOGUE] Player monologue detected - ignoring (likely VLM hallucination)")
                return None
            
            # Initialize step counter for naming keyboard sequence
            if not hasattr(action_clear_dialogue, '_naming_step'):
                action_clear_dialogue._naming_step = 0
            
            # SPECIAL CASE: Detect naming keyboard screen
            # Indicators: "YOUR NAME?" dialogue + still in TITLE_SEQUENCE
            # Solution: B → START → A sequence to exit with default name
            location = s.get('player', {}).get('location', '')
            if 'YOUR NAME' in dialogue and 'TITLE_SEQUENCE' in location:
                print(f"🎮 [S1_NAMING] Detected naming keyboard (step {action_clear_dialogue._naming_step})")
                
                if action_clear_dialogue._naming_step == 0:
                    action_clear_dialogue._naming_step = 1
                    print("🎮 [S1_NAMING] Step 1: Pressing B to clear any text")
                    return ['B']
                elif action_clear_dialogue._naming_step == 1:
                    action_clear_dialogue._naming_step = 2
                    print("🎮 [S1_NAMING] Step 2: Pressing START to jump to OK button")
                    return ['START']
                else:
                    action_clear_dialogue._naming_step = 0  # Reset for next time
                    print("🎮 [S1_NAMING] Step 3: Pressing A to confirm and exit")
                    return ['A']
            else:
                # Reset step counter when not in naming keyboard
                action_clear_dialogue._naming_step = 0
            
            # Press A if we have VISUAL confirmation of dialogue
            # NOTE: Don't press A based on game_state alone - it can get stuck
            # Require at least one visual indicator (text_box, screen_context, or continue_prompt)
            has_visual_dialogue = text_box_visible or screen_context == 'dialogue' or continue_prompt_visible
            
            if has_visual_dialogue:
                return ['A']
            elif game_state == 'dialog':
                # Visual indicators say no dialogue, but game_state stuck as 'dialog'
                # This is a known issue - don't press A, let transition logic handle it
                print(f"⚠️ [CLEAR_DIALOGUE] game_state='dialog' but no visual indicators - not pressing A (likely stuck state)")
                return None
            
            return None
        
        def action_clear_dialogue_persistent(s, v):
            """
            Press A to clear dialogue, including multi-page dialogues.
            
            Unlike action_clear_dialogue, this function will KEEP PRESSING A even when
            visual indicators are clear but game_state='dialog' is stuck. This is needed
            for NPCs with multi-page dialogue (like "..." continuation pages) where:
            1. First page shows real dialogue
            2. Press A → VLM hallucinates on next page
            3. Visual indicators clear but game_state still 'dialog'
            4. Need to press A again to advance past "..." page
            
            This prevents premature transitions while dialogue is still active.
            
            CRITICAL: Must check for player monologue to avoid spamming A on internal thoughts!
            """
            screen_context = v.get('screen_context', '').lower()
            text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
            continue_prompt_visible = v.get('visual_elements', {}).get('continue_prompt_visible', False)
            game_state = s.get('game', {}).get('game_state', '').lower()
            
            # Check for player monologue BEFORE pressing A
            on_screen_text = v.get('on_screen_text', {})
            dialogue_text = on_screen_text.get('dialogue', '')
            
            # Player monologue ONLY detects "Player:" prefix in dialogue text
            # Do NOT use speaker field - it's unreliable (Mom talking TO Casey shows speaker="CASEY")
            is_player_monologue = (dialogue_text and dialogue_text.strip().upper().startswith('PLAYER:'))
            
            if is_player_monologue:
                # Player monologues - don't press A, likely VLM hallucination
                # Let the state machine transition when dialogue actually clears
                print(f"💬 [PERSISTENT_DIALOGUE] Player monologue detected - ignoring (likely VLM hallucination)")
                return None
            
            # Press A if we have visual confirmation OR if game_state says dialogue is active
            # This handles both visible dialogue and hidden pages (like "...")
            has_visual_dialogue = text_box_visible or screen_context == 'dialogue' or continue_prompt_visible
            
            if has_visual_dialogue:
                print(f"💬 [PERSISTENT_DIALOGUE] Visual dialogue detected, pressing A")
                return ['A']
            elif game_state == 'dialog':
                # Game memory says dialogue active - keep pressing A even without visuals
                # This catches "..." pages that VLM hallucinates as HUD text
                print(f"💬 [PERSISTENT_DIALOGUE] game_state='dialog', pressing A (may be hidden page)")
                return ['A']
            
            # Only return None if BOTH visual AND memory say dialogue is done
            return None
        
        def action_clear_dialogue_then_move_away(direction: str) -> Callable:
            """
            Clear dialogue if present, otherwise move in the specified direction.
            Used to prevent re-triggering NPCs after dialogue ends.
            """
            def action_fn(s, v):
                screen_context = v.get('screen_context', '').lower()
                text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
                continue_prompt_visible = v.get('visual_elements', {}).get('continue_prompt_visible', False)
                game_state = s.get('game', {}).get('game_state', '').lower()
                
                # If in dialogue, press A to clear
                if text_box_visible or screen_context == 'dialogue' or game_state == 'dialog' or continue_prompt_visible:
                    return ['A']
                # Otherwise move away from NPC
                return [direction]
            return action_fn

        def action_clear_dialogue_then_try_move(direction: str) -> Callable:
            """
            Smart dialogue clearing with movement validation:
            1. If strong dialogue indicators show active dialogue (text_box + prompt/context), press A
            2. If weak/uncertain indicators, try to move 
            3. If movement failed (position unchanged), dialogue must still be blocking - press A again
            
            This is robust against perception errors, looping dialogues, and stuck game_state flags.
            
            NOTE: We don't trust game_state='dialog' alone because it can stay stuck even after dialogue clears.
            We require at least TWO indicators to confirm dialogue is active.
            
            Args:
                direction: Direction to move after dialogue is cleared
            """
            def action_fn(s, v):
                # Check dialogue indicators
                screen_context = v.get('screen_context', '').lower()
                text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
                continue_prompt_visible = v.get('visual_elements', {}).get('continue_prompt_visible', False)
                game_state = s.get('game', {}).get('game_state', '').lower()
                
                # Count how many strong indicators say dialogue is active
                # Strong indicators: text_box + continue_prompt, screen_context=dialogue
                strong_indicators = 0
                if text_box_visible and continue_prompt_visible:
                    strong_indicators += 1
                if screen_context == 'dialogue':
                    strong_indicators += 1
                
                # Dialogue is clearly active if we have strong visual indicators
                dialogue_clearly_active = strong_indicators >= 1
                
                # Get current position
                pos = s.get('player', {}).get('position', {})
                current_x, current_y = pos.get('x', -1), pos.get('y', -1)
                
                # Get last known position and action
                last_pos = getattr(action_fn, '_last_pos', (current_x, current_y))
                last_action = getattr(action_fn, '_last_action', None)
                
                # CASE 1: Dialogue is clearly active (strong visual evidence) - press A
                if dialogue_clearly_active:
                    action_fn._last_pos = (current_x, current_y)
                    action_fn._last_action = 'A'
                    print(f"🔍 [CLEAR_DIALOGUE_TRY_MOVE] Dialogue clearly active ({strong_indicators} indicators), pressing A (text_box={text_box_visible}, context={screen_context}, game_state={game_state}, prompt={continue_prompt_visible})")
                    return ['A']
                
                # CASE 2: We tried to move last time but position didn't change - dialogue is blocking
                if last_action == direction and last_pos == (current_x, current_y):
                    action_fn._last_pos = (current_x, current_y)
                    action_fn._last_action = 'A'
                    print(f"🔍 [CLEAR_DIALOGUE_TRY_MOVE] Movement BLOCKED! Position unchanged ({current_x},{current_y}). Dialogue still active - pressing A")
                    return ['A']
                
                # CASE 3: No strong dialogue indicators and (first attempt or movement succeeded) - try to move
                action_fn._last_pos = (current_x, current_y)
                action_fn._last_action = direction
                print(f"🔍 [CLEAR_DIALOGUE_TRY_MOVE] No strong dialogue indicators (game_state={game_state} alone not trusted), trying to move {direction} from ({current_x},{current_y})")
                return [direction]
            
            return action_fn

        def action_nav(goal: NavigationGoal):
            """
            Factory for navigation actions with stuck detection.
            
            Strategy:
            1. Always attempt navigation first (ignore VLM dialogue reports)
            2. Track position history to detect being stuck
            3. Only clear dialogue when stuck AND dialogue is detected in game state
            4. This prevents reacting to VLM hallucinations while handling real dialogue blocks
            """
            def nav_fn(s, v):
                # Initialize position tracking
                if not hasattr(nav_fn, '_position_history'):
                    nav_fn._position_history = deque(maxlen=5)
                if not hasattr(nav_fn, '_stuck_frames'):
                    nav_fn._stuck_frames = 0
                if not hasattr(nav_fn, '_last_navigation_attempt'):
                    nav_fn._last_navigation_attempt = None
                
                # Get current position
                player_data = s.get('player', {})
                position = player_data.get('position', {})
                current_pos = (position.get('x'), position.get('y'), player_data.get('location'))
                
                # Track position history
                nav_fn._position_history.append(current_pos)
                
                # Check if stuck (same position for 3+ consecutive frames)
                is_stuck = False
                if len(nav_fn._position_history) >= 3:
                    recent_positions = list(nav_fn._position_history)[-3:]
                    if all(pos == current_pos for pos in recent_positions):
                        is_stuck = True
                        nav_fn._stuck_frames += 1
                    else:
                        nav_fn._stuck_frames = 0
                else:
                    nav_fn._stuck_frames = 0
                
                # If stuck for 3+ frames, diagnose and intervene
                if is_stuck and nav_fn._stuck_frames >= 3:
                    # Check if stuck due to dialogue
                    game_state = s.get('game', {}).get('game_state', '').lower()
                    visual_elements = v.get('visual_elements', {})
                    text_box_visible = visual_elements.get('text_box_visible', False)
                    
                    # Multiple indicators of dialogue blocking navigation
                    dialogue_blocking = (
                        game_state == 'dialog' or 
                        text_box_visible or
                        v.get('screen_context', '').lower() == 'dialogue'
                    )
                    
                    if dialogue_blocking:
                        print(f"🚫 [NAV STUCK] Stuck at {current_pos} for {nav_fn._stuck_frames} frames - dialogue blocking")
                        print(f"🚫 [NAV STUCK] CANNOT directly press A - competition rules require VLM final decision")
                        print(f"🚫 [NAV STUCK] Returning None to yield to dialogue system Priority 1")
                        nav_fn._stuck_frames = 0  # Reset after intervention
                        return None  # Let Priority 1 dialogue system handle this
                    else:
                        # Stuck but not due to dialogue - might be pathfinding issue
                        # Try the goal anyway, let A* recalculate
                        print(f"🚫 [NAV STUCK] Stuck at {current_pos} for {nav_fn._stuck_frames} frames - no dialogue detected, continuing with goal")
                
                # Not stuck or haven't been stuck long enough - proceed with navigation
                return goal
            
            return nav_fn

        def action_simple(actions: List[str]):
            """Returns a simple action (like ['UP']) every time. No dialogue clearing."""
            def simple_fn(s, v):
                return actions
            return simple_fn

        def action_special_naming(s, v):
            """
            Handles gender and name selection screens.
            
            Sequence:
            1. "Are you a boy or girl?" - Press A (selects BOY)
            2. "What's your name?" - Press A ONCE to enter naming screen
            3. Naming screen appears with keyboard - Wait for it to fully load
            4. On keyboard screen - Press START to accept default name
            5. "So it's [NAME]?" - Press A (confirms choice)
            
            CRITICAL: We check screen_context to know if we're IN the naming keyboard.
            The naming keyboard shows screen_context='dialogue' with letters/grid visible.
            """
            dialogue = (v.get('on_screen_text', {}).get('dialogue', '') or '').upper()
            screen_context = v.get('screen_context', '').lower()
            menu_title = (v.get('on_screen_text', {}).get('menu_title', '') or '').upper()
            
            # Initialize state tracking
            if not hasattr(action_special_naming, '_entered_naming_screen'):
                action_special_naming._entered_naming_screen = False
            if not hasattr(action_special_naming, '_naming_step'):
                action_special_naming._naming_step = 0
            
            print(f"🎮 [NAMING DEBUG] dialogue='{dialogue[:50]}...', screen_context={screen_context}, menu_title='{menu_title[:30]}...', entered={action_special_naming._entered_naming_screen}")
            
            # Gender selection
            if "ARE YOU A BOY" in dialogue or "BOY OR" in dialogue:
                action_special_naming._entered_naming_screen = False
                action_special_naming._naming_step = 0
                print("🎮 [NAMING] Gender selection - pressing A")
                return ['A']
            
            # Name confirmation ("So it's..." or "Is this your name?")  
            if ("SO IT" in dialogue or "IS THIS" in dialogue or "THAT'S A NICE" in dialogue) and "NAME" in dialogue:
                action_special_naming._entered_naming_screen = False
                action_special_naming._naming_step = 0
                print("🎮 [NAMING] Name confirmation - pressing A")
                return ['A']
            
            # Check if we're IN the naming keyboard (letters visible, can type)
            # The keyboard shows as screen_context='dialogue' with a grid of letters
            # We detect this by checking if "NAME" is in menu_title (top of screen shows name entry)
            in_naming_keyboard = (screen_context == 'dialogue' and 
                                 action_special_naming._entered_naming_screen and
                                 ("NAME" in menu_title or len(menu_title) > 0))
            
            if in_naming_keyboard:
                # We're inside the naming keyboard - press START to accept default
                print(f"🎮 [NAMING] Inside keyboard (menu_title='{menu_title}'), pressing START to accept default")
                action_special_naming._entered_naming_screen = False  # Reset for next time
                return ['START']
            
            # "What's your name?" prompt - press A ONCE to enter naming screen
            if "YOUR NAME" in dialogue and not action_special_naming._entered_naming_screen:
                action_special_naming._entered_naming_screen = True
                print("🎮 [NAMING] 'YOUR NAME?' prompt detected - pressing A to enter screen")
                return ['A']
            
            # If we pressed A but naming screen hasn't appeared yet, wait
            if action_special_naming._entered_naming_screen and "YOUR NAME" in dialogue:
                print("🎮 [NAMING] Waiting for naming screen to load...")
                return None  # Wait one frame for screen to change
            
            # General dialogue clearing (for other dialogue in this state)
            if v.get('visual_elements', {}).get('text_box_visible', False):
                print("🎮 [NAMING] Clearing general dialogue with A")
                return ['A']
                
            return None

        def action_special_clock(s, v):
            """
            Handles the clock UI including the Yes/No confirmation.
            
            Clock sequence:
            1. "The clock..." - press A
            2. "Better set it and start it!" - press A to set time
            3. "Is this the correct time?" with Yes/No menu - Step 1: UP, Step 2: A
            
            Uses step-based approach for Yes/No menu (can't send two buttons in one frame).
            """
            dialogue = v.get('on_screen_text', {}).get('dialogue', '').upper()
            
            # Initialize step counter for Yes/No menu
            if not hasattr(action_special_clock, '_yesno_step'):
                action_special_clock._yesno_step = 0
            
            # Check if we're at the "Is this the correct time?" dialogue
            if "IS THIS" in dialogue and "CORRECT TIME" in dialogue:
                # Yes/No menu - need to press UP then A (separate frames)
                print(f"🕐 [CLOCK] Yes/No menu detected (step {action_special_clock._yesno_step})")
                
                if action_special_clock._yesno_step == 0:
                    action_special_clock._yesno_step = 1
                    print("🕐 [CLOCK] Step 1: Pressing UP to select YES")
                    return ['UP']
                else:
                    action_special_clock._yesno_step = 0  # Reset for next time
                    print("🕐 [CLOCK] Step 2: Pressing A to confirm")
                    return ['A']
            else:
                # Reset step counter when not in Yes/No menu
                action_special_clock._yesno_step = 0
            
            # For all other clock-related dialogue, just press A
            if "SET THE CLOCK" in dialogue or "IS THIS TIME" in dialogue or "THE CLOCK" in dialogue:
                print(f"🕐 [CLOCK] Clock dialogue detected, pressing A")
                return ['A']
                
            # General dialogue clearing
            if v.get('visual_elements', {}).get('text_box_visible', False):
                print(f"🕐 [CLOCK] Text box visible, pressing A")
                return ['A']
                
            return None

        def action_special_starter(s, v):
            """Handles selecting the starter."""
            dialogue = v.get('on_screen_text', {}).get('dialogue', '').upper()
            menu_title = v.get('on_screen_text', {}).get('menu_title', '').upper()
            if "CHOOSE A POKéMON" in dialogue or "BAG" in menu_title:
                return ['A']
            if "DO YOU CHOOSE THIS" in dialogue:
                return ['A']
            if v.get('visual_elements', {}).get('text_box_visible', False):
                return ['A']
            return None

        def action_special_nickname(s, v):
            """
            Handles nickname screen - either decline before entering OR exit if already inside.
            
            Strategy: Due to VLM timing, we often enter the naming window before detecting it.
            If inside the naming window, use shortcut: B (backspace) → START (move to OK) → A (confirm)
            """
            dialogue = (v.get('on_screen_text', {}).get('dialogue', '') or '').upper()
            screen_context = v.get('screen_context', '').lower()
            
            # Initialize step counter if needed
            if not hasattr(action_special_nickname, '_nickname_step'):
                action_special_nickname._nickname_step = 0
            
            # Check if we're INSIDE the naming window (keyboard visible)
            # Indicators: "nickname?" in dialogue, letter grid visible, "SELECT" menu visible
            menu_title = (v.get('on_screen_text', {}).get('menu_title', '') or '').upper()
            inside_naming_window = (
                ("NICKNAME?" in dialogue or menu_title == "SELECT") and
                screen_context == 'dialogue'
            )
            
            if inside_naming_window:
                # We're already inside - use B → START → A shortcut to exit quickly
                print(f"🎮 [NICKNAME WINDOW] Inside naming screen (step {action_special_nickname._nickname_step})")
                
                if action_special_nickname._nickname_step == 0:
                    action_special_nickname._nickname_step = 1
                    print("🎮 [NICKNAME WINDOW] Step 1: Pressing B to clear any letters")
                    return ['B']
                elif action_special_nickname._nickname_step == 1:
                    action_special_nickname._nickname_step = 2
                    print("🎮 [NICKNAME WINDOW] Step 2: Pressing START to jump to OK button")
                    return ['START']
                else:
                    action_special_nickname._nickname_step = 0  # Reset for next time
                    print("🎮 [NICKNAME WINDOW] Step 3: Pressing A to confirm and exit")
                    return ['A']
            
            # If asking about nickname BEFORE entering naming window (ideal case)
            if "NICKNAME" in dialogue and not inside_naming_window:
                print(f"🎮 [NICKNAME PROMPT] At nickname prompt (step {action_special_nickname._nickname_step})")
                
                if action_special_nickname._nickname_step == 0:
                    action_special_nickname._nickname_step = 1
                    print("🎮 [NICKNAME PROMPT] Step 1: Pressing DOWN to select NO")
                    return ['DOWN']
                else:
                    action_special_nickname._nickname_step = 0  # Reset for next time
                    print("🎮 [NICKNAME PROMPT] Step 2: Pressing A to confirm NO")
                    return ['A']
            
            # Clear any remaining dialogue
            if v.get('visual_elements', {}).get('text_box_visible', False):
                print("🎮 [NICKNAME] Clearing dialogue with A")
                return ['A']
            
            return None
            
        def action_pass_to_battle_bot(s, v):
            """Do nothing - lets main action.py call Battle Bot."""
            return None

        # --- Transition Check Functions (FIXED: Return state names, not True/None) ---
        
        def trans_game_state_not(state_value: str, next_state: str) -> Callable:
            """Transition when game_state is NOT the given value."""
            def check_fn(s, v):
                current_game_state = s.get('game', {}).get('game_state', '').lower()
                print(f"🔍 [TRANS_GAME_STATE_NOT] Checking if game_state '{current_game_state}' != '{state_value}': {current_game_state != state_value.lower()}")
                if current_game_state != state_value.lower():
                    print(f"🔍 [TRANS_GAME_STATE_NOT] Transitioning to {next_state}")
                    return next_state
                return None
            return check_fn

        def trans_dialogue_contains(text: str, next_state: str) -> Callable:
            """Transition when dialogue contains specific text."""
            def check_fn(s, v):
                dialogue = v.get('on_screen_text', {}).get('dialogue', '') or ''
                contains_text = text.upper() in dialogue.upper()
                print(f"🔍 [TRANS_DIALOGUE] Checking if '{text}' in '{dialogue[:50]}...': {contains_text}")
                if contains_text:
                    print(f"🔍 [TRANS_DIALOGUE] Transitioning to {next_state}")
                    return next_state
                return None
            return check_fn

        def trans_milestone_complete(milestone_id: str, next_state: str) -> Callable:
            """Transition when milestone is completed."""
            def check_fn(s, v):
                completed = s.get('milestones', {}).get(milestone_id, {}).get('completed', False)
                print(f"🔍 [TRANS_MILESTONE] Checking milestone '{milestone_id}': completed={completed}")
                if completed:
                    print(f"🔍 [TRANS_MILESTONE] Milestone '{milestone_id}' complete! Transitioning to {next_state}")
                    return next_state
                return None
            return check_fn

        def trans_location_contains(loc_name: str, next_state: str) -> Callable:
            """Transition when location contains specific text."""
            def check_fn(s, v):
                location = s.get('player', {}).get('location', '') or ''
                result = loc_name.upper() in location.upper()
                print(f"🔍 [TRANS_LOCATION] Checking if '{loc_name}' in '{location}': {result}")
                if result:
                    print(f"🔍 [TRANS_LOCATION] Transitioning to {next_state}")
                    return next_state
                return None
            return check_fn

        def trans_location_exact(loc_name: str, next_state: str) -> Callable:
            """Transition when location exactly matches (case-insensitive)."""
            def check_fn(s, v):
                location = s.get('player', {}).get('location', '') or ''
                result = loc_name.upper() == location.upper()
                print(f"🔍 [TRANS_LOCATION_EXACT] Checking if '{loc_name}' == '{location}': {result}")
                if result:
                    print(f"🔍 [TRANS_LOCATION_EXACT] Transitioning to {next_state}")
                    return next_state
                return None
            return check_fn

        def trans_no_dialogue(next_state: str, min_wait_steps: int = 2) -> Callable:
            """
            Transition when dialogue is FULLY cleared - both visually AND in game memory.
            
            CRITICAL: Must check BOTH conditions:
            1. Visual indicators (VLM can hallucinate, so check all indicators)
            2. Game memory state (player cannot move while game_state='dialog')
            
            PLAYER MONOLOGUE HANDLING: If VLM reports "Player: ..." dialogue, this is
            likely a hallucination. Treat it as NO dialogue for transition purposes.
            
            ESCAPE MECHANISM: If visuals are clear but game_state is stuck as 'dialog',
            force transition after waiting min_wait_steps to allow action to complete.
            This prevents premature transitions during multi-page dialogues while still
            escaping truly stuck states.
            
            Args:
                next_state: State to transition to
                min_wait_steps: Minimum steps to wait when visuals clear but game_state stuck
            """
            def check_fn(s, v):
                screen_context = v.get('screen_context', '').lower()
                text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
                continue_prompt_visible = v.get('visual_elements', {}).get('continue_prompt_visible', False)
                game_state = s.get('game', {}).get('game_state', '')
                
                # CRITICAL: Check for player monologue (VLM hallucination)
                # Player monologue ONLY detects "Player:" prefix in dialogue text
                dialogue_text = v.get('on_screen_text', {}).get('dialogue', '')
                is_player_monologue = (dialogue_text and dialogue_text.strip().upper().startswith('PLAYER:'))
                
                # If player monologue detected, treat all visual indicators as false (likely hallucination)
                if is_player_monologue:
                    print(f"🔍 [TRANS_NO_DIALOGUE] Player monologue detected - treating as no dialogue (likely VLM hallucination)")
                    text_box_visible = False
                    continue_prompt_visible = False
                    if screen_context == 'dialogue':
                        screen_context = 'overworld'
                
                # Transition if dialogue is FULLY cleared:
                # 1. No visual indicators (text_box, dialogue context, continue prompt)
                # 2. Game memory state is NOT 'dialog' (player can actually move)
                visuals_clear = not text_box_visible and screen_context != 'dialogue' and not continue_prompt_visible
                memory_clear = game_state != 'dialog'
                
                # Initialize counter for stuck detection
                if not hasattr(check_fn, '_stuck_steps'):
                    check_fn._stuck_steps = 0
                
                # Track how many steps visuals have been clear while game_state stuck
                if visuals_clear and not memory_clear:
                    check_fn._stuck_steps += 1
                else:
                    check_fn._stuck_steps = 0
                
                # CASE 1: Both clear - normal transition
                if visuals_clear and memory_clear:
                    check_fn._stuck_steps = 0  # Reset counter
                    print(f"🔍 [TRANS_NO_DIALOGUE] Dialogue fully cleared! visual={visuals_clear}, game_state={game_state}")
                    return next_state
                
                # CASE 2: Visuals clear but game_state stuck - wait min_wait_steps before forcing
                # This gives action_clear_dialogue_persistent time to complete multi-page dialogues
                elif visuals_clear and not memory_clear:
                    if check_fn._stuck_steps >= min_wait_steps:
                        print(f"⚠️ [TRANS_NO_DIALOGUE] Stuck for {check_fn._stuck_steps} steps (game_state={game_state}) - forcing transition!")
                        check_fn._stuck_steps = 0
                        return next_state
                    else:
                        print(f"🔍 [TRANS_NO_DIALOGUE] Visuals clear but game_state={game_state} - waiting ({check_fn._stuck_steps}/{min_wait_steps})")
                        return None
                
                # CASE 3: Visuals still show dialogue - keep waiting
                else:
                    return None
            return check_fn
        
        def trans_has_dialogue(next_state: str) -> Callable:
            """Transition when dialogue IS active (inverse of trans_no_dialogue)."""
            def check_fn(s, v):
                screen_context = v.get('screen_context', '').lower()
                text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
                continue_prompt_visible = v.get('visual_elements', {}).get('continue_prompt_visible', False)
                
                # Count strong indicators (don't trust game_state alone)
                strong_indicators = 0
                if text_box_visible and continue_prompt_visible:
                    strong_indicators += 1
                if screen_context == 'dialogue':
                    strong_indicators += 1
                
                # Dialogue active if at least 1 strong indicator
                if strong_indicators >= 1:
                    return next_state
                return None
            return check_fn
        
        def trans_detect_naming_screen(next_state: str) -> Callable:
            """
            Transition when we detect the actual naming/gender screen.
            The naming screen has distinct characteristics:
            - NOT in TITLE_SEQUENCE location anymore
            - OR has specific menu_title
            - OR dialogue contains gender question WITHOUT name already set
            """
            def check_fn(s, v):
                location = s.get('player', {}).get('location', '')
                dialogue = (v.get('on_screen_text', {}).get('dialogue', '') or '').upper()
                menu_title = (v.get('on_screen_text', {}).get('menu_title', '') or '').upper()
                player_name = s.get('player', {}).get('name', '')
                name_milestone_done = s.get('milestones', {}).get('PLAYER_NAME_SET', {}).get('completed', False)
                
                # If name is already set, we missed the screen
                if name_milestone_done:
                    print(f"🔍 [TRANS_NAMING] Name already set ({player_name}), missed the naming screen!")
                    return 'S3_TRUCK_RIDE'  # Skip directly to truck
                
                # Check for gender/naming screen indicators
                # Gender question should appear when we're NOT just in title sequence anymore
                if "BOY" in dialogue and "GIRL" in dialogue and 'TITLE_SEQUENCE' not in location:
                    print(f"🔍 [TRANS_NAMING] Gender question detected outside title sequence!")
                    return next_state
                
                # Naming keyboard has distinctive menu title
                if "NAME" in menu_title and len(menu_title) > 3:
                    print(f"🔍 [TRANS_NAMING] Naming screen menu detected: {menu_title}")
                    return next_state
                
                return None
            return check_fn
        
        def trans_name_set_plus_frames(s, v, frames_to_wait: int = 10):
            """
            Transition after PLAYER_NAME_SET milestone completes AND we've waited additional frames.
            This handles the delay between name being set and location actually changing.
            
            Strategy:
            1. Wait for PLAYER_NAME_SET milestone
            2. Count frames after milestone completes
            3. After N frames, check location and transition appropriately
            """
            name_milestone_done = s.get('milestones', {}).get('PLAYER_NAME_SET', {}).get('completed', False)
            location = s.get('player', {}).get('location', '')
            
            # Initialize frame counter on first call
            if not hasattr(trans_name_set_plus_frames, '_frames_since_name_set'):
                trans_name_set_plus_frames._frames_since_name_set = 0
                trans_name_set_plus_frames._name_was_set = False
            
            # Reset counter if milestone wasn't set before but is now
            if name_milestone_done and not trans_name_set_plus_frames._name_was_set:
                print(f"🔍 [S1_TRANS] PLAYER_NAME_SET milestone just completed! Starting frame counter.")
                trans_name_set_plus_frames._frames_since_name_set = 0
                trans_name_set_plus_frames._name_was_set = True
            
            # If name is set, increment counter
            if name_milestone_done:
                trans_name_set_plus_frames._frames_since_name_set += 1
                frames_waited = trans_name_set_plus_frames._frames_since_name_set
                print(f"🔍 [S1_TRANS] Name set, waited {frames_waited}/{frames_to_wait} frames. Location: '{location}'")
                
                # After waiting enough frames, check location and transition
                if frames_waited >= frames_to_wait:
                    print(f"🔍 [S1_TRANS] Waited {frames_to_wait} frames, checking location for transition...")
                    
                    # Check for truck/van
                    if 'MOVING_VAN' in location or 'VAN' in location or 'TRUCK' in location:
                        print(f"🔍 [S1_TRANS] ✅ Found truck/van in location! Transitioning to S3_TRUCK_RIDE")
                        # Reset for next time
                        trans_name_set_plus_frames._frames_since_name_set = 0
                        trans_name_set_plus_frames._name_was_set = False
                        return 'S3_TRUCK_RIDE'
                    
                    # Check for house
                    if 'HOUSE 1F' in location or 'BRENDAN' in location:
                        print(f"🔍 [S1_TRANS] ✅ Found house in location! Transitioning to S4_MOM_DIALOG_1F")
                        # Reset for next time
                        trans_name_set_plus_frames._frames_since_name_set = 0
                        trans_name_set_plus_frames._name_was_set = False
                        return 'S4_MOM_DIALOG_1F'
                    
                    # Still in TITLE_SEQUENCE after waiting - wait more
                    print(f"🔍 [S1_TRANS] ⚠️ Still in '{location}' after {frames_waited} frames, continuing to wait...")
            
            return None
            
        def trans_in_battle(next_state: str) -> Callable:
            """Transition when in battle."""
            def check_fn(s, v):
                if s.get('game', {}).get('in_battle', False):
                    return next_state
                return None
            return check_fn

        def trans_area_and_dialogue(x_range: List[int], y_range: List[int], next_state: str) -> Callable:
            """
            Transition when in specific AREA and dialogue appears.
            CRITICAL FIX: Handles "adjacent-interact" bug by checking area, not exact position.
            ALSO: Ignores player monologue hallucinations - only real NPC dialogue triggers transition.
            """
            def check_fn(s, v):
                pos = s.get('player', {}).get('position', {})
                x, y = pos.get('x', -1), pos.get('y', -1)
                
                # Check if in area
                in_area = x in x_range and y in y_range
                if not in_area:
                    return None
                
                # Check for dialogue
                text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
                if not text_box_visible:
                    return None
                
                # CRITICAL: Ignore player monologue hallucinations
                dialogue_text = v.get('on_screen_text', {}).get('dialogue', '')
                is_player_monologue = dialogue_text.strip().upper().startswith('PLAYER:')
                
                if is_player_monologue:
                    print(f"🔍 [TRANS_AREA_DIALOGUE] Player monologue detected - ignoring (likely VLM hallucination)")
                    return None
                
                # Real dialogue in the area - transition!
                print(f"🔍 [TRANS_AREA_DIALOGUE] In area, real dialogue detected - transitioning to {next_state}")
                return next_state
            return check_fn
        
        def trans_left_area_or_no_dialogue(x_range: List[int], y_range: List[int], next_state: str) -> Callable:
            """
            Transition when player has LEFT specific area OR all dialogue cleared.
            This prevents premature transitions while dialogue is blocking movement.
            Used for post-interaction dialogue like May's pokeball.
            """
            def check_fn(s, v):
                pos = s.get('player', {}).get('position', {})
                x, y = pos.get('x', -1), pos.get('y', -1)
                
                # Check if we've left the interaction area
                left_area = x not in x_range or y not in y_range
                
                # Check all dialogue indicators
                screen_context = v.get('screen_context', '').lower()
                text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
                continue_prompt_visible = v.get('visual_elements', {}).get('continue_prompt_visible', False)
                game_state = s.get('game', {}).get('game_state', '').lower()
                no_dialogue = not text_box_visible and screen_context != 'dialogue' and game_state != 'dialog' and not continue_prompt_visible
                
                # Transition if we've left the area OR dialogue is fully cleared
                if left_area or no_dialogue:
                    print(f"🔍 [TRANS_LEFT_AREA] Pos ({x},{y}), left_area={left_area}, no_dialogue={no_dialogue}")
                    return next_state
                return None
            return check_fn
        
        def trans_left_area_only(x_range: List[int], y_range: List[int], next_state: str) -> Callable:
            """
            Transition ONLY when player has physically left the area.
            This is the most robust check - if dialogue is blocking, player can't move.
            Once dialogue clears, player can move and will leave the area.
            DO NOT use perception checks - they are unreliable due to filtering.
            """
            def check_fn(s, v):
                pos = s.get('player', {}).get('position', {})
                x, y = pos.get('x', -1), pos.get('y', -1)
                
                # Only transition if we've physically left the interaction area
                left_area = x not in x_range or y not in y_range
                
                if left_area:
                    print(f"🔍 [TRANS_LEFT_AREA_ONLY] Pos ({x},{y}) - left area, transitioning to {next_state}")
                    return next_state
                return None
            return check_fn

        def trans_no_dialogue_and_not_in_battle(next_state: str) -> Callable:
            """Transition when dialogue is done AND not in battle."""
            def check_fn(s, v):
                if not v.get('visual_elements', {}).get('text_box_visible', False) and not s.get('game', {}).get('in_battle', False):
                    return next_state
                return None
            return check_fn

        def trans_no_dialogue_and_no_nickname_text(next_state: str) -> Callable:
            """Transition when dialogue is done AND nickname text is gone."""
            def check_fn(s, v):
                dialogue = v.get('on_screen_text', {}).get('dialogue', '') or ''
                if not v.get('visual_elements', {}).get('text_box_visible', False) and "NICKNAME" not in dialogue.upper():
                    return next_state
                return None
            return check_fn

        # --- State Machine Definition ---
        
        return {
            # === Phase 1: Title & Naming ===
            'S0_TITLE_SCREEN': BotState(
                name='S0_TITLE_SCREEN',
                description='Title screen',
                action_fn=action_press_a,
                next_state_fn=trans_has_dialogue('S1_PROF_DIALOG')
            ),
            'S1_PROF_DIALOG': BotState(
                name='S1_PROF_DIALOG',
                description='Professor Birch intro cutscene - press A until PLAYER_NAME_SET + 10 more frames',
                action_fn=action_clear_dialogue,
                next_state_fn=lambda s, v: trans_name_set_plus_frames(s, v, frames_to_wait=10)
            ),
            'S2_GENDER_NAME_SELECT': BotState(
                name='S2_GENDER_NAME_SELECT',
                description='Gender and Name selection screens',
                action_fn=action_special_naming,
                next_state_fn=trans_milestone_complete('PLAYER_NAME_SET', 'S3_TRUCK_RIDE')
            ),

            # === Phase 2: Truck & House (The "Stuck in House" Fix) ===
            'S3_TRUCK_RIDE': BotState(
                name='S3_TRUCK_RIDE',
                description='Inside the moving van',
                action_fn=action_nav(NavigationGoal(x=8, y=1, map_location='MOVING_VAN', description="Exit Van")),
                next_state_fn=trans_location_contains('HOUSE 1F', 'S4_MOM_DIALOG_1F')  # Matches both PLAYERS_HOUSE_1F and BRENDANS_HOUSE_1F
            ),
            'S4_MOM_DIALOG_1F': BotState(
                name='S4_MOM_DIALOG_1F',
                description='Mom dialogue after truck ride (1F) - multi-page dialogue',
                action_fn=action_clear_dialogue_persistent,  # Use persistent for multi-page dialogue
                next_state_fn=trans_no_dialogue('S5_NAV_TO_STAIRS_1F')
            ),
            'S5_NAV_TO_STAIRS_1F': BotState(
                name='S5_NAV_TO_STAIRS_1F',
                description='Navigate to stairs on 1F',
                action_fn=action_nav(NavigationGoal(x=8, y=2, map_location='PLAYERS_HOUSE_1F', description="Go to Stairs")),
                next_state_fn=trans_location_contains('2F', 'S6_NAV_TO_CLOCK')  # Check for 2F (works for both PLAYERS_HOUSE and BRENDANS_HOUSE)
            ),
            
            # === THE CRITICAL FIX: S6 -> S7 with area-based transition ===
            'S6_NAV_TO_CLOCK': BotState(
                name='S6_NAV_TO_CLOCK',
                description='Navigate to clock in 2F bedroom and interact',
                action_fn=action_nav(NavigationGoal(x=5, y=1, map_location='PLAYERS_HOUSE_2F', description="Interact with Clock", should_interact=True)),
                # CRITICAL: Transition when in clock AREA and dialogue appears (not exact position)
                # This handles the "adjacent-interact" bug where agent presses A from (6,1) or (5,2)
                next_state_fn=trans_area_and_dialogue(x_range=[4, 5, 6], y_range=[1, 2], next_state='S7_SET_CLOCK')
            ),
            'S7_SET_CLOCK': BotState(
                name='S7_SET_CLOCK',
                description='Setting the clock and subsequent Mom dialogue',
                action_fn=action_special_clock,
                next_state_fn=trans_no_dialogue('S8_NAV_OUT_OF_HOUSE')
            ),
            'S8_NAV_OUT_OF_HOUSE': BotState(
                name='S8_NAV_OUT_OF_HOUSE',
                description='Navigate to stairs on 2F, then exit house',
                action_fn=lambda s, v: self._action_exit_house(s, v),
                next_state_fn=trans_location_exact('LITTLEROOT TOWN', 'S9_NAV_TO_MAYS_HOUSE')
            ),
            
            # === Phase 3: Rival's House ===
            'S9_NAV_TO_MAYS_HOUSE': BotState(
                name='S9_NAV_TO_MAYS_HOUSE',
                description="Navigate to May's house",
                action_fn=action_nav(NavigationGoal(x=14, y=8, map_location='LITTLEROOT_TOWN', description="Go to May's House")),
                next_state_fn=trans_location_contains('MAYS HOUSE 1F', 'S10_MAYS_MOTHER_DIALOG')
            ),
            'S10_MAYS_MOTHER_DIALOG': BotState(
                name='S10_MAYS_MOTHER_DIALOG',
                description="May's mother dialogue (1F) - multi-page with '...' continuation",
                action_fn=action_clear_dialogue_persistent,  # Use persistent to handle multi-page dialogue
                next_state_fn=trans_no_dialogue('S11_NAV_TO_STAIRS_MAYS_HOUSE', min_wait_steps=3)  # Wait 3 steps for multi-page dialogue
            ),
            'S11_NAV_TO_STAIRS_MAYS_HOUSE': BotState(
                name='S11_NAV_TO_STAIRS_MAYS_HOUSE',
                description="Navigate to stairs in May's house (1F)",
                action_fn=action_nav(NavigationGoal(x=2, y=2, map_location='LITTLEROOT TOWN MAYS HOUSE 1F', description='Go to Stairs')),
                next_state_fn=trans_location_contains('MAYS HOUSE 2F', 'S11B_NAV_TO_POKEBALL')
            ),
            'S11B_NAV_TO_POKEBALL': BotState(
                name='S11B_NAV_TO_POKEBALL',
                description='Navigate to Pokéball on 2F and interact to trigger May',
                action_fn=action_nav(NavigationGoal(x=5, y=4, map_location='MAYS_HOUSE_2F', description="Interact with Pokéball", should_interact=True)),
                next_state_fn=trans_area_and_dialogue(x_range=[4, 5, 6], y_range=[3, 4, 5], next_state='S12_MAY_DIALOG')
            ),
            'S12_MAY_DIALOG': BotState(
                name='S12_MAY_DIALOG',
                description='May dialogue (2F) - clear dialogue then move LEFT to exit area',
                action_fn=action_clear_dialogue_then_try_move('LEFT'),
                next_state_fn=trans_left_area_only(x_range=[4, 5, 6], y_range=[3, 4, 5], next_state='S13_NAV_TO_STAIRS_2F')
            ),
            'S13_NAV_TO_STAIRS_2F': BotState(
                name='S13_NAV_TO_STAIRS_2F',
                description="Navigate to stairs on May's house 2F",
                action_fn=action_nav(NavigationGoal(x=1, y=1, map_location='LITTLEROOT TOWN MAYS HOUSE 2F', description='Go to Stairs')),
                next_state_fn=trans_location_contains('MAYS HOUSE 1F', 'S14_NAV_TO_EXIT_MAYS_HOUSE')
            ),
            'S14_NAV_TO_EXIT_MAYS_HOUSE': BotState(
                name='S14_NAV_TO_EXIT_MAYS_HOUSE',
                description="Navigate to exit on May's house 1F",
                action_fn=action_nav(NavigationGoal(x=2, y=9, map_location='LITTLEROOT TOWN MAYS HOUSE 1F', description="Exit May's House")),
                next_state_fn=trans_location_exact('LITTLEROOT TOWN', 'S15_NAV_TO_NPC_NORTH')
            ),
            'S15_NAV_TO_NPC_NORTH': BotState(
                name='S15_NAV_TO_NPC_NORTH',
                description='Navigate north to NPC area - dialogue auto-triggers',
                action_fn=action_nav(NavigationGoal(x=11, y=1, map_location='LITTLEROOT TOWN', description='Walk north (no interaction)', should_interact=False)),
                next_state_fn=trans_area_and_dialogue(x_range=[10, 11, 12], y_range=[1, 2, 3], next_state='S16_NPC_DIALOG')
            ),
            'S16_NPC_DIALOG': BotState(
                name='S16_NPC_DIALOG',
                description='NPC dialogue - clear dialogue then move UP',
                action_fn=action_clear_dialogue_then_try_move('UP'),
                next_state_fn=trans_left_area_only(x_range=[10, 11, 12], y_range=[1, 2, 3], next_state='S17_NAV_TO_ROUTE_101')
            ),
            'S17_NAV_TO_ROUTE_101': BotState(
                name='S17_NAV_TO_ROUTE_101',
                description='Move UP to Route 101 - Birch cutscene will auto-trigger',
                action_fn=action_simple(['UP']),  # Just move UP, dialogue auto-triggers after map transition
                next_state_fn=trans_has_dialogue('S18_BIRCH_DIALOG')  # Wait for Birch's "H-help me!" dialogue
            ),
            'S18_BIRCH_DIALOG': BotState(
                name='S18_BIRCH_DIALOG',
                description='Clear Birch cutscene dialogue on Route 101',
                action_fn=action_clear_dialogue,  # Clear the auto-triggered cutscene
                next_state_fn=trans_no_dialogue('S19_NAV_TO_BAG')  # Once cleared, go to bag
            ),
            'S19_NAV_TO_BAG': BotState(
                name='S19_NAV_TO_BAG',
                description="Navigate to Birch's bag on ground and interact with it",
                action_fn=action_nav(NavigationGoal(x=7, y=14, map_location='ROUTE 101', description="Interact with Birch's Bag", should_interact=True)),
                next_state_fn=trans_area_and_dialogue(x_range=[6, 7, 8], y_range=[13, 14, 15], next_state='S20_INTERACT_BAG')
            ),
            'S20_INTERACT_BAG': BotState(
                name='S20_INTERACT_BAG',
                description='Interact with bag to trigger starter menu',
                action_fn=action_clear_dialogue,
                next_state_fn=lambda s, v: (
                    'S24_NICKNAME' if "NICKNAME" in (v.get('on_screen_text', {}).get('dialogue', '') or '').upper()
                    else ('S23_BIRCH_DIALOG_2' if (
                        s.get('milestones', {}).get('STARTER_CHOSEN', {}).get('completed', False) and
                        'PROFESSOR BIRCHS LAB' in s.get('player', {}).get('location', '')
                    )
                    else ('S21_STARTER_SELECT' if "Choose a" in (v.get('on_screen_text', {}).get('dialogue', '') or '')
                    else None))
                )
            ),
            'S21_STARTER_SELECT': BotState(
                name='S21_STARTER_SELECT',
                description='Pokemon Selection from bag',
                action_fn=action_special_starter,
                next_state_fn=trans_in_battle('S22_FIRST_BATTLE')
            ),
            'S22_FIRST_BATTLE': BotState(
                name='S22_FIRST_BATTLE',
                description='First battle (Poochyena)',
                action_fn=action_pass_to_battle_bot,
                next_state_fn=trans_milestone_complete('STARTER_CHOSEN', 'S23_BIRCH_DIALOG_2')
            ),
            'S23_BIRCH_DIALOG_2': BotState(
                name='S23_BIRCH_DIALOG_2',
                description='Dialogue with Birch after battle (in lab)',
                action_fn=action_clear_dialogue,
                next_state_fn=trans_dialogue_contains("NICKNAME", 'S24_NICKNAME')
            ),
            'S24_NICKNAME': BotState(
                name='S24_NICKNAME',
                description='Nickname starter screen',
                action_fn=action_special_nickname,
                next_state_fn=trans_no_dialogue_and_no_nickname_text('S25_LEAVE_LAB')
            ),
            'S25_LEAVE_LAB': BotState(
                name='S25_LEAVE_LAB',
                description="Leave Birch's Lab",
                action_fn=action_nav(NavigationGoal(x=6, y=13, map_location='BIRCHS_LAB', description="Exit Lab")),
                next_state_fn=trans_location_exact('LITTLEROOT TOWN', 'COMPLETED')  # Exact match - not inside lab!
            ),
            
            # === Final State ===
            'COMPLETED': BotState(
                name='COMPLETED',
                description='Opening sequence complete - hand off to VLM/A*',
                action_fn=lambda s, v: None,
                next_state_fn=lambda s, v: None
            )
        }

    def _action_exit_house(self, state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> Union[List[str], NavigationGoal]:
        """
        Multi-phase house exit: 2F -> stairs -> 1F -> door
        Stairs are WALK-ON tiles - just navigate to them, don't press directions!
        
        On 1F: Uses waypoint navigation to avoid table obstacle.
        - From mom's position (4,5), go RIGHT to (8,5) to clear the table
        - Then go DOWN to door at (4,7)
        
        NOTE: Dialogue clearing is handled by get_action's early return logic.
        Do NOT clear dialogue here - it bypasses VLM executor and doesn't check for player monologues.
        """
        player_location = state_data.get('player', {}).get('location', '')
        player_pos = state_data.get('player', {}).get('position', {})
        x, y = player_pos.get('x', 0), player_pos.get('y', 0)
        
        if '2F' in player_location:
            # Phase 1: Navigate to stairs on 2F (walk-on tile at 7, 1)
            logger.info(f"[EXIT HOUSE] Phase 1: At ({x},{y}), navigating to 2F stairs (7,1)")
            return NavigationGoal(x=7, y=1, map_location='PLAYERS_HOUSE_2F', description="2F Stairs")
        
        elif '1F' in player_location:
            # Phase 2: Navigate to door on 1F
            # Door is at (8, 9) and (9, 9) - south wall of the house
            # Mom's position is (4,5), table may block some paths
            
            # Simple navigation: just go to the door at (8,9)
            logger.info(f"[EXIT HOUSE] Phase 2: At ({x},{y}), navigating to door (8,9)")
            return NavigationGoal(x=8, y=9, map_location='PLAYERS_HOUSE_1F', description="Exit House")
        
        else:
            logger.warning(f"[EXIT HOUSE] Unknown location: {player_location}")
            return None

    def get_state_summary(self) -> Dict[str, Any]:
        """Get current state summary for debugging/monitoring"""
        state = self.states.get(self.current_state_name)
        elapsed = time.time() - self.state_entry_time if state else 0
        
        return {
            'current_state': self.current_state_name,
            'state_description': state.description if state else 'Unknown',
            'attempt_count': self.state_attempt_count,
            'max_attempts': state.max_attempts if state else 0,
            'elapsed_seconds': elapsed,
            'timeout_seconds': state.timeout_seconds if state else 0,
            'last_action': self.last_action,
            'state_history_length': len(self.state_history)
        }
    
    def reset(self):
        """Reset the opener bot to initial state"""
        self.current_state_name = 'S0_TITLE_SCREEN'
        self.state_entry_time = time.time()
        self.state_attempt_count = 0
        self.last_action = None
        self.state_history.clear()
        logger.info("[OPENER BOT] Reset to S0_TITLE_SCREEN state")


# === Global Instance Management ===

_global_opener_bot: Optional[OpenerBot] = None


def get_opener_bot() -> OpenerBot:
    """Get or create the global opener bot instance"""
    global _global_opener_bot
    if _global_opener_bot is None:
        _global_opener_bot = OpenerBot()
    return _global_opener_bot
