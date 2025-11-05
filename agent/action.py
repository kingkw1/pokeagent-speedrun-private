import logging
import random
import sys
import logging
import random
from agent.system_prompt import system_prompt
from agent.opener_bot import get_opener_bot
from utils.state_formatter import format_state_for_llm, format_state_summary, get_movement_options, get_party_health_summary, format_movement_preview_for_llm
from utils.vlm import VLM

# Set up module logging
logger = logging.getLogger(__name__)

def format_observation_for_action(observation):
    """Format observation data for use in action prompts"""
    if isinstance(observation, dict) and 'visual_data' in observation:
        # Structured format - provide a clean summary for action decision
        visual_data = observation['visual_data']
        summary = f"Screen: {visual_data.get('screen_context', 'unknown')}"
        
        # Add key text information
        on_screen_text = visual_data.get('on_screen_text', {})
        if on_screen_text.get('dialogue'):
            summary += f" | Dialogue: \"{on_screen_text['dialogue']}\""
        if on_screen_text.get('menu_title'):
            summary += f" | Menu: {on_screen_text['menu_title']}"
            
        # Add entity information - handle various entity formats
        entities = visual_data.get('visible_entities', [])
        if entities:
            try:
                entity_names = []
                if isinstance(entities, list):
                    for e in entities[:3]:  # Limit to first 3
                        if isinstance(e, dict):
                            entity_names.append(e.get('name', 'unnamed'))
                        elif isinstance(e, str):
                            entity_names.append(e)
                        else:
                            entity_names.append(str(e))
                elif isinstance(entities, str):
                    entity_names = [entities]
                elif isinstance(entities, dict):
                    # Handle case where entities is a dict with keys like NPC, Pokemon
                    for key, value in entities.items():
                        if value and value != "none" and value != "null":
                            entity_names.append(f"{key}: {value}")
                
                if entity_names:
                    summary += f" | Entities: {', '.join(entity_names[:3])}"  # Limit display
            except Exception as e:
                # Fallback if entity processing fails
                summary += f" | Entities: {str(entities)[:50]}"
            
        return summary
    else:
        # Original text format or non-structured data
        return str(observation)

def calculate_2x2_moves(options, current, target):
    """Calculates D-pad presses in a 2x2 menu layout."""
    raise NotImplementedError
    # Example layout:
    # FIGHT (0,0) | BAG (1,0)
    # POKEMON(0,1)| RUN (1,1)
    positions = {opt: (i % 2, i // 2) for i, opt in enumerate(options)}
    if current not in positions or target not in positions:
        return []
    
    curr_x, curr_y = positions[current]
    targ_x, targ_y = positions[target]
    
    moves = []
    while curr_y < targ_y:
        moves.append("DOWN")
        curr_y += 1
    while curr_y > targ_y:
        moves.append("UP")
        curr_y -= 1
    while curr_x < targ_x:
        moves.append("RIGHT")
        curr_x += 1
    while curr_x > targ_x:
        moves.append("LEFT")
        curr_x -= 1
    return moves    

def calculate_column_moves(options, current, target):
    """Calculates D-pad presses in a single-column menu layout."""
    raise NotImplementedError
    if current not in options or target not in options:
        return []
    
    curr_index = options.index(current)
    targ_index = options.index(target)
    
    moves = []
    while curr_index < targ_index:
        moves.append("DOWN")
        curr_index += 1
    while curr_index > targ_index:
        moves.append("UP")
        curr_index -= 1
    
    return moves

def get_menu_navigation_moves(menu_state, options, current, target):
    """Calculates D-pad presses to go from current to target selection."""
    raise NotImplementedError
    if menu_state == "battle_action_select":
        # Use 2x2 logic: knows "FIGHT" is left of "BAG", "POKEMON" is below "FIGHT"
        # Example: to get from "FIGHT" to "RUN", press DOWN then RIGHT.
        return calculate_2x2_moves(options, current, target)

    elif menu_state in ["main_menu", "shop_menu"]:
        # Use 1-column logic: knows it only needs to press UP or DOWN.
        # Example: to get from "BAG" to "EXIT", press DOWN four times.
        return calculate_column_moves(options, current, target)
    
    # ... other menu types ...

def action_step(memory_context, current_plan, latest_observation, frame, state_data, recent_actions, vlm, visual_dialogue_active=False):
    """
    Decide and perform the next action button(s) based on memory, plan, observation, and comprehensive state.
    Returns a list of action buttons as strings.
    
    Args:
        memory_context: Recent memory/history
        current_plan: Current plan from planning module
        latest_observation: Perception output with visual data
        frame: Current screenshot
        state_data: Game state data
        recent_actions: List of recent actions taken
        vlm: VLM instance for action decisions
        visual_dialogue_active: VLM's visual detection of dialogue box (85.7% accurate, no time cost)
    """
    # 🤖 PRIORITY 0: OPENER BOT - Programmatic State Machine (Splits 0-4)
    # Handles deterministic early game states with high reliability using memory state
    # and milestone tracking as primary signals. Returns None to fallback to VLM.
    try:
        opener_bot = get_opener_bot()
        visual_data = latest_observation.get('visual_data', {}) if isinstance(latest_observation, dict) else {}
        
        if opener_bot.should_handle(state_data, visual_data):
            opener_action = opener_bot.get_action(state_data, visual_data, current_plan)
            
            if opener_action is not None:
                # Opener bot has a programmatic action - use it
                bot_state = opener_bot.get_state_summary()
                logger.info(f"🤖 [OPENER BOT] Taking control in state: {bot_state['current_state']}")
                logger.info(f"🤖 [OPENER BOT] Action: {opener_action} | Attempt: {bot_state['attempt_count']}/{bot_state['max_attempts']}")
                return opener_action
            else:
                # Opener bot returned None - fallback to VLM
                logger.debug(f"🤖 [OPENER BOT] Fallback to VLM in state: {opener_bot.current_state_name}")
        
    except Exception as e:
        logger.error(f"🤖 [OPENER BOT] Error: {e}", exc_info=True)
        # Continue to VLM logic on error
    
    # 🎯 PRIORITY 1: VLM VISUAL DIALOGUE DETECTION (HIGHEST PRIORITY)
    # NEW: Check for continue_prompt_visible (red triangle indicator) - MOST RELIABLE
    # The red triangle ❤️ at end of dialogue is a perfect signal for "press A"
    # 
    # DIALOGUE FALSE POSITIVE PROTECTION:
    # Some locations (e.g., MOVING_VAN) have visual elements that VLM mistakes for dialogue boxes.
    # Blacklist these specific locations to prevent the agent from spamming A button.
    DIALOGUE_DETECTION_BLACKLIST = [
        'MOVING_VAN',  # Has cardboard boxes that VLM mistakes for dialogue boxes
        # Add other problematic locations here if discovered
    ]
    
    # 🔺 PRIORITY 1A: RED TRIANGLE INDICATOR (MOST RELIABLE)
    # The red triangle ❤️ at end of dialogue is the PERFECT signal for "press A"
    # This is much more reliable than text_box_visible alone
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_elements = latest_observation.get('visual_data', {}).get('visual_elements', {})
        continue_prompt_visible = visual_elements.get('continue_prompt_visible', False)
        
        if continue_prompt_visible:
            current_location = state_data.get('player', {}).get('location', '')
            
            if current_location in DIALOGUE_DETECTION_BLACKLIST:
                logger.warning(f"🔺 [CONTINUE PROMPT] Red triangle detected but location '{current_location}' is blacklisted - ignoring")
                print(f"⚠️ [DIALOGUE] Ignoring continue prompt in {current_location} (known false positive)")
            else:
                logger.info(f"🔺 [CONTINUE PROMPT] Red triangle indicator detected - pressing A to continue dialogue")
                print(f"🔺 [DIALOGUE] Red triangle ❤️ visible, pressing A to continue")
                return ["A"]
    
    # 🔺 PRIORITY 1B: FALLBACK - TEXT BOX WITHOUT RED TRIANGLE
    # If text_box_visible but NO red triangle, wait (text is still scrolling)
    # Only press A if we're confident dialogue is complete AND waiting for input
    # NOTE: We could remove this fallback entirely and rely only on red triangle,
    # but keep it for backwards compatibility with locations that don't show triangle
    if visual_dialogue_active:
        current_location = state_data.get('player', {}).get('location', '')
        
        if current_location in DIALOGUE_DETECTION_BLACKLIST:
            logger.warning(f"💬 [DIALOGUE] VLM detected dialogue but location '{current_location}' is blacklisted - ignoring false positive")
            print(f"⚠️ [DIALOGUE] Ignoring VLM dialogue in {current_location} (known false positive)")
        else:
            # Check if red triangle is explicitly false (not just missing)
            visual_elements = latest_observation.get('visual_data', {}).get('visual_elements', {})
            continue_prompt = visual_elements.get('continue_prompt_visible')
            
            # Only press A if: triangle is True OR triangle info is missing (backwards compat)
            if continue_prompt is False:
                print(f"⏳ [DIALOGUE] Text box visible but no red triangle - waiting for text to finish scrolling")
                logger.info("[DIALOGUE] Waiting for continue prompt to appear")
                return None  # Don't press A yet, wait for red triangle
            
            # Triangle info missing - use old behavior as fallback
            logger.info(f"💬 [DIALOGUE] Text box visible (no triangle info) - pressing A")
            print(f"💬 [DIALOGUE] VLM visual detection: dialogue box active, pressing A")
            return ["A"]
    
    # 🚨 PRIORITY 2: NEW GAME MENU DETECTION
    # Must happen before ANY other logic to prevent override conflicts
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_data = latest_observation.get('visual_data', {})
        on_screen_text = visual_data.get('on_screen_text', {})
        dialogue_text = (on_screen_text.get('dialogue') or '').upper()
        menu_title = (on_screen_text.get('menu_title') or '').upper()
        
        # Check milestones to ensure we haven't progressed past this screen
        milestones = state_data.get('milestones', {})
        player_name_milestone = milestones.get('PLAYER_NAME_SET', {})
        player_name_set = player_name_milestone.get('completed', False) if isinstance(player_name_milestone, dict) else bool(player_name_milestone)
        
        if ('NEW GAME' in dialogue_text or 'NEW GAME' in menu_title) and not player_name_set:
            logger.info(f"🎯 [NEW GAME FIX] NEW GAME menu detected! Bypassing all other logic.")
            logger.info(f"🎯 [NEW GAME FIX] - dialogue: '{dialogue_text}'")
            logger.info(f"🎯 [NEW GAME FIX] - menu_title: '{menu_title}'")
            print(f"🎯 [NEW GAME FIX] Selecting NEW GAME with A")
            return ["A"]
    
    """
    ===============================================================================
    🚨 EMERGENCY PATCH APPLIED - REVIEW BEFORE PRODUCTION 🚨
    ===============================================================================
    
    PATCH: Title Screen Bypass (lines 18-22)
    - Original issue: Agent would freeze on title screen due to complex VLM processing
    - Emergency fix: Hard-coded "A" button press for title screen state
    - TODO: Replace with smarter detection that handles:
      * Multiple title screen states (main menu, options, etc.)
      * Character creation screens  
      * Save/load dialogs
      * Any other menu-like states that need simple navigation
    
    INTEGRATION NOTES:
    - This bypass should be expanded to handle more menu states programmatically
    - Consider creating a "simple_navigation_mode" for all menu/UI interactions
    - The main VLM action logic below this patch is intact and working
    - When reintegrating full AI, keep this as a fallback for known simple states
    
    ===============================================================================
    """
    # ENHANCED FIX: Robust title/menu screen detection (adapted from simple agent)
    game_data = state_data.get('game', {})
    player_data = state_data.get('player', {})
    
    # Use same detection logic as simple agent for consistency
    player_location = player_data.get("location", "")
    game_state_value = game_data.get("game_state", "").lower()
    player_name = player_data.get("name", "").strip()
    
    # FINAL FIX: Ultra-conservative title screen detection
    # Only trigger for actual title screens, never during gameplay
    is_title_screen = (
        # Only for explicit title sequence or very early states
        player_location == "TITLE_SEQUENCE" or
        # Only if game state explicitly contains "title" 
        game_state_value == "title" or
        # Only if no player name AND at exact origin (0,0) - very strict
        ((not player_name or player_name == "????????") and 
         (player_data.get('position', {}).get('x', -1) == 0 and 
          player_data.get('position', {}).get('y', -1) == 0) and
         player_location.lower() in ['', 'unknown', 'title_sequence'])
    )
    
    # CRITICAL: Use milestones to override title detection
    # If player name is set, we're past the title screen regardless of other conditions
    milestones = state_data.get('milestones', {})
    if milestones.get('PLAYER_NAME_SET', False) or milestones.get('INTRO_CUTSCENE_COMPLETE', False):
        is_title_screen = False  # Force override - we're in gameplay now
    
    if is_title_screen:
        logger.info(f"[ACTION] Title screen detected!")
        logger.info(f"[ACTION] - player_location: '{player_location}'")
        logger.info(f"[ACTION] - game_state: '{game_state_value}'")
        logger.info(f"[ACTION] - player_name: '{player_name}'")
        logger.info(f"[ACTION] - party_count: {game_data.get('party_count', 0)}")
        logger.info(f"[ACTION] - position: {player_data.get('position', {})}")
        logger.info("[ACTION] Using simple navigation: A to select NEW GAME")
        return ["A"]
    
    # ENHANCED FIX: Detect name selection screen after title screen
    # Check for name selection context using visual data and milestones
    visual_data = latest_observation.get('visual_data', {}) if isinstance(latest_observation, dict) else {}
    on_screen_text = visual_data.get('on_screen_text', {})
    
    dialogue_text = (on_screen_text.get('dialogue') or '').upper()
    menu_title = (on_screen_text.get('menu_title') or '').upper()
    
    # Look for name selection indicators - but also check step count as backup
    is_name_selection = False
    dialogue_text = (on_screen_text.get('dialogue') or '').upper()
    menu_title = (on_screen_text.get('menu_title') or '').upper()
    
    # FIX: Use actual step count from state_data instead of len(recent_actions)
    # The recent_actions is capped at 25, so len(recent_actions) gets stuck at 25
    current_step = state_data.get('step_number', len(recent_actions or []))
    
    # DEBUG: Verify step calculation is working
    if current_step >= 50:  # Only debug once we're in VLM mode
        print(f"🔢 [STEP DEBUG] current_step={current_step}, step_number={state_data.get('step_number', 'missing')}, recent_actions_len={len(recent_actions) if recent_actions else 0}")
    
    # DEBUG: Track our progress every few steps
    if current_step % 10 == 0 and current_step >= 30:
        print(f"🔍 [DEBUG] Step {current_step} reached - Milestone check in progress")
    
    # CRITICAL DEBUG: Force milestone status check at key steps
    intro_complete = milestones.get('INTRO_CUTSCENE_COMPLETE', False)
    
    if current_step in [33, 34, 35, 40, 45, 50, 51]:
        print(f"🚨 [CRITICAL] Step {current_step}: PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}, INTRO_COMPLETE={intro_complete}")
        print(f"   Navigation mode check: intro_complete={intro_complete}, current_step > 50: {current_step > 50}")
    
    # DEBUG: Always log visual data for name selection detection around critical steps
    if current_step >= 30:  # Only log around critical transition
        logger.info(f"[ACTION] Step {current_step} - Name check: dialogue='{dialogue_text}', menu='{menu_title}', PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}")
        logger.info(f"[ACTION] Step {current_step} - Visual data keys: {list(visual_data.keys()) if visual_data else 'None'}")
        logger.info(f"[ACTION] Step {current_step} - On-screen text keys: {list(on_screen_text.keys()) if on_screen_text else 'None'}")
    
    # Check if this looks like name selection screen using multiple methods
    name_text_detected = ('YOUR NAME' in dialogue_text or 'NAME?' in dialogue_text or 
                          'YOUR NAME' in menu_title or 'NAME?' in menu_title or
                          'SELECT NAME' in menu_title or 'SELECT YOUR NAME' in menu_title)
    
    # Also check VLM perception for name selection context
    vlm_context_name_selection = False
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        vd = latest_observation['visual_data']
        vlm_dialogue = vd.get('on_screen_text', {}).get('dialogue', '')
        vlm_menu = vd.get('on_screen_text', {}).get('menu_title', '')
        if vlm_dialogue and ('YOUR NAME' in vlm_dialogue or 'NAME?' in vlm_dialogue):
            vlm_context_name_selection = True
        if vlm_menu and ('SELECT' in vlm_menu and 'NAME' in vlm_menu):
            vlm_context_name_selection = True
    
    # Expanded step range and VLM detection
    in_name_step_range = (25 <= current_step <= 50 and not milestones.get('PLAYER_NAME_SET', False))
    
    if ((name_text_detected or vlm_context_name_selection or in_name_step_range) 
        and not milestones.get('PLAYER_NAME_SET', False)):
        is_name_selection = True
        logger.info("[ACTION] Name selection screen detected!")
        logger.info(f"[ACTION] - text_detected: {name_text_detected}, vlm_detected: {vlm_context_name_selection}, step_range: {in_name_step_range}")
        logger.info(f"[ACTION] - dialogue: '{dialogue_text}', menu: '{menu_title}'")
        
        # Simple name selection logic - press A to accept default name quickly
        if current_step < 30:  # Early steps: position at default
            logger.info("[ACTION] Positioning for name selection")
            return ["A"]
        else:  # Later steps: accept default name
            logger.info("[ACTION] Accepting default name")
            return ["A"]
    
    # NEW GAME MENU FIX: Detect "NEW GAME / OPTIONS" menu screen (HIGH PRIORITY)
    # This must happen BEFORE other override systems to prevent conflicts
    if ('NEW GAME' in dialogue_text or 'NEW GAME' in menu_title) and not milestones.get('PLAYER_NAME_SET', False):
        logger.info(f"[ACTION] NEW GAME menu detected!")
        logger.info(f"[ACTION] - dialogue: '{dialogue_text}'")
        logger.info(f"[ACTION] - menu_title: '{menu_title}'")
        logger.info("[ACTION] Selecting NEW GAME with A")
        return ["A"]
    
    # CRITICAL DEBUG: Override right after PLAYER_NAME_SET to avoid VLM confusion
    # But only until INTRO_CUTSCENE_COMPLETE - then let VLM take over
    
    # DEBUG: Track milestone status at key steps
    if current_step >= 40 and current_step % 5 == 0:  # Every 5th step after 40
        print(f"🏆 [MILESTONE] Step {current_step}: PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}, INTRO_CUTSCENE_COMPLETE={intro_complete}")
    
    # NAVIGATION DECISION LOGIC: Clear hierarchy of what mode to use
    
    # REMOVED: MEMORY-BASED DIALOGUE DETECTION
    # The game memory's in_dialog flag is unreliable (42.9% accurate vs VLM's 85.7%)
    # It frequently gets stuck reporting in_dialog=True even after dialogue ends
    # (e.g., MOVING_VAN, post-dialogue in LITTLEROOT TOWN)
    # 
    # Relying solely on VLM visual detection (text_box_visible) which is much more accurate
    # and doesn't suffer from stuck state issues.
    #
    # If memory-based detection is needed in future, it should ONLY be used when VLM also confirms dialogue
    # to avoid false positives from stuck memory state.
    
    # Log memory state for debugging but don't act on it
    in_dialog = game_data.get('in_dialog', False)
    if in_dialog:
        logger.debug(f"[ACTION] Memory reports in_dialog=True (not acting on this - VLM detection only)")
        # Note: Not returning ["A"] here - VLM detection above is the only trigger
    
    # 1. Post-name override: Only when name is set but intro cutscene isn't complete yet
    # FIXED: Don't activate if player has already progressed beyond intro (has Pokemon on routes)
    player_location = player_data.get('location', '')
    is_in_moving_van = "MOVING_VAN" in str(player_location).upper()
    override_step_limit = 15  # Maximum steps to spend in override mode
    
    # Check for advanced game states that should trigger VLM mode
    on_route_101 = 'ROUTE 101' in str(player_location).upper()
    has_pokemon = state_data.get('player', {}).get('party', [])
    advanced_location = on_route_101 or 'ROUTE' in str(player_location).upper()
    
    # CRITICAL FIX: If player already has Pokemon, they've completed intro - don't override!
    player_has_pokemon = len(has_pokemon) > 0 if has_pokemon else False
    
    if (milestones.get('PLAYER_NAME_SET', False) and 
        not intro_complete and 
        not advanced_location and  # Don't override if we're on routes
        not player_has_pokemon and  # FIXED: Don't override if player has Pokemon
        current_step <= override_step_limit and 
        not is_in_moving_van):
        logger.info(f"[ACTION] Step {current_step} - Post-name override active (location: {player_location})")
        print(f"🔧 [OVERRIDE] Step {current_step} - Post-name override: pressing A (intro_complete={intro_complete}, location={player_location}, has_pokemon={player_has_pokemon})")
        return ["A"]
    
    # 2. VLM Navigation Mode: When intro is complete OR we exceed override limits OR advanced location
    elif intro_complete or current_step > override_step_limit or is_in_moving_van or advanced_location:
        if current_step % 5 == 0 or current_step in [16, 21, 27] or advanced_location:
            print(f"🤖 [VLM MODE] Step {current_step} - VLM Navigation Active (intro_complete={intro_complete}, past_limit={current_step > override_step_limit}, moving_van={is_in_moving_van}, advanced_location={advanced_location})")
        
        # Override status check - only log periodically
        if current_step % 100 == 0:
            logger.info(f"Mode check (Step {current_step}): VLM navigation active, overrides inactive")
        
        # Direct VLM call - let the VLM handle all navigation decisions
        pass  # Continue to VLM logic below
    
    # 3. Legacy mode: Only for early game before VLM navigation is active
    else:
        print(f"🎯 [EARLY MODE] Step {current_step} - Legacy navigation active (name_set={milestones.get('PLAYER_NAME_SET', False)}, intro_complete={intro_complete})")
        
        # DEBUG: Log when NOT in title screen (to catch transition)
        if not is_title_screen and len(recent_actions or []) < 5:
            logger.info(f"[ACTION] NOT title screen - using full navigation logic")
            logger.info(f"[ACTION] - player_location: '{player_location}'")
            logger.info(f"[ACTION] - game_state: '{game_state_value}'")
            logger.info(f"[ACTION] - player_name: '{player_name}'")
            logger.info(f"[ACTION] - position: {player_data.get('position', {})}")
        
        # Debug logging for state detection (only if not in title)
        if not is_title_screen:
            logger.info(f"[ACTION] Debug - game_state: '{game_state_value}', location: '{player_location}', position: {player_data.get('position', {})}")
    
    # ============================================================================
    # VLM NAVIGATION LOGIC: All paths above lead here for VLM-based decisions
    # ============================================================================
    
    # CRITICAL POSITION DEBUG: Track if agent is actually moving
    player_data = state_data.get('player', {})
    current_position = player_data.get('position', {})
    current_x = current_position.get('x', 'unknown')
    current_y = current_position.get('y', 'unknown')
    current_map = current_position.get('map', 'unknown')
    
    print(f"🎯 [POSITION DEBUG] Step {len(recent_actions) if recent_actions else 0}: Player at ({current_x}, {current_y}) on map {current_map}")
    
    # Store position for comparison
    if not hasattr(action_step, 'last_position'):
        action_step.last_position = (current_x, current_y, current_map)
    
    last_x, last_y, last_map = action_step.last_position
    if (current_x, current_y, current_map) != (last_x, last_y, last_map):
        print(f"✅ [POSITION CHANGE] Moved from ({last_x}, {last_y}) to ({current_x}, {current_y}) on map {current_map}")
        action_step.last_position = (current_x, current_y, current_map)
    else:
        print(f"⚠️ [POSITION STUCK] NO MOVEMENT - Still at ({current_x}, {current_y}) on map {current_map}")

    # Get formatted state context and useful summaries
    state_context = format_state_for_llm(state_data)
    state_summary = format_state_summary(state_data)
    movement_options = get_movement_options(state_data)
    party_health = get_party_health_summary(state_data)
    
    # PRIORITY 1 ENHANCEMENT: Generate extended map view from MapStitcher
    extended_map_view = None
    exploration_status = None
    try:
        map_stitcher = state_data.get('map', {}).get('_map_stitcher_instance')
        if map_stitcher:
            # Get current location info
            location_name = state_data.get('player', {}).get('location', 'Unknown')
            player_pos = (current_x, current_y) if isinstance(current_x, int) and isinstance(current_y, int) else None
            
            if location_name and location_name != 'Unknown' and player_pos:
                # Generate extended map display (larger view from stitched data)
                try:
                    npcs = state_data.get('npcs', [])
                    connections = map_stitcher.get_location_connections(location_name)
                    extended_map_lines = map_stitcher.generate_location_map_display(
                        location_name,
                        player_pos,
                        npcs=npcs,
                        connections=connections
                    )
                    if extended_map_lines:
                        extended_map_view = '\n'.join(extended_map_lines)
                        print(f"🗺️ [EXTENDED MAP] Generated {len(extended_map_lines)} line extended view for {location_name}")
                        
                        # Get exploration stats
                        map_id = map_stitcher.get_map_id(
                            state_data.get('map', {}).get('bank', 0),
                            state_data.get('map', {}).get('number', 0)
                        )
                        if map_id in map_stitcher.map_areas:
                            area = map_stitcher.map_areas[map_id]
                            bounds = getattr(area, 'explored_bounds', {})
                            if bounds:
                                width = bounds.get('max_x', 0) - bounds.get('min_x', 0) + 1
                                height = bounds.get('max_y', 0) - bounds.get('min_y', 0) + 1
                                visited_count = getattr(area, 'visited_count', 1)
                                exploration_status = f"Explored area: {width}x{height} tiles | Visited: {visited_count}x"
                                print(f"🗺️ [EXPLORATION] {exploration_status}")
                except Exception as e:
                    logger.warning(f"[EXTENDED MAP] Error generating extended map view: {e}")
                    print(f"⚠️ [EXTENDED MAP] Failed to generate extended view: {e}")
    except Exception as e:
        logger.warning(f"[EXTENDED MAP] Error accessing map stitcher: {e}")
    
    logger.info("[ACTION] Starting action decision")
    logger.info(f"[ACTION] State: {state_summary}")
    logger.info(f"[ACTION] Party health: {party_health['healthy_count']}/{party_health['total_count']} healthy")
    if movement_options:
        logger.info(f"[ACTION] Movement options: {movement_options}")
    
    # Build enhanced action context
    action_context = []
    
    # Extract key info for context
    game_data = state_data.get('game', {})
    
    # Battle vs Overworld context
    if game_data.get('in_battle', False):
        action_context.append("=== BATTLE MODE ===")
        battle_info = game_data.get('battle_info', {})
        if battle_info:
            if 'player_pokemon' in battle_info and battle_info['player_pokemon']:
                player_pkmn = battle_info['player_pokemon']
                action_context.append(f"Your Pokemon: {player_pkmn.get('species_name', player_pkmn.get('species', 'Unknown'))} (Lv.{player_pkmn.get('level', '?')}) HP: {player_pkmn.get('current_hp', '?')}/{player_pkmn.get('max_hp', '?')}")
            if 'opponent_pokemon' in battle_info and battle_info['opponent_pokemon']:
                opp_pkmn = battle_info['opponent_pokemon']
                action_context.append(f"Opponent: {opp_pkmn.get('species_name', opp_pkmn.get('species', 'Unknown'))} (Lv.{opp_pkmn.get('level', '?')}) HP: {opp_pkmn.get('current_hp', '?')}/{opp_pkmn.get('max_hp', '?')}")
    else:
        action_context.append("=== OVERWORLD MODE ===")
        
        # PRIORITY 1: Add extended map view from MapStitcher (GLOBAL CONTEXT)
        if extended_map_view:
            action_context.append("")
            action_context.append("=== EXTENDED MAP VIEW (from exploration memory) ===")
            if exploration_status:
                action_context.append(exploration_status)
            action_context.append("")
            action_context.append(extended_map_view)
            action_context.append("")
            action_context.append("Legend: P=You, N=NPC, .=walkable, #=blocked, ~=grass, ≈=water, S=stairs/warp")
            action_context.append("This is your COMPLETE explored map - use it to plan paths and avoid dead ends!")
            action_context.append("")
        
        # Movement options from utility (LOCAL TACTICAL INFO)
        if movement_options:
            action_context.append("=== IMMEDIATE MOVEMENT OPTIONS ===")
            for direction, description in movement_options.items():
                action_context.append(f"  {direction}: {description}")
    
    # Add comprehensive state context (includes map visualization)
    if state_context and state_context.strip():
        action_context.append("=== GAME STATE CONTEXT ===")
        action_context.append(state_context.strip())
        print(f"🗺️ [MAP DEBUG] Added state context to VLM prompt ({len(state_context)} chars)")
        # Show a preview of the map data
        if "MAP:" in state_context:
            map_preview = state_context[state_context.find("MAP:"):state_context.find("MAP:") + 200] + "..."
            print(f"🗺️ [MAP DEBUG] Map preview: {map_preview}")
    else:
        print(f"🗺️ [MAP DEBUG] No state context available for VLM prompt")
    
    # Party health summary
    if party_health['total_count'] > 0:
        action_context.append("=== PARTY STATUS ===")
        action_context.append(f"Healthy Pokemon: {party_health['healthy_count']}/{party_health['total_count']}")
        if party_health['critical_pokemon']:
            action_context.append("Critical Pokemon:")
            for critical in party_health['critical_pokemon']:
                action_context.append(f"  {critical}")
    
    # Recent actions context
    if recent_actions:
        try:
            # Ensure recent_actions is a valid iterable
            if recent_actions is not None:
                recent_list = list(recent_actions) if recent_actions else []
                if recent_list:
                    action_context.append(f"Recent Actions: {', '.join(recent_list[-5:])}")
        except Exception as e:
            logger.warning(f"[ACTION] Error processing recent_actions: {e}")
            # Continue without recent actions context
    
    # Visual perception context (new structured data)
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_data = latest_observation['visual_data']
        action_context.append("=== VISUAL PERCEPTION ===")
        action_context.append(f"Screen Context: {visual_data.get('screen_context', 'unknown')}")
        
        # On-screen text information
        on_screen_text = visual_data.get('on_screen_text', {})
        visual_elements = visual_data.get('visual_elements', {})
        
        # CRITICAL FIX: Check if dialogue box is actually visible, not just if dialogue text exists
        text_box_visible = visual_elements.get('text_box_visible', False)
        

        
        if on_screen_text.get('menu_title'):
            action_context.append(f"Menu: {on_screen_text['menu_title']}")
        if on_screen_text.get('button_prompts'):
            # Handle button prompts that might be dictionaries or strings
            button_prompts = on_screen_text['button_prompts']
            if isinstance(button_prompts, list):
                prompt_strs = []
                for prompt in button_prompts:
                    if isinstance(prompt, dict):
                        # Extract text from dictionary format
                        prompt_text = prompt.get('text', str(prompt))
                        prompt_strs.append(prompt_text)
                    else:
                        prompt_strs.append(str(prompt))
                action_context.append(f"Button Prompts: {', '.join(prompt_strs)}")
            else:
                action_context.append(f"Button Prompts: {str(button_prompts)}")
        
        # Add dialogue box status for VLM clarity
        action_context.append(f"Dialogue Box Status: {'VISIBLE' if text_box_visible else 'NOT VISIBLE'}")
        
        # ENHANCED DIALOGUE DEBUG: Critical detection troubleshooting
        if on_screen_text.get('dialogue'):
            print(f"🗨️ [DIALOGUE DEBUG] Dialogue detected: '{on_screen_text.get('dialogue')}'")
            print(f"🗨️ [DIALOGUE DEBUG] - text_box_visible: {text_box_visible}")
            print(f"🗨️ [DIALOGUE DEBUG] - visual_elements: {visual_elements}")
            print(f"🗨️ [DIALOGUE DEBUG] - screen_context: {visual_data.get('screen_context', 'missing')}")
            print(f"🗨️ [DIALOGUE DEBUG] - All visual_data keys: {list(visual_data.keys())}")
            logger.info(f"[DIALOGUE DEBUG] Dialogue text: '{on_screen_text.get('dialogue')}', text_box_visible: {text_box_visible}, visual_elements: {visual_elements}")
        else:
            print(f"🗨️ [DIALOGUE DEBUG] NO dialogue detected in on_screen_text: {on_screen_text}")
            
        # CRITICAL: Check if we're actually in a dialogue state that should block movement
        screen_context = visual_data.get('screen_context', 'unknown')
        dialogue_text = on_screen_text.get('dialogue', '')
        
        # Filter out fake "dialogue" that's actually just placeholder text from perception template
        # or game state info that got misclassified
        is_fake_dialogue = dialogue_text and any(marker in dialogue_text for marker in [
            'Location:', 'Pos:', 'Money:', 'HP:', 'Pokedex:',  # Game state info
            'ONLY text from dialogue boxes',  # Perception template placeholder
            'DO NOT include HUD',  # Perception template placeholder
            'If no dialogue box visible',  # Perception template placeholder
        ])
        
        if screen_context == 'overworld' and dialogue_text and not is_fake_dialogue:
            print(f"🚨 [CRITICAL ERROR] VLM reports 'overworld' but REAL dialogue exists! This may be misclassified!")
            print(f"🚨 [CRITICAL ERROR] - dialogue: '{dialogue_text}'")
            print(f"🚨 [CRITICAL ERROR] - This could be why movement commands aren't working!")
        elif is_fake_dialogue:
            print(f"✅ [DIALOGUE FILTER] Ignoring fake 'dialogue' (perception template or game state): '{dialogue_text[:70]}...')")
        
        # Check if dialogue contains specific text that indicates we're reading a box/sign
        # Only process if it's NOT fake dialogue
        dialogue_text_raw = on_screen_text.get('dialogue', '')
        if dialogue_text_raw and not is_fake_dialogue:
            dialogue_text_lower = dialogue_text_raw.lower()
            if 'pokémon' in dialogue_text_lower and ('box' in dialogue_text_lower or 'logo' in dialogue_text_lower):
                print(f"🎁 [BOX INTERACTION] Detected box/sign interaction dialogue: '{dialogue_text_raw}'")
                print(f"🎁 [BOX INTERACTION] This requires A to close dialogue before movement will work!")
                action_context.append(f"📦 ACTIVE BOX DIALOGUE: \"{dialogue_text_raw}\" - MUST PRESS A TO CLOSE")
            elif text_box_visible:
                action_context.append(f"ACTIVE Dialogue: \"{dialogue_text_raw}\" - {on_screen_text.get('speaker', 'Unknown')}")
            elif not text_box_visible:
                action_context.append(f"Residual Text (NO dialogue box): \"{dialogue_text_raw}\" - IGNORE THIS")
        
        # Visible entities - handle various formats from VLM
        entities = visual_data.get('visible_entities', [])
        if entities:
            action_context.append("Visible Entities:")
            # Handle different entity formats that VLM might return
            try:
                if isinstance(entities, list) and len(entities) > 0:
                    for i, entity in enumerate(entities[:5]):  # Limit to 5 entities to avoid clutter
                        if isinstance(entity, dict):
                            # Entity is a dictionary with type/name/position
                            action_context.append(f"  - {entity.get('type', 'unknown')}: {entity.get('name', 'unnamed')} at {entity.get('position', 'unknown position')}")
                        elif isinstance(entity, str):
                            # Entity is just a string description
                            action_context.append(f"  - {entity}")
                        else:
                            # Entity is some other type
                            action_context.append(f"  - {str(entity)}")
                elif isinstance(entities, str):
                    # Entities is a single string
                    action_context.append(f"  - {entities}")
            except Exception as e:
                # Fallback if entity processing fails
                action_context.append(f"  - Entities: {str(entities)[:100]}")
                logger.warning(f"[ACTION] Error processing entities: {e}")
        
        # Visual elements status
        visual_elements = visual_data.get('visual_elements', {})
        active_elements = [k.replace('_', ' ').title() for k, v in visual_elements.items() if v]
        if active_elements:
            action_context.append(f"Active Visual Elements: {', '.join(active_elements)}")
        
        # Navigation information from enhanced VLM perception
        navigation_info = visual_data.get('navigation_info', {})
        if navigation_info:
            action_context.append("=== NAVIGATION ANALYSIS ===")
            
            exits = navigation_info.get('exits_visible', [])
            if exits and any(exit for exit in exits if exit):
                action_context.append(f"Exits Visible: {', '.join(str(e) for e in exits if e)}")
            
            interactables = navigation_info.get('interactable_objects', [])
            if interactables and any(obj for obj in interactables if obj):
                action_context.append(f"Interactable Objects: {', '.join(str(o) for o in interactables if o)}")
            
            barriers = navigation_info.get('movement_barriers', [])
            if barriers and any(barrier for barrier in barriers if barrier):
                action_context.append(f"Movement Barriers: {', '.join(str(b) for b in barriers if b)}")
            
            open_paths = navigation_info.get('open_paths', [])
            if open_paths and any(path for path in open_paths if path):
                action_context.append(f"Open Paths: {', '.join(str(p) for p in open_paths if p)}")
        
        # Spatial layout information
        spatial_layout = visual_data.get('spatial_layout', {})
        if spatial_layout:
            room_type = spatial_layout.get('room_type')
            player_pos = spatial_layout.get('player_position')
            features = spatial_layout.get('notable_features', [])
            
            if room_type:
                action_context.append(f"Room Type: {room_type}")
            if player_pos:
                action_context.append(f"Player Position: {player_pos}")
            if features and any(feature for feature in features if feature):
                action_context.append(f"Notable Features: {', '.join(str(f) for f in features if f)}")
    
    context_str = "\n".join(action_context)
    
    # Get the visual screen context to guide decision making
    visual_context = "unknown"
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_context = latest_observation['visual_data'].get('screen_context', 'unknown')
        if not visual_context:  # Handle None or empty string
            visual_context = "unknown"
    
    # DEBUG: Check why visual context becomes None
    if current_step >= 50 and (visual_context == "unknown" or visual_context is None):
        print(f"⚠️ [VISUAL DEBUG] Step {current_step} - visual_context is '{visual_context}'")
        if isinstance(latest_observation, dict):
            print(f"   latest_observation keys: {list(latest_observation.keys())}")
            if 'visual_data' in latest_observation:
                visual_data = latest_observation['visual_data']
                print(f"   visual_data keys: {list(visual_data.keys()) if visual_data else 'None'}")
                print(f"   screen_context value: {visual_data.get('screen_context') if visual_data else 'N/A'}")
        else:
            print(f"   latest_observation type: {type(latest_observation)}")
    
    # Enhanced Goal-Conditioned Action Prompt (Day 9 Navigation Implementation)
    # Strategic goal integration with tactical movement analysis
    strategic_goal = ""
    if current_plan and current_plan.strip():
        strategic_goal = f"""
=== YOUR STRATEGIC GOAL ===
{current_plan.strip()}

"""
    
    # SMART NAVIGATION ANALYSIS: Check VLM navigation data for specific guidance
    navigation_guidance = ""
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_data = latest_observation['visual_data']
        nav_info = visual_data.get('navigation_info', {})
        
        # Check for exits that VLM identified
        exits = nav_info.get('exits_visible', [])
        open_paths = nav_info.get('open_paths', [])
        notable_features = visual_data.get('spatial_layout', {}).get('notable_features', [])
        
        # Build specific navigation guidance based on VLM analysis
        if any(exit for exit in exits if exit and exit != "none" and "door" in str(exit).lower()):
            navigation_guidance += "\n🚪 VLM DETECTED EXITS: The VLM identified doors/exits. PRIORITIZE MOVEMENT toward these exits instead of pressing A.\n"
        
        if any(feature for feature in notable_features if feature and "door" in str(feature).lower()):
            navigation_guidance += f"\n🎯 NOTABLE FEATURES: {notable_features} - Move toward these features.\n"
        
        if any(path for path in open_paths if path and path != "none"):
            navigation_guidance += f"\n🛤️ OPEN PATHS: {open_paths} - Use these directions for movement.\n"
        
        # Special guidance for room navigation
        room_type = visual_data.get('spatial_layout', {}).get('room_type', '')
        if 'interior' in str(room_type).lower() or 'house' in str(room_type).lower():
            navigation_guidance += "\n🏠 ROOM EXIT STRATEGY: You're in a room/house. Look for exits at screen edges. Try all directions (UP/DOWN/LEFT/RIGHT) to find the way out.\n"
    
    # Get movement preview for pathfinding decisions
    movement_preview_text = ""
    walkable_options = []  # NEW: Store walkable directions as multiple-choice options
    
    if not game_data.get('in_battle', False):  # Only show movement options in overworld
        try:
            movement_preview_text = format_movement_preview_for_llm(state_data)
            print(f"🗺️ [MOVEMENT DEBUG] Raw movement preview result: '{movement_preview_text}'")
            
            # Extract WALKABLE directions for multiple-choice selection
            if movement_preview_text and movement_preview_text != "Movement preview: Not available":
                for line in movement_preview_text.split('\n'):
                    if 'WALKABLE' in line:
                        # Extract direction from line like "  UP   : ( 10, 13) [.] WALKABLE"
                        for direction in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
                            if line.strip().startswith(direction):
                                # Extract coordinates and description
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    coords_and_desc = parts[1].strip()
                                    walkable_options.append({
                                        'direction': direction,
                                        'details': coords_and_desc
                                    })
                                break
                
                print(f"🗺️ [MOVEMENT DEBUG] Extracted {len(walkable_options)} walkable options: {[opt['direction'] for opt in walkable_options]}")
                
                # Format movement preview with original full details
                movement_preview_text = f"\n{movement_preview_text}\n"
                print(f"🗺️ [MOVEMENT DEBUG] Formatted movement preview: '{movement_preview_text}'")
            else:
                print(f"🗺️ [MOVEMENT DEBUG] Movement preview empty or not available")
                movement_preview_text = ""
        except Exception as e:
            print(f"🗺️ [MOVEMENT DEBUG] Error getting movement preview: {e}")
            logger.warning(f"[ACTION] Error getting movement preview: {e}")
            movement_preview_text = ""
            walkable_options = []
    
    # ANTI-STUCK LOGIC: Detect when agent is stuck on a ledge or blocked path
    # If the agent has been pressing the same direction 5+ times and hasn't moved, override VLM
    if recent_actions and len(recent_actions) >= 5:
        last_5_actions = recent_actions[-5:]
        # Check if all last 5 actions are the same movement direction
        if all(action == last_5_actions[0] for action in last_5_actions) and last_5_actions[0] in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
            stuck_direction = last_5_actions[0]
            print(f"🚨 [ANTI-STUCK] Agent pressed {stuck_direction} 5+ times in a row!")
            
            # Check if movement preview shows this direction is blocked
            if movement_preview_text and "BLOCKED" in movement_preview_text:
                if stuck_direction in movement_preview_text.split("BLOCKED")[0][-20:]:  # Check if stuck direction is near BLOCKED text
                    print(f"🚨 [ANTI-STUCK] {stuck_direction} is BLOCKED (ledge or obstacle)!")
                    print(f"🚨 [ANTI-STUCK] Choosing alternative walkable direction...")
                    
                    # Parse walkable directions from movement preview
                    walkable_directions = []
                    for direction in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
                        if direction in movement_preview_text:
                            # Check if this direction is marked WALKABLE
                            direction_line_start = movement_preview_text.find(direction)
                            direction_line_end = movement_preview_text.find('\n', direction_line_start)
                            direction_line = movement_preview_text[direction_line_start:direction_line_end]
                            if 'WALKABLE' in direction_line:
                                walkable_directions.append(direction)
                    
                    if walkable_directions:
                        # Choose first walkable direction that isn't the stuck one
                        alternative_direction = next((d for d in walkable_directions if d != stuck_direction), walkable_directions[0])
                        print(f"✅ [ANTI-STUCK] Overriding VLM: choosing {alternative_direction} instead of {stuck_direction}")
                        logger.info(f"[ACTION] Anti-stuck override: {alternative_direction} (was stuck on {stuck_direction})")
                        return [alternative_direction]
    
    # Build action prompt with multiple-choice format if we have walkable options
    if walkable_options and len(walkable_options) > 0:
        # MULTIPLE-CHOICE FORMAT: Present WALKABLE options + INTERACT option if needed
        
        # ANTI-OSCILLATION: Track recent positions to detect bouncing between 2-3 tiles
        if not hasattr(action_step, 'position_history'):
            action_step.position_history = []
        
        # Add current position to history (keep last 10)
        current_pos_tuple = (current_x, current_y)
        action_step.position_history.append(current_pos_tuple)
        if len(action_step.position_history) > 10:
            action_step.position_history.pop(0)
        
        # Check if oscillating between 2-3 positions
        oscillation_warning = ""
        if len(action_step.position_history) >= 6:
            recent_positions = action_step.position_history[-6:]
            unique_positions = set(recent_positions)
            
            if len(unique_positions) <= 2:
                # Agent is bouncing between 1-2 positions - definitely stuck!
                oscillation_warning = "⚠️ WARNING: You've been oscillating between the same positions! TRY A DIFFERENT DIRECTION you haven't tried recently."
                print(f"🔄 [OSCILLATION DETECTED] Agent bouncing between {unique_positions} in last 6 steps!")
            elif len(unique_positions) == 3 and len(recent_positions) >= 8:
                # Check last 8 steps
                recent_8 = action_step.position_history[-8:] if len(action_step.position_history) >= 8 else action_step.position_history
                if len(set(recent_8)) <= 3:
                    oscillation_warning = "⚠️ You're moving in a small loop. Explore in a NEW direction to find the exit."
                    print(f"🔄 [SMALL LOOP] Agent stuck in small area: {set(recent_8)}")
        
        # Check if there are nearby NPCs or interactable objects
        has_interactables = False
        interactable_description = ""
        
        if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
            visual_data = latest_observation['visual_data']
            
            # Check for visible entities (NPCs, Pokemon)
            entities = visual_data.get('visible_entities', [])
            if entities and any(e for e in entities if e and e not in ['none', 'null', '']):
                has_interactables = True
                entity_list = []
                if isinstance(entities, list):
                    for e in entities:
                        if e and e not in ['none', 'null', '']:
                            if isinstance(e, dict):
                                entity_list.append(e.get('name', 'NPC'))
                            else:
                                entity_list.append(str(e))
                interactable_description = f"NPCs: {', '.join(entity_list[:3])}" if entity_list else ""
            
            # Check for interactable objects
            nav_info = visual_data.get('navigation_info', {})
            interactables = nav_info.get('interactable_objects', [])
            if interactables and any(obj for obj in interactables if obj and obj not in ['none', 'null', '']):
                has_interactables = True
                obj_list = [str(o) for o in interactables if o and o not in ['none', 'null', '']]
                if interactable_description:
                    interactable_description += f", Objects: {', '.join(obj_list[:3])}"
                else:
                    interactable_description = f"Objects: {', '.join(obj_list[:3])}"
        
        # Build the combined options list: movement + interact
        all_options = walkable_options.copy()
        
        if has_interactables:
            all_options.append({
                'direction': 'INTERACT',
                'details': f'Press A to interact ({interactable_description})',
                'is_interact': True
            })
            print(f"🎯 [INTERACT MODE] Added INTERACT option - {interactable_description}")
        
        # Extract just the objective for clarity
        objective_line = ""
        if current_plan and "OBJECTIVE:" in current_plan:
            objective_start = current_plan.find("OBJECTIVE:")
            objective_end = current_plan.find("\n", objective_start)
            objective_line = current_plan[objective_start:objective_end] if objective_end > 0 else current_plan[objective_start:objective_start+100]
        
        # Check which directions are available
        available_directions = [opt['direction'] for opt in walkable_options]
        
        # Context-aware goal based on location
        location = state_data.get('player', {}).get('location', '')
        
        if 'MOVING_VAN' in location.upper():
            # In the moving van - goal is to find and exit through the door
            goal = "Exit the moving van through the door"
            if 'RIGHT' in available_directions:
                instruction = "The door is to the RIGHT (EAST). Choose RIGHT to exit the van."
            elif 'LEFT' in available_directions or 'UP' in available_directions or 'DOWN' in available_directions:
                instruction = "Explore the van to find the door. Try different directions."
            else:
                instruction = "No clear path. Try moving to find the exit."
        elif 'HOUSE' in location.upper() or 'ROOM' in location.upper():
            # Inside a building - look for stairs or doors
            goal = "Exit the building"
            if 'DOWN' in available_directions:
                instruction = "Stairs/exit might be DOWN. Try DOWN to exit."
            else:
                instruction = "Look for stairs or a door to exit. Explore the room."
        else:
            # Overworld - default to heading north toward Oldale Town
            goal = "Navigate to Oldale Town (NORTH)"
            if 'UP' in available_directions:
                instruction = "Oldale Town is NORTH. Choose UP to move NORTH."
            else:
                instruction = "Oldale Town is NORTH. UP is blocked. Choose LEFT or RIGHT to go around."
        
        action_prompt = f"""{goal}

Position: ({current_x}, {current_y})
{instruction}

{oscillation_warning}

Options:
"""
        # Add numbered options for all options (movement + interact)
        print(f"🔍 [PROMPT BUILDER DEBUG] Building numbered list from {len(all_options)} options:")
        for i, option in enumerate(all_options, 1):
            action_prompt_line = f"{i}. {option['direction']} - {option['details']}\n"
            print(f"   Adding to prompt: '{action_prompt_line.strip()}'")
            action_prompt += action_prompt_line
        
        action_prompt += f"""
Answer with just the number (1-{len(all_options)})."""
        
        # Store all_options for parsing later
        walkable_options = all_options
    else:
        # FALLBACK: Original free-form prompt when no movement options available
        action_prompt = f"""Playing Pokemon Emerald. Screen: {visual_context}

{strategic_goal}=== NAVIGATION TASK ===

**CRITICAL: You have access to your COMPLETE explored map (shown above in EXTENDED MAP VIEW if available).**

**Step 1: Check the EXTENDED MAP VIEW (if shown above)**
- This shows the ENTIRE area you've explored, not just your immediate 15x15 view
- You are marked as 'P' on the map
- Use this to see paths, dead ends, and unexplored areas
- Plan your route to avoid getting stuck in cul-de-sacs

**Step 2: Check the MOVEMENT PREVIEW** below for immediate options:
{movement_preview_text}

**Step 3: Choose ONE WALKABLE direction** that:
- Avoids dead ends visible on the extended map
- Moves toward your strategic goal
- Is marked WALKABLE in the movement preview

**PATHFINDING RULES:**
- If the extended map shows a dead end ahead, DON'T GO THERE - backtrack
- If you're stuck (no forward progress), check the extended map for alternate routes
- NEVER repeatedly move into blocked tiles

=== DECISION RULES ===

🚨 **IF DIALOGUE BOX IS VISIBLE** (you see text at bottom of screen):
   → Press A to advance/close the dialogue

🎯 **IF IN OVERWORLD** (no dialogue, no menu):
   → First: Check EXTENDED MAP VIEW (above) to plan your route and avoid dead ends
   → Second: Choose a WALKABLE direction from MOVEMENT PREVIEW
   → Third: Move toward your goal while avoiding obstacles visible on the extended map

📋 **IF IN MENU**:
   → Use UP/DOWN to navigate options
   → Press A to select

⚔️ **IF IN BATTLE**:
   → Press A for moves/attacks

=== OUTPUT FORMAT - CRITICAL ===
You MUST respond with this EXACT format:

Line 1-2: Brief reasoning about THIS SPECIFIC frame (what you actually see, your current goal, your chosen direction)
Line 3: ONLY the button name - ONE of these exact words: A, B, UP, DOWN, LEFT, RIGHT, START

⚠️ CRITICAL INSTRUCTIONS:
1. ANALYZE THIS SPECIFIC FRAME
2. Look at the MOVEMENT PREVIEW to see which directions are WALKABLE
3. Choose a direction that matches your strategic goal
4. DO NOT hallucinate doors or features not visible in the movement data
5. If you're navigating to a location, pick the direction that gets you closer

Example 1 - Movement:
I'm on Route 101. My goal is north. The movement preview shows UP is walkable.
UP

Example 2 - Dialogue:
I see a dialogue box at the bottom with text. I need to close it.
A

Example 3 - Navigation:
I need to go to Littleroot Town which is south. DOWN is walkable according to preview.
DOWN

Now analyze THIS frame and respond with your reasoning and button:
"""
    
    # Construct complete prompt for VLM
    complete_prompt = system_prompt + action_prompt
    
    # GUARANTEED DEBUG: Always show VLM call and response
    # Double-check step calculation for VLM mode
    actual_step = len(recent_actions) if recent_actions else 0
    print(f"📞 [VLM CALL] Step {actual_step} (calculated from {len(recent_actions) if recent_actions else 0} recent_actions) - About to call VLM")
    
    # PERCEPTION DEBUG: Show what visual context we received
    print(f"👁️ [PERCEPTION DEBUG] Latest observation type: {type(latest_observation)}")
    if isinstance(latest_observation, dict):
        print(f"👁️ [PERCEPTION DEBUG] Observation keys: {list(latest_observation.keys())}")
        if 'visual_data' in latest_observation:
            vd = latest_observation['visual_data']
            print(f"👁️ [PERCEPTION DEBUG] Visual data keys: {list(vd.keys()) if vd else 'None'}")
            print(f"👁️ [PERCEPTION DEBUG] Screen context: '{vd.get('screen_context', 'missing')}' | Method: {latest_observation.get('extraction_method', 'unknown')}")
            print(f"👁️ [PERCEPTION DEBUG] On-screen text: {vd.get('on_screen_text', {})}")
            
            # ENHANCED PERCEPTION ANALYSIS
            screen_ctx = vd.get('screen_context', 'missing')
            dialogue_data = vd.get('on_screen_text', {}).get('dialogue', '')
            visual_elements = vd.get('visual_elements', {})
            
            print(f"👁️ [PERCEPTION ANALYSIS] Screen classification analysis:")
            print(f"   - VLM classified as: '{screen_ctx}'")
            print(f"   - Dialogue present: {bool(dialogue_data)}")
            print(f"   - Dialogue content: '{dialogue_data}'")
            print(f"   - Visual elements: {visual_elements}")
            
            # Check for dialogue box misclassification
            if dialogue_data and screen_ctx == 'overworld':
                print(f"🚨 [MISCLASSIFICATION] VLM says 'overworld' but dialogue exists!")
                print(f"🚨 [MISCLASSIFICATION] This is likely a dialogue screen misclassified as overworld!")
                
            # Check for box interaction patterns
            dialogue_data = vd.get('on_screen_text', {}).get('dialogue', '')  
            if dialogue_data and 'pokémon' in dialogue_data.lower() and ('box' in dialogue_data.lower() or 'logo' in dialogue_data.lower()):
                print(f"🎁 [BOX DETECTED] This appears to be box/sign dialogue that blocks movement!")
                print(f"🎁 [BOX DETECTED] Player must press A to close dialogue before movement works!")
        else:
            print(f"👁️ [PERCEPTION DEBUG] No visual_data in observation!")
    else:
        print(f"👁️ [PERCEPTION DEBUG] Observation is not a dict: {latest_observation}")
    
    # CRITICAL DEBUG: Why is recent_actions empty?
    if recent_actions is None:
        print(f"⚠️ [CRITICAL] recent_actions is None!")
    elif len(recent_actions) == 0:
        print(f"⚠️ [CRITICAL] recent_actions is empty list!")
    else:
        print(f"✅ [DEBUG] recent_actions has {len(recent_actions)} items: {recent_actions[-5:] if len(recent_actions) > 5 else recent_actions}")
    
    # Safe visual context logging
    visual_preview = visual_context[:100] + "..." if visual_context and len(visual_context) > 100 else (visual_context or "None")
    strategic_preview = strategic_goal[:100] + "..." if strategic_goal and len(strategic_goal) > 100 else (strategic_goal or "None")
    
    print(f"🔍 [VLM DEBUG] Step {actual_step} - Calling VLM with visual_context: '{visual_preview}'")
    print(f"   Strategic goal: '{strategic_preview}'")
    
    # DEBUG: Show the actual prompt being sent to VLM
    print(f"🔍 [VLM PROMPT DEBUG] Complete prompt length: {len(complete_prompt)} chars")
    
    # Check if movement preview is in the prompt
    if "MOVEMENT PREVIEW:" in complete_prompt:
        print(f"✅ [VLM PROMPT DEBUG] Movement preview IS included in prompt")
        # Movement preview check (only log if actually missing in navigation mode)
        mp_start = complete_prompt.find("MOVEMENT PREVIEW:")
        if mp_start == -1 and visual_context == 'overworld':
            logger.warning("[VLM PROMPT] Movement preview missing in overworld mode")
        # Otherwise it's expected (dialogue/battle) - don't log
    
    # Check if we're using multiple-choice mode
    if walkable_options and len(walkable_options) > 0:
        print(f"🎯 [MULTIPLE-CHOICE MODE] Presenting {len(walkable_options)} walkable options to VLM:")
        for i, opt in enumerate(walkable_options, 1):
            print(f"   {i}. {opt['direction']} - {opt['details']}")
    else:
        print(f"📝 [FREE-FORM MODE] Using traditional free-form action selection")
    
    # VLM prompt validation (only log on errors or periodically)
    if current_step % 100 == 0:
        logger.debug(f"VLM prompt length: {len(complete_prompt)} chars")
    
    # ULTRA DEBUG: Show the exact numbered list section
    if walkable_options and "YOUR MOVEMENT CHOICES" in complete_prompt:
        list_start = complete_prompt.find("YOUR MOVEMENT CHOICES")
        # Numbered list validation (only log issues)
        list_section = complete_prompt[list_start:list_start+500]
        if "1." not in list_section:
            logger.warning("[NUMBERED LIST] Options list formatting may be incorrect")
    elif "1." in complete_prompt and walkable_options:
        # Fallback: try to find first numbered option
        if "READ THE LIST:" in complete_prompt:
            list_start = complete_prompt.find("READ THE LIST:")
        else:
            list_start = complete_prompt.find("1.")
        # Validate but don't print unless there's an issue
        if list_start == -1:
            logger.warning("[NUMBERED LIST] Could not find numbered options in prompt")
    
    action_response = vlm.get_text_query(complete_prompt, "ACTION")
    
    # VLM RESPONSE VALIDATION: Detect and handle problematic responses
    if action_response and len(action_response) > 500:
        print(f"⚠️ [VLM WARNING] Response is suspiciously long ({len(action_response)} chars) - possible hallucination detected!")
        # Truncate to first 200 characters to avoid processing garbage
        action_response = action_response[:200]
        print(f"   Truncated to: '{action_response}'")
    
    # Check for repetitive patterns that indicate hallucination
    if action_response and len(action_response) > 50:
        first_50 = action_response[:50].lower()
        if "you are in battle mode" in first_50 and action_response.lower().count("you are in battle mode") > 3:
            print(f"🚨 [VLM ERROR] Detected repetitive hallucination - forcing simple 'A' response")
            action_response = "A"
    
    # GUARANTEED DEBUG: Always show FULL VLM response including reasoning
    print(f"🔍 [VLM RESPONSE] Step {actual_step} - FULL Response:")
    print("=" * 80)
    print(action_response)
    print("=" * 80)
    
    # SAFETY CHECK: Handle None or empty VLM response
    if action_response is None:
        logger.warning("[ACTION] VLM returned None response, using fallback action")
        action_response = "A"  # Safe fallback
    else:
        action_response = action_response.strip()
    
    valid_buttons = ['A', 'B', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT']
    
    # DEBUG: Show what we're about to parse
    print(f"🔍 [PARSING] Step {actual_step} - About to parse response (type: {type(action_response)})")
    
    # ROBUST PARSING: Handle various VLM response formats
    actions = []
    
    if action_response:
        # NEW FORMAT: Expect reasoning followed by action on last line
        # Split by newlines and get the last non-empty line as the action
        lines = [line.strip() for line in action_response.split('\n') if line.strip()]
        
        if len(lines) >= 2:
            # Extract reasoning (all lines except last)
            reasoning = '\n'.join(lines[:-1])
            action_line = lines[-1].upper()
            
            print(f"🧠 [VLM REASONING] {reasoning}")
            print(f"🎮 [VLM ACTION LINE] {action_line}")
        elif len(lines) == 1:
            # Only one line - treat as action without reasoning
            action_line = lines[0].upper()
            print(f"⚠️ [NO REASONING] VLM provided action without reasoning")
            print(f"🎮 [VLM ACTION LINE] {action_line}")
        else:
            # Empty response
            print(f"❌ [EMPTY RESPONSE] VLM returned empty response")
            action_line = "A"  # Fallback
        
        response_str = action_line
        
        # PRIORITY 0: MULTIPLE-CHOICE PARSING (if we provided walkable options)
        if walkable_options and len(walkable_options) > 0:
            print(f"🎯 [MULTIPLE-CHOICE] Parsing response for {len(walkable_options)} options")
            
            # Try to extract a number from the response
            import re
            number_match = re.search(r'\b([1-9])\b', response_str)
            
            if number_match:
                choice_num = int(number_match.group(1))
                print(f"✅ [CHOICE DETECTED] VLM selected option {choice_num}")
                
                # Validate the choice is within range
                if 1 <= choice_num <= len(walkable_options):
                    selected_option = walkable_options[choice_num - 1]
                    selected_direction = selected_option['direction']
                    print(f"✅ [MULTIPLE-CHOICE] Option {choice_num} maps to: {selected_direction}")
                    print(f"   Details: {selected_option['details']}")
                    
                    # Handle INTERACT option - convert to A button press
                    if selected_direction == 'INTERACT':
                        actions = ['A']
                        print(f"🎯 [INTERACT] Converting INTERACT to A button press")
                    else:
                        actions = [selected_direction]
                else:
                    print(f"❌ [INVALID CHOICE] Option {choice_num} out of range (1-{len(walkable_options)})")
                    # Fallback to first option
                    actions = [walkable_options[0]['direction']]
                    print(f"   Using fallback: {actions[0]}")
            else:
                # No number found - check if VLM responded with button (like "A" for dialogue)
                print(f"⚠️ [NO NUMBER] VLM didn't provide a number, checking for button names...")
                # Will fall through to button parsing below
        
        # PRIORITY 1: Check if response starts with a valid button (most common case)
        if not actions:  # Only parse as button if we didn't already get a direction from multiple-choice
            first_line = response_str.split('\n')[0].strip().upper()
            
            # Clean up common VLM artifacts in the first line
            cleaned_first_line = first_line
            for artifact in ['</OUTPUT>', '</output>', '<|END|>', '<|end|>', '<|ASSISTANT|>', '<|assistant|>', '|user|']:
                cleaned_first_line = cleaned_first_line.replace(artifact, '').strip()
            
            if cleaned_first_line in valid_buttons:
                actions = [cleaned_first_line]
            elif first_line in valid_buttons:
                actions = [first_line]
            # PRIORITY 1.5: Handle "A (explanation)" format by extracting just the button
            elif '(' in first_line:
                # Extract button before parentheses: "A (to attack)" -> "A"
                button_part = first_line.split('(')[0].strip().upper()
                if button_part in valid_buttons:
                    actions = [button_part]
        
        # PRIORITY 2: Try direct parsing (exact match)
        elif ',' in response_str:
            # Multi-action response
            raw_actions = [btn.strip().upper() for btn in response_str.split(',')]
            actions = [btn for btn in raw_actions if btn in valid_buttons][:3]
        
        # PRIORITY 3: Try exact match of whole response (with cleanup)
        elif response_str.upper() in valid_buttons:
            actions = [response_str.upper()]
        
        # PRIORITY 3.5: Try cleaned version of whole response
        if not actions:
            # Clean common VLM artifacts from the whole response
            cleaned_response = response_str.upper()
            for artifact in ['</OUTPUT>', '</output>', '<|END|>', '<|end|>', '<|ASSISTANT|>', '<|assistant|>', '|user|', '|assistant|']:
                cleaned_response = cleaned_response.replace(artifact, '').strip()
            
            if cleaned_response in valid_buttons:
                actions = [cleaned_response]
        
        # PRIORITY 4: Extract first valid button found anywhere in response
        if not actions:
            # Look for button names in order of preference (case insensitive)
            for button in valid_buttons:
                if button.lower() in response_str.lower():
                    actions = [button]
                    break
            
            # PRIORITY 5: Try common patterns if still no match
            if not actions:
                response_lower = response_str.lower()
                if 'up' in response_lower or 'north' in response_lower:
                    actions = ['UP']
                elif 'down' in response_lower or 'south' in response_lower:
                    actions = ['DOWN']
                elif 'left' in response_lower or 'west' in response_lower:
                    actions = ['LEFT']
                elif 'right' in response_lower or 'east' in response_lower:
                    actions = ['RIGHT']
                elif 'interact' in response_lower or 'confirm' in response_lower or 'select' in response_lower:
                    actions = ['A']
                elif 'back' in response_lower or 'cancel' in response_lower or 'menu' in response_lower:
                    actions = ['B']
    
    print(f"✅ Parsed actions: {actions}")
    if len(actions) == 0:
        print(f"❌ No valid actions parsed from: '{action_response}' - using fallback default")
        print(f"   Valid buttons are: {valid_buttons}")
        print(f"   Response length: {len(str(action_response)) if action_response else 'None'}")
        
        # ANTI-HALLUCINATION: If VLM is producing garbage, force a simple action
        if action_response and len(action_response) > 200:
            print(f"🚨 [ANTI-HALLUCINATION] VLM response too long - forcing simple navigation")
            actions = [random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT', 'A'])]
            print(f"   Anti-hallucination action: {actions}")
    else:
        print(f"✅ Successfully parsed {len(actions)} action(s): {actions}")
    
    print("-" * 80 + "\n")
    
    # ANTI-LOOP LOGIC: Detect if we're stuck pressing A repeatedly and force exploration
    if actions == ['A'] and recent_actions:
        recent_a_count = sum(1 for action in recent_actions[-10:] if action == 'A')  # Count A presses in last 10 actions
        if recent_a_count >= 8 and len(recent_actions) >= 10:  # If 8+ out of last 10 actions were A AND we have enough history
            print(f"🔄 [ANTI-LOOP] Step {current_step} - Detected A-loop ({recent_a_count}/10 recent actions). Forcing exploration.")
            exploration_options = ['UP', 'DOWN', 'LEFT', 'RIGHT']
            actions = [random.choice(exploration_options)]
            print(f"   Forcing exploration with: {actions}")
    
    # If no valid actions found, make intelligent default based on state
    if not actions:
        if game_data.get('in_battle', False):
            actions = ['A']  # Attack in battle
        elif party_health['total_count'] == 0:
            actions = ['A', 'A', 'A']  # Try to progress dialogue/menu
        else:
            actions = [random.choice(['A', 'RIGHT', 'UP', 'DOWN', 'LEFT'])]  # Random exploration
    
    logger.info(f"[ACTION] Actions decided: {', '.join(actions)}")
    final_step = len(recent_actions) if recent_actions else 0
    print(f"🎮 [FINAL ACTION] Step {final_step} - Returning actions: {actions}")
    return actions 