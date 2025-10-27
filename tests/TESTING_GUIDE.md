# Testing Guide

## Test Structure

### Core Directories

- **`dialogue/`** - All dialogue system tests (detection, completion, agent interaction)
  - **`dialogue/debug/`** - Debug scripts for dialogue issues
- **`navigation/`** - Navigation and pathfinding tests
- **`agent/`** - Agent behavior, modules, and objective planning tests
- **`integration/`** - Full system integration tests
- **`manual/`** - Manual/interactive test scripts
- **`scripts/`** - Automated test runner scripts
- **`scenarios/`** - Specific scenario-based tests
- **`standalone/`** - Independent test files
- **`utils/`** - Test utilities, formatters, and helper scripts
- **`states/`** - Saved emulator states for testing
- **`ground_truth/`** - Ground truth data for validation

### Running Tests

**Run all tests:**
```bash
cd tests && python run_tests.py
# or
pytest
```

**Run specific category:**
```bash
pytest dialogue/  # All dialogue tests
pytest agent/     # All agent tests
pytest navigation/  # All navigation tests
```

**Run single test:**
```bash
pytest dialogue/test_dialogue_detection.py
pytest agent/test_agent_modules.py
```

**With coverage:**
```bash
pytest --cov=agent --cov=pokemon_env
```

### Test Categories

#### Dialogue Tests (`dialogue/`)
- Detection: VLM-based text box detection
- Completion: Dialogue progression and A-press handling
- Integration: Full dialogue flow with agent
- Debug scripts in `dialogue/debug/` for troubleshooting

#### Navigation Tests (`navigation/`)
- Pathfinding algorithms
- Map navigation
- Route-specific tests (e.g., Route 101)

#### Agent Tests (`agent/`)
- Agent module tests (perception, action, planning)
- Objective planner
- Agent-dialogue integration

#### Integration Tests (`integration/`)
- Full system tests
- Multi-component interaction
- End-to-end workflows

#### Manual Tests (`manual/`)
- Interactive debugging
- Manual verification scripts
- Live system validation

### Key Files at Root

- **`conftest.py`** - Pytest configuration and fixtures
- **`run_tests.py`** - Main test runner
- **`test_integration.py`** - Core integration test
- **`test_data_flow.py`** - Data flow validation
- **`test_default_config.py`** - Configuration tests
- **`validate_live_system.py`** - Live system validator

### Best Practices

1. **Use appropriate directory** - Put tests in correct category folder
2. **Use saved states** - Leverage `states/` for consistent test scenarios
3. **Check ground truth** - Compare against `ground_truth/` data when validating
4. **Debug scripts** - Use `dialogue/debug/` scripts for troubleshooting
5. **Integration tests** - Add to `integration/` for multi-component tests

### Adding New Tests

1. Determine category (dialogue, navigation, agent, etc.)
2. Create test file in appropriate directory
3. Use existing fixtures from `conftest.py`
4. Add ground truth data if needed
5. Update this guide if adding new test category

### Troubleshooting

- **Dialogue issues**: Check `dialogue/debug/` scripts
- **Navigation problems**: Run `navigation/` tests
- **Agent behavior**: Debug with `agent/` tests
- **Full system**: Use `integration/` tests and `validate_live_system.py`
- **State issues**: Verify saved states in `states/`

### Continuous Integration

Tests are organized for easy CI integration:
- Fast unit tests: `dialogue/`, `agent/`, `utils/`
- Slower integration: `integration/`, `scenarios/`
- Manual tests: `manual/` (skip in CI)
