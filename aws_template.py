"""
AWS S3 Upload Script Template

This is a template for uploading images to S3. 
DO NOT commit the actual aws.py file with real credentials to version control.

Instructions:
1. Copy this file to aws.py
2. Replace the placeholder values with your actual AWS credentials
3. Run the script to upload your images to S3
4. The actual aws.py file is gitignored for security
"""

import boto3
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS Configuration - Use environment variables for security
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')

# Validate credentials are available
if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    print("❌ Error: AWS credentials not found!")
    print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file")
    exit(1)

# Set environment variables for boto3
os.environ['AWS_ACCESS_KEY_ID'] = AWS_ACCESS_KEY_ID
os.environ['AWS_SECRET_ACCESS_KEY'] = AWS_SECRET_ACCESS_KEY
os.environ['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION

# S3 Configuration
bucket_name = 'images-questionbank'
local_folder = 'images'  # Change this to your local folder path
new_prefix = 'Diagrams/Physics/images/'

print(f"🚀 Starting upload from '{local_folder}' to s3://{bucket_name}/{new_prefix}")

# Create an S3 client
try:
    s3 = boto3.client('s3')
    print("✅ S3 client initialized successfully")
except Exception as e:
    print(f"❌ Error initializing S3 client: {e}")
    exit(1)

# Upload files
upload_count = 0
for root, dirs, files in os.walk(local_folder):
    for file in files:
        print(f"Processing: {file}")
        local_path = os.path.join(root, file)
        
        # Compute relative path to maintain subdirectory structure
        relative_path = os.path.relpath(local_path, local_folder)
        
        # Construct the S3 key; replace backslashes if on Windows
        s3_key = os.path.join(new_prefix, relative_path).replace("\\", "/")
        
        try:
            print(f'📤 Uploading {local_path} to s3://{bucket_name}/{s3_key}')
            s3.upload_file(local_path, bucket_name, s3_key)
            upload_count += 1
            print(f'✅ Successfully uploaded {file}')
        except Exception as e:
            print(f'❌ Error uploading {file}: {e}')

print(f"\n🎉 Upload completed! {upload_count} files uploaded successfully.")
print(f"Your images are now available at: https://{bucket_name}.s3.amazonaws.com/{new_prefix}")
