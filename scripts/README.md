# Scripts Directory

This directory contains development and utility scripts for the PokeAgent project.

## Training Scripts

### `train_perception_vlm_fast.py`
- **Purpose**: Fast development version of VLM training
- **Model**: Uses Qwen2-VL-2B-Instruct (smaller, faster)
- **Use Case**: Quick prototyping and testing changes before full training
- **Usage**: 
  ```bash
  python scripts/train_perception_vlm_fast.py \
    --dataset_path data/perception_seed.jsonl \
    --output_dir models/test_run \
    --max_steps 10
  ```

## Production Training

For production training, use the main script in the root directory:
```bash
python train_perception_vlm.py \
  --dataset_path data/perception_seed.jsonl \
  --output_dir models/perception_v0.1
```

This uses Phi-3 Vision (8B parameters) and is the proven working configuration.