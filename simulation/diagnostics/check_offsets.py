import stable_retro as retro

# Define candidates (Decimal addresses)
# Set 1: Standard US Emerald (most common)
# 0x020241E4 (My HP) -> 33702372
# 0x02024448 (Enemy HP) -> 33702984

# Set 2: Alternate / Ruby/Sapphire Offset
# 0x0202408C (My HP) -> 33702028

# Set 3: FireRed/LeafGreen (Just in case)
# 0x02023D50 -> 33701200

# Set 4: The ones I gave you before (converted from 0x0219...)
# 35247176, 35247588

CANDIDATES = [
    33702372, # Set 1 MyHP
    33702984, # Set 1 EnemyHP
    33702028, # Set 2 MyHP
    35247588, # Set 4 MyHP
]

def main():
    # 1. Create a data.json that defines ALL of them
    variables = {}
    for i, addr in enumerate(CANDIDATES):
        variables[f"candidate_{i}"] = {"address": addr, "type": "|u1"}
    
    # We construct the data dictionary manually to inject into the running env
    # (or you can write this to data.json file, but let's try injection)
    
    print("Writing temporary data.json...")
    import json
    with open('simulation/data/PokemonEmerald-GBA/data.json', 'w') as f:
        json.dump({"info": variables}, f)
        
    print("Launching Env...")
    env = retro.make(game='PokemonEmerald-GBA', state='BattleLevel5')
    env.reset()
    
    # Step once
    obs, rew, term, trunc, info = env.step(env.action_space.sample())
    
    print("\n--- RESULTS ---")
    for k, v in info.items():
        if k.startswith("candidate"):
            print(f"{k} (Addr {variables[k]['address']}): {v}")
            
    print("\nLook at the values above. Do any of them match your Battle HP (e.g. ~20)?")

if __name__ == "__main__":
    main()
