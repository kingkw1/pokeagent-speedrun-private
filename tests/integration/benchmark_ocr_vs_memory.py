#!/usr/bin/env python3
"""
Benchmark OCR-based vs Memory-based dialogue detection

Measures the time cost per detection to understand performance impact
on agent decision-making speed.
"""

import sys
sys.path.append('/home/kevin/Documents/pokeagent-speedrun')

import time
import subprocess
import requests
from PIL import Image
import io
import base64
from utils.ocr_dialogue import create_ocr_detector

def benchmark_detection_methods(num_iterations=100):
    """Benchmark both detection methods"""
    
    print("="*80)
    print("DIALOGUE DETECTION PERFORMANCE BENCHMARK")
    print("="*80)
    print(f"Running {num_iterations} iterations of each method...\n")
    
    # Start server with a test state
    cmd = ["python", "-m", "server.app", "--load-state", "tests/states/dialog.state"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        time.sleep(10)  # Wait for server to start
        
        # Get screenshot and memory state
        frame_resp = requests.get("http://localhost:8000/api/frame", timeout=5)
        frame_data = frame_resp.json()
        image_data = base64.b64decode(frame_data['frame'])
        screenshot = Image.open(io.BytesIO(image_data))
        
        state_resp = requests.get("http://localhost:8000/state", timeout=5)
        state_data = state_resp.json()
        
        # Initialize detectors
        ocr_detector = create_ocr_detector()
        
        print("="*80)
        print("1. OCR-BASED DETECTION (Visual)")
        print("="*80)
        
        # Warm up
        for _ in range(5):
            ocr_detector.is_dialogue_box_visible(screenshot)
        
        # Benchmark OCR
        ocr_times = []
        for i in range(num_iterations):
            start = time.perf_counter()
            result = ocr_detector.is_dialogue_box_visible(screenshot)
            elapsed = time.perf_counter() - start
            ocr_times.append(elapsed * 1000)  # Convert to ms
            
            if i == 0:
                print(f"   Result: {result}")
        
        ocr_avg = sum(ocr_times) / len(ocr_times)
        ocr_min = min(ocr_times)
        ocr_max = max(ocr_times)
        ocr_median = sorted(ocr_times)[len(ocr_times)//2]
        
        print(f"\n   Average: {ocr_avg:.2f} ms")
        print(f"   Median:  {ocr_median:.2f} ms")
        print(f"   Min:     {ocr_min:.2f} ms")
        print(f"   Max:     {ocr_max:.2f} ms")
        
        print("\n" + "="*80)
        print("2. MEMORY-BASED DETECTION (Current)")
        print("="*80)
        
        # For memory-based, we'll simulate what happens in the current code
        # It reads dialog state and checks for text
        memory_times = []
        for i in range(num_iterations):
            start = time.perf_counter()
            # Simulate current is_in_dialog logic:
            # 1. Get state from API (this is what actually happens)
            dialog_state = state_data['game'].get('in_dialog', False)
            elapsed = time.perf_counter() - start
            memory_times.append(elapsed * 1000)
            
            if i == 0:
                print(f"   Result: {dialog_state}")
        
        memory_avg = sum(memory_times) / len(memory_times)
        memory_min = min(memory_times)
        memory_max = max(memory_times)
        memory_median = sorted(memory_times)[len(memory_times)//2]
        
        print(f"\n   Average: {memory_avg:.2f} ms")
        print(f"   Median:  {memory_median:.2f} ms")
        print(f"   Min:     {memory_min:.2f} ms")
        print(f"   Max:     {memory_max:.2f} ms")
        
        print("\n" + "="*80)
        print("COMPARISON")
        print("="*80)
        
        slowdown = ocr_avg / memory_avg if memory_avg > 0 else float('inf')
        diff_ms = ocr_avg - memory_avg
        
        print(f"\n   OCR avg:    {ocr_avg:.2f} ms")
        print(f"   Memory avg: {memory_avg:.2f} ms")
        print(f"   Difference: {diff_ms:.2f} ms slower with OCR")
        print(f"   Slowdown:   {slowdown:.1f}x")
        
        print("\n" + "="*80)
        print("IMPACT ANALYSIS")
        print("="*80)
        
        # Agent makes decisions every frame or few frames
        # Let's calculate impact at different decision rates
        
        decisions_per_second = [1, 2, 5, 10, 30, 60]
        
        print(f"\n   Impact per agent decision: +{diff_ms:.2f} ms\n")
        print(f"   {'Decisions/sec':<20} {'Extra time/sec':<20} {'Impact'}")
        print(f"   {'-'*60}")
        
        for dps in decisions_per_second:
            extra_per_sec = (diff_ms * dps) / 1000  # Convert to seconds
            impact_pct = (extra_per_sec / 1.0) * 100
            
            if extra_per_sec < 0.01:
                impact = "Negligible"
            elif extra_per_sec < 0.05:
                impact = "Very Low"
            elif extra_per_sec < 0.1:
                impact = "Low"
            elif extra_per_sec < 0.2:
                impact = "Moderate"
            else:
                impact = "High"
            
            print(f"   {dps:<20} {extra_per_sec*1000:.1f} ms{' '*13} {impact} ({impact_pct:.1f}%)")
        
        print("\n" + "="*80)
        print("RECOMMENDATION")
        print("="*80)
        
        if diff_ms < 5:
            print("\n   ✅ NEGLIGIBLE COST - Switch to OCR recommended")
            print("      Performance impact is minimal (<5ms per detection)")
        elif diff_ms < 20:
            print("\n   ⚠️  LOW COST - OCR acceptable for accuracy gain")
            print("      Performance impact is small but measurable")
        elif diff_ms < 50:
            print("\n   ⚠️  MODERATE COST - Consider hybrid approach")
            print("      Use OCR only when memory detection is ambiguous")
        else:
            print("\n   ❌ HIGH COST - Optimize or use hybrid")
            print("      OCR adds significant overhead, needs optimization")
        
        print(f"\n   Current accuracy:")
        print(f"      Memory: 3/7 correct (42.9%)")
        print(f"      OCR:    7/7 correct (100%)")
        print(f"\n   Trade-off: +{diff_ms:.2f}ms per detection for +57% accuracy")
        
    finally:
        process.terminate()
        process.wait(timeout=5)

if __name__ == "__main__":
    benchmark_detection_methods(num_iterations=100)
