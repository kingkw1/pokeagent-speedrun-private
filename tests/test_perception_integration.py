#!/usr/bin/env python3
"""
Test script for perception model integration.

This script loads a locally fine-tuned perception model and tests it on a single image,
printing the structured JSON output to verify the model is working correctly.

USAGE:
    python test_perception_integration.py --local_model_path /path/to/local/model --image_path /path/to/test/image.png

EXAMPLE:
    python test_perception_integration.py --local_model_path ./models/perception_v0.1/final_checkpoint --image_path ./data/curated_screenshots/screenshot_20251009_203917.png
"""

import argparse
import json
from PIL import Image
from agent import Agent
from agent.perception import perception_step


def create_mock_args(local_model_path):
    """Create a mock args object for Agent initialization."""
    class MockArgs:
        def __init__(self, model_path):
            self.backend = 'local'
            self.model_name = model_path
            self.simple = False
    
    return MockArgs(local_model_path)


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test perception model integration')
    parser.add_argument('--local_model_path', required=True,
                        help='Path to the directory containing the fine-tuned model checkpoint')
    parser.add_argument('--image_path', required=True,
                        help='Path to a single screenshot for testing')
    
    args = parser.parse_args()
    
    # Create mock args object for Agent initialization
    mock_args = create_mock_args(args.local_model_path)
    
    # Initialize the Agent with the local model configuration
    agent = Agent(mock_args)
    
    # Load the test image
    test_image = Image.open(args.image_path)
    
    # Create dummy state_data for the test
    state_data = {}
    
    # Call perception_step directly with the loaded image, dummy state, and agent's VLM
    perception_output = perception_step(test_image, state_data, agent.vlm)
    
    # Print the formatted JSON output
    print(json.dumps(perception_output, indent=2))


if __name__ == '__main__':
    main()