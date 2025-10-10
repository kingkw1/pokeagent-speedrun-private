import logging
import random
import sys
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
    # TEMPORARY FIX: Hard-coded rule for title screen to bypass VLM
    game_data = state_data.get('game', {})
    if game_data.get('state') == 'title':
        logger.info("[ACTION] Title screen detected - bypassing VLM and returning 'A'")
        return ["A"]
    
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
        action_context.append(f"Recent Actions: {', '.join(list(recent_actions)[-5:])}")
    
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
    
    action_prompt = f"""
    ★★★ COMPREHENSIVE GAME STATE DATA ★★★
    
    {state_context}
    
    ★★★ ENHANCED ACTION CONTEXT ★★★
    
    {context_str}
    
    ★★★ ACTION DECISION TASK ★★★
    
    You are the agent playing Pokemon Emerald with a speedrunning mindset. Make quick, efficient decisions.
    
    Memory Context: {memory_context}
    Current Plan: {current_plan if current_plan else 'No plan yet'}
    Latest Observation: {format_observation_for_action(latest_observation)}
    
    Based on the comprehensive state information above, decide your next action(s):
    
    BATTLE STRATEGY:
    - If in battle: Choose moves strategically based on type effectiveness and damage
    - Consider switching pokemon if current one is weak/low HP
    - Use items if pokemon is in critical condition
    
    NAVIGATION STRATEGY:
    - Use movement options analysis above for efficient navigation
    - Avoid blocked tiles (marked as BLOCKED)
    - Consider tall grass: avoid if party is weak, seek if need to train/catch
    - Navigate around water unless you have Surf
    - Use coordinates to track progress toward objectives
    
    MENU/DIALOGUE STRATEGY:
    - If in dialogue: A to advance text, B to cancel/skip if possible
    - If in menu: Navigate with UP/DOWN/LEFT/RIGHT, A to select, B to cancel/back out
    - If stuck in menu/interface: B repeatedly to exit to overworld
    - In Pokemon Center: A to talk to Nurse Joy, A to confirm healing
    
    HEALTH MANAGEMENT:
    - If pokemon are low HP/fainted, head to Pokemon Center
    - If no healthy pokemon, prioritize healing immediately
    - Consider terrain: avoid wild encounters if party is weak
    
    EFFICIENCY RULES:
    1. Output sequences of actions when you know what's coming (e.g., "RIGHT, RIGHT, RIGHT, A" to enter a door)
    2. For dialogue: "A, A, A, A, A" to mash through
    3. For movement: repeat directions based on movement options (e.g., "UP, UP, UP, UP" if UP shows "Normal path")
    4. If uncertain, output single action and reassess
    5. Use traversability data: move toward open paths, avoid obstacles
    6. If movement doesn't change coordinates (e.g., RIGHT but X doesn't increase), check map for walls (#) blocking your path
    
    Valid buttons: A, B, SELECT, START, UP, DOWN, LEFT, RIGHT, L, R
    - A: Interact with NPCs/objects, confirm selections, advance dialogue, use moves in battle
    - B: Cancel menus, back out of interfaces, run faster (with running shoes), flee from battle
    - START: Open main menu (Title sequence, Pokedex, Pokemon, Bag, etc.)
    - SELECT: Use registered key item (typically unused)
    - UP/DOWN/LEFT/RIGHT: Move character, navigate menus, select options
    - L/R: Cycle through pages in some menus, switch Pokemon in battle (rare usage)
    
    ⚠️ CRITICAL WARNING: NEVER save the game using the in-game save menu! Saving will crash the entire run and end your progress. If you encounter a save prompt in the game, press B to cancel it immediately!
    
    Return ONLY the button name(s) as a comma-separated list, nothing else.
    Maximum 10 actions in sequence. Avoid repeating same button more than 6 times.
    """
    
    # Construct complete prompt for VLM
    complete_prompt = system_prompt + action_prompt
    
    action_response = vlm.get_text_query(complete_prompt, "ACTION").strip().upper()
    valid_buttons = ['A', 'B', 'SELECT', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'L', 'R']
    
    # Split the response by commas and clean up
    actions = [btn.strip() for btn in action_response.split(',') if btn.strip() in valid_buttons]
    
    print(f"Parsed actions: {actions}")
    if len(actions) == 0:
        print("❌ No valid actions parsed - using default 'A'")
    print("-" * 80 + "\n")
    
    # Limit to maximum 10 actions and prevent excessive repetition
    actions = actions[:10]
    
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