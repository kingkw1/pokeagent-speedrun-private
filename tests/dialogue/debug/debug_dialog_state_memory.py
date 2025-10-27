#!/usr/bin/env python3
"""
Debug script: Check actual memory values when loading dialog.state
"""

import subprocess
import time
import requests
import sys

STATE_FILE = "tests/states/dialog.state"

def main():
    print("=" * 70)
    print("🔍 MEMORY DEBUG: dialog.state")
    print("=" * 70)
    
    # Start server
    cmd = ["python", "-m", "server.app", "--port", "8000", "--load-state", STATE_FILE]
    print(f"Starting server: {' '.join(cmd)}\n")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        time.sleep(5)
        
        # Get comprehensive debug info
        print("Fetching /debug/memory...")
        response = requests.get("http://localhost:8000/debug/memory", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print("\n📋 MEMORY VALUES:")
            print("-" * 70)
            for key, value in data.items():
                print(f"  {key}: {value}")
        
        # Get comprehensive state
        print("\n\nFetching /state...")
        response = requests.get("http://localhost:8000/state", timeout=2)
        if response.status_code == 200:
            state = response.json()
            game = state.get("game", {})
            player = state.get("player", {})
            
            print("\n📊 GAME STATE:")
            print("-" * 70)
            print(f"  game_state: {game.get('game_state')}")
            print(f"  in_dialog: {game.get('in_dialog')}")
            print(f"  in_battle: {game.get('in_battle')}")
            print(f"  in_menu: {game.get('in_menu')}")
            print(f"  at_title: {game.get('at_title')}")
            print(f"  overworld_visible: {game.get('overworld_visible')}")
            print(f"  movement_enabled: {game.get('movement_enabled')}")
            print(f"  input_blocked: {game.get('input_blocked')}")
            
            pos = player.get("position", {})
            if isinstance(pos, dict):
                print(f"\n  position: ({pos.get('x')}, {pos.get('y')})")
            else:
                print(f"\n  position: {pos}")
            print(f"  location: {player.get('location')}")
            
            # Dialog text
            dialog_text = state.get("dialog_text")
            print(f"\n  dialog_text: {repr(dialog_text)}")
        
        # Get comprehensive memory diagnostic
        print("\n\nFetching /debug/memory/comprehensive...")
        response = requests.get("http://localhost:8000/debug/memory/comprehensive", timeout=2)
        if response.status_code == 200:
            data = response.json()
            
            print("\n🔬 COMPREHENSIVE MEMORY DIAGNOSTIC:")
            print("-" * 70)
            
            # Dialog-related addresses
            if "dialog_detection" in data:
                dd = data["dialog_detection"]
                print("\nDIALOG DETECTION:")
                print(f"  DIALOG_STATE (0x{dd.get('DIALOG_STATE_addr', ''):08X}): {dd.get('DIALOG_STATE_value')}")
                print(f"  OVERWORLD_FREEZE (0x02022B4C): {dd.get('OVERWORLD_FREEZE_value')}")
                print(f"  SCRIPT_CONTEXT_GLOBAL: mode={dd.get('SCRIPT_GLOBAL_mode')}, status={dd.get('SCRIPT_GLOBAL_status')}")
                print(f"  SCRIPT_CONTEXT_IMMEDIATE: mode={dd.get('SCRIPT_IMMEDIATE_mode')}, status={dd.get('SCRIPT_IMMEDIATE_status')}")
                print(f"  is_in_dialog(): {dd.get('is_in_dialog_result')}")
            
            # Text buffers
            if "text_buffers" in data:
                print("\nTEXT BUFFERS:")
                for buf in data["text_buffers"]:
                    if buf.get("text"):
                        print(f"  {buf['name']}: {repr(buf['text'][:50])}")
        
    finally:
        print("\n" + "=" * 70)
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == "__main__":
    main()
