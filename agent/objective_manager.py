"""
Objective Management Module

Lightweight objective management system extracted from SimpleAgent for use in the four-module architecture.
This module provides milestone-driven strategic planning without the complex state management overhead.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from agent.navigation_planner import NavigationPlanner

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
        
        # Track completed sub-goals to prevent repeating actions
        # This replaces individual flags like rival_battle_completed
        self.completed_goals = {
            # Example: 'ROUTE_103_RIVAL_BATTLE': True
        }
        
        # Track previous state for transition detection
        self._previous_state = {
            'in_battle': False,
            'location': None,
        }
        
        # NEW: Initialize NavigationPlanner for comparison testing
        self.navigation_planner = NavigationPlanner()
        self._last_planner_location = None
        self._last_planner_coords = None
        
        logger.info(f"🏗️ [OBJECT LIFECYCLE] ObjectiveManager.__init__() called - created new instance with {len(self.objectives)} storyline objectives")
        print(f"🏗️ [OBJECT LIFECYCLE] ObjectiveManager.__init__() called - NEW INSTANCE CREATED")
        print(f"🗺️ [NAV PLANNER] NavigationPlanner initialized for comparison testing")
    
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
    
    def mark_goal_complete(self, goal_id: str, description: str = ""):
        """
        Mark a sub-goal as complete. This is persistent across calls.
        
        Args:
            goal_id: Unique identifier for the goal (e.g., 'ROUTE_103_RIVAL_BATTLE')
            description: Human-readable description for logging
        """
        if goal_id not in self.completed_goals:
            self.completed_goals[goal_id] = True
            logger.info(f"✅ [GOAL COMPLETE] {goal_id}: {description}")
            print(f"✅ [GOAL COMPLETE] {goal_id}" + (f": {description}" if description else ""))
    
    def is_goal_complete(self, goal_id: str) -> bool:
        """Check if a sub-goal has been completed"""
        return self.completed_goals.get(goal_id, False)
    
    def get_active_objectives(self) -> List[Objective]:
        """Get list of uncompleted objectives"""
        return [obj for obj in self.objectives if not obj.completed]
    
    def get_completed_objectives(self) -> List[Objective]:
        """Get list of completed objectives"""
        return [obj for obj in self.objectives if obj.completed]
    
    def check_storyline_milestones(self, state_data: Dict[str, Any]) -> List[str]:
        """
        Check emulator milestones and auto-complete corresponding storyline objectives.
        Also tracks state transitions for manual goal completion detection.
        """
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
        
        # CRITICAL FIX: Track state transitions for manual goal detection
        # This must happen here because check_storyline_milestones() is called every step
        # via planning → get_current_strategic_objective. get_next_action_directive() is
        # only called when battle_bot releases control, so it misses the transition.
        game_data = state_data.get('game', {})
        in_battle = game_data.get('in_battle', False)
        was_in_battle = self._previous_state.get('in_battle', False)
        
        # DEBUG: Log every state check
        logger.info(f"🔍 [STATE TRACKING] in_battle={in_battle}, was_in_battle={was_in_battle}")
        print(f"🔍 [STATE TRACKING] in_battle={in_battle}, was_in_battle={was_in_battle}")
        
        # Detect rival battle completion: was in battle at rival position → now not in battle
        if was_in_battle and not in_battle:
            player_data = state_data.get('player', {})
            position = player_data.get('position', {})
            current_x = position.get('x', 0)
            current_y = position.get('y', 0)
            current_location = player_data.get('location', '').upper()
            at_rival_position = (current_x == 9 and current_y == 3 and 'ROUTE 103' in current_location)
            
            logger.info(f"🔍 [TRANSITION DETECTED] Battle ended! at_rival_position={at_rival_position}, x={current_x}, y={current_y}, loc={current_location}")
            print(f"🔍 [TRANSITION DETECTED] Battle ended! at_rival_position={at_rival_position}")
            
            if at_rival_position and not self.is_goal_complete('ROUTE_103_RIVAL_BATTLE'):
                self.mark_goal_complete('ROUTE_103_RIVAL_BATTLE', 'Defeated rival May on Route 103')
                logger.info(f"✅ [BATTLE COMPLETION] Detected rival battle completion via state transition")
                print(f"✅ [GOAL COMPLETE] ROUTE_103_RIVAL_BATTLE")
        
        # Update previous state for next iteration
        old_in_battle = self._previous_state.get('in_battle', False)
        self._previous_state['in_battle'] = in_battle
        self._previous_state['location'] = state_data.get('player', {}).get('location', '').upper()
        
        if old_in_battle != in_battle:
            logger.info(f"🔄 [STATE CHANGE] Battle state changed: {old_in_battle} -> {in_battle}")
            print(f"🔄 [STATE CHANGE] Battle state: {old_in_battle} -> {in_battle}")
        
        logger.debug(f"🔍 [STATE UPDATE] Updated _previous_state: in_battle={in_battle}")
        
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
        # CRITICAL FIX: Use the current directive's description if available
        # This ensures the VLM gets the RIGHT goal (e.g., "Walk south to Oldale Town")
        # instead of the outdated milestone goal (e.g., "Battle rival trainer")
        current_directive = self.get_next_action_directive(state_data)
        if current_directive and current_directive.get('description'):
            directive_desc = current_directive['description']
            directive_action = current_directive.get('action', 'UNKNOWN')
            return f"CURRENT GOAL: {directive_desc} (Action: {directive_action})"
        
        # Fallback to milestone-based objective
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
        
        NOW USES NAVIGATIONPLANNER for multi-hop journeys while preserving
        all milestone tracking logic and special cases.
        
        Returns:
            {
                'action': 'NAVIGATE',  # or 'INTERACT', 'DIALOGUE', etc.
                'target': (x, y),      # Coordinate target (from planner)
                'description': 'Navigate to north exit in LITTLEROOT_TOWN',
                'milestone': 'OLDALE_TOWN'  # Expected milestone after completion
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
        
        # === PRIORITY: HANDLE ACTIVE DIALOGUE ===
        # CRITICAL: Always check for dialogue FIRST before any navigation
        # If dialogue is active, we must complete it before doing anything else
        if is_dialogue_active():
            return {
                'action': 'DIALOGUE',
                'target': None,
                'description': 'Press A to advance dialogue',
                'milestone': None
            }
        
        # =====================================================================
        # NEW: USE NAVIGATION PLANNER FOR MULTI-HOP JOURNEYS
        # =====================================================================
        # The planner handles complex navigation automatically while we still
        # control milestone-based objectives and special interactions
        # =====================================================================
        
        # === ROUTE 103: RIVAL BATTLE SEQUENCE (SPECIAL CASE) ===
        # The ROUTE_103 milestone completes when entering Route 103, not after battle
        # We use FIRST_RIVAL_BATTLE milestone to track actual battle completion
        
        # Get current battle state
        at_rival_position = (current_x == 9 and current_y == 3 and 'ROUTE 103' in current_location)
        game_data = state_data.get('game', {})
        in_battle = game_data.get('in_battle', False)
        was_in_battle = self._previous_state.get('in_battle', False)  # For logging only
        
        # Check if battle is complete (either via our detection or milestone)
        rival_battle_complete = self.is_goal_complete('ROUTE_103_RIVAL_BATTLE') or \
                               is_milestone_complete('FIRST_RIVAL_BATTLE')
        
        # logger.info(f"🔍 [RIVAL BATTLE] at (9,3)={at_rival_position}, in_battle={in_battle}, was_in_battle={was_in_battle}, complete={rival_battle_complete}")
        # print(f"🔍 [RIVAL BATTLE] Check: at (9,3)={at_rival_position}, in_battle={in_battle}, was_in_battle={was_in_battle}, complete={rival_battle_complete}")
        
        # === SPECIAL CASE: INSIDE BIRCH LAB ===
        # Wait for dialogue to auto-trigger (bypass planner)
        if 'BIRCHS LAB' in current_location or 'BIRCH LAB' in current_location:
            if rival_battle_complete and not is_milestone_complete('RECEIVED_POKEDEX'):
                return {
                    'action': 'WAIT_FOR_DIALOGUE',
                    'target': None,
                    'description': 'Wait for Birch to give Pokedex (auto-dialogue)',
                    'milestone': 'RECEIVED_POKEDEX'
                }
            elif is_milestone_complete('RECEIVED_POKEDEX') and not is_milestone_complete('ROUTE_102'):
                # Exit lab - door is at (6, 13) inside lab coordinates
                return {
                    'action': 'NAVIGATE',
                    'target': (6, 13, current_location),
                    'description': 'Exit Birch Lab',
                    'milestone': None
                }
        
        # === ROUTE 102 TRAINERS (SPECIAL CASE) ===
        # Navigate to specific trainer positions
        # if is_milestone_complete('ROUTE_102') and not is_milestone_complete('PETALBURG_CITY'):
            # # Battle trainers on Route 102
            # # Trainer positions from gameplay script: (33,15), (25,14), (19,7)
            # trainer_positions = [
            #     (33, 15, 'ROUTE 102', 'Trainer 1'),
            #     (25, 14, 'ROUTE 102', 'Trainer 2'),
            #     (19, 7, 'ROUTE 102', 'Trainer 3')
            # ]
            
            # if 'ROUTE 102' in current_location or 'ROUTE102' in current_location:
            #     # Check which trainers we've already battled (would need battle tracking)
            #     # For now, just navigate to first trainer position
            #     target_x, target_y, target_map, trainer_name = trainer_positions[0]
            #     return {
            #         'goal_coords': (target_x, target_y, target_map),
            #         'should_interact': True,  # Will trigger battle when we reach trainer
            #         'description': f'Navigate to {trainer_name} for battle',
            #         'milestone': None  # Intermediate battles don't have milestones
            #     }
        
        # SPECIAL CASE: On Route 103 but rival battle not complete
        # Logic: if ROUTE_103 complete AND RECEIVED_POKEDEX not complete AND rival battle not complete
        # Navigate to (9,3) which is adjacent to rival at (10,3), then interact facing RIGHT
        # This needs to be checked BEFORE general milestone progression
        if is_milestone_complete('ROUTE_103') and not is_milestone_complete('RECEIVED_POKEDEX'):
            rival_battle_complete = self.is_goal_complete('ROUTE_103_RIVAL_BATTLE') or \
                                   is_milestone_complete('FIRST_RIVAL_BATTLE')
            if not rival_battle_complete:
                logger.info(f"🎯 [RIVAL BATTLE] ROUTE_103 complete, RECEIVED_POKEDEX not complete, rival not battled - navigating to (9,3) to interact with rival at (10,3)")
                print(f"🎯 [RIVAL BATTLE] ROUTE_103 complete, RECEIVED_POKEDEX not complete, rival not battled - navigating to (9,3) to interact with rival at (10,3)")
                
                # Goal is to reach (9,3) and face RIGHT toward rival at (10,3), then press A
                # We provide the NPC's actual position so the navigation code knows which direction to face
                return {
                    'goal_coords': (9, 3, 'ROUTE_103'),
                    'npc_coords': (10, 3),  # Actual rival position for determining facing direction
                    'should_interact': True,
                    'description': 'Navigate to (9,3) and face RIGHT to interact with rival at (10,3)'
                }
        
        # =====================================================================
        # USE NAVIGATION PLANNER FOR ALL OTHER NAVIGATION
        # =====================================================================
        # Determine the target location based on milestone progression
        # Then let the planner handle the multi-hop journey automatically
        # =====================================================================
        
        target_location = None
        target_coords = None
        expected_milestone = None
        journey_reason = None
        
        # MILESTONE PROGRESSION LOGIC (same as before, just extracted)
        if is_milestone_complete('STARTER_CHOSEN') and not is_milestone_complete('OLDALE_TOWN'):
            target_location = 'OLDALE_TOWN'
            expected_milestone = 'OLDALE_TOWN'
            journey_reason = "After getting starter, travel to Oldale Town"
            
        elif is_milestone_complete('OLDALE_TOWN') and not is_milestone_complete('ROUTE_103'):
            target_location = 'ROUTE_103'
            target_coords = (9, 3)  # Rival position
            expected_milestone = 'ROUTE_103'
            journey_reason = "Navigate to Route 103 to battle rival May"
            
        elif rival_battle_complete and not is_milestone_complete('RECEIVED_POKEDEX'):
            target_location = 'PROFESSOR_BIRCHS_LAB'  # Note: BIRCHS with S to match location_graph
            expected_milestone = 'RECEIVED_POKEDEX'
            journey_reason = "Return to Birch Lab to receive Pokedex"
            
        elif is_milestone_complete('RECEIVED_POKEDEX') and not is_milestone_complete('ROUTE_102'):
            target_location = 'ROUTE_102'
            expected_milestone = 'ROUTE_102'
            journey_reason = "Head to Route 102 to continue adventure"
            
        elif is_milestone_complete('ROUTE_102') and not is_milestone_complete('PETALBURG_CITY'):
            target_location = 'PETALBURG_CITY'
            expected_milestone = 'PETALBURG_CITY'
            journey_reason = "Navigate west through Route 102 to Petalburg City"
        
        # If we have a target, use the navigation planner
        if target_location:
            # Get directive from navigation planner
            planner_directive = self._get_navigation_planner_directive(state_data)
            
            if planner_directive and not planner_directive.get('error'):
                # Planner successfully provided a directive
                # Add milestone info and return it
                planner_directive['milestone'] = expected_milestone
                planner_directive['journey_reason'] = journey_reason
                
                logger.info(f"🗺️ [PLANNER] Using NavigationPlanner directive: {planner_directive.get('description')}")
                print(f"🗺️ [PLANNER] Directive: {planner_directive.get('description')}")
                
                return planner_directive
            else:
                # Planner failed - log error but don't crash
                error_msg = planner_directive.get('description', 'Unknown error') if planner_directive else 'Planner returned None'
                logger.warning(f"⚠️ [PLANNER] Failed to get directive: {error_msg}")
                print(f"⚠️ [PLANNER] Failed: {error_msg}")
                # Fall through to return None (VLM will handle it)
        
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
    
    def _get_navigation_planner_directive(self, state_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get directive from NavigationPlanner for comparison testing.
        This runs in parallel with the existing navigation logic.
        """
        # Get current position
        player_data = state_data.get('player', {})
        position = player_data.get('position', {})
        current_x = position.get('x', 0)
        current_y = position.get('y', 0)
        current_location = player_data.get('location', '').upper()
        
        # Convert location name to graph format
        location_mapping = {
            'LITTLEROOT TOWN': 'LITTLEROOT_TOWN',
            'ROUTE 101': 'ROUTE_101',
            'OLDALE TOWN': 'OLDALE_TOWN',
            'ROUTE 103': 'ROUTE_103',
            'ROUTE 102': 'ROUTE_102',
            'PETALBURG CITY': 'PETALBURG_CITY',
            'ROUTE 104': 'ROUTE_104_SOUTH',  # May need to distinguish north/south
            'PETALBURG WOODS': 'PETALBURG_WOODS',
            'RUSTBORO CITY': 'RUSTBORO_CITY',
            'BIRCHS LAB': 'PROFESSOR_BIRCHS_LAB',  # Note: BIRCHS with S to match location_graph
            'BIRCH LAB': 'PROFESSOR_BIRCHS_LAB',
        }
        
        # Find matching location
        graph_location = None
        for loc_key, loc_value in location_mapping.items():
            if loc_key in current_location:
                graph_location = loc_value
                break
        
        if not graph_location:
            # Unknown location - can't use planner
            return {
                'action': 'UNKNOWN_LOCATION',
                'description': f'Location "{current_location}" not in navigation graph',
                'error': True
            }
        
        # Detect if we changed location (planner might auto-advance)
        location_changed = (graph_location != self._last_planner_location)
        coords_changed = ((current_x, current_y) != self._last_planner_coords)
        
        self._last_planner_location = graph_location
        self._last_planner_coords = (current_x, current_y)
        
        # Get milestones for determining target
        milestones = state_data.get('milestones', {})
        
        def is_milestone_complete(milestone_id: str) -> bool:
            milestone_data = milestones.get(milestone_id, {})
            return milestone_data.get('completed', False) if isinstance(milestone_data, dict) else False
        
        # Determine target based on current milestone state (same logic as existing directive)
        target_location = None
        target_coords = None
        journey_reason = None
        
        # STARTER_CHOSEN → OLDALE_TOWN
        if is_milestone_complete('STARTER_CHOSEN') and not is_milestone_complete('OLDALE_TOWN'):
            target_location = 'OLDALE_TOWN'
            journey_reason = "After getting starter, head to Oldale Town"
        
        # OLDALE_TOWN → ROUTE_103 (rival battle)
        elif is_milestone_complete('OLDALE_TOWN') and not is_milestone_complete('ROUTE_103'):
            target_location = 'ROUTE_103'
            target_coords = (9, 3)  # Rival position
            journey_reason = "Head to Route 103 to battle rival May"
    
        # ON ROUTE_103 → Navigate to rival if battle not complete, else return to lab
        elif 'ROUTE 103' in current_location:
            logger.info(f"🔍 [ROUTE 103 CHECK] In Route 103 - checking rival battle status")
            print(f"🔍 [ROUTE 103 CHECK] current_location={current_location}, graph_location={graph_location}")
            
            rival_battle_complete = self.is_goal_complete('ROUTE_103_RIVAL_BATTLE') or \
                                   is_milestone_complete('FIRST_RIVAL_BATTLE')
            
            logger.info(f"🔍 [ROUTE 103 CHECK] rival_battle_complete={rival_battle_complete}")
            print(f"🔍 [ROUTE 103 CHECK] rival_battle_complete={rival_battle_complete}")
            
            if not rival_battle_complete:
                # We're on Route 103 but haven't battled rival yet
                target_location = graph_location  # Stay on same location
                target_coords = (10, 3)  # But navigate to rival position
                journey_reason = "Navigate to rival trainer on Route 103"
                
                logger.info(f"🎯 [ROUTE 103] Setting target: location={target_location}, coords={target_coords}")
                print(f"🎯 [ROUTE 103] Setting target: location={target_location}, coords={target_coords}")
            else:
                # Rival battle complete - return to Birch's Lab to get Pokedex
                target_location = 'PROFESSOR_BIRCHS_LAB'  # Note: BIRCHS with S to match location_graph
                journey_reason = "Return to Birch Lab to get Pokedex after defeating rival"
                
                logger.info(f"🎯 [ROUTE 103] Rival defeated - returning to lab")
                print(f"🎯 [ROUTE 103] Rival battle complete - heading back to Birch's Lab")
        
        # ROUTE_103 → Back to Birch Lab (after rival battle)
        elif is_milestone_complete('ROUTE_103') and not is_milestone_complete('RECEIVED_POKEDEX'):
            rival_battle_complete = self.is_goal_complete('ROUTE_103_RIVAL_BATTLE') or \
                                   is_milestone_complete('FIRST_RIVAL_BATTLE')
            if rival_battle_complete:
                target_location = 'PROFESSOR_BIRCHS_LAB'  # Note: BIRCHS with S to match location_graph
                journey_reason = "Return to Birch Lab to get Pokedex"
        
        # RECEIVED_POKEDEX → ROUTE_102
        elif is_milestone_complete('RECEIVED_POKEDEX') and not is_milestone_complete('ROUTE_102'):
            target_location = 'ROUTE_102'
            journey_reason = "Head to Route 102 after receiving Pokedex"
        
        # ROUTE_102 → PETALBURG_CITY
        elif is_milestone_complete('ROUTE_102') and not is_milestone_complete('PETALBURG_CITY'):
            target_location = 'PETALBURG_CITY'
            journey_reason = "Navigate west through Route 102 to Petalburg City"
        
        # DEBUG: Log what target was determined
        logger.info(f"🔍 [TARGET DEBUG] target_location={target_location}, target_coords={target_coords}, graph_location={graph_location}")
        print(f"🔍 [TARGET DEBUG] target_location={target_location}, target_coords={target_coords}, graph_location={graph_location}")
        
        # If we have a target, plan/update journey
        if target_location:
            # Check if target is same location (intra-location navigation to coords)
            if target_location == graph_location and target_coords:
                # Same location - just navigate to coordinates
                # Don't use planner, return simple goal_coords directive
                logger.info(f"🎯 [OBJECTIVE] Intra-location navigation to {target_coords} in {graph_location}")
                print(f"🎯 [OBJECTIVE] Navigating to {target_coords} in current location")
                
                return {
                    'goal_coords': (*target_coords, graph_location),
                    'should_interact': True,  # Interact with rival/NPC
                    'description': journey_reason or f"Navigate to {target_coords}"
                }
            
            # Different location - use planner for multi-hop journey
            elif target_location != graph_location:
                # Check if we need to create a new plan
                if not self.navigation_planner.has_active_plan():
                    success = self.navigation_planner.plan_journey(
                        start_location=graph_location,
                        end_location=target_location,
                        final_coords=target_coords
                    )
                    if success:
                        print(f"\n{'=' * 80}")
                        print(f"🗺️ [NAV PLANNER] NEW JOURNEY PLANNED")
                        print(f"{'=' * 80}")
                        print(f"Reason: {journey_reason}")
                        print(f"Start: {graph_location}")
                        print(f"End: {target_location}")
                        if target_coords:
                            print(f"Final Target: {target_coords}")
                        print(f"Total Stages: {len(self.navigation_planner.stages)}")
                        print(f"{'=' * 80}\n")
                    else:
                        return {
                            'action': 'PLAN_FAILED',
                            'description': f'Failed to plan journey from {graph_location} to {target_location}',
                            'error': True
                        }
                elif self.navigation_planner.journey_end != target_location:
                    # Journey target changed - replan
                    print(f"\n⚠️ [NAV PLANNER] Target changed from {self.navigation_planner.journey_end} to {target_location}")
                    print(f"Replanning journey...\n")
                    self.navigation_planner.clear_plan()
                    return self._get_navigation_planner_directive(state_data)  # Recursive call to replan
        
        # Get current directive from planner
        if self.navigation_planner.has_active_plan():
            # Get the raw planner directive (with action types like NAVIGATE, CROSS_BOUNDARY, etc.)
            planner_directive = self.navigation_planner.get_current_directive(
                graph_location,
                (current_x, current_y)
            )
            
            if not planner_directive:
                return None
            
            # TRANSLATION LAYER: Convert planner's stage-based directives into simple GOAL COORDINATES
            # The planner tells us WHERE to go, action.py decides HOW to get there
            action_type = planner_directive.get('action')
            
            if action_type == 'NAVIGATE_AND_INTERACT':
                # Planner wants us to navigate to target coordinates
                target_coords = planner_directive['target']  # (x, y) tuple
                should_interact = planner_directive.get('should_interact', False)
                location = planner_directive.get('location', graph_location)
                
                # Return simple goal - action.py will use A* to get there
                return {
                    'goal_coords': (*target_coords, location),  # (x, y, 'LOCATION')
                    'should_interact': should_interact,
                    'description': planner_directive.get('description', 'Navigate to coordinates'),
                    'journey_progress': self.navigation_planner.get_progress_summary()
                }
                
            elif action_type == 'NAVIGATE_DIRECTION':
                # Planner wants us to move in a direction (approaching portal)
                direction = planner_directive.get('direction')
                portal_coords = planner_directive.get('portal_coords')  # (x, y)
                
                # Return directional goal - action.py will use frontier-based pathfinding
                return {
                    'goal_direction': direction,
                    'portal_coords': portal_coords,  # Hint for validation
                    'description': planner_directive.get('description', f'Move {direction}'),
                    'journey_progress': self.navigation_planner.get_progress_summary()
                }
                
            elif action_type == 'INTERACT_WARP':
                # Planner wants us to interact with a warp tile
                target_coords = planner_directive['target']
                location = planner_directive.get('location', graph_location)
                
                return {
                    'goal_coords': (*target_coords, location),
                    'should_interact': True,  # Always interact with warps
                    'description': planner_directive.get('description', 'Interact with warp'),
                    'journey_progress': self.navigation_planner.get_progress_summary()
                }
                
            elif action_type == 'COMPLETE':
                # Journey complete
                return {
                    'journey_complete': True,
                    'description': 'Navigation journey complete',
                    'journey_progress': self.navigation_planner.get_progress_summary()
                }
                
            elif action_type == 'CROSS_BOUNDARY':
                # Agent is crossing a portal/boundary between locations
                # Continue moving in the portal direction until location changes
                direction = planner_directive.get('direction', 'north')
                to_location = planner_directive.get('to_location', '')
                
                print(f"🚪 [CROSS_BOUNDARY] Crossing from {planner_directive.get('from_location')} to {to_location}")
                
                return {
                    'goal_direction': direction,
                    'description': planner_directive.get('description', f'Cross boundary {direction} to {to_location}'),
                    'journey_progress': self.navigation_planner.get_progress_summary()
                }
                
            elif action_type == 'WAIT':
                # Wait for warp/transition to complete (e.g., after stepping on warp tile)
                expected_location = planner_directive.get('expected_location', '')
                
                print(f"⏳ [WAIT] Waiting for warp to {expected_location}")
                
                return {
                    'wait_for_transition': True,
                    'expected_location': expected_location,
                    'description': planner_directive.get('description', f'Wait for transition to {expected_location}'),
                    'journey_progress': self.navigation_planner.get_progress_summary()
                }
                
            elif action_type == 'UNKNOWN':
                # Planner doesn't know what to do - let VLM handle
                print(f"❓ [UNKNOWN ACTION] NavigationPlanner returned UNKNOWN action")
                return None
                
            else:
                # Unhandled action type - log warning and return None
                print(f"⚠️ [UNHANDLED ACTION] NavigationPlanner returned unhandled action: {action_type}")
                logger.warning(f"Unhandled NavigationPlanner action type: {action_type}")
                return None
        else:
            # No active plan - agent is at destination or unknown state
            return None
    
    def compare_navigation_systems(self, state_data: Dict[str, Any]):
        """
        Compare old directive system with new NavigationPlanner.
        Prints detailed comparison for analysis.
        """
        print(f"\n{'█' * 80}")
        print(f"{'█' * 80}")
        print(f"🔍 NAVIGATION COMPARISON")
        print(f"{'█' * 80}")
        print(f"{'█' * 80}\n")
        
        # Get current position
        player_data = state_data.get('player', {})
        position = player_data.get('position', {})
        current_x = position.get('x', 0)
        current_y = position.get('y', 0)
        current_location = player_data.get('location', '').upper()
        
        print(f"📍 Current Position: ({current_x}, {current_y}) in {current_location}")
        
        # Get current milestone status
        milestones = state_data.get('milestones', {})
        active_milestones = [k for k, v in milestones.items() if isinstance(v, dict) and v.get('completed', False)]
        print(f"✅ Active Milestones: {', '.join(active_milestones) if active_milestones else 'None'}")
        
        print(f"\n{'-' * 80}")
        print(f"OLD SYSTEM (get_next_action_directive)")
        print(f"{'-' * 80}\n")
        
        old_directive = self.get_next_action_directive(state_data)
        if old_directive:
            print(f"Action: {old_directive.get('action')}")
            print(f"Target: {old_directive.get('target')}")
            print(f"Description: {old_directive.get('description')}")
            print(f"Milestone: {old_directive.get('milestone')}")
            if 'direction' in old_directive:
                print(f"Direction: {old_directive.get('direction')}")
                print(f"Target Location: {old_directive.get('target_location')}")
                print(f"Portal Coords: {old_directive.get('portal_coords')}")
        else:
            print("No directive (None)")
        
        print(f"\n{'-' * 80}")
        print(f"NEW SYSTEM (NavigationPlanner)")
        print(f"{'-' * 80}\n")
        
        new_directive = self._get_navigation_planner_directive(state_data)
        if new_directive:
            is_error = new_directive.get('error', False)
            is_at_dest = new_directive.get('at_destination', False)
            
            if is_error:
                print(f"❌ ERROR: {new_directive.get('description')}")
            elif is_at_dest:
                print(f"🎯 {new_directive.get('description')}")
            else:
                print(f"Action: {new_directive.get('action')}")
                if 'target' in new_directive and new_directive['target']:
                    print(f"Target: {new_directive.get('target')}")
                print(f"Description: {new_directive.get('description')}")
                
                # Show stage progress
                stage_idx = new_directive.get('stage_index', 0)
                total_stages = new_directive.get('total_stages', 0)
                if total_stages > 0:
                    print(f"Progress: Stage {stage_idx + 1}/{total_stages}")
                    
                # Show journey progress
                journey_progress = new_directive.get('journey_progress')
                if journey_progress:
                    print(f"Journey: {journey_progress}")
        else:
            print("No directive (None)")
        
        print(f"\n{'-' * 80}")
        print(f"COMPARISON ANALYSIS")
        print(f"{'-' * 80}\n")
        
        # Compare actions
        old_action = old_directive.get('action') if old_directive else None
        new_action = new_directive.get('action') if new_directive else None
        
        if old_action == new_action:
            print(f"✅ Actions MATCH: Both systems suggest '{old_action}'")
        else:
            print(f"⚠️ Actions DIFFER:")
            print(f"   Old: {old_action}")
            print(f"   New: {new_action}")
        
        # Compare targets
        old_target = old_directive.get('target') if old_directive else None
        new_target = new_directive.get('target') if new_directive else None
        
        if old_target and new_target:
            if old_target == new_target:
                print(f"✅ Targets MATCH: Both point to {old_target}")
            else:
                print(f"⚠️ Targets DIFFER:")
                print(f"   Old: {old_target}")
                print(f"   New: {new_target}")
        elif old_target or new_target:
            print(f"⚠️ One system has target, other doesn't:")
            print(f"   Old: {old_target}")
            print(f"   New: {new_target}")
        
        # Compare descriptions
        old_desc = old_directive.get('description') if old_directive else None
        new_desc = new_directive.get('description') if new_directive else None
        
        if old_desc and new_desc:
            print(f"\n📝 Description Comparison:")
            print(f"   Old: {old_desc}")
            print(f"   New: {new_desc}")
        
        print(f"\n{'█' * 80}")
        print(f"{'█' * 80}\n")