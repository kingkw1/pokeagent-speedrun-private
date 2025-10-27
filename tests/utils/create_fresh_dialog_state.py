#!/usr/bin/env python3
"""
Create a fresh dialogue savestate by:
1. Starting from a known state
2. Walking up to an NPC
3. Pressing A to trigger dialogue
4. Saving the state while dialogue is active
"""

print("""
🎯 MANUAL STATE CREATION INSTRUCTIONS:

1. Run: python run.py --manual --load-state tests/states/start.state
2. Walk to the NPC (girl in the room)
3. Press Z (A button) to start dialogue
4. While dialogue box is open, press F1 to save state
5. Name it: tests/states/dialog_fresh.state
6. Press Ctrl+C to exit

Then we'll test with the fresh state.
""")
