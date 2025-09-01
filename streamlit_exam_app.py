import streamlit as st
import json
import boto3
import os
import random
import time
from PIL import Image
import io
import requests
import pandas as pd
from datetime import datetime
import uuid

# Set page configuration
st.set_page_config(
    page_title="Physics Examination System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# AWS S3 Configuration - Load from environment variables
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
S3_BUCKET = os.getenv('S3_BUCKET', 'images-questionbank')
S3_PREFIX = os.getenv('S3_PREFIX', 'Diagrams/Physics/images/')

# Validate configuration
def validate_config():
    """Validate that all required configuration is available"""
    missing_vars = []
    
    if not AWS_ACCESS_KEY_ID:
        missing_vars.append('AWS_ACCESS_KEY_ID')
    if not AWS_SECRET_ACCESS_KEY:
        missing_vars.append('AWS_SECRET_ACCESS_KEY')
    
    if missing_vars:
        st.error(f"""
        ❌ **Configuration Error**
        
        The following environment variables are missing:
        {', '.join(missing_vars)}
        
        Please set these environment variables before running the application.
        
        **For local development:**
        1. Create a `.env` file in the project directory
        2. Add the following lines:
        ```
        AWS_ACCESS_KEY_ID=your_access_key_here
        AWS_SECRET_ACCESS_KEY=your_secret_key_here
        AWS_DEFAULT_REGION=us-west-2
        ```
        
        **For cloud deployment:**
        Set these as environment variables or secrets in your deployment platform.
        """)
        st.stop()

# Initialize session state variables
def init_session_state():
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'answers' not in st.session_state:
        st.session_state.answers = {}
    if 'exam_started' not in st.session_state:
        st.session_state.exam_started = False
    if 'exam_completed' not in st.session_state:
        st.session_state.exam_completed = False
    if 'timer_start' not in st.session_state:
        st.session_state.timer_start = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = {}
    if 'exam_id' not in st.session_state:
        st.session_state.exam_id = str(uuid.uuid4())[:8]
    if 'difficulty_distribution' not in st.session_state:
        st.session_state.difficulty_distribution = {"Easy": 0, "Medium": 0, "Hard": 0}

# S3 Helper Functions
def setup_aws_client():
    """Set up and return an S3 client using AWS credentials"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_DEFAULT_REGION
        )
        return s3_client
    except Exception as e:
        st.error(f"Error setting up AWS client: {e}")
        return None

def list_s3_image_files(s3_client, prefix=S3_PREFIX):
    """List all image files in the S3 bucket with the given prefix"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
    image_keys = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
        
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Check if the file has an image extension
                    if any(key.lower().endswith(ext) for ext in image_extensions):
                        image_keys.append(key)
        
        return sorted(image_keys)
    
    except Exception as e:
        st.error(f"Error listing S3 objects: {e}")
        return []

def generate_s3_url(s3_key):
    """Generate an unsigned S3 URL for a given S3 key"""
    return f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"

def load_image_from_url(url):
    """Load an image from a URL"""
    try:
        response = requests.get(url)
        img = Image.open(io.BytesIO(response.content))
        return img
    except Exception as e:
        st.error(f"Error loading image from URL: {e}")
        return None

# Question Generation Functions
def generate_questions(num_questions=10, difficulty_distribution=None):
    """
    Generate questions with specified difficulty distribution
    
    Args:
        num_questions: Total number of questions to generate
        difficulty_distribution: Dict with keys 'Easy', 'Medium', 'Hard' and values as percentages
    
    Returns:
        List of question dictionaries
    """
    if difficulty_distribution is None:
        difficulty_distribution = {"Easy": 50, "Medium": 30, "Hard": 20}
    
    # Initialize S3 client
    s3_client = setup_aws_client()
    if not s3_client:
        return []
    
    # Get all available image files
    all_image_keys = list_s3_image_files(s3_client)
    if not all_image_keys:
        st.error("No images found in S3 bucket")
        return []
    
    # Calculate number of questions for each difficulty
    question_counts = {
        difficulty: int(round(num_questions * (percentage / 100)))
        for difficulty, percentage in difficulty_distribution.items()
    }
    
    # Adjust to ensure we have exactly num_questions
    total = sum(question_counts.values())
    if total < num_questions:
        # Add remaining to the most common difficulty
        most_common = max(difficulty_distribution.keys(), key=lambda k: difficulty_distribution[k])
        question_counts[most_common] += (num_questions - total)
    elif total > num_questions:
        # Remove excess from the most common difficulty
        most_common = max(difficulty_distribution.keys(), key=lambda k: difficulty_distribution[k])
        question_counts[most_common] -= (total - num_questions)
    
    # Update session state with actual distribution
    st.session_state.difficulty_distribution = question_counts
    
    # Try loading from questions.json if available (for development/testing)
    try:
        with open("s3_questions.json", "r") as f:
            all_questions = json.load(f)
            
        # Filter and select questions based on difficulty
        questions = []
        for difficulty, count in question_counts.items():
            filtered = [q for q in all_questions if q["difficulty_level"] == difficulty]
            if filtered:
                # Select random questions of this difficulty
                selected = random.sample(filtered, min(count, len(filtered)))
                questions.extend(selected)
        
        # If we don't have enough questions, fill with random ones
        if len(questions) < num_questions:
            remaining = num_questions - len(questions)
            remaining_questions = random.sample(
                [q for q in all_questions if q not in questions],
                min(remaining, len(all_questions) - len(questions))
            )
            questions.extend(remaining_questions)
        
        # Shuffle the questions
        random.shuffle(questions)
        return questions[:num_questions]
    
    except FileNotFoundError:
        st.warning("Questions file not found. In production, this would call the question generator API.")
        
        # In production, you would call your S3 question generator here
        # For now, we'll create dummy questions for demonstration
        dummy_questions = []
        for difficulty, count in question_counts.items():
            for i in range(count):
                # Select a random image
                image_key = random.choice(all_image_keys)
                image_url = generate_s3_url(image_key)
                
                dummy_questions.append({
                    "question_text": f"Sample {difficulty} question about {os.path.basename(image_key)}",
                    "image_path": image_url,
                    "image_filename": os.path.basename(image_key),
                    "option_text": [
                        f"Option A for {difficulty} question",
                        f"Option B for {difficulty} question",
                        f"Option C for {difficulty} question",
                        f"Option D for {difficulty} question"
                    ],
                    "correct_answer_index": random.randint(0, 3),
                    "difficulty_level": difficulty,
                    "explanation": f"This is an explanation for a {difficulty} question."
                })
        
        random.shuffle(dummy_questions)
        return dummy_questions

# UI Helper Functions
def format_time(seconds):
    """Format seconds into minutes and seconds"""
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def show_timer():
    """Display a timer showing elapsed time"""
    if st.session_state.timer_start:
        elapsed = time.time() - st.session_state.timer_start
        st.sidebar.markdown(f"### ⏱️ Time Elapsed: {format_time(elapsed)}")

def show_progress():
    """Display progress through the exam"""
    if st.session_state.questions:
        progress = (st.session_state.current_question_index + 1) / len(st.session_state.questions)
        st.sidebar.progress(progress)
        st.sidebar.markdown(f"Question {st.session_state.current_question_index + 1} of {len(st.session_state.questions)}")

def display_difficulty_badge(difficulty):
    """Display a colored badge for the difficulty level"""
    if difficulty == "Easy":
        return st.sidebar.markdown("**Difficulty:** 🟢 Easy")
    elif difficulty == "Medium":
        return st.sidebar.markdown("**Difficulty:** 🟠 Medium")
    elif difficulty == "Hard":
        return st.sidebar.markdown("**Difficulty:** 🔴 Hard")
    else:
        return st.sidebar.markdown(f"**Difficulty:** {difficulty}")

# Navigation Functions
def next_question():
    """Move to the next question"""
    if st.session_state.current_question_index < len(st.session_state.questions) - 1:
        st.session_state.current_question_index += 1
    else:
        st.session_state.exam_completed = True

def prev_question():
    """Move to the previous question"""
    if st.session_state.current_question_index > 0:
        st.session_state.current_question_index -= 1

def jump_to_question(index):
    """Jump to a specific question"""
    if 0 <= index < len(st.session_state.questions):
        st.session_state.current_question_index = index

def submit_exam():
    """Submit the exam and calculate results"""
    st.session_state.exam_completed = True

def restart_exam():
    """Reset the exam state"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()

# Page Components
def show_welcome_page():
    """Display the welcome page with exam setup options"""
    st.title("📚 Physics Examination System")
    st.markdown("### Welcome to the online examination system!")
    
    with st.form("user_info_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", key="name")
            email = st.text_input("Email", key="email")
        with col2:
            institution = st.text_input("Institution/School", key="institution")
            student_id = st.text_input("Student ID (optional)", key="student_id")
        
        st.markdown("### Exam Configuration")
        col1, col2 = st.columns(2)
        with col1:
            num_questions = st.slider("Number of Questions", min_value=5, max_value=30, value=10, step=5)
        with col2:
            time_limit = st.slider("Time Limit (minutes)", min_value=10, max_value=120, value=30, step=5)
        
        st.markdown("### Difficulty Distribution")
        col1, col2, col3 = st.columns(3)
        with col1:
            easy_percent = st.slider("Easy (%)", min_value=0, max_value=100, value=50, step=10)
        with col2:
            medium_percent = st.slider("Medium (%)", min_value=0, max_value=100, value=30, step=10)
        with col3:
            hard_percent = st.slider("Hard (%)", min_value=0, max_value=100, value=20, step=10)
        
        # Validate percentages add up to 100%
        total_percent = easy_percent + medium_percent + hard_percent
        if total_percent != 100:
            st.warning(f"Difficulty percentages must add up to 100%. Current total: {total_percent}%")
        
        submitted = st.form_submit_button("Start Exam")
        
        if submitted and total_percent == 100:
            st.session_state.user_info = {
                "name": name,
                "email": email,
                "institution": institution,
                "student_id": student_id,
                "num_questions": num_questions,
                "time_limit": time_limit,
                "difficulty_distribution": {
                    "Easy": easy_percent,
                    "Medium": medium_percent,
                    "Hard": hard_percent
                }
            }
            
            # Generate questions
            with st.spinner("Preparing your examination..."):
                questions = generate_questions(
                    num_questions=num_questions,
                    difficulty_distribution={"Easy": easy_percent, "Medium": medium_percent, "Hard": hard_percent}
                )
                
                if questions:
                    st.session_state.questions = questions
                    st.session_state.exam_started = True
                    st.session_state.timer_start = time.time()
                    st.experimental_rerun()
                else:
                    st.error("Failed to generate questions. Please try again.")

def show_question_navigator():
    """Display the question navigator in the sidebar"""
    st.sidebar.markdown("### Question Navigator")
    
    # Create a grid of question buttons
    cols = st.sidebar.columns(5)
    for i, question in enumerate(st.session_state.questions):
        # Determine button color based on whether question is answered
        button_label = f"{i+1}"
        button_key = f"nav_btn_{i}"
        
        # Check if this question has been answered
        answered = i in st.session_state.answers
        
        # Highlight current question
        is_current = i == st.session_state.current_question_index
        
        # Choose button style
        if is_current:
            # Current question - blue
            button_label = f"**{button_label}**"
        elif answered:
            # Answered - green
            pass
        
        # Place button in the appropriate column
        col_index = i % 5
        if cols[col_index].button(button_label, key=button_key, use_container_width=True):
            jump_to_question(i)
            st.experimental_rerun()

def show_exam_page():
    """Display the main exam page with questions"""
    # Get current question
    if not st.session_state.questions:
        st.error("No questions available. Please restart the exam.")
        return
    
    question = st.session_state.questions[st.session_state.current_question_index]
    
    # Display question
    st.markdown(f"## Question {st.session_state.current_question_index + 1}")
    st.markdown(f"### {question['question_text']}")
    
    # Display image if available
    if 'image_path' in question and question['image_path']:
        try:
            st.image(question['image_path'], caption=question.get('image_filename', ''), use_column_width=True)
        except Exception as e:
            st.error(f"Error displaying image: {e}")
    
    # Display options
    option_labels = ["A", "B", "C", "D"]
    options = question.get('option_text', [])
    
    # Get previously selected answer if any
    current_answer = st.session_state.answers.get(st.session_state.current_question_index, None)
    
    # Display radio buttons for options
    selected_option = st.radio(
        "Select your answer:",
        options=range(len(options)),
        format_func=lambda i: f"{option_labels[i]}. {options[i]}",
        index=current_answer if current_answer is not None else 0,
        key=f"q{st.session_state.current_question_index}_options"
    )
    
    # Save the selected answer
    st.session_state.answers[st.session_state.current_question_index] = selected_option
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("← Previous", disabled=st.session_state.current_question_index == 0):
            prev_question()
            st.experimental_rerun()
    
    with col2:
        if st.button("Submit Exam", type="primary"):
            if len(st.session_state.answers) < len(st.session_state.questions):
                unanswered = len(st.session_state.questions) - len(st.session_state.answers)
                if not st.checkbox("I confirm I want to submit with unanswered questions", key="confirm_submit"):
                    st.warning(f"You have {unanswered} unanswered questions. Please check the navigator.")
                else:
                    submit_exam()
                    st.experimental_rerun()
            else:
                submit_exam()
                st.experimental_rerun()
    
    with col3:
        if st.button("Next →", disabled=st.session_state.current_question_index == len(st.session_state.questions) - 1):
            next_question()
            st.experimental_rerun()
    
    # Show difficulty in sidebar
    display_difficulty_badge(question.get('difficulty_level', 'Unknown'))

def calculate_results():
    """Calculate exam results"""
    if not st.session_state.questions:
        return {
            "score": 0,
            "total": 0,
            "percentage": 0,
            "correct": 0,
            "incorrect": 0,
            "unanswered": 0,
            "by_difficulty": {},
            "time_taken": 0
        }
    
    total_questions = len(st.session_state.questions)
    correct = 0
    by_difficulty = {"Easy": {"total": 0, "correct": 0}, 
                    "Medium": {"total": 0, "correct": 0}, 
                    "Hard": {"total": 0, "correct": 0}}
    
    for i, question in enumerate(st.session_state.questions):
        difficulty = question.get('difficulty_level', 'Unknown')
        if difficulty in by_difficulty:
            by_difficulty[difficulty]["total"] += 1
        
        if i in st.session_state.answers:
            if st.session_state.answers[i] == question.get('correct_answer_index', 0):
                correct += 1
                if difficulty in by_difficulty:
                    by_difficulty[difficulty]["correct"] += 1
    
    # Calculate time taken
    time_taken = 0
    if st.session_state.timer_start:
        time_taken = time.time() - st.session_state.timer_start
    
    return {
        "score": correct,
        "total": total_questions,
        "percentage": (correct / total_questions) * 100 if total_questions > 0 else 0,
        "correct": correct,
        "incorrect": sum(1 for i in st.session_state.answers if st.session_state.answers[i] != st.session_state.questions[i].get('correct_answer_index', 0)),
        "unanswered": total_questions - len(st.session_state.answers),
        "by_difficulty": by_difficulty,
        "time_taken": time_taken
    }

def show_results_page():
    """Display the results page"""
    st.title("📊 Exam Results")
    
    # Calculate results
    results = calculate_results()
    
    # Display summary
    st.markdown(f"### Summary for {st.session_state.user_info.get('name', 'Student')}")
    st.markdown(f"**Exam ID:** {st.session_state.exam_id}")
    st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Score overview
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score", f"{results['score']}/{results['total']}")
    with col2:
        st.metric("Percentage", f"{results['percentage']:.1f}%")
    with col3:
        st.metric("Time Taken", format_time(results['time_taken']))
    
    # Question breakdown
    st.markdown("### Question Breakdown")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Correct", results['correct'])
    with col2:
        st.metric("Incorrect", results['incorrect'])
    with col3:
        st.metric("Unanswered", results['unanswered'])
    
    # Performance by difficulty
    st.markdown("### Performance by Difficulty")
    diff_data = []
    for diff, stats in results['by_difficulty'].items():
        if stats['total'] > 0:
            percentage = (stats['correct'] / stats['total']) * 100
            diff_data.append({
                "Difficulty": diff,
                "Correct": stats['correct'],
                "Total": stats['total'],
                "Percentage": f"{percentage:.1f}%"
            })
    
    st.table(pd.DataFrame(diff_data))
    
    # Detailed answers
    st.markdown("### Detailed Review")
    with st.expander("View Question Details"):
        for i, question in enumerate(st.session_state.questions):
            user_answer = st.session_state.answers.get(i, None)
            correct_answer = question.get('correct_answer_index', 0)
            is_correct = user_answer == correct_answer
            
            st.markdown(f"#### Question {i+1}: {question['question_text']}")
            
            # Display image if available
            if 'image_path' in question and question['image_path']:
                st.image(question['image_path'], width=400)
            
            # Display options and answers
            options = question.get('option_text', [])
            option_labels = ["A", "B", "C", "D"]
            
            for j, option in enumerate(options):
                prefix = ""
                if j == correct_answer:
                    prefix = "✅ "
                elif j == user_answer:
                    prefix = "❌ " if not is_correct else ""
                
                st.markdown(f"{prefix}**{option_labels[j]}.** {option}")
            
            st.markdown(f"**Your Answer:** {option_labels[user_answer] if user_answer is not None else 'Not answered'}")
            st.markdown(f"**Correct Answer:** {option_labels[correct_answer]}")
            st.markdown(f"**Difficulty:** {question.get('difficulty_level', 'Unknown')}")
            
            if 'explanation' in question:
                st.markdown(f"**Explanation:** {question['explanation']}")
            
            st.markdown("---")
    
    # Restart button
    if st.button("Start New Exam", type="primary"):
        restart_exam()
        st.experimental_rerun()

# Main app
def main():
    # Validate configuration first
    validate_config()
    
    # Initialize session state
    init_session_state()
    
    # Display sidebar content
    st.sidebar.title("Physics Exam")
    
    if st.session_state.exam_started:
        show_timer()
        show_progress()
        
        if not st.session_state.exam_completed:
            show_question_navigator()
    
    # Display main content based on app state
    if not st.session_state.exam_started:
        show_welcome_page()
    elif st.session_state.exam_completed:
        show_results_page()
    else:
        show_exam_page()

if __name__ == "__main__":
    main()
