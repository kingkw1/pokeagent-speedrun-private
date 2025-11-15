# PokéAgent Speedrun Submission - Methodology

## Overview (~100 words)

**Approach**: Hybrid architecture combining VLM-based perception with programmatic controllers for reliability. Uses Gemini-2.0-flash-lite for visual analysis and action selection, complemented by deterministic state machines for critical sequences.

**State Information (S)**: Raw pixels processed by VLM for structured JSON extraction. Privileged game state from emulator memory used for pathfinding and battle mechanics. Custom OCR fallback for dialogue detection when VLM fails.

**External Tools (T)**: Offline-computed location graph from game wikis for navigation planning. No real-time external dependencies.

**Memory (M)**: Stateful milestone tracking, dialogue history (10-message buffer), position tracking for warp detection, and persistent battle/objective flags.

**Feedback (F)**: Checkpoint-based evaluation at official split milestones. No human-in-the-loop during runs.

**Fine-tuning (Φ)**: None - using base Gemini-2.0-flash-lite without domain-specific training.

---

## Detailed Architecture

### 1. Hybrid Hierarchical Controller (Master System)

**Core Philosophy**: Combine VLM adaptability with programmatic reliability through a priority-based delegation system.

**Priority Cascade**:
1. **Battle Bot** (Programmatic): Rule-based combat with type effectiveness
2. **Opener Bot** (Programmatic): Deterministic state machine for title→starter (95%+ success rate)
3. **Objective Manager** (Programmatic): Milestone-driven progression with tactical directives
4. **Dialogue Handler** (VLM + OCR): Hybrid detection using visual elements and text extraction
5. **Navigation System** (A* + VLM): Map-stitcher-based pathfinding with VLM executor for compliance
6. **VLM Action Selection** (Neural): General-purpose decision-making for novel situations

### 2. Perception Module

**Primary**: VLM structured extraction
- Input: Raw 240x160 RGB pixels from GBA screen
- Output: JSON with screen_context, on_screen_text, visible_entities, visual_elements
- Model: Gemini-2.0-flash-lite (Google API, ~1.5s per query)
- Handles: Overworld navigation, menu states, entity detection

**Secondary**: OCR fallback (Tesseract)
- Activated when VLM returns template text or uncertain dialogue state
- Pokemon-specific color matching for dialogue box detection
- Last-action gating: Only runs secondary VLM check if last action was 'A' (dialogue advancement)
- Validates text with pattern matching to filter false positives

**Tertiary**: Programmatic state detection
- Red triangle indicator for dialogue continuation prompts
- Color-based dialogue box boundary detection
- Menu title extraction via precise coordinate sampling

### 3. Specialized Controllers

**Opener Bot** (State Machine):
- 20+ states covering title screen through starter selection
- Dialogue detection via red triangle + text box visibility
- Story-gate recognition (clock setting, prerequisites)
- Permanent handoff to VLM after STARTER_CHOSEN milestone
- Completion time: ~60-90 seconds

**Battle Bot** (Rule-Based):
- Type effectiveness matrix for move selection
- Trainer vs wild battle classification (behavioral detection)
- Escape failure tracking → switches to fight mode after 9 stuck turns
- Memory-based HP/PP tracking with VLM fallback

**Navigation System** (A* Pathfinding):
- Map stitcher builds connected world graph from explored tiles
- Global A* with grass avoidance, ledge handling, portal detection
- Local BFS fallback for 15x15 visible grid
- Batch movement (up to 15 steps) for efficiency
- VLM executor validates all movements for competition compliance

**Objective Manager** (Milestone Progression):
- 40+ predefined milestones from official speedrun splits
- Location graph with portal types (open_world, warp_tile, ledge)
- Journey planning with multi-stage navigation
- Tactical directives provide goal_coords + should_interact flags
- Persistent state tracking (battle completion, dialogue status)

### 4. Memory Systems

**Dialogue History**: 10-message circular buffer for context-aware responses
**Position Tracking**: Recent positions deque (10 entries) for warp detection
**Milestone Flags**: Persistent completion markers (STARTER_CHOSEN, ROUTE_103_RIVAL_DEFEATED, etc.)
**Battle State**: Current battle type, run attempts, menu state counter
**Post-Dialogue Movement**: 3-step limiter to prevent infinite dialogue loops

### 5. Key Innovations

**VLM-Guided OCR Bypass**: When VLM sets `text_box_visible=true`, skip strict OCR validation and return raw text directly (fixes 100% OCR failure rate)

**Behavioral Battle Type Detection**: If stuck in "unknown" battle state for 9+ turns with 2+ run attempts, reclassify as trainer battle (fixes infinite run loops)

**Smart Secondary Check Gating**: Only run expensive VLM dialogue double-check when last action was 'A', reducing false positives and processing time

**Post-Dialogue Movement Limiting**: Track directional inputs after dialogue ends, pause after 3 movements to re-check for triggered dialogue (prevents Mom intercept loops)

**Map Stitcher Integration**: Server-side world graph construction from explored tiles enables global pathfinding beyond 15x15 vision

### 6. Competition Compliance

**Neural Network Final Action**: All actions route through VLM executor with explicit confirmation
- Navigation: VLM confirms direction before A* path execution  
- Dialogue: VLM validates 'A' button press
- Interaction: VLM approves goal interaction
- Satisfies "final action must come from neural network" requirement

**Reproducibility**: Checkpoint system saves state at split milestones for verification

**No Banned Tools**: No real-time web search, no external APIs during runs, no human intervention

### 7. Performance Characteristics

**Speed**: ~60 FPS gameplay with ~1.5s VLM inference via Gemini API (batched movements compensate for think time)
**Reliability**: 95%+ opener success, robust dialogue handling, intelligent battle classification
**Efficiency**: Movement batching (up to 15 steps), grass avoidance, optimal pathfinding
**Scalability**: Modular architecture supports adding new milestone handlers without core rewrites

---

## Scaffolding Penalty Breakdown

**State Information (S)**: Medium penalty
- Raw pixels (low penalty) + privileged state for pathfinding (medium penalty)
- Justification: Pathfinding requires spatial awareness unavailable from pixels alone

**Tools (T)**: Low penalty  
- Offline location graph from wikis (one-time computation, no real-time dependency)
- No calculators, web search, or external APIs during runs

**Memory (M)**: Medium penalty
- Structured memory (dialogue history, position tracking, milestone flags)
- Not a full vector DB or knowledge graph, but purpose-built state tracking

**Feedback (F)**: None
- Checkpoint evaluation only, no human-in-the-loop
- Agent runs autonomously from start to completion

**Fine-tuning (Φ)**: None
- Base Gemini-2.0-flash-lite without domain adaptation
- Potential future work: Fine-tune on Pokemon gameplay for better dialogue/menu understanding

---

## Future Enhancements

1. **VLM Fine-Tuning**: Train custom vision model on Pokemon Emerald screenshots for improved dialogue/menu comprehension
2. **RL Low-Level Controller**: Replace A* with learned navigation policies
3. **Dynamic Milestone Generation**: LLM-based strategy adaptation instead of fixed milestone list
4. **Memory Management Agent**: RL-based system for intelligent memory querying/storage
5. **Multi-Modal Perception**: Fuse VLM visual analysis with audio cues (background music changes signal events)

---

## Repository Structure

```
agent/
  action.py           # Master controller with priority cascade
  battle_bot.py       # Combat decision-making
  opener_bot.py       # Opening sequence state machine
  objective_manager.py # Milestone tracking and tactical directives
  perception.py       # VLM + OCR hybrid perception
  
utils/
  ocr_dialogue.py     # Pokemon-specific text extraction
  vlm.py              # Multi-backend VLM interface
  
server/
  map_stitcher.py     # World graph construction from explored tiles
  
docs/
  OPENER_BOT.md       # State machine documentation
  DIRECTIVE_SYSTEM.md # Tactical guidance system
  PATHFINDING_SUMMARY.md # Navigation architecture
```

---

**Submission Date**: November 15, 2025  
**Team**: kingkw1  
**Track**: Track 2 (RPG Speedrunning)  
**Model**: Gemini-2.0-flash-lite (Google API)
