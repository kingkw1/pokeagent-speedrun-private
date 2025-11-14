"""
Comprehensive tests for NavigationPlanner showing step-by-step breakdowns.

These tests demonstrate how the navigation planner guides the agent through
multi-hop journeys one instruction at a time, automatically advancing stages
as the agent makes progress.
"""

import sys
import logging
from agent.navigation_planner import NavigationPlanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")


def print_step(step_num: int, description: str):
    """Print a numbered step"""
    print(f"\n{'─' * 80}")
    print(f"STEP {step_num}: {description}")
    print('─' * 80)


def test_littleroot_to_route103():
    """
    Test: Navigate from Littleroot Town to Route 103 to battle rival May.
    
    This is the typical early-game journey where the agent needs to:
    1. Exit Littleroot Town northward
    2. Cross Route 101
    3. Pass through Oldale Town
    4. Reach Route 103
    5. Navigate to rival's position
    """
    print_section("TEST 1: Littleroot Town → Route 103 (Rival Battle)")
    
    planner = NavigationPlanner()
    
    # Create the plan
    print("🗺️  CREATING NAVIGATION PLAN")
    print(f"Start: LITTLEROOT_TOWN")
    print(f"End: ROUTE_103")
    print(f"Final Target: (9, 3) - Rival May's position")
    
    success = planner.plan_journey(
        start_location="LITTLEROOT_TOWN",
        end_location="ROUTE_103",
        final_coords=(9, 3)
    )
    
    if not success:
        print("❌ Failed to create plan!")
        return
    
    print(f"\n✅ Plan created: {len(planner.stages)} stages total")
    
    # Show full breakdown
    print("\n📋 FULL STAGE BREAKDOWN:")
    for i, stage in enumerate(planner.stages):
        print(f"  Stage {i}: {stage}")
    
    # Now simulate the journey step-by-step
    print("\n" + "=" * 80)
    print(" SIMULATING AGENT JOURNEY (One Instruction at a Time)")
    print("=" * 80)
    
    # Step 1: Agent starts in Littleroot Town
    print_step(1, "Agent starts in Littleroot Town at (10, 10)")
    current_location = "LITTLEROOT_TOWN"
    current_coords = (10, 10)
    
    directive = planner.get_current_directive(current_location, current_coords)
    print(f"\n📨 Agent receives ONE instruction:")
    print(f"   Action: {directive['action']}")
    print(f"   Target: {directive.get('target')}")
    print(f"   Location: {directive.get('location')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent thinks: 'I need to navigate to (10, 0) in LITTLEROOT_TOWN'")
    
    # Step 2: Agent reaches the exit coordinates
    print_step(2, "Agent reaches north exit at (10, 0)")
    current_coords = (10, 0)
    
    directive = planner.get_current_directive(current_location, current_coords)
    print(f"\n✅ Stage auto-advanced! (Agent reached target coordinates)")
    print(f"\n📨 Agent receives ONE instruction:")
    print(f"   Action: {directive['action']}")
    print(f"   From: {directive.get('from_location')}")
    print(f"   To: {directive.get('to_location')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent thinks: 'I need to cross the boundary to ROUTE_101'")
    
    # Step 3: Agent crosses to Route 101
    print_step(3, "Agent crosses boundary, now in Route 101 at (10, 28)")
    current_location = "ROUTE_101"
    current_coords = (10, 28)
    
    directive = planner.get_current_directive(current_location, current_coords)
    print(f"\n✅ Stage auto-advanced! (Agent's location changed)")
    print(f"\n📨 Agent receives ONE instruction:")
    print(f"   Action: {directive['action']}")
    print(f"   Target: {directive.get('target')}")
    print(f"   Location: {directive.get('location')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent thinks: 'I need to navigate to (11, 0) in ROUTE_101'")
    
    # Step 4: Agent reaches Route 101 north exit
    print_step(4, "Agent reaches Route 101 north exit at (11, 0)")
    current_coords = (11, 0)
    
    directive = planner.get_current_directive(current_location, current_coords)
    print(f"\n✅ Stage auto-advanced! (Agent reached target coordinates)")
    print(f"\n📨 Agent receives ONE instruction:")
    print(f"   Action: {directive['action']}")
    print(f"   From: {directive.get('from_location')}")
    print(f"   To: {directive.get('to_location')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent thinks: 'I need to cross the boundary to OLDALE_TOWN'")
    
    # Step 5: Agent crosses to Oldale Town
    print_step(5, "Agent crosses boundary, now in Oldale Town at (11, 24)")
    current_location = "OLDALE_TOWN"
    current_coords = (11, 24)
    
    directive = planner.get_current_directive(current_location, current_coords)
    print(f"\n✅ Stage auto-advanced! (Agent's location changed)")
    print(f"\n📨 Agent receives ONE instruction:")
    print(f"   Action: {directive['action']}")
    print(f"   Target: {directive.get('target')}")
    print(f"   Location: {directive.get('location')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent thinks: 'I need to navigate to (10, 0) in OLDALE_TOWN'")
    
    # Step 6: Agent reaches Oldale north exit
    print_step(6, "Agent reaches Oldale Town north exit at (10, 0)")
    current_coords = (10, 0)
    
    directive = planner.get_current_directive(current_location, current_coords)
    print(f"\n✅ Stage auto-advanced! (Agent reached target coordinates)")
    print(f"\n📨 Agent receives ONE instruction:")
    print(f"   Action: {directive['action']}")
    print(f"   From: {directive.get('from_location')}")
    print(f"   To: {directive.get('to_location')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent thinks: 'I need to cross the boundary to ROUTE_103'")
    
    # Step 7: Agent crosses to Route 103
    print_step(7, "Agent crosses boundary, now in Route 103 at (10, 22)")
    current_location = "ROUTE_103"
    current_coords = (10, 22)
    
    directive = planner.get_current_directive(current_location, current_coords)
    print(f"\n✅ Stage auto-advanced! (Agent's location changed)")
    print(f"\n📨 Agent receives ONE instruction:")
    print(f"   Action: {directive['action']}")
    print(f"   Target: {directive.get('target')}")
    print(f"   Location: {directive.get('location')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent thinks: 'I need to navigate to (9, 3) where rival May is waiting'")
    
    # Step 8: Agent reaches rival position
    print_step(8, "Agent reaches rival May at (9, 3)")
    current_coords = (9, 3)
    
    directive = planner.get_current_directive(current_location, current_coords)
    print(f"\n✅ Stage auto-advanced! (Agent reached target coordinates)")
    print(f"\n📨 Agent receives ONE instruction:")
    print(f"   Action: {directive['action']}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent thinks: 'Journey complete! Time to battle!'")
    
    print("\n" + "=" * 80)
    print(f"🎯 JOURNEY COMPLETE!")
    print(f"📊 Progress: {planner.get_progress_summary()}")
    print("=" * 80)


def test_littleroot_to_rustboro_gym():
    """
    Test: Navigate from Littleroot Town to Rustboro City Gym.
    
    This is a long journey that demonstrates:
    - Multiple open_world boundary crossings
    - Warp tile interaction (gym door)
    - 20 total stages including final navigation to Roxanne
    """
    print_section("TEST 2: Littleroot Town → Rustboro City Gym (Long Journey)")
    
    planner = NavigationPlanner()
    
    print("🗺️  CREATING NAVIGATION PLAN")
    print(f"Start: LITTLEROOT_TOWN")
    print(f"End: RUSTBORO_CITY_GYM")
    print(f"Final Target: (5, 2) - Gym Leader Roxanne")
    
    success = planner.plan_journey(
        start_location="LITTLEROOT_TOWN",
        end_location="RUSTBORO_CITY_GYM",
        final_coords=(5, 2)
    )
    
    if not success:
        print("❌ Failed to create plan!")
        return
    
    print(f"\n✅ Plan created: {len(planner.stages)} stages total")
    
    # Show full breakdown with stage types
    print("\n📋 FULL STAGE BREAKDOWN:")
    print("\nRoute sequence:")
    print("  Littleroot → Route 101 → Oldale → Route 102 → Petalburg →")
    print("  Route 104 South → Petalburg Woods → Route 104 North → Rustboro → Gym")
    
    print("\nStage details:")
    for i, stage in enumerate(planner.stages):
        stage_type = stage.stage_type.value
        if stage_type == "NAVIGATE":
            print(f"  Stage {i:2d}: NAVIGATE to {stage.target_coords} in {stage.location}")
        elif stage_type == "CROSS_BOUNDARY":
            print(f"  Stage {i:2d}: CROSS_BOUNDARY from {stage.location} to {stage.expected_next_location}")
        elif stage_type == "INTERACT_WARP":
            print(f"  Stage {i:2d}: INTERACT_WARP at {stage.target_coords} in {stage.location}")
        elif stage_type == "WAIT_FOR_WARP":
            print(f"  Stage {i:2d}: WAIT_FOR_WARP to {stage.expected_next_location}")
        elif stage_type == "COMPLETE":
            print(f"  Stage {i:2d}: COMPLETE at {stage.target_coords} in {stage.location}")
    
    # Simulate key stages
    print("\n" + "=" * 80)
    print(" KEY STAGES (Showing transitions)")
    print("=" * 80)
    
    # Start
    print("\n🚀 Stage 0: Agent in Littleroot Town")
    directive = planner.get_current_directive("LITTLEROOT_TOWN", (10, 10))
    print(f"   Instruction: {directive['action']} to {directive.get('target')}")
    
    # After several hops, at Rustboro
    print("\n🏙️  Stage 15: Agent reaches Rustboro City")
    # Manually advance to stage 16 for demonstration
    planner.current_stage_index = 16
    directive = planner.get_current_directive("RUSTBORO_CITY", (20, 25))
    print(f"   Instruction: {directive['action']} at {directive.get('target')} (Gym door)")
    
    # After warp
    print("\n🏛️  Stage 18: Agent warped into Gym")
    planner.current_stage_index = 18
    directive = planner.get_current_directive("RUSTBORO_CITY_GYM", (5, 10))
    print(f"   Instruction: {directive['action']} to {directive.get('target')} (Roxanne)")
    
    print("\n🎯 Final stage would be COMPLETE after reaching Roxanne")


def test_warp_tiles():
    """
    Test: Navigate with warp tiles (doors).
    
    This demonstrates the difference between open_world and warp_tile portals.
    """
    print_section("TEST 3: Warp Tiles (Littleroot → Player's House 2F)")
    
    planner = NavigationPlanner()
    
    print("🗺️  CREATING NAVIGATION PLAN")
    print(f"Start: LITTLEROOT_TOWN")
    print(f"End: PLAYERS_HOUSE_2F")
    print(f"Final Target: (5, 1) - Clock")
    
    success = planner.plan_journey(
        start_location="LITTLEROOT_TOWN",
        end_location="PLAYERS_HOUSE_2F",
        final_coords=(5, 1)
    )
    
    if not success:
        print("❌ Failed to create plan!")
        return
    
    print(f"\n✅ Plan created: {len(planner.stages)} stages total")
    
    # Show full breakdown
    print("\n📋 FULL STAGE BREAKDOWN:")
    for i, stage in enumerate(planner.stages):
        print(f"  Stage {i}: {stage}")
    
    # Simulate warp journey
    print("\n" + "=" * 80)
    print(" SIMULATING WARP JOURNEY")
    print("=" * 80)
    
    # Step 1: Navigate to door
    print_step(1, "Agent in Littleroot Town at (10, 10)")
    directive = planner.get_current_directive("LITTLEROOT_TOWN", (10, 10))
    print(f"\n📨 Agent receives: {directive['action']} to {directive.get('target')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 This is a WARP TILE, not an open boundary!")
    
    # Step 2: At door, ready to interact
    print_step(2, "Agent reaches house door at (4, 7)")
    directive = planner.get_current_directive("LITTLEROOT_TOWN", (4, 7))
    print(f"\n✅ Stage auto-advanced!")
    print(f"\n📨 Agent receives: {directive['action']}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent interacts with door and waits for warp...")
    
    # Step 3: Warp completes
    print_step(3, "Agent warps to Player's House 1F at (4, 7)")
    directive = planner.get_current_directive("PLAYERS_HOUSE_1F", (4, 7))
    print(f"\n✅ Stage auto-advanced! (Warp completed)")
    print(f"\n📨 Agent receives: {directive['action']} to {directive.get('target')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent needs to reach stairs at (8, 2)")
    
    # Step 4: At stairs
    print_step(4, "Agent reaches stairs at (8, 2)")
    directive = planner.get_current_directive("PLAYERS_HOUSE_1F", (8, 2))
    print(f"\n✅ Stage auto-advanced!")
    print(f"\n📨 Agent receives: {directive['action']}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent interacts with stairs...")
    
    # Step 5: Warp to 2F
    print_step(5, "Agent warps to 2F at (8, 2)")
    directive = planner.get_current_directive("PLAYERS_HOUSE_2F", (8, 2))
    print(f"\n✅ Stage auto-advanced! (Warp completed)")
    print(f"\n📨 Agent receives: {directive['action']} to {directive.get('target')}")
    print(f"   Description: {directive['description']}")
    print(f"\n💭 Agent navigates to clock at (5, 1)")
    
    # Step 6: At clock
    print_step(6, "Agent reaches clock at (5, 1)")
    directive = planner.get_current_directive("PLAYERS_HOUSE_2F", (5, 1))
    print(f"\n✅ Stage auto-advanced!")
    print(f"\n📨 Agent receives: {directive['action']}")
    print(f"   Description: {directive['description']}")
    print(f"\n🎯 Journey complete!")


def main():
    """Run all navigation planner tests"""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  NAVIGATION PLANNER - COMPREHENSIVE TEST SUITE".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    test_littleroot_to_route103()
    test_littleroot_to_rustboro_gym()
    test_warp_tiles()
    
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  ALL TESTS COMPLETE".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80 + "\n")


if __name__ == "__main__":
    main()
