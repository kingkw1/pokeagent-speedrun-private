# Test Scenario Runner - Quick Reference

## ✅ Created Files

1. **`tests/test_scenario_runner.py`** - Main test runner script
2. **`tests/SCENARIO_TESTING.md`** - Detailed documentation

## 🚀 Ready to Use

Your test infrastructure is ready! Here's how to run your first test:

```bash
# Activate your virtual environment first
source .venv/bin/activate

# Run the truck exit test
python tests/test_scenario_runner.py

# Or run with verbose output to see what's happening
python tests/test_scenario_runner.py -v
```

## 📊 What the Test Does

The "Exit Moving Van" test:

1. **Loads** `Emerald-GBAdvance/truck_start.state`
2. **Starts** the agent in `--agent-auto --headless` mode
3. **Monitors** the `/state` endpoint every 3 seconds
4. **Checks** if `player.location` changes from `MOVING_VAN` to any of:
   - `LITTLEROOT_TOWN_BRENDANS_HOUSE_2F` (upstairs)
   - `LITTLEROOT_TOWN_BRENDANS_HOUSE_1F` (downstairs)
   - `LITTLEROOT_TOWN` (outside)
5. **Reports** PASS if successful within 50 steps, FAIL otherwise

## 🎯 Expected Output

```
======================================================================
🧪 TEST: Exit Moving Van
📝 Agent should exit the moving van and successfully enter Brendan's house
📁 Save state: Emerald-GBAdvance/truck_start.state
🎯 Max steps: 50
======================================================================
🚀 Starting agent: python run.py --load-state Emerald-GBAdvance/truck_start.state --agent-auto --headless --port 8002
⏳ Waiting for server to initialize...
   📍 Step 0/50 [8.2s]: MOVING_VAN (10, 15)
   📍 Step 5/50 [23.4s]: MOVING_VAN (10, 16)
   📍 Step 12/50 [44.1s]: LITTLEROOT_TOWN_BRENDANS_HOUSE_2F (7, 8)

✅ PASS: Exit Moving Van
   ⏱️  Completed in 12 checks (44.1s)
   📍 Final location: LITTLEROOT_TOWN_BRENDANS_HOUSE_2F (7, 8)
```

## 📝 Adding More Tests

To add more tests, follow this pattern in `test_scenario_runner.py`:

```python
# 1. Create a success check function
def check_my_test(state_data):
    """Check if the goal is achieved"""
    location = state_data.get('player', {}).get('location', '')
    return location == 'TARGET_LOCATION'

# 2. Add to TESTS list
TESTS = [
    # ... existing tests ...
    ScenarioTest(
        name="My Test Name",
        save_state="Emerald-GBAdvance/my_save.state",
        max_steps=30,
        success_fn=check_my_test,
        description="What this test validates"
    ),
]
```

## 🔍 Key Features

- ✅ **Port Isolation**: Each test uses a different port to avoid conflicts
- ✅ **Progress Tracking**: Shows location updates in real-time
- ✅ **Clean Cleanup**: Properly terminates subprocesses
- ✅ **Flexible Filtering**: Run specific tests by name
- ✅ **State Monitoring**: Uses the `/state` API endpoint
- ✅ **Timeout Protection**: Won't run forever if agent gets stuck

## 🐛 Troubleshooting

If the test fails:

```bash
# Run with verbose to see agent output
python tests/test_scenario_runner.py -v

# Check if save state exists
ls -lh Emerald-GBAdvance/truck_start.state

# Make sure no other server is running
pkill -f "python run.py"

# Try running manually first to verify agent works
python run.py --load-state Emerald-GBAdvance/truck_start.state --agent-auto
```

## 🎯 Next Steps

1. **Run the test** to see current agent performance
2. **Analyze failures** to identify issues
3. **Fix agent code** based on test results
4. **Re-run test** to verify fixes
5. **Add more tests** for other scenarios

## 📚 More Information

See `tests/SCENARIO_TESTING.md` for:
- Detailed usage guide
- How to add new tests
- Available state data structure
- Suggested test scenarios
- Performance notes
- Integration with development workflow
