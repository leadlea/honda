#!/bin/bash

# CloudFront + S3 access fix script
# This script fixes common CloudFront and S3 access issues

set -e

# Configuration
BUCKET_NAME="honda-hr-bank"
BUCKET_REGION="ap-northeast-1"
CLOUDFRONT_DISTRIBUTION_ID="E1T3WQ2YHO1BNA"
ACCOUNT_ID="982534361827"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Fixing CloudFront + S3 access configuration${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# 1. Update S3 bucket policy to allow both CloudFront and direct access for deployment
echo -e "${YELLOW}📋 Updating S3 bucket policy...${NC}"
cat > /tmp/s3-bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Id": "S3-Console-Auto-Gen-Policy-1757146447799",
  "Statement": [
    {
      "Sid": "S3PolicyStmt-DO-NOT-MODIFY-1757146447674",
      "Effect": "Allow",
      "Principal": {
        "Service": "logging.s3.amazonaws.com"
      },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "${ACCOUNT_ID}"
        }
      }
    },
    {
      "Sid": "AllowSSLRequestsOnly",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}",
        "arn:aws:s3:::${BUCKET_NAME}/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    },
    {
      "Sid": "AllowCloudFrontServicePrincipal",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "ArnLike": {
          "AWS:SourceArn": "arn:aws:cloudfront::${ACCOUNT_ID}:distribution/${CLOUDFRONT_DISTRIBUTION_ID}"
        }
      }
    },
    {
      "Sid": "AllowDeploymentAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${ACCOUNT_ID}:root"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}",
        "arn:aws:s3:::${BUCKET_NAME}/*"
      ]
    }
  ]
}
EOF

# Apply the bucket policy
aws s3api put-bucket-policy \
    --bucket "$BUCKET_NAME" \
    --region "$BUCKET_REGION" \
    --policy file:///tmp/s3-bucket-policy.json

echo -e "${GREEN}✅ S3 bucket policy updated${NC}"

# 2. Check CloudFront distribution configuration
echo -e "${YELLOW}📋 Checking CloudFront distribution...${NC}"
DISTRIBUTION_STATUS=$(aws cloudfront get-distribution \
    --id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --query "Distribution.Status" \
    --output text)

echo -e "${GREEN}✅ CloudFront distribution status: $DISTRIBUTION_STATUS${NC}"

# 3. Create invalidation to clear cache
echo -e "${YELLOW}🔄 Creating CloudFront invalidation...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)

if [ -n "$INVALIDATION_ID" ]; then
    echo -e "${GREEN}✅ CloudFront invalidation created: $INVALIDATION_ID${NC}"
else
    echo -e "${YELLOW}⚠️  Could not create CloudFront invalidation${NC}"
fi

# 4. Test S3 bucket access
echo -e "${YELLOW}🧪 Testing S3 bucket access...${NC}"
if aws s3 ls "s3://$BUCKET_NAME" --region "$BUCKET_REGION" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ S3 bucket access successful${NC}"
else
    echo -e "${RED}❌ S3 bucket access failed${NC}"
fi

# 5. Upload a test index.html if it doesn't exist
echo -e "${YELLOW}📄 Checking for index.html...${NC}"
if ! aws s3 ls "s3://$BUCKET_NAME/index.html" --region "$BUCKET_REGION" >/dev/null 2>&1; then
    echo -e "${YELLOW}📝 Creating default index.html...${NC}"
    cat > /tmp/index.html << 'EOF'
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Honda ベテラン人材マッチングシステム</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            background: white;
            padding: 3rem;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            max-width: 600px;
        }
        h1 {
            color: #333;
            margin-bottom: 1rem;
            font-size: 2.5rem;
        }
        p {
            color: #666;
            font-size: 1.2rem;
            line-height: 1.6;
            margin-bottom: 2rem;
        }
        .status {
            background: #e8f5e8;
            color: #2e7d32;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            font-weight: bold;
        }
        .info {
            background: #f3e5f5;
            color: #7b1fa2;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Honda ベテラン人材マッチングシステム</h1>
        <div class="status">
            ✅ システムは正常に稼働しています
        </div>
        <p>
            AI を活用したベテラン人材マッチングシステムへようこそ。<br>
            経験豊富な Honda 社員の新しいキャリア機会をサポートします。
        </p>
        <div class="info">
            <strong>🌏 デプロイメント情報</strong><br>
            リージョン: 東京 (ap-northeast-1)<br>
            CDN: CloudFront<br>
            ストレージ: Amazon S3
        </div>
        <p>
            <small>システムの詳細については、開発チームにお問い合わせください。</small>
        </p>
    </div>
</body>
</html>
EOF

    aws s3 cp /tmp/index.html "s3://$BUCKET_NAME/index.html" \
        --region "$BUCKET_REGION" \
        --content-type "text/html" \
        --cache-control "no-cache, no-store, must-revalidate"
    
    echo -e "${GREEN}✅ Default index.html uploaded${NC}"
else
    echo -e "${GREEN}✅ index.html already exists${NC}"
fi

# Cleanup temp files
rm -f /tmp/s3-bucket-policy.json /tmp/index.html

echo -e "${GREEN}🎉 CloudFront + S3 configuration fix completed!${NC}"
echo -e "${YELLOW}📋 Summary:${NC}"
echo -e "   S3 Bucket: $BUCKET_NAME"
echo -e "   CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID"
echo -e "   CloudFront URL: https://doy5alruji476.cloudfront.net"
echo -e "   Status: $DISTRIBUTION_STATUS"
if [ -n "$INVALIDATION_ID" ]; then
    echo -e "   Invalidation: $INVALIDATION_ID"
fi
echo -e "${YELLOW}⏳ Changes may take 5-15 minutes to propagate${NC}"