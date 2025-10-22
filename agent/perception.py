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
            
            # Get movement options for VLM context
            from utils.state_formatter import get_movement_options
            movement_options = get_movement_options(state_data)
            
            # Format movement options for VLM
            movement_context = ""
            if movement_options:
                movement_context = "\n\nMovement Analysis Context:"
                for direction, description in movement_options.items():
                    movement_context += f"\n- {direction}: {description}"
            
            # Create focused JSON extraction prompt specifically for Pokemon Emerald
            extraction_prompt = f"""
Look at this Pokemon Emerald game screenshot and analyze what you see for navigation purposes.

Current game state: {state_summary}{movement_context}

CRITICAL NAVIGATION ANALYSIS:
You are looking at a Pokemon game screen. The player needs to NAVIGATE effectively.

LOCATION CONTEXT: {state_summary}

1. SCREEN TYPE DETECTION:
   - If you see a top-down view of a character on paths/grass/routes = "overworld"
   - If you see dialogue text at bottom of screen = "dialogue"
   - If you see a battle interface with Pokemon = "battle"

2. FOR OVERWORLD NAVIGATION:
   - LOOK FOR PATHS: Light colored areas where player can walk (roads, paths, clearings)
   - LOOK FOR GRASS: Green areas (may have wild Pokemon)
   - LOOK FOR OBSTACLES: Trees, rocks, water, buildings that block movement
   - LOOK FOR TRANSITIONS: Edges of map where player can move to new areas
   - DESCRIBE EACH DIRECTION: What's visible UP/DOWN/LEFT/RIGHT from player?

3. FOR INDOOR/ROOM NAVIGATION:
   - LOOK FOR EXITS: Dark rectangles at edges = doors/exits
   - LOOK FOR FURNITURE: Tables, beds, computers that block movement
   - IDENTIFY INTERACTABLES: NPCs, computers, items to press A on

Based on what is visible in the image, fill this JSON with your observations:

{{
    "screen_context": "overworld, battle, menu, dialogue, title, or cutscene",
    "on_screen_text": {{
        "dialogue": "ONLY text from dialogue boxes with white/black text boxes at bottom of screen. DO NOT include HUD/status text. If no dialogue box visible, use null",
        "speaker": "character name if shown in dialogue box or null", 
        "menu_title": "exact menu header text or null",
        "button_prompts": ["any button instructions like 'Press A' or empty array"]
    }},
    "visible_entities": ["describe NPCs, Pokemon, or characters you see in the game world - NOT the player's own Pokemon"],
    "navigation_info": {{
        "exits_visible": ["describe visible exits: 'path continues north', 'door to building south', 'route edge east'"],
        "interactable_objects": ["NPCs, trainers, items, computers - things that show dialogue when you press A"],
        "movement_barriers": ["trees', 'rocks', 'water', 'walls', 'furniture' - things blocking movement"],
        "open_paths": ["DESCRIBE what you see in each direction: 'UP: clear grass path', 'DOWN: route continues south', 'LEFT: trees blocking', 'RIGHT: path to town'"]
    }},
    "spatial_layout": {{
        "player_position": "where is the small player character sprite in the scene?",
        "room_type": "indoor room, outdoor route, town, forest, etc.",
        "notable_features": ["paths, roads, exits, doors, town entrances, route connections visible in THIS image"]
    }},
    "menu_state": "open menu name or closed",
    "visual_elements": {{
        "health_bars_visible": true_or_false,
        "pokemon_sprites_visible": true_or_false,
        "overworld_map_visible": true_or_false,
        "text_box_visible": true_or_false
    }}
}}

CRITICAL - DIALOGUE vs HUD:
- Dialogue boxes appear at the BOTTOM of the screen with text from NPCs/story
- The HUD/status overlay (player name, location, position, money, HP) is NOT dialogue
- ONLY extract dialogue if you see an actual dialogue text box
- If you just see the overworld with HUD, set dialogue to null

IMPORTANT:
- Only describe what you actually see in THIS specific image
- Don't make up information about battles or Pokemon not shown
- Don't copy text from instructions or system prompts
- Don't repeat the same response - analyze THIS frame freshly
- If you see a top-down map view with no text box, use "overworld" and dialogue=null

NAVIGATION ANALYSIS GUIDE:
- Look for doorways, stairs, passages leading to other areas
- Identify NPCs, computers, boxes, or other objects you could interact with by pressing A
- Notice walls, furniture, or other obstacles that would block movement
- See which directions have clear floor/grass areas you could walk to
- Use descriptive terms like "door to the south", "stairs leading up", "computer on the left"

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
                    
                    # Try to fix common JSON malformation issues
                    # Add missing closing brace if needed
                    brace_count = json_text.count('{') - json_text.count('}')
                    if brace_count > 0:
                        json_text += '}' * brace_count
                        print(f"🔧 [PERCEPTION] Fixed missing closing braces: added {brace_count}")
                    
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
            "navigation_info": {
                "exits_visible": [],
                "interactable_objects": ["Title screen menu"],
                "movement_barriers": [],
                "open_paths": []
            },
            "spatial_layout": {
                "player_position": "title screen",
                "room_type": "menu",
                "notable_features": ["Title screen interface"]
            },
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
            "navigation_info": {
                "exits_visible": [],
                "interactable_objects": ["Battle menu options"],
                "movement_barriers": [],
                "open_paths": []
            },
            "spatial_layout": {
                "player_position": "battle screen",
                "room_type": "battle",
                "notable_features": ["Pokemon battle interface"]
            },
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
            "navigation_info": {
                "exits_visible": ["Check for exits in all directions"],
                "interactable_objects": ["Look for NPCs, items, or interactive elements"],
                "movement_barriers": ["Unknown - check programmatically"],
                "open_paths": ["Movement depends on traversability data"]
            },
            "spatial_layout": {
                "player_position": f"In {current_location}",
                "room_type": "overworld",
                "notable_features": ["Check for doors, exits, or stairs"]
            },
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
            "navigation_info": {
                "exits_visible": [],
                "interactable_objects": [],
                "movement_barriers": [],
                "open_paths": []
            },
            "spatial_layout": {
                "player_position": "unknown",
                "room_type": "unknown",
                "notable_features": []
            },
            "menu_state": "unknown",
            "visual_elements": {
                "health_bars_visible": False,
                "pokemon_sprites_visible": False,
                "overworld_map_visible": False,
                "text_box_visible": False
            }
        } 