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


### 2.2 The High-Level Planner: A Language Model as Strategic Navigator


A novel and powerful approach is to instantiate the high-level planner using a fine-tuned LLM. This leverages the immense world knowledge and sophisticated reasoning capabilities of modern language models for strategic decision-making.8
The planner's architecture will consist of an LLM that takes as input the structured game state (produced by the perception module described in Section 3) and relevant context from the long-term memory system (Section 4). Its function is to output the next high-level subgoal in a structured format, such as:

```json
{"subgoal": "NAVIGATE_TO", "target": "Pewter City Gym"}
```

or

```json
{"subgoal": "DEFEAT_TRAINER", "target": "Rival Blue"}
```
To provide the planner with a valid set of potential subgoals and a curriculum for learning, an offline process can be used to generate a "skill graph." Inspired by the Plan4MC framework 8, a powerful foundation model like GPT-4 can be prompted to parse online game guides and wikis to extract a dependency graph of major game objectives. This graph establishes the necessary preconditions for major milestones (e.g., you must defeat Brock in Pewter City before you can proceed to Route 3), providing the planner with a structured representation of the game's progression.
The planner will not be a static, prompted model. To ensure its strategies are grounded and effective, it will be fine-tuned using a guidance-aware RL method. A framework like Plan-Then-Action Enhanced Reasoning with Group Relative Policy Optimization (PTA-GRPO) is well-suited for this.10 This approach jointly optimizes two objectives: the ultimate success in achieving the final goal (beating the game) and the quality of the intermediate subgoals (the "guidance"). This process rewards the planner for generating subgoals that are not only strategically sound in the long term but are also achievable by the low-level controller, thus aligning high-level strategy with low-level executability.


### 2.3 The Low-Level Controller: A Goal-Conditioned Policy for Execution


The low-level controller is a goal-conditioned RL policy, denoted as πlow​(action∣state,subgoal). Its sole responsibility is to receive a subgoal from the high-level planner and execute the sequence of primitive game actions (e.g., up, down, left, right, A, B) required to achieve it.
To maximize sample efficiency—a critical concern in a time-limited competition—this controller should be trained using an offline HRL methodology. The Guider algorithm provides an excellent template for this approach. The process involves three key stages:

1. **Offline Data Collection**: A large dataset of gameplay trajectories is collected. This does not need to be optimal gameplay; it can be generated by a simple scripted agent, a random exploration policy, or even by recording human players. The goal is to capture a wide variety of state-action transitions.

2. **Latent Subgoal Pre-training**: The Guider framework uses a latent variable model to learn a distribution of "reachable" subgoals from the offline data. This unsupervised pre-training phase allows the model to discover what constitutes a meaningful and achievable short-term objective within the game world, without requiring any reward signal.

3. **Low-Level Policy Training**: The low-level controller is then trained on this offline dataset to learn a policy that can reliably reach these latent subgoals. This grounds the controller in the dynamics of the environment, making it highly proficient at tactical, short-horizon tasks like navigation and interaction, all without the immense cost of online trial-and-error exploration.
This offline pre-training approach significantly reduces the burden on the online learning phase, allowing the agent to quickly acquire a competent set of basic skills.
| Feature | Hypothesized Baseline Architecture | Proposed Hierarchical Architecture |
|---------|-----------------------------------|-------------------------------------|
| **Planning Module** | Implicit / None (Purely Reactive) | LLM-based High-Level Planner |
| **Action Policy** | Flat RL Policy (e.g., PPO) | Goal-Conditioned Low-Level Controller |
| **Training Paradigm** | Online Reinforcement Learning | Offline HRL (Guider) + Guidance-Aware Online RL (PTA-GRPO) |
| **Key Strengths** | Simple to implement | Strategic decomposition, high sample efficiency, task modularity & reuse |
| **Key Weaknesses** | Poor exploration, no long-term strategy, extremely sample inefficient | Higher implementation complexity, requires large offline dataset |
	

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


## Section 4: An Enduring Memory: An RL-Based System for Long-Term Reasoning


Perhaps the most profound challenge in a long-horizon RPG is memory. An agent's ability to recall past events, learn from its experiences, and build a persistent model of the world is paramount for success. This section details a sophisticated, multi-component memory system that is actively managed by a dedicated reinforcement learning agent, moving far beyond the limitations of simple recurrent networks or the finite context windows of Transformers.


### 4.1 The Catastrophic Failure of Stateless Agents


Modern Transformer-based models, including LLMs, are fundamentally stateless. Their "memory" is confined to their context window. For an RPG playthrough that can last for hours and involve millions of state transitions (and thus, millions of potential tokens of information), relying solely on a context window is computationally and practically impossible.17 Any information that scrolls out of the context window is permanently lost. This necessitates an external, persistent memory architecture that can store and retrieve information over the entire duration of the game.19


### 4.2 A Hybrid Memory Architecture


Inspired by models of human cognition and recent AI research, a three-part hybrid memory system is proposed:

1. **Working Memory ("Scratchpad")**: This is a short-term, high-speed buffer that holds the most recent sequence of structured state representations generated by the VLM. It represents the agent's immediate consciousness and provides the context for moment-to-moment decisions.

2. **Episodic Memory (Vector Database)**: This is a long-term storage system for key events and experiences. Whenever a significant event occurs—such as defeating a gym leader, receiving a key item, or having a critical conversation with an NPC—the structured state and a text summary of the event are embedded into a high-dimensional vector and stored in a vector database. This allows for efficient semantic retrieval of past experiences. The agent can query this memory with natural language questions like, "What did the old man in Viridian City say about catching Pokémon?" to retrieve relevant memories.

3. **Semantic Memory (Knowledge Graph)**: This is a structured database for storing static, factual knowledge about the game world. It can be pre-populated by parsing game wikis and is updated during gameplay. This graph stores entities and their relationships, such as (Pikachu, type, Electric), (Thunder_Shock, learns_at_level, 1), or (Viridian_Forest, connects, Pewter_City). This relational structure allows for more complex, logical queries that are difficult to perform on an unstructured vector store.


### 4.3 The Memory Management Agent (MMA): Learning to Remember and Forget


The central innovation of this memory system is that it is not a passive repository. Instead, it is actively managed by a dedicated Memory Management Agent (MMA). This is a small RL agent, inspired by frameworks like MemAgent 17 and Memory-R1 18, that learns an intelligent policy for what to store, what to update, what to retrieve, and what to ignore.
The MMA is a policy network that, at each significant time step, observes the current game state and the contents of the working memory. It then selects a memory operation from its action space, which includes actions like:

- **WRITE_EPISODIC(event_summary)**: Compresses the current context into a summary and writes it to the vector database.
- **WRITE_SEMANTIC(entity, relation, entity)**: Extracts a new fact and adds it to the knowledge graph.
- **RETRIEVE_EPISODIC(query)**: Forms a query based on the current state and retrieves relevant episodes from the vector database, placing them into the working memory.
- **RETRIEVE_SEMANTIC(query)**: Queries the knowledge graph for factual information relevant to the current context.
- **NO_OP**: Takes no memory action.
This agent is trained using policy gradient reinforcement learning (e.g., PPO, as in Memory-R1 18). The reward signal is derived from the overall task success. A sequence of memory operations is rewarded if it contributes to a trajectory that successfully completes a high-level subgoal. This training process teaches the MMA to make goal-oriented memory decisions. It learns to identify and retain answer-critical information (e.g., "An NPC told me I need the HM 'CUT' to get past this tree") while discarding irrelevant content (e.g., the details of the 50th wild Pidgey encounter). This transforms the agent's memory from a simple storage device into an active component of its reasoning process. It effectively allows the agent to process an arbitrarily long stream of information with linear computational complexity by learning to maintain a compressed, relevant state representation in its fixed-size working memory.17
This approach recognizes that memory is not merely storage; it is an integral part of reasoning. By training the MMA with RL based on task success, the agent learns to perform goal-conditioned retrieval, asking "What information from my entire history is relevant to achieving my current subgoal?". While the removal of the scaffolding penalty from the main ranking reduces the *direct* scoring benefit of a learned memory system, the MMA remains a key innovation. [cite_start]It offers the potential for **superior long-term performance** compared to simpler retrieval methods by learning complex, multi-hop reasoning strategies[cite: 18]. Furthermore, its novelty makes it a strong candidate for the **Judges' Choice awards**. However, given the primary focus on Raw Performance, the implementation complexity of the MMA must be weighed against simpler, potentially faster memory augmentation techniques (e.g., direct RAG). A pragmatic approach might involve initially implementing direct RAG (Week 3) and pursuing the full MMA only if time permits and a clear performance benefit is demonstrable (Week 4).

## Section 5: System Integration and a Phased Training Protocol


The individual components—perception, planning, and memory—must be integrated into a cohesive system and trained in a structured, methodical manner. Attempting to train such a complex, multi-component agent end-to-end from scratch is computationally infeasible and highly susceptible to training instability. Therefore, a phased, curriculum-based training protocol is proposed to manage this complexity and build the agent's capabilities incrementally.


### 5.1 The Full Agent Loop (Perceive-Remember-Plan-Act)


The integrated agent operates in a continuous loop, with each component playing a distinct role in the decision-making process:

1. **Perceive**: At each time step t, the VLM captures a screenshot from the emulator and translates it into a structured JSON state, S_t.

2. **Remember**: The Memory Management Agent (MMA) receives S_t. It updates the Working Memory with this new information and, based on its learned policy, executes a memory operation. This may involve writing new information to long-term memory or retrieving relevant context, M_t, from the Episodic or Semantic stores.

3. **Plan**: The High-Level Planner (LLM) receives the augmented context, which consists of the current state and the retrieved memory context, (S_t, M_t). It analyzes this information and generates the next high-level subgoal, G_high.

4. **Act**: The Low-Level Controller receives the current state S_t and the subgoal G_high. It then executes a sequence of primitive actions, a_t, a_{t+1}, ..., until G_high is achieved, a timeout is reached, or the planner issues a new subgoal.

5. This loop repeats, allowing the agent to continuously perceive its environment, update its understanding of the world, formulate plans, and execute actions.


### 5.2 A Practical, Phased Training Protocol


This phased protocol de-risks the development process by breaking down the overwhelming task of training the full agent into a series of well-defined, manageable sub-problems. Each phase builds upon the stable, validated output of the previous one, creating a curriculum that guides the agent toward competence. This structured approach mirrors human learning—mastering basic skills before combining them to solve complex problems—and is a powerful technique for stabilizing RL by systematically reducing the exploration challenge.23


| Phase | Objective | Key Modules Involved | Training Method | Required Data / Environment | Success Metric |
|-------|-----------|---------------------|-----------------|---------------------------|----------------|
| **1** | Perception Foundation | Vision-Language Model (VLM) | Supervised Learning | Curated (screenshot, json_state) dataset | High accuracy on JSON field prediction; high F1 score on text extraction |
| **2** | Tactical Execution | Low-Level Controller | Offline Hierarchical RL (e.g., Guider) | Large offline dataset of varied gameplay trajectories | High success rate in achieving a diverse set of short-horizon subgoals |
| **3** | Strategic Planning | High-Level Planner, (frozen) Low-Level Controller | Guidance-Aware Online RL (e.g., PTA-GRPO) | Live interaction with the game emulator | High success rate in completing multi-step quests from the skill graph |
| **4** | Memory Integration & Full System Tuning | Memory Management Agent (MMA), (frozen) Full System | Policy Gradient RL (e.g., PPO) | Live interaction on very long-horizon, full-game tasks | High final game completion rate; minimization of in-game completion time |
	**Phase 1: Perception Foundation** - The first step is to build a reliable perception system. The VLM is trained via supervised learning on the curated dataset of screenshot-JSON pairs. The goal is to achieve high accuracy in parsing all relevant information from the screen. This module must be robust before any decision-making components are trained.

**Phase 2: Tactical Execution** - With a working perception module, the next step is to teach the agent how to act. The Low-Level Controller is trained using offline HRL on the large gameplay dataset. This phase focuses on mastering basic, short-horizon skills like navigation, interaction with objects and NPCs, and basic battle commands, without any high-level strategic context.

**Phase 3: Strategic Planning** - Once the agent has a competent low-level controller, it can begin to learn strategy. The High-Level Planner is trained online in the live game environment. Its task is to learn how to sequence the skills learned by the (now frozen) low-level controller to achieve more complex, multi-step objectives derived from the pre-computed skill graph.

**Phase 4: Memory Integration & Full System Tuning** - In the final phase, with the core perception-planning-action loop in place, the Memory Management Agent is trained. This requires running the agent on very long-horizon tasks that necessitate long-term memory. The MMA is trained via RL to optimize its memory operations to support the (now largely frozen) planner in completing the full game. This phase fine-tunes the entire system for peak performance.


## Section 6: Conclusion: A Roadmap to Competitive Performance


This report has outlined a comprehensive architectural blueprint for a highly competitive agent in the PokéAgent RPG Speedrunning Challenge. By synthesizing state-of-the-art techniques from hierarchical reinforcement learning, vision-language modeling, and active memory management, the proposed design directly addresses the core challenges of long-horizon, sparse-reward decision-making that define this problem domain.


### 6.1 Synthesizing the Architectural Advantages


The proposed agent's competitive edge stems from four key architectural innovations:

1. **Semantic Perception**: A fine-tuned Vision-Language Model replaces a simple CNN, allowing the agent to comprehend the multi-modal game state, including text and UI elements, providing a rich, structured foundation for decision-making.

2. **Hierarchical Decision-Making**: A hybrid LLM-HRL command structure separates high-level strategic planning from low-level tactical execution. This enables the agent to reason at multiple levels of temporal abstraction, efficiently exploring the vast state space and composing complex behaviors from reusable skills.

3. **Active Long-Term Memory**: A sophisticated, multi-component memory system managed by a dedicated RL agent allows for persistent, goal-conditioned storage and retrieval of information over arbitrarily long time horizons, overcoming the fundamental limitations of standard recurrent and Transformer architectures.

4. **Tractable Training**: A phased, curriculum-based training protocol deconstructs the immense challenge of building this agent into a manageable sequence of learning stages, ensuring a practical path to implementation.


### 6.2 Mapping Innovations to Competitive Metrics

This architecture is explicitly designed to optimize for the competition's revised evaluation metrics:

- **Maximizing Raw Performance**: The hierarchical planner, guided by game knowledge (potentially via a pre-computed skill graph or fine-tuning) and executed by an efficient low-level controller, aims to discover and follow near-optimal paths through the game's milestones. The focus on performance-tuned components like the Qwen VLM further supports rapid decision-making, directly contributing to faster completion times and higher milestone counts.

- **Competing for Judges' Choice Awards**: Our commitment to learning-based solutions—the VLM for perception, the potential RL-based MMA for memory, and the HRL structure—showcases the kind of innovation the Judges' Choice awards aim to recognize. Thorough documentation of these components will highlight their novelty and potential for advancing general AI capabilities.

- **Originality and Contribution**: The proposed synthesis of VLM-based perception, LLM-guided HRL, and potentially RL-managed memory represents a novel agent architecture that aligns with the competition's goal to foster innovative research, satisfying requirements for submission originality.


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