#!/usr/bin/env bash
# Frontend deployment script for Honda Veteran Talent Matching
# - ENV最優先で .env.production を生成
# - 静的アセットは 1年 + immutable、HTML/manifest/asset-manifest/SW は no-cache
# - 古い ClientId / 古い UserPoolId の混入をビルド後に検知して安全停止
# - CloudFront 全無効化

set -Eeuo pipefail

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────
STAGE=${1:-dev}
SERVICE_NAME="honda-veteran-talent-matching"
FRONTEND_DIR="frontend"
BUILD_DIR="$FRONTEND_DIR/build"

# デフォルト値（ENVで上書き可能）
BUCKET_NAME="${FRONTEND_BUCKET_NAME:-honda-hr-bank}"
BUCKET_REGION="${FRONTEND_BUCKET_REGION:-ap-northeast-1}"
CLOUDFRONT_DISTRIBUTION_ID="${CLOUDFRONT_DISTRIBUTION_ID:-E1T3WQ2YHO1BNA}"
CLOUDFRONT_DOMAIN="${CLOUDFRONT_DOMAIN:-doy5alruji476.cloudfront.net}"

# Colors / helpers
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
die(){ echo -e "${RED}❌ $*${NC}"; exit 1; }
mask(){ local v="$1"; echo "${v:0:3}******${v: -3}"; }

echo -e "${GREEN}🚀 Starting frontend deployment for stage: $STAGE${NC}"

# ──────────────────────────────────────────────────────────────
# Pre-checks
# ──────────────────────────────────────────────────────────────
command -v aws  >/dev/null 2>&1 || die "AWS CLI not found"
command -v node >/dev/null 2>&1 || die "Node.js not found"
command -v npm  >/dev/null 2>&1 || die "npm not found"

# 必須ENV（ここで未設定なら中断）
: "${REACT_APP_COGNITO_CLIENT_ID:?REACT_APP_COGNITO_CLIENT_ID is required}"
: "${REACT_APP_COGNITO_USER_POOL_ID:?REACT_APP_COGNITO_USER_POOL_ID is required}"

CLIENT_ID="$REACT_APP_COGNITO_CLIENT_ID"
USER_POOL_ID="$REACT_APP_COGNITO_USER_POOL_ID"

echo -e "${GREEN}🔐 Cognito ClientId: $(mask "$CLIENT_ID")${NC}"
echo -e "${GREEN}🔐 UserPoolId:       $(mask "$USER_POOL_ID")${NC}"

# 旧IDだけをブロック（誤検知しないよう限定）
if [[ "$CLIENT_ID" == "1179cu6f4a1g8hqhavmndtf8as" || \
      "$CLIENT_ID" == "2bggeikp7ijt5medn414pkfkmk" || \
      "$CLIENT_ID" == "placeholder-client-id" ]]; then
  die "Forbidden/placeholder ClientId detected. Abort."
fi

# 形式チェック
[[ "$CLIENT_ID" =~ ^[a-z0-9]{10,64}$ ]] || die "Invalid ClientId format (lowercase alnum, 10-64)"
[[ "$USER_POOL_ID" =~ ^ap-northeast-1_.+ ]] || die "Invalid UserPoolId format for ap-northeast-1"

# S3/CF 存在チェック
aws s3 ls "s3://$BUCKET_NAME" --region "$BUCKET_REGION" >/dev/null 2>&1 \
  || die "S3 bucket '$BUCKET_NAME' not found in region '$BUCKET_REGION'"
echo -e "${GREEN}✅ S3 Bucket: $BUCKET_NAME${NC}"
echo -e "${GREEN}✅ CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID${NC}"

# ──────────────────────────────────────────────────────────────
# Backend endpoint
# ──────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────
# Write .env.production（ENVの値を書き込む）
# ──────────────────────────────────────────────────────────────
echo -e "${YELLOW}📝 Creating $FRONTEND_DIR/.env.production...${NC}"
cat > "$FRONTEND_DIR/.env.production" << EOF
# Auto-generated for $STAGE
REACT_APP_API_URL=$API_URL
REACT_APP_COGNITO_USER_POOL_ID=$USER_POOL_ID
REACT_APP_COGNITO_CLIENT_ID=$CLIENT_ID
REACT_APP_REGION=${REACT_APP_REGION:-ap-northeast-1}
REACT_APP_STAGE=$STAGE
GENERATE_SOURCEMAP=false
EOF
echo -e "${GREEN}✅ .env.production created${NC}"

# ──────────────────────────────────────────────────────────────
# Build
# ──────────────────────────────────────────────────────────────
cd "$FRONTEND_DIR"
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
npm ci --production=false

echo -e "${YELLOW}🏗️  Building React app...${NC}"
npm run build
[ -d "build" ] || die "Build failed (build dir missing)"
echo -e "${GREEN}✅ Build succeeded${NC}"

# 旧ID混入チェック（追加の安全網）
if grep -R -E "1179cu6f4a1g8hqhavmndtf8as|2bggeikp7ijt5medn414pkfkmk" build >/dev/null 2>&1; then
  die "Found forbidden old client id inside build artifacts"
fi
if grep -R "ap-northeast-1_wkRvKeooL" build >/dev/null 2>&1; then
  die "Found old UserPoolId (wkRvKeooL) in build artifacts"
fi
cd ..

# ──────────────────────────────────────────────────────────────
# Optional: S3/CFront policy fix
# ──────────────────────────────────────────────────────────────
echo -e "${YELLOW}🔧 Ensuring S3/CFront config...${NC}"
chmod +x scripts/fix-cloudfront-s3.sh 2>/dev/null || true
./scripts/fix-cloudfront-s3.sh 2>/dev/null || echo -e "${YELLOW}⚠️  Skipped/failed config fix, continue${NC}"

# ──────────────────────────────────────────────────────────────
# Upload (改善版)
#  1) 静的アセット: 1年 + immutable（HTML/manifest/SW/asset-manifest は除外）
#  2) HTML/manifest/SW/asset-manifest: no-cache で個別アップロード
# ──────────────────────────────────────────────────────────────
echo -e "${YELLOW}☁️  Sync static assets → s3://$BUCKET_NAME (cache=1year, immutable)${NC}"
aws s3 sync "$BUILD_DIR" "s3://$BUCKET_NAME" \
  --region "$BUCKET_REGION" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --exclude "service-worker.js" \
  --exclude "service-worker-*" \
  --exclude "manifest.json" \
  --exclude "asset-manifest.json"

echo -e "${YELLOW}🧾 Upload HTML (no-cache)${NC}"
aws s3 cp "$BUILD_DIR/index.html" "s3://$BUCKET_NAME/index.html" \
  --region "$BUCKET_REGION" \
  --cache-control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" \
  --expires "0" \
  --content-type "text/html; charset=utf-8"

# 追加の .html があれば同様に no-cache で上書き
find "$BUILD_DIR" -name "*.html" ! -name "index.html" -print0 | while IFS= read -r -d '' f; do
  rel="${f#$BUILD_DIR/}"
  aws s3 cp "$f" "s3://$BUCKET_NAME/$rel" \
    --region "$BUCKET_REGION" \
    --cache-control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" \
    --expires "0" \
    --content-type "text/html; charset=utf-8"
done

# manifest.json（PWA用）
if [ -f "$BUILD_DIR/manifest.json" ]; then
  aws s3 cp "$BUILD_DIR/manifest.json" "s3://$BUCKET_NAME/manifest.json" \
    --region "$BUCKET_REGION" \
    --cache-control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" \
    --expires "0" \
    --content-type "application/manifest+json; charset=utf-8"
fi

# asset-manifest.json（CRA系）
if [ -f "$BUILD_DIR/asset-manifest.json" ]; then
  aws s3 cp "$BUILD_DIR/asset-manifest.json" "s3://$BUCKET_NAME/asset-manifest.json" \
    --region "$BUCKET_REGION" \
    --cache-control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" \
    --expires "0" \
    --content-type "application/json; charset=utf-8"
fi

# Service Worker
for sw in "$BUILD_DIR"/service-worker*.js; do
  [ -e "$sw" ] || continue
  rel="${sw#$BUILD_DIR/}"
  aws s3 cp "$sw" "s3://$BUCKET_NAME/$rel" \
    --region "$BUCKET_REGION" \
    --cache-control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" \
    --expires "0" \
    --content-type "application/javascript; charset=utf-8"
done

echo -e "${GREEN}✅ S3 upload complete${NC}"

# ──────────────────────────────────────────────────────────────
# CloudFront invalidation
# ──────────────────────────────────────────────────────────────
echo -e "${YELLOW}🔄 Invalidating CloudFront cache...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text 2>/dev/null || echo "")

if [ -n "$INVALIDATION_ID" ]; then
  echo -e "${GREEN}✅ Invalidation created: $INVALIDATION_ID${NC}"
else
  echo -e "${YELLOW}⚠️  Could not create invalidation (check IAM/Dist ID)${NC}"
fi

WEBSITE_URL="https://$CLOUDFRONT_DOMAIN"
echo -e "${GREEN}🌐 Website URL: $WEBSITE_URL${NC}"

# ──────────────────────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────────────────────
echo -e "${GREEN}🎉 Frontend deployment done${NC}"
echo -e "${YELLOW}📋 Summary:${NC}"
echo -e "   Stage:               $STAGE"
echo -e "   S3 Bucket:           $BUCKET_NAME (Region: $BUCKET_REGION)"
echo -e "   CloudFront Dist:     $CLOUDFRONT_DISTRIBUTION_ID"
echo -e "   Website URL:         $WEBSITE_URL"
echo -e "   API URL:             $API_URL"
echo -e "   Cognito User Pool:   $USER_POOL_ID"
echo -e "   Cognito Client:      $(mask "$CLIENT_ID")"
[ -n "$INVALIDATION_ID" ] && echo -e "   Invalidation:        $INVALIDATION_ID"
