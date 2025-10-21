#!/usr/bin/env python3
"""
Debug script to test VLM navigation perception on a specific game state
"""

import json
import sys
import requests
import time
from PIL import Image
from io import BytesIO

def test_vlm_navigation():
    """Test VLM perception on current game state"""
    
    # Start server in background
    import subprocess
    import os
    
    # Load the quick start save state
    server_cmd = [
        sys.executable, "-m", "server.app", 
        "--port", "8001", 
        "--load-state", "Emerald-GBAdvance/quick_start_save.state",
        "--headless"
    ]
    
    print("🚀 Starting server for navigation debug...")
    server = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for server to start
    time.sleep(5)
    
    try:
        # Get screenshot and state
        print("📸 Getting screenshot and state...")
        screenshot_response = requests.get("http://localhost:8001/screenshot")
        state_response = requests.get("http://localhost:8001/state")
        
        if screenshot_response.status_code != 200 or state_response.status_code != 200:
            print(f"❌ Server requests failed: screenshot={screenshot_response.status_code}, state={state_response.status_code}")
            return
        
        # Get the frame
        frame = Image.open(BytesIO(screenshot_response.content))
        state_data = state_response.json()
        
        print(f"🎮 Game State:")
        print(f"   Location: {state_data.get('player', {}).get('location', 'Unknown')}")
        print(f"   Position: {state_data.get('player', {}).get('position', {})}")
        print(f"   Game State: {state_data.get('game', {}).get('state', 'unknown')}")
        
        # Test perception
        print("\n🔍 Testing VLM perception...")
        from agent.perception import perception_step
        from utils.vlm import VLM
        
        # Initialize VLM
        vlm = VLM(backend="local", model="Qwen/Qwen2-VL-2B-Instruct")
        
        # Run perception
        observation = perception_step(frame, state_data, vlm)
        
        print("\n📊 VLM Perception Results:")
        visual_data = observation.get('visual_data', {})
        print(f"   Screen Context: {visual_data.get('screen_context', 'unknown')}")
        
        nav_info = visual_data.get('navigation_info', {})
        if nav_info:
            print(f"   Exits Visible: {nav_info.get('exits_visible', [])}")
            print(f"   Interactable Objects: {nav_info.get('interactable_objects', [])}")
            print(f"   Movement Barriers: {nav_info.get('movement_barriers', [])}")
            print(f"   Open Paths: {nav_info.get('open_paths', [])}")
        
        spatial = visual_data.get('spatial_layout', {})
        if spatial:
            print(f"   Room Type: {spatial.get('room_type', 'unknown')}")
            print(f"   Player Position: {spatial.get('player_position', 'unknown')}")
            print(f"   Notable Features: {spatial.get('notable_features', [])}")
        
        # Check movement options from game state
        print("\n🗺️ Movement Options from Game State:")
        from utils.state_formatter import get_movement_options
        movement_options = get_movement_options(state_data)
        for direction, description in movement_options.items():
            print(f"   {direction}: {description}")
            
        print("\n✅ Navigation debug complete!")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up server
        server.terminate()
        server.wait()

if __name__ == "__main__":
    test_vlm_navigation()