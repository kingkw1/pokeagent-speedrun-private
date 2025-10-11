#!/usr/bin/env python3
"""
Quick test to verify the new default Qwen2-VL base model configuration works.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent import Agent

def test_default_config():
    """Test the new default configuration (local backend + Qwen2-VL base model)."""
    
    print("🧪 Testing Default Configuration")
    print("=" * 50)
    
    # Create mock args that match the new defaults
    class MockArgs:
        def __init__(self):
            self.backend = 'local'  # New default
            self.model_name = 'Qwen/Qwen2-VL-2B-Instruct'  # New default
            self.simple = False
    
    try:
        print(f"🔄 Loading agent with default configuration...")
        print(f"   Backend: local")
        print(f"   Model: Qwen/Qwen2-VL-2B-Instruct")
        
        import time
        start_time = time.time()
        
        agent = Agent(MockArgs())
        
        load_time = time.time() - start_time
        
        print(f"✅ Agent loaded successfully in {load_time:.2f} seconds")
        print(f"🎯 VLM backend type: {type(agent.vlm.backend).__name__}")
        print(f"🎯 Model type detected: {getattr(agent.vlm.backend, 'model_type', 'unknown')}")
        
        # Quick VLM test if an image is available
        test_image_path = project_root / "data" / "curated_screenshots" / "screenshot_20251009_203917.png"
        
        if test_image_path.exists():
            print(f"\n🖼️  Testing VLM with sample image...")
            
            from agent.perception import perception_step
            
            start_time = time.time()
            mock_state_data = {"player": {}, "memory": {}}
            result = perception_step(str(test_image_path), mock_state_data, agent.vlm)
            perception_time = time.time() - start_time
            
            print(f"✅ Perception completed in {perception_time:.2f} seconds")
            print(f"📊 Extraction method: {result.get('extraction_method', 'unknown')}")
            print(f"🎯 Screen context: {result.get('visual_data', {}).get('screen_context', 'unknown')}")
            
            if perception_time < 5.0:
                print(f"🚀 Performance excellent: {perception_time:.2f}s is fast enough for near real-time use!")
            elif perception_time < 10.0:
                print(f"⚡ Performance good: {perception_time:.2f}s is suitable for strategic decisions")
            else:
                print(f"⚠️  Performance slow: {perception_time:.2f}s may need optimization")
        else:
            print(f"⚠️  Test image not found, skipping VLM test")
            
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        print("\nPossible solutions:")
        print("1. Ensure HuggingFace transformers is installed")
        print("2. Run 'hf auth login' if the model requires authentication")
        print("3. Check internet connection for model download")
        return False

def main():
    print("🎯 Default Configuration Test")
    print("Testing new default: local backend + Qwen/Qwen2-VL-2B-Instruct")
    print("=" * 80)
    
    success = test_default_config()
    
    if success:
        print(f"\n🎉 SUCCESS! New default configuration is working!")
        print(f"The agent will now use the fast Qwen2-VL base model by default.")
        print(f"\nTo run the agent with default settings:")
        print(f"  python run.py")
        print(f"\nTo use a different model:")
        print(f"  python run.py --backend local --model-name models/perception_v0.1/final_checkpoint")
        return 0
    else:
        print(f"\n❌ Configuration test failed!")
        print(f"Check the error messages above and try the suggested solutions.")
        return 1

if __name__ == '__main__':
    sys.exit(main())