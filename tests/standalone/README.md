# Standalone Test Scripts

These are **diagnostic/debug scripts**, not pytest tests.

They should be run directly (not with pytest):
```bash
# ✅ CORRECT: Run directly
source .venv/bin/activate
python tests/standalone/standalone_vlm_understanding.py

# ❌ WRONG: Don't use pytest
pytest tests/standalone/  # Won't find any tests
```

**Why not pytest?** These scripts execute code at module import time (before pytest can collect tests) and call `sys.exit()`. They're renamed from `test_*.py` to `standalone_*.py` to prevent pytest from collecting them.

## Available Scripts

### VLM Testing
- `standalone_vlm_understanding.py` - Verify VLM can understand game state  
- `standalone_vlm_simple_map.py` - Test VLM map understanding
- `standalone_vlm_simple_state.py` - Test VLM state interpretation
- `standalone_vlm_consistency.py` - Test VLM response consistency
- `standalone_vlm_with_screenshot.py` - Test VLM with screenshots
- `standalone_vlm_multiple_choice_isolation.py` - Test VLM multiple choice handling

### Perception Testing  
- `standalone_perception_gpu.py` - GPU-accelerated perception tests
- `standalone_perception_integration.py` - Perception integration tests

## Configuration

These scripts may require:
- A running emulator server (`python run.py --load-state ...`)
- Specific save states
- GPU access (for VLM tests)

Check each script for specific requirements.
