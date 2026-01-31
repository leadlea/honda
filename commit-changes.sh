#!/bin/bash
cd /Users/2511021/gen/honda
git add serverless.yml .github/workflows/deploy.yml
git commit -m "Fix: Add Cognito environment variables to Lambda functions for authentication"
git push origin main
