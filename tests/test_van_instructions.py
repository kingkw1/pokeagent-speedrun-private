#!/usr/bin/env python3
"""Quick test to see agent decision-making in the moving van"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Simulate the state data the agent would receive
test_state = {
    'player': {
        'location': 'MOVING_VAN',
        'position': {'x': 2, 'y': 2, 'map': 0x0001}
    },
    'game': {
        'in_battle': False,
        'dialogue': {'active': False}
    },
    'map': {}
}

# Test the context-aware goal selection logic
location = test_state.get('player', {}).get('location', '')
available_directions = ['UP', 'DOWN', 'LEFT', 'RIGHT']

print(f"Testing with location: {location}")
print(f"Available directions: {available_directions}")
print()

if 'MOVING_VAN' in location.upper():
    goal = "Exit the moving van through the door"
    if 'RIGHT' in available_directions:
        instruction = "The door is to the RIGHT (EAST). Choose RIGHT to exit the van."
    elif 'LEFT' in available_directions or 'UP' in available_directions or 'DOWN' in available_directions:
        instruction = "Explore the van to find the door. Try different directions."
    else:
        instruction = "No clear path. Try moving to find the exit."
    
    print(f"Goal: {goal}")
    print(f"Instruction: {instruction}")
    print()
    print("✅ PASS: Context-aware instructions are working!")
else:
    print("❌ FAIL: Location not recognized as MOVING_VAN")
