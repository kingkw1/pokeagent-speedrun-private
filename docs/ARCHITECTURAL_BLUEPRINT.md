# An Architectural Blueprint for a Competitive Agent in the PokéAgent RPG Speedrunning Challenge: A Hierarchical, Memory-Augmented Approach

## Section 1: Deconstructing the Long-Horizon Challenge: RPG Speedrunning as a Frontier Problem in AI


The task of speedrunning a complex Role-Playing Game (RPG) represents a significant frontier challenge for artificial intelligence. It encapsulates a class of problems characterized by extremely long-time horizons, vast state-action spaces, and exceptionally sparse reward signals. Framing this challenge within a formal structure is essential for developing a robust and competitive agent. This section deconstructs the problem, establishes the theoretical context, and justifies the necessity of a sophisticated architecture that moves beyond conventional reinforcement learning paradigms.


### 1.1 The Nature of the Problem: Sparse Rewards and Vast State-Action Spaces


From a theoretical standpoint, an RPG environment can be modeled as a Goal-Conditioned Markov Decision Process (GMDP).1 In this framework, the agent's objective is to learn a policy, π, that maximizes the expected cumulative reward for reaching a final goal state, gfinal​, from any given starting state, s0​. However, the specific nature of RPG speedrunning introduces several acute challenges that render standard deep reinforcement learning (RL) methods ineffective.
The primary obstacle is the extreme sparsity of rewards. In an RPG like Pokémon, meaningful rewards—such as defeating a gym leader, acquiring a key item like a bicycle, or clearing a major story milestone—are separated by thousands, or even tens of thousands, of low-level actions (e.g., walking, battling low-level wild Pokémon, navigating menus). This temporal distance makes the credit assignment problem—attributing a distant positive outcome to the specific sequence of actions that caused it—nearly impossible for "flat" RL algorithms. An agent might wander aimlessly for hours without receiving any positive feedback, making efficient learning intractable.
Compounding this is the long-horizon nature of the task. A full playthrough constitutes a single, massive episode. This exacerbates the sparse reward problem and places an immense burden on the agent's ability to plan and remember information over extended periods.1 An agent must recall, for instance, that an NPC in the first town gave a clue relevant to a puzzle in the fifth town, an interaction that may have occurred hours earlier in gameplay.
Finally, the overall objective of "beating the game" possesses a natural hierarchical structure.2 This high-level goal decomposes into a sequence of major sub-goals (e.g., "obtain the first badge," "traverse Mt. Moon," "defeat Team Rocket at Silph Co."), which in turn break down into smaller sub-tasks (e.g., "navigate to the gym," "defeat the gym's trainers," "solve the gym's puzzle"). Flat RL agents, which operate on the level of primitive actions, are incapable of recognizing or exploiting this hierarchical structure, leading to inefficient and strategically naive behavior.
A critical realization is that the game's state space is fundamentally multi-modal and only partially observable. A purely visual perception system, such as a standard Convolutional Neural Network (CNN), is insufficient because it treats all pixels with equal importance. In an RPG, a single pixel within a dialogue box containing a critical quest instruction holds far more semantic weight than a pixel of grass in the overworld. The true state is a composite of visual information (character positions, map layout), textual information (dialogue, item descriptions, menu options), and, crucially, latent variables that are not displayed on screen. These latent variables, such as internal quest flags or the status of a specific event trigger, must be inferred from the history of interactions. This necessitates a perception module capable of reading and comprehending text and a memory system that can track this history to build a complete model of the world state.


### 1.2 Interpreting the Evaluation Metrics: Raw Performance & Judges' Choice Awards

Based on the competition framework (updated October 19th, 2025), submissions for Track 2 are evaluated primarily on **Raw Performance**, with separate consideration for **Judges' Choice awards** based on methodology.

**Primary Ranking: Raw Performance**
The main leaderboard rank is determined solely by objective metrics:
1.  **Milestone Completion:** Percentage of game milestones achieved.
2.  **Completion Efficiency:** Time and action count required to reach milestones.
3.  **Reproducibility:** Ability for organizers to verify the run.

This metric rewards agents that find and execute the most efficient path through the game, prioritizing speed and progress above all else.

**Secondary Recognition: Judges' Choice Awards**
Separate awards recognize innovative approaches, including those with minimal scaffolding, creative tool use, or novel architectures. To be eligible, teams must document their methodology, detailing the support structures used across five dimensions: State Information (S), Tools (T), Memory (M), Feedback (F), and Fine-tuning (Φ).

**Our Strategic Alignment:**
This evaluation structure requires a two-pronged approach:
1.  **Maximize Raw Performance:** Our architecture must prioritize speed and milestone completion through efficient planning and execution.
2.  **Showcase Innovation:** Our learning-based components should be highlighted in the methodology documentation to compete for Judges' Choice awards.

The architecture proposed in this report is designed to excel at Raw Performance through its hierarchical structure and optimized components, while its learning-based elements position it well for the innovation awards.

#### 1.2.1 Alignment with Competition Framework and Optimizing for Adjusted Performance

The competition framework provides critical validation of our proposed architecture. The organizers have provided a baseline agent with a modular architecture consisting of Perception, Planning, Memory, and Action components. Our blueprint represents a sophisticated, learning-driven implementation of this exact structure, positioning us perfectly to satisfy the **Submission Originality Requirements**.

Our approach addresses each component with "novel approaches" and "meaningful modifications":

- **Perception**: Beyond basic VLM usage, we propose structured fine-tuning regimens to achieve true in-game literacy
- **Planning**: We replace simple planning with a two-layer Hierarchical RL system where the high-level planner is an LLM fine-tuned with guidance-aware RL  
- **Memory**: We elevate simple memory storage to an active, intelligent system managed by its own RL agent

**Optimizing Each Component of the Adjusted Performance Metric:**

*Maximizing Raw Performance:*
The raw metrics focus on milestone completion, time, and action count. Our hierarchical structure is purpose-built for this optimization. The high-level LLM planner focuses on finding the optimal sequence of major milestones (the "critical path" of the speedrun), while the offline-trained, low-level controller executes these subgoals with maximum efficiency.

*Minimizing the Scaffolding Penalty:*
Our architecture thoughtfully addresses each scaffolding dimension:

- **State Information (S)**: Our VLM-based perception works from raw pixels (lowest penalty input). By fine-tuning the VLM to extract structured state, we create an autonomous capability rather than relying on hand-coded parsers or emulator cheats.

- **Tools (T)**: Our agent avoids real-time external tools. The "skill graph" derived from game wikis is an offline pre-computation step—a common ML practice that should incur lower penalty than live dependencies.

- **Memory (M)**: While vector databases and knowledge graphs are listed as scaffolding, our key innovation is the Memory Management Agent (MMA) that learns to use memory via reinforcement learning. This transforms static external support into a novel, autonomous cognitive function.

- **Feedback (F)**: Our training protocol avoids human-in-the-loop feedback during evaluation, making the final agent fully autonomous.

- **Fine-tuning (FT)**: While fine-tuning incurs penalties, our advantage lies in our principled, phased training protocol that builds capabilities from the ground up through a full RL curriculum, demonstrating deep commitment to learning rather than simple model adaptation.


### 1.3 Why Baseline Approaches are Insufficient


A plausible baseline architecture for this task might consist of a CNN for visual feature extraction, a recurrent network like a Long Short-Term Memory (LSTM) unit to handle temporal dependencies, and a standard model-free deep RL algorithm like Proximal Policy Optimization (PPO) to output actions.
This approach, while straightforward to implement, is fundamentally ill-equipped for the complexities of RPG speedrunning:

1. **Perception**: A CNN perceives pixels, not semantics. It cannot read text, understand the structure of a menu, or distinguish between a friendly NPC and a rival trainer without extensive, brittle, post-processing logic.

2. **Memory**: An LSTM's memory is notoriously unstable over very long time horizons. It struggles to retain specific, critical pieces of information for thousands of steps and is prone to catastrophic forgetting. It provides a compressed history, not a queryable database of past events.

3. **Planning**: A flat PPO policy is purely reactive. It learns a mapping from the current state (or a short history of states) to an action. It has no mechanism for long-term, goal-directed planning and cannot reason about the hierarchical structure of the task. It would be forced to re-discover the path from Pallet Town to Viridian City every time, rather than treating "navigate to Viridian City" as a reusable skill.
To be competitive, an agent must move beyond this reactive paradigm. It requires a system that can comprehend the multi-modal game state, formulate and execute hierarchical plans, and maintain a persistent, structured memory of its journey.


## Section 2: The Hierarchical Command Structure: Strategic Planning and Tactical Execution


To overcome the limitations of flat RL, the core of the proposed agent is a two-layer decision-making engine based on the principles of Hierarchical Reinforcement Learning (HRL). This structure mimics human cognition by separating high-level strategic planning from low-level tactical execution. This decomposition is the most effective paradigm for managing temporal abstraction, enabling efficient exploration, and promoting skill reuse in long-horizon tasks.1 By breaking a daunting problem like "beat the game" into a manageable sequence of shorter-term subgoals, the agent can reason at multiple levels of granularity, focusing on proximal objectives without being overwhelmed by the final, distant goal.1


### 2.1 The Case for Hierarchy


The primary advantage of an HRL framework is its ability to introduce temporal abstraction. A high-level policy can issue a single command, such as "acquire the first gym badge," which triggers a low-level policy to execute a long sequence of primitive actions over hundreds or thousands of time steps. This simplifies the planning problem for the high-level policy, as it can operate in a more abstract and temporally compressed state-action space. Furthermore, this modular structure fosters the development of reusable skills.2 A low-level policy trained to navigate to a specific coordinate can be invoked by the high-level planner for countless different tasks, from visiting a Poké Mart to entering a rival's house. This compositionality is key to scaling learning to complex, multi-stage problems.4
The proposed architecture embodies a powerful hybrid of symbolic and sub-symbolic reasoning. Traditional RL operates in a sub-symbolic space, learning a direct mapping from high-dimensional state representations (like pixels) to low-level actions, but it lacks an understanding of abstract concepts. In contrast, Large Language Models (LLMs) excel at symbolic reasoning and possess vast common-sense knowledge but are not inherently grounded in an environment and cannot execute actions. The proposed architecture bridges this divide. The high-level LLM planner formulates a strategic, symbolic plan (e.g., "I need to heal my Pokémon at the Pokémon Center"). The HRL framework then translates this symbolic directive into a sequence of sub-symbolic policies executed by the low-level controller (navigating to the building, entering, and interacting with the nurse). This synergy leverages the strategic prowess of LLMs and the reactive efficiency of RL, creating a system far more capable than either paradigm in isolation.8


### 2.2 The High-Level Planner: A Programmatic, Milestone-Driven System

Given the VLM's unreliability in complex, multi-step reasoning and the hard 12-day deadline, we have pivoted from a fully VLM-based planner to a more robust and reliable **programmatic, milestone-driven planner**.

This planner is implemented as the `ObjectiveManager` module. Its architecture consists of a hard-coded list of all critical-path milestones required to complete the competition (up to the first gym), derived from the official splits.

At each step, this module:
1.  Receives the current `milestones` from the `state_data`.
2.  Compares this against its internal list of objectives.
3.  Determines the *first incomplete objective* in the sequence.
4.  Provides this single, unambiguous strategic goal (e.g., `"story_route_101"`) to the rest of the agent.

This "hard-scripted subgoal" approach ensures the agent is *always* focused on the correct high-level task and provides a stable, predictable foundation for our low-level controllers. This is a form of "Tool" use that is explicitly allowed by the new rules to maximize **Raw Performance**.

### 2.3 The Low-Level Controller: A Hybrid Hierarchical Controller (HHC)

Our original plan to train a goal-conditioned RL policy for navigation proved to be infeasible due to the VLM's core reasoning failures and the 12-day time limit. We have pivoted to a more robust **Hybrid Hierarchical Controller (HHC)**.

This HHC is implemented in the main `action.py` module, which acts as a "master controller." On every step, it delegates the task to one of three specialized sub-controllers based on the current game state and strategic objective:

1.  **Programmatic "Opener Bot":** This is a rule-based state machine that handles the entire deterministic opening sequence (Splits 0-4). It programmatically executes all actions for the title screen, character naming, setting the clock, exiting the van/house, and winning the first rival battle. This ensures 100% reliability and maximum speed on the competition's early milestones.

2.  **Programmatic "Battle Bot":** This is a simple, rule-based module that takes control whenever `game_state == 'battle'`. It uses effective logic (e.g., "select first super-effective move") to win all required battles to reach the first gym.

3.  **The "A\* Navigator" (Programmatic + VLM Executor):** This is our solution to the VLM's "cul-de-sac" and spatial reasoning failures.
    * **Pathfinding (Tool):** We use a programmatic **A\*** (A-Star) pathfinding algorithm as a "Tool". This tool reads the 100% reliable ASCII map grid from the `MapStitcher` and calculates the optimal (x,y) path to the destination provided by the `ObjectiveManager`.
    * **Executor (Neural Network):** The VLM's job is demoted from "navigator" to "executor." It is fed a simple prompt like, "Your current position is (10,10). The next step on your path is (10,11). What is the one button you should press?" The VLM's only task is to translate this coordinate-step into `DOWN`.

This hybrid architecture satisfies the "final action from a neural network" rule while guaranteeing reliable, fast, and optimal navigation, maximizing our **Raw Performance** score.
	

## Section 3: Advanced Perception: A Vision-Language Model for Semantic State Extraction


The agent's ability to make intelligent decisions is fundamentally constrained by the quality of its perception. This section proposes a paradigm shift from treating perception as simple feature extraction to treating it as comprehensive state comprehension. This is achieved by employing a Vision-Language Model (VLM) as the agent's "eyes and ears," enabling it to extract a rich, structured, and semantic representation of the game state from raw pixels.


### 3.1 The Limitations of Convolutional Vision


As established, a standard CNN is inadequate for parsing the complex and multi-modal interface of an RPG. While it can learn to recognize spatial patterns, it cannot natively read text from dialogue boxes, interpret the numerical values in a stat menu, or understand the symbolic meaning of icons on a town map.11 Any attempt to use a CNN for these tasks would require a cascade of brittle, hand-engineered post-processing modules (e.g., separate OCR systems, UI element detectors), which would be difficult to maintain and would likely incur a significant scaffolding penalty.


### 3.2 VLM as a Universal Game State Parser


The proposed solution is to use a pre-trained VLM, such as an open-source model based on modern architectures like Llama 3.2 Vision 12, as the core of the perception module. The VLM's task is framed as image-to-structure translation, a concept inspired by the Image2Struct framework.13 Given a raw screenshot of the game, the VLM is prompted to output a structured JSON object that represents the complete, multi-modal game state. This approach is supported by a growing body of research demonstrating the potential of LVLMs to perform detailed perception and reasoning in game environments.11
An example of the VLM's target output for a typical overworld screen might be:

```json
{
  "screen_context": "overworld",
  "player_location": {
    "map_name": "Route 1",
    "coordinates": {"x": 15, "y": 22}
  },
  "player_party": [
    {"name": "Pikachu", "level": 7, "hp_current": 22, "hp_max": 22, "status": "healthy"}
  ],
  "visible_entities": [
    {"type": "npc", "classification": "youngster", "is_interactive": true}
  ],
  "on_screen_text": null,
  "menu_state": "closed"
}
```

This structured output provides a rich, semantic, and immediately machine-readable representation of the world state. It disentangles the raw visual data from its meaning, allowing the planning and memory modules to operate on abstract concepts rather than raw pixels. This decoupling of perception from policy learning is a cornerstone of robust and modular agent design. In a traditional end-to-end model, the policy network must learn to see, understand, and act all at once, creating a monolithic and brittle system. With a modular VLM, the perception component can be fine-tuned or even replaced independently of the decision-making components. This makes the system more adaptable—for example, to a different version of the game with an updated UI—and vastly more interpretable, as the JSON output can be directly inspected to debug perception errors.7


### 3.3 Fine-Tuning the VLM for In-Game Literacy


While powerful, a general-purpose VLM must be fine-tuned to master the specific visual grammar and terminology of the Pokémon game world. This requires a specialized dataset and a structured training regimen.
**Data Collection**: A dataset of (screenshot, structured_json) pairs must be created. This process can be semi-automated. By running the game in an emulator, one can programmatically access the game's RAM to read the ground-truth state variables (player coordinates, party stats, quest flags, etc.). This ground-truth data can then be formatted into the target JSON structure and paired with the corresponding screenshot captured from the emulator at that exact moment.

**Progressive Learning**: A multi-stage fine-tuning strategy, similar to the one used for the CombatVLA model, should be employed to gradually increase the model's capabilities:

- **Stage 1: Coarse-Grained Context Tuning** - The initial training phase focuses on high-level scene understanding. The VLM learns to classify the screen into broad categories like "overworld," "battle," "menu," or "dialogue."

- **Stage 2: Fine-Grained Entity Tuning** - Once the model can identify the context, it is trained on the more difficult task of detailed entity extraction. This involves accurately performing OCR on text, parsing numerical values like HP and level, identifying specific items in the inventory, and extracting the positions of characters on the screen. This stage hones the model's ability to process complex layouts and extract key-value pairs from semi-structured data, a known challenge for vision models.
This systematic fine-tuning process will equip the agent with a highly accurate and reliable perception system, forming a solid foundation for all subsequent reasoning and planning.


## Section 4: A Pragmatic Memory System for a 12-Day Sprint

Given the 12-day timeframe and the competition's focus on the first gym, the original plan for a complex, RL-based "Memory Management Agent (MMA)" is no longer our primary path.

Instead, we are implementing a highly effective, two-part memory system sufficient for this sprint:

1.  **Strategic Memory (Persistent Objectives):** The agent's long-term "memory" is managed by the `ObjectiveManager`. By tracking which milestones are complete, the agent always knows its precise location in the overall story arc.

2.  **Tactical Memory (Rolling Buffer):** The `memory.py` module maintains a simple rolling buffer (a `deque`) of the last 50 observations and actions. This provides the VLM with immediate context of its recent actions, which is primarily used by our anti-loop safety systems.

This two-part system provides all necessary memory for completing the first gym, aligning with our focus on **Raw Performance** and rapid implementation.

## Section 5: System Integration and a Phased Training Protocol


The individual components—perception, planning, and memory—must be integrated into a cohesive system and trained in a structured, methodical manner. Attempting to train such a complex, multi-component agent end-to-end from scratch is computationally infeasible and highly susceptible to training instability. Therefore, a phased, curriculum-based training protocol is proposed to manage this complexity and build the agent's capabilities incrementally.


### 5.1 The Full Agent Loop (Perceive-Remember-Plan-Act)


The integrated agent operates in a continuous loop, with each component playing a distinct role in the decision-making process:

1. **Perceive**: At each time step t, the VLM captures a screenshot from the emulator and translates it into a structured JSON state, S_t.

2. **Remember**: The Memory Management Agent (MMA) receives S_t. It updates the Working Memory with this new information and, based on its learned policy, executes a memory operation. This may involve writing new information to long-term memory or retrieving relevant context, M_t, from the Episodic or Semantic stores.

3. **Plan**: The High-Level Planner (LLM) receives the augmented context, which consists of the current state and the retrieved memory context, (S_t, M_t). It analyzes this information and generates the next high-level subgoal, G_high.

4. **Act**: The Low-Level Controller receives the current state S_t and the subgoal G_high. It then executes a sequence of primitive actions, a_t, a_{t+1}, ..., until G_high is achieved, a timeout is reached, or the planner issues a new subgoal.

5. This loop repeats, allowing the agent to continuously perceive its environment, update its understanding of the world, formulate plans, and execute actions.


### 5.2 A Practical, 12-Day Implementation Sprint

Our original, long-term training protocol has been replaced by a 12-day high-urgency sprint (starting Nov 3) focused on implementing our Hybrid Hierarchical Controller. The "Phased Training" has become a "Phased Implementation":

* **Phase 1 (Days 1-2): Programmatic Controllers.** Build the "Opener Bot" and "Battle Bot" to solve the deterministic parts of the game.
* **Phase 2 (Days 3-4): Navigation Controller.** Build and integrate the A* pathfinding "Navigator" tool and the VLM-executor logic.
* **Phase 3 (Days 5-12): Integration, Testing, & Submission.** Run the full hybrid agent, debug the handoff logic, and generate the final submission runs.

This new plan prioritizes creating a robust, reliable agent capable of completing the competition's defined goal (the first gym) over a complex, learning-based agent that risks failing at basic tasks.


## Section 6: Conclusion: A Roadmap to Competitive Performance


This report has outlined a comprehensive architectural blueprint for a highly competitive agent in the PokéAgent RPG Speedrunning Challenge. By synthesizing state-of-the-art techniques from hierarchical reinforcement learning, vision-language modeling, and active memory management, the proposed design directly addresses the core challenges of long-horizon, sparse-reward decision-making that define this problem domain.


### 6.1 Synthesizing the Hybrid Architecture Advantages

Our final architecture is a pragmatic and powerful **Hybrid Hierarchical Controller (HHC)**. Its competitive edge stems from a clear separation of concerns, delegating tasks to the most reliable controller for the job:

1.  **Semantic Perception**: Our VLM (`Qwen/Qwen2-VL-Instruct`) is used as a fast, reliable "eye" to perform structured JSON extraction and visual dialogue detection.
2.  **Reliable Navigation**: We solve spatial reasoning (the "cul-de-sac" problem) by using a programmatic **A\* Pathfinding Tool** that reads reliable map data. The VLM's role is simplified to a simple "executor," satisfying the rules.
3.  **Maximum Speed & Reliability**: We use **Programmatic Bots** (Opener Bot, Battle Bot) to handle deterministic parts of the game (like the opening sequence) with 100% reliability and maximum speed.
4.  **Strategic Focus**: A persistent, programmatic `ObjectiveManager` acts as the high-level planner, ensuring the agent is always focused on the correct next milestone.

### 6.2 Mapping Innovations to Competitive Metrics

This hybrid architecture is explicitly designed to maximize **Raw Performance** and is a "meaningful modification" eligible for prizes:

-   **Maximizing Raw Performance**: By using programmatic bots and A\* pathfinding, we ensure our agent is as fast and reliable as possible, minimizing time and maximizing milestone completion.
-   **Competing for Judges' Choice Awards**: This HHC architecture is itself a "novel approach". We will document how our master controller in `action.py` intelligently "tools" (T) by delegating to different sub-controllers (programmatic bots, A\*, VLM) based on the game state.
-   **Originality and Contribution**: This architecture is a non-trivial, original implementation that goes far beyond the baseline. It satisfies the "neural network" requirement in the most intelligent way possible: using the VLM for the tasks it's good at (perception) while scaffolding it with programmatic tools (A\*, bots) for the tasks it fails at (spatial reasoning, deterministic sequences).


### 6.3 Final Recommendations and Future Work


For the participant, the immediate path forward is to begin with Phase 1: data collection and the fine-tuning of the VLM, as this perception module is the bedrock of the entire system. Concurrently, the generation of the offline gameplay dataset for Phase 2 can commence.
Beyond this competition, the proposed architecture serves as a generalizable framework for creating autonomous agents capable of tackling a wide range of complex, long-horizon tasks in interactive environments. Future work could explore its application to other RPGs to test for generalization, its extension to multi-agent scenarios, or the integration of more advanced world models within the hierarchical planning loop. Ultimately, this blueprint offers not just a strategy for winning a competition, but a principled approach to building more capable and intelligent artificial agents.
## Works Cited
1. (PDF) Reinforcement Learning with Anticipation: A Hierarchical ..., accessed October 9, 2025, https://www.researchgate.net/publication/395355057_Reinforcement_Learning_with_Anticipation_A_Hierarchical_Approach_for_Long-Horizon_Tasks/download
2. Hierarchical Reinforcement Learning: A Survey and Open Research Challenges - MDPI, accessed October 9, 2025, https://www.mdpi.com/2504-4990/4/1/9
3. Guide to Control: Offline Hierarchical Reinforcement ... - IJCAI, accessed October 9, 2025, https://www.ijcai.org/proceedings/2023/0469.pdf
4. Hierarchical and compositional reinforcement learning for autonomous systems, accessed October 9, 2025, https://repositories.lib.utexas.edu/items/d80d2c3a-333b-41b7-92ce-9c74b97081df
5. accessed December 31, 1969, uploaded:Track 2_ RPG Speedrunning - PokéAgent Challenge.pdf
6. Towards a Hierarchical Taxonomy of Autonomous Agents - at Illinois, accessed October 9, 2025, http://osl.cs.illinois.edu/media/papers/tosic-2004-smc-towards_a_hierarchical_taxonomy_of_autonomous_agents.pdf
7. Hierarchical Agents - Orases, accessed October 9, 2025, https://orases.com/ai-agent-development/hierarchical-agents/
8. Skill Reinforcement Learning and Planning for Open-World Long-Horizon Tasks | OpenReview, accessed October 9, 2025, https://openreview.net/forum?id=NY3HzOOL3u
9. World-Model based Hierarchical Planning with Semantic Communications for Autonomous Driving | OpenReview, accessed October 9, 2025, https://openreview.net/forum?id=HyS9pkHNTN
10. Plan Then Action:High-Level Planning Guidance Reinforcement Learning for LLM Reasoning - ResearchGate, accessed October 9, 2025, https://www.researchgate.net/publication/396142386_Plan_Then_ActionHigh-Level_Planning_Guidance_Reinforcement_Learning_for_LLM_Reasoning
11. Are Large Vision Language Models Good Game Players? - arXiv, accessed October 9, 2025, https://arxiv.org/html/2503.02358v1
12. Information Extraction with Vision Models | by Chetankumar Khadke - Medium, accessed October 9, 2025, https://khadkechetan.medium.com/information-extraction-with-vision-models-238b347ae8e6
13. NeurIPS Poster Image2Struct: Benchmarking Structure Extraction for Vision-Language Models, accessed October 9, 2025, https://neurips.cc/virtual/2024/poster/97829
14. Are Large Vision Language Models Good Game Players? - OpenReview, accessed October 9, 2025, https://openreview.net/forum?id=c4OGMNyzPT
15. VGBench: Evaluating Vision-Language Models in Real-Time Gaming Environments, accessed October 9, 2025, https://www.getmaxim.ai/blog/vgbench-evaluating-vision-language-models-in-real-time-gaming-environments/
16. CombatVLA: An Efficient Vision-Language-Action Model for Combat Tasks in 3D Action Role-Playing Games - arXiv, accessed October 9, 2025, https://arxiv.org/html/2503.09527v1
17. MemAgent: Reshaping Long-Context LLM with Multi-Conv RL ..., accessed October 9, 2025, https://www.alphaxiv.org/overview/2507.02259v1
18. [2508.19828] Memory-R1: Enhancing Large Language Model Agents to Manage and Utilize Memories via Reinforcement Learning - arXiv, accessed October 9, 2025, https://arxiv.org/abs/2508.19828
19. Breaking the Context Window: Building Infinite Memory for AI Agents : r/Rag - Reddit, accessed October 9, 2025, https://www.reddit.com/r/Rag/comments/1n9680y/breaking_the_context_window_building_infinite/
20. AI-Native Memory: The Emergence of Persistent, Context-Aware “Second Me” Agents, accessed October 9, 2025, https://ajithp.com/2025/06/30/ai-native-memory-persistent-agents-second-me/
21. MemAgent shows how reinforcement learning can turn LLMs into long-context reasoning machines—scaling to 3.5M tokens with linear cost. - Reddit, accessed October 9, 2025, https://www.reddit.com/r/machinelearningnews/comments/1m49mnt/memagent_shows_how_reinforcement_learning_can/
22. Look Back to Reason Forward: Revisitable Memory for Long-Context LLM Agents - arXiv, accessed October 9, 2025, https://arxiv.org/html/2509.23040v1
23. Hierarchical Planning for Autonomous Parking in Dynamic Environments - ResearchGate, accessed October 9, 2025, https://www.researchgate.net/publication/378530072_Hierarchical_Planning_for_Autonomous_Parking_in_Dynamic_Environments
24. Multiresolution Path Planning for Autonomous Agents - Dynamics and Control Systems Laboratory - Georgia Institute of Technology, accessed October 9, 2025, https://dcsl.gatech.edu/research/multires-pp.html
25. accessed December 31, 1969, uploaded:Official Rules - PokéAgent Challenge.pdf