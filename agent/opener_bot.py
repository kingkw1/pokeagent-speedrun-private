"""
Opener Bot - STATEFUL State Machine for Game Opening (Splits 0-4)

This module implements a STATEFUL rule-based controller that reliably handles
the deterministic opening sequence of Pokemon Emerald.

CRITICAL ARCHITECTURAL CHANGE:
- The bot now REMEMBERS its current state (self.current_state_name)
- Each frame, it only checks TRANSITION CONDITIONS from the current state
- This solves the "stateless Catch-22" where S6_NAV_TO_CLOCK and S8_NAV_OUT_OF_HOUSE
  would oscillate because both matched at the same time
- States use explicit next_state_fn to define when they're complete

Design Philosophy:
- Memory state (milestones, game_state) as PRIMARY signal (100% reliable)
- Visual elements (text_box_visible) as SECONDARY (85% reliable)
- VLM text parsing as TERTIARY hint only (60% reliable)
- Stateful transitions prevent mid-sequence state jumping
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

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
        
        if self.current_state_name == 'COMPLETED':
            print("[OPENER BOT SHOULD_HANDLE] State is COMPLETED, returning False")
            return False
            
        # Check if we've completed the opener sequence
        milestones = state_data.get('milestones', {})
        starter_chosen = milestones.get('STARTER_CHOSEN', {}).get('completed', False)
        player_loc = state_data.get('player', {}).get('location', '')
        
        print(f"🤖 [OPENER BOT SHOULD_HANDLE] Starter chosen: {starter_chosen}, Player location: {player_loc}")
        
        if starter_chosen:
            if 'BIRCHS_LAB' not in player_loc:
                print("[OPENER BOT] Starter chosen and outside lab. Handing off to VLM.")
                self._transition_to_state('COMPLETED')
                return False
        
        print(f"🤖 [OPENER BOT SHOULD_HANDLE] Bot is ACTIVE, will handle action")
        return True  # Bot is active

    def get_action(self, state_data: Dict[str, Any], visual_data: Dict[str, Any], 
                   current_plan: str = "") -> Union[List[str], NavigationGoal, None]:
        """
        Main stateful logic loop:
        1. Get current state
        2. Check safety fallbacks
        3. Check if state's transition condition is met (if yes, transition)
        4. Execute current state's action
        """
        # Debug: Show what data we received
        player_pos = state_data.get('player', {}).get('position', {})
        player_loc = state_data.get('player', {}).get('location', '')
        print(f"🤖 [OPENER BOT GET_ACTION] ========================================")
        print(f"🤖 [OPENER BOT GET_ACTION] Current state: {self.current_state_name}")
        print(f"🤖 [OPENER BOT GET_ACTION] Player position: ({player_pos.get('x', '?')}, {player_pos.get('y', '?')})")
        print(f"🤖 [OPENER BOT GET_ACTION] Player location: {player_loc}")
        print(f"🤖 [OPENER BOT GET_ACTION] Attempt: {self.state_attempt_count + 1}")
        
        # AUTO-DETECT STARTING STATE on first call
        if not self.initialized_state:
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
        if 'BIRCHS_LAB' in player_loc or 'BIRCH' in player_loc:
            print(f"🔍 [STATE DETECTION] In Birch's Lab!")
            if milestones.get('STARTER_CHOSEN', {}).get('completed', False):
                return 'S23_BIRCH_DIALOG_2'  # After getting starter
            else:
                return 'S20_INTERACT_BAG'  # Interacting with bag
        
        # Littleroot Town (OVERWORLD) - the critical case!
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
        
        # Check for May's house (before player's house - both contain "HOUSE")
        if 'MAYS HOUSE' in player_loc or ('MAY' in player_loc and 'HOUSE' in player_loc):
            print(f"🔍 [STATE DETECTION] In May's house!")
            if '2F' in player_loc:
                return 'S11B_NAV_TO_POKEBALL'  # On 2F
            else:
                return 'S10_MAYS_MOTHER_DIALOG'  # On 1F
        
        # Check if we're in player's house (Brendan's house)
        if ('PLAYERS_HOUSE' in player_loc or 'BRENDANS_HOUSE' in player_loc or 
            ('BRENDAN' in player_loc and 'HOUSE' in player_loc)):
            print(f"🔍 [STATE DETECTION] In player's house!")
            if '2F' in player_loc:
                # On 2nd floor - setting clock or leaving
                return 'S6_NAV_TO_CLOCK'
            else:
                # On 1st floor - Mom dialogue or navigating to stairs
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
            """Press A if dialogue is detected through any method."""
            screen_context = v.get('screen_context', '').lower()
            text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
            continue_prompt_visible = v.get('visual_elements', {}).get('continue_prompt_visible', False)
            game_state = s.get('game', {}).get('game_state', '').lower()
            
            # Press A if ANY indicator shows we're in dialogue
            if text_box_visible or screen_context == 'dialogue' or game_state == 'dialog' or continue_prompt_visible:
                return ['A']
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
            """Factory for navigation actions. Clears dialogue or returns NavGoal."""
            def nav_fn(s, v):
                if v.get('visual_elements', {}).get('text_box_visible', False):
                    return ['A']
                return goal
            return nav_fn

        def action_simple(actions: List[str]):
            """Returns a simple action (like ['UP']) every time. No dialogue clearing."""
            def simple_fn(s, v):
                return actions
            return simple_fn

        def action_special_naming(s, v):
            """Handles gender and name selection screens."""
            dialogue = v.get('on_screen_text', {}).get('dialogue', '').upper()
            if "ARE YOU A BOY" in dialogue:
                return ['A']
            if "YOUR NAME IS" in dialogue:
                return ['START']
            if "IS THIS YOUR NAME" in dialogue:
                return ['A']
            if v.get('visual_elements', {}).get('text_box_visible', False):
                return ['A']
            return None

        def action_special_clock(s, v):
            """
            Handles the clock UI including the Yes/No confirmation.
            
            Clock sequence:
            1. "The clock..." - press A
            2. "Better set the clock..." - press A to set time
            3. "Is this the correct time?" with Yes/No menu - press UP then A
            """
            dialogue = v.get('on_screen_text', {}).get('dialogue', '').upper()
            
            # Check if we're at the "Is this the correct time?" dialogue
            if "IS THIS" in dialogue and "CORRECT TIME" in dialogue:
                # Yes/No menu - press UP to select Yes, then A to confirm
                print(f"🕐 [CLOCK] Yes/No menu detected, pressing UP then A")
                return ['UP', 'A']
            
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
            """Handles nickname screen."""
            dialogue = v.get('on_screen_text', {}).get('dialogue', '').upper()
            if "NICKNAME" in dialogue:
                return ['B']
            if "ARE YOU SURE" in dialogue:
                return ['A']
            if v.get('visual_elements', {}).get('text_box_visible', False):
                return ['A']
            return None
            
        def action_pass_to_battle_bot(s, v):
            """Do nothing - lets main action.py call Battle Bot."""
            return None

        # --- Transition Check Functions (FIXED: Return state names, not True/None) ---
        
        def trans_game_state_not(state_value: str, next_state: str) -> Callable:
            """Transition when game_state is NOT the given value."""
            def check_fn(s, v):
                if s.get('game', {}).get('game_state', '').lower() != state_value.lower():
                    return next_state
                return None
            return check_fn

        def trans_dialogue_contains(text: str, next_state: str) -> Callable:
            """Transition when dialogue contains specific text."""
            def check_fn(s, v):
                dialogue = v.get('on_screen_text', {}).get('dialogue', '') or ''
                if text.upper() in dialogue.upper():
                    return next_state
                return None
            return check_fn

        def trans_milestone_complete(milestone_id: str, next_state: str) -> Callable:
            """Transition when milestone is completed."""
            def check_fn(s, v):
                if s.get('milestones', {}).get(milestone_id, {}).get('completed', False):
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

        def trans_no_dialogue(next_state: str) -> Callable:
            """Transition when dialogue is no longer visible AND game state confirms not in dialog."""
            def check_fn(s, v):
                screen_context = v.get('screen_context', '').lower()
                text_box_visible = v.get('visual_elements', {}).get('text_box_visible', False)
                continue_prompt_visible = v.get('visual_elements', {}).get('continue_prompt_visible', False)
                game_state = s.get('game', {}).get('game_state', '').lower()
                
                # Only transition if ALL FOUR conditions indicate no dialogue:
                # 1. No text box visible
                # 2. Screen context is not 'dialogue' 
                # 3. Game state is not 'dialog'
                # 4. No continue prompt (red triangle) visible
                if not text_box_visible and screen_context != 'dialogue' and game_state != 'dialog' and not continue_prompt_visible:
                    return next_state
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
            """
            def check_fn(s, v):
                pos = s.get('player', {}).get('position', {})
                x, y = pos.get('x', -1), pos.get('y', -1)
                if x in x_range and y in y_range and v.get('visual_elements', {}).get('text_box_visible', False):
                    return next_state
                return None
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
                next_state_fn=trans_game_state_not('title', 'S1_PROF_DIALOG')
            ),
            'S1_PROF_DIALOG': BotState(
                name='S1_PROF_DIALOG',
                description='Professor Birch intro dialogue',
                action_fn=action_clear_dialogue,
                next_state_fn=trans_dialogue_contains("ARE YOU A BOY", 'S2_GENDER_NAME_SELECT')
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
                next_state_fn=trans_location_contains('PLAYERS_HOUSE_1F', 'S4_MOM_DIALOG_1F')
            ),
            'S4_MOM_DIALOG_1F': BotState(
                name='S4_MOM_DIALOG_1F',
                description='Mom dialogue after truck ride (1F)',
                action_fn=action_clear_dialogue,
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
                description="May's mother dialogue (1F)",
                action_fn=action_clear_dialogue,
                next_state_fn=trans_no_dialogue('S11_NAV_TO_STAIRS_MAYS_HOUSE')
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
                next_state_fn=trans_dialogue_contains("Choose a", 'S21_STARTER_SELECT')
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
                action_fn=action_nav(NavigationGoal(x=5, y=8, map_location='BIRCHS_LAB', description="Exit Lab")),
                next_state_fn=trans_location_contains('LITTLEROOT_TOWN', 'COMPLETED')
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
        """
        player_location = state_data.get('player', {}).get('location', '')
        player_pos = state_data.get('player', {}).get('position', {})
        x, y = player_pos.get('x', 0), player_pos.get('y', 0)
        
        # Clear any dialogue first
        if visual_data.get('visual_elements', {}).get('text_box_visible', False):
            return ['A']
        
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
