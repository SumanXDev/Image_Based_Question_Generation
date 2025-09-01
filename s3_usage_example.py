#!/usr/bin/env python3
"""
Example usage script for the S3-Enhanced Question Generator with URL generation
This script demonstrates how to use the S3-enhanced question generator with unsigned URL generation.
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
    """Demonstrate different usage patterns of the S3-enhanced question generator."""
    
    print("🚀 S3-Enhanced Question Generator with URL Generation - Example Usage")
    print("This script demonstrates various ways to use the S3-enhanced generator")
    
    # Check if the S3 enhanced script exists
    if not os.path.exists("s3_enhanced_question_generator.py"):
        print("❌ s3_enhanced_question_generator.py not found!")
        return
    
    # Example 1: Basic usage with randomization (10 images)
    run_command([
        sys.executable, "s3_enhanced_question_generator.py",
        "--s3-prefix", "Diagrams/Physics/images/",
        "--max-images", "10",
        "--output", "s3_random_questions.json"
    ], "Example 1: Generate questions from 10 random S3 images with randomization")
    
    # Example 2: Deterministic output with seed
    run_command([
        sys.executable, "s3_enhanced_question_generator.py", 
        "--s3-prefix", "Diagrams/Physics/images/",
        "--max-images", "5",
        "--seed", "42",
        "--output", "s3_seeded_questions.json"
    ], "Example 2: Generate questions with fixed random seed (reproducible)")
    
    # Example 3: No randomization (consistent output)
    run_command([
        sys.executable, "s3_enhanced_question_generator.py",
        "--s3-prefix", "Diagrams/Physics/images/", 
        "--max-images", "3",
        "--no-randomize",
        "--output", "s3_consistent_questions.json"
    ], "Example 3: Generate questions without randomization (consistent)")
    
    # Example 4: Process with custom S3 bucket
    run_command([
        sys.executable, "s3_enhanced_question_generator.py",
        "--s3-bucket", "images-questionbank",
        "--s3-prefix", "Diagrams/Physics/images/",
        "--max-images", "5",
        "--seed", "123",
        "--output", "s3_custom_bucket_questions.json"
    ], "Example 4: Generate questions from custom S3 bucket")
    
    print(f"\n{'='*60}")
    print("🎉 Example demonstrations completed!")
    print("🔍 Check the generated JSON files to see the results with S3 URLs:")
    
    # List generated files
    example_files = [
        "s3_random_questions.json",
        "s3_seeded_questions.json", 
        "s3_consistent_questions.json",
        "s3_custom_bucket_questions.json"
    ]
    
    for file in example_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (not created)")
    
    print(f"\n📋 Note: All image_path fields now contain direct S3 URLs!")
    print(f"Example URL format: https://images-questionbank.s3.amazonaws.com/Diagrams/Physics/images/page_1_image_0.jpg")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
