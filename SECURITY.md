# Security Best Practices

## 🔐 Environment Variables Security

### Local Development

1. **Create a `.env` file** in your project root (this file is gitignored):
   ```env
   AWS_ACCESS_KEY_ID=your_aws_access_key_here
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
   AWS_DEFAULT_REGION=us-west-2
   S3_BUCKET=images-questionbank
   S3_PREFIX=Diagrams/Physics/images/
   GOOGLE_API_KEY=your_google_api_key_here
   ```

2. **Never commit credentials** to version control:
   - The `.gitignore` file already includes `.env`
   - Use `env.example` as a template for required variables

### Cloud Deployment Security

#### Streamlit Cloud
1. Go to your app's settings in Streamlit Cloud
2. Navigate to "Secrets"
3. Add your environment variables:
   ```toml
   AWS_ACCESS_KEY_ID = "your_aws_access_key_here"
   AWS_SECRET_ACCESS_KEY = "your_aws_secret_key_here"
   AWS_DEFAULT_REGION = "us-west-2"
   ```

#### AWS Deployment
**Best Practice: Use IAM Roles instead of access keys**

1. Create an IAM role with the necessary S3 permissions:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "s3:GetObject",
                   "s3:ListBucket"
               ],
               "Resource": [
                   "arn:aws:s3:::images-questionbank",
                   "arn:aws:s3:::images-questionbank/*"
               ]
           }
       ]
   }
   ```

2. Attach the role to your EC2 instance, ECS task, or Lambda function
3. Remove AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables

#### Google Cloud Run
```bash
gcloud run deploy physics-exam \
  --image gcr.io/YOUR-PROJECT-ID/physics-exam \
  --set-env-vars="AWS_ACCESS_KEY_ID=your_key,AWS_SECRET_ACCESS_KEY=your_secret"
```

#### Heroku
```bash
heroku config:set AWS_ACCESS_KEY_ID=your_key
heroku config:set AWS_SECRET_ACCESS_KEY=your_secret
```

## 🛡️ Additional Security Measures

### S3 Bucket Security

1. **Restrict bucket access** to only necessary IPs:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Deny",
               "Principal": "*",
               "Action": "s3:*",
               "Resource": [
                   "arn:aws:s3:::images-questionbank",
                   "arn:aws:s3:::images-questionbank/*"
               ],
               "Condition": {
                   "IpAddressIfExists": {
                       "aws:SourceIp": ["1.2.3.4/32", "5.6.7.8/32"]
                   }
               }
           }
       ]
   }
   ```

2. **Enable CloudTrail** for S3 access logging
3. **Use VPC endpoints** for S3 access if deploying in AWS

### Application Security

1. **Input Validation**: The app already validates user inputs
2. **Rate Limiting**: Consider adding rate limiting for production
3. **HTTPS Only**: Always deploy with HTTPS enabled
4. **Content Security Policy**: Add CSP headers if serving custom HTML

### Monitoring and Alerts

1. **CloudWatch Alarms** for unusual S3 access patterns
2. **AWS GuardDuty** for threat detection
3. **Application logs** for user activity monitoring

## 🔍 Security Checklist

- [ ] No hardcoded credentials in source code
- [ ] Environment variables used for all secrets
- [ ] `.env` file added to `.gitignore`
- [ ] IAM roles used instead of access keys (AWS deployments)
- [ ] S3 bucket permissions follow principle of least privilege
- [ ] HTTPS enabled in production
- [ ] Regular credential rotation scheduled
- [ ] Monitoring and alerting configured
- [ ] Security scanning included in CI/CD pipeline

## 🚨 If Credentials Are Compromised

1. **Immediately rotate** the compromised credentials
2. **Check CloudTrail logs** for unauthorized access
3. **Review S3 bucket access logs**
4. **Update all deployments** with new credentials
5. **Consider enabling MFA** for AWS account root user

## 📞 Reporting Security Issues

If you discover a security vulnerability, please report it privately by:
1. Creating a private security advisory on GitHub
2. Or emailing the maintainers directly

Do not create public issues for security vulnerabilities.
