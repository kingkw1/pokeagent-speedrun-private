"""
Goal Parser - Extract actionable navigation targets from strategic plans

This module parses high-level strategic plans (from planning.py) and converts them
into concrete pathfinding goals that can be executed by the A* pathfinding system.

Philosophy:
- NO hardcoded location checks like "if LITTLEROOT then go NORTH"
- Extract goals dynamically from the planning module's output
- Support flexible goal types: coordinates, NPCs, locations, milestones
- Convert natural language objectives into pathfinding targets

Example:
    Plan: "Navigate to Oldale Town to the north"
    → Goal: {"type": "location", "target": "OLDALE_TOWN", "direction_hint": "north"}
    
    Plan: "Find and talk to May at (15, 20) in Littleroot Town"
    → Goal: {"type": "npc", "target_coords": (15, 20), "npc_name": "May"}
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class GoalParser:
    """Parse strategic plans and extract concrete navigation goals"""
    
    # Location name patterns (Emerald-specific but extensible)
    LOCATION_PATTERNS = {
        'LITTLEROOT_TOWN': r'littleroot\s+town',
        'OLDALE_TOWN': r'oldale\s+town',
        'PETALBURG_CITY': r'petalburg\s+city',
        'ROUTE_101': r'route\s*101',
        'ROUTE_102': r'route\s*102',
        'ROUTE_103': r'route\s*103',
        'PROFESSOR_BIRCHS_LAB': r'(?:professor\s+)?birch(?:\'s|\s+)?lab',
    }
    
    # Direction patterns
    DIRECTION_PATTERNS = {
        'north': r'\b(?:north|up|upward|northward)\b',
        'south': r'\b(?:south|down|downward|southward)\b',
        'east': r'\b(?:east|right|eastward)\b',
        'west': r'\b(?:west|left|westward)\b',
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_goal_from_plan(self, plan: str, current_location: str, 
                               current_objective: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """
        Extract a concrete pathfinding goal from the strategic plan.
        
        Args:
            plan: Strategic plan string (e.g., "OBJECTIVE: Travel to Route 101...")
            current_location: Current player location
            current_objective: Current objective from objective_manager (optional)
            
        Returns:
            Goal dict with structure:
            {
                "type": "location" | "coordinates" | "npc" | "edge",
                "target": target location name or coordinate tuple,
                "direction_hint": "north" | "south" | "east" | "west" (optional),
                "npc_name": NPC name (if type == "npc"),
                "confidence": 0.0-1.0 confidence score
            }
            Returns None if no clear goal can be extracted.
        """
        if not plan:
            return None
        
        plan_lower = plan.lower()
        
        # Priority 1: Extract coordinate-based goals (most specific)
        coord_goal = self._extract_coordinate_goal(plan_lower)
        if coord_goal:
            logger.info(f"[GOAL PARSER] Extracted coordinate goal: {coord_goal}")
            return coord_goal
        
        # Priority 2: Extract NPC-based goals
        npc_goal = self._extract_npc_goal(plan_lower)
        if npc_goal:
            logger.info(f"[GOAL PARSER] Extracted NPC goal: {npc_goal}")
            return npc_goal
        
        # Priority 3: Extract location-based goals
        location_goal = self._extract_location_goal(plan_lower, current_location)
        if location_goal:
            logger.info(f"[GOAL PARSER] Extracted location goal: {location_goal}")
            return location_goal
        
        # Priority 4: Extract directional goals (least specific)
        direction_goal = self._extract_direction_goal(plan_lower)
        if direction_goal:
            logger.info(f"[GOAL PARSER] Extracted direction goal: {direction_goal}")
            return direction_goal
        
        # Priority 5: Use objective if available
        if current_objective:
            objective_goal = self._extract_objective_goal(current_objective, current_location)
            if objective_goal:
                logger.info(f"[GOAL PARSER] Extracted goal from objective: {objective_goal}")
                return objective_goal
        
        logger.debug(f"[GOAL PARSER] No clear goal extracted from plan: {plan[:100]}...")
        return None
    
    def _extract_coordinate_goal(self, plan: str) -> Optional[Dict[str, Any]]:
        """Extract coordinate-based goals like 'go to (15, 20)'"""
        # Pattern: (x, y) coordinates
        coord_pattern = r'\((\d+),\s*(\d+)\)'
        match = re.search(coord_pattern, plan)
        
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            
            # Look for NPC name nearby
            npc_name = None
            npc_pattern = r'(?:find|talk to|interact with)\s+(\w+)'
            npc_match = re.search(npc_pattern, plan)
            if npc_match:
                npc_name = npc_match.group(1)
            
            return {
                "type": "coordinates",
                "target": (x, y),
                "npc_name": npc_name,
                "confidence": 0.95  # High confidence for explicit coordinates
            }
        
        return None
    
    def _extract_npc_goal(self, plan: str) -> Optional[Dict[str, Any]]:
        """Extract NPC interaction goals like 'talk to Professor Birch'"""
        # Known NPCs in early game
        npc_patterns = {
            'PROFESSOR_BIRCH': r'(?:talk to|speak with|find|battle)\s+(?:professor\s+)?birch(?!\s*\'?s\s+lab)',  # Don't match "Birch's Lab"
            'MAY': r'(?:talk to|speak with|find|battle)\s+may\b',
            'BRENDAN': r'(?:talk to|speak with|find|battle)\s+brendan\b',
            'MOM': r'(?:talk to|speak with)\s+(?:mom|mother)\b',
            'DAD': r'(?:talk to|speak with)\s+(?:dad|father)\b',
            'RIVAL': r'(?:talk to|speak with|find|battle)\s+(?:the\s+)?rival\b',
        }
        
        for npc_id, pattern in npc_patterns.items():
            if re.search(pattern, plan, re.IGNORECASE):
                return {
                    "type": "npc",
                    "target": npc_id,
                    "npc_name": npc_id.replace('_', ' ').title(),
                    "confidence": 0.85
                }
        
        return None
    
    def _extract_location_goal(self, plan: str, current_location: str) -> Optional[Dict[str, Any]]:
        """Extract location-based goals like 'go to Route 101'"""
        for location_id, pattern in self.LOCATION_PATTERNS.items():
            match = re.search(pattern, plan, re.IGNORECASE)
            if match:
                # Don't set goal to current location (we're already here!)
                if current_location and location_id in current_location.upper().replace(' ', '_'):
                    logger.debug(f"[GOAL PARSER] Skipping goal {location_id} - already at current location")
                    continue
                
                # Extract direction hint if present
                direction_hint = None
                for direction, dir_pattern in self.DIRECTION_PATTERNS.items():
                    if re.search(dir_pattern, plan):
                        direction_hint = direction
                        break
                
                return {
                    "type": "location",
                    "target": location_id,
                    "direction_hint": direction_hint,
                    "confidence": 0.8
                }
        
        return None
    
    def _extract_direction_goal(self, plan: str) -> Optional[Dict[str, Any]]:
        """Extract pure directional goals like 'head north'"""
        for direction, pattern in self.DIRECTION_PATTERNS.items():
            if re.search(pattern, plan):
                return {
                    "type": "edge",
                    "target": f"{direction.upper()}_EDGE",
                    "direction_hint": direction,
                    "confidence": 0.6  # Lower confidence - very vague
                }
        
        return None
    
    def _extract_objective_goal(self, objective: Any, current_location: str) -> Optional[Dict[str, Any]]:
        """Extract goal from ObjectiveManager objective"""
        if not objective:
            return None
        
        # Get objective attributes
        obj_type = getattr(objective, 'objective_type', None)
        target_value = getattr(objective, 'target_value', None)
        description = getattr(objective, 'description', '')
        
        if obj_type == 'location' and target_value:
            # Location objective - convert to location goal
            target_normalized = target_value.upper().replace(' ', '_')
            
            # Skip if already at location
            if current_location and target_normalized in current_location.upper().replace(' ', '_'):
                return None
            
            return {
                "type": "location",
                "target": target_normalized,
                "confidence": 0.75
            }
        
        elif obj_type == 'pokemon' and 'starter' in description.lower():
            # Starter objective - likely need to go to Birch's lab
            return {
                "type": "location",
                "target": "PROFESSOR_BIRCHS_LAB",
                "confidence": 0.7
            }
        
        elif obj_type == 'battle' and 'rival' in description.lower():
            # Rival battle - likely Route 103
            return {
                "type": "location",
                "target": "ROUTE_103",
                "confidence": 0.7
            }
        
        return None


# Singleton instance
_goal_parser_instance = None

def get_goal_parser() -> GoalParser:
    """Get or create the global GoalParser instance"""
    global _goal_parser_instance
    if _goal_parser_instance is None:
        _goal_parser_instance = GoalParser()
    return _goal_parser_instance
