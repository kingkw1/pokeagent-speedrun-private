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
            return completed_ids
            
        for obj in self.get_active_objectives():
            # Only check storyline objectives with milestone IDs
            if obj.storyline and obj.milestone_id and not obj.completed:
                # Check if the corresponding emulator milestone is completed
                milestone_completed = milestones.get(obj.milestone_id, {}).get("completed", False)
                
                if milestone_completed:
                    # Auto-complete the storyline objective
                    obj.completed = True
                    obj.completed_at = datetime.now()
                    obj.progress_notes = f"Auto-completed by emulator milestone: {obj.milestone_id}"
                    completed_ids.append(obj.id)
                    logger.info(f"Auto-completed storyline objective via milestone {obj.milestone_id}: {obj.description}")
        
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