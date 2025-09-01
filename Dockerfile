FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY streamlit_requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY streamlit_exam_app.py ./
COPY s3_questions.json ./

# If you want to include the question generator (optional)
COPY s3_enhanced_question_generator.py ./

# Set default environment variables (will be overridden by deployment platform)
ENV AWS_DEFAULT_REGION=us-west-2
ENV S3_BUCKET=images-questionbank
ENV S3_PREFIX=Diagrams/Physics/images/

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "streamlit_exam_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
