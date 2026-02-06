import stable_retro as retro
import time

GAME = 'PokemonEmerald-GBA'

def main():
    print(f"Loading {GAME}...")
    env = retro.make(game=GAME, state=retro.State.NONE)
    env.reset()
    
    print("\n--- CORE INPUT DIAGNOSTIC ---")
    print(f"System: {env.system}")
    print(f"Buttons list: {env.unwrapped.buttons}")
    print(f"Action Space: {env.action_space}")
    
    # In Retro, the 'buttons' list maps Action Space Index -> Button Name.
    # If Index 3 says 'START', sending a 1 to Index 3 *must* trigger Start
    # UNLESS the core itself has remapped it.
    
    print("\nAttempting brute-force input injection on every channel...")
    
    # We will loop through 16 possible channels (Retro usually supports up to 16)
    # even if it says it only has 12.
    for i in range(16):
        print(f"\nTesting Input Channel {i}...")
        
        # Reset bits
        # We try to activate ONE bit at position 'i'
        # Note: input_state is usually a list of booleans or ints matching action_space
        
        # Construct a massive array just in case action space is wider than we think
        op = [0] * 32 
        op[i] = 1
        
        # Slice to actual size
        valid_op = op[:env.action_space.shape[0]]
        
        # If i is out of bounds, we skip
        if i >= len(valid_op):
            print(f"  Skipping (Index {i} out of bounds for action space size {len(valid_op)})")
            continue
            
        print(f"  Sending: {valid_op}")
        
        # Step a few times to ensure it registers
        obs, _, _, _, _ = env.step(valid_op)
        
        # Check if the button list thinks this is 'START'
        if i < len(env.unwrapped.buttons):
            mapped_name = env.unwrapped.buttons[i]
            print(f"  Mapped Name: {mapped_name}")
            if mapped_name == 'START':
                print("  ^^ THIS SHOULD BE START ^^")

if __name__ == "__main__":
    main()
