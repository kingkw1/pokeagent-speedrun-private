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

# --- 1. Dataset Loading ---

def load_jsonl(dataset_path: str) -> List[Dict[str, Any]]:
    """
    Loads a .jsonl file into a list of dictionaries.

    Args:
        dataset_path (str): The path to the .jsonl file.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                               represents a line in the .jsonl file.
    """
    data = []
    with open(dataset_path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def _copy_processor_files(base_model_id: str, output_dir: str) -> None:
    """
    Copy processor files from the base model cache to all checkpoint directories.
    
    This ensures fine-tuned models have all necessary files for loading.
    
    Args:
        base_model_id (str): The base model ID (e.g., "Qwen/Qwen2-VL-2B-Instruct")
        output_dir (str): The output directory containing checkpoint subdirectories
    """
    import os
    import shutil
    import glob
    from pathlib import Path
    
    print(f"Copying processor files from base model: {base_model_id}")
    
    # Find all checkpoint directories
    checkpoint_dirs = glob.glob(os.path.join(output_dir, "checkpoint-*"))
    
    if not checkpoint_dirs:
        print("⚠️  No checkpoint directories found. Processor files may need manual copying.")
        return
        
    # Try to find the base model in HuggingFace cache
    cache_root = Path.home() / ".cache" / "huggingface" / "hub"
    model_cache_name = f"models--{base_model_id.replace('/', '--')}"
    model_cache_dir = cache_root / model_cache_name
    
    if not model_cache_dir.exists():
        print(f"⚠️  Base model cache not found at: {model_cache_dir}")
        print("   You may need to manually copy processor files for model loading.")
        return
        
    # Find the latest snapshot directory
    snapshots_dir = model_cache_dir / "snapshots"
    if not snapshots_dir.exists():
        print("⚠️  No snapshots directory found in model cache.")
        return
        
    # Get the most recent snapshot (by modification time)
    snapshot_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]
    if not snapshot_dirs:
        print("⚠️  No snapshot directories found.")
        return
        
    latest_snapshot = max(snapshot_dirs, key=lambda x: x.stat().st_mtime)
    print(f"Using snapshot: {latest_snapshot.name}")
    
    # Define files to copy for different model types
    qwen_files = [
        "preprocessor_config.json",
        "tokenizer_config.json", 
        "tokenizer.json",
        "vocab.json",
        "merges.txt",
        "chat_template.json"
    ]
    
    phi_files = [
        "preprocessor_config.json",
        "processor_config.json",
        "tokenizer_config.json",
        "tokenizer.json", 
        "special_tokens_map.json",
        "processing_phi3_v.py"
    ]
    
    # Determine which files to copy based on model type
    if "qwen" in base_model_id.lower():
        files_to_copy = qwen_files
        model_type = "Qwen2-VL"
    else:
        files_to_copy = phi_files  
        model_type = "Phi-3-Vision"
        
    print(f"Detected model type: {model_type}")
    
    # Copy files to each checkpoint directory
    copied_count = 0
    for checkpoint_dir in checkpoint_dirs:
        print(f"Processing checkpoint: {os.path.basename(checkpoint_dir)}")
        
        for filename in files_to_copy:
            src_file = latest_snapshot / filename
            dst_file = Path(checkpoint_dir) / filename
            
            if src_file.exists():
                try:
                    shutil.copy2(src_file, dst_file)
                    copied_count += 1
                    print(f"  ✅ Copied {filename}")
                except Exception as e:
                    print(f"  ❌ Failed to copy {filename}: {e}")
            else:
                print(f"  ⚠️  File not found: {filename}")
    
    print(f"\n✅ Successfully copied {copied_count} processor files.")
    print("Fine-tuned model checkpoints are now ready for loading!")
    
    if copied_count == 0:
        print("\n⚠️  WARNING: No processor files were copied!")
        print("You may need to manually copy the following files from:")
        print(f"   {latest_snapshot}")
        print("To each checkpoint directory:")
        for checkpoint_dir in checkpoint_dirs:
            print(f"   {checkpoint_dir}")
        print("Required files:", ", ".join(files_to_copy))

# --- 2. Custom Dataset for VLM Fine-tuning ---

class VLMInstructionDataset(Dataset):
    """
    A custom PyTorch dataset for fine-tuning a Vision-Language Model.
    It loads images just-in-time and formats the data into the required
    chat template.
    """
    def __init__(self, data: List[Dict[str, Any]], processor: AutoProcessor, dataset_path: str):
        """
        Args:
            data (List[Dict[str, Any]]): The loaded dataset from the .jsonl file.
            processor (AutoProcessor): The model's processor for tokenization and image processing.
            dataset_path (str): The path to the original dataset file, used to resolve relative image paths.
        """
        self.data = data
        self.processor = processor
        # Get the directory of the dataset file to resolve relative image paths
        self.dataset_dir = os.path.dirname(dataset_path)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """
        Preprocesses a single data example to create the model inputs.

        Args:
            idx (int): The index of the item in the dataset.

        Returns:
            Dict[str, Any]: A dictionary containing the processed inputs
                            (input_ids, attention_mask, pixel_values, labels).
        """
        item = self.data[idx]

        # Resolve the absolute path for the image
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

        # Format the prompt based on model type
        if hasattr(self.processor, 'tokenizer') and 'qwen2-vl' in getattr(self.processor.tokenizer, 'name_or_path', '').lower():
            # Qwen2-VL format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": "Based on the visual frame, extract specific information into this JSON structure. Return ONLY the filled JSON object."}
                    ]
                },
                {
                    "role": "assistant", 
                    "content": json_string_output
                }
            ]
            prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            # Process with the formatted text and images
            inputs = self.processor(text=prompt, images=[image], return_tensors="pt")
        else:
            # Phi-3 Vision format
            prompt = (
                f"<|user|>\n<|image_1|>\nBased on the visual frame, extract specific "
                f"information into this JSON structure. Return ONLY the filled JSON object.<|end|>\n"
                f"<|assistant|>\n{json_string_output}<|end|>"
            )
            # Process the text and image using the processor
            inputs = self.processor(text=prompt, images=image, return_tensors="pt")

        # Create labels for training - mask everything except the assistant response
        labels = inputs["input_ids"].clone()
        
        # First, mask all image-related tokens (negative values and out-of-vocab tokens)
        # Image tokens are typically negative or beyond the base vocabulary
        base_vocab_size = self.processor.tokenizer.vocab_size
        
        # Mask image placeholder tokens (negative values)
        labels[labels < 0] = -100
        
        # Mask special image tokens that are beyond base vocabulary but not in added tokens
        # Keep only tokens that are either in base vocab or properly added special tokens
        extended_vocab_size = len(self.processor.tokenizer)  # Includes added tokens
        labels[labels >= extended_vocab_size] = -100
        
        # Now mask the user prompt part to only train on assistant response
        # We need to find where the assistant response starts
        # Look for the pattern "<|assistant|>\n" in the tokenized sequence
        assistant_start_text = "<|assistant|>\n"
        assistant_start_tokens = self.processor.tokenizer(assistant_start_text, add_special_tokens=False, return_tensors="pt")
        assistant_start_ids = assistant_start_tokens.input_ids[0]
        
        # Find where the assistant response starts in the sequence
        input_ids = inputs["input_ids"][0]
        assistant_start_pos = None
        
        # Search for the assistant start pattern
        for i in range(len(input_ids) - len(assistant_start_ids) + 1):
            if torch.equal(input_ids[i:i+len(assistant_start_ids)], assistant_start_ids):
                assistant_start_pos = i + len(assistant_start_ids)
                break
        
        if assistant_start_pos is not None:
            # Mask everything before the assistant response
            labels[0, :assistant_start_pos] = -100
        else:
            # Fallback: mask the first half if we can't find the pattern
            labels[0, :labels.shape[1]//2] = -100
        
        # Mask padding tokens after the end of sequence
        eos_token_id = self.processor.tokenizer.eos_token_id
        if eos_token_id in labels[0]:
            eos_indices = (labels[0] == eos_token_id).nonzero(as_tuple=True)[0]
            if len(eos_indices) > 0:
                # Mask everything after the first eos token
                labels[0, eos_indices[0] + 1:] = -100

        # Squeeze the tensors to remove the batch dimension, as the Trainer will re-batch them
        inputs = {k: v.squeeze(0) for k, v in inputs.items()}
        inputs["labels"] = labels.squeeze(0)

        return inputs

# --- 3. Custom Training Class to Handle Cache Issues ---

class CustomTrainer(Trainer):
    """Custom trainer to handle Phi-3 Vision cache issues"""
    
    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        """
        Override compute_loss to disable cache during training
        """
        # Ensure use_cache is False for training
        if hasattr(model.config, 'use_cache'):
            model.config.use_cache = False
        if hasattr(model, 'generation_config') and model.generation_config is not None:
            model.generation_config.use_cache = False
            
        # Remove any past_key_values from inputs if present
        if 'past_key_values' in inputs:
            del inputs['past_key_values']
            
        # Call the parent compute_loss with correct signature
        if num_items_in_batch is not None:
            return super().compute_loss(model, inputs, return_outputs, num_items_in_batch)
        else:
            return super().compute_loss(model, inputs, return_outputs)
    
    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
        """
        Override prediction_step to handle cache issues
        """
        # Ensure use_cache is False
        if hasattr(model.config, 'use_cache'):
            model.config.use_cache = False
            
        return super().prediction_step(model, inputs, prediction_loss_only, ignore_keys)
    
    def save_model(self, output_dir=None, _internal_call=False):
        """
        Override save_model to handle shared tensor issues in Phi-3 Vision
        """
        if output_dir is None:
            output_dir = self.args.output_dir
            
        try:
            # Try normal save first
            super().save_model(output_dir, _internal_call)
        except RuntimeError as e:
            if "shared tensors" in str(e):
                print(f"⚠️  Shared tensor issue detected, using safe_serialization=False")
                # Handle shared tensor issue by saving with safe_serialization=False
                self.model.save_pretrained(output_dir, safe_serialization=False)
                if hasattr(self, 'tokenizer') and self.tokenizer is not None:
                    self.tokenizer.save_pretrained(output_dir)
            else:
                raise e

# --- 4. Main Training Logic ---

def main():
    """
    The main function to orchestrate the fine-tuning process.
    """
    # --- A: Parse Command-Line Arguments ---
    parser = argparse.ArgumentParser(description="Fine-tune a Vision-Language Model.")
    parser.add_argument("--dataset_path", type=str, required=True, help="Path to the .jsonl training data file.")
    parser.add_argument("--model_id", type=str, default="microsoft/Phi-3.5-vision-instruct", help="The Hugging Face ID of the base model.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the fine-tuned model checkpoint.")
    args = parser.parse_args()

    print("--- Starting VLM Fine-Tuning ---")
    print(f"Model ID: {args.model_id}")
    print(f"Dataset Path: {args.dataset_path}")
    print(f"Output Directory: {args.output_dir}")

    # Validate dataset file exists
    if not os.path.exists(args.dataset_path):
        print(f"❌ Error: Dataset file not found: {args.dataset_path}")
        return

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(f"{args.output_dir}/logs", exist_ok=True)

    # --- B: Load the Base Model and Processor with Quantization ---
    print("\n--- Step B: Loading Base Model and Processor ---")
    
    # Check CUDA availability
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device count: {torch.cuda.device_count()}")
        print(f"Current CUDA device: {torch.cuda.current_device()}")
        print(f"CUDA device name: {torch.cuda.get_device_name()}")
    else:
        print("Warning: CUDA not available, training will use CPU (much slower)")

    # Configure 4-bit quantization for memory efficiency
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,  # Additional memory savings
    )

    # Load configuration and set attention implementation
    config = AutoConfig.from_pretrained(args.model_id, trust_remote_code=True)
    config._attn_implementation = "eager"  # Force eager attention to avoid FlashAttention2
    config.use_cache = False  # Disable KV cache to avoid DynamicCache issues
    
    # Load the model without quantization for fine-tuning
    print("Loading model without quantization for fine-tuning...")
    try:
        # Handle different model types
        if "qwen2-vl" in args.model_id.lower():
            from transformers import Qwen2VLForConditionalGeneration
            model = Qwen2VLForConditionalGeneration.from_pretrained(
                args.model_id,
                config=config,
                trust_remote_code=True,
                torch_dtype=torch.bfloat16,  # Use bfloat16 for memory efficiency
                device_map="auto",
                low_cpu_mem_usage=True,
                max_memory={0: "28GiB"}  # Limit GPU memory usage to leave room for optimizer
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                args.model_id,
                config=config,
                trust_remote_code=True,
                torch_dtype=torch.bfloat16,  # Use bfloat16 for memory efficiency
                device_map="auto",
                low_cpu_mem_usage=True,
                max_memory={0: "28GiB"}  # Limit GPU memory usage to leave room for optimizer
            )
        print("✅ Model loaded successfully")
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return

    # Configure model for training (disable cache and enable gradient checkpointing)
    if hasattr(model, 'config'):
        model.config.use_cache = False
    if hasattr(model, 'generation_config'):
        model.generation_config.use_cache = False
    
    # Enable gradient checkpointing for memory efficiency
    model.gradient_checkpointing_enable()
    
    # Additional memory optimizations
    torch.cuda.empty_cache()  # Clear cache before training
    
    print("✅ Model configured for training")

    # Load the processor
    processor = AutoProcessor.from_pretrained(args.model_id, trust_remote_code=True)

    print("Model and processor loaded successfully.")

    # --- C: Load and Preprocess the Data ---
    print("\n--- Step C: Loading and Preprocessing Dataset ---")

    # Load the raw data from the .jsonl file
    raw_dataset = load_jsonl(args.dataset_path)

    # Create the custom dataset for training
    train_dataset = VLMInstructionDataset(
        data=raw_dataset,
        processor=processor,
        dataset_path=args.dataset_path
    )

    print(f"Dataset loaded with {len(train_dataset)} examples.")

    # --- D: Configure and Run Training ---
    print("\n--- Step D: Configuring and Running Training ---")

    # Instantiate TrainingArguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=1,  # Reduce epochs for testing
        per_device_train_batch_size=1,
        learning_rate=1e-5,  # Lower learning rate for Adafactor optimizer
        logging_dir=f"{args.output_dir}/logs",
        logging_steps=10,
        report_to="none",  # Disable wandb or other reporting
        save_steps=500,  # Save checkpoints
        gradient_accumulation_steps=4,  # Increase gradient accumulation to reduce effective batch processing
        bf16=True,  # Use bfloat16 instead of fp16 for better stability with vision models
        gradient_checkpointing=True,  # Enable gradient checkpointing for memory efficiency
        dataloader_pin_memory=False,  # Reduce memory usage
        dataloader_num_workers=0,  # Reduce memory usage
        remove_unused_columns=False,  # Keep all columns for multimodal training
        max_grad_norm=1.0,  # Gradient clipping for stability
        optim="adafactor",  # Use memory-efficient Adafactor optimizer instead of Adam
        dataloader_drop_last=True,  # Drop incomplete batches
        ddp_find_unused_parameters=False,  # Reduce memory overhead
        save_strategy="epoch",  # Save at end of epoch
        save_total_limit=1,  # Keep only final checkpoint
    )

    # Instantiate the Custom Trainer
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
    )

    # Start the training process
    print("Starting training...")
    trainer.train()
    print("Training complete.")

    # --- E: Model is automatically saved due to save_strategy="epoch" ---
    print("\n--- Step E: Training Complete ---")
    print(f"Fine-tuned model saved to {args.output_dir}")
    
    # --- F: Copy processor files for complete model checkpoint ---
    print("\n--- Step F: Copying Processor Files ---")
    _copy_processor_files(args.model_id, args.output_dir)
    
    print("\n--- VLM Fine-Tuning Finished ---")


if __name__ == "__main__":
    # To run this script, use the following command in your terminal:
    # python train_perception_vlm.py --dataset_path path/to/your/data.jsonl --output_dir path/to/your/output/model
    # Example:
    # python train_perception_vlm.py --dataset_path data/perception_seed.jsonl --output_dir models/perception_v0.1
    main()