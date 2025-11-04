Here is a new, comprehensive prompt you can use to start a fresh thread.

This prompt is designed to bring the new Gemini instance up to speed on all our progress, strategic pivots, and the new 12-day plan, ensuring you don't have to re-explain anything.

---

### **Prompt for New Gemini Thread:**

Hello Gemini. I am in the middle of a high-urgency AI competition, and I need you to take over as my expert AI research and engineering advisor, effective immediately.

**The Situation:**
* **Project:** PokéAgent Speedrunning Challenge (Track 2).
* **Today's Date:** November 4th, 2025.
* **Final Deadline:** November 15th, 2025 (11 days remaining).

**Project History & Critical Context:**
We are **pivoting our strategy**. Our initial plan (from October 9th) was to build a "pure" learning-based agent based on the attached `ARCHITECTURAL_BLUEPRINT.md`. However, after weeks of debugging, we have established two critical facts:
1.  **The VLM is Unreliable:** The VLM (Qwen-2B) is fast, but it is fundamentally incapable of the complex spatial and logical reasoning required for navigation (gets stuck in cul-de-sacs) or handling the game's opening sequence (gets stuck in the moving van, on the naming screen, etc.).
2.  **The Rules Have Changed:** The competition rules have been updated. The "Adjusted Performance" (scaffolding penalty) has been **removed** from the main ranking. The main leaderboard is now based **solely on Raw Performance** (speed and milestone completion).
3.  **The Goal is Simpler:** The organizers have clarified the goal is to **complete the first gym**, not the entire game.

**Our New Strategy: The Hybrid Hierarchical Controller (HHC)**
Given these facts, we have formulated a new 12-day sprint plan. Our new architecture is a "meaningful modification" designed for maximum speed and reliability:
1.  **Programmatic "Opener Bot":** A hard-coded controller to reliably beat the deterministic opening sequence (Splits 0-4).
2.  **Programmatic "Battle Bot":** A rule-based bot to win all required battles.
3.  **Programmatic "A\* Navigator":** A pathfinding tool that uses the `MapStitcher`'s reliable ASCII grid to find the optimal path.
4.  **VLM as Executor:** The VLM's only job is to translate the A\* navigator's next step (e.g., "go to (10,11)") into a button press (e.g., `DOWN`), satisfying the "final action from a neural network" rule.

**Your Role:**
Your role is to act as my technical collaborator to execute this new 12-day plan. I will need your help with implementation details (especially for the programmatic bots and A\* algorithm), debugging, and strategic adjustments.

**Attached Key Documents:**
* **`PROJECT_PLAN.md` (NEW 12-DAY SPRINT):** This is our new "source of truth." It outlines our day-by-day tasks from today until the November 15th deadline.
* **`ARCHITECTURAL_BLUEPRINT.md` (UPDATED):** This is our *revised* technical design. It has been modified to reflect the new HHC architecture.
* **`README.md` (UPDATED):** This is our *revised* project README, also updated to reflect the new HHC architecture.
* **`COMPETITION_DETAILS.md`:** The official rules, including the *new* "Raw Performance" ranking criteria.
* **`objective_manager.py`:** Our high-level programmatic planner.
* **`map_stitcher.py` / `MAP_STITCHER_GUIDE.md`:** The files for the map system our A\* navigator will use.

Please review these documents to fully understand our new, pragmatic approach.

**Let's Begin:**
We are currently on **Day 27 (Tue, Nov 4)** of our new 12-day plan. Yesterday's task was to build the "Opener Bot." Today's task is to **Implement the "Battle Bot."**

Please confirm you have reviewed the new plan and architecture, and let's get started on designing the rule-based battle AI.