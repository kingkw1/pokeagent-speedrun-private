#!/usr/bin/env python3
"""
GPU-optimized test script for perception model integration.

This script explicitly forces GPU usage and optimizes settings for your RTX 5090.
"""

import argparse
import json
import time
import torch
from PIL import Image
from agent import Agent
from agent.perception import perception_step


def create_mock_args(local_model_path):
    """Create a mock args object for Agent initialization."""
    class MockArgs:
        def __init__(self, model_path):
            self.backend = 'local'
            self.model_name = model_path
            self.simple = False
    
    return MockArgs(local_model_path)


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='GPU-optimized test for perception model integration')
    parser.add_argument('--local_model_path', required=True,
                        help='Path to the directory containing the fine-tuned model checkpoint')
    parser.add_argument('--image_path', required=True,
                        help='Path to a single screenshot for testing')
    
    args = parser.parse_args()
    
    # Check GPU availability
    if not torch.cuda.is_available():
        print("❌ CUDA not available! Falling back to CPU.")
        return
    
    print(f"🚀 GPU detected: {torch.cuda.get_device_name(0)}")
    print(f"📊 GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print(f"💾 GPU memory free: {torch.cuda.mem_get_info()[0] / 1024**3:.1f} GB")
    
    # Create mock args object for Agent initialization
    mock_args = create_mock_args(args.local_model_path)
    
    # Initialize the Agent with the local model configuration
    print("🤖 Initializing Agent with GPU support...")
    agent = Agent(mock_args)
    
    # Force GPU usage if not already
    if hasattr(agent.vlm.backend, 'model'):
        device = next(agent.vlm.backend.model.parameters()).device
        print(f"📍 Model is on device: {device}")
        
        if device.type == 'cpu':
            print("⚠️  Model is on CPU, moving to GPU...")
            agent.vlm.backend.model = agent.vlm.backend.model.cuda()
            device = next(agent.vlm.backend.model.parameters()).device
            print(f"✅ Model moved to device: {device}")
    
    # Load the test image
    test_image = Image.open(args.image_path)
    print(f"🖼️  Loaded image: {test_image.size}")
    
    # Create dummy state_data for the test
    state_data = {}
    
    print("🔍 Running perception with GPU acceleration...")
    
    # Monitor GPU memory before inference
    if torch.cuda.is_available():
        torch.cuda.empty_cache()  # Clear any cached memory
        memory_before = torch.cuda.memory_allocated() / 1024**3
        print(f"📊 GPU memory before inference: {memory_before:.2f} GB")
    
    # TIME THE PERCEPTION CALL
    print("⏱️  Starting perception timing...")
    start_time = time.time()
    
    # Call perception_step directly with the loaded image, dummy state, and agent's VLM
    perception_output = perception_step(test_image, state_data, agent.vlm)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Monitor GPU memory after inference
    if torch.cuda.is_available():
        memory_after = torch.cuda.memory_allocated() / 1024**3
        memory_peak = torch.cuda.max_memory_allocated() / 1024**3
        print(f"📊 GPU memory after inference: {memory_after:.2f} GB")
        print(f"📊 GPU memory peak: {memory_peak:.2f} GB")
        
        # Reset peak memory stats
        torch.cuda.reset_peak_memory_stats()
    
    # DETAILED TIMING ANALYSIS
    print("\n" + "="*60)
    print("⏱️  TIMING ANALYSIS")
    print("="*60)
    print(f"🕐 Total perception time: {total_time:.3f} seconds")
    print(f"📈 Frames per second (if used every frame): {1/total_time:.1f} FPS")
    
    # Real-world performance analysis
    if total_time < 0.1:
        print("✅ EXCELLENT: Fast enough for real-time use (>10 FPS)")
    elif total_time < 0.2:
        print("✅ GOOD: Suitable for frequent use (5-10 FPS)")
    elif total_time < 0.5:
        print("⚠️  ACCEPTABLE: Usable but not every frame (2-5 FPS)")
    elif total_time < 1.0:
        print("⚠️  SLOW: Only for occasional use (1-2 FPS)")
    else:
        print("❌ TOO SLOW: Not suitable for real-time gaming (<1 FPS)")
    
    # Speedrunning context analysis
    game_fps = 60  # Pokemon runs at ~60 FPS
    perception_fps = 1 / total_time
    if perception_fps >= game_fps:
        print(f"🎮 Can analyze EVERY frame ({perception_fps:.1f} FPS >= {game_fps} FPS)")
    elif perception_fps >= game_fps / 2:
        print(f"🎮 Can analyze EVERY OTHER frame ({perception_fps:.1f} FPS)")
    elif perception_fps >= game_fps / 4:
        print(f"🎮 Can analyze EVERY 4th frame ({perception_fps:.1f} FPS)")
    else:
        frames_per_analysis = int(game_fps / perception_fps)
        print(f"🎮 Can analyze every {frames_per_analysis}th frame ({perception_fps:.1f} FPS)")
    
    # Check if VLM was actually used (not fallback)
    extraction_method = perception_output.get('extraction_method', 'unknown')
    if extraction_method == 'vlm':
        print("✅ VLM successfully used (not fallback)")
    else:
        print("⚠️  Fallback used - VLM timing not measured")
    
    # Print the formatted JSON output
    print("\n" + "="*60)
    print("PERCEPTION OUTPUT:")
    print("="*60)
    print(json.dumps(perception_output, indent=2))


if __name__ == '__main__':
    main()