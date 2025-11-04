
### **Project Plan: The 12-Day Sprint to First Gym**
**New Timeline:** November 3rd – November 15th
**New Primary Goal:** Create a stable, hybrid agent (V0.3) that can autonomously complete all milestones up to and including the first gym (`DEFEATED_ROXANNE`).

**Core Strategy: Implement a Hybrid Hierarchical Controller (HHC)**
Our `action.py` module will become a master controller that intelligently delegates tasks to one of three sub-controllers based on the game state and current objective:
1.  **The "Opener Bot" (Programmatic):** For the deterministic opening sequence.
2.  **The "Battle Bot" (Programmatic):** For all battles.
3.  **The "A\* Navigator" (Programmatic + VLM):** For overworld navigation.

---

### **Week 4 (Nov 3 - Nov 9): The Hybrid Agent Implementation Sprint**

**Goal:** Build and integrate the three core controllers (Opener, Navigator, Battler) and achieve the first full, autonomous run to Oldale Town.

* [ ] **Day 26 (Mon, Nov 3): Implement the "Opener Bot" (TODAY'S TASK)**
    * **Task:** Modify `action.py`. Create a rule-based function `run_opener_bot(objective, state_data)`. This bot will be a simple state machine.
    * **Logic:** The main `action_step` will check the current objective. If the objective ID is `story_game_start`, `story_littleroot_town`, etc., it will call this function.
    * **Daily Goal:** The bot can programmatically handle the title screen, character naming, setting the clock, and exiting the moving van and house, solving our biggest blockers.

* [ ] **Day 27 (Tue, Nov 4): Implement the "Battle Bot"**
    * **Task:** Create a new `agent/battle_bot.py` module. Implement a simple, rule-based policy (e.g., "always use the first super-effective or damaging move").
    * **Logic:** `action.py` will check `game_state`. If `in_battle == True`, it will call this new module.
    * **Daily Goal:** A bot that can reliably win the first rival battle (`story_rival_battle_1`) and simple wild encounters.

* [ ] **Day 28 (Wed, Nov 5): Implement the A\* "Navigator" Tool**
    * **Task:** Create a new `agent/navigator.py` module. Implement an A\* (A-Star) pathfinding algorithm.
    * **Input:** The 100% reliable ASCII map grid from the `MapStitcher`.
    * **Output:** A list of coordinates, e.g., `[(10,10), (10,11), (11,11)]`.
    * **Daily Goal:** A function that can solve the "cul-de-sac" problem by returning a valid path.

* [ ] **Day 29 (Thu, Nov 6): Implement the "Handoff" Logic in `action.py`**
    * **Task:** Rewrite `action.py` to be the master "Handoff" controller.
    * **Logic:** The `action_step` function will now follow this sequence:
        1.  `if game_state == 'battle'`: call `battle_bot`.
        2.  `if objective in [OPENER_OBJECTIVES]`: call `opener_bot`.
        3.  `else (default)`: call the `vlm_navigation_controller`.
    * **Daily Goal:** A clean `action.py` that correctly delegates control to the right sub-controller.

* [ ] **Day 30 (Fri, Nov 7): Integrate A\* with VLM (The "Navigator")**
    * **Task:** Implement the `vlm_navigation_controller` logic from Day 29.
    * **Logic:** This function will:
        1.  Get the destination from the `ObjectiveManager`.
        2.  Call the `navigator.py` A\* function to get the full path.
        3.  Get the *next single step* (e.g., `(10, 11)`) from the path.
        4.  Feed the VLM a simple prompt: "Your current position is (10,10). The next step in your path is (10,11). What is the one button you should press?"
    * **Daily Goal:** The VLM's job is now trivial. It acts as the final (neural network) step to translate `(10,11)` into `DOWN`, satisfying the competition rules while ensuring 100% reliable navigation.

* [ ] **Day 31 (Sat, Nov 8): V0.3 - Full Run to Oldale Town**
    * **Task:** Run the complete hybrid agent from the official start (Split 0).
    * **Daily Goal:** **V0.3 Agent** successfully uses the Opener Bot, wins the first battle, and hands off to the A\*/VLM Navigator to reach Oldale Town (`story_oldale_town`). This is our first end-to-end success.

* [ ] **Day 32 (Sun, Nov 9): Buffer & Debug Day 1**
    * **Task:** Fix bugs from the V0.3 run. The handoff logic or A\* pathing will likely have issues.
    * **Daily Goal:** A stable V0.3 agent.

---

### **Week 5 (Nov 10 - Nov 15): Finalization & Submission**

**Goal:** Push the V0.3 agent to the first gym, document, and submit.

* [ ] **Day 33 (Mon, Nov 10): Full Run to First Gym (Attempt 1)**
    * **Task:** Expand the `ObjectiveManager` list to include all steps to Roxanne. Run the full agent.
    * **Daily Goal:** Identify all failure points between Oldale and the first gym (e.g., Petalburg Woods, required trainer battles).

* [ ] **Day 34 (Tue, Nov 11): Final Optimization Sprint**
    * **Task:** Address the #1 blocker from yesterday's run. This is likely improving the Battle Bot (to handle trainer battles) or the Navigator (to handle new maps).
    * **Daily Goal:** A V0.4 Agent capable of reaching Rustboro City.

* [ ] **Day 35 (Wed, Nov 12): Final Methodology & Code Cleanup**
    * **Task:** **CODE FREEZE.** Write the `Methodology Description` doc for the submission. Clean up all test scripts and debug prints.
    * **Daily Goal:** A finalized, clean codebase and all written documentation.

* [ ] **Day 36 (Thu, Nov 13): Final Submission Run #1 (Video/Logs)**
    * **Task:** Run the V0.4 agent from Split 0. Record the video and capture the `submission.log`.
    * **Daily Goal:** A complete, verifiable run log and video.

* [ ] **Day 37 (Fri, Nov 14): SUBMIT (One Day Early)**
    * **Task:** Package the Code Archive (ZIP), the logs, the video link, and the methodology doc.
    * **Daily Goal:** **Final submission is uploaded and confirmed.**

* [ ] **Day 38 (Sat, Nov 15): DEADLINE. Buffer.**
    * **Task:** (Buffer) Resubmit only if a catastrophic failure was found in yesterday's package.
    * **Daily Goal:** Relax. We have submitted a robust, hybrid agent.