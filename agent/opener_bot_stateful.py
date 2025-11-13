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
        
        CRITICAL FIX: Opener bot completes when RECEIVED_POKEDEX milestone is reached.
        This prevents reactivation when agent returns to Birch's Lab after rival battle.
        """
        if self.current_state_name == 'COMPLETED':
            return False
            
        # Check if we've completed the opener sequence
        milestones = state_data.get('milestones', {})
        
        # FIXED: Check for RECEIVED_POKEDEX instead of just STARTER_CHOSEN + location
        # The agent comes BACK to the lab after beating rival to get the Pokedex.
        # We only want to deactivate after truly completing the opener sequence.
        if milestones.get('RECEIVED_POKEDEX', {}).get('completed', False):
            logger.info("[OPENER BOT] Received Pokedex - opener sequence complete. Handing off to VLM.")
            self._transition_to_state('COMPLETED')
            return False
        
        # Legacy check: Also deactivate if starter chosen and outside lab (safety net)
        if milestones.get('STARTER_CHOSEN', {}).get('completed', False):
            player_loc = state_data.get('player', {}).get('location', '')
            if 'BIRCHS_LAB' not in player_loc and 'BIRCH LAB' not in player_loc:
                logger.info("[OPENER BOT] Starter chosen and outside lab (before Pokedex). Handing off to VLM.")
                self._transition_to_state('COMPLETED')
                return False
        
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
        state = self.states.get(self.current_state_name)
        if not state:
            logger.error(f"[OPENER BOT] In unknown state {self.current_state_name}, completing.")
            self._transition_to_state('COMPLETED')
            return None

        # 1. Check Safety Fallbacks
        self.state_attempt_count += 1
        elapsed = time.time() - self.state_entry_time
        if self.state_attempt_count > state.max_attempts or elapsed > state.timeout_seconds:
            logger.warning(f"[OPENER BOT] ⚠️ SAFETY FALLBACK: State {state.name} timed out! Handing off to VLM.")
            self._transition_to_state('COMPLETED')
            return None

        # 2. Check for State Transition
        if state.next_state_fn:
            try:
                next_state_name = state.next_state_fn(state_data, visual_data)
                if next_state_name:
                    logger.info(f"[OPENER BOT] ✅ State {state.name} transition condition MET. Moving to {next_state_name}.")
                    self._transition_to_state(next_state_name)
                    # Get the NEW state after transition
                    state = self.states[self.current_state_name]
            except Exception as e:
                logger.error(f"[OPENER BOT] Error in next_state_fn for {state.name}: {e}")
                self._transition_to_state('COMPLETED')
                return None

        # 3. Execute Current State's Action
        action_or_goal = None
        if state.action_fn:
            try:
                action_or_goal = state.action_fn(state_data, visual_data)
                self.last_action = action_or_goal
                if isinstance(action_or_goal, NavigationGoal):
                    logger.info(f"[OPENER BOT] State: {state.name} | Goal: {action_or_goal.description}")
                else:
                    logger.info(f"[OPENER BOT] State: {state.name} | Action: {action_or_goal} | Attempt: {self.state_attempt_count}")
            except Exception as e:
                logger.error(f"[OPENER BOT] Error in action_fn for {state.name}: {e}")
                
        return action_or_goal
        
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
            """Press A if dialogue is visible, otherwise do nothing."""
            if v.get('visual_elements', {}).get('text_box_visible', False):
                return ['A']
            return None

        def action_nav(goal: NavigationGoal):
            """Factory for navigation actions. Clears dialogue or returns NavGoal."""
            def nav_fn(s, v):
                if v.get('visual_elements', {}).get('text_box_visible', False):
                    return ['A']
                return goal
            return nav_fn

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
            """Handles the clock UI."""
            dialogue = v.get('on_screen_text', {}).get('dialogue', '').upper()
            if "SET THE CLOCK" in dialogue or "IS THIS TIME" in dialogue:
                return ['A']
            if v.get('visual_elements', {}).get('text_box_visible', False):
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
                if text.upper() in v.get('on_screen_text', {}).get('dialogue', '').upper():
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
                if loc_name.upper() in s.get('player', {}).get('location', '').upper():
                    return next_state
                return None
            return check_fn

        def trans_no_dialogue(next_state: str) -> Callable:
            """Transition when dialogue is no longer visible."""
            def check_fn(s, v):
                if not v.get('visual_elements', {}).get('text_box_visible', False):
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
                dialogue = v.get('on_screen_text', {}).get('dialogue', '').upper()
                if not v.get('visual_elements', {}).get('text_box_visible', False) and "NICKNAME" not in dialogue:
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
                next_state_fn=trans_location_contains('PLAYERS_HOUSE_2F', 'S6_NAV_TO_CLOCK')
            ),
            
            # === THE CRITICAL FIX: S6 -> S7 with area-based transition ===
            'S6_NAV_TO_CLOCK': BotState(
                name='S6_NAV_TO_CLOCK',
                description='Navigate to clock in 2F bedroom',
                action_fn=action_nav(NavigationGoal(x=5, y=1, map_location='PLAYERS_HOUSE_2F', description="Go to Clock")),
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
                next_state_fn=trans_location_contains('LITTLEROOT_TOWN', 'S9_NAV_TO_MAYS_HOUSE')
            ),
            
            # === Phase 3: Rival's House ===
            'S9_NAV_TO_MAYS_HOUSE': BotState(
                name='S9_NAV_TO_MAYS_HOUSE',
                description="Navigate to May's house",
                action_fn=action_nav(NavigationGoal(x=12, y=7, map_location='LITTLEROOT_TOWN', description="Go to May's House")),
                next_state_fn=trans_location_contains('MAYS_HOUSE_1F', 'S10_MAYS_MOTHER_DIALOG')
            ),
            'S10_MAYS_MOTHER_DIALOG': BotState(
                name='S10_MAYS_MOTHER_DIALOG',
                description="May's mother dialogue (1F)",
                action_fn=action_clear_dialogue,
                next_state_fn=trans_no_dialogue('S11_NAV_TO_MAY')
            ),
            'S11_NAV_TO_MAY': BotState(
                name='S11_NAV_TO_MAY',
                description='Navigate to May (2F)',
                action_fn=action_nav(NavigationGoal(x=4, y=2, map_location='MAYS_HOUSE_2F', description="Go to May")),
                next_state_fn=trans_area_and_dialogue(x_range=[3, 4, 5], y_range=[1, 2, 3], next_state='S12_MAY_DIALOG')
            ),
            'S12_MAY_DIALOG': BotState(
                name='S12_MAY_DIALOG',
                description='May dialogue (2F)',
                action_fn=action_clear_dialogue,
                next_state_fn=trans_no_dialogue('S13_LEAVE_MAYS_HOUSE')
            ),
            'S13_LEAVE_MAYS_HOUSE': BotState(
                name='S13_LEAVE_MAYS_HOUSE',
                description="Leave May's house",
                action_fn=action_nav(NavigationGoal(x=4, y=7, map_location='MAYS_HOUSE_1F', description="Exit May's House")),
                next_state_fn=trans_location_contains('LITTLEROOT_TOWN', 'S14_NAV_TO_ROUTE_101')
            ),

            # === Phase 4: Route 101 & Starter Selection ===
            'S14_NAV_TO_ROUTE_101': BotState(
                name='S14_NAV_TO_ROUTE_101',
                description='Navigate north to Route 101',
                action_fn=action_nav(NavigationGoal(x=5, y=0, map_location='LITTLEROOT_TOWN', description="Go to Route 101")),
                next_state_fn=trans_location_contains('ROUTE_101', 'S15_BIRCH_DIALOG')
            ),
            'S15_BIRCH_DIALOG': BotState(
                name='S15_BIRCH_DIALOG',
                description='Dialogue with Birch on Route 101',
                action_fn=action_clear_dialogue,
                next_state_fn=trans_no_dialogue_and_not_in_battle('S16_NAV_TO_BAG')
            ),
            'S16_NAV_TO_BAG': BotState(
                name='S16_NAV_TO_BAG',
                description="Navigate to Birch's bag",
                action_fn=action_nav(NavigationGoal(x=5, y=7, map_location='ROUTE_101', description="Go to Birch's Bag")),
                next_state_fn=trans_area_and_dialogue(x_range=[4, 5, 6], y_range=[6, 7, 8], next_state='S17_STARTER_SELECT')
            ),
            'S17_STARTER_SELECT': BotState(
                name='S17_STARTER_SELECT',
                description='Pokemon Selection from bag',
                action_fn=action_special_starter,
                next_state_fn=trans_in_battle('S18_FIRST_BATTLE')
            ),
            'S18_FIRST_BATTLE': BotState(
                name='S18_FIRST_BATTLE',
                description='First battle (Poochyena)',
                action_fn=action_pass_to_battle_bot,
                next_state_fn=trans_milestone_complete('STARTER_CHOSEN', 'S19_BIRCH_DIALOG_2')
            ),
            'S19_BIRCH_DIALOG_2': BotState(
                name='S19_BIRCH_DIALOG_2',
                description='Dialogue with Birch after battle (in lab)',
                action_fn=action_clear_dialogue,
                next_state_fn=trans_dialogue_contains("NICKNAME", 'S20_NICKNAME')
            ),
            'S20_NICKNAME': BotState(
                name='S20_NICKNAME',
                description='Nickname starter screen',
                action_fn=action_special_nickname,
                next_state_fn=trans_no_dialogue_and_no_nickname_text('S21_LEAVE_LAB')
            ),
            'S21_LEAVE_LAB': BotState(
                name='S21_LEAVE_LAB',
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
        CORRECTED: Stairs are at (8, 2) on both floors
        """
        player_location = state_data.get('player', {}).get('location', '')
        player_pos = state_data.get('player', {}).get('position', {})
        x, y = player_pos.get('x', 0), player_pos.get('y', 0)
        
        # Clear any dialogue first
        if visual_data.get('visual_elements', {}).get('text_box_visible', False):
            return ['A']
        
        if '2F' in player_location:
            # Phase 1: Navigate to stairs on 2F
            if x == 8 and y == 2:
                logger.info("[EXIT HOUSE] At 2F stairs (8,2), going DOWN")
                return ['DOWN']
            logger.info(f"[EXIT HOUSE] Phase 1: At ({x},{y}), navigating to 2F stairs (8,2)")
            return NavigationGoal(x=8, y=2, map_location='PLAYERS_HOUSE_2F', description="Go to Stairs (2F)")
        
        elif '1F' in player_location:
            # Phase 2: Navigate to door on 1F
            logger.info(f"[EXIT HOUSE] Phase 2: At ({x},{y}), navigating to door (4,7)")
            return NavigationGoal(x=4, y=7, map_location='PLAYERS_HOUSE_1F', description="Exit House")
        
        else:
            logger.warning(f"[EXIT HOUSE] Unknown location: {player_location}")
            return None
