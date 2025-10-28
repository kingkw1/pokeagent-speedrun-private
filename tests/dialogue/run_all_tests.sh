#!/bin/bash
# Run all dialogue tests to verify they work

echo "=========================================="
echo "DIALOGUE TEST SUITE"
echo "=========================================="
echo ""

# Activate virtual environment if exists
if [ -f "../../.venv/bin/activate" ]; then
    source ../../.venv/bin/activate
fi

echo "1. Running test_unit_ocr_vs_memory.py (OCR vs Memory comparison)"
echo "=========================================="
python test_unit_ocr_vs_memory.py
if [ $? -eq 0 ]; then
    echo "✅ test_unit_ocr_vs_memory.py PASSED"
else
    echo "❌ test_unit_ocr_vs_memory.py FAILED"
fi
echo ""

echo "2. Running test_unit_multiflag_state.py (VLM detection tests)"
echo "=========================================="
python test_unit_multiflag_state.py
if [ $? -eq 0 ]; then
    echo "✅ test_unit_multiflag_state.py PASSED"
else
    echo "❌ test_unit_multiflag_state.py FAILED"
fi
echo ""

echo "=========================================="
echo "DIALOGUE TEST SUITE COMPLETE"
echo "=========================================="
echo ""
echo "Note: Integration tests require manual running with pytest:"
echo "  pytest tests/dialogue/test_integration_dialogue_completion.py -v"
echo "  pytest tests/dialogue/test_integration_agent_dialogue.py -v"
echo "  pytest tests/dialogue/test_integration_vlm_detection.py -v -m slow"
