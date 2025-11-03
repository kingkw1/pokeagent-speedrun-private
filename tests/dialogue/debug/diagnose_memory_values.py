#!/usr/bin/env python3
"""
Deep dive into memory values during dialogue detection

This will read raw memory addresses to see what's happening
"""

import subprocess
import time
import sys
sys.path.insert(0, '/home/kevin/Documents/pokeagent-speedrun')

from pokemon_env.memory_reader import PokemonEmeraldReader
from pokemon_env.emulator import EmeraldEmulator

def main():
    print("=" * 80)
    print("MEMORY VALUE DIAGNOSTIC")
    print("=" * 80)
    
    # Create emulator and load state
    rom_path = "Emerald-GBAdvance/rom.gba"
    emu = EmeraldEmulator(rom_path=rom_path)
    emu.initialize()
    
    print(f"Emulator core initialized: {emu.core is not None}")
    print(f"Memory reader initialized: {emu.memory_reader is not None}")
    
    emu.load_state("tests/save_states/dialog.state")
    
    print(f"State loaded successfully")
    
    # The reader is part of the emulator
    reader = emu.memory_reader
    
    def show_memory_values(label):
        print(f"\n{label}")
        print("-" * 80)
        
        # Script context values
        global_mode = reader._read_u8(reader.addresses.SCRIPT_CONTEXT_GLOBAL + reader.addresses.SCRIPT_MODE_OFFSET)
        global_status = reader._read_u8(reader.addresses.SCRIPT_CONTEXT_GLOBAL + reader.addresses.SCRIPT_STATUS_OFFSET)
        immediate_mode = reader._read_u8(reader.addresses.SCRIPT_CONTEXT_IMMEDIATE + reader.addresses.SCRIPT_MODE_OFFSET)
        immediate_status = reader._read_u8(reader.addresses.SCRIPT_CONTEXT_IMMEDIATE + reader.addresses.SCRIPT_STATUS_OFFSET)
        
        print(f"  SCRIPT_CONTEXT_GLOBAL mode:      {global_mode} (0x{global_mode:02X})")
        print(f"  SCRIPT_CONTEXT_GLOBAL status:    {global_status} (0x{global_status:02X})")
        print(f"  SCRIPT_CONTEXT_IMMEDIATE mode:   {immediate_mode} (0x{immediate_mode:02X})")
        print(f"  SCRIPT_CONTEXT_IMMEDIATE status: {immediate_status} (0x{immediate_status:02X})")
        
        # Dialog state values
        dialog_state = reader._read_u8(reader.addresses.DIALOG_STATE)
        overworld_freeze = reader._read_u8(0x02022B4C)
        
        print(f"  DIALOG_STATE:                    {dialog_state} (0x{dialog_state:02X})")
        print(f"  OVERWORLD_FREEZE:                {overworld_freeze} (0x{overworld_freeze:02X})")
        
        # Message box indicators
        try:
            is_signpost = reader._read_u8(reader.addresses.MSG_IS_SIGNPOST)
            box_cancelable = reader._read_u8(reader.addresses.MSG_BOX_CANCELABLE)
            print(f"  MSG_IS_SIGNPOST:                 {is_signpost} (0x{is_signpost:02X})")
            print(f"  MSG_BOX_CANCELABLE:              {box_cancelable} (0x{box_cancelable:02X})")
        except:
            print(f"  MSG box indicators: (unavailable)")
        
        # Dialog text
        dialog_text = reader.read_dialog()
        print(f"  Dialog text: '{dialog_text[:60] if dialog_text else 'None'}...'")
        
        # Detection result
        is_dialog = reader.is_in_dialog()
        print(f"  => is_in_dialog(): {is_dialog}")
        
        # Position (using proper method)
        x, y = reader.read_coordinates()
        print(f"  Player position: ({x}, {y})")
        
        # Check the savestate pointer
        savestate_ptr = reader._read_u32(reader.addresses.SAVESTATE_OBJECT_POINTER)
        print(f"  SAVESTATE_OBJECT_POINTER: 0x{savestate_ptr:08X}")
    
    # Initial state
    show_memory_values("INITIAL STATE (before any A presses)")
    
    # Press A several times
    for i in range(1, 4):
        print(f"\n{'=' * 80}")
        print(f"PRESSING A (attempt #{i})")
        print(f"{'=' * 80}")
        
        # Press and hold A for 12 frames, then release for 24 frames
        emu.press_buttons(["A"], hold_frames=12, release_frames=24)
        
        show_memory_values(f"AFTER A PRESS #{i}")
    
    # Try to move UP
    print(f"\n{'=' * 80}")
    print(f"PRESSING UP")
    print(f"{'=' * 80}")
    
    emu.press_buttons(["UP"], hold_frames=12, release_frames=24)
    
    show_memory_values("AFTER UP PRESS")
    
    emu.close()

if __name__ == "__main__":
    main()
