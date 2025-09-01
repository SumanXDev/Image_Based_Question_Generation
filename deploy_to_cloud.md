# Deploying the Physics Examination System to the Cloud

This guide provides instructions for deploying your Streamlit Physics Examination System to various cloud platforms.

## 🔐 Security Note

**Important**: Never commit AWS credentials to your repository. The application now uses environment variables for all sensitive information. See [SECURITY.md](SECURITY.md) for detailed security best practices.

## Option 1: Deploy to Streamlit Cloud (Easiest)

[Streamlit Cloud](https://streamlit.io/cloud) provides a simple way to deploy Streamlit apps with minimal configuration.

1. Create a GitHub repository with your code
2. Include these files:
   - `streamlit_exam_app.py`
   - `requirements.txt` (rename from streamlit_requirements.txt)
   - `s3_questions.json` (optional, for offline testing)

3. Sign up for Streamlit Cloud and connect your GitHub account
4. Deploy your app by selecting your repository
5. Add the following secrets in the Streamlit Cloud dashboard (go to Settings → Secrets):
   ```toml
   AWS_ACCESS_KEY_ID = "your_aws_access_key_here"
   AWS_SECRET_ACCESS_KEY = "your_aws_secret_key_here"
   AWS_DEFAULT_REGION = "us-west-2"
   S3_BUCKET = "images-questionbank"
   S3_PREFIX = "Diagrams/Physics/images/"
   ```

## Option 2: Deploy to AWS Elastic Beanstalk

1. Install the AWS CLI and EB CLI
2. Initialize your EB application:
   ```bash
   eb init -p docker physics-exam
   ```

3. Create an environment:
   ```bash
   eb create physics-exam-env
   ```

4. Deploy your application:
   ```bash
   eb deploy
   ```

5. Open your application:
   ```bash
   eb open
   ```

## Option 3: Deploy to Google Cloud Run

1. Install the Google Cloud SDK
2. Build and push your Docker image:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR-PROJECT-ID/physics-exam
   ```

3. Deploy to Cloud Run:
   ```bash
   gcloud run deploy physics-exam \
     --image gcr.io/YOUR-PROJECT-ID/physics-exam \
     --platform managed \
     --allow-unauthenticated \
     --set-env-vars="AWS_ACCESS_KEY_ID=your_aws_access_key_here,AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here,AWS_DEFAULT_REGION=us-west-2,S3_BUCKET=images-questionbank,S3_PREFIX=Diagrams/Physics/images/"
   ```

## Option 4: Deploy to Heroku

1. Install the Heroku CLI
2. Login to Heroku:
   ```bash
   heroku login
   ```

3. Create a new Heroku app:
   ```bash
   heroku create physics-exam
   ```

4. Create a `heroku.yml` file:
   ```yaml
   build:
     docker:
       web: Dockerfile
   ```

5. Set the stack to container:
   ```bash
   heroku stack:set container
   ```

6. Set environment variables:
   ```bash
   heroku config:set AWS_ACCESS_KEY_ID=your_aws_access_key_here
   heroku config:set AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
   heroku config:set AWS_DEFAULT_REGION=us-west-2
   heroku config:set S3_BUCKET=images-questionbank
   heroku config:set S3_PREFIX=Diagrams/Physics/images/
   ```

7. Deploy your app:
   ```bash
   git push heroku main
   ```

## Security Considerations

1. **AWS Credentials**: For production, use IAM roles instead of hardcoded credentials:
   - For AWS: Use IAM roles for EC2/ECS
   - For other platforms: Use environment variables or secrets management

2. **S3 Bucket Access**: Consider setting up a CloudFront distribution in front of your S3 bucket for:
   - Better performance (global CDN)
   - Additional security layer
   - Bandwidth cost optimization

3. **API Keys**: If using the question generator API in production:
   - Store API keys in environment variables or secrets manager
   - Implement rate limiting
   - Consider caching generated questions

## Scaling Considerations

1. **Database Integration**: For larger deployments, consider adding:
   - User authentication system
   - Database for storing exam results
   - Admin dashboard for managing exams

2. **Performance Optimization**:
   - Pre-generate question sets for popular configurations
   - Implement caching for S3 images
   - Use a CDN for image delivery

3. **Monitoring**:
   - Add logging and monitoring
   - Track usage patterns
   - Set up alerts for errors or unusual activity
