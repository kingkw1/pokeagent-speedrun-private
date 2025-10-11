# Configuration Update: Base Qwen2-VL Model

## What Changed

The PokéAgent system now defaults to using the base `Qwen/Qwen2-VL-2B-Instruct` model instead of our fine-tuned checkpoints.

## Why This Change

Performance testing revealed that the base Qwen2-VL model actually performs **better** than our current fine-tuned versions:

| Model | Inference Time | Performance |
|-------|---------------|-------------|
| Fine-tuned Qwen2-VL | 3.1 seconds | Good |
| **Base Qwen2-VL** | **2.3 seconds** | **Better!** |
| Original Phi-3-Vision | 38+ seconds | Slow |

## New Default Configuration

When you run the agent without specifying a model:

```bash
python run.py
```

It now automatically uses:
- **Backend**: `local` 
- **Model**: `Qwen/Qwen2-VL-2B-Instruct`

## Performance Benefits

✅ **2.3 second inference time** (16x faster than Phi-3-Vision)  
✅ **Lower memory usage** (4.2GB vs 7-9GB)  
✅ **Better accuracy** than current fine-tuned versions  
✅ **No manual model management** - downloads automatically  

## Using Different Models

You can still use any other model:

```bash
# Use fine-tuned model
python run.py --backend local --model-name models/perception_v0.2_qwen_final/checkpoint-3

# Use original Gemini (cloud)
python run.py --backend gemini --model-name gemini-2.5-flash

# Use Phi-3-Vision
python run.py --backend local --model-name models/perception_v0.1/final_checkpoint
```

## Future Plans

We plan to improve our fine-tuning approach with:
- **Larger training datasets** 
- **Better data quality**
- **Improved training techniques**

Once we achieve better performance than the base model, we'll switch back to fine-tuned versions.

## Testing

To verify the new configuration works:

```bash
# Test default configuration
python tests/test_default_config.py

# Test performance 
python tests/test_perception_gpu.py --local_model_path "Qwen/Qwen2-VL-2B-Instruct" --image_path ./data/curated_screenshots/screenshot_20251009_203917.png
```

This change makes the agent faster and more reliable out-of-the-box! 🚀