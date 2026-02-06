import stable_retro as retro
import sys
import os

# Define paths to ensure we are checking the right files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Assuming verify_env.py is in simulation/diagnostics/
# We need to look up one level to simulation/data/PokemonEmerald-GBA
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../data/PokemonEmerald-GBA"))

def main():
    print(f"Checking environment configuration...")
    print(f"Data Directory: {DATA_DIR}")
    
    # Verify files exist
    required_files = ['data.json', 'scenario.json', 'rom.gba', 'rom.sha', 'BattleLevel5.state']
    for f in required_files:
        path = os.path.join(DATA_DIR, f)
        if not os.path.exists(path):
            print(f"❌ CRITICAL ERROR: Missing {f}")
            return
        else:
            print(f"✅ Found {f}")

    try:
        # Load the environment (Read-Only mode effectively)
        # We assume the integration is already symlinked/installed correctly
        env = retro.make(
            game='PokemonEmerald-GBA', 
            state='BattleLevel5', 
            render_mode='rgb_array'
        )
        env.reset()
        
        # Step once to populate sensors
        obs, rew, term, trunc, info = env.step(env.action_space.sample())
        
        print("\n--- SENSOR READOUT ---")
        if 'my_hp' in info:
            print(f"✅ My HP: {info['my_hp']}")
        else:
            print("❌ My HP not found in info dict")
            
        if 'enemy_hp' in info:
            print(f"✅ Enemy HP: {info['enemy_hp']}")
        else:
            print("❌ Enemy HP not found in info dict")
            
        env.close()
        print("\nEnvironment is VALID.")
        
    except Exception as e:
        print(f"\n❌ FAILED to load environment: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
