#!/bin/bash

# Lambda version cleanup script
# This script removes old Lambda function versions to free up storage space

set -e

# Configuration
REGION="ap-northeast-1"
SERVICE_NAME="honda-veteran-talent-matching"
STAGE="prod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧹 Starting Lambda version cleanup for ${SERVICE_NAME}-${STAGE}${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Get all Lambda functions for this service
echo -e "${YELLOW}📋 Getting Lambda functions...${NC}"
FUNCTIONS=$(aws lambda list-functions \
    --region "$REGION" \
    --query "Functions[?starts_with(FunctionName, '${SERVICE_NAME}-${STAGE}')].FunctionName" \
    --output text)

if [ -z "$FUNCTIONS" ]; then
    echo -e "${YELLOW}⚠️  No Lambda functions found for ${SERVICE_NAME}-${STAGE}${NC}"
    exit 0
fi

echo -e "${GREEN}✅ Found Lambda functions:${NC}"
echo "$FUNCTIONS" | tr '\t' '\n'

# Cleanup old versions for each function
for FUNCTION_NAME in $FUNCTIONS; do
    echo -e "${YELLOW}🔍 Processing function: $FUNCTION_NAME${NC}"
    
    # Get all versions except $LATEST
    VERSIONS=$(aws lambda list-versions-by-function \
        --region "$REGION" \
        --function-name "$FUNCTION_NAME" \
        --query "Versions[?Version != '\$LATEST'].Version" \
        --output text)
    
    if [ -z "$VERSIONS" ]; then
        echo -e "${GREEN}✅ No old versions found for $FUNCTION_NAME${NC}"
        continue
    fi
    
    # Convert to array and keep only the latest 3 versions
    VERSION_ARRAY=($VERSIONS)
    TOTAL_VERSIONS=${#VERSION_ARRAY[@]}
    
    if [ $TOTAL_VERSIONS -le 3 ]; then
        echo -e "${GREEN}✅ Only $TOTAL_VERSIONS versions found for $FUNCTION_NAME, keeping all${NC}"
        continue
    fi
    
    # Sort versions numerically and delete all but the latest 3
    SORTED_VERSIONS=($(printf '%s\n' "${VERSION_ARRAY[@]}" | sort -n))
    VERSIONS_TO_DELETE=${SORTED_VERSIONS[@]:0:$((TOTAL_VERSIONS-3))}
    
    echo -e "${YELLOW}🗑️  Deleting old versions for $FUNCTION_NAME: $VERSIONS_TO_DELETE${NC}"
    
    for VERSION in $VERSIONS_TO_DELETE; do
        echo -e "${YELLOW}   Deleting version $VERSION...${NC}"
        aws lambda delete-function \
            --region "$REGION" \
            --function-name "$FUNCTION_NAME" \
            --qualifier "$VERSION" || echo -e "${RED}   Failed to delete version $VERSION${NC}"
    done
    
    echo -e "${GREEN}✅ Cleanup completed for $FUNCTION_NAME${NC}"
done

# Check current account storage usage
echo -e "${YELLOW}📊 Checking current Lambda storage usage...${NC}"
aws lambda get-account-settings \
    --region "$REGION" \
    --query "AccountUsage" \
    --output table

echo -e "${GREEN}🎉 Lambda version cleanup completed!${NC}"
echo -e "${YELLOW}💡 Tip: Consider setting up automatic version cleanup in your deployment pipeline${NC}"