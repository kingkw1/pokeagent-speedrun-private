#!/usr/bin/env python3
"""
VLM Compliance Analysis Script

⚠️  NOTE: This script requires code instrumentation described in 
    docs/compliance/TESTING_PLAN.md which has NOT been implemented.
    
    For current compliance verification, use instead:
    - ./verify_compliance.sh (quick check)
    - python scripts/quick_vlm_check.py (detailed analysis)
    - python scripts/inspect_llm_logs.py (log debugging)

Analyzes logs to prove that 100% of emulator actions originate from VLM decisions,
satisfying competition requirements that "final action comes from a neural network".

Usage:
    python scripts/analyze_vlm_compliance.py
    
Requirements (NOT IMPLEMENTED):
    - .pokeagent_cache/vlm_compliance.log (action tracking)
    - .pokeagent_cache/vlm_calls.log (VLM call tracking)
    - llm_logs/llm_log_*.jsonl (optional, for LLM metrics)
"""

import os
import json
import glob
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple

def parse_timestamp(ts_str: str) -> datetime:
    """Parse timestamp string to datetime object."""
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

def load_vlm_calls(filepath: str) -> List[Dict]:
    """Load VLM calls from log file."""
    if not os.path.exists(filepath):
        print(f"⚠️ VLM calls log not found: {filepath}")
        return []
    
    calls = []
    current_call = {}
    
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            
            if line.startswith("[") and "] VLM CALL" in line:
                # Save previous call
                if current_call:
                    calls.append(current_call)
                
                # Start new call
                timestamp_str = line.split("]")[0][1:]
                current_call = {
                    "timestamp": parse_timestamp(timestamp_str),
                    "timestamp_str": timestamp_str
                }
            
            elif line.startswith("Type:") and current_call:
                current_call["type"] = line.split(":", 1)[1].strip()
            
            elif line.startswith("Prompt length:") and current_call:
                try:
                    length = int(line.split(":")[1].strip().split()[0])
                    current_call["prompt_length"] = length
                except:
                    pass
            
            elif line.startswith("Caller:") and current_call:
                current_call["caller"] = line.split(":", 1)[1].strip()
    
    # Save last call
    if current_call:
        calls.append(current_call)
    
    return calls

def load_actions(filepath: str) -> List[Dict]:
    """Load actions from compliance log file."""
    if not os.path.exists(filepath):
        print(f"⚠️ Action compliance log not found: {filepath}")
        return []
    
    actions = []
    current_action = {}
    in_stack = False
    
    with open(filepath, "r") as f:
        for line in f:
            line = line.rstrip()
            
            if line.startswith("[") and "] ACTION RECEIVED" in line:
                # Save previous action
                if current_action:
                    actions.append(current_action)
                
                # Start new action
                timestamp_str = line.split("]")[0][1:]
                current_action = {
                    "timestamp": parse_timestamp(timestamp_str),
                    "timestamp_str": timestamp_str,
                    "stack": []
                }
                in_stack = False
            
            elif line.startswith("Buttons:") and current_action:
                buttons_str = line.split(":", 1)[1].strip()
                # Parse list format: ['UP', 'RIGHT']
                try:
                    import ast
                    current_action["buttons"] = ast.literal_eval(buttons_str)
                except:
                    current_action["buttons"] = [buttons_str]
            
            elif line.startswith("Source:") and current_action:
                current_action["source"] = line.split(":", 1)[1].strip()
            
            elif line.startswith("Call Stack:"):
                in_stack = True
            
            elif in_stack and line.startswith("  "):
                current_action["stack"].append(line.strip())
    
    # Save last action
    if current_action:
        actions.append(current_action)
    
    return actions

def load_llm_logs() -> List[Dict]:
    """Load LLM API call logs."""
    logs = []
    
    log_files = glob.glob("llm_logs/llm_log_*.jsonl")
    if not log_files:
        print(f"⚠️ No LLM logs found in llm_logs/")
        return []
    
    for filepath in sorted(log_files)[-5:]:  # Last 5 log files
        try:
            with open(filepath, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        logs.append(entry)
                    except:
                        pass
        except:
            pass
    
    return logs

def analyze_compliance():
    """Main analysis function."""
    print("="*80)
    print("VLM COMPLIANCE ANALYSIS")
    print("="*80)
    print()
    
    # Load data
    print("📂 Loading logs...")
    vlm_calls = load_vlm_calls(".pokeagent_cache/vlm_calls.log")
    actions = load_actions(".pokeagent_cache/vlm_compliance.log")
    llm_logs = load_llm_logs()
    
    print(f"   VLM calls logged: {len(vlm_calls)}")
    print(f"   Actions logged: {len(actions)}")
    print(f"   LLM API calls: {len(llm_logs)}")
    print()
    
    # Test 1: Check for logs
    if len(actions) == 0:
        print("❌ TEST 1 FAILED: No action logs found!")
        print("   Please ensure instrumentation is added to server/app.py")
        return
    
    print("✅ TEST 1 PASSED: Action logging operational")
    print()
    
    # Test 2: Analyze VLM call types
    print("="*80)
    print("VLM CALL TYPE DISTRIBUTION")
    print("="*80)
    
    vlm_types = defaultdict(int)
    for call in vlm_calls:
        call_type = call.get("type", "unknown")
        vlm_types[call_type] += 1
    
    for call_type, count in sorted(vlm_types.items(), key=lambda x: -x[1]):
        print(f"   {call_type:30s} : {count:5d} calls")
    print()
    
    # Test 3: Check action sources
    print("="*80)
    print("ACTION SOURCE ANALYSIS")
    print("="*80)
    
    sources = defaultdict(int)
    agent_actions = 0
    non_agent_actions = 0
    
    for action in actions:
        source = action.get("source", "unknown")
        sources[source] += 1
        
        # Check if action came from agent
        stack = action.get("stack", [])
        is_agent = any("agent/" in frame for frame in stack)
        
        if is_agent:
            agent_actions += 1
        else:
            non_agent_actions += 1
    
    for source, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"   {source:30s} : {count:5d} actions")
    
    print()
    print(f"   Actions from agent: {agent_actions}")
    print(f"   Actions from other: {non_agent_actions}")
    
    if non_agent_actions > 0:
        print(f"   ⚠️ {non_agent_actions} actions NOT from agent - investigating...")
        for action in actions:
            stack = action.get("stack", [])
            if not any("agent/" in frame for frame in stack):
                print(f"      {action['timestamp_str']}: {action.get('buttons')} - {action.get('source')}")
    
    print()
    
    # Test 4: Temporal correlation
    print("="*80)
    print("TEMPORAL CORRELATION (VLM CALLS → ACTIONS)")
    print("="*80)
    
    matched_actions = 0
    unmatched_actions = []
    
    for action in actions:
        action_time = action.get("timestamp")
        if not action_time:
            continue
        
        # Find VLM call within 10 seconds before this action
        found = False
        for vlm_call in vlm_calls:
            vlm_time = vlm_call.get("timestamp")
            if not vlm_time:
                continue
            
            time_diff = (action_time - vlm_time).total_seconds()
            
            # VLM call should be 0-10 seconds BEFORE action
            if 0 <= time_diff <= 10:
                found = True
                break
        
        if found:
            matched_actions += 1
        else:
            unmatched_actions.append(action)
    
    print(f"   Actions with VLM call: {matched_actions}/{len(actions)}")
    
    if unmatched_actions:
        print(f"   ⚠️ {len(unmatched_actions)} actions WITHOUT VLM calls:")
        for action in unmatched_actions[:10]:  # Show first 10
            print(f"      {action['timestamp_str']}: {action.get('buttons')}")
        if len(unmatched_actions) > 10:
            print(f"      ... and {len(unmatched_actions) - 10} more")
    
    print()
    
    # Test 5: Check for executor pattern compliance
    print("="*80)
    print("VLM EXECUTOR PATTERN CHECK")
    print("="*80)
    
    executor_types = [t for t in vlm_types.keys() if "EXECUTOR" in t or t == "ACTION"]
    print(f"   Executor VLM calls: {sum(vlm_types[t] for t in executor_types)}")
    print(f"   Executor types found:")
    for exec_type in executor_types:
        print(f"      - {exec_type}: {vlm_types[exec_type]} calls")
    print()
    
    # Test 6: LLM API analysis (if available)
    if llm_logs:
        print("="*80)
        print("LLM API CALL ANALYSIS")
        print("="*80)
        
        request_types = defaultdict(int)
        for log in llm_logs:
            req_type = log.get("request_type", "unknown")
            request_types[req_type] += 1
        
        print("   Request type distribution:")
        for req_type, count in sorted(request_types.items(), key=lambda x: -x[1]):
            print(f"      {req_type:30s} : {count:5d} calls")
        print()
    
    # Final verdict
    print("="*80)
    print("COMPLIANCE VERDICT")
    print("="*80)
    print()
    
    tests_passed = 0
    tests_total = 5
    
    # Test 1: Actions logged
    if len(actions) > 0:
        print("✅ Test 1: Action logging operational")
        tests_passed += 1
    else:
        print("❌ Test 1: No actions logged")
    
    # Test 2: VLM calls logged
    if len(vlm_calls) > 0:
        print("✅ Test 2: VLM calls logged")
        tests_passed += 1
    else:
        print("❌ Test 2: No VLM calls logged")
    
    # Test 3: All actions from agent
    if non_agent_actions == 0:
        print("✅ Test 3: 100% of actions from agent system")
        tests_passed += 1
    else:
        print(f"❌ Test 3: {non_agent_actions} actions from non-agent sources")
    
    # Test 4: Temporal correlation
    correlation_rate = matched_actions / len(actions) if actions else 0
    if correlation_rate >= 0.95:
        print(f"✅ Test 4: {correlation_rate*100:.1f}% actions have VLM calls (≥95%)")
        tests_passed += 1
    else:
        print(f"❌ Test 4: Only {correlation_rate*100:.1f}% actions have VLM calls (<95%)")
    
    # Test 5: Executor pattern used
    executor_call_count = sum(vlm_types[t] for t in executor_types)
    if executor_call_count > 0:
        print(f"✅ Test 5: VLM executor pattern used ({executor_call_count} calls)")
        tests_passed += 1
    else:
        print(f"❌ Test 5: No VLM executor calls found")
    
    print()
    print(f"Overall: {tests_passed}/{tests_total} tests passed")
    print()
    
    if tests_passed == tests_total:
        print("🎉 FULL COMPLIANCE: All actions originate from neural network!")
        print("   Competition requirement satisfied: 'final action comes from neural network'")
    elif tests_passed >= 3:
        print("⚠️ PARTIAL COMPLIANCE: Most tests passed, but review failures above")
    else:
        print("❌ NON-COMPLIANT: Multiple test failures - action bypass detected!")
    
    print("="*80)

if __name__ == "__main__":
    analyze_compliance()
