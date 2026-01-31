#!/bin/bash

# Lambda Layer cleanup script
# This script removes old Lambda layer versions to free up storage space

set -e

# Configuration
REGION="ap-northeast-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧹 Starting Lambda Layer cleanup${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Get all Lambda layers
echo -e "${YELLOW}📋 Getting Lambda layers...${NC}"
LAYERS=$(aws lambda list-layers \
    --region "$REGION" \
    --query "Layers[].LayerName" \
    --output text)

if [ -z "$LAYERS" ]; then
    echo -e "${YELLOW}⚠️  No Lambda layers found${NC}"
    exit 0
fi

echo -e "${GREEN}✅ Found Lambda layers:${NC}"
echo "$LAYERS" | tr '\t' '\n'

TOTAL_DELETED=0

# Cleanup old versions for each layer
for LAYER_NAME in $LAYERS; do
    echo -e "${YELLOW}🔍 Processing layer: $LAYER_NAME${NC}"
    
    # Get all versions
    VERSIONS=$(aws lambda list-layer-versions \
        --region "$REGION" \
        --layer-name "$LAYER_NAME" \
        --query "LayerVersions[].Version" \
        --output text)
    
    if [ -z "$VERSIONS" ]; then
        echo -e "${GREEN}✅ No versions found for $LAYER_NAME${NC}"
        continue
    fi
    
    # Convert to array and keep only the latest 2 versions
    VERSION_ARRAY=($VERSIONS)
    TOTAL_VERSIONS=${#VERSION_ARRAY[@]}
    
    if [ $TOTAL_VERSIONS -le 2 ]; then
        echo -e "${GREEN}✅ Only $TOTAL_VERSIONS versions found for $LAYER_NAME, keeping all${NC}"
        continue
    fi
    
    # Sort versions numerically and delete all but the latest 2
    SORTED_VERSIONS=($(printf '%s\n' "${VERSION_ARRAY[@]}" | sort -n))
    VERSIONS_TO_DELETE=${SORTED_VERSIONS[@]:0:$((TOTAL_VERSIONS-2))}
    
    echo -e "${YELLOW}🗑️  Deleting old versions for $LAYER_NAME: $VERSIONS_TO_DELETE${NC}"
    
    for VERSION in $VERSIONS_TO_DELETE; do
        echo -e "${YELLOW}   Deleting version $VERSION...${NC}"
        if aws lambda delete-layer-version \
            --region "$REGION" \
            --layer-name "$LAYER_NAME" \
            --version-number "$VERSION" 2>/dev/null; then
            TOTAL_DELETED=$((TOTAL_DELETED + 1))
        else
            echo -e "${RED}   Failed to delete version $VERSION${NC}"
        fi
    done
    
    echo -e "${GREEN}✅ Cleanup completed for $LAYER_NAME${NC}"
done

echo -e "${GREEN}🎉 Deleted $TOTAL_DELETED Lambda layer versions!${NC}"

# Check current account storage usage
echo -e "${YELLOW}📊 Checking current Lambda storage usage...${NC}"
aws lambda get-account-settings \
    --region "$REGION" \
    --query "AccountUsage" \
    --output table

echo -e "${GREEN}✅ Lambda layer cleanup completed!${NC}"
