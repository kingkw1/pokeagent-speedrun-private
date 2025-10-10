# Quick Reference: Data Collection Scripts

## Generate Draft JSON Files

### Single Image
```bash
python scripts/generate_draft.py --image_path data/screenshots/example.png
```

### Batch Process Directory (Recommended)
```bash
python scripts/generate_draft.py --directory data/screenshots
```

## Aggregate to JSONL Training File

### Basic Aggregation
```bash
python scripts/aggregate_to_jsonl.py --directory data/screenshots --output data/perception_seed.jsonl
```

### With Image Validation
```bash
python scripts/aggregate_to_jsonl.py --directory data/screenshots --output data/perception_seed.jsonl --validate-images
```

## Complete Workflow

1. **Collect screenshots** → `data/screenshots/*.png`
2. **Generate drafts** → `python scripts/generate_draft.py --directory data/screenshots`
3. **Manual review** → Edit `.json` files as needed
4. **Create JSONL** → `python scripts/aggregate_to_jsonl.py --directory data/screenshots --output data/perception_seed.jsonl`

## Output Files

- `data/screenshots/*.json` - Individual draft annotations
- `data/perception_seed.jsonl` - Final training data file