import streamlit as st
import json
import os
import time
from datetime import datetime, timedelta
from PIL import Image
import base64
from io import BytesIO

# Import the question generation functionality
try:
    from image import generate_questions_from_image_live, initialize_api, update_image_paths
    GENERATION_AVAILABLE = True
except ImportError:
    GENERATION_AVAILABLE = False
    st.warning("Question generation not available. Install required dependencies.")

def load_questions(json_file="questions.json"):
    """Load questions from JSON file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Questions file '{json_file}' not found!")
        return []
    except json.JSONDecodeError:
        st.error(f"Invalid JSON format in '{json_file}'!")
        return []

def save_questions(questions, json_file="questions.json"):
    """Save questions to JSON file."""
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving questions: {e}")
        return False

def display_image(image_path):
    """Display image if it exists."""
    if image_path and os.path.exists(image_path):
        try:
            image = Image.open(image_path)
            st.image(image, caption="Question Image", use_container_width=True)
        except Exception as e:
            st.error(f"Error loading image: {e}")
    elif image_path:
        st.warning(f"Image not found: {image_path}")

def calculate_score(user_answers, questions):
    """Calculate the exam score."""
    correct = 0
    total = len(questions)
    
    for i, question in enumerate(questions):
        if i < len(user_answers) and user_answers[i] == question['correct_answer_index']:
            correct += 1
    
    return correct, total, (correct / total * 100) if total > 0 else 0

def format_time(seconds):
    """Format time in MM:SS format."""
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def main():
    st.set_page_config(
        page_title="Physics MCQ Examination System",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🧪 Physics MCQ Examination System")
    st.markdown("---")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["📝 Take Exam", "📊 View Results", "⚙️ Question Management", "🔄 Generate Questions"]
    )
    
    if page == "📝 Take Exam":
        exam_page()
    elif page == "📊 View Results":
        results_page()
    elif page == "⚙️ Question Management":
        question_management_page()
    elif page == "🔄 Generate Questions":
        generate_questions_page()

def exam_page():
    """Main examination interface."""
    st.header("📝 Physics Examination")
    
    # Load questions
    questions = load_questions()
    if not questions:
        st.error("No questions available. Please check the questions.json file.")
        return
    
    # Initialize session state
    if 'exam_started' not in st.session_state:
        st.session_state.exam_started = False
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = [-1] * len(questions)
    if 'exam_finished' not in st.session_state:
        st.session_state.exam_finished = False
    if 'exam_duration' not in st.session_state:
        st.session_state.exam_duration = 20  # Default 20 minutes
    
    # Pre-exam setup
    if not st.session_state.exam_started:
        st.subheader("Exam Instructions")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            **Welcome to the Physics MCQ Examination!**
            
            📋 **Instructions:**
            - This exam contains multiple-choice questions on physics concepts
            - Each question has 4 options, select the most appropriate answer
            - You can navigate between questions using the navigation buttons
            - Your answers are automatically saved as you progress
            - Click 'Submit Exam' when you're finished
            
            ⏰ **Time Management:**
            - Set your desired exam duration using the slider
            - A timer will be displayed during the exam
            - The exam will auto-submit when time expires
            
            🎯 **Scoring:**
            - Each correct answer: +1 point
            - No negative marking for incorrect answers
            - Results will be displayed immediately after submission
            """)
        
        with col2:
            st.info(f"📊 **Exam Overview**\n\n"
                   f"Total Questions: {len(questions)}\n\n"
                   f"Difficulty Breakdown:\n"
                   f"- Easy: {sum(1 for q in questions if q['difficulty_level'] == 'Easy')}\n"
                   f"- Medium: {sum(1 for q in questions if q['difficulty_level'] == 'Medium')}\n"
                   f"- Hard: {sum(1 for q in questions if q['difficulty_level'] == 'Hard')}")
        
        # Exam duration setting
        st.session_state.exam_duration = st.slider(
            "⏱️ Set Exam Duration (minutes):",
            min_value=5,
            max_value=60,
            value=st.session_state.exam_duration,
            step=5
        )
        
        if st.button("🚀 Start Exam", type="primary", use_container_width=True):
            st.session_state.exam_started = True
            st.session_state.start_time = time.time()
            st.session_state.user_answers = [-1] * len(questions)
            st.session_state.exam_finished = False
            st.rerun()
    
    # During exam
    elif st.session_state.exam_started and not st.session_state.exam_finished:
        # Timer
        elapsed_time = time.time() - st.session_state.start_time
        total_time = st.session_state.exam_duration * 60
        remaining_time = max(0, total_time - elapsed_time)
        
        # Auto-submit if time is up
        if remaining_time <= 0:
            st.session_state.exam_finished = True
            st.rerun()
        
        # Display timer
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if remaining_time <= 300:  # Less than 5 minutes
                st.error(f"⏰ Time Remaining: {format_time(remaining_time)}")
            elif remaining_time <= 600:  # Less than 10 minutes
                st.warning(f"⏰ Time Remaining: {format_time(remaining_time)}")
            else:
                st.info(f"⏰ Time Remaining: {format_time(remaining_time)}")
        
        # Question navigation
        if 'current_question' not in st.session_state:
            st.session_state.current_question = 0
        
        # Progress bar
        progress = (st.session_state.current_question + 1) / len(questions)
        st.progress(progress)
        st.caption(f"Question {st.session_state.current_question + 1} of {len(questions)}")
        
        # Display current question
        current_q = questions[st.session_state.current_question]
        
        st.markdown("---")
        
        # Question content
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.subheader(f"Question {st.session_state.current_question + 1}")
            
            # Difficulty badge
            difficulty_color = {
                'Easy': 'green',
                'Medium': 'orange', 
                'Hard': 'red'
            }
            st.markdown(f"<span style='background-color:{difficulty_color.get(current_q['difficulty_level'], 'gray')}; "
                       f"color:white; padding:4px 8px; border-radius:4px; font-size:12px;'>"
                       f"{current_q['difficulty_level']}</span>", 
                       unsafe_allow_html=True)
            
            st.markdown(f"**{current_q['question_text']}**")
            
            # Answer options
            answer = st.radio(
                "Select your answer:",
                options=range(len(current_q['option_text'])),
                format_func=lambda x: f"{chr(65+x)}. {current_q['option_text'][x]}",
                index=st.session_state.user_answers[st.session_state.current_question] if st.session_state.user_answers[st.session_state.current_question] != -1 else None,
                key=f"question_{st.session_state.current_question}"
            )
            
            # Save answer
            if answer is not None:
                st.session_state.user_answers[st.session_state.current_question] = answer
        
        with col2:
            # Display image if available
            if 'image_path' in current_q and current_q['image_path']:
                display_image(current_q['image_path'])
        
        # Navigation buttons
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        with col1:
            if st.button("⬅️ Previous", disabled=st.session_state.current_question == 0):
                st.session_state.current_question -= 1
                st.rerun()
        
        with col2:
            if st.button("➡️ Next", disabled=st.session_state.current_question == len(questions) - 1):
                st.session_state.current_question += 1
                st.rerun()
        
        with col3:
            # Question navigator
            question_num = st.selectbox(
                "Jump to:",
                options=range(len(questions)),
                format_func=lambda x: f"Q{x+1}",
                index=st.session_state.current_question,
                key="question_navigator"
            )
            if question_num != st.session_state.current_question:
                st.session_state.current_question = question_num
                st.rerun()
        
        with col4:
            # Submit exam
            answered_count = sum(1 for ans in st.session_state.user_answers if ans != -1)
            if st.button(f"✅ Submit Exam ({answered_count}/{len(questions)} answered)", 
                        type="primary"):
                if answered_count < len(questions):
                    if st.checkbox("I understand that some questions are unanswered"):
                        st.session_state.exam_finished = True
                        st.rerun()
                else:
                    st.session_state.exam_finished = True
                    st.rerun()
        
        # Answer status grid
        st.markdown("---")
        st.subheader("📋 Answer Status")
        
        cols = st.columns(10)
        for i in range(len(questions)):
            col_idx = i % 10
            with cols[col_idx]:
                if st.session_state.user_answers[i] != -1:
                    if i == st.session_state.current_question:
                        st.success(f"Q{i+1} ✓")
                    else:
                        st.info(f"Q{i+1} ✓")
                else:
                    if i == st.session_state.current_question:
                        st.warning(f"Q{i+1}")
                    else:
                        st.error(f"Q{i+1}")
    
    # After exam completion
    elif st.session_state.exam_finished:
        display_results(questions)

def display_results(questions):
    """Display exam results."""
    st.header("🎉 Exam Completed!")
    
    # Calculate results
    correct, total, percentage = calculate_score(st.session_state.user_answers, questions)
    
    # Overall results
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Score", f"{correct}/{total}")
    
    with col2:
        st.metric("📈 Percentage", f"{percentage:.1f}%")
    
    with col3:
        if percentage >= 80:
            st.metric("🏆 Grade", "Excellent", delta="A+")
        elif percentage >= 70:
            st.metric("🏆 Grade", "Good", delta="A")
        elif percentage >= 60:
            st.metric("🏆 Grade", "Average", delta="B")
        else:
            st.metric("🏆 Grade", "Needs Improvement", delta="C")
    
    with col4:
        exam_time = time.time() - st.session_state.start_time
        st.metric("⏱️ Time Taken", format_time(exam_time))
    
    # Performance by difficulty
    st.subheader("📈 Performance Analysis")
    
    difficulty_stats = {}
    for level in ['Easy', 'Medium', 'Hard']:
        level_questions = [i for i, q in enumerate(questions) if q['difficulty_level'] == level]
        if level_questions:
            level_correct = sum(1 for i in level_questions 
                              if i < len(st.session_state.user_answers) and 
                              st.session_state.user_answers[i] == questions[i]['correct_answer_index'])
            level_total = len(level_questions)
            difficulty_stats[level] = {
                'correct': level_correct,
                'total': level_total,
                'percentage': (level_correct / level_total * 100) if level_total > 0 else 0
            }
    
    col1, col2, col3 = st.columns(3)
    for i, (level, stats) in enumerate(difficulty_stats.items()):
        with [col1, col2, col3][i]:
            st.metric(
                f"{level} Questions",
                f"{stats['correct']}/{stats['total']}",
                f"{stats['percentage']:.1f}%"
            )
    
    # Detailed results
    with st.expander("🔍 View Detailed Results", expanded=False):
        for i, question in enumerate(questions):
            user_answer = st.session_state.user_answers[i] if i < len(st.session_state.user_answers) else -1
            correct_answer = question['correct_answer_index']
            
            if user_answer == correct_answer:
                st.success(f"**Question {i+1}** ✅ Correct")
            elif user_answer == -1:
                st.warning(f"**Question {i+1}** ⚪ Not Answered")
            else:
                st.error(f"**Question {i+1}** ❌ Incorrect")
            
            st.write(f"**Q:** {question['question_text']}")
            
            if user_answer != -1:
                st.write(f"**Your Answer:** {chr(65+user_answer)}. {question['option_text'][user_answer]}")
            else:
                st.write("**Your Answer:** Not answered")
            
            st.write(f"**Correct Answer:** {chr(65+correct_answer)}. {question['option_text'][correct_answer]}")
            st.write(f"**Explanation:** {question['explanation']}")
            st.markdown("---")
    
    # Action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Take Another Exam", type="primary", use_container_width=True):
            # Reset exam state
            for key in ['exam_started', 'start_time', 'user_answers', 'exam_finished', 'current_question']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    with col2:
        # Save results to session state for results page
        if 'exam_history' not in st.session_state:
            st.session_state.exam_history = []
        
        exam_result = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'score': f"{correct}/{total}",
            'percentage': percentage,
            'time_taken': format_time(time.time() - st.session_state.start_time),
            'difficulty_breakdown': difficulty_stats
        }
        
        if len(st.session_state.exam_history) == 0 or st.session_state.exam_history[-1] != exam_result:
            st.session_state.exam_history.append(exam_result)
        
        if st.button("📊 View All Results", use_container_width=True):
            st.session_state.page = "📊 View Results"
            st.rerun()

def results_page():
    """Display historical exam results."""
    st.header("📊 Exam Results History")
    
    if 'exam_history' not in st.session_state or not st.session_state.exam_history:
        st.info("No exam results available yet. Take an exam to see your results here!")
        return
    
    # Display results table
    results_data = []
    for i, result in enumerate(st.session_state.exam_history):
        results_data.append({
            'Exam #': i + 1,
            'Date': result['date'],
            'Score': result['score'],
            'Percentage': f"{result['percentage']:.1f}%",
            'Time Taken': result['time_taken']
        })
    
    st.dataframe(results_data, use_container_width=True)
    
    # Statistics
    if len(st.session_state.exam_history) > 1:
        st.subheader("📈 Performance Trends")
        
        percentages = [r['percentage'] for r in st.session_state.exam_history]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Best Score", f"{max(percentages):.1f}%")
        
        with col2:
            st.metric("Average Score", f"{sum(percentages)/len(percentages):.1f}%")
        
        with col3:
            improvement = percentages[-1] - percentages[0] if len(percentages) > 1 else 0
            st.metric("Improvement", f"{improvement:+.1f}%")

def question_management_page():
    """Manage questions in the system."""
    st.header("⚙️ Question Management")
    
    questions = load_questions()
    
    if not questions:
        st.warning("No questions loaded. Generate or import questions first.")
        return
    
    # Display questions
    st.subheader(f"📝 Current Questions ({len(questions)} total)")
    
    # Filter by difficulty
    difficulty_filter = st.selectbox(
        "Filter by difficulty:",
        options=["All", "Easy", "Medium", "Hard"]
    )
    
    filtered_questions = questions
    if difficulty_filter != "All":
        filtered_questions = [q for q in questions if q['difficulty_level'] == difficulty_filter]
    
    # Display questions
    for i, question in enumerate(filtered_questions):
        with st.expander(f"Question {questions.index(question) + 1}: {question['question_text'][:50]}..."):
            st.write(f"**Difficulty:** {question['difficulty_level']}")
            st.write(f"**Question:** {question['question_text']}")
            
            # Display options
            for j, option in enumerate(question['option_text']):
                if j == question['correct_answer_index']:
                    st.success(f"{chr(65+j)}. {option} ✅")
                else:
                    st.write(f"{chr(65+j)}. {option}")
            
            st.write(f"**Explanation:** {question['explanation']}")
            
            if 'image_path' in question and question['image_path']:
                display_image(question['image_path'])

def generate_questions_page():
    """Generate new questions from images.""" 
    st.header("🔄 Generate New Questions")
    
    if not GENERATION_AVAILABLE:
        st.error("Question generation is not available. Please install the required dependencies:")
        st.code("pip install google-genai python-dotenv pillow")
        return
    
    st.info("📝 **Remember:** You need to configure your Google Gemini API key first [[memory:4405792]]!")
    
    # Image upload
    uploaded_file = st.file_uploader(
        "Upload an image for question generation:",
        type=['png', 'jpg', 'jpeg'],
        help="Upload a physics diagram or image to generate questions from"
    )
    
    # Image path input
    image_path = st.text_input(
        "Or enter path to existing image:",
        placeholder="e.g., images/physics_diagram.jpg"
    )
    
    # Configuration
    st.subheader("⚙️ Generation Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        num_easy = st.number_input("Easy questions:", min_value=0, max_value=10, value=2)
        num_medium = st.number_input("Medium questions:", min_value=0, max_value=10, value=2) 
        num_hard = st.number_input("Hard questions:", min_value=0, max_value=10, value=1)
    
    with col2:
        append_mode = st.checkbox("Append to existing questions", value=True)
        if not append_mode:
            st.warning("⚠️ This will replace all existing questions!")
    
    # Generate button
    if st.button("🎯 Generate Questions", type="primary", disabled=not (uploaded_file or image_path)):
        try:
            # Handle file upload
            if uploaded_file:
                # Save uploaded file temporarily
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                image_to_process = temp_path
            else:
                image_to_process = image_path
            
            # Initialize API
            with st.spinner("Initializing API..."):
                client = initialize_api()
            
            # Generate questions
            with st.spinner("Generating questions... This may take a moment."):
                new_questions = generate_questions_from_image_live(image_to_process, client)
            
            if new_questions:
                # Update image paths to use the actual image file
                new_questions = update_image_paths(new_questions, image_to_process)
                
                # Update questions
                if append_mode:
                    existing_questions = load_questions()
                    combined_questions = existing_questions + new_questions
                else:
                    combined_questions = new_questions
                
                # Save to file
                if save_questions(combined_questions):
                    st.success(f"✅ Successfully generated and saved {len(new_questions)} new questions!")
                    
                    # Display preview
                    with st.expander("🔍 Preview Generated Questions"):
                        for i, q in enumerate(new_questions):
                            st.write(f"**Question {i+1}:** {q['question_text']}")
                            st.write(f"**Difficulty:** {q['difficulty_level']}")
                            for j, option in enumerate(q['option_text']):
                                if j == q['correct_answer_index']:
                                    st.success(f"{chr(65+j)}. {option}")
                                else:
                                    st.write(f"{chr(65+j)}. {option}")
                            st.markdown("---")
                else:
                    st.error("Failed to save questions to file.")
            else:
                st.error("Failed to generate questions. Please check your API configuration and image.")
            
            # Clean up temporary file
            if uploaded_file and os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as e:
            st.error(f"Error generating questions: {e}")
            # Clean up on error
            if uploaded_file and 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    main()
