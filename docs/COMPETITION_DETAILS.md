Here is the Markdown file with all citations removed.

```markdown
# PokéAgent Challenge 2025

A NeurIPS 2025 competition advancing AI decision-making through the complex environments of Pokémon battles and gameplay. The competition is a skills-based event designed to advance research in reinforcement learning, large-language-model agents, and long-horizon planning.

## Official Competition Rules

### General Information

* **Competition Title:** PokéAgent Challenge 2025
* **Competition Sponsor:** PokéAgent Challenge Organizing Committee (Princeton University, UT Austin, Carnegie Mellon University, Google DeepMind)
* **Sponsor Address:** Dept. of Computer Science, Princeton University, 35 Olden St, Princeton NJ 08544 USA
* **Total Prize Pool:** USD $15,000+ (subject to sponsorship). Exact distributions are published on the Competition Website.

### Entry & Eligibility

* **Acceptance:** Entry in the Competition constitutes your acceptance of the Official Rules.
* **Accounts:** One registered account per individual is allowed. Multiple accounts or identities are prohibited and will result in immediate disqualification.
* **General Participation:** Employees, interns, or contractors of the organizing committee may participate but are ineligible for prizes.
* **Participant Responsibility:** All Participants are responsible for compliance with their employer's internal policies.
* **Prize Eligibility:** For a team to be eligible to win, each member must be at least 18 years old and at least the age of majority in their place of residence.

### Competition Tracks

The Competition comprises two equally-weighted tracks (50% each):

1.  **Battling Track (50%):** Evaluates language-based competitive agents on Pokémon Showdown™. This track comprises two battle modes, and their scores are averaged for the final track score.
2.  **Speedrunning Track (50%):** Evaluates autonomous Emerald speedruns in the provided emulator environment.

### Team Limits

* Maximum team size is 10 members.
* Team mergers are permitted until the Team Merger Deadline (see Timeline).

### Submissions & Timeline

* **Final Submission:** Teams may designate up to 1 Final Submission for judging before the Final Submission Deadline.
* **Tentative Timeline (2025):**
    * **Competition Launch:** 11 Jul
    * **Team Merger Deadline:** 15 Sep
    * **Final Submission Deadline:** 31 Oct
    * **Offline Evaluation Complete:** 7 Nov
* **Authoritative Timeline:** Dates are approximate. The authoritative timeline will be maintained on the Competition Website.

### Data, Tools, & Originality

* **Data Access & Use:** Participants may use the provided datasets and tools only for developing Competition Submissions and for non-commercial academic research or education. Any other use requires the Sponsor's express written consent.
* **Data Security:** You must employ reasonable measures to prevent anyone who has not agreed to the Rules from accessing the data. Redistribution is prohibited.
* **External Data & Tools:** External data, pretrained models, and automated ML tools are permitted provided they are (i) publicly available to all Participants at minimal or no cost or (ii) satisfy the Reasonableness Standard set by the Host.
* **Submission Originality:**
    * Exact clones or trivial modifications of organizer-hosted baselines are not eligible for prizes.
    * Prize-eligible submissions must demonstrate novel approaches, meaningful modifications, or original implementations.
    * Simple repackaging, or minimal code changes will be disqualified from prize consideration.
    * The organizing committee will evaluate all submissions for originality.

### Winner Obligations & Licensing

* **Winner License:** You grant a worldwide, non-exclusive, transferable, irrevocable license. You may also release your code under an OSI-approved license, provided it does not restrict the Sponsor's rights.
* **Winner Obligations:** Within 14 days of notification, prize winners must:
    1.  Deliver fully reproducible code, pretrained weights, and documentation.
    2.  Execute the license grant.
    3.  Complete and return all required tax and eligibility forms.
* **Award Receipt:** To receive awards, Competition winners must attend the NeurIPS workshop (in-person) and detail their solution in the retrospective paper.

### Organizer Authority

* **Rule Modifications:** The Competition organizers may change the Rules, timeline, evaluation metrics, prize structure, or any other aspect at any time. This includes modifying game rules to ensure fair play.
* **Disqualification Powers:** Organizers reserve the right to disqualify participants or teams at any point if cheating, plagiarism, collusion, or other misconduct is discovered or suspected. This can occur even after results are announced.
* **Final Authority:** All organizer decisions are final and binding.
* **Governing Law:** These Rules are governed by the laws of the State of California, USA.

---

## Track 2: Speedrunning - Long-Horizon RPG Gameplay

This track challenges agents to complete a full Pokémon role-playing game (Pokémon Emerald) as quickly and efficiently as possible. Agents must navigate a massive, partially observable world, balancing immediate objectives with long-term strategic goals.

**Submissions for Track 2 end November 15th, 2025**.

*(Note: The general competition Final Submission Deadline is Oct 31st, but the Track 2 page specifies a Nov 15th deadline for its submissions.)*

### Starter Kits

A starter kit is provided with modular components for perception, planning & memory, and control.

**What's Included:**
* **Agent Scaffolding:** Modular framework for building Pokémon Emerald speedrunning agents.
* **Pokémon Emerald Wrapper:** Custom emulator API for real-time game interaction.
* **Baseline Implementation:** Reference agent with VLM setup and basic planning.
* **Evaluation Tools:** Automated testing and performance measurement.

### Compute Credits

Application for compute credits is closed and credits have been distributed.

### How to Submit for Track 2

* Submissions focus on achieving maximum game completion under time constraints.
* Agents must interact exclusively through the custom Pokémon Emerald emulator API.
* Any method may be used, as long as the final action comes from a neural network.
* All submissions will undergo anti-cheat verification.

**Submission Requirements:**
* **Code Archive:** A ZIP or TAR.GZ file of your agent implementation with all dependencies and a README.
* **Action & State Logs (Anti-Cheat):** The `submission.log` and detailed logs generated by the starter kit to validate the run.
* **Methodology Description:** A brief document (1-2 paragraphs) describing your approach and scaffolding components.

### Final Ranking Criteria

* Final rankings are determined by **raw performance metrics only (number of actions and time)**.
* This is a simplification from a previous "Adjusted Performance" metric, based on community feedback.

**Primary Ranking Components:**
* **Milestone Completion:** Percentage of game milestones accomplished (e.g., gym badges, story progression).
* **Completion Efficiency:** Time and action count to achieve milestones.
* **Reproducibility:** Clear documentation and verifiable results.

### Methodology & Judges' Choice Awards

While scaffolding complexity does not affect the main rankings, teams must document their methodology for consideration of separate Judges' Choice and innovation awards.

**Methodology Dimensions:**
* **State Information (S):** What information your agent receives (e.g., raw pixels vs. parsed game state).
* **Tools (T):** External tools available during gameplay (e.g., web search, calculators).
* **Fine-tuning (F):** Specialized training on Pokémon data.

Separate Judges' Choice awards will recognize innovative approaches, including those with minimal scaffolding, creative tool use, and novel architectural designs.

---

## Prizes

*"100 GCP" refers to "$100 worth of GCP credits."*

### Track 2 Awards

Top performing agents in the RPG speedrunning challenge will be awarded $4,500 and 1000 GCP total:

* **1st Place:** $1,500 + 700 GCP
* **2nd Place:** $1,000 + 300 GCP
* **3rd-4th Place:** $500

### Judges' Choice Awards

Senior organizers will award at least four non-placing projects with $400 or 500 GCP. These projects do not necessarily have to place highly but should propose a novel approach or demonstrate interesting capabilities in long-horizon planning or RPG navigation.

---

## Contact & Support

For questions or support, please contact:

* **Email:** pokeagentchallenge@gmail.com
* **Discord:** Join the Discord community for direct assistance and discussions.

---

©2025 PokéAgent Challenge. All rights reserved. NeurIPS 2025 Competition Track.
```