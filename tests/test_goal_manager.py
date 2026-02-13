# tests/test_goal_manager.py
import unittest
from agent.brain.goal_manager import GoalManager


class TestGoalManager(unittest.TestCase):
    def setUp(self):
        self.gm = GoalManager()

    # ------------------------------------------------------------------
    # Basic state
    # ------------------------------------------------------------------

    def test_initial_state(self):
        """Ensure the manager starts in the correct state."""
        active_task = self.gm.state["sub_tasks"][0]
        self.assertEqual(active_task["status"], "IN_PROGRESS")

    # ------------------------------------------------------------------
    # Defensive parsing — malformed / missing perception data
    # ------------------------------------------------------------------

    def test_safe_parsing_empty_data(self):
        """Empty dict (missing 'visual_data' entirely) must not crash."""
        self.gm.update({})
        self.assertEqual(self.gm.state["sub_tasks"][0]["status"], "IN_PROGRESS")

    def test_safe_parsing_none_dialogue(self):
        """VLM explicitly sets dialogue=None on false-positive filtering."""
        mock = {
            "visual_data": {
                "screen_context": "overworld",
                "on_screen_text": {"dialogue": None, "speaker": None},
            }
        }
        self.gm.update(mock)
        self.assertEqual(self.gm.state["sub_tasks"][0]["status"], "IN_PROGRESS")

    def test_safe_parsing_on_screen_text_is_string(self):
        """VLM sometimes returns on_screen_text as a raw string instead of dict."""
        mock = {
            "visual_data": {
                "screen_context": "dialogue",
                "on_screen_text": "Wait! Don't go out there!",
            }
        }
        self.gm.update(mock)
        self.assertEqual(self.gm.state["sub_tasks"][0]["status"], "BLOCKED")

    def test_safe_parsing_on_screen_text_is_none(self):
        """on_screen_text could be None rather than missing."""
        mock = {
            "visual_data": {
                "screen_context": "overworld",
                "on_screen_text": None,
            }
        }
        self.gm.update(mock)
        self.assertEqual(self.gm.state["sub_tasks"][0]["status"], "IN_PROGRESS")

    # ------------------------------------------------------------------
    # Blocker detection
    # ------------------------------------------------------------------

    def test_blocker_detection(self):
        """Specific dialogue keywords trigger the BLOCKED state."""
        mock = {
            "visual_data": {
                "screen_context": "overworld",
                "on_screen_text": {
                    "dialogue": "Wait! Don't go out into the tall grass!",
                    "speaker": "Prof. Birch",
                },
            }
        }
        self.gm.update(mock)
        active = self.gm.state["sub_tasks"][0]
        self.assertEqual(active["status"], "BLOCKED")
        self.assertIn("Wait!", active["blocker_context"])

    def test_non_blocking_dialogue(self):
        """Normal dialogue must NOT trigger a block."""
        mock = {
            "visual_data": {
                "screen_context": "overworld",
                "on_screen_text": {
                    "dialogue": "Hello there! Nice weather today.",
                    "speaker": "Townsfolk",
                },
            }
        }
        self.gm.update(mock)
        self.assertEqual(self.gm.state["sub_tasks"][0]["status"], "IN_PROGRESS")

    def test_repeated_blocking_is_idempotent(self):
        """Seeing the same blocker on consecutive frames must not double-trigger."""
        mock = {
            "visual_data": {
                "screen_context": "dialogue",
                "on_screen_text": {
                    "dialogue": "Wait! It's dangerous!",
                    "speaker": "Old Man",
                },
            }
        }
        self.gm.update(mock)
        self.gm.update(mock)  # second frame, same text
        self.gm.update(mock)  # third frame

        # Still only one task, still BLOCKED (not duplicated)
        self.assertEqual(len(self.gm.state["sub_tasks"]), 1)
        self.assertEqual(self.gm.state["sub_tasks"][0]["status"], "BLOCKED")

    # ------------------------------------------------------------------
    # Recovery task injection
    # ------------------------------------------------------------------

    def test_add_recovery_task_becomes_active(self):
        """After adding a recovery task, current_directive returns it."""
        # Block first
        self.gm.state["sub_tasks"][0]["status"] = "BLOCKED"

        self.gm.add_recovery_task("Interact with Old Man for tutorial")
        self.assertIn("Interact with Old Man", self.gm.current_directive)
        self.assertIn("IN_PROGRESS", self.gm.current_directive)

    # ------------------------------------------------------------------
    # Task completion
    # ------------------------------------------------------------------

    def test_complete_task_removes_from_stack(self):
        """Completing the active task exposes the next one underneath."""
        # Add a recovery task on top of the original
        self.gm.add_recovery_task("Talk to NPC")
        self.assertEqual(len(self.gm.state["sub_tasks"]), 2)

        completed = self.gm.complete_task()
        self.assertEqual(completed["task"], "Talk to NPC")
        self.assertEqual(completed["status"], "COMPLETED")

        # Original task is now active again
        self.assertEqual(len(self.gm.state["sub_tasks"]), 1)
        self.assertIn("Traverse Route 102", self.gm.current_directive)

    def test_complete_task_on_empty_stack(self):
        """Completing when no tasks remain returns None gracefully."""
        self.gm.state["sub_tasks"].clear()
        self.assertIsNone(self.gm.complete_task())


if __name__ == "__main__":
    unittest.main()
