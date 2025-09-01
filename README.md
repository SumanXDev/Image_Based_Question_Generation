# Physics Examination System

An interactive physics examination system that automatically generates questions from images stored in Amazon S3, with a user-friendly Streamlit interface.

![Physics Examination System](https://img.shields.io/badge/Physics-Examination_System-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.22+-red)
![Python](https://img.shields.io/badge/Python-3.8+-green)

## 📋 Features

- **Automatic Question Generation**: Uses S3 images to generate physics questions
- **Customizable Exams**: Configure number of questions and difficulty distribution
- **Interactive UI**: User-friendly interface with question navigation
- **Real-time Feedback**: Immediate scoring and detailed explanations
- **S3 Integration**: Direct image loading from your S3 bucket
- **Cloud-Ready**: Easy deployment to various cloud platforms

## 🚀 Quick Start

### Automated Setup (Recommended)

1. **Run the setup script**:
   ```bash
   python setup.py
   ```
   This will guide you through setting up credentials and dependencies.

2. **Start the application**:
   ```bash
   streamlit run streamlit_exam_app.py
   ```

3. **Access the app** at http://localhost:8501

### Manual Setup

1. **Install dependencies**:
   ```bash
   pip install -r streamlit_requirements.txt
   ```

2. **Create environment file**:
   ```bash
   cp env.example .env
   # Edit .env with your AWS credentials
   ```

3. **Run the Streamlit app**:
   ```bash
   streamlit run streamlit_exam_app.py
   ```

### Docker Deployment

1. **Build the Docker image**:
   ```bash
   docker build -t physics-exam .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8501:8501 physics-exam
   ```

3. **Access the app** at http://localhost:8501

## 🔧 Configuration

### Environment Variables

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_DEFAULT_REGION`: AWS region (default: us-west-2)

### S3 Configuration

The app is configured to use:
- Bucket: `images-questionbank`
- Prefix: `Diagrams/Physics/images/`

To change these settings, modify the constants at the top of `streamlit_exam_app.py`.

## 📊 Exam Workflow

1. **Welcome Screen**: Enter user information and configure exam settings
2. **Question Interface**: Answer questions with interactive navigation
3. **Results Page**: View detailed performance breakdown and explanations

## 🧩 Components

### 1. Question Generator

The system can work in two modes:
- **Local JSON**: Uses pre-generated questions from `s3_questions.json`
- **API Integration**: Can call the question generator API for dynamic question generation

### 2. S3 Image Integration

- Direct loading of images from S3 URLs
- Automatic URL generation for S3 objects
- Efficient image caching

### 3. Examination UI

- Progress tracking
- Timer functionality
- Question navigation
- Difficulty indicators

### 4. Scoring System

- Overall score calculation
- Performance breakdown by difficulty
- Detailed explanations for each question

## 🌐 Cloud Deployment

See [deploy_to_cloud.md](deploy_to_cloud.md) for detailed instructions on deploying to:
- Streamlit Cloud
- AWS Elastic Beanstalk
- Google Cloud Run
- Heroku

## 📝 License

This project is available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.