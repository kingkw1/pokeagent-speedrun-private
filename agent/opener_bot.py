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
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BotState:
    """Represents a state in the opener bot state machine"""
    name: str
    description: str
    
    # Detection criteria (checked in order of reliability)
    milestone_check: Optional[str] = None  # Milestone that should be complete
    milestone_incomplete: Optional[str] = None  # Milestone that should NOT be complete
    memory_check: Optional[Callable[[Dict[str, Any]], bool]] = None  # Function to check game state
    visual_check: Optional[Callable[[Dict[str, Any]], bool]] = None  # Function to check visual data
    
    # Actions to take
    action_fn: Optional[Callable[[Dict[str, Any], Dict[str, Any]], List[str]]] = None
    simple_action: Optional[List[str]] = None  # Simple action like ["A"]
    
    # Transition
    next_state: Optional[str] = None
    max_attempts: int = 10  # Max times to try this state before fallback
    timeout_seconds: float = 30.0  # Max time in this state before fallback


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
        """Build the complete state machine for the opening sequence"""
        return {
            'IDLE': BotState(
                name='IDLE',
                description='Waiting to take control',
                next_state='TITLE_SCREEN'
            ),
            
            'TITLE_SCREEN': BotState(
                name='TITLE_SCREEN',
                description='Title screen - press A to start',
                milestone_incomplete='GAME_RUNNING',
                memory_check=lambda s: s.get('game', {}).get('state', '').lower() == 'title',
                simple_action=['A'],
                next_state='NAME_SELECTION',
                max_attempts=5,
                timeout_seconds=20.0
            ),
            
            'NAME_SELECTION': BotState(
                name='NAME_SELECTION',
                description='Name selection and character creation',
                milestone_incomplete='PLAYER_NAME_SET',
                memory_check=lambda s: (
                    s.get('game', {}).get('state', '').lower() != 'title' and
                    (not s.get('player', {}).get('name') or 
                     s.get('player', {}).get('name', '').strip() in ['', '????????'])
                ),
                simple_action=['A'],  # Confirm default name/choices
                next_state='MOVING_VAN',
                max_attempts=15,  # Multiple steps for gender, name, clock
                timeout_seconds=45.0
            ),
            
            'MOVING_VAN': BotState(
                name='MOVING_VAN',
                description='Moving van - handle dialogue and exit',
                # No milestone check - player might still be in van during/after naming
                memory_check=lambda s: s.get('player', {}).get('location', '') == 'MOVING_VAN',
                action_fn=self._handle_moving_van,
                next_state='PLAYERS_HOUSE',
                max_attempts=20,
                timeout_seconds=60.0
            ),
            
            'PLAYERS_HOUSE': BotState(
                name='PLAYERS_HOUSE',
                description='Navigate player house to reach Littleroot Town',
                # No milestone check - you reach house from van, milestone may not be set
                memory_check=lambda s: 'PLAYERS_HOUSE' in s.get('player', {}).get('location', ''),
                action_fn=self._handle_players_house,
                next_state='LITTLEROOT_TOWN',
                max_attempts=30,
                timeout_seconds=90.0
            ),
            
            'LITTLEROOT_TOWN': BotState(
                name='LITTLEROOT_TOWN',
                description='Navigate Littleroot Town toward Route 101',
                milestone_check='LITTLEROOT_TOWN',
                memory_check=lambda s: 'LITTLEROOT' in s.get('player', {}).get('location', '').upper(),
                action_fn=self._handle_littleroot_town,
                next_state='ROUTE_101',
                max_attempts=50,
                timeout_seconds=120.0
            ),
            
            'ROUTE_101': BotState(
                name='ROUTE_101',
                description='Reached Route 101 - mission complete',
                milestone_check='ROUTE_101',
                memory_check=lambda s: s.get('player', {}).get('location', '') == 'ROUTE_101',
                simple_action=None,  # Return None to hand control to VLM
                next_state='COMPLETED',
                max_attempts=1,
                timeout_seconds=5.0
            ),
            
            'COMPLETED': BotState(
                name='COMPLETED',
                description='Opening sequence complete - hand off to VLM',
                milestone_check='ROUTE_101',  # Only enter this state after Route 101
                simple_action=None,  # Always return None
                next_state='COMPLETED'
            )
        }
    
    def should_handle(self, state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> bool:
        """
        Determine if opener bot should take control.
        
        Returns True if:
        - ROUTE_101 milestone not yet complete (still in opening sequence)
        - Current state matches one of our programmed states
        
        Args:
            state_data: Game state data from server
            visual_data: Visual data from perception module
        
        Returns:
            True if opener bot should handle, False to let VLM take control
        """
        # Check if we're past the opening sequence
        milestones = state_data.get('milestones', {})
        if milestones.get('ROUTE_101', False):
            logger.info("[OPENER BOT] ROUTE_101 milestone reached - handing off to VLM")
            return False
        
        # Check if current state matches any of our programmed states
        for state_name, state in self.states.items():
            if state_name in ['IDLE', 'COMPLETED']:
                continue
            
            if self._check_state_match(state, state_data, visual_data):
                if self.current_state_name != state_name:
                    logger.info(f"[OPENER BOT] State detected: {state_name} - taking control")
                return True
        
        logger.debug(f"[OPENER BOT] No matching state - location: {state_data.get('player', {}).get('location', 'UNKNOWN')}")
        return False
    
    def get_action(self, state_data: Dict[str, Any], visual_data: Dict[str, Any], 
                   current_plan: str = "") -> Optional[List[str]]:
        """
        Get programmatic action for current state, or None to fallback to VLM.
        
        Args:
            state_data: Game state data from server
            visual_data: Visual data from perception module
            current_plan: Current objective/plan from planning module (used as hint)
        
        Returns:
            List of button actions (e.g., ['A'], ['DOWN']) or None for VLM fallback
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
        
        # Get action for current state
        action = self._get_state_action(state, state_data, visual_data)
        
        if action is not None:
            self.last_action = action
            self.state_attempt_count += 1
            self.state_history.append((self.current_state_name, time.time(), action))
            logger.info(f"[OPENER BOT] State: {state.name} | Action: {action} | Attempt: {self.state_attempt_count}/{state.max_attempts}")
        
        return action
    
    def _detect_current_state(self, state_data: Dict[str, Any], visual_data: Dict[str, Any]) -> str:
        """Detect which state we're currently in based on game data"""
        
        # Check states in priority order (most specific first, IDLE/COMPLETED last)
        state_priority = [
            'ROUTE_101',
            'LITTLEROOT_TOWN',
            'PLAYERS_HOUSE',
            'MOVING_VAN',
            'NAME_SELECTION',
            'TITLE_SCREEN',
            'COMPLETED'  # Only matches if ROUTE_101 milestone is complete
        ]
        
        for state_name in state_priority:
            state = self.states[state_name]
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
                logger.info(f"[OPENER BOT] State {state.name} milestone check failed: {state.milestone_check} not set")
                return False
        
        if state.milestone_incomplete:
            if milestones.get(state.milestone_incomplete, False):
                logger.info(f"[OPENER BOT] State {state.name} milestone incomplete check failed: {state.milestone_incomplete} is set")
                return False
        
        # Check memory state (high confidence)
        if state.memory_check:
            try:
                result = state.memory_check(state_data)
                if not result:
                    logger.info(f"[OPENER BOT] State {state.name} memory check failed")
                    return False
                else:
                    logger.info(f"[OPENER BOT] State {state.name} memory check passed!")
            except Exception as e:
                logger.warning(f"[OPENER BOT] Memory check failed for {state.name}: {e}")
                return False
        
        # Check visual state (medium confidence)
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
        if len(self.state_history) >= 5:
            recent_actions = [h[2] for h in self.state_history[-5:]]
            if len(set(str(a) for a in recent_actions)) == 1:  # All same action
                logger.warning(f"[OPENER BOT] Detected repeated action loop: {recent_actions[0]}")
                return True
        
        return False
    
    def _get_state_action(self, state: BotState, state_data: Dict[str, Any], 
                         visual_data: Dict[str, Any]) -> Optional[List[str]]:
        """Get action for a state, either simple action or from action function"""
        
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
        
        # No action defined - fallback to VLM
        return None
    
    # =========================================================================
    # State-Specific Action Handlers
    # =========================================================================
    
    def _handle_moving_van(self, state_data: Dict[str, Any], 
                          visual_data: Dict[str, Any]) -> Optional[List[str]]:
        """
        Handle moving van state - simply walk RIGHT to exit.
        
        Strategy:
        The player starts in the moving van and just needs to walk RIGHT 3 times to exit.
        No dialogue handling needed - just move right.
        """
        logger.debug(f"[OPENER BOT] MOVING_VAN: Walking RIGHT to exit van (attempt {self.state_attempt_count + 1}/20)")
        return ['RIGHT']
    
    def _handle_players_house(self, state_data: Dict[str, Any], 
                             visual_data: Dict[str, Any]) -> Optional[List[str]]:
        """
        Handle player's house navigation.
        
        Strategy:
        1. If dialogue active -> press A
        2. If on 2F -> go DOWN to stairs
        3. If on 1F -> go DOWN to exit
        4. Otherwise -> fallback to VLM for complex navigation
        """
        on_screen_text = visual_data.get('on_screen_text', {})
        visual_elements = visual_data.get('visual_elements', {})
        player_location = state_data.get('player', {}).get('location', '')
        
        # Handle dialogue first
        continue_prompt = visual_elements.get('continue_prompt_visible', False)
        text_box_visible = visual_elements.get('text_box_visible', False)
        
        if continue_prompt or text_box_visible:
            logger.debug("[OPENER BOT] PLAYERS_HOUSE: Dialogue active - pressing A")
            return ['A']
        
        # Navigate based on floor
        if 'PLAYERS_HOUSE_2F' in player_location:
            logger.debug("[OPENER BOT] PLAYERS_HOUSE: On 2F - going DOWN to stairs")
            return ['DOWN']
        
        if 'PLAYERS_HOUSE_1F' in player_location:
            logger.debug("[OPENER BOT] PLAYERS_HOUSE: On 1F - going DOWN to exit")
            return ['DOWN']
        
        # Unknown floor - fallback to VLM
        logger.debug("[OPENER BOT] PLAYERS_HOUSE: Unknown floor - fallback to VLM")
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
