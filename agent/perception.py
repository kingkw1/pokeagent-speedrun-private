import time
import logging
import json
import re
import signal
from utils.vlm import VLM
from utils.state_formatter import format_state_for_llm, format_state_summary
from agent.system_prompt import system_prompt

# Set up module logging
logger = logging.getLogger(__name__)

def perception_step(frame, state_data, vlm):
    """
    Extract structured visual information from the game frame using VLM-based analysis.
    Returns observation dictionary with structured visual data.
    
    ===============================================================================
    � HYBRID APPROACH - STRUCTURED VLM EXTRACTION �
    ===============================================================================
    
    NEW STRATEGY: Image-to-Structure Extraction
    - Ask VLM to extract specific information into structured JSON format
    - Much more focused and efficient than long text descriptions
    - Machine-readable output that downstream modules can easily use
    - Fallback to programmatic analysis if VLM fails
    
    ADVANTAGES:
    - ✅ Efficient: Focused prompts, faster responses
    - ✅ Structured: JSON output, no text parsing needed
    - ✅ Reliable: Built-in fallback to programmatic analysis
    - ✅ Useful: Extracts visual information not available in game state
    
    EXTRACTED INFORMATION:
    - Screen context (overworld, battle, menu, dialogue)
    - On-screen text and dialogue
    - Visible entities (NPCs, items, trainers)
    - Menu states and UI elements
    
    ===============================================================================
    """
    import time
    perception_start = time.time()
    
    # Get basic state info for analysis
    state_summary = format_state_summary(state_data)
    game_data = state_data.get('game', {})
    player_data = state_data.get('player', {})
    
    logger.info("[PERCEPTION] Starting hybrid VLM-based structured extraction")
    logger.info(f"[PERCEPTION] State: {state_summary}")
    
    setup_time = time.time() - perception_start
    
    # Determine if we should use VLM or fallback to programmatic analysis
    current_location = player_data.get('location', 'Unknown')
    game_state = game_data.get('state', 'unknown')
    in_battle = game_data.get('in_battle', False)
    
    # Try VLM-based structured extraction first
    visual_data = None
    
    # Import json and re at module level to avoid scoping issues
    import json
    import re
    import signal
    
    try:
        if frame is not None:
            logger.info("[PERCEPTION] Attempting VLM-based structured extraction...")
            
            # Create focused JSON extraction prompt specifically for Pokemon Emerald
            extraction_prompt = f"""
Look at this Pokemon Emerald game screenshot and describe only what you actually see.

Current game state: {state_summary}

Based on what is visible in the image, fill this JSON with your observations:

{{
    "screen_context": "overworld, battle, menu, dialogue, title, or cutscene",
    "on_screen_text": {{
        "dialogue": "exact text from any dialogue boxes or null",
        "speaker": "character name if shown or null", 
        "menu_title": "exact menu header text or null",
        "button_prompts": ["any button instructions like 'Press A' or empty array"]
    }},
    "visible_entities": ["describe NPCs, Pokemon, or characters you see"],
    "menu_state": "open menu name or closed",
    "visual_elements": {{
        "health_bars_visible": true_or_false,
        "pokemon_sprites_visible": true_or_false,
        "overworld_map_visible": true_or_false,
        "text_box_visible": true_or_false
    }}
}}

IMPORTANT:
- Only describe what you actually see in THIS image
- Don't make up information about battles or Pokemon not shown
- Don't copy text from instructions or system prompts
- If it shows character name selection, use "menu" for screen_context
- If you see a top-down map view, use "overworld"
- If you see dialogue text at bottom, use "dialogue"
- Put null for anything not clearly visible

Return only the JSON with real observations:"""
            
            # Make VLM call with timeout protection
            def timeout_handler(signum, frame):
                raise TimeoutError("VLM call timed out")
            
            # Set up timeout (60 seconds for local model on GPU)
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)  # Increased timeout for local models on GPU
            
            try:
                print(f"🔍 [PERCEPTION] Step - Calling VLM for visual analysis...")
                print(f"🖼️ [PERCEPTION] Frame type: {type(frame)}")
                print(f"📝 [PERCEPTION] Extraction prompt length: {len(extraction_prompt)} chars")
                
                vlm_response = vlm.get_query(frame, system_prompt + extraction_prompt, "PERCEPTION-EXTRACT")
                signal.alarm(0)  # Cancel timeout
                
                print(f"🔍 [PERCEPTION] VLM Raw Response:")
                print(f"=== START VLM RESPONSE ===")
                print(vlm_response)
                print(f"=== END VLM RESPONSE ===")
                
                # Extract JSON from response (handle cases where VLM adds extra text or markdown)
                # First try to find JSON in markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', vlm_response, re.DOTALL)
                if not json_match:
                    # Fallback to finding any JSON-like structure
                    json_match = re.search(r'\{.*\}', vlm_response, re.DOTALL)
                
                if json_match:
                    # Get the JSON text (use group 1 if we matched markdown, otherwise group 0)
                    json_text = json_match.group(1) if json_match.lastindex else json_match.group(0)
                    print(f"🔍 [PERCEPTION] Extracted JSON: {json_text[:200]}...")
                    
                    # Fix Python tuple syntax to JSON array syntax before parsing
                    json_text = re.sub(r'\((\d+),\s*(\d+)\)', r'[\1, \2]', json_text)
                    visual_data = json.loads(json_text)
                    print(f"✅ [PERCEPTION] VLM extraction successful! Screen context: {visual_data.get('screen_context', 'unknown')}")
                    logger.info("[PERCEPTION] VLM extraction successful")
                else:
                    print(f"❌ [PERCEPTION] No JSON found in VLM response!")
                    logger.warning("[PERCEPTION] VLM response not in JSON format, using fallback")
                    
            except (TimeoutError, json.JSONDecodeError, Exception) as e:
                signal.alarm(0)  # Cancel timeout
                print(f"❌ [PERCEPTION] VLM extraction failed: {e}")
                logger.warning(f"[PERCEPTION] VLM extraction failed: {e}, using fallback")
                visual_data = None
                
    except Exception as e:
        logger.warning(f"[PERCEPTION] VLM setup failed: {e}, using fallback")
        visual_data = None
    
    # Fallback to programmatic analysis if VLM failed
    if visual_data is None:
        print(f"🔧 [PERCEPTION] VLM failed - using programmatic fallback")
        logger.info("[PERCEPTION] Using programmatic fallback analysis")
        visual_data = create_programmatic_visual_data(game_state, in_battle, current_location, game_data)
        print(f"🔧 [PERCEPTION] Fallback result: {visual_data.get('screen_context', 'unknown')}")
    else:
        print(f"✅ [PERCEPTION] VLM success - got screen context: {visual_data.get('screen_context', 'unknown')}")
    
    # Create structured observation
    observation = {
        "visual_data": visual_data,
        "state_summary": state_summary,
        "extraction_method": "vlm" if visual_data.get("_source") != "programmatic" else "programmatic",
        # Backwards compatibility for memory logging
        "description": visual_data.get("scene_description", f"Screen: {visual_data.get('screen_context', 'unknown')}")
    }
    
    # Format state context for memory purposes
    state_context = format_state_for_llm(state_data)
    observation["state_data"] = state_context
    
    # Final timing
    total_time = time.time() - perception_start
    
    logger.info(f"[PERCEPTION] Extraction completed via {observation['extraction_method']} method")
    logger.info(f"[PERCEPTION] ⏱️  TOTAL TIME: {total_time:.3f}s (setup: {setup_time:.3f}s)")
    return observation


def create_programmatic_visual_data(game_state, in_battle, current_location, game_data):
    """
    Create structured visual data using programmatic analysis as fallback.
    Returns the same JSON structure as VLM extraction.
    """
    if game_state == 'title':
        return {
            "_source": "programmatic",
            "screen_context": "title",
            "on_screen_text": {
                "dialogue": None,
                "speaker": None,
                "menu_title": "Pokemon Emerald",
                "button_prompts": ["Press A to continue"]
            },
            "visible_entities": [],
            "menu_state": "title_screen",
            "visual_elements": {
                "health_bars_visible": False,
                "pokemon_sprites_visible": False,
                "overworld_map_visible": False,
                "text_box_visible": False
            }
        }
    elif in_battle:
        battle_info = game_data.get('battle_info', {})
        player_pokemon = battle_info.get('player_pokemon', {})
        opponent_pokemon = battle_info.get('opponent_pokemon', {})
        
        return {
            "_source": "programmatic",
            "screen_context": "battle",
            "on_screen_text": {
                "dialogue": None,
                "speaker": None,
                "menu_title": None,
                "button_prompts": []
            },
            "visible_entities": [
                {
                    "type": "player_pokemon",
                    "name": player_pokemon.get('species', 'Unknown'),
                    "position": "bottom_left"
                },
                {
                    "type": "opponent_pokemon", 
                    "name": opponent_pokemon.get('species', 'Unknown'),
                    "position": "top_right"
                }
            ],
            "menu_state": "battle_menu",
            "visual_elements": {
                "health_bars_visible": True,
                "pokemon_sprites_visible": True,
                "overworld_map_visible": False,
                "text_box_visible": False
            }
        }
    elif current_location and current_location != 'Unknown':
        return {
            "_source": "programmatic",
            "screen_context": "overworld",
            "on_screen_text": {
                "dialogue": None,
                "speaker": None,
                "menu_title": None,
                "button_prompts": []
            },
            "visible_entities": [],
            "menu_state": "closed",
            "visual_elements": {
                "health_bars_visible": False,
                "pokemon_sprites_visible": False,
                "overworld_map_visible": True,
                "text_box_visible": False
            }
        }
    else:
        return {
            "_source": "programmatic",
            "screen_context": "unknown",
            "on_screen_text": {
                "dialogue": None,
                "speaker": None,
                "menu_title": None,
                "button_prompts": []
            },
            "visible_entities": [],
            "menu_state": "unknown",
            "visual_elements": {
                "health_bars_visible": False,
                "pokemon_sprites_visible": False,
                "overworld_map_visible": False,
                "text_box_visible": False
            }
        } 