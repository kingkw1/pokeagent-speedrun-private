#!/usr/bin/env python3
"""
Utility script to fix missing processor files in existing model checkpoints.

This script copies the necessary processor files from the base model cache 
to any checkpoint directories that are missing them.
"""

import os
import sys
import argparse
import shutil
import glob
from pathlib import Path

def fix_checkpoint_processor_files(checkpoint_path, base_model_id=None):
    """
    Fix missing processor files for a specific checkpoint.
    
    Args:
        checkpoint_path (str): Path to the checkpoint directory
        base_model_id (str): Base model ID to copy files from (auto-detected if None)
    """
    checkpoint_path = Path(checkpoint_path)
    
    if not checkpoint_path.exists():
        print(f"❌ Checkpoint directory not found: {checkpoint_path}")
        return False
        
    print(f"🔧 Fixing processor files for: {checkpoint_path}")
    
    # Auto-detect base model if not provided
    if base_model_id is None:
        # Check config to determine model type
        config_path = checkpoint_path / "config.json"
        if config_path.exists():
            try:
                import json
                with open(config_path) as f:
                    config = json.load(f)
                    
                model_type = config.get("model_type", "").lower()
                
                if model_type == "qwen2_vl":
                    base_model_id = "Qwen/Qwen2-VL-2B-Instruct"
                elif model_type == "phi3_v":
                    base_model_id = "microsoft/phi-3-vision-128k-instruct" 
                else:
                    # Fallback based on path
                    if "qwen" in str(checkpoint_path).lower():
                        base_model_id = "Qwen/Qwen2-VL-2B-Instruct"
                    else:
                        base_model_id = "microsoft/phi-3-vision-128k-instruct"
                        
            except Exception as e:
                print(f"⚠️  Could not read config: {e}")
                # Fallback based on path
                if "qwen" in str(checkpoint_path).lower():
                    base_model_id = "Qwen/Qwen2-VL-2B-Instruct"
                else:
                    base_model_id = "microsoft/phi-3-vision-128k-instruct"
    
    print(f"📋 Detected base model: {base_model_id}")
    
    # Find base model in cache
    cache_root = Path.home() / ".cache" / "huggingface" / "hub"
    model_cache_name = f"models--{base_model_id.replace('/', '--')}"
    model_cache_dir = cache_root / model_cache_name
    
    if not model_cache_dir.exists():
        print(f"❌ Base model cache not found: {model_cache_dir}")
        print("   Try downloading the base model first:")
        print(f"   python -c \"from transformers import AutoProcessor; AutoProcessor.from_pretrained('{base_model_id}')\"")
        return False
        
    # Find latest snapshot
    snapshots_dir = model_cache_dir / "snapshots"
    if not snapshots_dir.exists():
        print("❌ No snapshots directory found in model cache.")
        return False
        
    snapshot_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]
    if not snapshot_dirs:
        print("❌ No snapshot directories found.")
        return False
        
    latest_snapshot = max(snapshot_dirs, key=lambda x: x.stat().st_mtime)
    print(f"📂 Using snapshot: {latest_snapshot.name}")
    
    # Define files to copy based on model type
    if "qwen" in base_model_id.lower():
        files_to_copy = [
            "preprocessor_config.json",
            "tokenizer_config.json", 
            "tokenizer.json",
            "vocab.json",
            "merges.txt",
            "chat_template.json"
        ]
        model_type_name = "Qwen2-VL"
    else:
        files_to_copy = [
            "preprocessor_config.json",
            "processor_config.json", 
            "tokenizer_config.json",
            "tokenizer.json",
            "special_tokens_map.json",
            "processing_phi3_v.py",
            "image_processing_phi3_v.py"
        ]
        model_type_name = "Phi-3-Vision"
    
    print(f"🎯 Copying {model_type_name} processor files...")
    
    # Copy files
    copied_count = 0
    for filename in files_to_copy:
        src_file = latest_snapshot / filename
        dst_file = checkpoint_path / filename
        
        if src_file.exists():
            try:
                shutil.copy2(src_file, dst_file)
                copied_count += 1
                print(f"  ✅ Copied {filename}")
            except Exception as e:
                print(f"  ❌ Failed to copy {filename}: {e}")
        else:
            print(f"  ⚠️  File not found in cache: {filename}")
    
    success = copied_count > 0
    if success:
        print(f"✅ Successfully copied {copied_count} processor files to {checkpoint_path}")
    else:
        print(f"❌ No processor files were copied to {checkpoint_path}")
        
    return success


def find_broken_checkpoints():
    """Find checkpoint directories that are missing processor files."""
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "models"
    
    broken_checkpoints = []
    
    # Find all checkpoint directories
    for model_dir in models_dir.glob("*/"):
        for checkpoint_dir in model_dir.glob("*checkpoint*"):
            # Check if essential processor files are missing
            essential_files = ["preprocessor_config.json", "tokenizer_config.json"]
            
            missing_files = []
            for filename in essential_files:
                if not (checkpoint_dir / filename).exists():
                    missing_files.append(filename)
            
            if missing_files:
                broken_checkpoints.append({
                    'path': checkpoint_dir,
                    'missing_files': missing_files
                })
    
    return broken_checkpoints


def main():
    parser = argparse.ArgumentParser(description='Fix missing processor files in model checkpoints')
    parser.add_argument('--checkpoint', 
                       help='Specific checkpoint directory to fix')
    parser.add_argument('--base_model', 
                       help='Base model ID to copy files from (auto-detected if not provided)')
    parser.add_argument('--auto-fix', action='store_true',
                       help='Automatically fix all broken checkpoints')
    parser.add_argument('--list-broken', action='store_true',
                       help='List all checkpoints with missing processor files')
    
    args = parser.parse_args()
    
    if args.list_broken:
        print("🔍 Scanning for broken checkpoints...")
        broken_checkpoints = find_broken_checkpoints()
        
        if not broken_checkpoints:
            print("✅ No broken checkpoints found!")
            return 0
            
        print(f"❌ Found {len(broken_checkpoints)} checkpoint(s) with missing processor files:")
        for checkpoint_info in broken_checkpoints:
            print(f"  {checkpoint_info['path']}")
            print(f"    Missing: {', '.join(checkpoint_info['missing_files'])}")
        
        if not args.auto_fix:
            print(f"\nTo fix these, run:")
            print(f"  python {__file__} --auto-fix")
        
    if args.auto_fix:
        print("🔧 Auto-fixing all broken checkpoints...")
        broken_checkpoints = find_broken_checkpoints()
        
        if not broken_checkpoints:
            print("✅ No broken checkpoints found!")
            return 0
            
        fixed_count = 0
        for checkpoint_info in broken_checkpoints:
            if fix_checkpoint_processor_files(checkpoint_info['path'], args.base_model):
                fixed_count += 1
                
        print(f"\n🎯 Fixed {fixed_count}/{len(broken_checkpoints)} checkpoints")
        return 0 if fixed_count == len(broken_checkpoints) else 1
        
    if args.checkpoint:
        success = fix_checkpoint_processor_files(args.checkpoint, args.base_model)
        return 0 if success else 1
        
    # Default: list broken checkpoints
    return main() if parser.parse_args(['--list-broken']) else 1


if __name__ == '__main__':
    sys.exit(main())