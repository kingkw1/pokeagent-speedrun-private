"""
Objective Management Module

Lightweight objective management system extracted from SimpleAgent for use in the four-module architecture.
This module provides milestone-driven strategic planning without the complex state management overhead.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class Objective:
    """Single objective/goal for the agent"""
    id: str
    description: str
    objective_type: str  # "location", "battle", "item", "dialogue", "custom", "system", "pokemon"
    target_value: Optional[Any] = None  # Specific target (coords, trainer name, item name, etc.)
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    progress_notes: str = ""
    storyline: bool = False  # True for main storyline objectives (auto-verified), False for agent sub-objectives
    milestone_id: Optional[str] = None  # Emulator milestone ID for storyline objectives


class ObjectiveManager:
    """
    Lightweight objective management for strategic planning integration.
    
    Extracted from SimpleAgent to provide milestone-driven strategic planning
    without complex state management dependencies.
    """
    
    def __init__(self):
        """Initialize with core storyline objectives"""
        self.objectives: List[Objective] = []
        self._initialize_storyline_objectives()
        
        # Track persistent state for events that shouldn't repeat
        self.rival_battle_completed = False  # Once true, stays true (battle done)
        self._was_in_rival_battle = False  # Track if we were in battle (to detect completion)
        
        logger.info(f"ObjectiveManager initialized with {len(self.objectives)} storyline objectives")
    
    def _initialize_storyline_objectives(self):
        """Initialize the main storyline objectives for Pokémon Emerald progression"""
        storyline_objectives = [
            {
                "id": "story_game_start",
                "description": "Complete title sequence and begin the game",
                "objective_type": "system",
                "target_value": "Game Running",
                "milestone_id": "GAME_RUNNING"
            },
            {
                "id": "story_littleroot_town",
                "description": "Arrive in Littleroot Town and explore the area",
                "objective_type": "location", 
                "target_value": "Littleroot Town",
                "milestone_id": "LITTLEROOT_TOWN"
            },
            {
                "id": "story_route_101",
                "description": "Travel north to Route 101 to find Professor Birch",
                "objective_type": "location",
                "target_value": "Route 101", 
                "milestone_id": "ROUTE_101"
            },
            {
                "id": "story_starter_chosen",
                "description": "Choose starter Pokémon and receive first party member",
                "objective_type": "pokemon",
                "target_value": "Starter Pokémon",
                "milestone_id": "STARTER_CHOSEN"
            },
            {
                "id": "story_oldale_town",
                "description": "Continue journey to Oldale Town",
                "objective_type": "location",
                "target_value": "Oldale Town",
                "milestone_id": "OLDALE_TOWN"
            },
            {
                "id": "story_route_103",
                "description": "Head to Route 103 for rival battle",
                "objective_type": "location",
                "target_value": "Route 103",
                "milestone_id": "ROUTE_103"
            },
            {
                "id": "story_rival_battle_1",
                "description": "Battle rival trainer for the first time",
                "objective_type": "battle",
                "target_value": "Rival Battle 1",
                "milestone_id": "FIRST_RIVAL_BATTLE"
            },
            {
                "id": "story_return_littleroot",
                "description": "Return to Littleroot Town after rival battle",
                "objective_type": "location",
                "target_value": "Littleroot Town Return",
                "milestone_id": "LITTLEROOT_RETURN"
            },
            {
                "id": "story_route_102",
                "description": "Travel west to Route 102 toward Petalburg City",
                "objective_type": "location",
                "target_value": "Route 102",
                "milestone_id": "ROUTE_102"
            },
            {
                "id": "story_petalburg_city",
                "description": "Arrive at Petalburg City and meet Norman",
                "objective_type": "location",
                "target_value": "Petalburg City",
                "milestone_id": "PETALBURG_CITY"
            },
            {
                "id": "story_petalburg_gym_visit",
                "description": "Visit Petalburg Gym and meet Norman (Dad)",
                "objective_type": "dialogue",
                "target_value": "Norman Meeting",
                "milestone_id": "MET_NORMAN"
            },
            {
                "id": "story_route_104_south",
                "description": "Travel north to Route 104 (southern section)",
                "objective_type": "location",
                "target_value": "Route 104 South",
                "milestone_id": "ROUTE_104_SOUTH"
            },
            {
                "id": "story_petalburg_woods",
                "description": "Navigate through Petalburg Woods",
                "objective_type": "location",
                "target_value": "Petalburg Woods",
                "milestone_id": "PETALBURG_WOODS"
            },
            {
                "id": "story_route_104_north",
                "description": "Reach northern section of Route 104",
                "objective_type": "location",
                "target_value": "Route 104 North",
                "milestone_id": "ROUTE_104_NORTH"
            },
            {
                "id": "story_rustboro_city",
                "description": "Arrive at Rustboro City",
                "objective_type": "location",
                "target_value": "Rustboro City",
                "milestone_id": "RUSTBORO_CITY"
            },
            {
                "id": "story_gym_1_roxanne",
                "description": "Challenge and defeat Roxanne at Rustboro Gym",
                "objective_type": "battle",
                "target_value": "Gym Leader Roxanne",
                "milestone_id": "DEFEATED_ROXANNE"
            }
        ]
        
        # Convert to Objective instances
        for obj_data in storyline_objectives:
            objective = Objective(
                id=obj_data["id"],
                description=obj_data["description"],
                objective_type=obj_data["objective_type"],
                target_value=obj_data["target_value"],
                storyline=True,  # All these are storyline objectives
                milestone_id=obj_data["milestone_id"]
            )
            self.objectives.append(objective)
    
    def get_active_objectives(self) -> List[Objective]:
        """Get list of uncompleted objectives"""
        return [obj for obj in self.objectives if not obj.completed]
    
    def get_completed_objectives(self) -> List[Objective]:
        """Get list of completed objectives"""
        return [obj for obj in self.objectives if obj.completed]
    
    def check_storyline_milestones(self, state_data: Dict[str, Any]) -> List[str]:
        """Check emulator milestones and auto-complete corresponding storyline objectives"""
        completed_ids = []
        
        # Get milestones from the game state (if available)
        milestones = state_data.get("milestones", {})
        
        if not milestones:
            # No milestone data available, skip checking
            logger.debug("No milestone data available in state_data")
            logger.debug(f"State data keys: {list(state_data.keys())}")
            return completed_ids
        
        logger.debug(f"Checking {len(milestones)} milestones: {list(milestones.keys())}")
            
        for obj in self.get_active_objectives():
            # Only check storyline objectives with milestone IDs
            if obj.storyline and obj.milestone_id and not obj.completed:
                # Check if the corresponding emulator milestone is completed
                milestone_data = milestones.get(obj.milestone_id, {})
                milestone_completed = milestone_data.get("completed", False) if isinstance(milestone_data, dict) else False
                
                logger.debug(f"Objective '{obj.id}' checking milestone '{obj.milestone_id}': {milestone_data}")
                
                if milestone_completed:
                    # Auto-complete the storyline objective
                    obj.completed = True
                    obj.completed_at = datetime.now()
                    obj.progress_notes = f"Auto-completed by emulator milestone: {obj.milestone_id}"
                    completed_ids.append(obj.id)
                    logger.info(f"✅ Auto-completed storyline objective via milestone {obj.milestone_id}: {obj.description}")
        
        return completed_ids
    
    def get_current_strategic_objective(self, state_data: Dict[str, Any]) -> Optional[Objective]:
        """Get the current strategic objective based on milestones and game state"""
        # First, update objectives based on milestones
        self.check_storyline_milestones(state_data)
        
        # Get the first uncompleted objective (they are in story order)
        active_objectives = self.get_active_objectives()
        if active_objectives:
            return active_objectives[0]
        
        # No objectives remaining
        return None
    
    def get_strategic_plan_description(self, state_data: Dict[str, Any]) -> Optional[str]:
        """Generate a strategic plan description for the current state"""
        current_objective = self.get_current_strategic_objective(state_data)
        
        if current_objective:
            # Add tactical context based on objective type
            base_description = current_objective.description
            
            # Add context based on objective type
            if current_objective.objective_type == "location":
                return f"STRATEGIC GOAL: {base_description}. Navigate carefully and interact with NPCs for guidance."
            elif current_objective.objective_type == "battle":
                return f"STRATEGIC GOAL: {base_description}. Prepare for battle - heal Pokemon if needed first."
            elif current_objective.objective_type == "dialogue":
                return f"STRATEGIC GOAL: {base_description}. Look for the right NPC to interact with."
            elif current_objective.objective_type == "pokemon":
                return f"STRATEGIC GOAL: {base_description}. Follow story progression to obtain Pokemon."
            elif current_objective.objective_type == "system":
                return f"STRATEGIC GOAL: {base_description}. Complete basic game setup."
            else:
                return f"STRATEGIC GOAL: {base_description}"
        
        return None
    
    def get_next_action_directive(self, state_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get specific action directive based on current milestone state.
        Returns a dict with action type and target details, or None if no specific directive.
        
        This is the "Quick Win" implementation that provides detailed sub-goals
        without requiring a full script refactor.
        
        Returns:
            {
                'action': 'NAVIGATE_AND_INTERACT',  # or 'NAVIGATE', 'BATTLE', etc.
                'target': (x, y, 'MAP_NAME'),       # Coordinate target
                'description': 'Walk to rival and press A',  # Human-readable
                'milestone': 'FIRST_RIVAL_BATTLE'   # Expected milestone after completion
            }
        """
        logger.info(f"🔍 [OBJECTIVE_MANAGER DEBUG] get_next_action_directive() CALLED")
        print(f"🔍 [OBJECTIVE_MANAGER] get_next_action_directive() CALLED")
        
        # First update objectives based on milestones
        self.check_storyline_milestones(state_data)
        
        # Get current position
        player_data = state_data.get('player', {})
        position = player_data.get('position', {})
        current_x = position.get('x', 0)
        current_y = position.get('y', 0)
        current_location = player_data.get('location', '').upper()
        
        # Get milestone states
        milestones = state_data.get('milestones', {})
        
        # Helper to check if milestone is complete
        def is_milestone_complete(milestone_id: str) -> bool:
            milestone_data = milestones.get(milestone_id, {})
            return milestone_data.get('completed', False) if isinstance(milestone_data, dict) else False
        
        # Helper to check if dialogue is active (prevents navigation during dialogue)
        def is_dialogue_active() -> bool:
            """Check if dialogue is currently active"""
            screen_context = state_data.get('screen_context', '')
            text_box_visible = state_data.get('visual_dialogue_active', False)
            
            # Check both screen_context and text_box visibility
            is_active = (screen_context == 'dialogue' or text_box_visible)
            
            if is_active:
                logger.info(f"🔍 [DIALOGUE CHECK] Dialogue active - screen_context={screen_context}, text_box={text_box_visible}")
                print(f"💬 [DIALOGUE] Active - waiting for dialogue to finish")
            
            return is_active
        
        # === ROUTE 103: RIVAL BATTLE SEQUENCE ===
        # The ROUTE_103 milestone completes when entering Route 103, not after battle
        # We use FIRST_RIVAL_BATTLE milestone to track actual battle completion
        # BUT: The milestone system doesn't auto-set FIRST_RIVAL_BATTLE, so we need manual detection
        
        # Detect battle completion using state transition: was in battle → now not in battle at rival position
        at_rival_position = (current_x == 9 and current_y == 3 and 'ROUTE 103' in current_location)
        in_battle = state_data.get('in_battle', False)
        
        # Track battle state transitions
        if in_battle and at_rival_position:
            self._was_in_rival_battle = True
        
        # Battle is complete if we were in battle and now we're not (at rival position)
        battle_just_completed = self._was_in_rival_battle and at_rival_position and not in_battle
        
        # Once battle is detected as complete, set persistent flag (stays true even after leaving position)
        if battle_just_completed or is_milestone_complete('FIRST_RIVAL_BATTLE'):
            self.rival_battle_completed = True
            logger.info(f"✅ [RIVAL BATTLE] Battle completion detected! Setting persistent flag.")
        
        rival_battle_complete = self.rival_battle_completed
        
        logger.info(f"🔍 [RIVAL BATTLE CHECK] at_rival_pos={at_rival_position}, in_battle={in_battle}, was_in_battle={self._was_in_rival_battle}, dialogue={is_dialogue_active()}, complete={rival_battle_complete}")
        print(f"🔍 [RIVAL BATTLE] Position check: at (9,3)={at_rival_position}, battle={in_battle}, dialogue={is_dialogue_active()}, complete={rival_battle_complete}")
        
        if is_milestone_complete('ROUTE_103') and not rival_battle_complete:
            # We're on Route 103, need to interact with rival at (9, 3)
            target_x, target_y, target_map = 9, 3, 'ROUTE 103'
            
            # Check if we're at the target
            if current_x == target_x and current_y == target_y and target_map in current_location:
                logger.info(f"📍 [DIRECTIVE] At rival position, ready to interact")
                return {
                    'action': 'INTERACT',
                    'target': (target_x, target_y, target_map),
                    'description': 'Press A to interact with rival and start battle',
                    'milestone': 'FIRST_RIVAL_BATTLE'
                }
            else:
                logger.info(f"📍 [DIRECTIVE] Navigate to rival at ({target_x}, {target_y})")
                return {
                    'action': 'NAVIGATE_AND_INTERACT',
                    'target': (target_x, target_y, target_map),
                    'description': 'Walk to rival at Route 103 and press A to battle',
                    'milestone': 'FIRST_RIVAL_BATTLE'
                }
        
        # === OLDALE TOWN: POKEMON CENTER HEALING ===
        # After rival battle, navigate to Pokemon Center
        if rival_battle_complete and not is_milestone_complete('HEALED_AFTER_RIVAL'):
            # CRITICAL: Don't navigate while dialogue is active
            if is_dialogue_active():
                logger.info(f"💬 [DIRECTIVE] Dialogue active, pressing A to continue")
                return {
                    'action': 'DIALOGUE',
                    'target': None,
                    'description': 'Press A to advance dialogue',
                    'milestone': None
                }
            
            logger.info(f"📍 [DIRECTIVE] Rival battle complete, need to heal at Pokemon Center")
            
            # First, need to get to Oldale Town if we're still on Route 103
            if 'ROUTE 103' in current_location:
                logger.info(f"📍 [DIRECTIVE] Still on Route 103, navigate south to Oldale Town")
                # Route 103 exit is at the bottom/south - navigate to approximate exit position
                # The exit from Route 103 is around (8, 19) based on the map
                return {
                    'action': 'NAVIGATE_AND_INTERACT',
                    'target': (8, 19, 'ROUTE 103'),
                    'description': 'Leave Route 103 south to return to Oldale Town',
                    'milestone': None
                }
            
            # After rival battle, go to Pokemon Center
            if 'OLDALE TOWN' in current_location and 'POKEMON CENTER' not in current_location:
                # Outside, need to enter Pokemon Center at (6, 16)
                return {
                    'action': 'NAVIGATE_AND_INTERACT',
                    'target': (6, 16, 'OLDALE TOWN'),
                    'description': 'Enter Oldale Pokemon Center to heal',
                    'milestone': None  # No milestone for entering
                }
            elif 'POKEMON CENTER 1F' in current_location:
                # Inside Pokemon Center, interact with Nurse Joy at (7, 3)
                target_x, target_y = 7, 3
                if current_x == target_x and current_y == target_y:
                    return {
                        'action': 'INTERACT',
                        'target': (target_x, target_y, 'OLDALE TOWN POKEMON CENTER 1F'),
                        'description': 'Talk to Nurse Joy to heal Pokemon',
                        'milestone': 'HEALED_AFTER_RIVAL'
                    }
                else:
                    return {
                        'action': 'NAVIGATE_AND_INTERACT',
                        'target': (target_x, target_y, 'OLDALE TOWN POKEMON CENTER 1F'),
                        'description': 'Walk to Nurse Joy and press A',
                        'milestone': 'HEALED_AFTER_RIVAL'
                    }
        
        # === RETURN TO BIRCH LAB ===
        if is_milestone_complete('HEALED_AFTER_RIVAL') and not is_milestone_complete('RECEIVED_POKEDEX'):
            # Need to return to Littleroot Town and talk to Birch
            if 'LITTLEROOT TOWN' in current_location and 'LAB' not in current_location:
                # Navigate to Birch's Lab entrance at (7, 16)
                return {
                    'action': 'NAVIGATE_AND_INTERACT',
                    'target': (7, 16, 'LITTLEROOT TOWN'),
                    'description': 'Enter Birch Lab to receive Pokedex',
                    'milestone': None
                }
            elif 'BIRCHS LAB' in current_location or 'BIRCH LAB' in current_location:
                # Inside lab - dialogue will auto-trigger, just need to be present
                # This milestone completes via dialogue
                return {
                    'action': 'WAIT_FOR_DIALOGUE',
                    'target': None,
                    'description': 'Wait for Birch to give Pokedex (auto-dialogue)',
                    'milestone': 'RECEIVED_POKEDEX'
                }
        
        # === ROUTE 102 TRAINERS ===
        if is_milestone_complete('ROUTE_102') and not is_milestone_complete('ROUTE_102_CLEARED'):
            # Battle trainers on Route 102
            # Trainer positions from gameplay script: (33,15), (25,14), (19,7)
            trainer_positions = [
                (33, 15, 'ROUTE 102', 'Trainer 1'),
                (25, 14, 'ROUTE 102', 'Trainer 2'),
                (19, 7, 'ROUTE 102', 'Trainer 3')
            ]
            
            if 'ROUTE 102' in current_location or 'ROUTE102' in current_location:
                # Check which trainers we've already battled (would need battle tracking)
                # For now, just navigate to first trainer position
                target_x, target_y, target_map, trainer_name = trainer_positions[0]
                return {
                    'action': 'NAVIGATE_TO_BATTLE',
                    'target': (target_x, target_y, target_map),
                    'description': f'Navigate to {trainer_name} for battle',
                    'milestone': None  # Intermediate battles don't have milestones
                }
        
        # No specific directive - return None to let VLM handle it
        logger.debug(f"📍 [DIRECTIVE] No specific directive for current state")
        return None
    
    def get_objectives_summary(self) -> Dict[str, Any]:
        """Get a summary of objectives for debugging/monitoring"""
        active = self.get_active_objectives()
        completed = self.get_completed_objectives()
        
        current_objective = None
        if active:
            current_objective = {
                "id": active[0].id,
                "description": active[0].description,
                "type": active[0].objective_type,
                "milestone_id": active[0].milestone_id
            }
        
        return {
            "current_objective": current_objective,
            "active_count": len(active),
            "completed_count": len(completed),
            "total_count": len(self.objectives),
            "completion_rate": len(completed) / len(self.objectives) if self.objectives else 0
        }