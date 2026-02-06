# Simulation & RL Training Environment

This directory contains the infrastructure for training Reinforcement Learning (RL) agents to play *Pokémon Emerald* using `stable-retro`. 

## Goal

The primary goal of this module is to create a "Digital Twin" of the game environment that runs significantly faster than real-time. This allows us to train specialized sub-policies (e.g., a "Battle Bot") using algorithms like PPO, which can then be deployed as part of the larger hierarchical agent.

## Architecture: The Neuro-Symbolic Stack

This project implements a **Hierarchical Control System** designed to solve the Sim-to-Real gap in autonomous agents.

| Component | Technology | Role | Frequency |
| :--- | :--- | :--- | :--- |
| **Strategic Layer** | Gemini 1.5 Pro (VLM) | High-level planning, navigation, dialogue understanding. | 0.2 Hz |
| **Tactical Layer** | PPO (RL Policy) | **Zero-latency** combat decisions based on optimal control theory. | 60 Hz |
| **Digital Twin** | Stable-Retro (GBA) | High-speed headless simulation for policy training (1000+ FPS). | N/A |

The **Tactical Layer** (this repo) is trained in isolation using the Digital Twin to ensure safety and performance before deployment.

## File Structure

```
simulation/
├── check_env.py             # Quick verification script to ensure Retro loads the game and sensors correctly.
├── PLAN.MD                  # Development roadmap and step-by-step implementation plan.
├── train.py                 # Main PPO training script using Stable-Baselines3.
│                            # Defines the `EmeraldBattleWrapper` (Reward function & Observation storage).
├── data/
│   └── PokemonEmerald-GBA/  # Custom integration files for Stable Retro.
│       ├── BattleLevel5.state # Save state: Start of the first rival battle.
│       ├── data.json        # RAM Map: Defines memory addresses for sensors (HP, etc.).
│       ├── metadata.json    # Game system configuration (GBA, default state).
│       ├── rom.gba          # The Game Boy Advance ROM file (must match SHA1 checksum).
│       ├── rom.sha          # SHA1 checksum for verification.
│       ├── scenario.json    # Retro scenario definitions (rewards/done conditions).
│       └── starter.state    # Save state: Game start.
└── diagnostics/             # Tools for debugging the environment and simulator.
    ├── check_offsets.py     # Helps verify if memory addresses in data.json are correct.
    ├── debug_inputs.py      # Debugs controller input mapping.
    ├── find_memory.py       # Helper to scan RAM values (like Cheat Engine) to find variable addresses.
    ├── play_and_save.py     # Interactive tool to play the game, test specific scenarios, and create .state files.
    ├── verify_env.py        # Verifies that custom gym environments load without errors.
    └── verify_sensors.py    # Specifically checks if `info` dictionary returns correct RAM values.
```

## Setup & Usage

### 1. Prerequisites
Ensure you have the correct Python dependencies installed (see root `requirements.txt`).
You must have the `Pokemon Emerald (USA, Europe)` ROM placed in `simulation/data/PokemonEmerald-GBA/rom.gba`.

### 2. Verify the Environment
Before training, run the checking script to ensure the ROM loads and memory addresses are reading correctly:
```bash
python simulation/check_env.py
```
*   **Success:** Prints "✅ HP Sensors Active" and observation shapes.
*   **Failure:** Check `data.json` offsets or ROM version.

### 3. Create Custom Save States
If you need to train on a different part of the game (e.g., a Gym Leader battle), use the helper tool:
```bash
python simulation/diagnostics/play_and_save.py
```
*   Play until the desired moment.
*   Press `M` to save a `.state` file.
*   Update `train.py` or `metadata.json` to point to this new state.

### 4. Train the Agent
Run the training loop (PPO):
```bash
python simulation/train.py
```
This will:
1.  Spin up parallel environments (using `SubprocVecEnv`).
2.  Train the agent to maximize the reward function defined in `EmeraldBattleWrapper`.
3.  Save the resulting model to `models/PPO/`.

## Key Concepts

### Observation Space
Currently, the agent observes a simplified state (defined in `EmeraldBattleWrapper`):
*   **My HP**: Normalized (0.0 - 1.0)
*   **Enemy HP**: Normalized (0.0 - 1.0)

### Reward Function
The agent is incentivized to win battles efficiently:
*   `Reward = (Damage Dealt * 2.0) - (Damage Taken * 1.0)`
*   **Bonus**: +10 for defeating the enemy.

### Custom Integration
We bypass the standard Retro game integration to allow for custom memory maps and save states. This is handled by pointing Retro to our local `simulation/data` folder during initialization.
