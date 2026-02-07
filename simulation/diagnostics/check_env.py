import stable_retro as retro
import numpy as np

# Restore your data.json and scenario.json BEFORE running this!

def main():
    print("Checking environment readiness...")
    env = retro.make(
        game='PokemonEmerald-GBA', 
        state='BattleLevel5', 
        render_mode='rgb_array'
    )
    env.reset()
    
    # 1. Check RAM reading (The "Sensors")
    # Step once to populate values
    obs, rew, term, trunc, info = env.step(env.action_space.sample())
    
    print("\n--- SENSOR CHECK ---")
    if 'my_hp' in info and 'enemy_hp' in info:
        print(f"✅ HP Sensors Active: MyHP={info['my_hp']}, EnemyHP={info['enemy_hp']}")
    else:
        print(f"❌ HP Sensors Missing! Keys found: {list(info.keys())}")
        
    # 2. Check Action Space
    print(f"✅ Action Space: {env.action_space}")
    
    # 3. Check Visuals
    print(f"✅ Visual Observation Shape: {obs.shape}")
    
    print("\nEnvironment is READY for PPO Training.")
    env.close()

if __name__ == "__main__":
    main()
