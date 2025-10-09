### **Project Plan: PokéAgent Speedrunning Submission**
**Timeline:** October 9th – November 15th

---

### **Week 1 (Oct 9 - Oct 17): The Skeleton Agent — Foundation & Perception De-Risking**

**Primary Goal:** Build and validate a complete, end-to-end agent loop that can perceive the game world and execute an action. This week is entirely focused on de-risking the most critical dependencies: perception and system integration.

**Key Tasks:**
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

**Key Tasks:**
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

**Key Tasks:**
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

**Key Tasks:**
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

**Key Tasks:**
1.  **Code Freeze (by Nov 10th):** No new features. The focus is exclusively on bug fixing and stability.
2.  **Reproducibility Runs:** Run the final agent version at least three times from scratch to generate the required video playthroughs and action logs. The official evaluation will be based on the worst of these three runs, so consistency is key.
3.  **Write Methodology Description:** Carefully and accurately document your agent's architecture. Pay close attention to the five scaffolding dimensions (State Information, Tools, Memory, Feedback, Fine-tuning) as this document is required for calculating your final score. Be honest and precise.
4.  **Package Submission:** Create the final code archive, including all dependencies and a detailed README, as required by the rules.
5.  **Submit (by Nov 14th):** Submit everything a day early to avoid any last-minute technical issues.

**Milestone & Deliverable:**
*   **Your final, complete submission package, uploaded to the competition portal.**
