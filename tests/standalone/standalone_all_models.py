#!/usr/bin/env python3
"""
Test script to verify all trained perception models work correctly.

This script tests all available perception models to ensure they load and run properly.
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent import Agent
from agent.perception import perception_step


def create_mock_args(model_path):
    """Create a mock args object for Agent initialization."""
    class MockArgs:
        def __init__(self, model_path):
            self.backend = 'local'
            self.model_name = model_path
            self.simple = False
    
    return MockArgs(model_path)


def test_model(model_path, image_path):
    """
    Test a single model with the given image.
    
    Returns:
        dict: Test results with timing and success info
    """
    print(f"\n{'='*60}")
    print(f"Testing Model: {model_path}")
    print(f"{'='*60}")
    
    try:
        # Initialize agent
        mock_args = create_mock_args(model_path)
        start_time = time.time()
        agent = Agent(mock_args)
        init_time = time.time() - start_time
        
        print(f"✅ Model loaded successfully in {init_time:.2f} seconds")
        
        # Test perception (note: perception_step expects frame, state_data, vlm)
        start_time = time.time()
        # Mock state data since we're just testing the VLM loading
        mock_state_data = {"player": {}, "memory": {}}
        result = perception_step(image_path, mock_state_data, agent.vlm)
        perception_time = time.time() - start_time
        
        print(f"✅ Perception completed in {perception_time:.2f} seconds")
        print(f"📊 Extraction method: {result.get('extraction_method', 'unknown')}")
        print(f"🎯 Screen context: {result.get('visual_data', {}).get('screen_context', 'unknown')}")
        
        return {
            'model': model_path,
            'success': True,
            'init_time': init_time,
            'perception_time': perception_time,
            'extraction_method': result.get('extraction_method', 'unknown'),
            'screen_context': result.get('visual_data', {}).get('screen_context', 'unknown')
        }
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return {
            'model': model_path,
            'success': False,
            'error': str(e),
            'init_time': None,
            'perception_time': None
        }


def find_available_models():
    """
    Find all available trained models in the models directory.
    
    Returns:
        list: List of model paths
    """
    models_dir = project_root / "models"
    available_models = []
    
    # Known model patterns
    model_patterns = [
        "perception_v0.1/final_checkpoint",
        "perception_v0.2_qwen/checkpoint-*", 
        "perception_v0.2_qwen_final/checkpoint-*"
    ]
    
    for pattern in model_patterns:
        pattern_path = models_dir / pattern
        if "*" in pattern:
            # Handle glob patterns
            import glob
            matches = glob.glob(str(pattern_path))
            available_models.extend(matches)
        else:
            # Handle direct paths
            if pattern_path.exists():
                available_models.append(str(pattern_path))
    
    # Also check for any other checkpoint directories
    for model_dir in models_dir.glob("*/"):
        for checkpoint_dir in model_dir.glob("checkpoint-*"):
            checkpoint_path = str(checkpoint_dir)
            if checkpoint_path not in available_models:
                available_models.append(checkpoint_path)
                
    return sorted(available_models)


def main():
    parser = argparse.ArgumentParser(description='Test all available perception models')
    parser.add_argument('--image_path', 
                       default='./data/curated_screenshots/screenshot_20251009_203917.png',
                       help='Path to test image')
    parser.add_argument('--models', nargs='*',
                       help='Specific models to test (default: all available)')
    
    args = parser.parse_args()
    
    # Verify test image exists
    if not os.path.exists(args.image_path):
        print(f"❌ Test image not found: {args.image_path}")
        return 1
    
    # Find models to test
    if args.models:
        models_to_test = args.models
    else:
        models_to_test = find_available_models()
    
    if not models_to_test:
        print("❌ No models found to test!")
        print("Expected models in:")
        print("  - models/perception_v0.1/final_checkpoint")
        print("  - models/perception_v0.2_qwen*/checkpoint-*")
        return 1
    
    print(f"🔍 Found {len(models_to_test)} model(s) to test")
    print(f"📸 Using test image: {args.image_path}")
    
    # Test each model
    results = []
    for model_path in models_to_test:
        if not os.path.exists(model_path):
            print(f"\n⚠️  Skipping non-existent model: {model_path}")
            continue
            
        result = test_model(model_path, args.image_path)
        results.append(result)
    
    # Summary report
    print(f"\n{'='*80}")
    print("SUMMARY REPORT")
    print(f"{'='*80}")
    
    successful_models = [r for r in results if r['success']]
    failed_models = [r for r in results if not r['success']]
    
    print(f"✅ Successful models: {len(successful_models)}")
    print(f"❌ Failed models: {len(failed_models)}")
    
    if successful_models:
        print(f"\n📊 Performance Comparison:")
        print(f"{'Model':<50} {'Init Time':<12} {'Perception':<12} {'Method':<12} {'Context'}")
        print("-" * 100)
        
        for result in successful_models:
            model_name = os.path.basename(result['model'])
            init_time = f"{result['init_time']:.2f}s" if result['init_time'] else "N/A"
            perc_time = f"{result['perception_time']:.2f}s" if result['perception_time'] else "N/A"
            method = result.get('extraction_method', 'N/A')[:10]
            context = result.get('screen_context', 'N/A')[:15]
            
            print(f"{model_name:<50} {init_time:<12} {perc_time:<12} {method:<12} {context}")
    
    if failed_models:
        print(f"\n❌ Failed Models:")
        for result in failed_models:
            print(f"  {result['model']}: {result.get('error', 'Unknown error')}")
    
    print(f"\n🎯 All models tested! Check individual results above.")
    return 0 if not failed_models else 1


if __name__ == '__main__':
    sys.exit(main())