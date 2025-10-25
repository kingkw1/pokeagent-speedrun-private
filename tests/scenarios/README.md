# Scenario Tests

**Runtime**: 1-5 minutes per test  
**Dependencies**: May spawn servers, load save states

Run these tests to validate end-to-end workflows and performance.

## Running

```bash
# Using the scenario runner (recommended)
python tests/scenarios/run_scenarios.py

# Or with pytest
.venv/bin/python -m pytest tests/scenarios/ -v

# Specific test
.venv/bin/python -m pytest tests/scenarios/test_fps_adjustment_pytest.py -v
```

## Tests

- **test_fps_adjustment_pytest.py** - FPS switching (30→120 FPS)
- **test_torchic_state.py** - Save state validation example
- **test_map_stitcher_fix.py** - Map stitcher performance monitoring
- **run_scenarios.py** - Multi-step test framework
- **diagnose.py** - Debug agent hangs
- **diagnose_performance.py** - Track performance degradation

## Archive

Old tests moved to `archive/` subdirectory:
- Tests replaced by faster unit tests
- Redundant server-based tests
- Deprecated functionality

See main [tests/README.md](../README.md) for more details.
