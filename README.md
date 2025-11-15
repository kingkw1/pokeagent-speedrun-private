# AI Agent for the PokéAgent Speedrunning Challenge

This repository contains the development of a sophisticated, hierarchical AI agent designed to compete in **Track 2 (RPG Speedrunning)** of the NeurIPS 2025 PokéAgent Challenge. Our goal is to build a high-performance agent that can complete Pokémon Emerald by optimizing for the competition's primary ranking metric: **Raw Performance** (milestone completion percentage, time, and action efficiency). Our innovative architecture also aims for the **Judges' Choice** awards by demonstrating novel AI capabilities.

This project is built upon the official starter kit but features a custom, learning-driven architecture with advanced perception capabilities and intelligent action sequencing.

---

## SUBMISSIONS
- split 01 at 094244
- split 02 at 102815
- split 03 at 105806
- split 04 at 152403
- split 05 at 181241

## Current Status & Recent Achievements

**� Directive System Operational (November 12, 2025)**

Successfully implemented tactical directive system for post-opener gameplay:

- ✅ **Route 103 Rival Battle**: Navigates to rival, triggers battle, completes dialogue
- ✅ **Persistent State Tracking**: Battle completion persists even after moving
- ✅ **Dialogue Integration**: Detects and completes post-battle dialogue before navigating
- ✅ **Bug Fixed**: Solved position oscillation after battle completion

**�🎉 Navigation System Complete (November 7, 2025)**

We've successfully implemented a robust navigation system that solves critical pathfinding bugs:

- ✅ **Local BFS Pathfinding**: Navigates around obstacles using 15x15 visible grid
- ✅ **Map Validation**: Detects stale map data and handles gracefully
- ✅ **Goal Parser**: Extracts navigation targets from strategic plans
- ✅ **Bug Fixed**: Solved "re-entering Birch's Lab" issue with intelligent pathfinding

**🤖 Opener Bot Operational (November 2025)**

The programmatic state machine for the opening sequence is complete and tested:

- ✅ **Full Opening Coverage**: Title screen through starter selection
- ✅ **STARTER_CHOSEN Handoff**: Permanent VLM handoff after opening complete
- ✅ **Story-Gate Handling**: Manages Mom's clock directive and other prerequisites
- ✅ **Dialogue + Navigation Hybrid**: Bot handles UI, VLM handles movement

**Previous Milestones:**

- ✅ **VLM Perception Fixed**: Implemented robust JSON parsing with Python tuple to JSON array conversion
- ✅ **Smart Action Sequencing**: Agent now makes single intelligent actions or controlled sequences for navigation
- ✅ **Real-Time Performance**: Agent runs at ~60 FPS with 2.3s VLM inference time using Qwen2-VL-2B-Instruct
- ✅ **Intelligent Behavior**: Agent properly advances through dialogue, navigates menus, and explores the overworld

## Architectural Overview: The Hybrid Hierarchical Controller (HHC)

Our agent uses a **Hybrid Hierarchical Controller (HHC)** that combines programmatic reliability with VLM adaptability. The architecture delegates tasks to specialized controllers based on game context.

### 1. Master Controller (`action.py`)
The master controller orchestrates all decision-making with a priority system:

1.  **Priority 0A: Battle Bot** - Handles combat encounters
2.  **Priority 0B: Opener Bot** - Handles deterministic opening sequence
3.  **Priority 0C: Directive System** - Provides tactical guidance for story progression
4.  **Priority 1: Dialogue Detection** - Handles active dialogue
5.  **Priority 2: Navigation System** - Handles pathfinding with VLM fallback
6.  **Priority 3: VLM Action Selection** - General-purpose decision making

### 2. Specialized Sub-Controllers

#### **Directive System** ✅ OPERATIONAL
- **Status**: Fully implemented and tested
- **Purpose**: Provides tactical guidance between high-level objectives and actions
- **Coverage**: Route 103 rival battle, post-battle dialogue, navigation
- **Key Features**:
  - Position-based state tracking (e.g., battle completion at 9,3)
  - Persistent state flags (battle completion persists after moving)
  - Dialogue priority (completes dialogue before navigating)
  - A* pathfinding integration for obstacle avoidance
- **Competition Compliant**: All actions route through VLM executor

See `docs/DIRECTIVE_SYSTEM.md` for complete documentation.

#### **Opener Bot** ✅ OPERATIONAL
- **Status**: Fully implemented and tested
- **Coverage**: Title screen → starter selection (STARTER_CHOSEN milestone)
- **Architecture**: Programmatic state machine with 20+ states
- **Handoff**: Permanent VLM handoff after exiting Birch's Lab with starter
- **Reliability**: 95%+ success rate, ~60-90 second completion time
- **Key Features**:
  - Dialogue detection and handling (red triangle + text box detection)
  - Story-gate recognition (clock setting, prerequisites)
  - Hybrid approach: Bot handles UI, VLM handles navigation
  - Safety mechanisms (timeouts, attempt limits, loop detection)

See `docs/OPENER_BOT.md` for complete documentation.

#### **Navigation System** ✅ OPERATIONAL
- **Status**: Local BFS pathfinding implemented and tested
- **Algorithm**: Breadth-first search on 15x15 visible tile grid
- **Components**:
  - `_local_pathfind_from_tiles()`: BFS pathfinding engine
  - `_validate_map_stitcher_bounds()`: Stale data detection
  - `goal_parser.py`: Extract goals from strategic plans
  - `location_db.py`: World map connectivity graph
- **Bug Fixes**: Solves "re-entering Birch's Lab" and navigation loops
- **Future**: Full A* pathfinding available in `utils/pathfinding.py` for long-range navigation

See `docs/PATHFINDING_SUMMARY.md` for complete implementation details.

#### **Battle Bot** 🔮 PLANNED
- **Status**: Placeholder implementation
- **Strategy**: Rule-based move selection with type effectiveness
- **Scope**: Sufficient for reaching first gym

### 3. The VLM Integration Strategy

Our architecture uses the VLM strategically rather than relying on it for everything:

- **✅ VLM Strengths**: Navigation decisions, adaptive behavior, general gameplay
- **❌ VLM Weaknesses**: Deterministic sequences, spatial reasoning, dialogue advancement
- **🎯 Our Approach**: 
  - Programmatic control for deterministic tasks (opener, dialogue, battles)
  - VLM for adaptive navigation and general decision-making
  - Hybrid handoff: Programs return `None` to trigger VLM fallback when uncertain

This "Neural Network Executor" pattern satisfies competition rules (final action from neural network) while maximizing reliability.

---

## Development Progress

**November 12, 2025: Directive System Complete**

- ✅ **Tactical Directives**: Implemented ObjectiveManager.get_next_action_directive()
- ✅ **Route 103 Rival Battle**: Navigate to (9,3), interact, trigger battle
- ✅ **Dialogue Integration**: Detect and complete post-battle dialogue
- ✅ **Persistent State**: Battle completion persists after moving away
- ✅ **Bug Fixes**: Solved position oscillation and dialogue detection issues
- ✅ **Testing**: All unit tests passing, integration tests successful

**November 7, 2025: Navigation & Pathfinding Complete**

- ✅ **Local BFS Pathfinding**: Implemented breadth-first search on 15x15 grid
- ✅ **Map Validation**: Stale data detection prevents navigation errors
- ✅ **Goal Extraction**: Parser extracts navigation targets from plans
- ✅ **Bug Fixes**: Solved "re-entering Birch's Lab" navigation bug
- ✅ **Full A* Implementation**: Complete (450 lines) but not currently used

**November 2025: Opener Bot Complete**

- ✅ **State Machine**: 20+ states covering title → starter selection
- ✅ **Story-Gate Handling**: Manages prerequisites like clock setting
- ✅ **STARTER_CHOSEN Handoff**: Permanent VLM takeover after opening
- ✅ **Testing**: All unit tests passing, integration tests successful

**October 11, 2025: Core Agent Operational**

- ✅ **Environment & Baseline**: Successfully set up complete development environment
- ✅ **VLM Integration**: Integrated Qwen2-VL-2B-Instruct model with 16x performance improvement
- ✅ **End-to-End Agent Loop**: Built stable perceive-plan-act loop
- ✅ **Perception System**: Implemented structured JSON extraction with robust error handling
- ✅ **Action System**: Created intelligent action sequencing
- ✅ **Critical Bug Fixes**: Resolved "brain confusion" issues with VLM JSON parsing

**Current Focus**: Implementing Pokemon Center healing and continuing toward first gym.

---

## Key Features

- **🧠 Hybrid Hierarchical Controller:** Master controller delegates to specialized sub-controllers (Battle, Opener, Directive, Navigator) based on game context
- **🎯 Directive System (OPERATIONAL):** Tactical guidance for story progression with persistent state tracking
- **🤖 Opener Bot (OPERATIONAL):** Programmatic state machine handles title → starter selection with 95%+ reliability
- **🗺️ Local BFS Pathfinding (OPERATIONAL):** Navigates around obstacles using 15x15 visible grid  
- **✅ Map Validation:** Detects stale map data and prevents navigation errors
- **⚔️ VLM Integration:** Strategic use for adaptive navigation and general gameplay
- **🎯 Goal-Driven Planning:** Extracts navigation targets from strategic plans
- **📊 Full A* Available:** Complete long-range pathfinding system ready for future use
- **🛡️ Robust Error Handling:** Safety mechanisms prevent loops and handle edge cases
---

## Installation

### Prerequisites

- Python 3.10+ with CUDA-compatible GPU recommended
- `mgba` system library for game emulation
- Legally obtained Pokemon Emerald ROM

### Setup Steps

1. **Clone the Repository**
```bash
git clone <your-repo-url>
cd pokeagent-speedrun
```

2. **Install Dependencies**
```bash
# Install uv package manager if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install all dependencies
uv sync
```

3. **Install System Dependencies**
```bash
# Ubuntu/Debian
sudo apt-get install libmgba-dev

# macOS (with Homebrew)
brew install mgba
```

4. **Add Pokemon Emerald ROM**
Place your legally obtained `rom.gba` file in the `Emerald-GBAdvance/` directory.

For detailed setup instructions, see `docs/STARTERKIT_README.md`.

---

## Running the Agent

### Quick Start

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the agent in autonomous mode
python run.py --agent-auto
```

This launches Pokemon Emerald and starts the AI agent, which will:
1. Perceive the game screen using the VLM
2. Make intelligent decisions based on the current context
3. Execute actions or action sequences
4. Continue the perceive-plan-act loop autonomously

### Available Modes

- `--agent-auto`: Fully autonomous operation (recommended)
- Manual controls available: Tab=Cycle Mode, Space=Agent Step, M=Show State

### Performance Metrics

When running, you'll see real-time metrics:
- Server FPS: Game execution speed (~60-80 FPS target)
- VLM inference time: ~2.3s for perception processing
- Action queue status and step counts

---

## Model Training & Development

### VLM Perception Training

The perception system uses a fine-tuned Qwen2-VL model. While we currently use the base model for optimal performance, you can retrain with:

```bash
python train_perception_vlm.py \
    --dataset_path data/perception_seed.jsonl \
    --model_id "Qwen/Qwen2-VL-2B-Instruct" \
    --output_dir models/perception_custom
```

### Testing & Validation

```bash
# Test perception system
python test_perception_gpu.py

# Test default configuration
python tests/test_default_config.py
```

---

## Competition Context & Strategy

This agent is being developed for **Track 2 (RPG Speedrunning)** of the NeurIPS 2025 PokéAgent Challenge. The primary goal is to achieve the highest **Raw Performance**, measured by milestone completion percentage and efficiency (time and actions).

### New Ranking Criteria (Updated Oct 19th, 2025)
The competition recently clarified that the main leaderboard rankings are determined **solely by objective Raw Performance metrics**. The previously mentioned scaffolding penalty (λ) has been removed from the main ranking calculation.

### Our Strategy for Success
Our architecture is designed to maximize Raw Performance while also showcasing innovation for the separate **Judges' Choice Awards**:

1.  **Maximize Speed & Milestones:** Our hierarchical planning and RL-based control systems aim to find and execute the fastest possible routes through the game's milestones. The focus is on efficient decision-making and execution.
2.  **Demonstrate Innovation:** While not directly impacting the main rank, our learning-based components (VLM Perception, potential RL Memory Management) showcase novel AI capabilities that align with the spirit of the Judges' Choice awards for innovative methods.
3.  **Methodology Documentation:** We will still thoroughly document our approach, including scaffolding dimensions, to be eligible for the Judges' Choice awards.

### Evaluation Metrics

Submissions are ranked on **Adjusted Performance**, which balances:
- **Raw Performance**: Speed, milestone completion, and efficiency
- **Scaffolding Penalty**: Reduced scores for excessive human-provided knowledge or external tools

### Our Competitive Advantages

Our architecture is designed to maximize Adjusted Performance by:

1. **Minimal Scaffolding**: Uses base VLM models with learned capabilities rather than extensive human-coded knowledge
2. **Autonomous Decision Making**: No human-in-the-loop feedback during execution
3. **Efficient Architecture**: Real-time performance suitable for speedrunning requirements
4. **Robust Operation**: Intelligent fallback systems prevent crashes and ensure progress

### Current Capabilities (as of Nov 4th)

The agent is undergoing a planned pivot to a Hybrid Hierarchical Controller architecture to maximize Raw Performance.

- ✅ **Dialogue & Perception:** VLM-based dialogue detection is now reliable.
- 🚧 **Navigation:** VLM-based navigation has been proven unreliable (gets stuck in cul-de-sacs). **Currently implementing A\* programmatic pathfinder.**
- 🚧 **Game Opening:** VLM-based agent fails at opening menus/naming. **Currently implementing programmatic "Opener Bot".**
- 🔄 **Strategic Planning:** Programmatic `ObjectiveManager` is complete and provides high-level goals.

---

## Documentation

- `docs/ARCHITECTURAL_BLUEPRINT.md` - Detailed technical architecture and design philosophy
- `docs/PROJECT_PLAN.md` - Development timeline and milestones
- `docs/STARTERKIT_README.md` - Original starter kit setup instructions
- `docs/MODEL_COMPATIBILITY_GUIDE.md` - Model configuration and compatibility notes

## Contributing

This project is under active development for the NeurIPS 2025 competition. See the project plan for current development priorities and upcoming milestones.

---

## License

Based on the official PokéAgent Challenge starter kit. See `LICENSE` for details.