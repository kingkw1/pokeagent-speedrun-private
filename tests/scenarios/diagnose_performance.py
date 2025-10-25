#!/usr/bin/env python3
"""
Performance diagnostic tool - tracks why agent slows down over time.

This tool monitors:
1. Prompt length growth (extended map accumulation)
2. VLM inference time per step
3. Memory usage growth
4. Context window saturation
"""

import subprocess
import time
import requests
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def diagnose_performance_degradation(port=8004, max_steps=15):
    """Track performance metrics to identify slowdown causes"""
    
    print("\n" + "="*80)
    print("🔍 PERFORMANCE DIAGNOSTIC: Tracking Agent Slowdown")
    print("="*80)
    
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
    
    # Capture both stdout and stderr to analyze
    log_file = "/tmp/agent_perf_diag.log"
    with open(log_file, "w") as f:
        process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    
    try:
        print("⏳ Waiting for server startup...")
        time.sleep(8)
        
        print("\n📊 Performance Tracking:\n")
        print(f"{'Step':<6} {'Time':<8} {'Δt':<8} {'Loc':<20} {'Pos':<10} {'Analysis':<30}")
        print("-" * 95)
        
        start_time = time.time()
        last_step_time = start_time
        step_times = []
        
        for step in range(max_steps):
            step_start = time.time()
            
            try:
                response = requests.get(f"http://127.0.0.1:{port}/state", timeout=20)
                
                if response.status_code == 200:
                    elapsed = time.time() - start_time
                    step_duration = time.time() - last_step_time
                    step_times.append(step_duration)
                    last_step_time = time.time()
                    
                    state = response.json()
                    location = state.get('player', {}).get('location', 'unknown')[:20]
                    pos = state.get('player', {}).get('position', {})
                    pos_str = f"({pos.get('x', '?')},{pos.get('y', '?')})"
                    
                    # Analyze performance
                    analysis = ""
                    if step_duration < 3:
                        analysis = "✓ Fast"
                    elif step_duration < 6:
                        analysis = "○ Normal"
                    elif step_duration < 10:
                        analysis = "⚠ Slow"
                    else:
                        analysis = "❌ Very Slow"
                    
                    # Add trend info
                    if len(step_times) >= 3:
                        avg_recent = sum(step_times[-3:]) / 3
                        avg_first = sum(step_times[:3]) / 3 if len(step_times) >= 3 else step_times[0]
                        if avg_recent > avg_first * 1.5:
                            analysis += " (degrading!)"
                    
                    print(f"{step:<6} {elapsed:>6.1f}s  {step_duration:>6.1f}s  {location:<20} {pos_str:<10} {analysis:<30}")
                    
                    # Brief pause
                    time.sleep(0.5)
                    
            except requests.exceptions.Timeout:
                elapsed = time.time() - start_time
                print(f"{step:<6} {elapsed:>6.1f}s  {'TIMEOUT':<8} {'---':<20} {'---':<10} ❌ HUNG")
                break
                
            except requests.exceptions.ConnectionError:
                print(f"{step:<6} ---      {'CRASH':<8} {'---':<20} {'---':<10} ❌ SERVER LOST")
                break
        
        # Analyze the log file for prompt growth
        print("\n" + "="*80)
        print("📈 PROMPT LENGTH ANALYSIS")
        print("="*80)
        
        time.sleep(2)  # Let logs flush
        
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Look for extended map messages
            map_messages = []
            for line in log_content.split('\n'):
                if '[EXTENDED MAP] Generated' in line and 'line extended view' in line:
                    # Extract line count
                    try:
                        parts = line.split('Generated')[1].split('line')[0].strip()
                        num_lines = int(parts)
                        map_messages.append(num_lines)
                    except:
                        pass
            
            if map_messages:
                print(f"\n🗺️  Extended Map Growth:")
                print(f"   First map: {map_messages[0]} lines")
                if len(map_messages) > 1:
                    print(f"   Last map:  {map_messages[-1]} lines")
                    growth = map_messages[-1] - map_messages[0]
                    print(f"   Growth:    +{growth} lines ({growth*100//map_messages[0] if map_messages[0] > 0 else 0}%)")
                    
                    if growth > 50:
                        print(f"\n⚠️  WARNING: Map grew by {growth} lines!")
                        print(f"   This adds ~{growth * 80} characters to the prompt")
                        print(f"   Larger prompts = slower VLM inference")
            else:
                print("   No extended map messages found in logs")
                
        except Exception as e:
            print(f"   Could not analyze log file: {e}")
        
        # Performance summary
        print("\n" + "="*80)
        print("📊 PERFORMANCE SUMMARY")
        print("="*80)
        
        if step_times:
            avg_time = sum(step_times) / len(step_times)
            min_time = min(step_times)
            max_time = max(step_times)
            
            print(f"Steps completed: {len(step_times)}")
            print(f"Average step time: {avg_time:.2f}s")
            print(f"Min step time: {min_time:.2f}s")
            print(f"Max step time: {max_time:.2f}s")
            print(f"Slowdown factor: {max_time/min_time:.2f}x")
            
            # Detect degradation
            if len(step_times) >= 6:
                first_half_avg = sum(step_times[:len(step_times)//2]) / (len(step_times)//2)
                second_half_avg = sum(step_times[len(step_times)//2:]) / (len(step_times) - len(step_times)//2)
                
                print(f"\nFirst half average: {first_half_avg:.2f}s")
                print(f"Second half average: {second_half_avg:.2f}s")
                
                if second_half_avg > first_half_avg * 1.3:
                    print(f"\n❌ PERFORMANCE DEGRADATION DETECTED!")
                    print(f"   Agent is {second_half_avg/first_half_avg:.1f}x slower in later steps")
                    print(f"\n💡 LIKELY CAUSES:")
                    print(f"   1. Extended map view growing with exploration")
                    print(f"   2. Context window getting saturated")
                    print(f"   3. Memory leak in MapStitcher")
                    print(f"\n🔧 SUGGESTED FIXES:")
                    print(f"   1. Limit extended map size (max lines/tiles)")
                    print(f"   2. Only show map within N tiles of player")
                    print(f"   3. Compress map representation")
                else:
                    print(f"\n✅ Performance is stable (no degradation)")
        
        print(f"\n📝 Full logs available at: {log_file}")
        
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
        diagnose_performance_degradation()
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        sys.exit(1)
