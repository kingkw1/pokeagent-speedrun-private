# agent/brain/planner.py
import json
import logging
import re

logger = logging.getLogger(__name__)

# Default fallback when LLM output is unparseable or missing required keys
_FALLBACK_PLAN = {
    "recovery_task": "Explore alternative routes",
    "reasoning": "Fallback — LLM response could not be parsed.",
}


class RecoveryPlanner:
    """
    The Reasoning Engine.
    Uses an LLM to generate recovery steps when the agent gets blocked.

    Phase 1: Context comes from a hardcoded cheat-sheet string.
    Phase 2: Context will come from EpisodicMemory.retrieve().
    """

    def __init__(self, vlm=None):
        """
        Args:
            vlm: An initialised ``utils.vlm.VLM`` instance.  When *None* the
                 planner falls back to a deterministic mock (useful for unit
                 tests and offline demos).
        """
        self.vlm = vlm

        # PHASE 1: HARDCODED CONTEXT (The "Cheat Sheet")
        # In Phase 2, replace this with memory.retrieve()
        self.static_knowledge = (
            "KNOWN GAME MECHANICS:\n"
            "- If an Old Man blocks the path, you must talk to him to watch a catching tutorial.\n"
            "- If a small tree blocks the path, you need the HM Cut.\n"
            "- If a ledge blocks the path, go around; ledges are one-way.\n"
            "- If a Team Aqua/Magma grunt is blocking a door, you usually need to "
            "clear a nearby dungeon or deliver an item."
        )

    def generate_recovery_plan(
        self,
        current_goal: str,
        blocker_reason: str,
        blocker_context: str,
    ) -> dict:
        """
        Asks the LLM to formulate a plan based on the active blocker and
        available context.

        Returns:
            dict with keys ``recovery_task`` (str) and ``reasoning`` (str).
            Always returns a valid dict — falls back to a safe default on any
            parse or API error.
        """
        prompt = (
            "You are an expert Pokemon Speedrun Guide.\n\n"
            f"CONTEXT (Game Knowledge):\n{self.static_knowledge}\n\n"
            f"SITUATION:\n"
            f"The player's current goal is: \"{current_goal}\".\n"
            f"The player is currently blocked.\n"
            f"System Reason: \"{blocker_reason}\"\n"
            f"On-Screen Visual Context: \"{blocker_context}\"\n\n"
            "TASK:\n"
            "Based strictly on the CONTEXT provided, what is the immediate next "
            "step the player should take to clear the blocker?\n\n"
            "Output your response as a valid JSON object with EXACTLY these two keys:\n"
            "- \"recovery_task\": A short, actionable command string (e.g., \"Talk to the Old Man\").\n"
            "- \"reasoning\": A brief explanation of why this solves the problem.\n\n"
            "Return ONLY the JSON object, no other text."
        )

        response_text = self._call_llm(prompt)
        return self._parse_response(response_text)

    # ------------------------------------------------------------------
    # LLM integration
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """
        Send a text-only prompt to the VLM backend.

        If no VLM was provided at construction time, returns a deterministic
        mock response so that tests and offline demos still work.
        """
        if self.vlm is not None:
            logger.info(f"[RecoveryPlanner] Sending prompt to LLM ({len(prompt)} chars)")
            return self.vlm.get_text_query(prompt, module_name="RECOVERY-PLANNER")

        # ── Mock fallback (no VLM configured) ──
        print(f"   [RecoveryPlanner] Mock mode — no VLM configured (prompt {len(prompt)} chars)")
        return (
            '{"recovery_task": "Interact with the Old Man", '
            '"reasoning": "The context states that the Old Man requires you to '
            'watch a catching tutorial before passing."}'
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(response_text: str) -> dict:
        """
        Extract and validate the JSON plan from the LLM response.

        Handles:
        - Markdown code fences (```json ... ```)
        - Bare JSON objects
        - Missing / unexpected keys (fills defaults)
        """
        # Try to locate a JSON object in the response
        # 1. Check for markdown-fenced JSON
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if not json_match:
            # 2. Bare JSON object
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)

        if not json_match:
            logger.warning(f"[RecoveryPlanner] No JSON found in response: {response_text[:200]}")
            return dict(_FALLBACK_PLAN)

        try:
            plan = json.loads(json_match.group(0) if not json_match.lastindex else json_match.group(1))
        except json.JSONDecodeError:
            logger.warning(f"[RecoveryPlanner] JSON decode failed: {response_text[:200]}")
            return dict(_FALLBACK_PLAN)

        # Validate required keys — fill missing with fallback values
        if "recovery_task" not in plan or not plan["recovery_task"]:
            plan["recovery_task"] = _FALLBACK_PLAN["recovery_task"]
        if "reasoning" not in plan or not plan["reasoning"]:
            plan["reasoning"] = _FALLBACK_PLAN["reasoning"]

        return plan