# Integration Tests

**Runtime**: 30-120 seconds per test  
**Dependencies**: Direct emulator (no server)

Run these tests before major changes to validate core emulator functionality.

## Running

```bash
# All integration tests
.venv/bin/python -m pytest tests/integration/ -v

# Specific test
.venv/bin/python -m pytest tests/integration/test_memory_reading.py -v
```

## Tests

- **test_memory_reading.py** - Core memory reading validation (critical)
- **test_map_transitions.py** - Location transition testing
- **test_ground_truth.py** - Regression testing vs saved outputs
- **test_dialogue_detection.py** - OCR dialogue system end-to-end

## When to Run

- ✅ Before major refactors
- ✅ After emulator changes
- ✅ Weekly validation
- ❌ Not every commit (too slow)

See main [tests/README.md](../README.md) for more details.
