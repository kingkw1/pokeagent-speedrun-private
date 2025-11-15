#!/bin/bash
# VLM Executor Compliance Verification Script
# Checks that all actions have corresponding VLM executor calls
#
# For complete compliance documentation, see: docs/compliance/README.md

echo "🔍 VLM EXECUTOR COMPLIANCE VERIFICATION"
echo "========================================"
echo ""

# Find most recent log file
LATEST_LOG=$(ls -t llm_logs/llm_log_*.jsonl 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "❌ ERROR: No log files found in llm_logs/"
    echo "Run the agent first: python run.py --agent-auto --backend gemini --max-steps 20"
    exit 1
fi

echo "📄 Analyzing log file: $LATEST_LOG"
echo ""

# Count interaction types
echo "📊 VLM Interaction Breakdown:"
echo "----------------------------"
cat "$LATEST_LOG" | jq -r '.interaction_type // "null"' | sort | uniq -c | while read count type; do
    if [ "$type" == "null" ]; then
        echo "   $count session_start entries"
    else
        echo "   $count $type"
    fi
done
echo ""

# Check for executor calls
EXECUTOR_COUNT=$(cat "$LATEST_LOG" | jq -r 'select(.interaction_type != null) | select(.interaction_type | contains("EXECUTOR"))' | wc -l)
ACTION_COUNT=$(cat "$LATEST_LOG" | jq -r 'select(.interaction_type == "gemini_ACTION")' | wc -l)
PERCEPTION_COUNT=$(cat "$LATEST_LOG" | jq -r 'select(.interaction_type | contains("PERCEPTION"))' | wc -l)

echo "🎯 Compliance Metrics:"
echo "---------------------"
echo "   Perception calls:   $PERCEPTION_COUNT (VLM analyzing game state)"
echo "   Executor calls:     $EXECUTOR_COUNT (VLM making action decisions)"
echo "   Direct ACTION calls: $ACTION_COUNT (VLM making navigation decisions)"
echo ""

TOTAL_VLM_ACTIONS=$((EXECUTOR_COUNT + ACTION_COUNT))
echo "   Total VLM action decisions: $TOTAL_VLM_ACTIONS"
echo ""

# Verify compliance
if [ $TOTAL_VLM_ACTIONS -eq 0 ]; then
    echo "❌ COMPLIANCE VIOLATION DETECTED!"
    echo "   No VLM executor or action calls found."
    echo "   Actions are being made programmatically without VLM involvement."
    echo ""
    echo "💡 This indicates the fixes may not be active or the agent isn't running."
    exit 1
elif [ $EXECUTOR_COUNT -gt 0 ]; then
    echo "✅ COMPLIANCE VERIFIED!"
    echo "   VLM executor calls detected - agent is routing actions through VLM."
    echo ""
    
    # Show breakdown of executor types
    echo "🔍 Executor Call Breakdown:"
    cat "$LATEST_LOG" | jq -r 'select(.interaction_type != null) | select(.interaction_type | contains("EXECUTOR")) | .interaction_type' | sort | uniq -c | while read count type; do
        echo "   $count $type"
    done
    echo ""
else
    echo "⚠️  PARTIAL COMPLIANCE"
    echo "   Found $ACTION_COUNT direct ACTION calls but 0 EXECUTOR calls."
    echo "   This is acceptable if agent is only navigating (not in dialogue/menus)."
    echo ""
fi

# Check submission log correlation
if [ -f "submission.log" ]; then
    ACTIONS_IN_SUBMISSION=$(grep -c "ACTION=" submission.log 2>/dev/null || echo 0)
    echo "📋 Submission Log Verification:"
    echo "------------------------------"
    echo "   Actions in submission.log: $ACTIONS_IN_SUBMISSION"
    echo "   VLM action decisions:      $TOTAL_VLM_ACTIONS"
    echo ""
    
    if [ $ACTIONS_IN_SUBMISSION -gt $TOTAL_VLM_ACTIONS ]; then
        MISSING=$((ACTIONS_IN_SUBMISSION - TOTAL_VLM_ACTIONS))
        echo "⚠️  WARNING: $MISSING actions in submission.log have no VLM call!"
        echo "   This may indicate programmatic bypasses are still active."
    elif [ $TOTAL_VLM_ACTIONS -ge $ACTIONS_IN_SUBMISSION ]; then
        echo "✅ All actions accounted for (VLM calls >= submission actions)"
    fi
    echo ""
fi

# Show sample executor calls
echo "📝 Sample Executor Prompts:"
echo "--------------------------"
cat "$LATEST_LOG" | jq -r 'select(.interaction_type != null) | select(.interaction_type | contains("EXECUTOR")) | "\(.interaction_type): \(.prompt[:100])..."' | head -3
echo ""

# Check for compliance violations in logs
if [ -f "submission.log" ]; then
    VIOLATIONS=$(grep -c "COMPLIANCE VIOLATION" submission.log 2>/dev/null || echo 0)
    if [ $VIOLATIONS -gt 0 ]; then
        echo "🚨 CRITICAL: $VIOLATIONS compliance violations detected in submission.log!"
        echo "   The agent crashed due to VLM executor failures."
        echo ""
        grep "COMPLIANCE VIOLATION" submission.log | tail -3
    fi
fi

echo "✅ Verification complete!"
echo ""
echo "To verify with fresh run:"
echo "  python run.py --agent-auto --backend gemini --max-steps 20"
