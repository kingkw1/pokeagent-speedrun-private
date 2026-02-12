# 🧠 Memory & Planning System: The "Staff Engineer" Roadmap (v2)

**Objective:** Build a resilient agent capable of encountering an obstacle,
logging it, querying its history via RAG, and replanning using an LLM.

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

## 🛠️ ARCHITECTURE: The Integration Point

Before writing code, we define exactly where this fits into the existing
`Agent.step()` loop in `agent/__init__.py`.

### Current Flow (agent/__init__.py)

```
1. Perception   →  perception_step(frame, state_data, vlm)
2. Stuck Detect →  position_history / oscillation check
3. Planning     →  planning_step(memory, plan, ..., state_data, vlm)
4. Memory       →  string concatenation of recent observations
5. Action       →  action_step(memory, plan, perception, ..., vlm)
```

### New Flow

```
1.  Perception    →  perception_step(frame, state_data, vlm)
1.5 Goal Manager  →  goal_manager.update(perception_output)     ← NEW
2.  Stuck Detect  →  position_history / oscillation check
3.  Planning      →  planning_step(...) OR recovery_planner(...)  ← MODIFIED
4.  Memory        →  episodic_memory.log_event(...)               ← UPGRADED (Phase 2)
5.  Action        →  action_step(memory, plan, perception, ..., vlm)
```

**Insertion point:** Between the perception safety check (~line 155) and the
`should_replan` logic (~line 168) in `agent/__init__.py`.

### The Input Contract

`GoalManager.update(perception_output)` consumes the VLM output dict. The
fields live **inside `perception_output['visual_data']`**, not at the top
level. The correct access paths are:

| Field                   | Path                                                          | Type          |
| ----------------------- | ------------------------------------------------------------- | ------------- |
| Dialogue text           | `perception_output['visual_data']['on_screen_text']['dialogue']` | `str \| None`  |
| Speaker                 | `perception_output['visual_data']['on_screen_text']['speaker']`  | `str \| None`  |
| Screen context          | `perception_output['visual_data']['screen_context']`             | `str`          |
| Text box visible        | `perception_output['visual_data']['visual_elements']['text_box_visible']` | `bool` |

> **⚠️ Note:** The existing `goal_manager.py` accesses
> `perception_output.get("on_screen_text")` directly — this is incorrect and
> will always return `None`. The rewrite must use the paths above.

---

## 📅 PHASE 1: The "Reasoning Engine" (MVP — Day 1)

**Goal:** Implement the logic core. The agent "thinks" about obstacles using an
LLM, with a static "Cheat Sheet" as the context source.

### 1.1 The `GoalManager` Class

-   **Methodology:** A finite state machine tracking `current_objective`.
    States: `IN_PROGRESS`, `BLOCKED`, `COMPLETED`.
-   **Input parsing:** Extracts dialogue from
    `perception_output['visual_data']['on_screen_text']['dialogue']`.
    Regex/keyword match: `["wait", "stop", "don't go", "dangerous"]`.
    If match found → transition to `BLOCKED`.
-   **Implementation:**
    -   File: `agent/brain/goal_manager.py` (rewrite existing file)
    -   Logic:
        -   Maintains a stack of `sub_tasks`.
        -   Exposes `update(perception_output)` → returns current state.
        -   Exposes `get_current_directive()` → returns plan string for the
            action module.
-   **Verification:**
    -   **Test:** `tests/test_goal_manager.py`
    -   **Success:** Feed mock perception:
        ```python
        {"visual_data": {"on_screen_text": {"dialogue": "Wait! Don't go out!"},
                         "screen_context": "dialogue"}}
        ```
        Assert state becomes `BLOCKED`.

### 1.2 The Context-Aware Planner (LLM Integration)

-   **Methodology:** A `RecoveryPlanner` that takes the blocker description and
    a context string, then asks the LLM for immediate recovery steps.
    No hardcoded dictionary.
-   **Implementation:**
    -   File: `agent/brain/planner.py` (new file)
    -   Context (hardcoded for Day 1):
        `"Old Man = Tutorial. Tree = Cut. Ledge = One way."`
    -   Prompt:
        `"You are a Game Guide. Context: {CONTEXT}. Situation: Blocked by {BLOCKER}. What is the immediate recovery action?"`
    -   Calls the existing `utils.vlm.VLM` client (Gemini).
-   **Verification:**
    -   **Script:** `demo_planner.py`
    -   **Success:** Prints:
        `"Plan: Talk to the Old Man to trigger the catching tutorial."`

> **✅ MVP CHECKPOINT 1:** The agent can perceive a block and produce a correct
> recovery plan using an LLM with a cheat sheet. The interface is identical to
> what Phase 2 will use.

---

## 📅 PHASE 2: The "Episodic Memory" (MVP — Day 2)

**Goal:** Replace the static cheat sheet with a dynamic Vector Database.

### 2.1 The Vector Store (`ChromaDB`)

-   **Methodology:** Local, persistent vector storage.
-   **Embedding model:** `all-MiniLM-L6-v2` (80 MB, ms-latency on CPU,
    sufficient for short game text).
-   **Implementation:**
    -   File: `agent/brain/memory.py` (already exists — verify/refine)
    -   API surface:
        -   `add_memory(text, metadata)` — stores an event.
        -   `retrieve(query, n=3)` — semantic search, returns list of strings.
-   **Verification:**
    -   **Script:** `demo_rag_memory.py` (already exists — verify/refine)
    -   **Success:** Log `"NPC said route is closed."` → Query
        `"Why can't I pass?"` → Returns the log entry.

### 2.2 The "RAG" Connection

-   **Methodology:** Inject the DB into the Planner.
-   **Implementation:**
    -   Modify `RecoveryPlanner` in `agent/brain/planner.py`:
        -   **Old:** `CONTEXT = "Old Man = Tutorial..."`
        -   **New:** `CONTEXT = memory.retrieve(query=blocker_description)`
-   **Verification:**
    -   **Script:** `demo_full_flow.py`
    -   **Success:**
        1.  Log: `"Blocked by Old Man."`
        2.  Log: `"Retrieving context..."`
        3.  Log: `"Context Found: 'Old Man needs tutorial.'"`
        4.  Log: `"LLM Plan: 'Interact with the Old Man.'"`

> **🚀 MVP COMPLETION LINE** — If you stop here, you have a Staff-Engineer-level
> demo: a log trace where the agent "thinks," "remembers," and "adapts."

---

## 📅 PHASE 3: Spatial Awareness (Stretch — High Risk)

**Goal:** Tie memories to coordinates.

-   **Risk Warning:** Dynamic cost overlays in the A* pathfinder is a large
    change and out of scope for a 2-day MVP.
-   **Revised Scope: Logging Only.**
    -   Log `(x, y, map_id)` as metadata on every `add_memory()` call.
    -   Do **not** attempt to update the pathfinding graph dynamically.
    -   Value: We can *show* the spatial data ("Look, I know *where* I got
        blocked") without risking breakage in navigation code.

---

## 📅 PHASE 4: Recursive Sub-Goaling (North Star)

**Goal:** Multi-step dependency chains (Get Cut → Beat Gym → Cut Tree).

-   **Status:** Out of scope for MVP.
-   **Role:** "Next Steps" talking point.

---

## Immediate Execution Steps

1.  Rewrite `agent/brain/goal_manager.py` — fix input contract, remove
    hardcoded dictionary, wire `BLOCKED` state transition.
2.  Create `agent/brain/planner.py` — LLM-based `RecoveryPlanner`.
3.  Write `tests/test_goal_manager.py` — unit tests with mock perception dicts.
4.  Create `demo_planner.py` — standalone demo showing LLM reasoning.

---

## Summary of Artifacts

| File                          | Phase       | Status       | Purpose                             |
| ----------------------------- | ----------- | ------------ | ----------------------------------- |
| `agent/brain/goal_manager.py` | **Phase 1** | Rewrite      | State Machine (Logic Core)          |
| `agent/brain/planner.py`      | **Phase 1** | New          | LLM-based Recovery Planner          |
| `tests/test_goal_manager.py`  | **Phase 1** | New          | Unit tests for goal tracking        |
| `demo_planner.py`             | **Phase 1** | New          | LLM reasoning demo script           |
| `agent/brain/memory.py`       | **Phase 2** | Exists       | VectorDB Wrapper (`EpisodicMemory`) |
| `demo_rag_memory.py`          | **Phase 2** | Exists       | Semantic retrieval demo             |
| `demo_full_flow.py`           | **Phase 2** | New          | End-to-end RAG demo                 |
| `docs/MEMORY_ARCHITECTURE.md` | **Phase 1** | New          | Architecture documentation          |
