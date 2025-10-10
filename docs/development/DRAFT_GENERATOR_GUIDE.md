# Draft Generator Usage Guide

## Overview
The `generate_draft.py` script is a helper tool for data collection that uses the production VLM perception logic to generate structured JSON data from game screenshots.

## Purpose
- Speed up manual data annotation process
- Generate consistent structured data using the same logic as the agent
- Provide draft JSON that can be copied, edited, and saved for training data

## Usage

### Basic Command
```bash
python generate_draft.py --image_path path/to/screenshot.png
```

### Example
```bash
python generate_draft.py --image_path data/screenshots/overworld_001.png
```

## Expected Output
The script will print a clean JSON structure to the console:

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
    },
    {
      "type": "npc",
      "name": "Professor Birch",
      "position": "north"
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

## JSON Schema

### `screen_context`
- Type: string
- Values: "overworld", "battle", "menu", "dialogue", "title"
- Description: The current game screen type

### `on_screen_text`
- `dialogue`: Text being spoken (if any)
- `speaker`: Who is speaking (if applicable)
- `menu_title`: Title of open menu (if any)
- `button_prompts`: List of visible button prompts

### `visible_entities`
- Array of objects with:
  - `type`: "player", "npc", "trainer", "pokemon", etc.
  - `name`: Entity name if identifiable
  - `position`: Relative position on screen

### `menu_state`
- Type: string
- Values: Menu name or "closed"
- Description: Current menu state

### `visual_elements`
- Boolean flags for UI elements:
  - `health_bars_visible`: Health/status bars visible
  - `pokemon_sprites_visible`: Pokemon sprites on screen
  - `overworld_map_visible`: Overworld map view active
  - `text_box_visible`: Text/dialogue box visible

## Requirements
- Python 3.7+
- PIL/Pillow for image loading
- VLM backend properly configured
- Valid Gemini API credentials (if using Gemini backend)

## Error Handling
- Validates image file exists before processing
- Graceful error messages for common issues
- Exits with appropriate error codes for scripting

## Integration Notes
- Uses the exact same prompts and logic as `agent/perception.py`
- Maintains consistency with production perception system
- Output can be directly used for training data or testing