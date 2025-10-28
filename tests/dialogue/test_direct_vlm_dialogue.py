#!/usr/bin/env python3
"""
Direct test: What does Qwen-2B see in dialog2.state?
"""

import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

from pokemon_env.emulator import EmeraldEmulator
from utils.vlm import VLM

print("="*80)
print("TESTING QWEN-2B DIALOGUE DETECTION ON DIALOG2.STATE")
print("="*80)

# Load dialog2.state
env = EmeraldEmulator('Emerald-GBAdvance/rom.gba', headless=True)
env.initialize()
env.load_state('tests/states/dialog2.state')
env.tick(60)

# Get screenshot
screenshot = env.get_screenshot()
print(f"\n📸 Screenshot captured: {screenshot.size if screenshot else 'None'}")

# Get game state
state = env.get_comprehensive_state()
game = state.get('game', {})
print(f"\n📊 Memory state:")
print(f"   in_dialog: {game.get('in_dialog')}")
print(f"   overworld_visible: {game.get('overworld_visible')}")
print(f"   movement_enabled: {game.get('movement_enabled')}")

# Test with VLM
print(f"\n🤖 Testing Qwen-2B VLM...")
vlm = VLM(backend='local', model_name='Qwen/Qwen2-VL-2B-Instruct')
print(f"   Model: {vlm.model_name}")

# Simple dialogue check
print(f"\n🔍 Question: Is there a dialogue box visible at the bottom of the screenshot?")
simple_prompt = "Is there a dialogue box visible at the bottom of the screenshot? Answer ONLY YES or NO."

response = vlm.get_query(screenshot, simple_prompt, "TEST")
print(f"📝 VLM Response: '{response}'")

# Try alternative phrasing
print(f"\n🔍 Question 2: Do you see a text box with dialogue at the bottom?")
alt_prompt = "Look at the bottom of the screen. Do you see a text box with dialogue? Answer YES or NO."

response2 = vlm.get_query(screenshot, alt_prompt, "TEST")
print(f"📝 VLM Response 2: '{response2}'")

# Try descriptive question
print(f"\n🔍 Question 3: What do you see at the bottom of the screen?")
desc_prompt = "Describe what you see at the bottom of this Pokemon game screenshot in one sentence."

response3 = vlm.get_query(screenshot, desc_prompt, "TEST")
print(f"📝 VLM Response 3: '{response3}'")

env.close()

print(f"\n" + "="*80)
print(f"INTERPRETATION:")
print(f"="*80)
if 'YES' in response.upper():
    print(f"✅ Qwen-2B detected dialogue box!")
elif 'NO' in response.upper():
    print(f"❌ Qwen-2B says NO dialogue box")
    print(f"   This could mean:")
    print(f"   1. dialog2.state doesn't actually have dialogue visible")
    print(f"   2. VLM cannot see/recognize the dialogue box")
    print(f"   3. Prompt needs better phrasing")
else:
    print(f"⚠️  Ambiguous response from VLM")

print(f"\nMemory says in_dialog={game.get('in_dialog')} (known to be unreliable)")
