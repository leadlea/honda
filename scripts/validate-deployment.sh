#!/bin/bash

# Deployment validation script for Honda Veteran Talent Matching
# This script validates that the deployment is working correctly

set -e

# Configuration
STAGE=${1:-dev}
SERVICE_NAME="honda-veteran-talent-matching"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Validating deployment for stage: $STAGE${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Function to check if a resource exists
check_resource() {
    local resource_type=$1
    local resource_name=$2
    local check_command=$3
    
    echo -e "${YELLOW}📋 Checking $resource_type: $resource_name${NC}"
    
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $resource_type exists: $resource_name${NC}"
        return 0
    else
        echo -e "${RED}❌ $resource_type not found: $resource_name${NC}"
        return 1
    fi
}

# Function to test API endpoint
test_endpoint() {
    local endpoint=$1
    local expected_status=${2:-200}
    
    echo -e "${YELLOW}🌐 Testing endpoint: $endpoint${NC}"
    
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$endpoint" || echo "000")
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ Endpoint responding: $endpoint (Status: $status_code)${NC}"
        return 0
    else
        echo -e "${RED}❌ Endpoint failed: $endpoint (Status: $status_code, Expected: $expected_status)${NC}"
        return 1
    fi
}

# Initialize counters
TOTAL_CHECKS=0
PASSED_CHECKS=0

# Check CloudFormation stack
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if check_resource "CloudFormation Stack" "$SERVICE_NAME-$STAGE" \
   "aws cloudformation describe-stacks --stack-name '$SERVICE_NAME-$STAGE'"; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi

# Get stack outputs
echo -e "${YELLOW}📋 Getting stack outputs...${NC}"
STACK_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$SERVICE_NAME-$STAGE" \
    --query "Stacks[0].Outputs" \
    --output json 2>/dev/null || echo "[]")

# Extract key values
API_URL=$(echo "$STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="ApiGatewayUrl") | .OutputValue' 2>/dev/null || echo "")
BUCKET_NAME=$(echo "$STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="FrontendBucketName") | .OutputValue' 2>/dev/null || echo "")
USER_POOL_ID=$(echo "$STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="CognitoUserPoolId") | .OutputValue' 2>/dev/null || echo "")
CLIENT_ID=$(echo "$STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="CognitoClientId") | .OutputValue' 2>/dev/null || echo "")

# Check DynamoDB tables
TABLES=(
    "users"
    "veteran-profiles"
    "opportunities"
    "recommendations"
    "questionnaires"
    "questionnaire-responses"
    "applications"
    "public-profiles"
    "contact-requests"
)

for table in "${TABLES[@]}"; do
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if check_resource "DynamoDB Table" "$SERVICE_NAME-$STAGE-$table" \
       "aws dynamodb describe-table --table-name '$SERVICE_NAME-$STAGE-$table'"; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
done

# Check Lambda functions
FUNCTIONS=(
    "authHandler"
    "profileHandler"
    "businessTitleHandler"
    "questionnaireHandler"
    "matchingHandler"
    "applicationHandler"
    "publicSearchHandler"
    "contactHandler"
)

for function in "${FUNCTIONS[@]}"; do
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if check_resource "Lambda Function" "$SERVICE_NAME-$STAGE-$function" \
       "aws lambda get-function --function-name '$SERVICE_NAME-$STAGE-$function'"; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
done

# Check Cognito User Pool
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -n "$USER_POOL_ID" ] && check_resource "Cognito User Pool" "$USER_POOL_ID" \
   "aws cognito-idp describe-user-pool --user-pool-id '$USER_POOL_ID'"; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi

# Check S3 bucket
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -n "$BUCKET_NAME" ] && check_resource "S3 Bucket" "$BUCKET_NAME" \
   "aws s3api head-bucket --bucket '$BUCKET_NAME'"; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi

# Test API endpoints if API URL is available
if [ -n "$API_URL" ]; then
    echo -e "${BLUE}🌐 Testing API endpoints...${NC}"
    
    # Test public endpoints (no auth required)
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if test_endpoint "$API_URL/public/categories"; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if test_endpoint "$API_URL/public/veterans/search"; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
    
    # Test authenticated endpoints (expect 401 without auth)
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if test_endpoint "$API_URL/auth/profile" "401"; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  API URL not found, skipping endpoint tests${NC}"
fi

# Check frontend deployment
if [ -n "$BUCKET_NAME" ]; then
    echo -e "${BLUE}🌐 Checking frontend deployment...${NC}"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if aws s3api head-object --bucket "$BUCKET_NAME" --key "index.html" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend deployed: index.html found in S3${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${RED}❌ Frontend not deployed: index.html not found in S3${NC}"
    fi
    
    # Test S3 website endpoint if configured
    WEBSITE_URL="http://$BUCKET_NAME.s3-website-us-west-2.amazonaws.com"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if test_endpoint "$WEBSITE_URL"; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  S3 bucket not found, skipping frontend tests${NC}"
fi

# Summary
echo -e "\n${BLUE}📊 Validation Summary${NC}"
echo -e "===================="
echo -e "Total checks: $TOTAL_CHECKS"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed: ${RED}$((TOTAL_CHECKS - PASSED_CHECKS))${NC}"

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    echo -e "\n${GREEN}🎉 All validation checks passed! Deployment is healthy.${NC}"
    
    echo -e "\n${BLUE}📋 Deployment Information${NC}"
    echo -e "========================="
    [ -n "$API_URL" ] && echo -e "API Gateway URL: $API_URL"
    [ -n "$BUCKET_NAME" ] && echo -e "S3 Bucket: $BUCKET_NAME"
    [ -n "$USER_POOL_ID" ] && echo -e "Cognito User Pool: $USER_POOL_ID"
    [ -n "$CLIENT_ID" ] && echo -e "Cognito Client: $CLIENT_ID"
    [ -n "$WEBSITE_URL" ] && echo -e "Website URL: $WEBSITE_URL"
    
    exit 0
else
    echo -e "\n${RED}❌ Some validation checks failed. Please review the deployment.${NC}"
    
    echo -e "\n${YELLOW}🔧 Troubleshooting Tips${NC}"
    echo -e "======================"
    echo -e "1. Check CloudFormation stack events for errors"
    echo -e "2. Verify AWS permissions and service limits"
    echo -e "3. Review Lambda function logs in CloudWatch"
    echo -e "4. Ensure all required environment variables are set"
    echo -e "5. Check API Gateway configuration and CORS settings"
    
    exit 1
fi