#!/usr/bin/env python3
"""
Fast Training Script for VLM Perception

This is a lightweight version of the training script that uses a smaller, faster model
for quick testing and development. Use this for initial experimentation before moving
to the full-scale training.
"""

import argparse
import json
import os
from typing import List, Dict, Any

import torch
from PIL import Image
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoProcessor,
    AutoConfig,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)

# --- Dataset Loading and Dataset Class (same as main script) ---

def load_jsonl(dataset_path: str) -> List[Dict[str, Any]]:
    """Loads a .jsonl file into a list of dictionaries."""
    data = []
    with open(dataset_path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

class VLMInstructionDataset(Dataset):
    """Custom PyTorch dataset for fine-tuning a Vision-Language Model."""
    
    def __init__(self, data: List[Dict[str, Any]], processor: AutoProcessor, dataset_path: str):
        self.data = data
        self.processor = processor
        self.dataset_dir = os.path.dirname(dataset_path)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        item = self.data[idx]

        # Load image - handle relative paths correctly
        image_path = item['image_path']
        if not os.path.isabs(image_path):
            # If it's a relative path, check if it already includes the base directory
            if image_path.startswith('data/'):
                # Path already includes 'data/', use it directly from project root
                image_path = os.path.join(os.path.dirname(self.dataset_dir), image_path)
            else:
                # Path is relative to dataset directory
                image_path = os.path.join(self.dataset_dir, image_path)
        
        image = Image.open(image_path).convert("RGB")
        json_string_output = item['json_string']

        # Format prompt with Qwen2-VL format
        prompt = (
            f"<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>"
            f"Extract specific information from this Pokemon game screenshot into JSON format. "
            f"Return ONLY the filled JSON object.<|im_end|>\n"
            f"<|im_start|>assistant\n{json_string_output}<|im_end|>"
        )

        # Process text and image
        inputs = self.processor(text=prompt, images=image, return_tensors="pt")

        # Set up labels for training
        labels = inputs["input_ids"].clone()
        
        # Mask the user prompt part to only train on the assistant response
        user_prompt_part = (
            f"<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>"
            f"Extract specific information from this Pokemon game screenshot into JSON format. "
            f"Return ONLY the filled JSON object.<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        user_tokens = self.processor.tokenizer(user_prompt_part, return_tensors="pt")
        user_prompt_len = user_tokens.input_ids.shape[1]
        labels[0, :user_prompt_len] = -100

        # Handle padding
        if self.processor.tokenizer.pad_token_id is not None:
            labels[labels == self.processor.tokenizer.pad_token_id] = -100

        # Squeeze tensors
        inputs = {k: v.squeeze(0) for k, v in inputs.items()}
        inputs["labels"] = labels.squeeze(0)

        return inputs

def main():
    """Main training function with smaller, faster model."""
    parser = argparse.ArgumentParser(description="Fast VLM fine-tuning for development")
    parser.add_argument("--dataset_path", type=str, required=True, help="Path to .jsonl file")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen2-VL-2B-Instruct", 
                       help="Model ID (default uses smaller efficient model)")
    parser.add_argument("--max_steps", type=int, default=50, help="Maximum training steps")
    
    args = parser.parse_args()

    print("🚀 Fast VLM Training")
    print(f"Model: {args.model_id}")
    print(f"Dataset: {args.dataset_path}")
    print(f"Output: {args.output_dir}")
    print(f"Max steps: {args.max_steps}")

    # Validate and setup
    if not os.path.exists(args.dataset_path):
        print(f"❌ Dataset not found: {args.dataset_path}")
        return

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"\n🔧 CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"🎮 GPU: {torch.cuda.get_device_name()}")

    # Load model with minimal memory usage
    print("\n📥 Loading model...")
    try:
        # Try without quantization first for simplicity
        config = AutoConfig.from_pretrained(args.model_id, trust_remote_code=True)
        config._attn_implementation = "eager"
        
        model = AutoModelForCausalLM.from_pretrained(
            args.model_id,
            config=config,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            device_map="auto"  # Automatically distribute across available devices
        )
        print("✅ Model loaded successfully")
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return

    # Load processor
    print("📥 Loading processor...")
    try:
        processor = AutoProcessor.from_pretrained(args.model_id, trust_remote_code=True)
        print("✅ Processor loaded successfully")
    except Exception as e:
        print(f"❌ Processor loading failed: {e}")
        return

    # Load dataset
    print("📊 Loading dataset...")
    raw_data = load_jsonl(args.dataset_path)
    train_dataset = VLMInstructionDataset(raw_data, processor, args.dataset_path)
    print(f"✅ Dataset loaded: {len(train_dataset)} examples")

    # Configure training (minimal settings for quick testing)
    print("⚙️ Configuring training...")
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        max_steps=args.max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=2,
        learning_rate=1e-4,
        logging_steps=5,
        save_steps=25,
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        dataloader_pin_memory=False,
        remove_unused_columns=False,
        report_to="none",
        warmup_steps=5,
    )

    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
    )

    # Start training
    print(f"\n🎯 Starting training ({args.max_steps} steps)...")
    try:
        trainer.train()
        print("✅ Training completed!")
        
        # Save final model
        final_path = os.path.join(args.output_dir, "final_checkpoint")
        trainer.save_model(final_path)
        print(f"💾 Model saved to: {final_path}")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        return

    print("\n🎉 Fast training complete!")

if __name__ == "__main__":
    main()