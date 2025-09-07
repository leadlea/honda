#!/bin/bash
# Frontend deployment script for Honda Veteran Talent Matching
# Builds the React app and deploys it to S3/CloudFront
# - ENV を最優先して Cognito 設定を埋め込む
# - 旧 ClientId / 旧 UserPoolId が混入していたら即中断
# - ビルド成果物にも旧 ID が無いかガード

set -Eeuo pipefail

STAGE=${1:-dev}
SERVICE_NAME="honda-veteran-talent-matching"
FRONTEND_DIR="frontend"
BUILD_DIR="$FRONTEND_DIR/build"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
die(){ echo -e "${RED}❌ $*${NC}"; exit 1; }

echo -e "${GREEN}🚀 Starting frontend deployment for stage: $STAGE${NC}"

# ── Pre-checks ────────────────────────────────────────────────────────────────
command -v aws  >/dev/null 2>&1 || die "AWS CLI not found"
command -v node >/dev/null 2>&1 || die "Node.js not found"
command -v npm  >/dev/null 2>&1 || die "npm not found"

: "${REACT_APP_COGNITO_CLIENT_ID:?REACT_APP_COGNITO_CLIENT_ID is required}"
: "${REACT_APP_COGNITO_USER_POOL_ID:?REACT_APP_COGNITO_USER_POOL_ID is required}"

# 旧 ID（混入したら中断）
FORBIDDEN_CLIENT_IDS=(
  "1179cu6f4a1g8hqhavmndtf8as"   # 一番古い
  "2bggeikp7ijt5medn414pkfkmk"   # 旧
  "1f62alqbqneo30qb0giarl9dva"   # 直前まで使ってたID（今回から禁止）
)
FORBIDDEN_POOL_IDS=(
  "ap-northeast-1_wkRvKeooL"     # 旧プール
)

for bad in "${FORBIDDEN_CLIENT_IDS[@]}"; do
  [[ "$REACT_APP_COGNITO_CLIENT_ID" == "$bad" ]] && die "Forbidden ClientId specified: $bad"
done
for bad in "${FORBIDDEN_POOL_IDS[@]}"; do
  [[ "$REACT_APP_COGNITO_USER_POOL_ID" == "$bad" ]] && die "Forbidden UserPoolId specified: $bad"
done

# ── Hosting config（既存インフラ） ─────────────────────────────────────────────
echo -e "${YELLOW}📋 Using existing S3/CloudFront config...${NC}"
BUCKET_NAME="${FRONTEND_BUCKET_NAME:-honda-hr-bank}"
BUCKET_REGION="${FRONTEND_BUCKET_REGION:-ap-northeast-1}"
CLOUDFRONT_DISTRIBUTION_ID="${CLOUDFRONT_DISTRIBUTION_ID:-E1T3WQ2YHO1BNA}"
CLOUDFRONT_DOMAIN="${CLOUDFRONT_DOMAIN:-doy5alruji476.cloudfront.net}"

aws s3 ls "s3://$BUCKET_NAME" --region "$BUCKET_REGION" >/dev/null 2>&1 \
  || die "S3 bucket '$BUCKET_NAME' not found in region '$BUCKET_REGION'"

echo -e "${GREEN}✅ S3 Bucket: $BUCKET_NAME${NC}"
echo -e "${GREEN}✅ CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID${NC}"
echo -e "${GREEN}✅ CloudFront Domain: $CLOUDFRONT_DOMAIN${NC}"

# ── Backend endpoint ──────────────────────────────────────────────────────────
echo -e "${YELLOW}📋 Resolving API Gateway URL...${NC}"
API_URL="${REACT_APP_API_URL:-}"
if [ -z "$API_URL" ]; then
  API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$SERVICE_NAME-$STAGE" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
    --output text 2>/dev/null || echo "")
fi
if [ -z "$API_URL" ] || [ "$API_URL" = "None" ]; then
  API_URL="https://api-placeholder.execute-api.ap-northeast-1.amazonaws.com"
  echo -e "${YELLOW}⚠️  API Gateway URL not found. Using placeholder: $API_URL${NC}"
else
  echo -e "${GREEN}✅ API URL: $API_URL${NC}"
fi

# ── .env.production を生成（ENV 最優先） ───────────────────────────────────────
echo -e "${YELLOW}📝 Creating $FRONTEND_DIR/.env.production...${NC}"
cat > "$FRONTEND_DIR/.env.production" << EOF
REACT_APP_API_URL=$API_URL
REACT_APP_COGNITO_USER_POOL_ID=$REACT_APP_COGNITO_USER_POOL_ID
REACT_APP_COGNITO_CLIENT_ID=$REACT_APP_COGNITO_CLIENT_ID
REACT_APP_REGION=${REACT_APP_REGION:-ap-northeast-1}
REACT_APP_STAGE=$STAGE
GENERATE_SOURCEMAP=false
EOF
echo -e "${GREEN}✅ .env.production created${NC}"

# ── Build ────────────────────────────────────────────────────────────────────
cd "$FRONTEND_DIR"
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
npm ci --production=false

echo -e "${YELLOW}🏗️  Building React app...${NC}"
npm run build
[ -d "build" ] || die "Build failed (build dir missing)"
echo -e "${GREEN}✅ Build succeeded${NC}"

# ビルド成果物に旧 ID が混入していないか確認
if rg -n "1179cu6f4a1g8hqhavmndtf8as|2bggeikp7ijt5medn414pkfkmk|1f62alqbqneo30qb0giarl9dva|ap-northeast-1_wkRvKeooL" -S build >/dev/null 2>&1; then
  die "❌ Forbidden Cognito ID found inside build artifacts"
fi
cd ..

# ── Optional: S3/CloudFront 設定補正 ───────────────────────────────────────────
chmod +x scripts/fix-cloudfront-s3.sh 2>/dev/null || true
./scripts/fix-cloudfront-s3.sh 2>/dev/null || echo -e "${YELLOW}⚠️  Skipped/failed config fix, continue${NC}"

# ── Upload to S3 ─────────────────────────────────────────────────────────────
echo -e "${YELLOW}☁️  Uploading static assets to S3...${NC}"
aws s3 sync "$BUILD_DIR" "s3://$BUCKET_NAME" \
  --region "$BUCKET_REGION" --delete \
  --cache-control "public, max-age=31536000" \
  --exclude "*.html" --exclude "service-worker.js" --exclude "manifest.json"

echo -e "${YELLOW}☁️  Uploading HTML/manifest with no-cache...${NC}"
aws s3 sync "$BUILD_DIR" "s3://$BUCKET_NAME" \
  --region "$BUCKET_REGION" --delete \
  --cache-control "no-cache, no-store, must-revalidate" \
  --include "*.html" --include "service-worker.js" --include "manifest.json"

aws s3 cp "s3://$BUCKET_NAME/index.html" "s3://$BUCKET_NAME/index.html" \
  --region "$BUCKET_REGION" --metadata-directive REPLACE \
  --content-type "text/html" \
  --cache-control "no-cache, no-store, must-revalidate" || true

echo -e "${GREEN}✅ S3 upload complete${NC}"

# ── CloudFront invalidation ──────────────────────────────────────────────────
echo -e "${YELLOW}🔄 Creating CloudFront invalidation...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' --output text 2>/dev/null || echo "")
[ -n "$INVALIDATION_ID" ] \
  && echo -e "${GREEN}✅ Invalidation: $INVALIDATION_ID${NC}" \
  || echo -e "${YELLOW}⚠️  Could not create invalidation${NC}"

WEBSITE_URL="https://$CLOUDFRONT_DOMAIN"
echo -e "${GREEN}🌐 Website URL: $WEBSITE_URL${NC}"

echo -e "${YELLOW}📋 Summary:${NC}"
echo -e "  Stage:               $STAGE"
echo -e "  API URL:             $API_URL"
echo -e "  UserPoolId:          $REACT_APP_COGNITO_USER_POOL_ID"
echo -e "  ClientId:            $REACT_APP_COGNITO_CLIENT_ID"
echo -e "  S3 Bucket:           $BUCKET_NAME / $BUCKET_REGION"
echo -e "  CloudFront:          $CLOUDFRONT_DISTRIBUTION_ID"
[ -n "$INVALIDATION_ID" ] && echo -e "  Invalidation:        $INVALIDATION_ID"
