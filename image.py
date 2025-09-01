from google import genai
import json
import os
import argparse
from PIL import Image  # Used to verify the image file
from dotenv import load_dotenv

def initialize_api():
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

def generate_questions_from_image_live(image_path: str, client: genai.Client) -> list | None:
    """
    Takes an image, sends it to the Gemini API, and returns parsed JSON output (list).
    """
    try:
        validate_image(image_path)
        print(f"Processing image: {image_path}...")

        # Upload the image
        image_file = client.files.upload(file=image_path)
        print(f"Image uploaded successfully: {image_path}")

        # Prompt (kept as you provided)
        prompt = """
        From a physics teacher's perspective, analyze the provided image which illustrates Torricelli's Law.
        Generate exactly 5 multiple-choice questions with a range of difficulties:
        - 2 'Easy'
        - 2 'Medium'
        - 1 'Hard'

        You MUST return your response as a single, raw JSON array of objects.
        Do not include any introductory text, explanations, or markdown code fences like ```json or ```.
        The response should start with '[' and end with ']'.

        Each object in the JSON array must have these exact keys:
        - "question_text": A string containing the question.
        - "image_path": A string representing the local path to the image file, use "page_1_image_0.jpg".
        - "option_text": A list of four strings representing the possible answers.
        - "correct_answer_index": The integer index (0-3) of the correct option.
        - "difficulty_level": A string which must be 'Easy', 'Medium', or 'Hard'.
        - "explanation": A string that clearly explains why the correct answer is right, based on physics principles.
        """

        print("Sending request to the Gemini API... This might take a moment.")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, image_file]
        )

        # Parse model text directly as JSON
        response_text = (response.text or "").strip()
        parsed_json = json.loads(response_text)  # may raise JSONDecodeError

        # Optional: quick schema sanity check (keeps your keys)
        if not isinstance(parsed_json, list):
            raise ValueError("Model output is not a JSON array.")
        for i, item in enumerate(parsed_json, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Item {i} is not an object.")
            for key in ["question_text", "image_path", "option_text", "correct_answer_index", "difficulty_level", "explanation"]:
                if key not in item:
                    raise ValueError(f"Item {i} missing key: {key}")
            if not isinstance(item["option_text"], list) or len(item["option_text"]) != 4:
                raise ValueError(f"Item {i} must have exactly 4 options.")
            if item["difficulty_level"] not in ["Easy", "Medium", "Hard"]:
                raise ValueError(f"Item {i} has invalid difficulty_level: {item['difficulty_level']}")

        print("Successfully received and parsed the JSON response from the API.")
        return parsed_json

    except json.JSONDecodeError:
        print("\n--- JSON DECODING ERROR ---")
        print("The API did not return a valid JSON object. This can happen with model variability.")
        print("Below is the raw text received from the API for debugging:")
        print("---------------------------------")
        print(response.text if 'response' in locals() and hasattr(response, 'text') else "(no response text)")
        print("---------------------------------")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print("\nRaw API Response on Error:", response.text)
        return None

def update_image_paths(data: list, actual_image_path: str) -> list:
    """Update the image_path in all questions to use the actual image path."""
    for question in data:
        if 'image_path' in question:
            question['image_path'] = actual_image_path
    return data

def save_json(data: list, out_path: str) -> str:
    """Write data to JSON file, ensure directory exists, return final path."""
    out_path = out_path or "questions.json"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out_path

# --- Main Execution Block ---
if __name__ == "__main__":
    # CLI args for image path and output JSON file
    parser = argparse.ArgumentParser(description="Generate MCQs from an image and save to JSON.")
    parser.add_argument("--image", type=str, default="page_1_image_0.jpg", help="Path to the image to analyze.")
    parser.add_argument("--out", type=str, default="questions.json", help="Path to output JSON file.")
    args = parser.parse_args()

    # Dependency hint
    try:
        import dotenv  # noqa: F401
    except ImportError:
        print("Required package 'python-dotenv' is not installed. Please run: pip install python-dotenv")
        exit(1)

    # Initialize API client
    try:
        client = initialize_api()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        exit(1)

    # Generate questions
    generated_questions = generate_questions_from_image_live(args.image, client)

    # Save to JSON file
    if generated_questions:
        # Update image paths to use the actual image file
        generated_questions = update_image_paths(generated_questions, args.image)
        out_file = save_json(generated_questions, args.out)
        print(f"\n========== FINAL GENERATED QUESTIONS ==========")
        print(json.dumps(generated_questions, indent=2))
        print("=============================================\n")
        print(f"JSON saved to: {out_file}")
    else:
        print("\nQuestion generation failed. Please review the error messages above.")
