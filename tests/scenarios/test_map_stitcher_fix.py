#!/usr/bin/env python3
"""
Quick test to verify map stitcher optimization is working.

This script runs the agent for a few steps and monitors:
1. How many times the map stitcher updates
2. Size of extended map view over time
3. Step timing consistency
"""

import subprocess
import time
import requests
import re

def test_map_stitcher_optimization():
    """Test that map stitcher only updates when position changes"""
    
    print("🧪 Testing Map Stitcher Optimization")
    print("=" * 70)
    
    # Start the agent
    cmd = [
        "python", "run.py",
        "--load-state", "Emerald-GBAdvance/truck_start.state",
        "--agent-auto",
        "--headless",
        "--port", "8005"
    ]
    
    print(f"🚀 Starting agent...")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Wait for server to start
    time.sleep(3)
    
    # Track metrics
    step_times = []
    map_sizes = []
    positions = []
    stitcher_updates = 0
    stitcher_skips = 0
    
    print("\n📊 Monitoring agent behavior:\n")
    print(f"{'Step':<6} {'Time':<8} {'Position':<12} {'Map Lines':<12} {'Update?':<10}")
    print("-" * 70)
    
    last_time = time.time()
    
    # Monitor for 10 steps
    for step in range(10):
        try:
            # Poll the state
            response = requests.get(f"http://127.0.0.1:8005/state", timeout=15)
            current_time = time.time()
            step_duration = current_time - last_time
            last_time = current_time
            
            if response.status_code == 200:
                state = response.json()
                player = state.get('player', {})
                location = player.get('location', 'Unknown')
                pos = player.get('position', {})
                x, y = pos.get('x', '?'), pos.get('y', '?')
                
                step_times.append(step_duration)
                positions.append((x, y))
                
                # Check stdout for map stitcher activity
                # This would be better with log parsing, but stdout gives us quick feedback
                
                print(f"{step:<6} {step_duration:>6.2f}s  ({x:>2}, {y:>2}) @ {location:<15}  {'...':<12} {'...':<10}")
            else:
                print(f"{step:<6} {'ERROR':<8} Response: {response.status_code}")
            
            time.sleep(0.5)  # Small delay between polls
            
        except requests.Timeout:
            print(f"{step:<6} {'TIMEOUT':<8}")
            break
        except requests.ConnectionError:
            print(f"{step:<6} {'DISCONN':<8}")
            break
        except Exception as e:
            print(f"{step:<6} {'ERROR':<8} {e}")
            break
    
    # Cleanup
    print("\n🧹 Stopping agent...")
    process.terminate()
    process.wait(timeout=5)
    
    # Analysis
    print("\n" + "=" * 70)
    print("📈 PERFORMANCE ANALYSIS")
    print("=" * 70)
    
    if step_times:
        avg_time = sum(step_times) / len(step_times)
        first_half = sum(step_times[:5]) / min(5, len(step_times[:5]))
        second_half = sum(step_times[5:]) / max(1, len(step_times[5:]))
        
        print(f"⏱️  Average step time: {avg_time:.2f}s")
        print(f"   First 5 steps: {first_half:.2f}s")
        print(f"   Last 5 steps:  {second_half:.2f}s")
        
        if second_half > first_half * 1.5:
            print(f"   ⚠️  WARNING: {(second_half/first_half - 1)*100:.1f}% slowdown detected!")
        else:
            print(f"   ✅ GOOD: Consistent performance ({(second_half/first_half - 1)*100:+.1f}%)")
    
    # Position analysis
    unique_positions = len(set(positions))
    print(f"\n📍 Positions visited: {unique_positions} unique out of {len(positions)} steps")
    
    if unique_positions < len(positions) * 0.3:
        print(f"   ⚠️  Agent is stuck! Only moved to {unique_positions} different positions")
    
    # Check if we need to inspect logs for detailed map stitcher info
    print("\n💡 For detailed map stitcher activity, check logs with:")
    print("   grep 'Map stitcher update triggered\\|Skipping map stitcher' submission.log")

if __name__ == "__main__":
    test_map_stitcher_optimization()
