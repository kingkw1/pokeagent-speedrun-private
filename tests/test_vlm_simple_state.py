#!/usr/bin/env python3
"""
Comprehensive test for VLM behavior in the simple state scenario.
This test replicates the exact conditions where the agent gets stuck pressing 'A'.
"""

import sys
import os
import json
import time
import requests
from pathlib import Path

# Add project root to path
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

from utils.vlm import VLM
from utils.state_formatter import format_state_for_llm, format_movement_preview_for_llm
from agent.objective_manager import ObjectiveManager

class SimpleStateVLMTest:
    def __init__(self):
        self.vlm = VLM(backend="local", model_name="Qwen/Qwen2-VL-2B-Instruct")
        self.objective_manager = ObjectiveManager()
        
    def setup_server_and_capture_data(self):
        """Start server, capture screenshot and state data"""
        print("🚀 Starting server to capture data...")
        
        # Start the server in background
        import subprocess
        import signal
        
        try:
            # Start server process
            server_cmd = [
                sys.executable, "-m", "server.app", 
                "--port", "8000", 
                "--load-state", "Emerald-GBAdvance/simple_test.state"
            ]
            
            env = os.environ.copy()
            env['PYTHONPATH'] = '/home/kevin/Documents/pokeagent-speedrun'
            
            self.server_process = subprocess.Popen(
                server_cmd,
                cwd='/home/kevin/Documents/pokeagent-speedrun',
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for server to start
            print("⏳ Waiting for server to initialize...")
            time.sleep(8)  # Give it time to load the state
            
            # Try to get state data
            max_retries = 5
            for i in range(max_retries):
                try:
                    print(f"📊 Attempting to get state data (attempt {i+1}/{max_retries})...")
                    state_response = requests.get('http://localhost:8000/state', timeout=10)
                    if state_response.status_code == 200:
                        state_data = state_response.json()
                        print("✅ Successfully captured state data")
                        break
                    else:
                        print(f"❌ State request failed: {state_response.status_code}")
                        time.sleep(2)
                except Exception as e:
                    print(f"❌ State request error: {e}")
                    if i < max_retries - 1:
                        time.sleep(2)
                    else:
                        raise
            
            # Try to get screenshot
            try:
                print("📸 Attempting to capture screenshot...")
                screenshot_response = requests.get('http://localhost:8000/screenshot', timeout=10)
                if screenshot_response.status_code == 200:
                    with open('screenshots/test_simple_state.png', 'wb') as f:
                        f.write(screenshot_response.content)
                    print("✅ Successfully captured screenshot")
                else:
                    print(f"⚠️ Screenshot request failed: {screenshot_response.status_code}")
            except Exception as e:
                print(f"⚠️ Screenshot error: {e}")
            
            return state_data
            
        except Exception as e:
            print(f"❌ Server setup failed: {e}")
            raise
        finally:
            # Clean up server
            if hasattr(self, 'server_process'):
                try:
                    self.server_process.terminate()
                    self.server_process.wait(timeout=5)
                except:
                    self.server_process.kill()
                    
    def create_realistic_prompt(self, state_data):
        """Create the exact prompt that the agent would send to VLM"""
        
        # Include the system prompt used by the agent
        system_prompt = """
You are an AI agent playing Pokémon Emerald on a Game Boy Advance emulator. Your goal is to analyze the current game frame, understand the game state, and make intelligent decisions to progress efficiently. Use your perception, memory, planning, and action modules to interact with the game world. Always provide detailed, context-aware responses and consider the current situation in the game.
""" 
        
        # Format state context (includes map)
        state_context = format_state_for_llm(state_data)
        
        # Get movement preview
        movement_preview = format_movement_preview_for_llm(state_data)
        
        # Get strategic goal
        try:
            current_plan = self.objective_manager.get_strategic_plan_description(state_data)
        except:
            current_plan = "Travel north to Route 101 to find Professor Birch. Navigate carefully and interact with NPCs for guidance."
        
        strategic_goal = f"""
=== YOUR STRATEGIC GOAL ===
{current_plan}

""" if current_plan else ""
        
        # Build the exact prompt structure used by the agent
        action_prompt = f"""Playing Pokemon Emerald. Current screen: overworld

{strategic_goal}Situation: Player: AAAAAAA | Location: ROUTE 101 | Pos: [10, 15] | State: overworld | Money: $3000 | Party: 1 pokemon | Lead: TORCHIC | HP:19/19 | Pokedex: 0 caught, 0 seen | Items: 0 | Time: 00:00:00

=== GAME STATE CONTEXT ===
{state_context.strip()}

{movement_preview}

🚨 CRITICAL NAVIGATION INSTRUCTIONS 🚨

**YOU ARE ON A ROUTE - MOVE WITH DIRECTIONAL BUTTONS, NOT 'A'!**

Look at the MOVEMENT PREVIEW above. It shows:
- UP: WALKABLE means you can go UP
- DOWN: WALKABLE means you can go DOWN  
- LEFT: WALKABLE means you can go LEFT
- RIGHT: WALKABLE means you can go RIGHT

🎯 **YOUR JOB: CHOOSE A DIRECTION TO MOVE**

✅ **CORRECT ACTIONS ON ROUTES:**
- UP (when UP is WALKABLE in MOVEMENT PREVIEW)
- DOWN (when DOWN is WALKABLE in MOVEMENT PREVIEW)
- LEFT (when LEFT is WALKABLE in MOVEMENT PREVIEW)  
- RIGHT (when RIGHT is WALKABLE in MOVEMENT PREVIEW)

❌ **WRONG ACTIONS ON ROUTES:**
- A (this does nothing useful on routes - stops movement!)
- Pressing A repeatedly when you should be moving
- Ignoring the MOVEMENT PREVIEW directions

🎮 **DECISION RULES:**
1. **If screen_context = "overworld" AND MOVEMENT PREVIEW shows WALKABLE directions:**
   → Pick UP, DOWN, LEFT, or RIGHT based on your strategic goal
   → DO NOT pick A unless there's dialogue on screen

2. **If DIALOGUE visible on screen:** Press A to advance dialogue

3. **If in a MENU:** Use UP/DOWN to navigate, A to select

4. **If in BATTLE:** Use A for moves/attacks

**CHOOSE THE DIRECTION THAT MOVES YOU TOWARD YOUR STRATEGIC GOAL**

RESPOND WITH ONLY ONE BUTTON NAME: A, B, UP, DOWN, LEFT, RIGHT, START

NO explanations. NO extra text. Just one direction that's WALKABLE in the MOVEMENT PREVIEW.
"""
        
        # Combine system prompt + action prompt (exactly like the agent does)
        complete_prompt = system_prompt + action_prompt
        return complete_prompt
        
    def test_vlm_responses(self, prompt):
        """Test VLM with multiple attempts and analyze responses"""
        print("🧪 Testing VLM responses...")
        
        responses = []
        for i in range(5):
            try:
                print(f"   Test {i+1}/5...")
                response = self.vlm.get_text_query(prompt, f"simple_state_test_{i+1}")
                responses.append(response.strip().upper())
                print(f"   Response: '{response.strip()}'")
            except Exception as e:
                print(f"   Error: {e}")
                responses.append("ERROR")
        
        return responses
        
    def analyze_results(self, responses, movement_preview):
        """Analyze VLM responses and determine if they're appropriate"""
        print("\n📊 ANALYSIS RESULTS:")
        print("=" * 60)
        
        # Count responses
        response_counts = {}
        for response in responses:
            response_counts[response] = response_counts.get(response, 0) + 1
        
        print(f"Response distribution: {response_counts}")
        
        # Extract available directions from movement preview
        available_directions = []
        if "UP" in movement_preview and "WALKABLE" in movement_preview:
            available_directions.append("UP")
        if "DOWN" in movement_preview and "WALKABLE" in movement_preview:
            available_directions.append("DOWN")
        if "LEFT" in movement_preview and "WALKABLE" in movement_preview:
            available_directions.append("LEFT")
        if "RIGHT" in movement_preview and "WALKABLE" in movement_preview:
            available_directions.append("RIGHT")
            
        print(f"Available walkable directions: {available_directions}")
        
        # Analyze appropriateness
        appropriate_responses = 0
        inappropriate_responses = 0
        
        for response in responses:
            if response in available_directions:
                appropriate_responses += 1
                print(f"✅ '{response}' - APPROPRIATE (directional movement)")
            elif response == "A":
                inappropriate_responses += 1
                print(f"❌ '{response}' - INAPPROPRIATE (should use directional movement)")
            elif response in ["B", "START"]:
                inappropriate_responses += 1
                print(f"❌ '{response}' - INAPPROPRIATE (not useful for navigation)")
            else:
                inappropriate_responses += 1
                print(f"❌ '{response}' - INAPPROPRIATE/ERROR")
        
        # Final assessment
        success_rate = appropriate_responses / len(responses) * 100
        print(f"\n🎯 SUCCESS RATE: {success_rate:.1f}% ({appropriate_responses}/{len(responses)})")
        
        # Specific failure analysis
        if response_counts.get("A", 0) > 0:
            a_percentage = response_counts["A"] / len(responses) * 100
            print(f"⚠️  VLM pressed 'A' {response_counts['A']} times ({a_percentage:.1f}%) - this is the core problem!")
        
        return {
            "success_rate": success_rate,
            "appropriate_responses": appropriate_responses,
            "inappropriate_responses": inappropriate_responses,
            "response_counts": response_counts,
            "available_directions": available_directions
        }

def main():
    print("🚨 VLM SIMPLE STATE TEST")
    print("=" * 60)
    print("This test replicates the exact conditions where the agent gets stuck.")
    print("The VLM should choose directional movement (UP/DOWN/LEFT/RIGHT), NOT 'A'.")
    print()
    
    test = SimpleStateVLMTest()
    
    try:
        # Step 1: Capture data from emulator
        print("📋 STEP 1: Capturing game state data...")
        state_data = test.setup_server_and_capture_data()
        
        # Step 2: Create realistic prompt
        print("\n📋 STEP 2: Creating realistic VLM prompt...")
        prompt = test.create_realistic_prompt(state_data)
        
        # Show prompt preview
        print(f"📝 Prompt length: {len(prompt)} characters")
        print(f"📝 Prompt preview (last 300 chars):")
        print("-" * 50)
        print(prompt[-300:])
        print("-" * 50)
        
        # Extract movement preview for analysis
        movement_preview = format_movement_preview_for_llm(state_data)
        print(f"\n🗺️  Movement Preview:")
        print(movement_preview)
        
        # Step 3: Test VLM responses
        print(f"\n📋 STEP 3: Testing VLM responses...")
        responses = test.test_vlm_responses(prompt)
        
        # Step 4: Analyze results
        print(f"\n📋 STEP 4: Analyzing results...")
        results = test.analyze_results(responses, movement_preview)
        
        # Final verdict
        print(f"\n🏁 FINAL VERDICT:")
        print("=" * 60)
        if results["success_rate"] >= 80:
            print("✅ VLM PASSED - Good directional movement behavior")
            return True
        elif results["success_rate"] >= 50:
            print("⚠️ VLM PARTIAL - Some directional movement but inconsistent")
            return False
        else:
            print("❌ VLM FAILED - Poor directional movement behavior")
            if results["response_counts"].get("A", 0) > len(responses) * 0.5:
                print("💥 ROOT CAUSE: VLM has strong bias toward pressing 'A' button")
            return False
            
    except Exception as e:
        print(f"💥 TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n{'='*60}")
    if success:
        print("✅ SIMPLE STATE VLM TEST PASSED")
        sys.exit(0)
    else:
        print("❌ SIMPLE STATE VLM TEST FAILED")
        sys.exit(1)