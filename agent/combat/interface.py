from abc import ABC, abstractmethod

class BattleAgent(ABC):
    """
    Abstract interface for all battle controllers.
    Ensures the main agent can swap brains without breaking.
    """
    @abstractmethod
    def get_action(self, state_data: dict) -> int:
        """
        Decide the next move based on game state.
        
        Args:
            state_data: dict containing RAM info (HP, moves, species, etc.)
            
        Returns:
            int: The index of the action to take (0-3 usually).
                 Mapping: 0=Move1, 1=Move2, 2=Move3, 3=Move4
        """
        pass