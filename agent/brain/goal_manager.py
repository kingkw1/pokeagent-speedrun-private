import json
from typing import List, Dict, Optional


BLOCKING_KEYWORDS = ["wait", "stop", "don't go", "dangerous"] # Keywords indicating player cannot progress

class GoalManager:
    """
    The Executive State Machine. 
    Tracks the current objective and detects when the agent is blocked.
    """
    def __init__(self):
        # The "Quest Log"
        self.state = {
            "current_objective": "Reach Petalburg City",
            "sub_tasks": [
                {
                    "id": 1, 
                    "task": "Traverse Route 102", 
                    "status": "IN_PROGRESS", 
                    "blocker_context": None
                }
            ],
        }
        
        # Keywords that indicate the player cannot progress
        self.blocking_keywords = BLOCKING_KEYWORDS

    def update(self, perception_output: dict):
        """
        Processes the VLM perception output to update goal states.
        Strictly adheres to the Input Contract to prevent NoneType errors.
        """
        # 1. Safely extract data using the Input Contract
        visual_data = perception_output.get("visual_data", {})
        
        # Dialogue extraction — handle None, missing, and string-typed on_screen_text
        on_screen_text = visual_data.get("on_screen_text", {})
        if isinstance(on_screen_text, str):
            # VLM sometimes returns on_screen_text as a raw string instead of dict
            dialogue = on_screen_text
        elif isinstance(on_screen_text, dict):
            dialogue = on_screen_text.get("dialogue") or ""
        else:
            dialogue = ""
        
        # Context extraction
        screen_context = visual_data.get("screen_context", "")

        # 2. Check for Blockers in Dialogue
        if dialogue and isinstance(dialogue, str):
            dialogue_lower = dialogue.lower()
            for keyword in self.blocking_keywords:
                if keyword in dialogue_lower:
                    self._handle_blocker(
                        reason=f"NPC Dialogue Keyword: '{keyword}'", 
                        context=dialogue
                    )
                    break # Don't trigger multiple times for one text box

    def _handle_blocker(self, reason: str, context: str):
        """Transitions the active task to BLOCKED state."""
        if not self.state["sub_tasks"]:
            return

        active_task = self.state["sub_tasks"][0]
        
        # Only log and update if we aren't already blocked
        if active_task["status"] != "BLOCKED":
            print(f"⚠️ [GoalManager] BLOCKER DETECTED: {reason}")
            print(f"   Context: '{context}'")
            
            active_task["status"] = "BLOCKED"
            active_task["blocker_context"] = context
            
            # Note: In Step 1.2, we will call the LLM Planner here 
            # to generate a Recovery task and insert it into the stack.

    @property
    def current_directive(self) -> str:
        """Returns the high-level plan string for the Agent's planning module."""
        if not self.state["sub_tasks"]:
            return f"Current Goal: {self.state['current_objective']} (Status: NO ACTIVE TASKS)"
            
        active_task = self.state["sub_tasks"][0]
        return f"Current Goal: {active_task['task']} (Status: {active_task['status']})"

    def add_recovery_task(self, task_description: str):
        """Utility for the Planner to inject new sub-goals (Used in 1.2)"""
        self.state["sub_tasks"].insert(0, {
            "id": 99,
            "task": task_description,
            "status": "IN_PROGRESS",
            "type": "RECOVERY",
            "blocker_context": None
        })

    def signal_blocker(self, reason: str, context: str):
        """External trigger to force BLOCKED state (e.g., battle transition)."""
        self._handle_blocker(reason=reason, context=context)

    def complete_task(self):
        """Marks the active task as COMPLETED and removes it from the stack."""
        if not self.state["sub_tasks"]:
            return None

        completed = self.state["sub_tasks"].pop(0)
        completed["status"] = "COMPLETED"
        print(f"✅ [GoalManager] TASK COMPLETED: {completed['task']}")
        return completed