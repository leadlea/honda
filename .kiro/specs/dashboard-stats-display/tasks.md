# 実装計画

- [x] 1. バックエンド統計API実装
  - [x] 1.1 Statistics Handler Lambda関数作成
    - `src/handlers/stats_handler.py` ファイル作成
    - ユーザー統計データ取得関数実装
    - 完了したAIスキル棚卸し数カウント関数実装
    - 推薦数カウント関数実装
    - 自薦応募数カウント関数実装
    - プロフィール閲覧数取得関数実装
    - AIスキルポートフォリオ見出し取得関数実装
    - 並行データ取得（ThreadPoolExecutor）実装
    - エラーハンドリングとロギング実装
    - _要件: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 5.1, 5.2, 6.1, 6.2, 6.3_

  - [x] 1.2 API Gateway エンドポイント設定
    - `serverless.yml` に `/stats/{userId}` エンドポイント追加
    - Cognito認証統合設定
    - CORS設定
    - Lambda関数とエンドポイントの紐付け
    - _要件: 5.1, 5.2_

  - [x] 1.3 プロフィール閲覧数追跡機能実装
    - `src/handlers/public_search_handler.py` にプロフィール閲覧数増加処理追加
    - VeteranProfiles テーブルの `profile_views` フィールド更新
    - 閲覧数増加のエラーハンドリング
    - _要件: 4.1, 4.2, 4.4_

- [x] 2. フロントエンド統計表示実装
  - [x] 2.1 Statistics Service作成
    - `frontend/src/services/statisticsService.ts` ファイル作成
    - `getDashboardData` メソッド実装（AIスキルポートフォリオ見出しと統計データを取得）
    - `getUserStatistics` メソッド実装（後方互換性のため）
    - API呼び出しと認証ヘッダー設定
    - エラーハンドリングとデフォルト値返却
    - TypeScript型定義（UserStatistics, DashboardData）追加
    - _要件: 1.3, 2.3, 3.3, 4.2, 5.1, 5.2, 6.2_

  - [x] 2.2 Dashboard Component更新
    - `frontend/src/components/dashboard/Dashboard.tsx` 更新
    - ダッシュボードデータ取得用のuseEffect追加
    - ローディング状態管理（loadingStats）追加
    - AIスキルポートフォリオ見出し表示ロジック実装（設定されている場合のみ表示）
    - 統計データ表示ロジック実装
    - renderStatValue関数実装（ローディング中は「...」、データあれば数値、なければ「-」）
    - _要件: 1.3, 1.4, 2.3, 2.4, 3.3, 3.4, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4_

  - [x] 2.3 Statistics Service型定義追加
    - `frontend/src/types/profile.ts` に UserStatistics インターフェース追加
    - `frontend/src/types/profile.ts` に DashboardData インターフェース追加
    - 統計データとAIスキルポートフォリオ見出しの型定義
    - _要件: 全要件の型安全性_
    
  - [ ] 2.4 Dashboard CSS更新
    - `frontend/src/components/dashboard/Dashboard.css` 更新
    - AIスキルポートフォリオ見出し用のスタイル追加（.business-title）
    - ウェルカムメッセージとサブタイトルの間に配置
    - _要件: 5.2, 5.4_

- [x] 3. DynamoDB GSI確認と最適化
  - [x] 3.1 既存GSIの確認
    - Questionnaires テーブルの UserIdIndex 存在確認
    - Applications テーブルの UserIdIndex 存在確認
    - Recommendations テーブルのキー構造確認
    - _要件: 5.3, 5.4_

  - [x] 3.2 必要に応じてGSI追加
    - 不足しているGSIを `serverless.yml` に追加
    - DynamoDBテーブル定義更新
    - _要件: 5.3, 5.4_

- [x] 4. 統合とデプロイ
  - [x] 4.1 バックエンドデプロイ
    - Serverless Framework でバックエンドデプロイ
    - API Gateway エンドポイント動作確認
    - Lambda関数ログ確認
    - _要件: 全要件の統合_

  - [x] 4.2 フロントエンドビルドとデプロイ
    - React アプリケーションビルド
    - S3へのデプロイ
    - CloudFront キャッシュクリア
    - _要件: 全要件の統合_

  - [x] 4.3 エンドツーエンド動作確認
    - ダッシュボードアクセスして統計データ表示確認
    - AIスキルポートフォリオ見出しが正しく表示されることを確認（設定されている場合）
    - AIスキルポートフォリオ見出しが表示されないことを確認（設定されていない場合）
    - 完了したAIスキル棚卸し数が正しく表示されることを確認
    - 推薦数、自薦応募数、プロフィール閲覧数の表示確認
    - ローディング状態の表示確認
    - エラー時のフォールバック動作確認
    - _要件: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4_

- [x] 5. テストとドキュメント
  - [x] 5.1 バックエンド単体テスト作成
    - `tests/unit/test_stats_handler.py` 作成
    - 各カウント関数のテスト（AIスキルポートフォリオ見出し取得を含む）
    - エラーケースのテスト
    - 並行実行のテスト
    - _要件: 6.1, 6.2, 6.3_

  - [x] 5.2 フロントエンド単体テスト作成
    - `frontend/src/services/statisticsService.test.ts` 作成
    - `frontend/src/components/dashboard/Dashboard.test.tsx` 更新
    - ダッシュボードデータ取得のテスト（AIスキルポートフォリオ見出しを含む）
    - AIスキルポートフォリオ見出し表示のテスト
    - ローディング状態のテスト
    - エラーハンドリングのテスト
    - _要件: 6.2_

  - [x] 5.3 パフォーマンステスト
    - 統計データ取得のレスポンス時間測定
    - 並行実行の効果確認
    - 5秒以内のレスポンス確認
    - _要件: 6.3, 6.4_
