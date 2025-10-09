### **Project Plan: PokéAgent Speedrunning Submission**
**Timeline:** October 9th – November 15th

---

### **Week 1 (Oct 9 - Oct 17): The Skeleton Agent — Foundation & Perception De-Risking**

**Primary Goal:** Build and validate a complete, end-to-end agent loop that can perceive the game world and execute an action. This week is entirely focused on de-risking the most critical dependencies: perception and system integration.

#### **Daily Breakdown:**

*   **Day 1 (Thu, Oct 9): Environment & Baseline Validation**
    *   **Task:** Set up the complete development environment: clone the starter kit repo, install the emulator, and configure all Python dependencies.
    *   **Daily Goal:** Successfully run the organizer-provided baseline agent. Generate a valid `submission.log` file to confirm the setup is correct.

*   **Day 2 (Fri, Oct 10): VLM Data Collection Pipeline**
    *   **Task:** Write a script to programmatically capture screenshots from the emulator. Manually play the game for 15 minutes, capturing ~50 screenshots of varied states (overworld, dialogue, menus). For 10 of these, manually write the target structured JSON output.
    *   **Daily Goal:** A folder of screenshots and a corresponding JSONL file with 10 `(image_path, json_string)` pairs. This is the seed for our perception dataset.

*   **Day 3 (Sat, Oct 11): VLM Fine-Tuning Test**
    *   **Task:** Using the 10-sample dataset, run a fine-tuning job on a base VLM (e.g., Llama 3.2 Vision).[1, 2] The goal is not a good model, but to debug the training script and prove the process works.
    *   **Daily Goal:** A fine-tuning script that runs to completion without errors and saves a new model checkpoint.

*   **Day 4 (Sun, Oct 12): Agent Code Scaffolding**
    *   **Task:** Create the main `agent.py` file. Define the four core modules (Perception, Planning, Memory, Action) as Python classes with placeholder methods, following the baseline's modular design.[3]
    *   **Daily Goal:** A runnable script that initializes the four modules and enters a main loop, even if the loop does nothing yet.

*   **Day 5 (Mon, Oct 13): Perception Module Integration**
    *   **Task:** Integrate the VLM checkpoint from Day 3 into the Perception module. The module's main method should now take a screenshot and return the VLM's predicted JSON string.
    *   **Daily Goal:** A test script that feeds a screenshot to the Perception module and prints a valid (though likely inaccurate) JSON object.

*   **Day 6 (Tue, Oct 14): Action Module & Emulator Control**
    *   **Task:** Implement the Action module's core function: translating a simple command (e.g., `"PRESS A"`) into the correct API call to the emulator.
    *   **Daily Goal:** The agent can now make the character in the game perform a single action, like turning or confirming a menu option.

*   **Day 7 (Wed, Oct 15): V0.1 - The First End-to-End Run**
    *   **Task:** Hard-code the Planning module to output a single command (e.g., `"PRESS UP"`). Connect all modules.
    *   **Daily Goal:** Execute a single script that launches the agent, which then perceives the screen (using the VLM), gets a hard-coded plan, and executes a single action in the emulator. **This is your V0.1 Skeleton Agent.**

*   **Day 8 (Thu, Oct 16): Review, Refactor & Contingency**
    *   **Task:** Clean up the Week 1 code, add comments, and document the VLM data collection process. This is a built-in buffer day to catch up on any prior task that has fallen behind.
    *   **Daily Goal:** A clean, documented codebase for V0.1.

*   **Day 9 (Fri, Oct 17): Head Start on Week 2**
    *   **Task:** Begin data collection for the navigation controller. Record 15-20 minutes of gameplay, focusing on walking between the first three towns. Log `(screenshot, action)` pairs.
    *   **Daily Goal:** A preliminary dataset for imitation learning.

**Key Tasks (Summary):**
1.  **Environment Setup:** Fully install and configure the starter kit, emulator, and all dependencies. Ensure you can run the baseline agent and generate valid submission logs.
2.  **VLM Perception - Initial Test:** The biggest unknown is the Vision-Language Model's ability to accurately parse the game screen.
    *   Collect a small, targeted dataset (~50-100 screenshots) of the most important game states: overworld navigation, dialogue boxes, and the battle interface.
    *   Fine-tune a base VLM (e.g., an open-source Llama 3.2 Vision model) on this small dataset.[1] The goal is not perfection, but to prove the model can learn to output a structured JSON state from a raw pixel screenshot.[2]
3.  **Build the Skeleton Agent (V0.1):**
    *   **Perception:** Integrate the initial VLM.
    *   **Planning:** A placeholder module. It will contain a single, hard-coded instruction (e.g., `{"subgoal": "NAVIGATE_TO", "target": "coordinates(10,12)"}`).
    *   **Memory:** A placeholder module that does nothing for now.
    *   **Action/Control:** A placeholder module that translates the planner's command into a simple sequence of button presses (e.g., "press UP 5 times").

**Milestone & Deliverable:**
*   **A functional V0.1 Agent.** This agent can be launched, will successfully read the screen using the VLM, parse it to JSON, and execute a single hard-coded command in the emulator. This proves the entire pipeline works.

**Risk Mitigation:**
*   **Risk:** The VLM is too slow or its accuracy is unacceptably low even on the simple dataset.
*   **Contingency Plan:** If the VLM proves unworkable, we immediately pivot to a more "scaffolded" perception module. This could involve using computer vision libraries (e.g., OpenCV) for template matching of key UI elements or, as a last resort, reading directly from the emulator's RAM. This would incur a scaffolding penalty but guarantees a working perception system, allowing the project to proceed.

---

### **Week 2 (Oct 18 - Oct 24): Basic Competence — The First Autonomous Milestone**

**Primary Goal:** Achieve the first meaningful, autonomous task in the game. This demonstrates that the agent can execute a simple plan from start to finish.

#### **Daily Breakdown:**

*   **Day 10 (Sat, Oct 18): Scripted Planner Implementation**
    *   **Task:** Replace the hard-coded planner with a script that defines a sequence of the first three game milestones.[3] The planner should check the game state and issue the next subgoal (e.g., `NAVIGATE_TO Oldale Town`).
    *   **Daily Goal:** The Planning module now outputs a sequence of logical subgoals.

*   **Day 11 (Sun, Oct 19): Navigation Controller Training**
    *   **Task:** Train a simple behavioral cloning model on the navigation dataset collected on Day 9. The model should predict the next action given a state and a target coordinate.
    *   **Daily Goal:** A trained navigation policy model file (`nav_controller.pth`).

*   **Day 12 (Mon, Oct 20): Navigation Controller Integration**
    *   **Task:** Integrate the trained navigation model into the Action module. The module can now accept a `NAVIGATE_TO` command and execute the policy.
    *   **Daily Goal:** The agent can autonomously walk to a specific (x, y) coordinate on the current map.

*   **Day 13 (Tue, Oct 21): Full System Test - First Milestone**
    *   **Task:** Run the full agent loop. The scripted planner will issue the "Go to Oldale" subgoal, and the navigation controller will execute it.
    *   **Daily Goal:** **V0.2 Agent** successfully navigates from the start to Oldale Town without intervention.

*   **Day 14 (Wed, Oct 22): Expansion and Reliability Testing**
    *   **Task:** Expand the scripted plan to include reaching Petalburg City. Run the agent 5 times to identify common failure points in the navigation policy.
    *   **Daily Goal:** Agent can reliably reach Petalburg City. A list of failure cases is documented.

*   **Day 15 (Thu, Oct 23): First Leaderboard Submission**
    *   **Task:** Package the V0.2 agent and perform a full run, generating all required logs.
    *   **Daily Goal:** Submit your first entry to the competition leaderboard. This validates the submission process and provides a performance baseline.

*   **Day 16 (Fri, Oct 24): VLM & Controller Refinement**
    *   **Task:** Based on failures, collect more data for both the VLM (for tricky perception states) and the navigation controller (for areas it gets stuck). Retrain both models.
    *   **Daily Goal:** Improved VLM and navigation controller checkpoints.

**Key Tasks (Summary):**
1.  **Implement a Scripted Planner:** Replace the single-command placeholder with a simple script that sequences the first few official game milestones (e.g., 1. Exit Mom's house, 2. Navigate to Oldale Town, 3. Navigate to Petalburg City).
2.  **Develop the Low-Level Controller (Navigation):** The most fundamental skill is navigation.
    *   Record yourself playing for 15-20 minutes, simply walking between key points on the early-game routes.
    *   Use this data to train a basic goal-conditioned navigation policy via imitation learning. The policy will take in the current state (from the VLM) and a target coordinate (from the planner) and output the correct direction button.
3.  **Integrate and Test:** Combine the scripted planner and the new navigation controller into the agent skeleton.

**Milestone & Deliverable:**
*   **A V0.2 Navigational Agent.** This agent can autonomously complete the first two-to-three game milestones. It will successfully navigate from the starting town to Petalburg City without human intervention. This is your first submittable agent.

**Risk Mitigation:**
*   **Risk:** The imitation-learned navigation policy is unreliable and frequently gets stuck.
*   **Contingency Plan:** Fall back to a classic pathfinding algorithm (like A*). We would need to build a simple grid-based representation of the world map from the VLM's output. This is more scaffolding, but provides a 100% reliable navigation controller, ensuring the high-level planner can be tested effectively.

---

### **Week 3 (Oct 25 - Oct 31): Scaling Up & Memory Integration**

**Primary Goal:** Expand the agent's capabilities to handle a longer sequence of tasks and introduce a persistent memory system.

#### **Daily Breakdown:**

*   **Day 17 (Sat, Oct 25): Battle Perception**
    *   **Task:** Collect ~50 screenshots of early-game battle UIs. Update the VLM's target JSON schema to include player/enemy HP, Pokémon names, and moves. Retrain the VLM.
    *   **Daily Goal:** The VLM can now parse the basic elements of the battle screen.

*   **Day 18 (Sun, Oct 26): Rule-Based Battle Controller**
    *   **Task:** Implement a simple, rule-based policy for battles (e.g., "Always use the first available attack move"). Integrate this logic into the Action module.
    *   **Daily Goal:** The agent can now autonomously complete a wild Pokémon battle.

*   **Day 19 (Mon, Oct 27): Foundational Memory System**
    *   **Task:** Set up a local vector database (e.g., ChromaDB). Implement a `WRITE_MEMORY` function that takes a text summary of an event (e.g., "Defeated Youngster Joey"), creates a vector embedding, and stores it.
    *   **Daily Goal:** The agent now logs key events to a persistent vector store.

*   **Day 20 (Tue, Oct 28): Memory Retrieval Integration**
    *   **Task:** Implement a `RETRIEVE_MEMORY` function. Before the planner makes a decision, it queries the vector DB for relevant memories based on the current game state.
    *   **Daily Goal:** The planner's context is now augmented with relevant information from past events.

*   **Day 21 (Wed, Oct 29): Expand Scripted Plan to First Gym**
    *   **Task:** Extend the scripted planner to cover all milestones up to defeating Roxanne in Rustboro City. This includes navigating the forest and battling required trainers.
    *   **Daily Goal:** A hard-coded plan that guides the agent through the first major story arc.

*   **Day 22 (Thu, Oct 30): V0.3 - Full System Test**
    *   **Task:** Run the complete agent from the beginning. It should now navigate, battle, and use its memory to progress through the first gym.
    *   **Daily Goal:** **V0.3 Agent** successfully defeats the first gym leader.

*   **Day 23 (Fri, Oct 31): Data Prep for LLM Planner**
    *   **Task:** Convert the successful run logs from the V0.3 agent into a high-quality dataset for fine-tuning the LLM planner. The format should be `(state_summary, memory_context) -> (next_subgoal)`.
    *   **Daily Goal:** A clean, curated dataset in JSONL format ready for fine-tuning.

**Key Tasks (Summary):**
1.  **Expand the Scripted Plan:** Extend the planner's script to cover all milestones up to the first or second gym leader. This will require adding logic for new situations (e.g., simple trainer battles, item acquisition).
2.  **Implement Foundational Memory System:**
    *   Set up a simple vector database for episodic memory.
    *   At key events (e.g., after a dialogue, winning a battle, reaching a new town), the agent will generate a text summary of the event and store its vector embedding in the database.
    *   The planner can now perform a basic retrieval step before making a decision, pulling the top 1-2 most relevant past events into its context.
3.  **Refine Low-Level Control:** Add a simple, rule-based policy for winning early-game wild Pokémon battles (e.g., "always use the highest power move").

**Milestone & Deliverable:**
*   **A V0.3 Memory-Augmented Agent.** This agent can reliably play through the first ~hour of the game, reaching Rustboro City. It logs key events to its memory and can use that context to inform its path.

**Risk Mitigation:**
*   **Risk:** The vector database retrieval is too slow or returns irrelevant information, confusing the planner.
*   **Contingency Plan:** Revert to a simpler memory model. Create a structured dictionary or log file that stores key-value pairs (e.g., `{"met_rival": true, "last_town_visited": "Petalburg"}`). This is less flexible but provides a stable, predictable context for the planner.

---

### **Week 4 (Nov 1 - Nov 7): The Push for Autonomy & Performance Tuning**

**Primary Goal:** Replace hard-coded components with learned policies to improve the "Adjusted Performance" score by reducing the scaffolding penalty.

#### **Daily Breakdown:**

*   **Day 24 (Sat, Nov 1): LLM Planner Fine-Tuning**
    *   **Task:** Fine-tune a base LLM on the dataset created yesterday. The goal is to teach the LLM to replicate the logic of the successful scripted runs.
    *   **Daily Goal:** A fine-tuned LLM planner checkpoint.

*   **Day 25 (Sun, Nov 2): LLM Planner Integration**
    *   **Task:** Swap the scripted planner module with the new fine-tuned LLM planner. This is a major architectural change.
    *   **Daily Goal:** The agent now makes high-level decisions using the learned LLM.

*   **Day 26 (Mon, Nov 3): Debugging the LLM Planner**
    *   **Task:** Run the agent and observe the LLM's behavior. Implement robust error handling for invalid or nonsensical subgoals. Add a "sanity check" layer to validate the LLM's output.
    *   **Daily Goal:** The agent can run for 15 minutes with the LLM planner without critical failures.

*   **Day 27 (Tue, Nov 4): Performance Analysis**
    *   **Task:** Let the agent run for as long as possible. Analyze the logs to identify the biggest time-sinks and sources of error.
    *   **Daily Goal:** A prioritized list of the top 3 performance bottlenecks.

*   **Day 28 (Wed, Nov 5): Optimization Sprint**
    *   **Task:** Address the #1 bottleneck from yesterday. This could involve improving the battle policy, adding more data to the navigation controller, or refining the LLM fine-tuning prompts.
    *   **Daily Goal:** A measurable improvement in the targeted bottleneck.

*   **Day 29 (Thu, Nov 6): V0.9 - Pre-Competition Agent Run**
    *   **Task:** Conduct a full end-to-end run with the optimized, LLM-driven agent.
    *   **Daily Goal:** A complete run log and video of the **V0.9 Agent**.

*   **Day 30 (Fri, Nov 7): Code Freeze & Fallback Prep**
    *   **Task:** **CODE FREEZE.** No new features are to be added. Ensure the V0.3 scripted agent is packaged and ready as a reliable fallback submission.
    *   **Daily Goal:** A final, stable V0.9 codebase and a packaged V0.3 fallback.

**Key Tasks (Summary):**
1.  **Train the High-Level Planner:** This is the most important step for reducing the scaffolding penalty.
    *   Use the successful trajectories from the V0.3 agent as a dataset.
    *   Fine-tune a powerful LLM (e.g., GPT-4o, Claude 3.5 Sonnet) on this data to teach it to generate the *next* correct subgoal given the game state and memory.
    *   Replace the scripted planner with this new, learned LLM planner.
2.  **Full System Testing:** Execute multiple full runs of the agent from start to finish. This is critical for identifying bugs, edge cases, and failure points in the more autonomous system.
3.  **Performance Analysis:** Analyze the logs from the test runs. Identify the biggest time-sinks (e.g., inefficient navigation, slow battle decisions) and focus on optimizing those specific modules.

**Milestone & Deliverable:**
*   **A V0.9 Pre-Competition Agent.** This version uses a learned LLM for high-level planning. It should perform comparably to the scripted version but will score significantly better on the final evaluation due to its reduced reliance on scaffolding.

**Risk Mitigation:**
*   **Risk:** The fine-tuned LLM planner is erratic, hallucinates invalid subgoals, or is simply worse than the script.
*   **Contingency Plan:** We retain the robust, scripted planner as our fallback submission. The priority is a high-performing, reliable agent. A well-executed scripted agent that gets far in the game may still outscore a "more autonomous" but buggy agent that fails early.

---

### **Week 5 (Nov 8 - Nov 15): Finalization, Documentation, and Submission**

**Primary Goal:** Freeze development, ensure reproducibility, and package the final submission.

#### **Daily Breakdown:**

*   **Day 31 (Sat, Nov 8): Reproducibility Run #1**
    *   **Task:** Start the first of the three required official runs with the V0.9 agent. Monitor for any issues.
    *   **Daily Goal:** Run #1 is complete. Video and logs are saved and verified.

*   **Day 32 (Sun, Nov 9): Reproducibility Run #2 & Documentation**
    *   **Task:** Start Run #2. While it's running, write the first draft of the Methodology Description, focusing on the scaffolding dimensions.[1]
    *   **Daily Goal:** Run #2 is complete. A full draft of the methodology document is written.

*   **Day 33 (Mon, Nov 10): Reproducibility Run #3 & Documentation Finalization**
    *   **Task:** Start the final official run. Review and finalize the methodology document, ensuring it is accurate and compelling.
    *   **Daily Goal:** Run #3 is complete. The methodology document is finalized.

*   **Day 34 (Tue, Nov 11): Final Packaging**
    *   **Task:** Create the final submission `.zip` file. Include the code, model weights, dependencies file, and a detailed README explaining how to reproduce the results.
    *   **Daily Goal:** The complete submission package is created.

*   **Day 35 (Wed, Nov 12): Peer Review & Validation**
    *   **Task:** If possible, have a teammate (or yourself, after a break) try to run the agent from scratch using only the packaged `.zip` file and README. This is the ultimate validation check.
    *   **Daily Goal:** Confirmation that the submission package is fully reproducible.

*   **Day 36 (Thu, Nov 13): Buffer Day**
    *   **Task:** A final buffer day for any unforeseen issues with packaging, documentation, or testing.
    *   **Daily Goal:** Complete peace of mind that the submission is ready.

*   **Day 37 (Fri, Nov 14): **SUBMIT**
    *   **Task:** Upload the final submission package to the competition portal, one day ahead of the deadline.
    *   **Daily Goal:** Submission successfully uploaded and confirmed.

*   **Day 38 (Sat, Nov 15): Deadline Day**
    *   **Task:** Monitor competition channels and relax. You've completed the sprint.

**Key Tasks (Summary):**
1.  **Code Freeze (by Nov 10th):** No new features. The focus is exclusively on bug fixing and stability.
2.  **Reproducibility Runs:** Run the final agent version at least three times from scratch to generate the required video playthroughs and action logs. The official evaluation will be based on the worst of these three runs, so consistency is key.
3.  **Write Methodology Description:** Carefully and accurately document your agent's architecture. Pay close attention to the five scaffolding dimensions (State Information, Tools, Memory, Feedback, Fine-tuning) as this document is required for calculating your final score. Be honest and precise.
4.  **Package Submission:** Create the final code archive, including all dependencies and a detailed README, as required by the rules.
5.  **Submit (by Nov 14th):** Submit everything a day early to avoid any last-minute technical issues.

**Milestone & Deliverable:**
*   **Your final, complete submission package, uploaded to the competition portal.**
