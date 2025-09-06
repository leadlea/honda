#!/bin/bash

# Frontend deployment script for Honda Veteran Talent Matching
# This script builds the React app and deploys it to S3

set -e

# Configuration
STAGE=${1:-dev}
SERVICE_NAME="honda-veteran-talent-matching"
FRONTEND_DIR="frontend"
BUILD_DIR="$FRONTEND_DIR/build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting frontend deployment for stage: $STAGE${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is not installed. Please install it first.${NC}"
    exit 1
fi

# Use manually created S3 bucket
echo -e "${YELLOW}📋 Using manually created S3 bucket...${NC}"
BUCKET_NAME="${FRONTEND_BUCKET_NAME:-honda-veteran-talent-matching-$STAGE-frontend}"
BUCKET_REGION="${FRONTEND_BUCKET_REGION:-ap-northeast-1}"

# Verify bucket exists
if ! aws s3 ls "s3://$BUCKET_NAME" --region "$BUCKET_REGION" >/dev/null 2>&1; then
    echo -e "${RED}❌ S3 bucket '$BUCKET_NAME' not found in region '$BUCKET_REGION'.${NC}"
    echo -e "${YELLOW}Please create the bucket manually:${NC}"
    echo -e "   aws s3 mb s3://$BUCKET_NAME --region $BUCKET_REGION"
    echo -e "   aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document error.html"
    exit 1
fi

echo -e "${GREEN}✅ Found S3 bucket: $BUCKET_NAME${NC}"

# Get API Gateway URL
echo -e "${YELLOW}📋 Getting API Gateway URL...${NC}"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$SERVICE_NAME-$STAGE" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
    --output text 2>/dev/null || echo "")

if [ -z "$API_URL" ]; then
    echo -e "${RED}❌ Could not find API Gateway URL.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found API Gateway URL: $API_URL${NC}"

# Get Cognito configuration
echo -e "${YELLOW}📋 Getting Cognito configuration...${NC}"
USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name "$SERVICE_NAME-$STAGE" \
    --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolId'].OutputValue" \
    --output text 2>/dev/null || echo "")

CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$SERVICE_NAME-$STAGE" \
    --query "Stacks[0].Outputs[?OutputKey=='CognitoClientId'].OutputValue" \
    --output text 2>/dev/null || echo "")

if [ -z "$USER_POOL_ID" ] || [ -z "$CLIENT_ID" ]; then
    echo -e "${RED}❌ Could not find Cognito configuration.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found Cognito User Pool ID: $USER_POOL_ID${NC}"
echo -e "${GREEN}✅ Found Cognito Client ID: $CLIENT_ID${NC}"

# Create environment configuration file
echo -e "${YELLOW}📝 Creating environment configuration...${NC}"
cat > "$FRONTEND_DIR/.env.production" << EOF
# Auto-generated environment configuration for $STAGE
REACT_APP_API_URL=$API_URL
REACT_APP_COGNITO_USER_POOL_ID=$USER_POOL_ID
REACT_APP_COGNITO_CLIENT_ID=$CLIENT_ID
REACT_APP_REGION=us-west-2
REACT_APP_STAGE=$STAGE
GENERATE_SOURCEMAP=false
EOF

echo -e "${GREEN}✅ Environment configuration created${NC}"

# Navigate to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
npm ci --production=false

# Run type checking
echo -e "${YELLOW}🔍 Running type checking...${NC}"
npm run type-check

# Build the application
echo -e "${YELLOW}🏗️  Building React application...${NC}"
npm run build

# Check if build was successful
if [ ! -d "build" ]; then
    echo -e "${RED}❌ Build failed - build directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build completed successfully${NC}"

# Navigate back to root
cd ..

# Sync build files to S3
echo -e "${YELLOW}☁️  Uploading files to S3...${NC}"
aws s3 sync "$BUILD_DIR" "s3://$BUCKET_NAME" \
    --region "$BUCKET_REGION" \
    --delete \
    --cache-control "public, max-age=31536000" \
    --exclude "*.html" \
    --exclude "service-worker.js" \
    --exclude "manifest.json"

# Upload HTML files with no-cache
aws s3 sync "$BUILD_DIR" "s3://$BUCKET_NAME" \
    --region "$BUCKET_REGION" \
    --delete \
    --cache-control "no-cache, no-store, must-revalidate" \
    --include "*.html" \
    --include "service-worker.js" \
    --include "manifest.json"

# Set proper content types
aws s3 cp "s3://$BUCKET_NAME/index.html" "s3://$BUCKET_NAME/index.html" \
    --region "$BUCKET_REGION" \
    --metadata-directive REPLACE \
    --content-type "text/html" \
    --cache-control "no-cache, no-store, must-revalidate"

echo -e "${GREEN}✅ Files uploaded to S3 successfully${NC}"

# Get the website URL
WEBSITE_URL=$(aws s3api get-bucket-website --bucket "$BUCKET_NAME" --query 'WebsiteConfiguration.IndexDocument.Suffix' --output text 2>/dev/null || echo "")

if [ "$WEBSITE_URL" != "None" ] && [ -n "$WEBSITE_URL" ]; then
    WEBSITE_URL="http://$BUCKET_NAME.s3-website-$BUCKET_REGION.amazonaws.com"
    echo -e "${GREEN}🌐 Website URL: $WEBSITE_URL${NC}"
else
    echo -e "${YELLOW}⚠️  Website hosting not configured. You may need to set up CloudFront manually.${NC}"
fi

echo -e "${GREEN}🎉 Frontend deployment completed successfully!${NC}"
echo -e "${YELLOW}📋 Deployment Summary:${NC}"
echo -e "   Stage: $STAGE"
echo -e "   S3 Bucket: $BUCKET_NAME"
echo -e "   API URL: $API_URL"
echo -e "   Cognito User Pool: $USER_POOL_ID"
echo -e "   Cognito Client: $CLIENT_ID"
if [ -n "$WEBSITE_URL" ]; then
    echo -e "   Website URL: $WEBSITE_URL"
fi