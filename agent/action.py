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
            
        # Add entity information  
        entities = visual_data.get('visible_entities', [])
        if entities:
            entity_names = [e.get('name', 'unnamed') for e in entities[:3]]
            summary += f" | Entities: {', '.join(entity_names)}"
            
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
    current_step = len(recent_actions or [])
    
    # DEBUG: Track our progress every few steps
    if current_step % 10 == 0 and current_step >= 30:
        print(f"🔍 [DEBUG] Step {current_step} reached - Milestone check in progress")
    
    # CRITICAL DEBUG: Force milestone status check at key steps
    if current_step in [33, 34, 35, 40, 45, 50, 51]:
        print(f"🚨 [CRITICAL] Step {current_step}: PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}, INTRO_COMPLETE={milestones.get('INTRO_CUTSCENE_COMPLETE', False)}")
        print(f"   Navigation mode check: intro_complete={intro_complete}, current_step > 50: {current_step > 50}")
    
    # DEBUG: Always log visual data for name selection detection around critical steps
    if current_step >= 30:  # Only log around critical transition
        logger.info(f"[ACTION] Step {current_step} - Name check: dialogue='{dialogue_text}', menu='{menu_title}', PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}")
        logger.info(f"[ACTION] Step {current_step} - Visual data keys: {list(visual_data.keys()) if visual_data else 'None'}")
        logger.info(f"[ACTION] Step {current_step} - On-screen text keys: {list(on_screen_text.keys()) if on_screen_text else 'None'}")
    
    # Check if this looks like name selection screen OR if we're in the critical step range
    name_text_detected = ('YOUR NAME' in dialogue_text or 'NAME?' in dialogue_text or 
                          'YOUR NAME' in menu_title or 'NAME?' in menu_title)
    
    # We know from your image that name selection happens around steps 33-40
    # So let's add step-based detection as backup
    in_name_step_range = (32 <= current_step <= 45 and not milestones.get('PLAYER_NAME_SET', False))
    
    if (name_text_detected or in_name_step_range) and not milestones.get('PLAYER_NAME_SET', False):
        is_name_selection = True
        logger.info("[ACTION] Name selection screen detected!")
        logger.info(f"[ACTION] - text_detected: {name_text_detected}, step_range: {in_name_step_range}")
        logger.info(f"[ACTION] - dialogue: '{dialogue_text}', menu: '{menu_title}'")
        
        # Simple name selection logic - just press A to accept default or navigate quickly
        name_step = current_step - 32  # Normalize to name selection steps
        if name_step < 2:  # First steps: make sure we're at A (default position)
            logger.info("[ACTION] Positioning at 'A'")
            return ["A"]
        elif name_step < 4:  # Quick navigation to confirm
            logger.info("[ACTION] Quick name entry")
            return ["DOWN", "DOWN", "A"]  # Move to OK and confirm
        else:  # Fallback: just keep pressing A to get through
            logger.info("[ACTION] Pressing A to complete name selection")
            return ["A"]
    
    # CRITICAL DEBUG: Override right after PLAYER_NAME_SET to avoid VLM confusion
    # But only until INTRO_CUTSCENE_COMPLETE - then let VLM take over
    intro_complete = milestones.get('INTRO_CUTSCENE_COMPLETE', False)
    
    # DEBUG: Track milestone status at key steps
    if current_step >= 40 and current_step % 5 == 0:  # Every 5th step after 40
        print(f"🏆 [MILESTONE] Step {current_step}: PLAYER_NAME_SET={milestones.get('PLAYER_NAME_SET', False)}, INTRO_CUTSCENE_COMPLETE={intro_complete}")
    
    # NAVIGATION DECISION LOGIC: Clear hierarchy of what mode to use
    
    # 1. Post-name override: Only when name is set but intro cutscene isn't complete yet
    if milestones.get('PLAYER_NAME_SET', False) and not intro_complete and current_step <= 50:
        logger.info(f"[ACTION] Step {current_step} - Post-name override active")
        print(f"🔧 [OVERRIDE] Step {current_step} - Post-name override: pressing A (intro_complete={intro_complete})")
        return ["A"]
    
    # 2. VLM Navigation Mode: When intro is complete OR we're past step 50 (safety fallback)
    elif intro_complete or current_step > 50:
        if current_step % 5 == 0 or current_step in [51, 61, 67]:
            print(f"🤖 [VLM MODE] Step {current_step} - VLM Navigation Active (intro_complete={intro_complete})")
        
        # JUMP directly to VLM call - skip all intermediate processing
        pass  # Continue to VLM logic below
    
    # 3. Legacy mode: Only for early game before VLM navigation is active
    else:
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
        
        # Visible entities
        entities = visual_data.get('visible_entities', [])
        if entities:
            action_context.append("Visible Entities:")
            for entity in entities[:5]:  # Limit to 5 entities to avoid clutter
                action_context.append(f"  - {entity.get('type', 'unknown')}: {entity.get('name', 'unnamed')} at {entity.get('position', 'unknown position')}")
        
        # Visual elements status
        visual_elements = visual_data.get('visual_elements', {})
        active_elements = [k.replace('_', ' ').title() for k, v in visual_elements.items() if v]
        if active_elements:
            action_context.append(f"Active Visual Elements: {', '.join(active_elements)}")
    
    context_str = "\n".join(action_context)
    
    # Get the visual screen context to guide decision making
    visual_context = "unknown"
    if isinstance(latest_observation, dict) and 'visual_data' in latest_observation:
        visual_context = latest_observation['visual_data'].get('screen_context', 'unknown')
    
    # Enhanced Goal-Conditioned Action Prompt (Day 9 Navigation Implementation)
    # Strategic goal integration with tactical movement analysis
    strategic_goal = ""
    if current_plan and current_plan.strip():
        strategic_goal = f"""
=== YOUR STRATEGIC GOAL ===
{current_plan.strip()}

"""
    
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

{context_str}{movement_preview_text}

=== DECISION LOGIC ===
Based on your STRATEGIC GOAL and current situation:

1. **If DIALOGUE/TEXT visible**: Press A to advance
2. **If MENU open**: Use UP/DOWN to navigate, A to select
3. **If BATTLE**: Use A to attack or select moves
4. **If OVERWORLD with STRATEGIC GOAL**: 
   - Analyze the MOVEMENT PREVIEW above
   - Choose the single best direction (UP/DOWN/LEFT/RIGHT) that moves you closer to your goal
   - Consider obstacles, doors, and terrain in your pathfinding
5. **If uncertain or no clear goal**: Use A or explore with single direction

Choose from: A, B, UP, DOWN, LEFT, RIGHT, START
Return 1-3 actions maximum. Focus on the single best action for your strategic goal.
"""
    
    # Construct complete prompt for VLM
    complete_prompt = system_prompt + action_prompt
    
    # GUARANTEED DEBUG: Always show VLM call and response
    print(f"📞 [VLM CALL] Step {current_step} - About to call VLM")
    print(f"🔍 [VLM DEBUG] Step {current_step} - Calling VLM with visual_context: '{visual_context[:100]}...'")
    print(f"   Strategic goal: '{strategic_goal[:100]}...' ")
    
    action_response = vlm.get_text_query(complete_prompt, "ACTION")
    
    # GUARANTEED DEBUG: Always show VLM response
    print(f"🔍 [VLM RESPONSE] Step {current_step} - Raw response: '{action_response}'")
    
    # SAFETY CHECK: Handle None or empty VLM response
    if action_response is None:
        logger.warning("[ACTION] VLM returned None response, using fallback action")
        action_response = "A"  # Safe fallback
    else:
        action_response = action_response.strip().upper()
    
    valid_buttons = ['A', 'B', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT']
    
    # DEBUG: Show what we're about to parse
    print(f"🔍 [PARSING] Step {current_step} - About to parse response: '{action_response}' (type: {type(action_response)})")
    
    # ROBUST PARSING: Handle various VLM response formats
    actions = []
    
    if action_response:
        response_str = str(action_response).strip()
        
        # Try direct parsing first (exact match)
        if ',' in response_str:
            # Multi-action response
            raw_actions = [btn.strip().upper() for btn in response_str.split(',')]
            actions = [btn for btn in raw_actions if btn in valid_buttons][:3]
        else:
            # Single action response - try exact match
            action = response_str.upper()
            if action in valid_buttons:
                actions = [action]
            else:
                # Try to extract action from formatted response
                # Look for button names in the response (case insensitive)
                for button in valid_buttons:
                    if button.lower() in response_str.lower():
                        actions = [button]
                        break
                
                # If still no match, try common patterns
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
                    elif 'a' in response_lower or 'interact' in response_lower or 'confirm' in response_lower:
                        actions = ['A']
                    elif 'b' in response_lower or 'back' in response_lower or 'cancel' in response_lower:
                        actions = ['B']
    
    print(f"✅ Parsed actions: {actions}")
    if len(actions) == 0:
        print(f"❌ No valid actions parsed from: '{action_response}' - using fallback default")
        print(f"   Valid buttons are: {valid_buttons}")
        print(f"   Response length: {len(str(action_response)) if action_response else 'None'}")
    else:
        print(f"✅ Successfully parsed {len(actions)} action(s): {actions}")
    print("-" * 80 + "\n")
    
    # If no valid actions found, make intelligent default based on state
    if not actions:
        if game_data.get('in_battle', False):
            actions = ['A']  # Attack in battle
        elif party_health['total_count'] == 0:
            actions = ['A', 'A', 'A']  # Try to progress dialogue/menu
        else:
            actions = [random.choice(['A', 'RIGHT', 'UP', 'DOWN', 'LEFT'])]  # Random exploration
    
    logger.info(f"[ACTION] Actions decided: {', '.join(actions)}")
    return actions 