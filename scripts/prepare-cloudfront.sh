#!/bin/bash

# CloudFront preparation script for Honda Veteran Talent Matching
# This script prepares the configuration for CloudFront distribution

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

echo -e "${GREEN}☁️  Preparing CloudFront configuration for stage: $STAGE${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Use existing S3 bucket configuration
echo -e "${YELLOW}📋 Getting S3 bucket information...${NC}"
BUCKET_NAME="${FRONTEND_BUCKET_NAME:-honda-hr-bank}"
BUCKET_REGION="${FRONTEND_BUCKET_REGION:-ap-northeast-1}"

# Verify bucket exists
if ! aws s3 ls "s3://$BUCKET_NAME" --region "$BUCKET_REGION" >/dev/null 2>&1; then
    echo -e "${RED}❌ S3 bucket '$BUCKET_NAME' not found in region '$BUCKET_REGION'.${NC}"
    echo -e "${YELLOW}Please verify the bucket name and region are correct.${NC}"
    exit 1
fi

# Construct S3 website URL
BUCKET_URL="http://$BUCKET_NAME.s3-website-$BUCKET_REGION.amazonaws.com"

# Try to get API Gateway URL from CloudFormation, use placeholder if not found
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$SERVICE_NAME-$STAGE" \
    --region "$BUCKET_REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
    --output text 2>/dev/null || echo "https://api-placeholder.execute-api.$BUCKET_REGION.amazonaws.com")

echo -e "${GREEN}✅ Found S3 bucket: $BUCKET_NAME${NC}"
echo -e "${GREEN}✅ S3 website URL: $BUCKET_URL${NC}"
echo -e "${GREEN}✅ API Gateway URL: $API_URL${NC}"

# Create CloudFront distribution configuration
echo -e "${YELLOW}📝 Creating CloudFront distribution configuration...${NC}"

# Extract domain from S3 website URL
S3_DOMAIN="$BUCKET_NAME.s3-website-$BUCKET_REGION.amazonaws.com"

cat > "cloudfront-config-$STAGE.json" << EOF
{
  "CallerReference": "$SERVICE_NAME-$STAGE-$(date +%s)",
  "Comment": "CloudFront distribution for Honda Veteran Talent Matching - $STAGE",
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3-$BUCKET_NAME",
        "DomainName": "$S3_DOMAIN",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only",
          "OriginSslProtocols": {
            "Quantity": 1,
            "Items": ["TLSv1.2"]
          }
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-$BUCKET_NAME",
    "ViewerProtocolPolicy": "redirect-to-https",
    "TrustedSigners": {
      "Enabled": false,
      "Quantity": 0
    },
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {
        "Forward": "none"
      }
    },
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000,
    "Compress": true
  },
  "CacheBehaviors": {
    "Quantity": 2,
    "Items": [
      {
        "PathPattern": "/static/*",
        "TargetOriginId": "S3-$BUCKET_NAME",
        "ViewerProtocolPolicy": "redirect-to-https",
        "TrustedSigners": {
          "Enabled": false,
          "Quantity": 0
        },
        "ForwardedValues": {
          "QueryString": false,
          "Cookies": {
            "Forward": "none"
          }
        },
        "MinTTL": 31536000,
        "DefaultTTL": 31536000,
        "MaxTTL": 31536000,
        "Compress": true
      },
      {
        "PathPattern": "*.html",
        "TargetOriginId": "S3-$BUCKET_NAME",
        "ViewerProtocolPolicy": "redirect-to-https",
        "TrustedSigners": {
          "Enabled": false,
          "Quantity": 0
        },
        "ForwardedValues": {
          "QueryString": false,
          "Cookies": {
            "Forward": "none"
          }
        },
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 0,
        "Compress": true
      }
    ]
  },
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      {
        "ErrorCode": 403,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      },
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      }
    ]
  },
  "Enabled": true,
  "PriceClass": "PriceClass_100"
}
EOF

echo -e "${GREEN}✅ CloudFront configuration created: cloudfront-config-$STAGE.json${NC}"

# Create deployment instructions
cat > "CLOUDFRONT_DEPLOYMENT_INSTRUCTIONS.md" << EOF
# CloudFront Deployment Instructions

## Overview
This document provides instructions for manually setting up CloudFront distribution for the Honda Veteran Talent Matching frontend.

## Prerequisites
- S3 bucket deployed and configured: \`$BUCKET_NAME\`
- Frontend files uploaded to S3
- AWS CLI configured with appropriate permissions

## Step 1: Create CloudFront Distribution

Run the following command to create the CloudFront distribution:

\`\`\`bash
aws cloudfront create-distribution --distribution-config file://cloudfront-config-$STAGE.json
\`\`\`

## Step 2: Get Distribution Information

After creation, get the distribution details:

\`\`\`bash
# List distributions to find your distribution ID
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='CloudFront distribution for Honda Veteran Talent Matching - $STAGE'].{Id:Id,DomainName:DomainName,Status:Status}"

# Get specific distribution details (replace DISTRIBUTION_ID with actual ID)
aws cloudfront get-distribution --id DISTRIBUTION_ID
\`\`\`

## Step 3: Update DNS (Optional)

If you have a custom domain, create a CNAME record pointing to the CloudFront domain name.

## Step 4: Invalidate Cache (When Updating)

When you deploy new frontend code, invalidate the CloudFront cache:

\`\`\`bash
# Replace DISTRIBUTION_ID with your actual distribution ID
aws cloudfront create-invalidation --distribution-id DISTRIBUTION_ID --paths "/*"
\`\`\`

## Configuration Details

- **S3 Bucket**: $BUCKET_NAME
- **S3 Website URL**: $BUCKET_URL
- **API Gateway URL**: $API_URL
- **Stage**: $STAGE

## Cache Behaviors

1. **Static Assets** (\`/static/*\`): Long-term caching (1 year)
2. **HTML Files** (\`*.html\`): No caching for dynamic updates
3. **Default**: Medium-term caching (1 day)

## Error Handling

- 403/404 errors redirect to \`index.html\` for SPA routing
- Error responses cached for 5 minutes

## Security

- HTTPS redirect enforced
- Compression enabled for better performance

## Monitoring

Monitor your CloudFront distribution through:
- AWS CloudWatch metrics
- CloudFront access logs (if enabled)
- Real User Monitoring (RUM) if configured

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Check S3 bucket policy and public access settings
2. **Slow Updates**: CloudFront cache may need invalidation
3. **CORS Issues**: Ensure API Gateway CORS is properly configured

### Useful Commands

\`\`\`bash
# Check distribution status
aws cloudfront get-distribution --id DISTRIBUTION_ID --query "Distribution.Status"

# List recent invalidations
aws cloudfront list-invalidations --distribution-id DISTRIBUTION_ID

# Get distribution configuration
aws cloudfront get-distribution-config --id DISTRIBUTION_ID
\`\`\`
EOF

echo -e "${GREEN}✅ CloudFront deployment instructions created: CLOUDFRONT_DEPLOYMENT_INSTRUCTIONS.md${NC}"

echo -e "${BLUE}📋 Next Steps:${NC}"
echo -e "1. Review the generated CloudFront configuration: ${YELLOW}cloudfront-config-$STAGE.json${NC}"
echo -e "2. Follow the instructions in: ${YELLOW}CLOUDFRONT_DEPLOYMENT_INSTRUCTIONS.md${NC}"
echo -e "3. Create the CloudFront distribution using AWS CLI"
echo -e "4. Update your DNS if using a custom domain"

echo -e "${GREEN}🎉 CloudFront preparation completed!${NC}"