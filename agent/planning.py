import logging
from utils.vlm import VLM
from utils.state_formatter import format_state_for_llm, format_state_summary
from agent.system_prompt import system_prompt
from agent.objective_manager import ObjectiveManager

# Set up module logging
logger = logging.getLogger(__name__)

def planning_step(memory_context, current_plan, slow_thinking_needed, state_data, vlm):
    """
    Decide and update your high-level plan based on memory context, current state, and the need for slow thinking.
    Returns updated plan.
    
    ===============================================================================
    🚨 MAJOR ARCHITECTURAL CHANGE - VLM PLANNING ELIMINATED 🚨  
    ===============================================================================
    
    CRITICAL CHANGE: This function now uses ZERO VLM calls (fully programmatic)
    
    ORIGINAL PROBLEM:
    - Two expensive VLM calls per planning cycle were causing memory crashes
    - "PLANNING-ASSESSMENT" call to check if current plan is complete
    - "PLANNING-CREATION" call to generate new strategic plans
    - Long prompts with comprehensive state data were overwhelming resources
    - Agent would freeze or be killed by OS due to excessive memory usage
    
    EMERGENCY SOLUTION:
    - Replaced all VLM planning with fast programmatic logic
    - Context-aware plan generation based on game state analysis
    - Simple but effective plans tailored to current situation
    
    CURRENT PLANNING LOGIC:
    - Title screen: "Navigate through title screen and character creation..."
    - Battle: "Focus on battle: attack with effective moves, heal if HP low..."
    - Pokemon Center: "Heal Pokemon at the Pokemon Center, then continue..."
    - Unknown location: "Explore current area, interact with NPCs..."
    - Known location: "Navigate [location] efficiently. Talk to NPCs..."
    
    ⚠️  REINTEGRATION STRATEGY FOR INTELLIGENT PLANNING:
    
    OPTION 1 - Keep Programmatic as Base (Recommended):
    - Current logic is actually quite effective for most scenarios
    - Add VLM calls only for complex strategic decisions
    - Use VLM for long-term route planning, not immediate tactical decisions
    - Example: "Should I go to Gym 1 or train more Pokemon first?"
    
    OPTION 2 - Hybrid Planning System:
    - Programmatic planning for immediate actions (current approach)
    - Occasional VLM calls for strategic review (every 10-20 steps)
    - VLM focuses on high-level goals, not step-by-step tactics
    - Implement strict timeouts and fallback to programmatic plans
    
    OPTION 3 - Smart VLM Triggers:
    - Use programmatic logic to detect when VLM planning is actually needed
    - Major story events, new areas, complex puzzles
    - Keep programmatic for routine navigation and battles
    - Much more efficient than calling VLM for every decision
    
    PRESERVED ELEMENTS:
    - Function signature matches caller expectations
    - Proper logging for debugging and monitoring  
    - Plans are contextually appropriate and actionable
    - Integration with memory and action modules intact
    
    ⚡ PERFORMANCE IMPACT:
    - Planning now takes ~1ms instead of ~10-30 seconds
    - Zero memory overhead from VLM processing
    - No API rate limiting or timeout issues
    - Agent can make decisions in real-time
    
    ===============================================================================
    """
    # Get basic state info for programmatic planning
    state_summary = format_state_summary(state_data)
    game_data = state_data.get('game', {})
    player_data = state_data.get('player', {})
    
    logger.info("[PLANNING] Starting enhanced milestone-driven planning step")
    logger.info(f"[PLANNING] State: {state_summary}")
    logger.info(f"[PLANNING] Slow thinking needed: {slow_thinking_needed}")
    
    # ENHANCED STRATEGIC PLANNING: Use ObjectiveManager for milestone-driven strategy
    # Initialize objective manager (persistent across calls)
    if not hasattr(planning_step, 'objective_manager'):
        planning_step.objective_manager = ObjectiveManager()
        logger.info("[PLANNING] Initialized ObjectiveManager for strategic planning")
    
    # Get milestone-driven strategic context
    obj_manager = planning_step.objective_manager
    strategic_plan = obj_manager.get_strategic_plan_description(state_data)
    
    # Get objectives summary for logging
    objectives_summary = obj_manager.get_objectives_summary()
    logger.info(f"[PLANNING] Objectives status: {objectives_summary['completed_count']}/{objectives_summary['total_count']} completed")
    if objectives_summary['current_objective']:
        current_obj = objectives_summary['current_objective']
        logger.info(f"[PLANNING] Current objective: {current_obj['description']} (milestone: {current_obj['milestone_id']})")
    
    # Use strategic plan if available, otherwise fallback to programmatic planning
    if strategic_plan:
        current_plan = strategic_plan
        logger.info(f"[PLANNING] Using strategic milestone-driven plan")
    else:
        # Fallback to existing programmatic planning logic
        current_location = player_data.get('location', 'Unknown')
        game_state = game_data.get('state', 'unknown')
        in_battle = game_data.get('in_battle', False)
    
        # Fallback programmatic planning (existing logic preserved)
        if game_state == 'title':
            current_plan = "Navigate through title screen and character creation to start the game."
            logger.info("[PLANNING] Title screen fallback plan generated")
        elif in_battle:
            current_plan = "Focus on battle: attack with effective moves, heal if HP is low, switch Pokemon if needed."
            logger.info("[PLANNING] Battle fallback plan generated")
        elif 'POKEMON_CENTER' in current_location.upper():
            current_plan = "Heal Pokemon at the Pokemon Center, then continue adventure."
            logger.info("[PLANNING] Pokemon Center fallback plan generated")
        elif current_location == 'Unknown' or not current_location:
            current_plan = "Explore the current area, interact with NPCs, and progress the story."
            logger.info("[PLANNING] Exploration fallback plan generated")
        else:
            # General overworld plan
            current_plan = f"Navigate {current_location} efficiently. Talk to NPCs for story progression, battle trainers for experience, and head toward the next major objective."
            logger.info(f"[PLANNING] Overworld fallback plan generated for {current_location}")
    
    # Add tactical context to any plan (strategic or fallback)
    tactical_context = get_tactical_context(state_data)
    if tactical_context:
        current_plan = f"{current_plan} {tactical_context}"
    
    logger.info(f"[PLANNING] Final enhanced plan: {current_plan}")
    return current_plan


def get_tactical_context(state_data):
    """Generate tactical context based on current game state"""
    game_data = state_data.get('game', {})
    player_data = state_data.get('player', {})
    
    tactical_notes = []
    
    # Battle context
    if game_data.get('in_battle', False):
        battle_info = game_data.get('battle_info', {})
        if battle_info is None:
            battle_info = {}
        player_pokemon = battle_info.get('player_pokemon', {})
        if player_pokemon is None:
            player_pokemon = {}
        if player_pokemon.get('hp_current', 0) < (player_pokemon.get('hp_max', 1) * 0.3):
            tactical_notes.append("URGENT: Pokemon health critical - consider healing or switching.")
    
    # Party health context
    party = game_data.get('party', [])
    # SAFETY CHECK: Ensure party is iterable
    if party is None:
        party = []
    
    healthy_count = sum(1 for p in party if p.get('hp_current', 0) > 0)
    total_count = len(party)
    if total_count > 0 and healthy_count / total_count < 0.5:
        tactical_notes.append("WARNING: Most party Pokemon are fainted - visit Pokemon Center.")
    
    # Money context for purchases
    money = player_data.get('money', 0)
    if money is None:
        money = 0
    if money < 500:
        tactical_notes.append("LOW FUNDS: Consider battling trainers for money.")
    
    return " ".join(tactical_notes) 