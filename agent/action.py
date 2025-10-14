import logging
import random
import sys
import logging
import random
from agent.system_prompt import system_prompt
from utils.state_formatter import format_state_for_llm, format_state_summary, get_movement_options, get_party_health_summary
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
    
    # Multiple robust conditions for title/menu screen detection
    is_title_screen = (
        # Direct title sequence detection
        player_location == "TITLE_SEQUENCE" or
        # Game state indicates title/intro
        "title" in game_state_value or "intro" in game_state_value or
        # Player name not set (indicates title sequence)
        not player_name or player_name == "????????" or
        # Check if no pokemon in party (common at game start)
        game_data.get('party_count', 0) == 0 or
        # Legacy checks for other menu indicators
        player_location.lower() in ['title', 'menu', 'main_menu', '', 'unknown'] or
        'new game' in player_location.lower() or
        # Check if we have invalid player position (common in menus)
        (player_data.get('position', {}).get('x', -1) <= 0 and 
         player_data.get('position', {}).get('y', -1) <= 0)
    )
    
    if is_title_screen:
        logger.info(f"[ACTION] Title screen detected!")
        logger.info(f"[ACTION] - player_location: '{player_location}'")
        logger.info(f"[ACTION] - game_state: '{game_state_value}'")
        logger.info(f"[ACTION] - player_name: '{player_name}'")
        logger.info(f"[ACTION] - party_count: {game_data.get('party_count', 0)}")
        logger.info(f"[ACTION] - position: {player_data.get('position', {})}")
        logger.info("[ACTION] Using simple navigation: A to select NEW GAME")
        return ["A"]
    
    # Debug logging for state detection (only if not in title)
    if not is_title_screen:
        logger.info(f"[ACTION] Debug - game_state: '{game_state_value}', location: '{player_location}', position: {player_data.get('position', {})}")
    
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
            action_context.append(f"Button Prompts: {', '.join(on_screen_text['button_prompts'])}")
        
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
    
    action_prompt = f"""
    Playing Pokemon Emerald. Current screen: {visual_context}
    
    Situation: {format_observation_for_action(latest_observation)}
    
    {context_str}
    
    What should I do?
    - If text/dialogue visible: A
    - If menu open: UP, DOWN, or A  
    - If overworld with clear path: direction or short sequence like "RIGHT, RIGHT"
    - If uncertain: single action
    
    Choose from: A, B, UP, DOWN, LEFT, RIGHT, START
    Give me 1-3 actions maximum.
    """
    
    # Construct complete prompt for VLM
    complete_prompt = system_prompt + action_prompt
    
    action_response = vlm.get_text_query(complete_prompt, "ACTION")
    
    # SAFETY CHECK: Handle None or empty VLM response
    if action_response is None:
        logger.warning("[ACTION] VLM returned None response, using fallback action")
        action_response = "A"  # Safe fallback
    else:
        action_response = action_response.strip().upper()
    
    valid_buttons = ['A', 'B', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT']
    
    # Parse multi-action sequences (up to 3 actions for navigation efficiency)
    if ',' in action_response:
        actions = [btn.strip() for btn in action_response.split(',') if btn.strip() in valid_buttons][:3]
    else:
        # Single action response
        action = action_response.strip()
        actions = [action] if action in valid_buttons else []
    
    print(f"Parsed actions: {actions}")
    if len(actions) == 0:
        print("❌ No valid actions parsed - using default 'A'")
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