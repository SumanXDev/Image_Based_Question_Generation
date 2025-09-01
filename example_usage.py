#!/usr/bin/env python3
"""
Example usage script for the Enhanced Question Generator
This script demonstrates how to use the enhanced question generator in different modes.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and display the result."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Success!")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Error!")
        print(f"Exit code: {e.returncode}")
        if e.stdout:
            print("stdout:", e.stdout)
        if e.stderr:
            print("stderr:", e.stderr)
        return False

def main():
    """Demonstrate different usage patterns of the enhanced question generator."""
    
    print("🚀 Enhanced Question Generator - Example Usage")
    print("This script demonstrates various ways to use the enhanced generator")
    
    # Check if the enhanced script exists
    if not os.path.exists("enhanced_image_question_generator.py"):
        print("❌ enhanced_image_question_generator.py not found!")
        return
    
    # Check if images directory exists
    if not os.path.exists("images"):
        print("❌ images directory not found!")
        print("Please ensure you have an 'images' directory with image files.")
        return
    
    # Example 1: Basic usage with randomization (5 images)
    run_command([
        sys.executable, "enhanced_image_question_generator.py",
        "--images-dir", "images",
        "--max-images", "5",
        "--output", "example_random_questions.json"
    ], "Example 1: Generate questions from 5 random images with randomization")
    
    # Example 2: Deterministic output with seed
    run_command([
        sys.executable, "enhanced_image_question_generator.py", 
        "--images-dir", "images",
        "--max-images", "3",
        "--seed", "42",
        "--output", "example_seeded_questions.json"
    ], "Example 2: Generate questions with fixed random seed (reproducible)")
    
    # Example 3: No randomization (consistent output)
    run_command([
        sys.executable, "enhanced_image_question_generator.py",
        "--images-dir", "images", 
        "--max-images", "2",
        "--no-randomize",
        "--output", "example_consistent_questions.json"
    ], "Example 3: Generate questions without randomization (consistent)")
    
    # Example 4: Process all images without statistics
    run_command([
        sys.executable, "enhanced_image_question_generator.py",
        "--images-dir", "images",
        "--max-images", "3",
        "--no-stats",
        "--output", "example_no_stats.json"
    ], "Example 4: Generate questions without saving statistics")
    
    print(f"\n{'='*60}")
    print("🎉 Example demonstrations completed!")
    print("🔍 Check the generated JSON files to see the results:")
    
    # List generated files
    example_files = [
        "example_random_questions.json",
        "example_seeded_questions.json", 
        "example_consistent_questions.json",
        "example_no_stats.json"
    ]
    
    for file in example_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (not created)")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
