import logging
import random
import sys
import logging
import random
from agent.system_prompt import system_prompt
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

def action_step(memory_context, current_plan, latest_observation, frame, state_data, recent_actions, vlm):
    """
    Decide and perform the next action button(s) based on memory, plan, observation, and comprehensive state.
    Returns a list of action buttons as strings.
    
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
    
    # CRITICAL DEBUG: Override right after PLAYER_NAME_SET to avoid VLM confusion
    # But only until INTRO_CUTSCENE_COMPLETE - then let VLM take over
    
    # DEBUG: Track milestone status at key steps
    if current_step >= 40 and current_step % 5 == 0:  # Every 5th step after 40
        print(f"🏆 [MILESTONE] Step {current_step}: PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}, INTRO_CUTSCENE_COMPLETE={intro_complete}")
    
    # NAVIGATION DECISION LOGIC: Clear hierarchy of what mode to use
    
    # 1. Post-name override: Only when name is set but intro cutscene isn't complete yet
    # IMPROVED: Add multiple exit conditions to prevent infinite loops
    player_location = player_data.get('location', '')
    is_in_moving_van = "MOVING_VAN" in str(player_location).upper()
    override_step_limit = 15  # Maximum steps to spend in override mode
    
    # Check for advanced game states that should trigger VLM mode
    on_route_101 = 'ROUTE 101' in str(player_location).upper()
    has_pokemon = state_data.get('player', {}).get('party', [])
    advanced_location = on_route_101 or 'ROUTE' in str(player_location).upper()
    
    if (milestones.get('PLAYER_NAME_SET', False) and 
        not intro_complete and 
        not advanced_location and  # Don't override if we're on routes
        current_step <= override_step_limit and 
        not is_in_moving_van):
        logger.info(f"[ACTION] Step {current_step} - Post-name override active (location: {player_location})")
        print(f"🔧 [OVERRIDE] Step {current_step} - Post-name override: pressing A (intro_complete={intro_complete}, location={player_location})")
        return ["A"]
    
    # 2. VLM Navigation Mode: When intro is complete OR we exceed override limits OR advanced location
    elif intro_complete or current_step > override_step_limit or is_in_moving_van or advanced_location:
        if current_step % 5 == 0 or current_step in [16, 21, 27] or advanced_location:
            print(f"🤖 [VLM MODE] Step {current_step} - VLM Navigation Active (intro_complete={intro_complete}, past_limit={current_step > override_step_limit}, moving_van={is_in_moving_van}, advanced_location={advanced_location})")
        
        # EMERGENCY FIX: Route navigation override with movement preview
        # If we're on a route and about to call VLM but recent actions show A-pressing or truly stuck movement, force movement
        if 'ROUTE' in str(player_location).upper() and recent_actions:
            recent_a_count = sum(1 for action in recent_actions[-2:] if action == 'A')
            
            # REAL stuck detection: Check if position hasn't changed despite movement attempts
            position_data = state_data.get('player', {}).get('position', {})
            current_pos = (position_data.get('x'), position_data.get('y'))
            
            # Count recent movement attempts (not total movements, but attempts that should change position)
            recent_movement_attempts = sum(1 for action in recent_actions[-3:] if action in ['UP', 'DOWN', 'LEFT', 'RIGHT'])
            
            # Check if we're ACTUALLY stuck: movement attempts but position tracking shows we're hitting barriers
            # This requires checking if the last few movements resulted in position changes
            is_position_stuck = False
            if recent_movement_attempts >= 2:
                # If we've tried movement recently, we should be able to see position changes
                # The position_stuck detection would need historical position tracking
                # For now, we'll rely on the movement preview to detect blocked directions
                logger.info(f"[ACTION] Recent movement attempts: {recent_movement_attempts}, current_pos: {current_pos}")
            
            # Trigger emergency navigation for A-pressing (always wrong on routes) 
            # but NOT for repeated directional movement (that's normal navigation)
            if recent_a_count >= 1:  # Only A-pressing is always wrong on routes
                logger.warning(f"[ACTION] A-pressing detected on {player_location}! recent_actions: {recent_actions[-5:]}")
                logger.warning(f"[ACTION] Position: {current_pos}")
                
                # Get movement preview to find walkable directions
                movement_preview_text = ""
                try:
                    movement_preview_text = format_movement_preview_for_llm(state_data)
                    logger.info(f"[ACTION] Movement preview: {movement_preview_text}")
                except Exception as e:
                    logger.warning(f"[ACTION] Error getting movement preview: {e}")
                
                # Parse movement preview to find walkable directions
                walkable_directions = []
                if "MOVEMENT PREVIEW:" in movement_preview_text:
                    for line in movement_preview_text.split('\n'):
                        if any(dir in line for dir in ['UP', 'DOWN', 'LEFT', 'RIGHT']):
                            if 'WALKABLE' in line:
                                direction = next((dir for dir in ['UP', 'DOWN', 'LEFT', 'RIGHT'] if dir in line), None)
                                if direction:
                                    walkable_directions.append(direction)
                
                logger.warning(f"[ACTION] Walkable directions: {walkable_directions}")
                
                # Choose best direction based on route goals and walkability
                # No more artificial direction avoidance - let the agent navigate naturally
                if walkable_directions:
                    # For Route 101, prefer UP if walkable, otherwise try other directions  
                    if 'ROUTE 101' in str(player_location).upper():
                        if 'UP' in walkable_directions:
                            logger.warning(f"[ACTION] Route 101 - using UP (walkable)")
                            return ["UP"]
                        elif 'LEFT' in walkable_directions:
                            logger.warning(f"[ACTION] Route 101 - using LEFT (UP blocked)")
                            return ["LEFT"] 
                        elif 'RIGHT' in walkable_directions:
                            logger.warning(f"[ACTION] Route 101 - using RIGHT (UP blocked)")
                            return ["RIGHT"]
                        elif 'DOWN' in walkable_directions:
                            logger.warning(f"[ACTION] Route 101 - using DOWN (other directions blocked)")
                            return ["DOWN"]
                    
                    # Generic route navigation - try first walkable direction
                    chosen_direction = walkable_directions[0]
                    logger.warning(f"[ACTION] Using first walkable direction: {chosen_direction}")
                    return [chosen_direction]
                else:
                    # No walkable directions found, try different approach
                    logger.warning(f"[ACTION] No walkable directions found! Trying RIGHT as fallback")
                    return ["RIGHT"]
        
        # JUMP directly to VLM call - skip all intermediate processing
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
    
    # Get formatted state context and useful summaries
    state_context = format_state_for_llm(state_data)
    state_summary = format_state_summary(state_data)
    movement_options = get_movement_options(state_data)
    party_health = get_party_health_summary(state_data)
    
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
            if 'player_pokemon' in battle_info:
                player_pkmn = battle_info['player_pokemon']
                action_context.append(f"Your Pokemon: {player_pkmn.get('species_name', player_pkmn.get('species', 'Unknown'))} (Lv.{player_pkmn.get('level', '?')}) HP: {player_pkmn.get('current_hp', '?')}/{player_pkmn.get('max_hp', '?')}")
            if 'opponent_pokemon' in battle_info:
                opp_pkmn = battle_info['opponent_pokemon']
                action_context.append(f"Opponent: {opp_pkmn.get('species_name', opp_pkmn.get('species', 'Unknown'))} (Lv.{opp_pkmn.get('level', '?')}) HP: {opp_pkmn.get('current_hp', '?')}/{opp_pkmn.get('max_hp', '?')}")
    else:
        action_context.append("=== OVERWORLD MODE ===")
        
        # Movement options from utility
        if movement_options:
            action_context.append("Movement Options:")
            for direction, description in movement_options.items():
                action_context.append(f"  {direction}: {description}")
    
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
        if on_screen_text.get('dialogue'):
            action_context.append(f"Dialogue: \"{on_screen_text['dialogue']}\" - {on_screen_text.get('speaker', 'Unknown')}")
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
    if not game_data.get('in_battle', False):  # Only show movement options in overworld
        try:
            movement_preview_text = format_movement_preview_for_llm(state_data)
            if movement_preview_text and movement_preview_text != "Movement preview: Not available":
                movement_preview_text = f"\n{movement_preview_text}\n"
        except Exception as e:
            logger.warning(f"[ACTION] Error getting movement preview: {e}")
            movement_preview_text = ""
    
    action_prompt = f"""Playing Pokemon Emerald. Current screen: {visual_context}

{strategic_goal}Situation: {format_observation_for_action(latest_observation)}

{context_str}{movement_preview_text}{navigation_guidance}

=== DECISION LOGIC ===
Based on your STRATEGIC GOAL and current situation:

1. **If DIALOGUE/TEXT visible**: Press A to advance
2. **If MENU open**: Use UP/DOWN to navigate, A to select
3. **If BATTLE**: Use A to attack or select moves
4. **If OVERWORLD - Room Navigation**: 
   - FIRST: Check NAVIGATION ANALYSIS above for exits and doors
   - If VLM detected exits/doors, move toward them using UP/DOWN/LEFT/RIGHT
   - If no clear exits visible, explore systematically (try each direction)
   - AVOID repeatedly pressing A on objects unless they're clearly exits/doors
5. **If OVERWORLD - Route/Town**: 
   - Use MOVEMENT PREVIEW to navigate toward your STRATEGIC GOAL
   - Choose direction that advances toward next objective
6. **If uncertain**: Explore with UP/DOWN/LEFT/RIGHT (avoid A unless on clear interactables)

RESPOND WITH ONLY ONE BUTTON NAME: A, B, UP, DOWN, LEFT, RIGHT, START

NO explanations. NO extra text. NO repetition. Just one button name.
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
    
    # GUARANTEED DEBUG: Always show VLM response
    response_preview = action_response[:200] + "..." if action_response and len(action_response) > 200 else action_response
    print(f"🔍 [VLM RESPONSE] Step {actual_step} - Raw response: '{response_preview}'")
    
    # SAFETY CHECK: Handle None or empty VLM response
    if action_response is None:
        logger.warning("[ACTION] VLM returned None response, using fallback action")
        action_response = "A"  # Safe fallback
    else:
        action_response = action_response.strip().upper()
    
    valid_buttons = ['A', 'B', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT']
    
    # DEBUG: Show what we're about to parse
    print(f"🔍 [PARSING] Step {actual_step} - About to parse response: '{action_response}' (type: {type(action_response)})")
    
    # ROBUST PARSING: Handle various VLM response formats
    actions = []
    
    if action_response:
        response_str = str(action_response).strip()
        
        # PRIORITY 1: Check if response starts with a valid button (most common case)
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