# Honda Veteran Talent Matching System

AI-powered veteran talent matching system that helps experienced Honda employees find new career opportunities through intelligent questionnaires, profile management, and smart recommendations.

## 🚀 Features

- **AI-Generated Questionnaires**: Personalized questionnaires using AWS Bedrock Claude Sonnet 4
- **Smart Profile Management**: Dynamic business title generation and skill assessment
- **Intelligent Matching**: AI-powered recommendation engine for internal and external opportunities
- **Privacy Controls**: Granular visibility settings for profile sharing
- **External Platform**: Honda Veteran Bank for external recruiters
- **Role-Based Access**: Secure authentication with Cognito and RBAC

## 🏗️ Architecture

- **Backend**: Python 3.12 + AWS Lambda + Serverless Framework 4
- **Frontend**: React 18 + TypeScript + AWS Amplify
- **Database**: DynamoDB with optimized GSI design
- **AI/ML**: AWS Bedrock (Claude Sonnet 4 Cross-region inference)
- **Authentication**: AWS Cognito User Pools
- **Infrastructure**: AWS Serverless (API Gateway, S3, CloudFront)
- **CI/CD**: GitHub Actions + Serverless Framework

## 📋 Prerequisites

- Python 3.12+
- Node.js 18+
- AWS CLI configured
- Serverless Framework 4
- Git

## 🛠️ Installation

### Backend Setup

1. Clone the repository:
```bash
git clone https://github.com/leadlea/honda.git
cd honda
```

2. Install Python dependencies:
```bash
pip install -r requirements-dev.txt
```

3. Install Serverless Framework and plugins:
```bash
npm install -g serverless@4
npm install
```

4. Configure AWS credentials:
```bash
aws configure
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

## 🚀 Deployment

### Development Environment

1. Deploy backend services:
```bash
serverless deploy --stage dev
```

2. Build and deploy frontend:
```bash
cd frontend
npm run build
aws s3 sync build/ s3://honda-veteran-talent-matching-dev-frontend
```

### Production Environment

1. Deploy via GitHub Actions:
   - Push to `main` branch
   - GitHub Actions will automatically deploy to production

2. Manual deployment:
```bash
serverless deploy --stage prod
```

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/unit/ --cov=src
```

### Run Integration Tests
```bash
pytest tests/integration/
```

### Run Frontend Tests
```bash
cd frontend
npm test
```

### Code Quality Checks
```bash
# Formatting
black src/ tests/
isort src/ tests/

# Linting
flake8 src/ tests/
mypy src/

# Security
bandit -r src/
```

## 📁 Project Structure

```
honda-veteran-talent-matching/
├── .github/workflows/          # GitHub Actions CI/CD
├── .kiro/specs/               # Feature specifications
├── src/                       # Python backend source
│   ├── handlers/              # Lambda function handlers
│   ├── models/                # Data models
│   ├── services/              # Business logic
│   ├── repositories/          # Data access layer
│   └── utils/                 # Utility functions
├── tests/                     # Test files
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
├── frontend/                  # React frontend
│   ├── src/                   # Frontend source code
│   └── public/                # Static assets
├── serverless.yml             # Serverless Framework configuration
├── requirements.txt           # Python dependencies
└── package.json               # Node.js dependencies
```

## 🔧 Configuration

### Environment Variables

Create `.env` files for different environments:

```bash
# .env.dev
STAGE=dev
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# .env.prod
STAGE=prod
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### AWS Resources

The system creates the following AWS resources:
- Cognito User Pool for authentication
- DynamoDB tables for data storage
- Lambda functions for business logic
- API Gateway for REST endpoints
- S3 bucket for frontend hosting
- IAM roles and policies

## 📊 Monitoring

- **CloudWatch Logs**: Lambda function logs
- **CloudWatch Metrics**: Performance monitoring
- **X-Ray Tracing**: Distributed tracing (optional)
- **CodeCov**: Test coverage reporting

## 🔒 Security

- **Authentication**: AWS Cognito with JWT tokens
- **Authorization**: Role-based access control (RBAC)
- **Data Encryption**: At rest and in transit
- **PII Protection**: Anonymization and pseudonymization
- **Security Scanning**: Automated vulnerability checks

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Contact the Honda Development Team

## 🗺️ Roadmap

- [ ] Multi-language support (Japanese/English)
- [ ] Advanced AI analytics dashboard
- [ ] Mobile application
- [ ] Integration with external job boards
- [ ] Real-time notifications
- [ ] Video interview scheduling