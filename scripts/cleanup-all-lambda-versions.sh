#!/bin/bash

# Cleanup ALL Lambda function versions across all projects

set -e

REGION="ap-northeast-1"

echo "🧹 Starting cleanup of ALL Lambda function versions..."

# Get all Lambda functions
FUNCTIONS=$(aws lambda list-functions \
    --region "$REGION" \
    --query "Functions[].FunctionName" \
    --output text)

TOTAL_DELETED=0

for FUNCTION_NAME in $FUNCTIONS; do
    echo "🔍 Processing: $FUNCTION_NAME"
    
    # Get all versions except $LATEST
    VERSIONS=$(aws lambda list-versions-by-function \
        --region "$REGION" \
        --function-name "$FUNCTION_NAME" \
        --query "Versions[?Version != '\$LATEST'].Version" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$VERSIONS" ]; then
        continue
    fi
    
    # Delete ALL old versions
    for VERSION in $VERSIONS; do
        if aws lambda delete-function \
            --region "$REGION" \
            --function-name "$FUNCTION_NAME" \
            --qualifier "$VERSION" 2>/dev/null; then
            TOTAL_DELETED=$((TOTAL_DELETED + 1))
            echo "   ✅ Deleted version $VERSION"
        fi
    done
done

echo "🎉 Deleted $TOTAL_DELETED Lambda versions!"

# Check storage
aws lambda get-account-settings \
    --region "$REGION" \
    --query "AccountUsage" \
    --output table

echo "✅ Cleanup completed!"
