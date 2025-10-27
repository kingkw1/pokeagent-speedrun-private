#!/usr/bin/env python3
"""
Debug AUTO mode - check if agent is trying to act
"""

import subprocess
import time
import requests

def main():
    print("Starting agent with dialog.state in AUTO mode...")
    
    # Start agent
    cmd = ["python", "run.py", "--agent-auto", "--load-state", "tests/states/dialog.state"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    try:
        # Wait for startup
        print("Waiting 15 seconds for agent to initialize...")
        time.sleep(15)
        
        # Monitor for 30 seconds
        print("\n📊 Monitoring agent decision-making:")
        print(f"{'Time':<6} {'Queue Empty':<12} {'State':<20} {'Action Sent'}")
        print("-" * 80)
        
        start_time = time.time()
        
        while time.time() - start_time < 30:
            try:
                # Check queue status
                queue_resp = requests.get("http://localhost:8000/queue_status", timeout=1)
                queue_empty = queue_resp.json().get("queue_empty", False) if queue_resp.status_code == 200 else "ERROR"
                
                # Check state
                state_resp = requests.get("http://localhost:8000/state", timeout=1)
                if state_resp.status_code == 200:
                    state = state_resp.json()
                    pos = state["player"]["position"]
                    in_dialog = state["game"].get("in_dialog", False)
                    state_str = f"({pos['x']},{pos['y']}) dialog={in_dialog}"
                else:
                    state_str = "ERROR"
                
                elapsed = int(time.time() - start_time)
                print(f"{elapsed}s{'':<3} {str(queue_empty):<12} {state_str:<20}")
                
            except Exception as e:
                print(f"  Error: {e}")
            
            time.sleep(1)
        
        # Check LLM logs
        print("\n📋 Checking LLM logs...")
        import glob
        import os
        import json
        
        log_files = sorted(glob.glob("llm_logs/llm_log_*.jsonl"), key=os.path.getmtime)
        if log_files:
            latest = log_files[-1]
            print(f"Latest log: {latest}")
            
            with open(latest, 'r') as f:
                lines = f.readlines()
            
            print(f"Total entries: {len(lines)}")
            
            if len(lines) > 1:
                print("\nLast 10 entries:")
                for line in lines[-10:]:
                    entry = json.loads(line)
                    entry_type = entry.get('type', 'unknown')
                    
                    if entry_type == 'action_decision':
                        action = entry.get('action', 'NONE')
                        reasoning = entry.get('reasoning', 'No reason')[:60]
                        print(f"  ACTION: {action} - {reasoning}")
                    elif entry_type == 'state_observation':
                        state_summary = entry.get('state_summary', {})
                        in_dialog = state_summary.get('in_dialog', 'unknown')
                        print(f"  STATE: in_dialog={in_dialog}")
                    else:
                        print(f"  {entry_type}")
            else:
                print("❌ Only session_start - agent never ran")
        else:
            print("❌ No log files found")
        
    finally:
        print("\n🛑 Stopping agent...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()

if __name__ == "__main__":
    main()
