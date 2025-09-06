# Honda Veteran Talent Matching - Deployment Guide

This guide provides comprehensive instructions for deploying the Honda Veteran Talent Matching system to AWS.

## Overview

The system uses a serverless architecture with the following components:
- **Backend**: AWS Lambda functions with API Gateway
- **Database**: DynamoDB tables
- **Authentication**: AWS Cognito
- **AI/ML**: AWS Bedrock (Claude Sonnet 4)
- **Frontend**: React SPA hosted on S3 with optional CloudFront CDN
- **CI/CD**: GitHub Actions with Serverless Framework 4

## Prerequisites

### Required Tools
- [Node.js 18+](https://nodejs.org/)
- [Python 3.12](https://www.python.org/)
- [AWS CLI](https://aws.amazon.com/cli/)
- [Serverless Framework 4](https://www.serverless.com/)
- [Git](https://git-scm.com/)

### AWS Requirements
- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Access to the following AWS services:
  - Lambda
  - API Gateway
  - DynamoDB
  - Cognito
  - S3
  - Bedrock (Claude Sonnet 4)
  - CloudFormation
  - IAM

### Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/leadlea/honda.git
   cd honda
   ```

2. **Install backend dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Install Serverless Framework**:
   ```bash
   npm install -g serverless@4
   npm install
   ```

4. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

## Deployment Methods

### Method 1: Automated Deployment (GitHub Actions)

The system includes automated CI/CD pipelines that deploy on push to main/develop branches.

#### Setup GitHub Secrets

Configure the following secrets in your GitHub repository:

```
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
SERVERLESS_ACCESS_KEY=your_serverless_access_key (optional)
```

#### Deployment Process

1. **Push to develop branch** → Deploys to `dev` stage
2. **Push to main branch** → Deploys to `prod` stage

The pipeline will:
1. Run tests and code quality checks
2. Deploy backend infrastructure and Lambda functions
3. Deploy frontend to S3
4. Generate CloudFront configuration files

### Method 2: Manual Deployment

#### Step 1: Deploy Backend

```bash
# Deploy to development
serverless deploy --stage dev

# Deploy to production
serverless deploy --stage prod
```

#### Step 2: Deploy Frontend

```bash
# Deploy frontend to development
./scripts/deploy-frontend.sh dev

# Deploy frontend to production
./scripts/deploy-frontend.sh prod
```

#### Step 3: Setup CloudFront (Optional)

```bash
# Generate CloudFront configuration
./scripts/prepare-cloudfront.sh dev

# Create CloudFront distribution
aws cloudfront create-distribution --distribution-config file://cloudfront-config-dev.json
```

## Configuration

### Environment Variables

The system uses the following environment variables:

#### Backend (Lambda)
- `STAGE`: Deployment stage (dev/prod)
- `REGION`: AWS region (us-west-2)
- `DYNAMODB_TABLE_PREFIX`: DynamoDB table prefix
- `BEDROCK_MODEL_ID`: Bedrock model identifier
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `COGNITO_CLIENT_ID`: Cognito Client ID

#### Frontend (React)
- `REACT_APP_API_URL`: API Gateway endpoint URL
- `REACT_APP_COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `REACT_APP_COGNITO_CLIENT_ID`: Cognito Client ID
- `REACT_APP_REGION`: AWS region
- `REACT_APP_STAGE`: Deployment stage

### AWS Resources Created

The deployment creates the following AWS resources:

#### DynamoDB Tables
- `{service}-{stage}-users`
- `{service}-{stage}-veteran-profiles`
- `{service}-{stage}-opportunities`
- `{service}-{stage}-recommendations`
- `{service}-{stage}-questionnaires`
- `{service}-{stage}-questionnaire-responses`
- `{service}-{stage}-applications`
- `{service}-{stage}-public-profiles`
- `{service}-{stage}-contact-requests`

#### Lambda Functions
- `authHandler`: Authentication and user management
- `profileHandler`: Profile CRUD operations
- `businessTitleHandler`: AI-powered business title generation
- `questionnaireHandler`: Dynamic questionnaire management
- `matchingHandler`: AI-powered matching and recommendations
- `applicationHandler`: Application management
- `publicSearchHandler`: Public veteran search
- `contactHandler`: External contact management

#### Other Resources
- Cognito User Pool and Client
- API Gateway with custom authorizer
- S3 bucket for frontend hosting
- IAM roles and policies

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `GET /auth/profile` - Get user profile
- `PUT /auth/permissions` - Update permissions

### Profile Management
- `GET /profiles/{userId}` - Get veteran profile
- `PUT /profiles/{userId}` - Update veteran profile
- `PUT /profiles/{userId}/privacy` - Update privacy settings
- `POST /profiles/{userId}/business-title` - Generate business title

### Questionnaire
- `GET /questionnaire/{userId}` - Get questionnaire
- `POST /questionnaire/{userId}/submit` - Submit responses
- `GET /questionnaire/{userId}/history` - Get response history
- `PUT /questionnaire/{userId}/regenerate` - Regenerate questionnaire

### Recommendations
- `GET /recommendations/{userId}` - Get recommendations

### Applications
- `POST /applications/{userId}` - Create application
- `PUT /applications/{applicationId}/status` - Update application status
- `GET /opportunities/search` - Search opportunities

### Public Platform
- `GET /public/veterans/search` - Search public veterans
- `GET /public/veterans/{profileId}` - Get public profile
- `POST /public/contact/{profileId}` - Contact veteran
- `GET /public/categories` - Get skill categories

## Monitoring and Troubleshooting

### CloudWatch Logs

Monitor Lambda function logs in CloudWatch:
```bash
# View logs for a specific function
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/honda-veteran-talent-matching"

# Tail logs in real-time
serverless logs -f authHandler --tail --stage dev
```

### Common Issues

#### 1. Deployment Failures
- **Issue**: CloudFormation stack creation fails
- **Solution**: Check IAM permissions and AWS service limits

#### 2. CORS Errors
- **Issue**: Frontend can't access API
- **Solution**: Verify API Gateway CORS configuration

#### 3. Authentication Issues
- **Issue**: Users can't log in
- **Solution**: Check Cognito configuration and JWT token validation

#### 4. AI Service Errors
- **Issue**: Bedrock API calls fail
- **Solution**: Verify Bedrock access permissions and model availability

### Health Checks

Test the deployment with these commands:

```bash
# Test API Gateway endpoint
curl -X GET "https://your-api-id.execute-api.us-west-2.amazonaws.com/dev/public/categories"

# Test Cognito authentication
aws cognito-idp admin-get-user --user-pool-id your-pool-id --username test@example.com

# Test DynamoDB access
aws dynamodb scan --table-name honda-veteran-talent-matching-dev-users --limit 1
```

## Security Considerations

### Data Protection
- All data is encrypted at rest and in transit
- PII data is handled according to privacy requirements
- Access is controlled through IAM roles and Cognito

### API Security
- All authenticated endpoints require valid JWT tokens
- Rate limiting is configured through API Gateway
- Request validation is enabled

### Network Security
- HTTPS is enforced for all communications
- CORS is properly configured
- Security headers are set

## Performance Optimization

### Lambda Functions
- Memory allocation optimized per function
- Cold start mitigation through provisioned concurrency (if needed)
- Connection pooling for DynamoDB

### Frontend
- Static assets cached with long TTL
- HTML files served with no-cache headers
- Compression enabled

### Database
- DynamoDB queries optimized with proper indexing
- Connection reuse in Lambda functions
- Batch operations where applicable

## Cost Optimization

### AWS Resources
- DynamoDB uses on-demand billing
- Lambda functions sized appropriately
- S3 storage class optimization
- CloudFront caching reduces origin requests

### Monitoring Costs
- Use AWS Cost Explorer to monitor spending
- Set up billing alerts
- Regular review of resource utilization

## Backup and Recovery

### Data Backup
- DynamoDB point-in-time recovery enabled
- S3 versioning for frontend assets
- CloudFormation templates in version control

### Disaster Recovery
- Multi-AZ deployment for high availability
- Infrastructure as Code for quick recovery
- Regular backup testing

## Support and Maintenance

### Regular Tasks
- Monitor CloudWatch metrics and alarms
- Review and rotate access keys
- Update dependencies and security patches
- Performance optimization reviews

### Scaling Considerations
- Lambda concurrency limits
- DynamoDB capacity planning
- API Gateway throttling limits
- Bedrock API rate limits

## Additional Resources

- [AWS Serverless Application Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/)
- [Serverless Framework Documentation](https://www.serverless.com/framework/docs/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [React Deployment Best Practices](https://create-react-app.dev/docs/deployment/)

For additional support, please refer to the project documentation or contact the development team.