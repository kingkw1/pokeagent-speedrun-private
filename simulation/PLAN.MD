
### Phase 1: The "Digital Twin" Infrastructure (Simulation)
**Goal:** Establish a high-speed, headless training environment using `stable-retro`.

**Step 1.1: Environment Initialization**
*   **Action:**
    *   Install `stable-retro`, `stable-baselines3`, and `shimmy`.
    *   Acquire the correct Pokémon Emerald ROM (sha1 must match `stable-retro` expectations, usually `f3ae088181bf583e55da942a2b44ad1d`).
    *   Run `python -m retro.import .` to import the ROM.
*   **VCC:** Run `python -m retro.examples.interactive --game PokemonEmerald-GBA`. The window opens and you can play the game manually.

**Step 1.2: Scenario Definition (The "Save State")**
*   **Action:**
    *   Play the game until the very first rival battle (May/Brendan).
    *   Save state **exactly** as the text "May would like to battle!" finishes and the UI appears.
    *   Name this state `BattleLevel5`.
*   **VCC:** A script loads `retro.make(game='PokemonEmerald-GBA', state='BattleLevel5')`, resets the env, and immediately prints "Step 0" without crashing.

**Step 1.3: Sensor Definition (RAM Mapping)**
*   **Action:**
    *   Locate the `data.json` file for PokemonEmerald in your `stable-retro` installation.
    *   Verify or Add these variables (using standard GBA memory maps):
        *   `enemy_hp`: Address `0x02024448` (Verify this offset for Emerald).
        *   `my_hp`: Address `0x020241e4` (Verify this offset).
*   **VCC:** Run a diagnostic script that steps the environment and prints: `{"enemy_hp": 20, "my_hp": 20}`. The numbers must match what is on screen.

### Phase 2: The "Brain" (Policy Development)
**Goal:** Train a PPO model to win the specific battle scenario.

**Step 2.1: The Gym Wrapper**
*   **Action:** Write `EmeraldBattleEnv` (as drafted previously).
    *   **Input:** Raw RAM dict from Retro.
    *   **Normalization:** Convert HP (0-20) to Float (0.0-1.0).
    *   **Reward Function:** `(DamageDealt * 2) - DamageTaken`.
*   **VCC:** Run `check_env(EmeraldBattleEnv)` from stable-baselines3. It must pass without warnings.

**Step 2.2: Training Loop**
*   **Action:** Run PPO training for 500,000 steps (should take <1 hour on modern hardware).
    *   Use `SubprocVecEnv` to run 4-8 environments in parallel.
*   **VCC:** Tensorboard logs show `ep_rew_mean` increasing. The saved model `emerald_battle_v1.zip` exists.

**Step 2.3: Sim Validation**
*   **Action:** Load the model and watch it play 10 battles in `render_mode='human'`.
*   **VCC:** The agent wins >80% of battles against the Level 5 rival.

### **Phase 3: Scaling Intelligence (Future Roadmap)**
**Goal:** Once the baseline HP-based agent is trained, we will incrementally restore complexity to the observation space to enable type-matching and advanced strategy.

#### **3.1 Expanding the Sensor Suite**
We will use `diagnostics/find_memory.py` to locate the following static addresses relative to the Battle Structure.

| Feature | RAM Type | Purpose | Implementation Strategy |
| :--- | :--- | :--- | :--- |
| **Move 1 ID** | `u16` | Identify move type (Water, Fire). | Lookup table in wrapper: `ID -> {Type, Power}`. |
| **Move PP** | `u8` | Resource management. | Normalize `current_pp / max_pp`. |
| **Enemy Species** | `u16` | Identify enemy type. | Lookup table: `SpeciesID -> {Type1, Type2}`. |
| **Status Condition** | `u8` | Detect Sleep/Poison. | One-hot encoding (e.g., `[is_sleep, is_poison]`). |

*Note: In Gen 3, Move 1 is typically at offset `+12` bytes from the start of the Pokémon struct. PP is at `+20`.*

#### **3.2 Knowledge Injection (The Lookup Tables)**
Instead of forcing the agent to learn the entire type chart from scratch (which takes millions of steps), we will inject **domain knowledge** directly into the observation space.

**New Observation Vector:**
```python
[
  # HP (Existing)
  my_hp_norm, enemy_hp_norm,
  
  # Type Effectiveness (Calculated in Wrapper)
  move_1_effectiveness, # e.g., 2.0 (Super Effective), 0.5 (Not Very)
  move_2_effectiveness,
  move_3_effectiveness,
  move_4_effectiveness,

  # Resources
  move_1_has_pp, # Boolean (1.0 or 0.0)
  ...
]
```
*Why this wins:* This reduces the problem from "Memorize all 386 Pokémon types" to "Pick the move with the highest effectiveness number."

#### **3.3 Action Masking (Safety)**
To prevent the agent from selecting Move 3 when it has 0 PP (which wastes a turn struggling), we will implement **Action Masking**.
*   **Technique:** Use `ActionMasker` from `sb3-contrib`.
*   **Logic:** If `pp[i] == 0`, mask Action `i`.

### Phase 4: The "Driver" (Deployment Bridge)
**Goal:** Build the interface that allows your Python code to "see" the real mGBA emulator the same way the model sees the simulation.

**Step 4.1: Clean Slate Setup**
*   **Action:** Create a new folder `deployment/`. Copy *only* the necessary connection/server files from `sethkartenPokeAgent` (likely `server/`, `pokemon_env/`, and `run.py`). Delete the old `agent/` folder logic.
*   **VCC:** You can run `python run.py` and it connects to mGBA and takes a screenshot.

**Step 4.2: The RAM Driver (Parity Check)**
*   **Action:** Update `pokemon_env/emerald_utils.py` to read the **exact same memory addresses** you used in Step 1.3.
    *   *Critical:* If Sim used `0x02024448` for EnemyHP, Real must use `0x02024448`.
*   **VCC:** Run `verify_parity.py`. It connects to a running mGBA battle and prints `Real World Sensor Read: HP=20/20`.

**Step 4.3: The Inference Engine**
*   **Action:** Create `agent/battle_bot.py`.
    *   Class `BattleBot`: Loads `.zip` model.
    *   Method `get_move(my_hp, enemy_hp)`: Returns button press.
*   **VCC:** A unit test loads the zip, inputs `(10, 0)` (low HP, enemy dead), and asserts the output is valid (not an error).

### Phase 5: System Integration (The Hierarchical Agent)
**Goal:** Integrate the Battle Bot as a sub-routine of the main VLM agent.

**Step 5.1: The Hierarchical Controller**
*   **Action:** Create a simple `main_agent.py` loop:
    ```python
    while True:
        # 1. Perception (Strategic)
        state_description = vlm.analyze_screenshot()
        
        # 2. Router
        if "BATTLE" in state_description:
             # Handover to Tactical Layer
             run_battle_routine() 
        else:
             # Stay in Strategic Layer
             vlm.decide_navigation()
    ```
*   **VCC:** Logs show "Transitioning to Battle Mode" when a battle starts.

**Step 5.2: The Battle Sub-Routine**
*   **Action:** Implement `run_battle_routine()`:
    *   Loop: Read RAM $\to$ `BattleBot.predict()` $\to$ Send Input $\to$ Sleep(0.1s).
    *   Break condition: RAM shows Enemy HP = 0 or text detection sees "Won".
*   **VCC:** Full End-to-End Test. You start the script, walk into the rival, the battle triggers, the RL agent takes over, wins, and hands control back to the VLM.
