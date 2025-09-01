from google import genai
import json
import os
import argparse
import random
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
from dotenv import load_dotenv
import glob
from pathlib import Path

class QuestionGeneratorConfig:
    """Configuration class for question generation with randomization settings."""
    
    def __init__(self, randomize: bool = True, seed: Optional[int] = None):
        self.randomize = randomize
        if seed is not None:
            random.seed(seed)
        
        # Randomization settings
        self.question_count_range = (3, 7)  # Min and max questions per image
        self.difficulty_variations = [
            {"Easy": 3, "Medium": 1, "Hard": 1},
            {"Easy": 2, "Medium": 2, "Hard": 1},
            {"Easy": 2, "Medium": 1, "Hard": 2},
            {"Easy": 1, "Medium": 3, "Hard": 1},
            {"Easy": 1, "Medium": 2, "Hard": 2},
        ]
        
        # Subject variations for more diverse questions
        self.subject_contexts = [
            "physics teacher's perspective",
            "engineering student's perspective", 
            "physicist's analytical viewpoint",
            "academic researcher's perspective",
            "practical application standpoint"
        ]
        
        # Question type variations
        self.question_styles = [
            "conceptual understanding",
            "mathematical calculation",
            "practical application",
            "theoretical analysis",
            "comparative analysis"
        ]

def initialize_api() -> genai.Client:
    """
    Loads the API key from environment variables and returns a genai client.
    """
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables. Please create a .env file and add it.")
    
    client = genai.Client(api_key=api_key)
    print("API client initialized successfully.")
    return client

def validate_image(image_path: str) -> None:
    """Raise if the path doesn't exist or isn't a readable image."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    try:
        with Image.open(image_path) as im:
            im.verify()  # lightweight check
    except Exception as e:
        raise ValueError(f"File is not a valid image: {image_path}") from e

def get_image_files(directory: str) -> List[str]:
    """Get all image files from the specified directory."""
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.tiff']
    image_files = []
    
    for extension in image_extensions:
        pattern = os.path.join(directory, extension)
        image_files.extend(glob.glob(pattern))
        # Also check for uppercase extensions
        pattern = os.path.join(directory, extension.upper())
        image_files.extend(glob.glob(pattern))
    
    return sorted(list(set(image_files)))  # Remove duplicates and sort

def generate_randomized_prompt(config: QuestionGeneratorConfig, image_filename: str) -> Tuple[str, Dict[str, int]]:
    """Generate a randomized prompt with varying parameters."""
    
    if config.randomize:
        # Randomize question count
        question_count = random.randint(*config.question_count_range)
        
        # Randomize difficulty distribution
        difficulty_dist = random.choice(config.difficulty_variations)
        
        # Adjust difficulty distribution to match question count
        total_diff_questions = sum(difficulty_dist.values())
        if total_diff_questions != question_count:
            # Scale the distribution to match the question count
            scale_factor = question_count / total_diff_questions
            difficulty_dist = {
                k: max(1, round(v * scale_factor)) 
                for k, v in difficulty_dist.items()
            }
            # Ensure we have exactly the right number of questions
            current_total = sum(difficulty_dist.values())
            if current_total != question_count:
                # Adjust the most common difficulty
                max_key = max(difficulty_dist.keys(), key=lambda k: difficulty_dist[k])
                difficulty_dist[max_key] += (question_count - current_total)
        
        # Randomize subject context and question style
        subject_context = random.choice(config.subject_contexts)
        question_style = random.choice(config.question_styles)
        
        # Add some variation to the analysis approach
        analysis_approaches = [
            "carefully analyze the provided image",
            "examine the scientific content shown in the image",
            "study the educational material presented in the image",
            "investigate the principles illustrated in the image"
        ]
        analysis_approach = random.choice(analysis_approaches)
        
    else:
        # Default values when randomization is disabled
        question_count = 5
        difficulty_dist = {"Easy": 2, "Medium": 2, "Hard": 1}
        subject_context = "physics teacher's perspective"
        question_style = "conceptual understanding"
        analysis_approach = "analyze the provided image"
    
    # Build difficulty instruction
    difficulty_text = []
    for diff, count in difficulty_dist.items():
        if count > 0:
            difficulty_text.append(f"- {count} '{diff}'")
    difficulty_instruction = "\n        ".join(difficulty_text)
    
    prompt = f"""
    From a {subject_context}, {analysis_approach} with focus on {question_style}.
    Generate exactly {question_count} multiple-choice questions with the following difficulty distribution:
    {difficulty_instruction}

    You MUST return your response as a single, raw JSON array of objects.
    Do not include any introductory text, explanations, or markdown code fences like ```json or ```.
    The response should start with '[' and end with ']'.

    Each object in the JSON array must have these exact keys:
    - "question_text": A string containing the question.
    - "image_path": A string representing the local path to the image file, use "{image_filename}".
    - "option_text": A list of four strings representing the possible answers.
    - "correct_answer_index": The integer index (0-3) of the correct option.
    - "difficulty_level": A string which must be 'Easy', 'Medium', or 'Hard'.
    - "explanation": A string that clearly explains why the correct answer is right, based on scientific principles.
    - "topic": A string indicating the main scientific topic or concept covered.
    - "subtopic": A string indicating the specific subtopic or area within the main topic.
    
    Ensure questions are diverse, scientifically accurate, and appropriately challenging for their difficulty level.
    """
    
    return prompt, difficulty_dist

def generate_questions_from_image_batch(
    image_path: str, 
    client: genai.Client, 
    config: QuestionGeneratorConfig,
    max_retries: int = 3
) -> Optional[List[Dict[str, Any]]]:
    """
    Generate questions from a single image with retry logic and enhanced error handling.
    """
    image_filename = os.path.basename(image_path)
    
    for attempt in range(max_retries):
        try:
            validate_image(image_path)
            print(f"  Processing: {image_filename} (attempt {attempt + 1}/{max_retries})")

            # Upload the image
            image_file = client.files.upload(file=image_path)
            print(f"  ✓ Image uploaded successfully")

            # Generate randomized prompt
            prompt, difficulty_dist = generate_randomized_prompt(config, image_filename)
            
            if config.randomize:
                print(f"  ✓ Generated randomized prompt - Questions: {sum(difficulty_dist.values())}, Difficulties: {difficulty_dist}")
            
            # Add small delay to avoid rate limiting
            time.sleep(1)
            
            print("  ⏳ Sending request to Gemini API...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, image_file]
            )

            # Parse model text directly as JSON
            response_text = (response.text or "").strip()
            
            # Clean response text of potential markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            parsed_json = json.loads(response_text)

            # Validate the response structure
            if not isinstance(parsed_json, list):
                raise ValueError("Model output is not a JSON array.")
            
            for i, item in enumerate(parsed_json, start=1):
                if not isinstance(item, dict):
                    raise ValueError(f"Item {i} is not an object.")
                
                required_keys = [
                    "question_text", "image_path", "option_text", 
                    "correct_answer_index", "difficulty_level", "explanation"
                ]
                for key in required_keys:
                    if key not in item:
                        raise ValueError(f"Item {i} missing key: {key}")
                
                if not isinstance(item["option_text"], list) or len(item["option_text"]) != 4:
                    raise ValueError(f"Item {i} must have exactly 4 options.")
                
                if item["difficulty_level"] not in ["Easy", "Medium", "Hard"]:
                    raise ValueError(f"Item {i} has invalid difficulty_level: {item['difficulty_level']}")
                
                # Add missing optional fields with defaults
                if "topic" not in item:
                    item["topic"] = "Physics"
                if "subtopic" not in item:
                    item["subtopic"] = "General"
                
                # Ensure image_path is set correctly
                item["image_path"] = image_filename

            print(f"  ✓ Successfully generated {len(parsed_json)} questions")
            return parsed_json

        except json.JSONDecodeError as e:
            print(f"  ❌ JSON parsing error (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print(f"  📝 Raw response for debugging:")
                print(f"  {response_text[:500]}..." if len(response_text) > 500 else response_text)
        except Exception as e:
            print(f"  ❌ Error (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                if 'response' in locals() and hasattr(response, 'text'):
                    print(f"  📝 Raw API response: {response.text[:200]}...")
        
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 2  # Exponential backoff
            print(f"  ⏳ Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
    
    print(f"  ❌ Failed to generate questions for {image_filename} after {max_retries} attempts")
    return None

def process_image_directory(
    images_dir: str,
    client: genai.Client,
    config: QuestionGeneratorConfig,
    max_images: Optional[int] = None,
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    Process all images in a directory and generate questions.
    """
    print(f"🔍 Scanning directory: {images_dir}")
    image_files = get_image_files(images_dir)
    
    if not image_files:
        raise ValueError(f"No image files found in directory: {images_dir}")
    
    if config.randomize and max_images:
        # Randomly sample images if max_images is specified
        if len(image_files) > max_images:
            image_files = random.sample(image_files, max_images)
    elif max_images:
        image_files = image_files[:max_images]
    
    print(f"📊 Found {len(image_files)} images to process")
    
    all_questions = []
    processing_stats = {
        "total_images": len(image_files),
        "successful": 0,
        "failed": 0,
        "total_questions": 0,
        "start_time": datetime.now().isoformat(),
        "image_results": {}
    }
    
    for i, image_path in enumerate(image_files, 1):
        image_filename = os.path.basename(image_path)
        print(f"\n📸 [{i}/{len(image_files)}] Processing: {image_filename}")
        
        try:
            questions = generate_questions_from_image_batch(image_path, client, config)
            
            if questions:
                all_questions.extend(questions)
                processing_stats["successful"] += 1
                processing_stats["total_questions"] += len(questions)
                processing_stats["image_results"][image_filename] = {
                    "status": "success",
                    "question_count": len(questions),
                    "difficulties": {}
                }
                
                # Count difficulties
                for q in questions:
                    diff = q.get("difficulty_level", "Unknown")
                    processing_stats["image_results"][image_filename]["difficulties"][diff] = \
                        processing_stats["image_results"][image_filename]["difficulties"].get(diff, 0) + 1
                
                print(f"  ✅ Success! Generated {len(questions)} questions")
            else:
                processing_stats["failed"] += 1
                processing_stats["image_results"][image_filename] = {
                    "status": "failed",
                    "question_count": 0
                }
        
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            processing_stats["failed"] += 1
            processing_stats["image_results"][image_filename] = {
                "status": "error",
                "error": str(e),
                "question_count": 0
            }
    
    processing_stats["end_time"] = datetime.now().isoformat()
    processing_stats["success_rate"] = (processing_stats["successful"] / processing_stats["total_images"]) * 100
    
    return {
        "questions": all_questions,
        "stats": processing_stats
    }

def save_results(
    results: Dict[str, Any],
    output_file: str,
    save_stats: bool = True
) -> Tuple[str, Optional[str]]:
    """Save questions and statistics to files."""
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file) or "."
    os.makedirs(output_dir, exist_ok=True)
    
    # Save questions
    questions_file = output_file
    with open(questions_file, "w", encoding="utf-8") as f:
        json.dump(results["questions"], f, ensure_ascii=False, indent=2)
    
    stats_file = None
    if save_stats:
        # Save statistics
        base_name = os.path.splitext(questions_file)[0]
        stats_file = f"{base_name}_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(results["stats"], f, ensure_ascii=False, indent=2)
    
    return questions_file, stats_file

def print_summary(stats: Dict[str, Any]) -> None:
    """Print a summary of the processing results."""
    print(f"\n{'='*60}")
    print("📊 PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Total Images Processed: {stats['total_images']}")
    print(f"Successful: {stats['successful']} ({stats['success_rate']:.1f}%)")
    print(f"Failed: {stats['failed']}")
    print(f"Total Questions Generated: {stats['total_questions']}")
    
    if stats['successful'] > 0:
        avg_questions = stats['total_questions'] / stats['successful']
        print(f"Average Questions per Image: {avg_questions:.1f}")
    
    print(f"Processing Time: {stats['start_time']} to {stats['end_time']}")
    print(f"{'='*60}")

# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enhanced MCQ generator - processes multiple images with randomization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process all images with randomization
    python enhanced_image_question_generator.py --images-dir ./images
    
    # Process specific number of images
    python enhanced_image_question_generator.py --images-dir ./images --max-images 10
    
    # Disable randomization for consistent output
    python enhanced_image_question_generator.py --images-dir ./images --no-randomize
    
    # Set random seed for reproducible randomization
    python enhanced_image_question_generator.py --images-dir ./images --seed 42
        """
    )
    
    # Directory and file arguments
    parser.add_argument("--images-dir", type=str, default="images", 
                       help="Directory containing images to process (default: ./images)")
    parser.add_argument("--output", type=str, default="all_questions.json",
                       help="Output JSON file for all questions (default: all_questions.json)")
    
    # Processing control arguments
    parser.add_argument("--max-images", type=int, default=None,
                       help="Maximum number of images to process (default: all)")
    parser.add_argument("--max-retries", type=int, default=3,
                       help="Maximum retries per image (default: 3)")
    
    # Randomization arguments
    parser.add_argument("--no-randomize", action="store_true",
                       help="Disable randomization for consistent output")
    parser.add_argument("--seed", type=int, default=None,
                       help="Random seed for reproducible results")
    
    # Output control arguments
    parser.add_argument("--no-stats", action="store_true",
                       help="Don't save processing statistics")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not os.path.exists(args.images_dir):
        print(f"❌ Error: Images directory not found: {args.images_dir}")
        exit(1)
    
    # Check dependencies
    try:
        import dotenv  # noqa: F401
    except ImportError:
        print("❌ Required package 'python-dotenv' is not installed.")
        print("Please run: pip install python-dotenv")
        exit(1)
    
    print("🚀 Enhanced Question Generator Starting...")
    print(f"📁 Images Directory: {args.images_dir}")
    print(f"📄 Output File: {args.output}")
    
    # Initialize configuration
    config = QuestionGeneratorConfig(
        randomize=not args.no_randomize,
        seed=args.seed
    )
    
    if config.randomize:
        seed_info = f" (seed: {args.seed})" if args.seed else " (random seed)"
        print(f"🎲 Randomization: Enabled{seed_info}")
    else:
        print("🔒 Randomization: Disabled")
    
    # Initialize API client  
    try:
        client = initialize_api()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        exit(1)
    
    # Process all images
    try:
        results = process_image_directory(
            args.images_dir,
            client,
            config,
            max_images=args.max_images
        )
        
        # Save results
        questions_file, stats_file = save_results(
            results,
            args.output,
            save_stats=not args.no_stats
        )
        
        # Print summary
        print_summary(results["stats"])
        
        print(f"\n💾 Questions saved to: {questions_file}")
        if stats_file:
            print(f"📈 Statistics saved to: {stats_file}")
        
        if results["questions"]:
            print(f"\n📋 Sample question from the results:")
            sample_q = results["questions"][0]
            print(f"   Question: {sample_q['question_text'][:100]}...")
            print(f"   Difficulty: {sample_q['difficulty_level']}")
            print(f"   Image: {sample_q['image_path']}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        exit(1)
    
    print("\n✅ Processing completed successfully!")
