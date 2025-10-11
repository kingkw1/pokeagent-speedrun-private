Of course. A well-written README is crucial for documenting our progress and guiding the project. Based on a comprehensive review of all the documents you've provided—from the competition rules to our own architectural blueprint—I've drafted a new `README.md` file for our project.

This version preserves the essential setup instructions from the starter kit but prominently features our unique, sophisticated architecture and clearly states our project's current status.

-----

Here is the draft for your new `README.md`:

# Hierarchical Agent for the PokéAgent Speedrunning Challenge

[cite\_start]This repository contains the development of a sophisticated, hierarchical AI agent designed to compete in **Track 2 (RPG Speedrunning)** of the NeurIPS 2025 PokéAgent Challenge[cite: 6, 431]. [cite\_start]Our goal is to build a highly autonomous agent that can complete Pokémon Emerald by optimizing for the competition's "Adjusted Performance" metric, which rewards both speed and low reliance on human-provided scaffolding[cite: 503, 504, 505, 506, 507].

This project is built upon the official starter kit but features a custom, learning-driven architecture as detailed in our `ARCHITECTURAL_BLUEPRINT.md`.

\<hr\>

## Architectural Overview

Our agent moves beyond the baseline implementation by employing a two-layer hierarchical command structure, a VLM-based perception system focused on structured data extraction, and a phased training protocol designed to build capabilities incrementally.

### 1\. Hierarchical Command Structure

To tackle the long-horizon nature of an RPG, our agent separates high-level strategy from low-level execution.

  * **High-Level Planner:** A fine-tuned Large Language Model (LLM) that acts as the strategic brain. It receives context from the perception and memory modules to decide on the next major subgoal, such as `"NAVIGATE_TO: OLDALE TOWN"`.
  * **Low-Level Controller:** A goal-conditioned reinforcement learning policy trained to execute the subgoals issued by the planner. It handles the tactical, moment-to-moment actions like navigation and interaction.

### 2\. Advanced VLM Perception

The agent's "vision" is powered by a fine-tuned Vision-Language Model (VLM). Instead of producing simple text descriptions, our perception module is trained to perform **image-to-structure translation**, outputting a structured JSON object that represents the complete, multi-modal game state from raw pixels. This provides rich, machine-readable data for all other modules.

### 3\. Active Memory Management

To handle a game that spans hours, our blueprint includes a hybrid memory system managed by a dedicated RL agent (the Memory Management Agent, or MMA). This system learns what to remember, what to forget, and what to retrieve to support the planner's decisions, overcoming the context-window limitations of standard models.

\<hr\>

## Project Status

As of **Saturday, October 11, 2025**, this project has successfully completed Week 1 of the development plan: **The Skeleton Agent**.

  * **✅ Foundation & De-Risking Complete:** We have a stable, end-to-end agent loop that can perceive the game, make a decision, and execute an action without crashing.
  * **✅ Perception Pipeline Validated:** We have successfully fine-tuned a VLM (`Qwen/Qwen2-VL-Instruct`) on a custom dataset and integrated it into the perception module, achieving a **12x performance improvement** over initial models.
  * **✅ Now Entering Week 2:** We are now beginning the implementation of the scripted planner and the training of the low-level navigation controller.

\<hr\>

## Features

This agent builds upon the starter kit with several unique architectural features:

  * **Hierarchical Planner:** A two-layer system for strategic and tactical decision-making.
  * **Structured JSON Perception:** A fine-tuned VLM that extracts a rich, semantic state from raw game frames.
  * **RL-Managed Memory:** A planned memory system that learns to store and retrieve relevant information over long time horizons.
  * **Phased Training Protocol:** A structured curriculum for incrementally building the agent's skills.
  * **Performance-Tuned:** Utilizes smaller, faster VLM models (`Qwen/Qwen2-VL-Instruct`) for near-real-time inference.
  * **Modular & Extensible:** Built on the starter kit's four-module architecture (Perception, Planning, Memory, Action).

\<hr\>

## Installation

Installation follows the standard procedure from the starter kit.

### 1\. Clone the Repository

```bash
git clone <your-repo-url>
cd pokeagent-speedrun
```

### 2\. Set Up Environment

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

### 3\. Install System Libraries & ROM

Follow the instructions in the original `STARTERKIT_README.md` to install the `mgba` system library and place your legally-obtained Pokémon Emerald ROM in the `Emerald-GBAdvance/` directory.

\<hr\>

## Running the Agent

The agent is designed to run in a fully autonomous mode.

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the agent with our fine-tuned local model
python run.py --agent-auto
```

This will launch the game and the agent, which will then begin executing its perceive-plan-act loop.

\<hr\>

## Training the Perception Model

A key part of our project is the fine-tuning of the VLM. This process is managed by the `train_perception_vlm.py` script.

**1. Prepare Data:**
Create a `.jsonl` file where each line contains an `image_path` and a corresponding `json_string` representing the desired structured output.

**2. Run Training:**

```bash
python train_perception_vlm.py \
    --dataset_path data/perception_seed.jsonl \
    --model_id "Qwen/Qwen2-VL-Instruct" \
    --output_dir models/perception_v0.2_qwen
```

**3. Test the Model:**
Use the `test_perception_gpu.py` script to evaluate the performance and accuracy of your newly trained model checkpoint.

\<hr\>

## Competition Context

[cite\_start]This agent is being developed for Track 2 of the PokéAgent Challenge, which focuses on speedrunning Pokémon Emerald[cite: 431, 432]. [cite\_start]Final rankings are based on **Adjusted Performance**, a metric that rewards high milestone completion and fast times while penalizing reliance on human-provided knowledge or "scaffolding"[cite: 503, 504, 505, 506, 507]. Our architecture is explicitly designed to minimize this penalty by learning key cognitive functions like planning and memory management.