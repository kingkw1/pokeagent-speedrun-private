# IMPORTANT NOTE: You are a code generation assistant. You do not have access
# to my local file system or any of my data. Your sole task is to write a
# complete Python script based on the specifications below. I will be the one
# to run this script in my own environment with my own data.

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
        image_path = os.path.join(self.dataset_dir, item['image_path'])
        image = Image.open(image_path).convert("RGB")

        json_string_output = item['json_string']

        # Format the prompt using the required chat template
        # <|user|>
        # <|image_1|>
        # Based on the visual frame, extract specific information into this JSON structure. Return ONLY the filled JSON object.
        # <|end|>
        # <|assistant|>
        # {the_json_string_output}<|end|>
        prompt = (
            f"<|user|>\n<|image_1|>\nBased on the visual frame, extract specific "
            f"information into this JSON structure. Return ONLY the filled JSON object.\n<|end|>\n"
            f"<|assistant|>\n{json_string_output}<|end|>"
        )

        # Process the text and image using the processor
        inputs = self.processor(text=prompt, images=image, return_tensors="pt")

        # To ensure the model learns to generate the assistant's response, we mask
        # the user's part of the prompt in the labels.
        labels = inputs["input_ids"].clone()

        # Create the prompt part that should be ignored by the loss function
        user_prompt_part = (
             f"<|user|>\n<|image_1|>\nBased on the visual frame, extract specific "
             f"information into this JSON structure. Return ONLY the filled JSON object.\n<|end|>\n"
             f"<|assistant|>\n"
        )

        # Tokenize the user part to find its length
        user_prompt_tokens = self.processor.tokenizer(user_prompt_part, return_tensors="pt")
        user_prompt_len = user_prompt_tokens.input_ids.shape[1]

        # Mask the user prompt and padding tokens
        labels[0, :user_prompt_len] = -100

        # The processor might add padding, which should also be ignored
        # Find where the actual content ends (before padding)
        # The end token is usually followed by padding tokens
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

# --- 3. Main Training Logic ---

def main():
    """
    The main function to orchestrate the fine-tuning process.
    """
    # --- A: Parse Command-Line Arguments ---
    parser = argparse.ArgumentParser(description="Fine-tune a Vision-Language Model.")
    parser.add_argument("--dataset_path", type=str, required=True, help="Path to the .jsonl training data file.")
    parser.add_argument("--model_id", type=str, default="microsoft/phi-3-vision-128k-instruct", help="The Hugging Face ID of the base model.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the fine-tuned model checkpoint.")
    args = parser.parse_args()

    print("--- Starting VLM Fine-Tuning ---")
    print(f"Model ID: {args.model_id}")
    print(f"Dataset Path: {args.dataset_path}")
    print(f"Output Directory: {args.output_dir}")

    # --- B: Load the Base Model and Processor with Quantization ---
    print("\n--- Step B: Loading Base Model and Processor ---")

    # Configure 4-bit quantization for memory efficiency
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    # Load the model
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        trust_remote_code=True,
        quantization_config=bnb_config,
        torch_dtype="auto"
    )

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
        num_train_epochs=2,
        per_device_train_batch_size=1,
        learning_rate=2e-4,
        logging_dir=f"{args.output_dir}/logs",
        logging_steps=10,
        report_to="none",  # Disable wandb or other reporting
    )

    # Instantiate the Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
    )

    # Start the training process
    print("Starting training...")
    trainer.train()
    print("Training complete.")

    # --- E: Save the Final Model ---
    print("\n--- Step E: Saving the Final Model ---")

    final_model_path = os.path.join(args.output_dir, "final_checkpoint")
    trainer.save_model(final_model_path)

    print(f"Fine-tuned model saved to {final_model_path}")
    print("\n--- VLM Fine-Tuning Finished ---")


if __name__ == "__main__":
    # To run this script, use the following command in your terminal:
    # python train_perception_vlm.py --dataset_path path/to/your/data.jsonl --output_dir path/to/your/output/model
    # Example:
    # python train_perception_vlm.py --dataset_path data/perception_seed.jsonl --output_dir models/perception_v0.1
    main()