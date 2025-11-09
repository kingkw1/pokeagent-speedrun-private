#!/usr/bin/env python3
"""Test enhanced hallucination detection against real examples"""

def test_hallucination_detection():
    """Simulate the is_hud_text function to test detection"""
    
    test_cases = [
        # Real hallucinations from logs
        {
            'dialogue': "You are in the forest. You can see a path leading to the right.",
            'should_filter': True,
            'reason': "Scene description: 'you are in' + 'you can see' + 'path leading' = 3 indicators"
        },
        {
            'dialogue': "You are now on Route 101. You have 3000 coins and 1 Pokemon named TREECKO.",
            'should_filter': True,
            'reason': "Game state narration: 'you are now' + 'you have' (2x) = 3 indicators"
        },
        {
            'dialogue': "You are on Route 101. You are currently at position (7, 7). You have $3000 in your bank. You have 1 Pokemon in your party, Treecko. You are currently in the overworld.",
            'should_filter': True,
            'reason': "Multiple game state patterns: 'currently at position', 'in your bank', 'in your party', 'in the overworld'"
        },
        # Real dialogue (should NOT filter)
        {
            'dialogue': "PROF. BIRCH: Oh! You're...",
            'should_filter': False,
            'reason': "Real dialogue - character speech"
        },
        {
            'dialogue': "Yes/No",
            'should_filter': False,
            'reason': "Real menu choice"
        },
        # HUD text (should filter)
        {
            'dialogue': "Player: CASEY | Location: ROUTE 101 | Pos: (7, 9) | State: overworld | Money: $3000",
            'should_filter': True,
            'reason': "HUD pattern with pipes and keywords"
        },
    ]
    
    # Simplified detection logic from perception.py
    def is_hud_text_simple(dialogue_str):
        if not dialogue_str:
            return False
        
        dialogue_lower = dialogue_str.lower()
        
        # Pattern 1: HUD with pipes
        if '|' in dialogue_str and any(kw in dialogue_str for kw in ['Location:', 'Pos:', 'State:', 'Money:']):
            return True
        
        # Pattern 3: Hallucination indicators
        hallucination_indicators = [
            'you can see', 'you are in', 'you are on', 'you are now', 'you are currently',
            'you have', 'there is a', 'there are', 'in the forest', 'path leading',
            'in your bank', 'in your party',
        ]
        
        hallucination_count = sum(1 for ind in hallucination_indicators if ind in dialogue_lower)
        if hallucination_count >= 2:
            return True
        
        # Game state patterns (single match = filter)
        game_state_patterns = [
            'you have $', 'you have 1 pokemon', 'currently at position',
            'in your bank', 'in your party', 'in the overworld',
        ]
        
        for pattern in game_state_patterns:
            if pattern in dialogue_lower:
                return True
        
        # Length check
        if len(dialogue_str) > 150 and any(ind in dialogue_lower for ind in ['you can see', 'you are in', 'there is', 'there are']):
            return True
        
        return False
    
    print("=" * 80)
    print("HALLUCINATION DETECTION TEST")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        dialogue = test['dialogue']
        expected = test['should_filter']
        reason = test['reason']
        
        result = is_hud_text_simple(dialogue)
        
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\nTest {i}: {status}")
        print(f"Input: {dialogue[:80]}{'...' if len(dialogue) > 80 else ''}")
        print(f"Expected: {'FILTER' if expected else 'KEEP'}, Got: {'FILTER' if result else 'KEEP'}")
        print(f"Reason: {reason}")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    if failed == 0:
        print("🎉 All tests passed! Hallucination detection is working correctly.")
    else:
        print("⚠️  Some tests failed. Detection logic needs adjustment.")

if __name__ == '__main__':
    test_hallucination_detection()
