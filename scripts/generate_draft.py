#!/usr/bin/env python3
"""
Draft Generator for VLM Perception Data

This script is a helper tool for data collection pipeline. It takes a single game 
screenshot and uses the production VLM perception logic to generate a draft of 
structured JSON data for manual annotation.

Usage:
    # Single image mode
    python generate_draft.py --image_path data/screenshots/some_image.png
    
    # Batch mode for directory
    python generate_draft.py --directory data/screenshots
"""

import argparse
import json
import re
import sys
from pathlib import Path
from PIL import Image
import glob
import os

# Import VLM and system prompt from the project
sys.path.append(str(Path(__file__).parent.parent))
from utils.vlm import VLM
from agent.system_prompt import system_prompt


def load_image(image_path):
    """Load and validate image file."""
    try:
        image = Image.open(image_path)
        return image
    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return None


def find_png_files(directory):
    """Find all PNG files in the given directory."""
    directory = Path(directory)
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return []
    
    png_files = list(directory.glob("*.png"))
    print(f"📁 Found {len(png_files)} PNG files in {directory}")
    return png_files


def process_single_image(image_path, vlm, output_mode="console"):
    """Process a single image and return/save the JSON result."""
    print(f"🔍 Processing: {image_path}")
    
    # Load the image
    image = load_image(image_path)
    if image is None:
        return None
    
    print(f"✅ Loaded image: {image_path} ({image.size[0]}x{image.size[1]})")
    
    # Create the production extraction prompt
    extraction_prompt = create_extraction_prompt(image_path)
    
    # Combine system prompt with extraction prompt (same as production)
    full_prompt = system_prompt + extraction_prompt
    
    try:
        # Make VLM call
        vlm_response = vlm.get_query(image, full_prompt, "PERCEPTION-EXTRACT")
        
        # Extract and clean JSON
        json_data = extract_json_from_response(vlm_response)
        
        if json_data:
            if output_mode == "console":
                print("✅ Draft JSON generated successfully:")
                print("=" * 60)
                print(json.dumps(json_data, indent=2, ensure_ascii=False))
                print("=" * 60)
            elif output_mode == "file":
                # Save JSON file next to the image
                json_path = Path(image_path).with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                print(f"✅ Saved: {json_path}")
            
            return json_data
        else:
            print("❌ Failed to extract valid JSON from VLM response")
            return None
            
    except Exception as e:
        print(f"❌ Error during VLM call: {e}")
        return None


def create_extraction_prompt(image_path):
    """
    Create the exact same extraction prompt used in production.
    Copied directly from agent/perception.py to ensure consistency.
    """
    # Use the image filename as basic context
    context = f"Screenshot from {Path(image_path).name}"
    
    extraction_prompt = f"""
                Based on the visual frame, extract specific information into this JSON structure.
                Only fill in information that is clearly visible on screen. Use null for missing data.

                Current game context: {context}

                Return ONLY the filled JSON object:

                {{
                "screen_context": null,
                "on_screen_text": {{
                    "dialogue": null,
                    "speaker": null,
                    "menu_title": null,
                    "button_prompts": []
                }},
                "visible_entities": [],
                "menu_state": null,
                "visual_elements": {{
                    "health_bars_visible": false,
                    "pokemon_sprites_visible": false,
                    "overworld_map_visible": false,
                    "text_box_visible": false
                }}
                }}

                Fill screen_context with one of: "overworld", "battle", "menu", "dialogue", "title"
                For visible_entities, list NPCs, trainers, or Pokemon you can see with their approximate positions
                For menu_state, specify the open menu name or "closed"
                """
    return extraction_prompt


def extract_json_from_response(vlm_response):
    """
    Extract JSON from VLM response using the same logic as production.
    Copied from agent/perception.py to ensure consistency.
    """
    # Extract JSON from response (handle cases where VLM adds extra text)
    json_match = re.search(r'\{.*\}', vlm_response, re.DOTALL)
    if json_match:
        try:
            json_data = json.loads(json_match.group(0))
            return json_data
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            print(f"Raw response: {vlm_response}")
            return None
    else:
        print("❌ No JSON found in VLM response")
        print(f"Raw response: {vlm_response}")
        return None


def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(
        description="Generate draft structured JSON data from game screenshots using VLM perception"
    )
    
    # Create mutually exclusive group for single image vs batch mode
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--image_path", 
        help="Path to a single game screenshot image"
    )
    group.add_argument(
        "--directory",
        help="Path to directory containing PNG files for batch processing"
    )
    
    args = parser.parse_args()
    
    # Initialize VLM (hard-coded to Gemini backend for now)
    print("🤖 Initializing VLM backend...")
    try:
        vlm = VLM(backend="gemini", model_name="gemini-2.0-flash-exp")
        print("✅ VLM initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing VLM: {e}")
        sys.exit(1)
    
    if args.image_path:
        # Single image mode
        if not Path(args.image_path).exists():
            print(f"❌ Image file not found: {args.image_path}")
            sys.exit(1)
        
        print(f"🔍 Single image mode: {args.image_path}")
        result = process_single_image(args.image_path, vlm, output_mode="console")
        if result is None:
            sys.exit(1)
            
    elif args.directory:
        # Batch mode
        png_files = find_png_files(args.directory)
        if not png_files:
            print("❌ No PNG files found in directory")
            sys.exit(1)
        
        print(f"🔄 Batch mode: Processing {len(png_files)} files...")
        
        success_count = 0
        for i, png_file in enumerate(png_files, 1):
            print(f"\n[{i}/{len(png_files)}] Processing {png_file.name}...")
            result = process_single_image(png_file, vlm, output_mode="file")
            if result is not None:
                success_count += 1
        
        print(f"\n🎉 Batch processing complete!")
        print(f"✅ Successfully processed: {success_count}/{len(png_files)} files")
        if success_count < len(png_files):
            print(f"⚠️ Failed to process: {len(png_files) - success_count} files")


if __name__ == "__main__":
    main()