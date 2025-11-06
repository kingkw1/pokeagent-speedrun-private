"""
Opener Bot - Programmatic State Machine for Game Opening (Splits 0-4)

This module implements a rule-based controller that reliably handles the deterministic
opening sequence of Pokemon Emerald, bypassing VLM unreliability on these tasks.

Design Philosophy:
- Memory state (milestones, game_state) as PRIMARY signal (100% reliable)
- Visual elements (text_box_visible, red triangle) as SECONDARY (85% reliable)
- VLM text parsing as TERTIARY hint only (60% reliable)
- Always return None to fallback to VLM when uncertain

State Coverage:
- Split 0: Title screen and game initialization
- Split 1: Name selection and character creation
- Split 2: Moving van dialogue and exit
- Split 3: Player's house navigation
- Split 4: Reaching Route 101

Safety Features:
- Time limits (30s per state)
- Step count limits (5 repeated actions)
- Milestone verification
- Automatic VLM fallback on uncertainty
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class NavigationGoal:
    """A data class to represent a navigation sub-goal for the A* Navigator."""
    x: int
    y: int
    map_location: str  # e.g., 'PLAYERS_HOUSE_2F'
    description: str

@dataclass
class BotState:
    """Represents a state in the opener bot state machine"""
    name: str
    description: str
    
    # Detection criteria
    milestone_check: Optional[str] = None
    milestone_incomplete: Optional[str] = None
    memory_check: Optional[Callable[[Dict[str, Any]], bool]] = None
    visual_check: Optional[Callable[[Dict[str, Any]], bool]] = None  # Check VLM perception data
    
    # Action or Goal
    action_fn: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Union[List[str], 'NavigationGoal', None]]] = None
    simple_action: Optional[List[str]] = None
    nav_goal: Optional['NavigationGoal'] = None  # NEW: For A* Navigator
    
    # Transition
    next_state: Optional[str] = None
    max_attempts: int = 20  # Increased from 10 to allow for VLM processing overhead
    timeout_seconds: float = 120.0  # Increased from 30s - VLM takes 3-5s per action


class OpenerBot:
    """
    Programmatic state machine for Pokemon Emerald opening sequence.
    
    Handles deterministic early game states (title screen, name selection, moving van, etc.)
    with high reliability by using memory state and milestone tracking as primary signals.
    """
    
    def __init__(self):
        """Initialize the opener bot with state machine configuration"""
        self.current_state_name = 'IDLE'
        self.state_entry_time = time.time()
        self.state_attempt_count = 0
        self.last_action = None
        
        # Track state history for debugging
        self.state_history: List[tuple] = []  # (state_name, timestamp, action_taken)
        
        # Define the state machine
        self.states = self._build_state_machine()
        
        logger.info("[OPENER BOT] Initialized with state machine covering Splits 0-4")
    
    def _build_state_machine(self) -> Dict[str, BotState]:
        """
        Builds the state machine to act as a "Local Sub-Goal Manager."
        It directs the A* Navigator by setting navigation goals,
        and only takes direct action for special UI screens.
        """
        
        # --- Helper Action Functions ---

        def action_handle_dialogue(state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> Optional[List[str]]:
            """Returns ['A'] if dialogue is visible, else None to transition."""
            if visual_data.get('visual_elements', {}).get('text_box_visible', False):
                return ['A']
            return None  # No dialogue, so state is complete.
        
        def check_dialogue_visible(visual_data: Dict[str, Any]) -> bool:
            """Helper to check if dialogue is currently visible"""
            return visual_data.get('visual_elements', {}).get('text_box_visible', False)

        def action_handle_navigation_or_dialogue(nav_goal: NavigationGoal) -> Callable:
            """
            Factory for navigation states.
            1. Clears dialogue with ['A'].
            2. Returns a NavigationGoal for the A* Navigator.
            """
            def action_fn(state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> Union[List[str], NavigationGoal]:
                if visual_data.get('visual_elements', {}).get('text_box_visible', False):
                    return ['A']  # Clear dialogue
                return nav_goal  # Pass navigation goal to A*
            return action_fn

        def action_special_naming(state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> Optional[List[str]]:
            """Handles Gender, Name, and Confirm screens. Fixes 'AAAAAA' bug."""
            dialogue = visual_data.get('on_screen_text', {}).get('dialogue', '').upper()
            if "ARE YOU A BOY" in dialogue: return ['A']
            if "YOUR NAME IS" in dialogue: return ['START']
            if "IS THIS YOUR NAME" in dialogue: return ['A']
            if visual_data.get('visual_elements', {}).get('text_box_visible', False):
                 return ['A']
            return None

        def action_special_clock(state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> Optional[List[str]]:
            """Handles the clock setting UI and subsequent dialogue.
            
            Expected sequence:
            1. Press A to set clock (shows current time)
            2. "Is this the correct time?" - Default is "No", need to press UP to select "Yes"
            3. Press A to confirm "Yes"
            4. Clear any follow-up dialogue
            """
            dialogue = visual_data.get('on_screen_text', {}).get('dialogue', '').upper()
            
            # Step 2: Yes/No question - need to select "Yes" (default is "No")
            if "IS THIS" in dialogue and ("CORRECT" in dialogue or "RIGHT" in dialogue):
                # First time seeing this question, press UP to select "Yes"
                logger.info("[CLOCK] Detected Yes/No question - selecting 'Yes' with UP")
                return ['UP', 'A']  # UP to select Yes, then A to confirm
            
            # Step 1: Initial clock interaction or time display
            if "SET THE CLOCK" in dialogue or "CLOCK" in dialogue:
                logger.info("[CLOCK] Interacting with clock - pressing A")
                return ['A']
            
            # Step 4: Clear any remaining dialogue
            if visual_data.get('visual_elements', {}).get('text_box_visible', False):
                logger.info("[CLOCK] Clearing dialogue - pressing A")
                return ['A']
            
            # Done with clock sequence
            logger.info("[CLOCK] Clock sequence complete")
            return None

        def action_special_starter_select(state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> Optional[List[str]]:
            """Handles selecting the Pokemon from Birch's bag."""
            dialogue = visual_data.get('on_screen_text', {}).get('dialogue', '').upper()
            menu_title = visual_data.get('on_screen_text', {}).get('menu_title', '').upper()
            if "CHOOSE A POKéMON" in dialogue or "BAG" in menu_title:
                return ['A']  # Select first Pokemon
            if "DO YOU CHOOSE THIS" in dialogue:
                return ['A']  # Confirm "YES"
            if visual_data.get('visual_elements', {}).get('text_box_visible', False):
                 return ['A']
            return None

        def action_special_nickname(state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> Optional[List[str]]:
            """Handles the nickname screen with B -> A."""
            dialogue = visual_data.get('on_screen_text', {}).get('dialogue', '').upper()
            if "NICKNAME" in dialogue: return ['B']
            if "ARE YOU SURE" in dialogue: return ['A']
            if visual_data.get('visual_elements', {}).get('text_box_visible', False):
                 return ['A']
            return None

        # --- State Machine Definition ---
        
        return {
            'IDLE': BotState(name='IDLE', description='Waiting', next_state='S0_TITLE_SCREEN'),

            # === Phase 1: Title & Naming (Before PLAYER_NAME_SET) ===
            'S0_TITLE_SCREEN': BotState(
                name='S0_TITLE_SCREEN',
                description='Title screen',
                milestone_incomplete='PLAYER_NAME_SET',
                memory_check=lambda s: s.get('game', {}).get('game_state', '').lower() == 'title',
                simple_action=['A'],
                next_state='S1_PROF_DIALOG'
            ),
            'S1_PROF_DIALOG': BotState(
                name='S1_PROF_DIALOG',
                description='Professor Birch intro dialogue',
                milestone_incomplete='PLAYER_NAME_SET',
                action_fn=action_handle_dialogue,
                next_state='S2_GENDER_NAME_SELECT'
            ),
            'S2_GENDER_NAME_SELECT': BotState(
                name='S2_GENDER_NAME_SELECT',
                description='Gender and Name selection screens',
                milestone_incomplete='PLAYER_NAME_SET',
                action_fn=action_special_naming,
                next_state='S3_TRUCK_RIDE'
            ),

            # === Phase 2: Truck & House (Fixes "Stuck in House" Bug) ===
            'S3_TRUCK_RIDE': BotState(
                name='S3_TRUCK_RIDE',
                description='Inside the moving van',
                milestone_check='PLAYER_NAME_SET',
                memory_check=lambda s: s.get('player', {}).get('location', '') == 'MOVING_VAN',
                # Goal: Exit the van (door is at (8, 1))
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=8, y=1, map_location='MOVING_VAN', description="Exit Van")
                ),
                next_state='S4_MOM_DIALOG_1F'
            ),
            'S4_MOM_DIALOG_1F': BotState(
                name='S4_MOM_DIALOG_1F',
                description='Mom dialogue after truck ride (1F) - ONLY when dialogue visible',
                milestone_check='PLAYER_NAME_SET',
                memory_check=lambda s: 'HOUSE 1F' in s.get('player', {}).get('location', '').upper(),
                visual_check=lambda v: v.get('visual_elements', {}).get('text_box_visible', False) == True,  # VLM confirms dialogue
                action_fn=action_handle_dialogue,
                max_attempts=20,  # Allow more attempts for multi-box dialogue
                timeout_seconds=120.0,  # Longer timeout due to VLM processing overhead (3-5s per action)
                next_state='S5_NAV_TO_STAIRS'
            ),
            'S5_NAV_TO_STAIRS': BotState(
                name='S5_NAV_TO_STAIRS',
                description='Navigate to stairs (1F) - ONLY when no dialogue',
                milestone_check='PLAYER_NAME_SET',
                memory_check=lambda s: 'HOUSE 1F' in s.get('player', {}).get('location', '').upper(),
                visual_check=lambda v: v.get('visual_elements', {}).get('text_box_visible', False) == False,  # VLM confirms NO dialogue
                # Goal: Go to stairs to 2F (at (8, 1) - stairs position)
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=8, y=1, map_location='PLAYERS_HOUSE_1F', description="Go to Stairs")
                ),
                next_state='S6_NAV_TO_CLOCK'
            ),
            'S6_NAV_TO_CLOCK': BotState(
                name='S6_NAV_TO_CLOCK',
                description='Navigate to clock in 2F bedroom',
                milestone_check='PLAYER_NAME_SET',
                memory_check=lambda s: 'HOUSE 2F' in s.get('player', {}).get('location', '').upper(),
                # Exclude clock dialogue - that's S7's job
                visual_check=lambda v: not ("CLOCK" in (v.get('on_screen_text', {}).get('dialogue') or '').upper() or 
                                            "IS THIS" in (v.get('on_screen_text', {}).get('dialogue') or '').upper()),
                # Goal: Go to clock at (5,1) - player moves from stairs (8,2) → LEFT → LEFT → UP → interact
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=5, y=1, map_location='PLAYERS_HOUSE_2F', description="Go to Clock")
                ),
                next_state='S7_SET_CLOCK'
            ),
            'S7_SET_CLOCK': BotState(
                name='S7_SET_CLOCK',
                description='Setting the clock and subsequent Mom dialogue',
                milestone_check='PLAYER_NAME_SET',
                memory_check=lambda s: 'HOUSE 2F' in s.get('player', {}).get('location', '').upper(),
                # Detect clock dialogue
                visual_check=lambda v: ("CLOCK" in (v.get('on_screen_text', {}).get('dialogue') or '').upper() or
                                       "IS THIS" in (v.get('on_screen_text', {}).get('dialogue') or '').upper() or
                                       v.get('visual_elements', {}).get('text_box_visible', False)),
                action_fn=action_special_clock,  # Special handler
                next_state='S8_NAV_OUT_OF_HOUSE'
            ),
            'S8_NAV_OUT_OF_HOUSE': BotState(
                name='S8_NAV_OUT_OF_HOUSE',
                description='Navigate out of the house (from 2F)',
                milestone_check='PLAYER_NAME_SET',
                memory_check=lambda s: 'HOUSE' in s.get('player', {}).get('location', '').upper() and 'LAB' not in s.get('player', {}).get('location', '').upper(),
                # Goal: Go to exit (1F, at (4, 7))
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=4, y=7, map_location='PLAYERS_HOUSE_1F', description="Exit House")
                ),
                next_state='S9_NAV_TO_MAYS_HOUSE'
            ),
            
            # === Phase 3: Rival's House (Before ROUTE_101) ===
            'S9_NAV_TO_MAYS_HOUSE': BotState(
                name='S9_NAV_TO_MAYS_HOUSE',
                description='Navigate to May\'s house',
                milestone_check='LITTLEROOT_TOWN',
                memory_check=lambda s: 'LITTLEROOT_TOWN' in s.get('player', {}).get('location', ''),
                # Goal: Go to rival's house door (at (12, 7))
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=12, y=7, map_location='LITTLEROOT_TOWN', description="Go to May's House")
                ),
                next_state='S10_MAYS_MOTHER_DIALOG'
            ),
            'S10_MAYS_MOTHER_DIALOG': BotState(
                name='S10_MAYS_MOTHER_DIALOG',
                description='May\'s mother dialogue (1F)',
                milestone_check='LITTLEROOT_TOWN',
                memory_check=lambda s: 'MAYS_HOUSE_1F' in s.get('player', {}).get('location', ''),
                action_fn=action_handle_dialogue,
                next_state='S11_NAV_TO_MAY'
            ),
            'S11_NAV_TO_MAY': BotState(
                name='S11_NAV_TO_MAY',
                description='Navigate to May (2F)',
                milestone_check='LITTLEROOT_TOWN',
                memory_check=lambda s: 'MAYS_HOUSE' in s.get('player', {}).get('location', ''),
                # Goal: Go to May (2F, at (4, 2))
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=4, y=2, map_location='MAYS_HOUSE_2F', description="Go to May")
                ),
                next_state='S12_MAY_DIALOG'
            ),
            'S12_MAY_DIALOG': BotState(
                name='S12_MAY_DIALOG',
                description='May dialogue (2F)',
                milestone_check='LITTLEROOT_TOWN',
                memory_check=lambda s: 'MAYS_HOUSE_2F' in s.get('player', {}).get('location', ''),
                action_fn=action_handle_dialogue,
                next_state='S13_LEAVE_MAYS_HOUSE'
            ),
            'S13_LEAVE_MAYS_HOUSE': BotState(
                name='S13_LEAVE_MAYS_HOUSE',
                description='Leave May\'s house (from 2F)',
                milestone_check='LITTLEROOT_TOWN',
                memory_check=lambda s: 'MAYS_HOUSE' in s.get('player', {}).get('location', ''),
                # Goal: Exit the house (1F, at (4, 7))
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=4, y=7, map_location='MAYS_HOUSE_1F', description="Exit May's House")
                ),
                next_state='S14_NAV_TO_ROUTE_101'
            ),

            # === Phase 4: Starter Selection (On ROUTE_101) ===
            'S14_NAV_TO_ROUTE_101': BotState(
                name='S14_NAV_TO_ROUTE_101',
                description='Navigate north to road (Route 101)',
                milestone_check='LITTLEROOT_TOWN',
                milestone_incomplete='ROUTE_101',
                memory_check=lambda s: 'LITTLEROOT_TOWN' in s.get('player', {}).get('location', ''),
                # Goal: Go to Route 101 entrance (at (5, 0))
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=5, y=0, map_location='LITTLEROOT_TOWN', description="Go to Route 101")
                ),
                next_state='S15_BIRCH_DIALOG'
            ),
            'S15_BIRCH_DIALOG': BotState(
                name='S15_BIRCH_DIALOG',
                description='Dialogue with Birch on Route 101',
                milestone_check='ROUTE_101',
                milestone_incomplete='STARTER_CHOSEN',
                action_fn=action_handle_dialogue,
                next_state='S16_NAV_TO_BAG'
            ),
            'S16_NAV_TO_BAG': BotState(
                name='S16_NAV_TO_BAG',
                description='Navigate to Birch\'s bag',
                milestone_check='ROUTE_101',
                # Goal: Go to Birch's Bag (at (5, 7))
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=5, y=7, map_location='ROUTE_101', description="Go to Birch's Bag")
                ),
                next_state='S17_STARTER_SELECT'
            ),
            'S17_STARTER_SELECT': BotState(
                name='S17_STARTER_SELECT',
                description='Pokemon Selection from bag',
                milestone_check='ROUTE_101',
                milestone_incomplete='STARTER_CHOSEN',
                action_fn=action_special_starter_select,  # Special handler
                next_state='S18_FIRST_BATTLE'
            ),
            'S18_FIRST_BATTLE': BotState(
                name='S18_FIRST_BATTLE',
                description='First battle (Poochyena)',
                milestone_check='ROUTE_101',
                # Fix: STARTER_CHOSEN milestone set *after* battle
                milestone_incomplete='STARTER_CHOSEN',
                memory_check=lambda s: s.get('game', {}).get('in_battle', False),
                simple_action=None,  # This will pass to the Battle Bot
                next_state='S19_BIRCH_DIALOG_2'
            ),
            'S19_BIRCH_DIALOG_2': BotState(
                name='S19_BIRCH_DIALOG_2',
                description='Dialogue with Birch after battle (in lab)',
                milestone_check='STARTER_CHOSEN',
                memory_check=lambda s: 'BIRCHS_LAB' in s.get('player', {}).get('location', ''),
                action_fn=action_handle_dialogue,
                next_state='S20_NICKNAME'
            ),
            'S20_NICKNAME': BotState(
                name='S20_NICKNAME',
                description='Nickname starter screen',
                milestone_check='STARTER_CHOSEN',
                action_fn=action_special_nickname,  # Special handler (B, A)
                next_state='S21_LEAVE_LAB'
            ),
            'S21_LEAVE_LAB': BotState(
                name='S21_LEAVE_LAB',
                description='Leave Birch\'s Lab',
                milestone_check='STARTER_CHOSEN',
                memory_check=lambda s: 'BIRCHS_LAB' in s.get('player', {}).get('location', ''),
                # Goal: Exit the lab (at (5, 8))
                action_fn=action_handle_navigation_or_dialogue(
                    NavigationGoal(x=5, y=8, map_location='BIRCHS_LAB', description="Exit Lab")
                ),
                next_state='COMPLETED'
            ),
            
            # === Final State ===
            'COMPLETED': BotState(
                name='COMPLETED',
                description='Opening sequence complete - hand off to VLM/A*',
                # Bot's job is done when we are on Route 101 *after* getting starter
                milestone_check='STARTER_CHOSEN', 
                memory_check=lambda s: 'ROUTE_101' in s.get('player', {}).get('location', ''),
                simple_action=None,  # Always return None
                next_state='COMPLETED'
            )
        }
    
    def should_handle(self, state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> bool:
        """
        Determine if opener bot should take control.
        
        Returns True if:
        - STARTER_CHOSEN milestone not yet complete (still in opening sequence)
        - Current state matches one of our programmed states
        
        Args:
            state_data: Game state data from server
            visual_data: Visual data from perception module
        
        Returns:
            True if opener bot should handle, False to let VLM take control
        """
        # Check if we're past the opening sequence (after getting starter)
        player_location = state_data.get('player', {}).get('location', 'UNKNOWN')
        milestones = state_data.get('milestones', {})
        if milestones.get('STARTER_CHOSEN', False):
            # Check if we're back on Route 101 (fully complete)
            if 'ROUTE_101' in player_location.upper() or 'ROUTE' not in player_location.upper():
                logger.info("[OPENER BOT] STARTER_CHOSEN milestone complete and outside lab - handing off to VLM")
                return False
        
        # Check if current state matches any of our programmed states
        for state_name, state in self.states.items():
            if state_name in ['IDLE', 'COMPLETED']:
                continue
            
            if self._check_state_match(state, state_data, visual_data):
                if self.current_state_name != state_name:
                    logger.info(f"[OPENER BOT] State detected: {state_name} - taking control")
                return True
        
        logger.debug(f"[OPENER BOT] No matching state found - location: {player_location}")
        return False
    
    def get_action(self, state_data: Dict[str, Any], visual_data: Dict[str, Any], 
                   current_plan: str = "") -> Union[List[str], NavigationGoal, None]:
        """
        Get programmatic action, navigation goal, or None for VLM fallback.
        
        Args:
            state_data: Game state data from server
            visual_data: Visual data from perception module
            current_plan: Current objective/plan from planning module (used as hint)
        
        Returns:
            - List[str]: Direct button presses (e.g., ['A'] for dialogue)
            - NavigationGoal: Sub-goal for A* Navigator
            - None: Fallback to VLM
        """
        # Update current state based on detection
        new_state = self._detect_current_state(state_data, visual_data)
        
        if new_state != self.current_state_name:
            self._transition_to_state(new_state)
        
        # Get current state configuration
        state = self.states.get(self.current_state_name)
        if not state:
            logger.warning(f"[OPENER BOT] Unknown state: {self.current_state_name}")
            return None
        
        # Check safety limits
        if self._should_fallback_to_vlm(state):
            logger.warning(f"[OPENER BOT] Safety limit reached in state {state.name} - falling back to VLM")
            return None
        
        # Get action or navigation goal for current state
        action_or_goal = self._get_state_action(state, state_data, visual_data)
        
        if action_or_goal is not None:
            self.last_action = action_or_goal
            self.state_attempt_count += 1
            self.state_history.append((self.current_state_name, time.time(), action_or_goal))
            
            if isinstance(action_or_goal, NavigationGoal):
                logger.info(f"[OPENER BOT] State: {state.name} | Goal: {action_or_goal.description} -> ({action_or_goal.x}, {action_or_goal.y})")
            else:
                logger.info(f"[OPENER BOT] State: {state.name} | Action: {action_or_goal} | Attempt: {self.state_attempt_count}/{state.max_attempts}")
        
        return action_or_goal
    
    def _detect_current_state(self, state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> str:
        """Detect which state we're currently in based on game data"""
        
        # Check all states in order
        # States are ordered from most specific to least specific in the state machine
        for state_name, state in self.states.items():
            if state_name in ['IDLE', 'COMPLETED']:
                continue
                
            if self._check_state_match(state, state_data, visual_data):
                return state_name
        
        return 'IDLE'
    
    def _check_state_match(self, state: BotState, state_data: Dict[str, Any], 
                          visual_data: Dict[str, Any]) -> bool:
        """Check if current game state matches a bot state definition"""
        
        milestones = state_data.get('milestones', {})
        
        # Check milestone requirements (highest confidence)
        if state.milestone_check:
            if not milestones.get(state.milestone_check, False):
                return False
        
        if state.milestone_incomplete:
            if milestones.get(state.milestone_incomplete, False):
                return False
        
        # Check memory state (high confidence)
        if state.memory_check:
            try:
                if not state.memory_check(state_data):
                    return False
            except Exception as e:
                logger.warning(f"[OPENER BOT] Memory check failed for {state.name}: {e}")
                return False
        
        # Check VLM visual perception (highest confidence for dialogue detection)
        if state.visual_check:
            try:
                if not state.visual_check(visual_data):
                    return False
            except Exception as e:
                logger.warning(f"[OPENER BOT] Visual check failed for {state.name}: {e}")
                return False
        
        return True
    
    def _transition_to_state(self, new_state: str):
        """Transition to a new state, resetting counters"""
        old_state = self.current_state_name
        self.current_state_name = new_state
        self.state_entry_time = time.time()
        self.state_attempt_count = 0
        self.last_action = None
        
        logger.info(f"[OPENER BOT] State transition: {old_state} -> {new_state}")
    
    def _should_fallback_to_vlm(self, state: BotState) -> bool:
        """Check if we should fallback to VLM due to safety limits"""
        
        # Check attempt count limit
        if self.state_attempt_count >= state.max_attempts:
            logger.warning(f"[OPENER BOT] Max attempts ({state.max_attempts}) reached for {state.name}")
            return True
        
        # Check time limit
        elapsed = time.time() - self.state_entry_time
        if elapsed > state.timeout_seconds:
            logger.warning(f"[OPENER BOT] Timeout ({state.timeout_seconds}s) reached for {state.name}")
            return True
        
        # Check for repeated action loops (same action 5+ times in a row)
        # BUT: Allow repeated 'A' presses for dialogue clearing (normal behavior)
        # ONLY check actions from the CURRENT state (not previous states)
        current_state_actions = [h[2] for h in self.state_history if h[0] == self.current_state_name]
        if len(current_state_actions) >= 5:
            recent_actions = current_state_actions[-5:]
            if len(set(str(a) for a in recent_actions)) == 1:  # All same action
                action = recent_actions[0]
                # Allow repeated 'A' for dialogue - it's expected behavior
                if action != ['A']:
                    logger.warning(f"[OPENER BOT] Detected repeated action loop: {action}")
                    return True
        
        return False
    
    def _get_state_action(self, state: BotState, state_data: Dict[str, Any], 
                         visual_data: Dict[str, Any]) -> Union[List[str], NavigationGoal, None]:
        """Get action, nav_goal, or None for a state."""
        
        # Handle completed state
        if state.name == 'COMPLETED':
            return None
        
        # Use action function if defined
        if state.action_fn:
            try:
                return state.action_fn(state_data, visual_data)
            except Exception as e:
                logger.error(f"[OPENER BOT] Action function failed for {state.name}: {e}")
                return None
        
        # Use simple action
        if state.simple_action:
            return state.simple_action
            
        # Use nav_goal
        if state.nav_goal:
            return state.nav_goal
        
        # No action defined - fallback to VLM
        return None
    
    # =========================================================================
    # State-Specific Action Handlers
    # =========================================================================
    
    def _handle_naming(self, state_data: Dict[str, Any], 
                      visual_data: Dict[str, Any]) -> Optional[List[str]]:
        """
        Handle naming sequence - gender, name, confirmation.
        
        Strategy:
        1. Detect dialogue keywords to identify which screen we're on
        2. Use START button for name selection (not A repeatedly which causes "AAAAAA")
        3. Press A for confirmations
        """
        on_screen_text = visual_data.get('on_screen_text', {})
        dialogue = on_screen_text.get('dialogue', '').upper()
        visual_elements = visual_data.get('visual_elements', {})
        
        # Gender selection
        if 'BOY' in dialogue or 'GIRL' in dialogue:
            logger.debug("[OPENER BOT] NAME_SELECTION: Gender screen - confirming default")
            return ['A']
        
        # Name input screen - use START to accept default
        # Look for "Your name is..." or similar prompts
        if ('YOUR NAME' in dialogue) and not ('IS THIS YOUR NAME' in dialogue):
            logger.debug("[OPENER BOT] NAME_SELECTION: Name input - pressing START for default")
            return ['START']
        
        # Name confirmation - specifically "IS THIS YOUR NAME?"
        if 'IS THIS YOUR NAME' in dialogue:
            logger.debug("[OPENER BOT] NAME_SELECTION: Name confirmation - accepting")
            return ['A']
        
        # Default: handle any dialogue with A
        if visual_elements.get('text_box_visible', False):
            logger.debug("[OPENER BOT] NAME_SELECTION: Dialogue present - pressing A")
            return ['A']
        
        # No dialogue means we might be done
        logger.debug("[OPENER BOT] NAME_SELECTION: No dialogue - checking if complete")
        return ['A']  # Try one more A to be safe
    
    def _handle_moving_van(self, state_data: Dict[str, Any], 
                          visual_data: Dict[str, Any]) -> Optional[List[str]]:
        """
        Handle moving van state - handle dialogue and exit.
        
        Strategy:
        1. Clear any dialogue with A
        2. Otherwise return None to let VLM/A* navigate to exit
        """
        visual_elements = visual_data.get('visual_elements', {})
        
        # Handle dialogue first
        if visual_elements.get('text_box_visible', False):
            logger.debug("[OPENER BOT] MOVING_VAN: Dialogue active - pressing A")
            return ['A']
        
        # Let VLM handle navigation to exit
        logger.debug("[OPENER BOT] MOVING_VAN: No dialogue - fallback to VLM for navigation")
        return None
    
    def _handle_players_house(self, state_data: Dict[str, Any], 
                             visual_data: Dict[str, Any]) -> Optional[List[str]]:
        """
        Handle player's house navigation including clock-setting story gate.
        
        Strategy:
        1. Clear all dialogue with A (including "SET THE CLOCK" directive from Mom)
        2. Let VLM/A* Navigator handle all movement (finding clock, stairs, exit)
        3. Detect and handle special clock-setting screen when triggered
        
        This fixes the "stuck in house" bug by acknowledging Mom's directives
        while letting the navigator find objectives.
        """
        on_screen_text = visual_data.get('on_screen_text', {})
        dialogue = on_screen_text.get('dialogue', '').upper()
        visual_elements = visual_data.get('visual_elements', {})
        player_location = state_data.get('player', {}).get('location', '')
        
        # Handle clock setting screen (special UI)
        if 'SET THE CLOCK' in dialogue or 'IS THIS TIME' in dialogue:
            logger.debug("[OPENER BOT] PLAYERS_HOUSE: Clock setting screen - confirming default time")
            return ['A']
        
        # Handle all other dialogue (including Mom's "go set the clock" directive)
        if visual_elements.get('text_box_visible', False):
            logger.debug(f"[OPENER BOT] PLAYERS_HOUSE: Dialogue - '{dialogue[:50]}...' - pressing A")
            return ['A']
        
        # No dialogue - let VLM/A* Navigator handle movement
        logger.debug(f"[OPENER BOT] PLAYERS_HOUSE: No dialogue at {player_location} - fallback to VLM for navigation")
        return None
    
    def _handle_littleroot_town(self, state_data: Dict[str, Any], 
                               visual_data: Dict[str, Any]) -> Optional[List[str]]:
        """
        Handle Littleroot Town navigation toward Route 101.
        
        Strategy:
        1. If dialogue active -> press A
        2. Otherwise -> fallback to VLM (complex navigation with NPCs)
        
        Note: This is complex navigation with potential NPC interactions,
        so we primarily rely on VLM but handle dialogue programmatically.
        """
        visual_elements = visual_data.get('visual_elements', {})
        
        # Handle dialogue
        continue_prompt = visual_elements.get('continue_prompt_visible', False)
        text_box_visible = visual_elements.get('text_box_visible', False)
        
        if continue_prompt or text_box_visible:
            logger.debug("[OPENER BOT] LITTLEROOT_TOWN: Dialogue active - pressing A")
            return ['A']
        
        # Complex navigation - let VLM handle
        logger.debug("[OPENER BOT] LITTLEROOT_TOWN: Navigation phase - fallback to VLM")
        return None
    
    def _handle_route_101(self, state_data: Dict[str, Any], 
                         visual_data: Dict[str, Any]) -> Optional[List[str]]:
        """
        Handle Route 101 sequence: Birch rescue, starter selection, first battle, nickname.
        
        Strategy:
        1. Clear all dialogue with A
        2. Detect and handle special UI screens (starter selection, nickname)
        3. Let battle system handle combat
        4. Let VLM handle navigation (to bag, around lab, etc.)
        """
        on_screen_text = visual_data.get('on_screen_text', {})
        dialogue = on_screen_text.get('dialogue', '').upper()
        menu_title = on_screen_text.get('menu_title', '').upper()
        visual_elements = visual_data.get('visual_elements', {})
        player_location = state_data.get('player', {}).get('location', '')
        in_battle = state_data.get('game', {}).get('in_battle', False)
        
        # Handle battle - return None to let battle system handle it
        if in_battle:
            logger.debug("[OPENER BOT] ROUTE_101: In battle - fallback to battle system")
            return None
        
        # Handle starter selection screen
        if 'CHOOSE' in dialogue and 'POKéMON' in dialogue:
            logger.debug("[OPENER BOT] ROUTE_101: Starter selection - choosing first Pokemon")
            return ['A']
        
        if 'BAG' in menu_title or 'BAG' in dialogue:
            logger.debug("[OPENER BOT] ROUTE_101: At Birch's bag - selecting")
            return ['A']
        
        if 'DO YOU CHOOSE THIS' in dialogue:
            logger.debug("[OPENER BOT] ROUTE_101: Confirming starter selection")
            return ['A']
        
        # Handle nickname screen - decline with B
        if 'NICKNAME' in dialogue:
            logger.debug("[OPENER BOT] ROUTE_101: Nickname screen - declining")
            return ['B']
        
        # Handle any other dialogue
        if visual_elements.get('text_box_visible', False):
            logger.debug(f"[OPENER BOT] ROUTE_101: Dialogue at {player_location} - pressing A")
            return ['A']
        
        # No dialogue - let VLM handle navigation
        logger.debug(f"[OPENER BOT] ROUTE_101: No dialogue at {player_location} - fallback to VLM for navigation")
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
        self.current_state_name = 'IDLE'
        self.state_entry_time = time.time()
        self.state_attempt_count = 0
        self.last_action = None
        self.state_history.clear()
        logger.info("[OPENER BOT] Reset to IDLE state")


# Global instance for use across agent modules
_global_opener_bot = None

def get_opener_bot() -> OpenerBot:
    """Get or create the global opener bot instance"""
    global _global_opener_bot
    if _global_opener_bot is None:
        _global_opener_bot = OpenerBot()
    return _global_opener_bot
