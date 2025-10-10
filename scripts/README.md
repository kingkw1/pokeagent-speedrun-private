# Data Collection Pipeline Scripts

This directory contains two scripts for the data collection pipeline that help generate and aggregate structured JSON data from game screenshots.

## Scripts Overview

### 1. `generate_draft.py` - VLM Draft Generator
Generates structured JSON data from screenshots using the production VLM perception logic.

### 2. `aggregate_to_jsonl.py` - JSONL Aggregator
Combines individual JSON files into a single JSONL file for training data.

---

## generate_draft.py

### Purpose
- Generate draft structured JSON annotations from game screenshots
- Uses the exact same VLM prompts and logic as the production agent
- Supports both single image and batch processing modes

### Usage

#### Single Image Mode
```bash
python scripts/generate_draft.py --image_path data/screenshots/some_image.png
```

#### Batch Mode (Recommended)
```bash
python scripts/generate_draft.py --directory data/screenshots
```

### Behavior
- **Single Mode**: Prints JSON to console for copy/paste
- **Batch Mode**: Creates `.json` files next to each `.png` file in the directory

### Example Output Structure
```json
{
  "screen_context": "overworld",
  "on_screen_text": {
    "dialogue": null,
    "speaker": null,
    "menu_title": null,
    "button_prompts": []
  },
  "visible_entities": [
    {
      "type": "player",
      "name": "ASH",
      "position": "center"
    }
  ],
  "menu_state": "closed",
  "visual_elements": {
    "health_bars_visible": false,
    "pokemon_sprites_visible": false,
    "overworld_map_visible": true,
    "text_box_visible": false
  }
}
```

---

## aggregate_to_jsonl.py

### Purpose
- Combine individual JSON files into a single JSONL (JSON Lines) file
- Format data for training or analysis pipelines
- Validate that corresponding image files exist

### Usage

#### Basic Aggregation
```bash
python scripts/aggregate_to_jsonl.py --directory data/screenshots --output data/perception_seed.jsonl
```

#### With Image Validation
```bash
python scripts/aggregate_to_jsonl.py --directory data/screenshots --output data/perception_seed.jsonl --validate-images
```

### Output Format
Each line in the JSONL file contains:
```json
{"image_path": "data/screenshots/1728512400.png", "json_string": "{\"screen_context\":\"overworld\",\"on_screen_text\":{\"dialogue\":null,\"speaker\":null,\"menu_title\":null,\"button_prompts\":[]},\"visible_entities\":[],\"menu_state\":\"closed\",\"visual_elements\":{\"health_bars_visible\":false,\"pokemon_sprites_visible\":false,\"overworld_map_visible\":true,\"text_box_visible\":false}}"}
```

---

## Complete Workflow

### Step 1: Collect Screenshots
Gather ~50 PNG screenshots in a directory (e.g., `data/screenshots/`)

### Step 2: Generate Draft JSON Files
```bash
# Generate JSON files for all PNGs in the directory
python scripts/generate_draft.py --directory data/screenshots
```
This creates `.json` files next to each `.png` file.

### Step 3: Manual Review and Editing
- Review each generated JSON file
- Edit and correct the data as needed
- Ensure accuracy for your 10 best examples

### Step 4: Aggregate to JSONL
```bash
# Create the final JSONL file
python scripts/aggregate_to_jsonl.py --directory data/screenshots --output data/perception_seed.jsonl --validate-images
```

### Final Output
- `data/screenshots/` - Directory with PNG and JSON file pairs
- `data/perception_seed.jsonl` - Single file with all labeled examples

---

## Features

### generate_draft.py Features
- ✅ Single image and batch processing modes
- ✅ Uses production VLM prompts for consistency
- ✅ Handles errors gracefully with detailed logging
- ✅ Creates JSON files alongside PNG files in batch mode
- ✅ Progress tracking for batch operations

### aggregate_to_jsonl.py Features
- ✅ Finds and aggregates all JSON files in a directory
- ✅ Optional image validation to ensure PNG files exist
- ✅ Relative path handling for cleaner output
- ✅ Detailed progress reporting and error handling
- ✅ Example output display for verification

---

## Error Handling

Both scripts include comprehensive error handling:
- File existence validation
- JSON parsing error handling
- VLM initialization and timeout handling
- Graceful degradation with informative error messages
- Exit codes for scripting integration

---

## Dependencies

- Python 3.7+
- PIL/Pillow for image processing
- VLM backend (Gemini configured)
- Valid API credentials for VLM service

---

## Integration Notes

- Scripts use the exact same perception logic as `agent/perception.py`
- JSON schema matches the production agent expectations
- Output format is compatible with training pipelines
- Maintains consistency across the entire data collection workflow