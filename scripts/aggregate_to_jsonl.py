#!/usr/bin/env python3
"""
JSON to JSONL Aggregator

This script aggregates individual JSON files in a directory into a single JSONL 
(JSON Lines) file for training data. Each line in the output contains the image 
path and the JSON data as a string.

Usage:
    python aggregate_to_jsonl.py --directory data/screenshots --output data/perception_seed.jsonl
"""

import argparse
import json
import sys
from pathlib import Path


def find_json_files(directory):
    """Find all JSON files in the given directory."""
    directory = Path(directory)
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return []
    
    json_files = list(directory.glob("*.json"))
    print(f"📁 Found {len(json_files)} JSON files in {directory}")
    return sorted(json_files)  # Sort for consistent ordering


def load_json_file(json_path):
    """Load and validate a JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ Error loading {json_path}: {e}")
        return None


def create_jsonl_entry(json_path, json_data):
    """Create a JSONL entry with image path and JSON string."""
    # Find corresponding image file (same name, .png extension)
    image_path = json_path.with_suffix('.png')
    
    # Convert to relative path for cleaner output
    try:
        # Try to make it relative to current working directory
        relative_image_path = image_path.relative_to(Path.cwd())
        image_path_str = str(relative_image_path)
    except ValueError:
        # If can't make relative, use absolute path
        image_path_str = str(image_path)
    
    # Create the JSONL entry
    jsonl_entry = {
        "image_path": image_path_str,
        "json_string": json.dumps(json_data, separators=(',', ':'), ensure_ascii=False)
    }
    
    return jsonl_entry


def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(
        description="Aggregate JSON files into JSONL format for training data"
    )
    parser.add_argument(
        "--directory",
        required=True,
        help="Directory containing JSON files to aggregate"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSONL file path (e.g., data/perception_seed.jsonl)"
    )
    parser.add_argument(
        "--validate-images",
        action="store_true",
        help="Validate that corresponding PNG files exist for each JSON file"
    )
    
    args = parser.parse_args()
    
    # Find all JSON files
    json_files = find_json_files(args.directory)
    if not json_files:
        print("❌ No JSON files found")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 Processing {len(json_files)} JSON files...")
    
    jsonl_entries = []
    success_count = 0
    
    for i, json_file in enumerate(json_files, 1):
        print(f"[{i}/{len(json_files)}] Processing {json_file.name}...")
        
        # Load JSON data
        json_data = load_json_file(json_file)
        if json_data is None:
            continue
        
        # Validate corresponding image exists if requested
        if args.validate_images:
            image_path = json_file.with_suffix('.png')
            if not image_path.exists():
                print(f"⚠️ Warning: No corresponding PNG file for {json_file.name}")
                continue
        
        # Create JSONL entry
        jsonl_entry = create_jsonl_entry(json_file, json_data)
        jsonl_entries.append(jsonl_entry)
        success_count += 1
    
    if not jsonl_entries:
        print("❌ No valid JSON entries found")
        sys.exit(1)
    
    # Write JSONL file
    print(f"💾 Writing JSONL file: {output_path}")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in jsonl_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        print(f"✅ Successfully created JSONL file!")
        print(f"📊 Entries written: {len(jsonl_entries)}")
        print(f"📄 Output file: {output_path}")
        
        # Show example of first entry
        if jsonl_entries:
            print(f"\n📋 Example entry:")
            print(json.dumps(jsonl_entries[0], indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"❌ Error writing JSONL file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()