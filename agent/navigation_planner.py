"""
NavigationPlanner - Multi-stage pathfinding and directive generation

This class converts high-level navigation goals into step-by-step executable directives
using the location graph. It handles multi-hop journeys by breaking them into stages
and automatically advancing as the agent progresses.

Example:
    planner = NavigationPlanner()
    planner.plan_journey("LITTLEROOT_TOWN", "ROUTE_103", final_coords=(9, 3))
    
    # Returns sequence of stages:
    # Stage 0: Navigate to exit portal in LITTLEROOT_TOWN
    # Stage 1: Cross boundary to ROUTE_101
    # Stage 2: Navigate to exit portal in ROUTE_101
    # Stage 3: Cross boundary to OLDALE_TOWN
    # Stage 4: Navigate to exit portal in OLDALE_TOWN
    # Stage 5: Cross boundary to ROUTE_103
    # Stage 6: Navigate to final target in ROUTE_103

Usage:
    directive = planner.get_current_directive(current_location, current_coords)
    # Returns: {"action": "NAVIGATE", "target": (10, 0), "location": "LITTLEROOT_TOWN", ...}
"""

from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import logging
from agent.location_graph import (
    find_shortest_path,
    get_portal_info,
    LOCATION_GRAPH
)

logger = logging.getLogger(__name__)


class StageType(Enum):
    """Types of navigation stages"""
    NAVIGATE = "NAVIGATE"  # Move to coordinates within a location
    CROSS_BOUNDARY = "CROSS_BOUNDARY"  # Cross an open_world portal
    INTERACT_WARP = "INTERACT_WARP"  # Interact with a warp tile (door, cave entrance)
    WAIT_FOR_WARP = "WAIT_FOR_WARP"  # Wait for warp to complete
    COMPLETE = "COMPLETE"  # Journey complete


class NavigationStage:
    """Represents a single stage in a multi-stage journey"""
    
    def __init__(
        self,
        stage_type: StageType,
        location: str,
        target_coords: Optional[Tuple[int, int]] = None,
        expected_next_location: Optional[str] = None,
        portal_info: Optional[Dict[str, Any]] = None,
        description: str = ""
    ):
        self.stage_type = stage_type
        self.location = location
        self.target_coords = target_coords
        self.expected_next_location = expected_next_location
        self.portal_info = portal_info or {}
        self.description = description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging"""
        return {
            "stage_type": self.stage_type.value,
            "location": self.location,
            "target_coords": self.target_coords,
            "expected_next_location": self.expected_next_location,
            "portal_info": self.portal_info,
            "description": self.description
        }
    
    def __repr__(self):
        if self.stage_type == StageType.NAVIGATE:
            return f"NAVIGATE to {self.target_coords} in {self.location}"
        elif self.stage_type == StageType.CROSS_BOUNDARY:
            return f"CROSS_BOUNDARY from {self.location} to {self.expected_next_location}"
        elif self.stage_type == StageType.INTERACT_WARP:
            return f"INTERACT_WARP at {self.target_coords} in {self.location}"
        elif self.stage_type == StageType.WAIT_FOR_WARP:
            return f"WAIT_FOR_WARP to {self.expected_next_location}"
        elif self.stage_type == StageType.COMPLETE:
            return f"COMPLETE at {self.target_coords} in {self.location}"
        return f"{self.stage_type.value} in {self.location}"


class NavigationPlanner:
    """
    Manages multi-stage navigation plans and provides one directive at a time.
    
    The planner maintains the full journey plan but only exposes the current stage
    to the agent, advancing automatically as stages complete.
    """
    
    def __init__(self):
        self.stages: List[NavigationStage] = []
        self.current_stage_index: int = 0
        self.journey_start: Optional[str] = None
        self.journey_end: Optional[str] = None
        self.final_coords: Optional[Tuple[int, int]] = None
    
    def has_active_plan(self) -> bool:
        """Check if there's an active navigation plan"""
        return len(self.stages) > 0 and self.current_stage_index < len(self.stages)
    
    def clear_plan(self):
        """Clear the current navigation plan"""
        self.stages = []
        self.current_stage_index = 0
        self.journey_start = None
        self.journey_end = None
        self.final_coords = None
        logger.info("🗑️ Navigation plan cleared")
    
    def plan_journey(
        self,
        start_location: str,
        end_location: str,
        final_coords: Optional[Tuple[int, int]] = None,
        start_coords: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        Plan a multi-stage journey from start to end location.
        
        Args:
            start_location: Starting location name (e.g., "LITTLEROOT_TOWN")
            end_location: Destination location name (e.g., "ROUTE_103")
            final_coords: Final target coordinates in destination (optional)
            start_coords: Current coordinates in start location (optional)
        
        Returns:
            True if plan created successfully, False otherwise
        """
        logger.info(f"🗺️ Planning journey: {start_location} → {end_location}")
        
        # Clear any existing plan
        self.clear_plan()
        
        # Find shortest path
        path = find_shortest_path(start_location, end_location)
        
        if not path:
            logger.error(f"❌ No path found from {start_location} to {end_location}")
            return False
        
        self.journey_start = start_location
        self.journey_end = end_location
        self.final_coords = final_coords
        
        # Convert path to stages
        self._build_stages_from_path(path, final_coords)
        
        logger.info(f"✅ Journey planned: {len(self.stages)} stages")
        self._log_full_plan()
        
        return True
    
    def _build_stages_from_path(
        self,
        path: List[Tuple[str, str, Dict[str, Any]]],
        final_coords: Optional[Tuple[int, int]] = None
    ):
        """
        Build navigation stages from a location path.
        
        Each portal crossing requires 2 stages:
        1. NAVIGATE to exit_coords (or INTERACT_WARP for warp tiles)
        2. CROSS_BOUNDARY (or WAIT_FOR_WARP for warp tiles)
        
        Final stage: NAVIGATE to final_coords (or COMPLETE if already there)
        """
        for i, (from_loc, to_loc, portal_info) in enumerate(path):
            portal_type = portal_info.get("type", "open_world")
            exit_coords = portal_info.get("exit_coords")
            entry_coords = portal_info.get("entry_coords")
            direction = portal_info.get("direction", "unknown")
            
            if portal_type == "open_world":
                # Stage 1: Navigate to exit coordinates
                self.stages.append(NavigationStage(
                    stage_type=StageType.NAVIGATE,
                    location=from_loc,
                    target_coords=exit_coords,
                    description=f"Navigate to {direction} exit in {from_loc}"
                ))
                
                # Stage 2: Cross boundary
                self.stages.append(NavigationStage(
                    stage_type=StageType.CROSS_BOUNDARY,
                    location=from_loc,
                    expected_next_location=to_loc,
                    portal_info=portal_info,
                    description=f"Cross boundary to {to_loc}"
                ))
            
            elif portal_type == "warp_tile":
                # Stage 1: Navigate to warp tile and interact
                self.stages.append(NavigationStage(
                    stage_type=StageType.INTERACT_WARP,
                    location=from_loc,
                    target_coords=exit_coords,
                    description=f"Interact with warp tile at {exit_coords} in {from_loc}"
                ))
                
                # Stage 2: Wait for warp to complete
                self.stages.append(NavigationStage(
                    stage_type=StageType.WAIT_FOR_WARP,
                    location=from_loc,
                    expected_next_location=to_loc,
                    portal_info=portal_info,
                    description=f"Wait for warp to {to_loc}"
                ))
        
        # Final stage: Navigate to final coordinates or mark complete
        if final_coords:
            self.stages.append(NavigationStage(
                stage_type=StageType.NAVIGATE,
                location=self.journey_end,
                target_coords=final_coords,
                description=f"Navigate to final target {final_coords} in {self.journey_end}"
            ))
        
        # Always add COMPLETE stage
        self.stages.append(NavigationStage(
            stage_type=StageType.COMPLETE,
            location=self.journey_end,
            target_coords=final_coords,
            description="Journey complete"
        ))
    
    def get_current_stage(self) -> Optional[NavigationStage]:
        """Get the current navigation stage"""
        if not self.has_active_plan():
            return None
        return self.stages[self.current_stage_index]
    
    def get_current_directive(
        self,
        current_location: str,
        current_coords: Optional[Tuple[int, int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the current navigation directive.
        
        This is the ONE instruction the agent receives. The planner automatically
        advances to the next stage when appropriate.
        
        Args:
            current_location: Agent's current location
            current_coords: Agent's current coordinates (optional)
        
        Returns:
            Directive dict with action, target, and metadata, or None if no plan
        """
        if not self.has_active_plan():
            return None
        
        stage = self.get_current_stage()
        
        # Auto-advance if location changed (boundary crossed or warp completed)
        if self._should_auto_advance(stage, current_location, current_coords):
            logger.info(f"✅ Stage {self.current_stage_index} complete: {stage.description}")
            self.current_stage_index += 1
            
            # Check if journey complete
            if not self.has_active_plan():
                logger.info("🎯 Journey complete!")
                return {
                    "action": "COMPLETE",
                    "location": current_location,
                    "description": "Navigation complete"
                }
            
            # Get next stage
            stage = self.get_current_stage()
            logger.info(f"▶️ Advancing to stage {self.current_stage_index}: {stage.description}")
        
        # Convert stage to directive
        return self._stage_to_directive(stage, current_location, current_coords)
    
    def _should_auto_advance(
        self,
        stage: NavigationStage,
        current_location: str,
        current_coords: Optional[Tuple[int, int]]
    ) -> bool:
        """Check if we should automatically advance to next stage"""
        
        # CROSS_BOUNDARY: advance when location changes
        if stage.stage_type == StageType.CROSS_BOUNDARY:
            if current_location == stage.expected_next_location:
                return True
        
        # WAIT_FOR_WARP: advance when location changes
        elif stage.stage_type == StageType.WAIT_FOR_WARP:
            if current_location == stage.expected_next_location:
                return True
        
        # NAVIGATE: advance when we reach target coordinates
        elif stage.stage_type == StageType.NAVIGATE:
            if current_coords and stage.target_coords:
                if current_coords == stage.target_coords:
                    return True
        
        # INTERACT_WARP: advance after interaction (location should change next step)
        # We'll advance in WAIT_FOR_WARP instead
        
        return False
    
    def _stage_to_directive(
        self,
        stage: NavigationStage,
        current_location: str,
        current_coords: Optional[Tuple[int, int]]
    ) -> Dict[str, Any]:
        """Convert a navigation stage to an executable directive"""
        
        if stage.stage_type == StageType.NAVIGATE:
            return {
                "action": "NAVIGATE",
                "target": stage.target_coords,
                "location": stage.location,
                "description": stage.description,
                "stage_index": self.current_stage_index,
                "total_stages": len(self.stages)
            }
        
        elif stage.stage_type == StageType.CROSS_BOUNDARY:
            return {
                "action": "CROSS_BOUNDARY",
                "from_location": stage.location,
                "to_location": stage.expected_next_location,
                "portal_type": stage.portal_info.get("type"),
                "direction": stage.portal_info.get("direction"),
                "description": stage.description,
                "stage_index": self.current_stage_index,
                "total_stages": len(self.stages)
            }
        
        elif stage.stage_type == StageType.INTERACT_WARP:
            return {
                "action": "INTERACT_WARP",
                "target": stage.target_coords,
                "location": stage.location,
                "to_location": stage.expected_next_location,
                "description": stage.description,
                "stage_index": self.current_stage_index,
                "total_stages": len(self.stages)
            }
        
        elif stage.stage_type == StageType.WAIT_FOR_WARP:
            return {
                "action": "WAIT",
                "expected_location": stage.expected_next_location,
                "description": stage.description,
                "stage_index": self.current_stage_index,
                "total_stages": len(self.stages)
            }
        
        elif stage.stage_type == StageType.COMPLETE:
            return {
                "action": "COMPLETE",
                "location": stage.location,
                "final_coords": stage.target_coords,
                "description": stage.description,
                "stage_index": self.current_stage_index,
                "total_stages": len(self.stages)
            }
        
        return {
            "action": "UNKNOWN",
            "description": f"Unknown stage type: {stage.stage_type}"
        }
    
    def _log_full_plan(self):
        """Log the complete navigation plan for debugging"""
        logger.info("=" * 60)
        logger.info(f"📋 FULL NAVIGATION PLAN: {self.journey_start} → {self.journey_end}")
        logger.info("=" * 60)
        for i, stage in enumerate(self.stages):
            prefix = "▶️" if i == self.current_stage_index else "  "
            logger.info(f"{prefix} Stage {i}: {stage}")
        logger.info("=" * 60)
    
    def get_progress_summary(self) -> str:
        """Get a human-readable progress summary"""
        if not self.has_active_plan():
            return "No active navigation plan"
        
        current = self.current_stage_index + 1
        total = len(self.stages)
        stage = self.get_current_stage()
        
        return (
            f"Journey: {self.journey_start} → {self.journey_end} | "
            f"Stage {current}/{total}: {stage.description}"
        )
    
    def force_advance_stage(self):
        """Manually advance to next stage (for debugging/testing)"""
        if self.has_active_plan():
            logger.warning(f"⚠️ Manually advancing from stage {self.current_stage_index}")
            self.current_stage_index += 1


# ============================================================================
# TESTING AND EXAMPLES
# ============================================================================

def test_navigation_planner():
    """Test the NavigationPlanner with various journeys"""
    print("\n" + "=" * 80)
    print("TESTING NAVIGATION PLANNER")
    print("=" * 80)
    
    planner = NavigationPlanner()
    
    # Test 1: Simple journey (Littleroot → Route 103)
    print("\n" + "-" * 80)
    print("TEST 1: Littleroot Town → Route 103 (Rival Battle)")
    print("-" * 80)
    
    success = planner.plan_journey(
        start_location="LITTLEROOT_TOWN",
        end_location="ROUTE_103",
        final_coords=(9, 3)  # Rival May position
    )
    
    if success:
        print(f"\n✅ Plan created successfully!")
        print(f"📊 Progress: {planner.get_progress_summary()}\n")
        
        # Simulate journey step-by-step
        print("🎮 SIMULATING JOURNEY:\n")
        
        # Stage 0: Navigate to exit in Littleroot
        directive = planner.get_current_directive("LITTLEROOT_TOWN", (10, 5))
        print(f"Agent receives: {directive['action']} → {directive.get('target')} in {directive.get('location')}")
        print(f"Description: {directive['description']}\n")
        
        # Simulate reaching exit coords
        directive = planner.get_current_directive("LITTLEROOT_TOWN", (10, 0))
        print(f"Agent at (10, 0) - Stage advanced!")
        print(f"Agent receives: {directive['action']} → {directive.get('to_location')}")
        print(f"Description: {directive['description']}\n")
        
        # Simulate crossing to Route 101
        directive = planner.get_current_directive("ROUTE_101", (10, 28))
        print(f"Agent crossed to Route 101!")
        print(f"Agent receives: {directive['action']} → {directive.get('target')} in {directive.get('location')}")
        print(f"Description: {directive['description']}\n")
        
        # Simulate reaching Route 101 exit
        directive = planner.get_current_directive("ROUTE_101", (11, 0))
        print(f"Agent at (11, 0) - Stage advanced!")
        print(f"Agent receives: {directive['action']} → {directive.get('to_location')}")
        print(f"Description: {directive['description']}\n")
        
        # Simulate crossing to Oldale
        directive = planner.get_current_directive("OLDALE_TOWN", (11, 24))
        print(f"Agent crossed to Oldale Town!")
        print(f"Agent receives: {directive['action']} → {directive.get('target')} in {directive.get('location')}")
        print(f"Description: {directive['description']}\n")
        
        # Simulate reaching Oldale exit
        directive = planner.get_current_directive("OLDALE_TOWN", (10, 0))
        print(f"Agent at (10, 0) - Stage advanced!")
        print(f"Agent receives: {directive['action']} → {directive.get('to_location')}")
        print(f"Description: {directive['description']}\n")
        
        # Simulate crossing to Route 103
        directive = planner.get_current_directive("ROUTE_103", (10, 22))
        print(f"Agent crossed to Route 103!")
        print(f"Agent receives: {directive['action']} → {directive.get('target')} in {directive.get('location')}")
        print(f"Description: {directive['description']}\n")
        
        # Simulate reaching rival
        directive = planner.get_current_directive("ROUTE_103", (9, 3))
        print(f"Agent at rival position (9, 3) - Stage advanced!")
        print(f"Agent receives: {directive['action']}")
        print(f"Description: {directive['description']}\n")
        
        print(f"📊 Final Progress: {planner.get_progress_summary()}")
    
    # Test 2: Long journey with warp tiles (Littleroot → Rustboro Gym)
    print("\n" + "-" * 80)
    print("TEST 2: Littleroot Town → Rustboro City Gym")
    print("-" * 80)
    
    planner.clear_plan()
    success = planner.plan_journey(
        start_location="LITTLEROOT_TOWN",
        end_location="RUSTBORO_CITY_GYM",
        final_coords=(5, 2)  # Roxanne position
    )
    
    if success:
        print(f"\n✅ Plan created successfully!")
        print(f"📊 Total stages: {len(planner.stages)}\n")
        
        print("📋 COMPLETE STAGE BREAKDOWN:\n")
        for i, stage in enumerate(planner.stages):
            print(f"Stage {i}: {stage}")
        
        print(f"\n📊 Progress: {planner.get_progress_summary()}")
    
    # Test 3: Simple warp tile (Littleroot → Player's House 2F)
    print("\n" + "-" * 80)
    print("TEST 3: Littleroot Town → Player's House 2F")
    print("-" * 80)
    
    planner.clear_plan()
    success = planner.plan_journey(
        start_location="LITTLEROOT_TOWN",
        end_location="PLAYERS_HOUSE_2F",
        final_coords=(5, 1)  # Clock position
    )
    
    if success:
        print(f"\n✅ Plan created successfully!")
        print(f"📊 Total stages: {len(planner.stages)}\n")
        
        print("📋 COMPLETE STAGE BREAKDOWN:\n")
        for i, stage in enumerate(planner.stages):
            print(f"Stage {i}: {stage}")
        
        print(f"\n🎮 SIMULATING WARP JOURNEY:\n")
        
        # Navigate to house door
        directive = planner.get_current_directive("LITTLEROOT_TOWN", (5, 10))
        print(f"Agent receives: {directive['action']} → {directive.get('target')} in {directive.get('location')}")
        print(f"Description: {directive['description']}\n")
        
        # Reach door and interact
        directive = planner.get_current_directive("LITTLEROOT_TOWN", (4, 7))
        print(f"Agent at door (4, 7) - Stage advanced!")
        print(f"Agent receives: {directive['action']}")
        print(f"Description: {directive['description']}\n")
        
        # Warp completes
        directive = planner.get_current_directive("PLAYERS_HOUSE_1F", (4, 7))
        print(f"Agent warped to Player's House 1F!")
        print(f"Agent receives: {directive['action']} → {directive.get('target')} in {directive.get('location')}")
        print(f"Description: {directive['description']}\n")
        
        print(f"📊 Progress: {planner.get_progress_summary()}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    test_navigation_planner()
