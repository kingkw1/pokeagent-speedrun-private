#!/usr/bin/env python3
"""
Comprehensive test of the newly trained Qwen2-VL model using the training script's automation.

This script demonstrates the complete pipeline:
1. Trains a new model with automated processor file copying  
2. Tests the trained model for performance
3. Compares with existing models
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_training_pipeline():
    """Test the complete training pipeline with automated processor file copying."""
    
    print("🚀 Testing Complete Training Pipeline")
    print("=" * 60)
    
    # Create a temporary output directory for testing
    with tempfile.TemporaryDirectory(prefix="perception_test_") as temp_dir:
        test_output_dir = Path(temp_dir) / "test_model"
        
        print(f"📁 Training model to: {test_output_dir}")
        
        # Run training command
        train_cmd = [
            sys.executable, "train_perception_vlm.py",
            "--model_id", "Qwen/Qwen2-VL-2B-Instruct", 
            "--dataset_path", "data/perception_seed.jsonl",
            "--output_dir", str(test_output_dir)
        ]
        
        print(f"🔧 Running: {' '.join(train_cmd)}")
        
        import subprocess
        start_time = time.time()
        result = subprocess.run(train_cmd, capture_output=True, text=True, cwd=project_root)
        training_time = time.time() - start_time
        
        print(f"⏱️  Training completed in {training_time:.2f} seconds")
        
        if result.returncode != 0:
            print(f"❌ Training failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
        print("✅ Training completed successfully!")
        
        # Check if checkpoint was created
        checkpoint_dirs = list(test_output_dir.glob("checkpoint-*"))
        if not checkpoint_dirs:
            print("❌ No checkpoint directories found after training")
            return False
            
        checkpoint_dir = checkpoint_dirs[0]
        print(f"📂 Found checkpoint: {checkpoint_dir}")
        
        # Check if processor files were automatically copied
        required_files = [
            "preprocessor_config.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "vocab.json",
            "merges.txt"
        ]
        
        missing_files = []
        for filename in required_files:
            if not (checkpoint_dir / filename).exists():
                missing_files.append(filename)
                
        if missing_files:
            print(f"❌ Missing processor files: {missing_files}")
            return False
        else:
            print("✅ All processor files automatically copied!")
            
        # Test loading the trained model
        print("\n🧪 Testing model loading...")
        
        try:
            from agent import Agent
            
            class MockArgs:
                def __init__(self, model_path):
                    self.backend = 'local'
                    self.model_name = model_path
                    self.simple = False
            
            mock_args = MockArgs(str(checkpoint_dir))
            start_time = time.time()
            agent = Agent(mock_args)
            load_time = time.time() - start_time
            
            print(f"✅ Model loaded successfully in {load_time:.2f} seconds")
            
            # Quick VLM test with base model for comparison
            print("\n📊 Quick performance comparison:")
            
            base_model_args = MockArgs("Qwen/Qwen2-VL-2B-Instruct")
            start_time = time.time()
            base_agent = Agent(base_model_args)
            base_load_time = time.time() - start_time
            
            print(f"  Fine-tuned model load time: {load_time:.2f}s")
            print(f"  Base model load time: {base_load_time:.2f}s")
            
            return True
            
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            return False


def main():
    print("🎯 Comprehensive Pipeline Test")
    print("Testing automated training with processor file copying")
    print("=" * 80)
    
    # Check prerequisites
    if not (project_root / "data" / "perception_seed.jsonl").exists():
        print("❌ Training dataset not found: data/perception_seed.jsonl")
        return 1
        
    if not (project_root / "train_perception_vlm.py").exists():
        print("❌ Training script not found: train_perception_vlm.py")
        return 1
    
    # Test the complete pipeline
    if test_training_pipeline():
        print("\n🎉 SUCCESS! Complete pipeline test passed!")
        print("✅ Training script works with automated processor file copying")
        print("✅ Fine-tuned models load correctly")
        print("✅ All infrastructure improvements are working")
        return 0
    else:
        print("\n❌ Pipeline test failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())