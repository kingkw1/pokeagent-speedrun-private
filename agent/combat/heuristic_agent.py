import random
from .interface import BattleAgent
from simulation.pokedex import MOVES_DATA, SPECIES_DATA, get_effectiveness

class HeuristicBattleAgent(BattleAgent):
    """
    A rule-based battle agent that uses Pokedex knowledge 
    to pick the most effective move.
    """
    def __init__(self):
        print("[Combat] Heuristic Agent initialized.")

    def get_action(self, state_data: dict) -> int:
        # 1. Identify Enemy Type
        enemy_id = state_data.get('enemy_species', 0)
        enemy_info = SPECIES_DATA.get(enemy_id, {'types': [None, None]})
        enemy_types = enemy_info.get('types', [None, None])
        
        best_move_idx = 0
        best_score = -999
        
        # 2. Evaluate Moves
        for i in range(1, 5):
            move_id = state_data.get(f'move_{i}', 0)
            pp = state_data.get(f'move_{i}_pp', 0)
            
            # Skip invalid moves
            if move_id == 0 or pp == 0:
                continue
                
            move_info = MOVES_DATA.get(move_id, {'type': 0, 'power': 0})
            
            # Score Calculation
            # Power * Effectiveness
            eff = get_effectiveness(move_info['type'], enemy_types)
            score = move_info['power'] * eff
            
            # Tie-breaker: Randomize slightly to avoid loops
            score += random.random()
            
            if score > best_score:
                best_score = score
                best_move_idx = i - 1 # Convert 1-based slot to 0-based index
                
        return best_move_idx