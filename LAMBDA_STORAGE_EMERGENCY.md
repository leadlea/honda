# Lambda Storage Emergency Response

## 🚨 緊急事態: Code storage limit exceeded

### 即座に実行する手順

1. **手動でLambda関数のバージョンを削除**:
```bash
# 東京リージョンのLambda関数一覧を取得
aws lambda list-functions --region ap-northeast-1 --query "Functions[?starts_with(FunctionName, 'honda-veteran-talent-matching')].FunctionName" --output table

# 特定の関数の古いバージョンを削除
aws lambda list-versions-by-function --region ap-northeast-1 --function-name honda-veteran-talent-matching-prod-publicSearchHandler --query "Versions[?Version != '\$LATEST'].Version" --output table

# 古いバージョンを削除（例：バージョン1-10を削除）
for i in {1..10}; do
  aws lambda delete-function --region ap-northeast-1 --function-name honda-veteran-talent-matching-prod-publicSearchHandler --qualifier $i
done
```

2. **自動クリーンアップスクリプトを実行**:
```bash
chmod +x scripts/cleanup-lambda-versions.sh
./scripts/cleanup-lambda-versions.sh
```

3. **現在のストレージ使用量を確認**:
```bash
aws lambda get-account-settings --region ap-northeast-1 --query "AccountUsage" --output table
```

### 根本的な解決策

1. **serverless.ymlの設定変更**:
   - `versionFunctions: false` を追加済み
   - これにより新しいバージョンの自動作成を無効化

2. **定期的なクリーンアップ**:
   - CI/CDパイプラインにクリーンアップステップを追加済み
   - 月1回の定期実行を推奨

3. **監視の設定**:
   - CloudWatchアラームでストレージ使用量を監視
   - 70%に達したら警告を送信

### 予防策

1. **デプロイ戦略の見直し**:
   - Blue/Green デプロイメントの代わりにRolling デプロイメントを検討
   - 必要最小限の関数のみデプロイ

2. **コードサイズの最適化**:
   - 不要な依存関係の削除
   - Lambda Layersの活用
   - コードの圧縮

3. **定期メンテナンス**:
   - 月次でのバージョンクリーンアップ
   - 未使用のLambda関数の削除

### 緊急連絡先

- AWS サポート: 技術的な問題の場合
- 開発チーム: デプロイメント関連の問題の場合

### 参考リンク

- [AWS Lambda Quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- [Serverless Framework Version Management](https://www.serverless.com/framework/docs/providers/aws/guide/functions#versioning)