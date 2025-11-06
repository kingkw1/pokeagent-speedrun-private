# Opener Bot Tests

This directory contains tests for the Opener Bot state machine that handles the deterministic opening sequence of Pokemon Emerald.

## Test Files

### Unit Tests
- **`test_unit_clock_sequence.py`** - Unit tests for the clock setting sequence states
  - Tests state detection logic
  - Tests state transitions
  - Tests NavigationGoal generation
  - Can run without emulator

### Integration Tests  
- **`test_clock_yes_no_navigation.py`** - Integration test for clock Yes/No dialogue handling
  - Tests complete clock interaction: navigate → turn → interact → Yes/No → confirm
  - Tests orientation tracking (player must face clock before pressing A)
  - Tests dialogue option selection (UP to select "Yes", A to confirm)
  - Requires emulator and full agent stack
  - Uses save state: `tests/save_states/clock_interaction_save.state`
  - Success: Player stays at (5,2), completes in ~5-10 steps

## Running Tests

### Unit Tests (Fast)
```bash
pytest tests/opener_bot/test_unit_clock_sequence.py -v
```

### Integration Tests (Slow)
```bash
# Run the integration test
python tests/opener_bot/test_clock_yes_no_navigation.py

# Or with pytest
pytest tests/opener_bot/test_clock_yes_no_navigation.py -v -s
```

## Test Coverage

The Opener Bot handles:
- **Phase 1**: Title screen & naming (S0-S2)
- **Phase 2**: Truck & house navigation (S3-S8) ✅ **TESTED**
  - Clock setting with Yes/No dialogue ✅
  - Orientation-aware interaction ✅
- **Phase 3**: Rival's house (S9-S13)
- **Phase 4**: Starter selection (S14-S21)

## Related Documentation

See `docs/OPENER_BOT_EXTENSION.md` for architectural design and implementation details.
