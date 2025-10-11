# Model Compatibility and Training Improvements

## Overview

This document describes the improvements made to handle multiple trained perception models and automate the fine-tuning process.

**Current Configuration**: The system now defaults to using the base `Qwen/Qwen2-VL-2B-Instruct` model as it performs better than our current fine-tuned versions (2.3s vs 3.1s inference time). We plan to improve fine-tuning with larger datasets in the future.

## Key Improvements

### 1. Universal Model Type Detection (`utils/vlm.py`)

**Problem**: The system only worked with specific model types and couldn't handle different architectures automatically.

**Solution**: Added robust model type detection that supports all trained models:

```python
def _detect_model_type(self, model_name: str) -> str:
    """
    Detect model type from name patterns or config file.
    
    Supports:
    - models/perception_v0.1/* (phi-3-vision)  
    - models/perception_v0.2_qwen* (qwen2-vl)
    - Any Hugging Face model names
    """
```

**Supported Models**:
- ✅ `models/perception_v0.1/final_checkpoint` (Phi-3-Vision)
- ✅ `models/perception_v0.1/checkpoint-*` (Phi-3-Vision) 
- ✅ `models/perception_v0.2_qwen*/checkpoint-*` (Qwen2-VL)
- ✅ `Qwen/Qwen2-VL-2B-Instruct` (Base Qwen2-VL)
- ✅ `microsoft/phi-3-vision-128k-instruct` (Base Phi-3)

### 2. Automated Processor File Copying (`train_perception_vlm.py`)

**Problem**: Fine-tuned models were missing processor files needed for loading, requiring manual copying every time.

**Solution**: Added automatic processor file copying after training:

```python
def _copy_processor_files(base_model_id: str, output_dir: str) -> None:
    """
    Copy processor files from base model cache to all checkpoint directories.
    Ensures fine-tuned models have all necessary files for loading.
    """
```

**Features**:
- ✅ Automatically detects model type (Qwen2-VL vs Phi-3-Vision)
- ✅ Copies the correct processor files for each model type
- ✅ Works with all checkpoint directories  
- ✅ Provides detailed progress reporting
- ✅ Handles missing files gracefully with helpful error messages

### 3. Model Checkpoint Repair Tool (`scripts/fix_model_checkpoints.py`)

**Problem**: Existing models with missing processor files couldn't be loaded.

**Solution**: Created a utility script to fix broken checkpoints:

```bash
# List broken checkpoints
python scripts/fix_model_checkpoints.py --list-broken

# Auto-fix all broken checkpoints  
python scripts/fix_model_checkpoints.py --auto-fix

# Fix specific checkpoint
python scripts/fix_model_checkpoints.py --checkpoint models/perception_v0.1/checkpoint-3
```

**Features**:
- ✅ Scans for missing processor files automatically
- ✅ Auto-detects model type from config or path
- ✅ Copies files from HuggingFace cache
- ✅ Batch processing for multiple checkpoints

### 4. Comprehensive Testing (`tests/test_all_models.py`)

**Problem**: No easy way to verify all models work correctly.

**Solution**: Created a test script that validates all available models:

```bash
# Test all available models
python tests/test_all_models.py

# Test specific models
python tests/test_all_models.py --models models/perception_v0.1/final_checkpoint
```

**Features**:
- ✅ Auto-discovers all available models
- ✅ Tests model loading and basic functionality
- ✅ Performance comparison between models
- ✅ Detailed error reporting

## Usage Examples

### Training a New Model (Fully Automated)

```bash
# Train Qwen2-VL model - processor files copied automatically
python train_perception_vlm.py \
    --model_id "Qwen/Qwen2-VL-2B-Instruct" \
    --dataset_path data/perception_seed.jsonl \
    --output_dir models/perception_v0.3_qwen

# The checkpoint will be immediately usable!
python tests/test_perception_gpu.py \
    --local_model_path models/perception_v0.3_qwen/checkpoint-3 \
    --image_path ./data/curated_screenshots/screenshot_20251009_203917.png
```

### Using Any Trained Model

```python
from agent import Agent

# Works with any model automatically
models = [
    "models/perception_v0.1/final_checkpoint",           # Phi-3-Vision
    "models/perception_v0.2_qwen_final/checkpoint-3",    # Qwen2-VL fine-tuned
    "Qwen/Qwen2-VL-2B-Instruct",                        # Qwen2-VL base
]

for model_path in models:
    class MockArgs:
        def __init__(self, model_path):
            self.backend = 'local'
            self.model_name = model_path
            self.simple = False
    
    agent = Agent(MockArgs(model_path))  # Auto-detects model type
    # Agent is ready to use!
```

### Fixing Broken Models

```bash
# Check for broken models
python scripts/fix_model_checkpoints.py --list-broken

# Fix them all  
python scripts/fix_model_checkpoints.py --auto-fix
```

## Model Performance Summary

| Model | Type | Load Time | Inference Time | Notes |
|-------|------|-----------|----------------|-------|
| `perception_v0.1/final_checkpoint` | Phi-3-Vision | ~5s | ~38s | Original model |
| `perception_v0.2_qwen_final/checkpoint-3` | Qwen2-VL | ~3s | ~3s | Fine-tuned (slower than base) |
| `Qwen/Qwen2-VL-2B-Instruct` | Qwen2-VL Base | ~3s | ~2.3s | **🎯 Current default - 16x faster!** |

## What You Need to Handle Manually

### 1. HuggingFace Authentication
Some models may require authentication:
```bash
huggingface-cli login
# or
hf auth login
```

### 2. Missing Model Files  
If the base model isn't in your HuggingFace cache, download it first:
```python
from transformers import AutoProcessor
AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
```

### 3. Custom Model Types
For new model architectures, you may need to:
1. Add detection patterns to `_detect_model_type()`
2. Add the model class import in the VLM backend
3. Add processor file patterns to the copying functions

## Error Messages and Solutions

### "Unrecognized model type"
- **Cause**: New model architecture not detected
- **Solution**: Add pattern to `_detect_model_type()` or specify base model manually

### "Processor files not found"  
- **Cause**: Base model not in HuggingFace cache
- **Solution**: Download base model first or use `--auto-fix`

### "Model loading failed"
- **Cause**: Missing processor files in checkpoint
- **Solution**: Run `python scripts/fix_model_checkpoints.py --auto-fix`

## Future Enhancements

The system is designed to be extensible. To add support for new model types:

1. **Add detection pattern** in `utils/vlm.py:_detect_model_type()`
2. **Add model class import** in `utils/vlm.py:__init__()`  
3. **Add processor files list** in `train_perception_vlm.py:_copy_processor_files()`
4. **Add format handling** in `utils/vlm.py:get_vlm_query()`

The improvements ensure that any new models you train will work immediately without manual intervention!