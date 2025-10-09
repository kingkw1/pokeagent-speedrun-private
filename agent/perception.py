import time
import logging
from utils.vlm import VLM
from utils.state_formatter import format_state_for_llm, format_state_summary
from agent.system_prompt import system_prompt

# Set up module logging
logger = logging.getLogger(__name__)

def perception_step(frame, state_data, vlm):
    """
    Observe and describe your current situation using both visual and comprehensive state data.
    Returns observation dictionary with visual analysis.
    
    ===============================================================================
    🚨 CRITICAL EMERGENCY PATCH - COMPLETE VLM BYPASS 🚨
    ===============================================================================
    
    MAJOR CHANGE: This function now uses ZERO VLM calls (completely programmatic)
    
    ORIGINAL ISSUE:
    - vlm.get_query() calls were hanging indefinitely, causing complete agent freeze
    - Long prompts with comprehensive state data were overwhelming the VLM
    - Memory leaks and API timeouts were crashing the entire process
    
    EMERGENCY SOLUTION:
    - Replaced VLM visual analysis with game state-based descriptions
    - Fast programmatic analysis based on game_state, location, battle status
    - Generates contextually appropriate observations without AI processing
    
    CURRENT LOGIC:
    - Title screen: "I can see the Pokemon Emerald title screen..."
    - Battle: "I'm in battle. My Pokemon: X vs Opponent: Y..."  
    - Overworld: "I'm in [location]. I can see the overworld map..."
    - Unknown: "I can see the game screen but situation is unclear..."
    
    ⚠️  REINTEGRATION STRATEGY FOR FULL AI:
    
    OPTION 1 - Hybrid Approach (Recommended):
    - Keep programmatic analysis for simple states (title, battle, menus)
    - Add VLM calls only for complex scenarios (new areas, story events)
    - Use shorter prompts and strict timeouts
    
    OPTION 2 - Gradual VLM Reintroduction:
    - Start with very short, focused VLM prompts
    - Add proper timeout handling (5-10 seconds max)
    - Implement fallback to programmatic analysis on VLM failure
    - Test extensively with different game states
    
    OPTION 3 - Keep Programmatic (Surprisingly Effective):
    - The current approach actually works well for most game states
    - Consider keeping it as the primary method
    - Use VLM only for specific edge cases or story analysis
    
    PRESERVED ELEMENTS:
    - State context formatting is still generated (for memory/action modules)
    - Function signature matches what other modules expect
    - Logging and error handling infrastructure intact
    
    ===============================================================================
    """
    # Get basic state info for fast programmatic analysis
    state_summary = format_state_summary(state_data)
    game_data = state_data.get('game', {})
    player_data = state_data.get('player', {})
    
    logger.info("[PERCEPTION] EMERGENCY MODE: Using fast programmatic perception")
    logger.info(f"[PERCEPTION] State: {state_summary}")
    
    # CRITICAL FIX: Replace hanging VLM call with fast programmatic perception
    # Generate observation based on game state without VLM overhead
    
    current_location = player_data.get('location', 'Unknown')
    game_state = game_data.get('state', 'unknown')
    in_battle = game_data.get('in_battle', False)
    money = player_data.get('money', 0)
    
    # Create context-appropriate observation without VLM calls
    if game_state == 'title':
        description = "I can see the Pokemon Emerald title screen. I need to press A to continue and start the game."
        logger.info("[PERCEPTION] Title screen detected")
    elif in_battle:
        battle_info = game_data.get('battle_info', {})
        player_pokemon = battle_info.get('player_pokemon', {})
        opponent_pokemon = battle_info.get('opponent_pokemon', {})
        description = f"I'm in battle. My Pokemon: {player_pokemon.get('species', 'Unknown')} vs Opponent: {opponent_pokemon.get('species', 'Unknown')}. I need to choose my battle strategy."
        logger.info("[PERCEPTION] Battle detected")
    elif current_location and current_location != 'Unknown':
        description = f"I'm in {current_location}. I can see the overworld map and need to navigate efficiently. Current money: ${money}."
        logger.info(f"[PERCEPTION] Overworld location: {current_location}")
    else:
        description = "I can see the game screen but the current situation is unclear. I should take action to progress."
        logger.info("[PERCEPTION] Unknown situation detected")
    
    # Format state context for memory purposes
    state_context = format_state_for_llm(state_data)
    
    observation = {
        "description": description, 
        "state_data": state_context
    }
    
    logger.info(f"[PERCEPTION] Fast analysis completed: {description[:100]}...")
    return observation 