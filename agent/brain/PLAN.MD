# 🧠 Memory & Planning System: The "Staff Engineer" Roadmap

**Objective:** Build a resilient agent capable of encountering an obstacle,
logging it, querying its history for solutions, and replanning—starting with
a "Blocker-Recovery" demo.

### Design Rationale (LLM-First Approach)

1.  **Interface Consistency:** The LLM call is wired on Day 1 via
    `get_recovery_plan(context, blocker)`. Day 2 only changes *where the
    context comes from* (hardcoded string → vector database)—no interface
    rework required.
2.  **Systems over Scripts:** Calling an LLM with a "Context Window"
    demonstrates a system architecture (RAG pattern), even before the database
    is connected. A hardcoded dictionary looks like a script.
3.  **Risk Mitigation:** If Day 2 runs long and ChromaDB isn't perfect, the
    demo still shows an AI analyzing a situation and generating a plan—a
    passing grade. A hardcoded dictionary without the DB is a failing grade.

---

## 📅 PHASE 1: The "Reasoning Engine" (MVP — Day 1)

**Goal:** Implement the **Goal Manager** and the **LLM Planner**. Establish the
"Reasoning Loop" immediately, using a static "Cheat Sheet" as a placeholder for
memory.

### 1.1 The `GoalManager` Class

-   **Methodology:** Create a finite state machine that tracks the current
    objective. It handles states: `IN_PROGRESS`, `BLOCKED`, and `COMPLETED`.
-   **Implementation:**
    -   File: `agent/brain/goal_manager.py`
    -   Logic: A class that tracks the `current_objective`. It exposes an
        `update(perception)` method. If perception contains specific "Stop"
        keywords, it transitions to `BLOCKED`.
-   **Verification:**
    -   **Action:** Unit test `tests/test_goal_manager.py`.
    -   **Success:** Feeding mock perception changes state to `BLOCKED`.

### 1.2 The Context-Aware Planner (LLM Integration)

-   **Methodology:** Implement a `RecoveryPlanner` that accepts `current_state`
    and `context`. The LLM is called from Day 1—no hardcoded dictionary.
    -   **Input:** `"Blocked by Old Man."`
    -   **Context (hardcoded for Day 1):**
        `"Old Man requires tutorial interaction. Ledges are one-way."`
    -   **Prompt:**
        `"You are a Game Guide. Based *only* on the context provided, what is the next step to clear the blocker?"`
-   **Implementation:**
    -   File: `agent/brain/planner.py`
    -   Logic: Calls the existing Gemini/VLM client.
-   **Verification:**
    -   **Action:** Run script `demo_planner.py`.
    -   **Success:** The script prints the LLM's raw response explaining *why*
        it chose the recovery step.

> **✅ MVP CHECKPOINT 1:** You have a "Thinking" agent. It uses an LLM to
> reason about obstacles using a provided context window.

---

## 📅 PHASE 2: The "Episodic Memory" (MVP — Day 2)

**Goal:** Replace the hardcoded context string with a **Vector Database**. This
makes the system dynamic and capable of "learning" from gameplay history.

### 2.1 The Vector Store (`ChromaDB`)

-   **Methodology:** Implement a local, persistent vector database using
    `chromadb`.
-   **Implementation:**
    -   File: `agent/brain/memory.py`
    -   Logic: Wrapper class `EpisodicMemory`. Handles embedding generation and
        document storage.
-   **Verification:**
    -   **Action:** Run `demo_rag_memory.py`.
    -   **Success:** Store `"Saw a red potion."` → Query `"healing item."` →
        Result: `"Saw a red potion."` (proving semantic understanding).

### 2.2 The "RAG" Connection

-   **Methodology:** Connect Phase 2 (DB) into Phase 1 (Planner).
-   **Implementation:**
    -   Update `RecoveryPlanner`:
        -   **Old Code:** `context = "Old Man requires tutorial..."`
        -   **New Code:**
            `context = memory.retrieve(query="How to pass " + blocker_name)`
-   **Verification:**
    -   **Action:** Run `demo_full_flow.py`.
    -   **Success:**
        1.  Log: `"Blocked by Old Man."`
        2.  Log: `"Retrieving context..."`
        3.  Log: `"Context Found: 'Old Man needs tutorial.'"`
        4.  Log: `"LLM Plan: 'Interact with the Old Man.'"`

> **🚀 MVP COMPLETION LINE** — If you stop here, you have a Staff-Engineer-level
> demo: a log trace where the agent "thinks," "remembers," and "adapts."

---

## 📅 PHASE 3: The "Cartographer" (Incremental Complexity)

**Goal:** Tie memories to **Space**. The agent shouldn't just remember *what*
happened, but *where* it happened.

### 3.1 Location Tagging

-   **Methodology:** Enrich the memory log with coordinate data from the
    existing `location_db.py`.
-   **Implementation:**
    -   Update `memory.log_event()` to accept `(x, y, map_id)`.
    -   Store coordinates in the `metadata` field of ChromaDB.
-   **Verification:**
    -   **Action:** Query memory with a filter.
    -   **Success:** `memory.retrieve("blocker", where={"map_id": "Route 102"})`
        returns only events for that specific area.

### 3.2 The "Mistake Map"

-   **Methodology:** Visualize where the agent failed.
-   **Implementation:**
    -   Create a heatmap or list of "Blocked" coordinates.
    -   Feed this into `navigation_planner.py` as "Invisible Walls" (cost
        penalty in pathfinding).
-   **Verification:**
    -   **Action:** Run the navigation test.
    -   **Success:** The agent plans a path *around* the tile where it was
        previously blocked, without re-verifying.

---

## 📅 PHASE 4: The "Strategist" (Long-Term Vision)

**Goal:** Recursive Planning and Hierarchical Objectives. The agent manages its
own backlog of tasks.

### 4.1 Recursive Sub-Goaling

-   **Methodology:** If a recovery plan fails (e.g., "Interact with NPC" fails
    because the agent doesn't have a Pokédex), the system recurses.
-   **Implementation:**
    -   `GoalManager` allows tasks to have child tasks.
    -   Goal: "Pass Old Man" → Blocked (Need Pokédex).
        -   Sub-Goal: "Get Pokédex" → Blocked (Need to see Birch).
            -   Sub-Goal: "Go to Lab."
-   **Verification:**
    -   **Action:** Complex simulation script.
    -   **Success:** The stack grows 3 levels deep and unwinds successfully as
        tasks complete.

### 4.2 The "Dream" (Offline Optimization)

-   **Methodology:** Analyze logs *after* a run to optimize future runs.
-   **Implementation:**
    -   Script reads ChromaDB history and uses Gemini to summarize:
        *"What went wrong today?"*
    -   Writes a "Lesson" back into the database for the next run.
-   **Verification:**
    -   **Action:** Run the summarizer.
    -   **Success:** A new entry appears in DB:
        `"Lesson: Always buy potions before entering Route 102."`

---

## Summary of Artifacts

| File                          | Phase       | Purpose                             |
| ----------------------------- | ----------- | ----------------------------------- |
| `agent/brain/goal_manager.py` | **Phase 1** | State Machine (Logic Core)          |
| `agent/brain/planner.py`      | **Phase 1** | LLM-based Recovery Planner          |
| `tests/test_goal_manager.py`  | **Phase 1** | Unit tests for goal tracking        |
| `demo_planner.py`             | **Phase 1** | LLM reasoning demo script           |
| `agent/brain/memory.py`       | **Phase 2** | VectorDB Wrapper (`EpisodicMemory`) |
| `demo_rag_memory.py`          | **Phase 2** | Semantic retrieval demo             |
| `demo_full_flow.py`           | **Phase 2** | End-to-end RAG demo                 |
| `docs/MEMORY_ARCHITECTURE.md` | **Phase 1** | Architecture documentation          |
