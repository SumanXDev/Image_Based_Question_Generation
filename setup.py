#!/usr/bin/env python3
"""
Physics Examination System Setup Script

This script helps you set up the environment securely for the first time.
"""

import os
import shutil

def create_env_file():
    """Create .env file from template with user input"""
    print("🔧 Setting up environment configuration...")
    
    if os.path.exists('.env'):
        response = input(".env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return False
    
    print("\n📝 Please provide your AWS credentials:")
    print("(You can find these in your AWS Console > IAM > Security Credentials)")
    
    aws_access_key = input("AWS Access Key ID: ").strip()
    aws_secret_key = input("AWS Secret Access Key: ").strip()
    aws_region = input("AWS Region (default: us-west-2): ").strip() or "us-west-2"
    
    google_api_key = input("Google API Key (optional, for question generation): ").strip()
    
    env_content = f"""# AWS Credentials
AWS_ACCESS_KEY_ID={aws_access_key}
AWS_SECRET_ACCESS_KEY={aws_secret_key}
AWS_DEFAULT_REGION={aws_region}

# S3 Configuration
S3_BUCKET=images-questionbank
S3_PREFIX=Diagrams/Physics/images/

# Google API Key (only needed if using question generator)
GOOGLE_API_KEY={google_api_key}

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env file created successfully!")
    return True

def create_aws_script():
    """Create aws.py from template"""
    print("\n🔧 Setting up AWS upload script...")
    
    if os.path.exists('aws.py'):
        response = input("aws.py already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("AWS script setup skipped.")
            return False
    
    if os.path.exists('aws_template.py'):
        shutil.copy('aws_template.py', 'aws.py')
        print("✅ aws.py created from template!")
        print("💡 You can now run 'python aws.py' to upload images to S3")
        return True
    else:
        print("❌ aws_template.py not found!")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    
    try:
        import subprocess
        subprocess.check_call(['pip', 'install', '-r', 'streamlit_requirements.txt'])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies. Please run manually:")
        print("pip install -r streamlit_requirements.txt")
        return False
    except FileNotFoundError:
        print("❌ pip not found. Please install Python and pip first.")
        return False

def main():
    """Main setup function"""
    print("🚀 Physics Examination System Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('streamlit_exam_app.py'):
        print("❌ Error: streamlit_exam_app.py not found!")
        print("Please run this script from the project root directory.")
        return
    
    success_count = 0
    
    # Step 1: Create .env file
    if create_env_file():
        success_count += 1
    
    # Step 2: Create aws.py script
    if create_aws_script():
        success_count += 1
    
    # Step 3: Install dependencies
    if install_dependencies():
        success_count += 1
    
    print("\n" + "=" * 50)
    if success_count == 3:
        print("🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Run 'python aws.py' to upload images to S3 (if needed)")
        print("2. Run 'streamlit run streamlit_exam_app.py' to start the app")
        print("3. Open http://localhost:8501 in your browser")
    else:
        print(f"⚠️  Setup partially completed ({success_count}/3 steps)")
        print("Please check the error messages above and try again.")
    
    print("\n🔒 Security reminder:")
    print("Never commit your .env or aws.py files to version control!")

if __name__ == "__main__":
    main()
