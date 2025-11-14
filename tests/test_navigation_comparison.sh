#!/bin/bash
# Test navigation comparison on splits 03, 04, 05
# Runs each split for 20 seconds to compare old vs new navigation systems

TIMEOUT=20
PYTHON=".venv/bin/python"

echo "████████████████████████████████████████████████████████████████"
echo "  NAVIGATION COMPARISON TEST"
echo "  Testing splits 03, 04, 05 for 20 seconds each"
echo "████████████████████████████████████████████████████████████████"
echo ""

# Split 03: After getting starter, heading to Oldale
echo "════════════════════════════════════════════════════════════════"
echo "SPLIT 03: BIRCH - After getting starter"
echo "════════════════════════════════════════════════════════════════"
echo ""
timeout ${TIMEOUT}s $PYTHON run.py --save_state Emerald-GBAdvance/splits/03_birch/03_birch.state
RESULT_03=$?
echo ""
echo "Split 03 exit code: $RESULT_03 (124 = timeout, expected)"
echo ""
sleep 2

# Split 04: At Route 103, need to battle rival
echo "════════════════════════════════════════════════════════════════"
echo "SPLIT 04: RIVAL - Route 103 rival battle"
echo "════════════════════════════════════════════════════════════════"
echo ""
timeout ${TIMEOUT}s $PYTHON run.py --save_state Emerald-GBAdvance/splits/04_rival/04_rival.state
RESULT_04=$?
echo ""
echo "Split 04 exit code: $RESULT_04 (124 = timeout, expected)"
echo ""
sleep 2

# Split 05: After rival, heading to Petalburg
echo "════════════════════════════════════════════════════════════════"
echo "SPLIT 05: PETALBURG - Heading to Petalburg City"
echo "════════════════════════════════════════════════════════════════"
echo ""
timeout ${TIMEOUT}s $PYTHON run.py --save_state Emerald-GBAdvance/splits/05_petalburg/05_petalburg.state
RESULT_05=$?
echo ""
echo "Split 05 exit code: $RESULT_05 (124 = timeout, expected)"
echo ""

echo "████████████████████████████████████████████████████████████████"
echo "  ALL TESTS COMPLETE"
echo "████████████████████████████████████████████████████████████████"
echo ""
echo "Results:"
echo "  Split 03: Exit code $RESULT_03"
echo "  Split 04: Exit code $RESULT_04"
echo "  Split 05: Exit code $RESULT_05"
echo ""
echo "Review the output above to compare OLD vs NEW navigation systems"
echo "████████████████████████████████████████████████████████████████"
