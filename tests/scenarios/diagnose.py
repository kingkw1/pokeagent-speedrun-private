#!/usr/bin/env python3
"""
Diagnostic runner for debugging agent hangs during scenario tests.
This version includes enhanced logging to identify where the agent gets stuck.
"""

import subprocess
import time
import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def diagnose_van_exit(port=8003):
    """Run van exit test with detailed diagnostics"""
    
    print("\n" + "="*70)
    print("🔍 DIAGNOSTIC MODE: Exit Moving Van")
    print("="*70)
    
    save_state = "Emerald-GBAdvance/truck_start.state"
    
    if not os.path.exists(save_state):
        print(f"❌ Save state not found: {save_state}")
        return
    
    # Start the agent
    cmd = [
        sys.executable,
        "run.py",
        "--load-state", save_state,
        "--agent-auto",
        "--headless",
        "--port", str(port)
    ]
    
    print(f"🚀 Starting: {' '.join(cmd)}\n")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        print("⏳ Waiting for server startup...")
        time.sleep(8)
        
        print("\n📊 Monitoring agent behavior (30 steps):\n")
        print(f"{'Step':<6} {'Time':<8} {'Location':<30} {'Pos':<12} {'Status':<15}")
        print("-" * 85)
        
        start_time = time.time()
        last_check_time = start_time
        
        for step in range(30):
            step_start = time.time()
            
            try:
                response = requests.get(f"http://127.0.0.1:{port}/state", timeout=20)
                
                if response.status_code == 200:
                    elapsed = time.time() - start_time
                    step_time = time.time() - step_start
                    
                    state = response.json()
                    location = state.get('player', {}).get('location', 'unknown')
                    pos = state.get('player', {}).get('position', {})
                    pos_str = f"({pos.get('x', '?')},{pos.get('y', '?')})"
                    
                    # Check if agent is making any progress
                    status = "✓ OK"
                    if step_time > 10:
                        status = "⚠ SLOW"
                    
                    print(f"{step:<6} {elapsed:>6.1f}s  {location:<30} {pos_str:<12} {status:<15}")
                    
                    last_check_time = time.time()
                    
                    # Brief pause
                    time.sleep(0.5)
                    
            except requests.exceptions.Timeout:
                elapsed = time.time() - start_time
                since_last = time.time() - last_check_time
                print(f"{step:<6} {elapsed:>6.1f}s  {'TIMEOUT':<30} {'---':<12} ⚠ HUNG ({since_last:.1f}s)")
                
                # If hung for too long, give up
                if since_last > 30:
                    print("\n❌ Agent appears to be completely hung (30+ seconds no response)")
                    break
                    
            except requests.exceptions.ConnectionError:
                print(f"{step:<6} ---      {'CONNECTION LOST':<30} {'---':<12} ❌ CRASH")
                break
                
            except Exception as e:
                print(f"{step:<6} ---      {'ERROR':<30} {'---':<12} ❌ {str(e)[:20]}")
                break
        
        print("\n" + "="*70)
        print("📊 DIAGNOSTIC SUMMARY")
        print("="*70)
        print(f"Total time: {time.time() - start_time:.1f}s")
        print(f"Steps completed: {step + 1}/30")
        print("\n💡 INSIGHTS:")
        print("  - If 'HUNG' appears frequently: VLM is getting stuck on inference")
        print("  - If 'SLOW' appears: VLM is working but taking 10+ seconds per call")
        print("  - If stuck at same position: Navigation oscillation bug")
        print("  - If CONNECTION LOST: Server crashed")
        
    finally:
        print(f"\n🧹 Cleaning up (PID {process.pid})...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("   ✓ Clean shutdown")
        except subprocess.TimeoutExpired:
            process.kill()
            print("   ⚠ Force killed")

if __name__ == "__main__":
    try:
        diagnose_van_exit()
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        sys.exit(1)
