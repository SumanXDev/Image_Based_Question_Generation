import boto3
from google import genai
import json
import os
import argparse
import random
import time
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse
from botocore.exceptions import NoCredentialsError, ClientError

class S3QuestionGeneratorConfig:
    """Configuration class for S3-based question generation with global difficulty distribution."""
    
    def __init__(self, randomize: bool = True, seed: Optional[int] = None):
        self.randomize = randomize
        if seed is not None:
            random.seed(seed)
        
        # Single question per image (modified from original)
        self.questions_per_image = 1
        
        # Global difficulty distributions for all images combined
        self.global_difficulty_distributions = [
            {"Easy": 0.5, "Medium": 0.3, "Hard": 0.2},     # 50% Easy, 30% Medium, 20% Hard
            {"Easy": 0.4, "Medium": 0.4, "Hard": 0.2},     # 40% Easy, 40% Medium, 20% Hard
            {"Easy": 0.3, "Medium": 0.4, "Hard": 0.3},     # 30% Easy, 40% Medium, 30% Hard
            {"Easy": 0.6, "Medium": 0.25, "Hard": 0.15},   # 60% Easy, 25% Medium, 15% Hard
            {"Easy": 0.35, "Medium": 0.35, "Hard": 0.3},   # 35% Easy, 35% Medium, 30% Hard
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

class S3ImageHandler:
    """Handler for S3 operations and image management."""
    
    def __init__(self, bucket_name: str, aws_access_key: str, aws_secret_key: str, region: str = 'us-west-2'):
        """Initialize S3 client with credentials."""
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        print(f"✅ S3 client initialized for bucket: {bucket_name}")
    
    def list_image_files(self, prefix: str = "") -> List[str]:
        """List all image files in the S3 bucket with the given prefix."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        image_keys = []
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        # Check if the file has an image extension
                        if any(key.lower().endswith(ext) for ext in image_extensions):
                            image_keys.append(key)
            
            print(f"📊 Found {len(image_keys)} images in S3 bucket with prefix '{prefix}'")
            return sorted(image_keys)
        
        except Exception as e:
            print(f"❌ Error listing S3 objects: {e}")
            return []
    
    def download_image_to_temp(self, s3_key: str) -> Optional[str]:
        """Download an image from S3 to a temporary file and return the local path."""
        try:
            # Create a temporary file
            file_extension = os.path.splitext(s3_key)[1]
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
            temp_path = temp_file.name
            temp_file.close()
            
            # Download from S3
            self.s3_client.download_file(self.bucket_name, s3_key, temp_path)
            print(f"  ✓ Downloaded {s3_key} to temporary file")
            return temp_path
        
        except Exception as e:
            print(f"  ❌ Error downloading {s3_key}: {e}")
            return None
    
    def cleanup_temp_file(self, temp_path: str):
        """Clean up temporary file."""
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as e:
            print(f"  ⚠️  Warning: Could not clean up temp file {temp_path}: {e}")
    
    def generate_s3_url(self, s3_key: str) -> str:
        """Generate unsigned S3 URL for a given S3 key."""
        return f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
    
    def generate_signed_urls_for_s3_uri(self, s3_uri: str, expiration: int = 3600) -> List[Dict[str, str]]:
        """
        Generate a list of signed URLs for all images in the specified S3 folder using an S3 URI.
        
        :param s3_uri: S3 URI of the folder (e.g., s3://bucket-name/folder-name/)
        :param expiration: Time in seconds for the signed URL to remain valid (default is 3600 seconds)
        :return: List of dictionaries containing image names and their signed URLs
        """
        # Parse the S3 URI to extract bucket name and folder name
        parsed_uri = urlparse(s3_uri, allow_fragments=False)
        bucket_name = parsed_uri.netloc
        folder_name = parsed_uri.path.lstrip('/')

        # Ensure the folder name ends with a slash to correctly list objects
        if not folder_name.endswith('/'):
            folder_name += '/'

        try:
            # List objects in the specified folder with delimiter to avoid subfolders
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=folder_name,
                Delimiter='/'
            )
        except NoCredentialsError:
            print("Error: AWS credentials not found.")
            return []
        except ClientError as e:
            print(f"Error listing objects in the bucket: {e}")
            return []

        signed_urls = []

        # Process files in the specified folder (excluding subfolders)
        if 'Contents' in response:
            for obj in response['Contents']:
                file_name = obj['Key']
                # Ensure the file is directly within the specified folder
                if file_name.startswith(folder_name) and file_name.count('/') == folder_name.count('/'):
                    # Ensure the file is an image by checking the extension
                    if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
                        try:
                            # Extract just the image name (basename)
                            image_name = os.path.basename(file_name)

                            # Generate the unsigned URL
                            signed_url = f"https://{bucket_name}.s3.amazonaws.com/{file_name}"
                            
                            signed_urls.append({
                                "image_name": image_name,
                                "signed_url": signed_url
                            })
                        except NoCredentialsError:
                            print("Error: AWS credentials not found.")
                            return []
                        except Exception as e:
                            print(f"Error generating signed URL for {file_name}: {e}")
                            return []

        return signed_urls

def setup_aws_environment():
    """Set up AWS environment variables - load from .env file or environment."""
    load_dotenv()  # Load from .env file if it exists
    
    # Check if credentials are already set in environment
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("✅ AWS environment variables loaded from environment")
    else:
        print("⚠️  AWS credentials not found in environment variables")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")

def initialize_api() -> genai.Client:
    """Load API key from environment variables and return a genai client."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables. Please create a .env file and add it.")
    
    client = genai.Client(api_key=api_key)
    print("✅ Gemini API client initialized successfully.")
    return client

def validate_image(image_path: str) -> None:
    """Validate that the path exists and is a readable image."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    try:
        with Image.open(image_path) as im:
            im.verify()  # lightweight check
    except Exception as e:
        raise ValueError(f"File is not a valid image: {image_path}") from e

def assign_global_difficulties(image_count: int, config: S3QuestionGeneratorConfig) -> List[str]:
    """Assign difficulties globally across all images based on distribution ratios."""
    if config.randomize:
        # Choose a random global distribution
        distribution = random.choice(config.global_difficulty_distributions)
    else:
        # Use the first distribution as default
        distribution = config.global_difficulty_distributions[0]
    
    # Calculate the number of questions for each difficulty
    difficulties = []
    for difficulty, ratio in distribution.items():
        count = max(1, round(image_count * ratio))  # Ensure at least 1 question of each difficulty
        difficulties.extend([difficulty] * count)
    
    # Adjust to match exactly the image count
    while len(difficulties) > image_count:
        difficulties.pop()  # Remove excess
    while len(difficulties) < image_count:
        # Add more from the most common difficulty
        most_common = max(distribution.keys(), key=lambda k: distribution[k])
        difficulties.append(most_common)
    
    # Shuffle the difficulties for random assignment
    if config.randomize:
        random.shuffle(difficulties)
    
    print(f"📋 Global difficulty distribution: {dict((d, difficulties.count(d)) for d in set(difficulties))}")
    return difficulties

def generate_single_question_prompt(
    config: S3QuestionGeneratorConfig, 
    image_filename: str, 
    assigned_difficulty: str
) -> str:
    """Generate a prompt for a single question with specified difficulty."""
    
    if config.randomize:
        # Randomize subject context and question style
        subject_context = random.choice(config.subject_contexts)
        question_style = random.choice(config.question_styles)
        
        # Add variation to the analysis approach
        analysis_approaches = [
            "carefully analyze the provided image",
            "examine the scientific content shown in the image",
            "study the educational material presented in the image",
            "investigate the principles illustrated in the image"
        ]
        analysis_approach = random.choice(analysis_approaches)
    else:
        # Default values when randomization is disabled
        subject_context = "physics teacher's perspective"
        question_style = "conceptual understanding"
        analysis_approach = "analyze the provided image"
    
    prompt = f"""
    From a {subject_context}, {analysis_approach} with focus on {question_style}.
    Generate exactly 1 multiple-choice question with '{assigned_difficulty}' difficulty level.

    You MUST return your response as a single, raw JSON array containing exactly ONE object.
    Do not include any introductory text, explanations, or markdown code fences like ```json or ```.
    The response should start with '[' and end with ']'.

    The single object in the JSON array must have these exact keys:
    - "question_text": A string containing the question.
    - "image_path": A string representing the image file name, use "{image_filename}".
    - "option_text": A list of exactly four strings representing the possible answers.
    - "correct_answer_index": The integer index (0-3) of the correct option.
    - "difficulty_level": A string which must be exactly '{assigned_difficulty}'.
    - "explanation": A string that clearly explains why the correct answer is right, based on scientific principles.
    - "topic": A string indicating the main scientific topic or concept covered.
    - "subtopic": A string indicating the specific subtopic or area within the main topic.
    
    Ensure the question is scientifically accurate and appropriately challenging for the '{assigned_difficulty}' difficulty level.
    Make the question diverse and engaging while maintaining scientific rigor.
    """
    
    return prompt

def generate_question_from_s3_image(
    s3_key: str,
    s3_handler: S3ImageHandler,
    client: genai.Client,
    config: S3QuestionGeneratorConfig,
    assigned_difficulty: str,
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """Generate a single question from an S3 image with specified difficulty."""
    
    image_filename = os.path.basename(s3_key)
    temp_path = None
    
    for attempt in range(max_retries):
        try:
            print(f"  📸 Processing: {image_filename} (attempt {attempt + 1}/{max_retries})")
            print(f"  🎯 Target difficulty: {assigned_difficulty}")
            
            # Download image from S3 to temporary file
            temp_path = s3_handler.download_image_to_temp(s3_key)
            if not temp_path:
                raise Exception("Failed to download image from S3")
            
            # Validate the downloaded image
            validate_image(temp_path)
            
            # Upload to Gemini
            image_file = client.files.upload(file=temp_path)
            print(f"  ✓ Image uploaded to Gemini API")
            
            # Generate prompt for single question
            prompt = generate_single_question_prompt(config, image_filename, assigned_difficulty)
            
            if config.randomize:
                print(f"  ✓ Generated randomized prompt for {assigned_difficulty} difficulty")
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
            print("  ⏳ Sending request to Gemini API...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, image_file]
            )
            
            # Clean and parse response
            response_text = (response.text or "").strip()
            
            # Remove potential markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            parsed_json = json.loads(response_text)
            
            # Validate response structure
            if not isinstance(parsed_json, list) or len(parsed_json) != 1:
                raise ValueError("Expected exactly one question in JSON array")
            
            question = parsed_json[0]
            
            if not isinstance(question, dict):
                raise ValueError("Question is not a valid object")
            
            required_keys = [
                "question_text", "image_path", "option_text", 
                "correct_answer_index", "difficulty_level", "explanation"
            ]
            for key in required_keys:
                if key not in question:
                    raise ValueError(f"Missing required key: {key}")
            
            if not isinstance(question["option_text"], list) or len(question["option_text"]) != 4:
                raise ValueError("Must have exactly 4 answer options")
            
            if question["difficulty_level"] != assigned_difficulty:
                print(f"  ⚠️  Warning: Generated difficulty '{question['difficulty_level']}' doesn't match assigned '{assigned_difficulty}'")
                question["difficulty_level"] = assigned_difficulty  # Force correct difficulty
            
            # Ensure optional fields exist
            if "topic" not in question:
                question["topic"] = "Physics"
            if "subtopic" not in question:
                question["subtopic"] = "General"
            
            # Set correct image path with S3 URL
            question["image_path"] = s3_handler.generate_s3_url(s3_key)
            question["image_filename"] = image_filename  # Keep filename for reference
            
            print(f"  ✅ Successfully generated 1 question with {assigned_difficulty} difficulty")
            return question
            
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
        
        finally:
            # Clean up temporary file after each attempt
            if temp_path:
                s3_handler.cleanup_temp_file(temp_path)
                temp_path = None
    
    print(f"  ❌ Failed to generate question for {image_filename} after {max_retries} attempts")
    return None

def process_s3_images(
    s3_handler: S3ImageHandler,
    s3_prefix: str,
    client: genai.Client,
    config: S3QuestionGeneratorConfig,
    max_images: Optional[int] = None
) -> Dict[str, Any]:
    """Process images from S3 and generate questions with global difficulty distribution."""
    
    print(f"🔍 Scanning S3 bucket for images with prefix: {s3_prefix}")
    image_keys = s3_handler.list_image_files(s3_prefix)
    
    if not image_keys:
        raise ValueError(f"No image files found in S3 bucket with prefix: {s3_prefix}")
    
    # Limit number of images if specified
    if max_images and len(image_keys) > max_images:
        if config.randomize:
            image_keys = random.sample(image_keys, max_images)
        else:
            image_keys = image_keys[:max_images]
    
    print(f"📊 Processing {len(image_keys)} images from S3")
    
    # Assign difficulties globally across all images
    difficulties = assign_global_difficulties(len(image_keys), config)
    
    # Pair each image with its assigned difficulty
    image_difficulty_pairs = list(zip(image_keys, difficulties))
    
    if config.randomize:
        random.shuffle(image_difficulty_pairs)  # Randomize processing order
    
    all_questions = []
    processing_stats = {
        "total_images": len(image_keys),
        "successful": 0,
        "failed": 0,
        "total_questions": 0,
        "start_time": datetime.now().isoformat(),
        "s3_bucket": s3_handler.bucket_name,
        "s3_prefix": s3_prefix,
        "global_difficulty_distribution": dict((d, difficulties.count(d)) for d in set(difficulties)),
        "image_results": {}
    }
    
    for i, (s3_key, assigned_difficulty) in enumerate(image_difficulty_pairs, 1):
        image_filename = os.path.basename(s3_key)
        print(f"\n📸 [{i}/{len(image_keys)}] Processing: {image_filename}")
        
        try:
            question = generate_question_from_s3_image(
                s3_key, s3_handler, client, config, assigned_difficulty
            )
            
            if question:
                all_questions.append(question)
                processing_stats["successful"] += 1
                processing_stats["total_questions"] += 1
                processing_stats["image_results"][image_filename] = {
                    "status": "success",
                    "s3_key": s3_key,
                    "s3_url": s3_handler.generate_s3_url(s3_key),
                    "question_count": 1,
                    "assigned_difficulty": assigned_difficulty,
                    "generated_difficulty": question.get("difficulty_level", "Unknown")
                }
                print(f"  ✅ Success! Generated 1 question with {assigned_difficulty} difficulty")
            else:
                processing_stats["failed"] += 1
                processing_stats["image_results"][image_filename] = {
                    "status": "failed",
                    "s3_key": s3_key,
                    "s3_url": s3_handler.generate_s3_url(s3_key),
                    "assigned_difficulty": assigned_difficulty,
                    "question_count": 0
                }
        
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            processing_stats["failed"] += 1
            processing_stats["image_results"][image_filename] = {
                "status": "error",
                "s3_key": s3_key,
                "s3_url": s3_handler.generate_s3_url(s3_key),
                "assigned_difficulty": assigned_difficulty,
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
        stats_file = f"{base_name}_s3_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(results["stats"], f, ensure_ascii=False, indent=2)
    
    return questions_file, stats_file

def print_summary(stats: Dict[str, Any]) -> None:
    """Print a summary of the processing results."""
    print(f"\n{'='*60}")
    print("📊 S3 PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"S3 Bucket: {stats['s3_bucket']}")
    print(f"S3 Prefix: {stats['s3_prefix']}")
    print(f"Total Images Processed: {stats['total_images']}")
    print(f"Successful: {stats['successful']} ({stats['success_rate']:.1f}%)")
    print(f"Failed: {stats['failed']}")
    print(f"Total Questions Generated: {stats['total_questions']} (1 per image)")
    
    print(f"\n🎯 Global Difficulty Distribution:")
    for difficulty, count in stats['global_difficulty_distribution'].items():
        percentage = (count / stats['total_images']) * 100
        print(f"   {difficulty}: {count} questions ({percentage:.1f}%)")
    
    print(f"\nProcessing Time: {stats['start_time']} to {stats['end_time']}")
    print(f"{'='*60}")

# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="S3-Enhanced MCQ generator - processes images from S3 with global difficulty distribution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process all images from S3 with randomization
    python s3_enhanced_question_generator.py --s3-prefix "Diagrams/Physics/images/"
    
    # Process specific number of images with fixed seed
    python s3_enhanced_question_generator.py --s3-prefix "Diagrams/Physics/images/" --max-images 20 --seed 42
    
    # Disable randomization for consistent output
    python s3_enhanced_question_generator.py --s3-prefix "Diagrams/Physics/images/" --no-randomize
        """
    )
    
    # S3 Configuration
    parser.add_argument("--s3-bucket", type=str, default="images-questionbank",
                       help="S3 bucket name (default: images-questionbank)")
    parser.add_argument("--s3-prefix", type=str, default="Diagrams/Physics/images/",
                       help="S3 prefix/folder path (default: Diagrams/Physics/images/)")
    
    # AWS Credentials (can also be set via environment variables)
    parser.add_argument("--aws-access-key", type=str, default=None,
                       help="AWS Access Key ID (default: from environment or aws.py)")
    parser.add_argument("--aws-secret-key", type=str, default=None,
                       help="AWS Secret Access Key (default: from environment or aws.py)")
    parser.add_argument("--aws-region", type=str, default="us-west-2",
                       help="AWS region (default: us-west-2)")
    
    # Output arguments
    parser.add_argument("--output", type=str, default="s3_questions.json",
                       help="Output JSON file for all questions (default: s3_questions.json)")
    
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
    
    print("🚀 S3-Enhanced Question Generator Starting...")
    print(f"☁️  S3 Bucket: {args.s3_bucket}")
    print(f"📁 S3 Prefix: {args.s3_prefix}")
    print(f"📄 Output File: {args.output}")
    
    # Initialize configuration
    config = S3QuestionGeneratorConfig(
        randomize=not args.no_randomize,
        seed=args.seed
    )
    
    if config.randomize:
        seed_info = f" (seed: {args.seed})" if args.seed else " (random seed)"
        print(f"🎲 Randomization: Enabled{seed_info}")
    else:
        print("🔒 Randomization: Disabled")
    
    print("📋 Mode: 1 question per image with global difficulty distribution")
    
    # Setup AWS environment (using credentials from aws.py)
    setup_aws_environment()
    
    # Get AWS credentials
    aws_access_key = args.aws_access_key or os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = args.aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if not aws_access_key or not aws_secret_key:
        print("❌ AWS credentials not found. Please provide them via arguments or environment variables.")
        exit(1)
    
    # Check dependencies
    try:
        import dotenv  # noqa: F401
    except ImportError:
        print("❌ Required package 'python-dotenv' is not installed.")
        print("Please run: pip install python-dotenv boto3")
        exit(1)
    
    # Initialize S3 handler
    try:
        s3_handler = S3ImageHandler(
            bucket_name=args.s3_bucket,
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            region=args.aws_region
        )
    except Exception as e:
        print(f"❌ Failed to initialize S3 handler: {e}")
        exit(1)
    
    # Initialize Gemini API client  
    try:
        client = initialize_api()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        exit(1)
    
    # Process all images from S3
    try:
        results = process_s3_images(
            s3_handler,
            args.s3_prefix,
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
            print(f"   Image URL: {sample_q['image_path']}")
            print(f"   Image File: {sample_q.get('image_filename', 'N/A')}")
            print(f"   Topic: {sample_q.get('topic', 'N/A')}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        exit(1)
    
    print("\n✅ S3 processing completed successfully!")
