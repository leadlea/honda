# 実装計画: AI人材発掘・配置マッチングMVP（AI CoE支援）文言更新

## 概要

既存の旧MVP用語（「製造業プラチナアドバイザリー」系）から「双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）」への文言統一を段階的に実装します。既存のブランディング基盤ファイル（term-mapping.json、message_config.py、ai_content_config.py、branding_logger.py、termMappingService.ts、brandingUtils.ts）の用語を新しい双日TI用語に更新し、フロントエンド・バックエンド全体で統一された用語体験を提供します。コードロジック・API構造・DBスキーマは一切変更しません。

## タスク

- [x] 1. 用語マッピング設定基盤の更新
  - [x] 1.1 用語マッピング設定ファイル（term-mapping.json）の更新
    - `src/config/term-mapping.json` のすべての用語を新しい双日TI用語に更新
    - `termMappings.legacy_terms`: 旧用語→新用語マッピングを更新（例: 「製造業プラチナアドバイザリー」→「AI人材発掘・配置マッチングMVP（AI CoE支援）」、「登録人材」→「社内AI人材候補」、「スキル棚卸し」→「AIスキル棚卸し（セルフ診断）」、「参画機会レコメンド」→「AIポジション／プロジェクト レコメンド」、「参画申請」→「自薦応募」、「参画意向」→「応募意向」、「登録人材検索」→「社内AI人材候補検索」等）
    - `ui_labels`: すべてのUIラベルを新用語に更新
    - `branding.messaging`: taglineを「AI内製化を前進させるための人材発掘と適材配置」に、brand_conceptを双日TI向けに更新
    - `messages`: success/errors/infoメッセージをすべて新用語に更新
    - _要件: 1.1, 1.2, 1.4, 1.5, 2.1, 2.2, 3.1, 6.1, 6.2, 6.3, 8.1_

  - [x] 1.2 フロントエンド用語変換サービス（termMappingService.ts）の更新
    - `frontend/src/services/termMappingService.ts` の `validateTermConsistency()` 内の `requiredTerms` と `requiredLabels` を新用語に合わせて更新
    - 旧用語チェックリストを新しいマッピングキーに変更
    - _要件: 1.1, 1.2, 1.4, 1.5, 6.3_

  - [x] 1.3 フロントエンドブランディングユーティリティ（brandingUtils.ts）の更新
    - `frontend/src/utils/brandingUtils.ts` の `BRANDING_CONFIG` を双日TI向けに更新（platformName、mission、targetAudience等）
    - `TONE_GUIDELINES` を社内向け信頼感あるトーンに更新
    - `TERM_MAPPINGS` を新用語マッピングに更新
    - `BRANDED_MESSAGES` の全カテゴリ（welcome、dashboard、profile、questionnaire、recommendations、applications、search、common、ecosystem）を新用語に更新
    - `validateBrandingConsistency()` のチェック対象を新用語に更新
    - _要件: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 6.1, 6.2, 6.3_

  - [ ]* 1.4 用語マッピングサービスのプロパティテスト作成
    - **プロパティ 1: 用語マッピング一貫性**
    - **検証対象: 要件 1.1, 1.2, 1.4, 1.5, 2.1, 2.2, 3.1, 6.3**

- [x] 2. フロントエンドコンポーネント文言更新
  - [x] 2.1 アプリケーションタイトルとナビゲーション更新
    - `frontend/src/App.tsx` でアプリケーションタイトルを「AI人材発掘・配置マッチングMVP（AI CoE支援）」に更新
    - ナビゲーションメニュー項目を新用語に更新（「社内AI人材候補」「AIスキル棚卸し（セルフ診断）」「AIスキルポートフォリオ」「AIポジション／プロジェクト レコメンド」「自薦応募」等）
    - _要件: 1.1, 1.2_

  - [x] 2.2 ダッシュボード用語更新
    - `frontend/src/components/dashboard/Dashboard.tsx` と `Dashboard.css` で統計表示とメッセージの用語を新用語に更新
    - すべてのダッシュボード要素で「社内AI人材候補」「AIスキルポートフォリオ」「AIポジション／プロジェクト レコメンド」「自薦応募」等の新用語を使用
    - _要件: 1.3_

  - [ ]* 2.3 ダッシュボード用語統一のプロパティテスト作成
    - **プロパティ 2: ダッシュボード用語統一**
    - **検証対象: 要件 1.3**

  - [x] 2.4 プロフィール管理画面の用語更新
    - `frontend/src/components/profile/ProfileManagement.tsx` と `ProfileManagement.css` で「AIスキルポートフォリオ」関連用語に更新
    - `frontend/src/components/profile/UserProfile.tsx` でプロフィール関連用語を統一
    - `frontend/src/components/profile/BusinessTitleGenerator.tsx` で見出し生成関連用語を更新
    - `frontend/src/components/profile/PrivacySettings.tsx` でプライバシー設定の用語を更新
    - _要件: 1.4_

  - [x] 2.5 AIスキル棚卸し（セルフ診断）画面の用語更新
    - `frontend/src/components/questionnaire/Questionnaire.tsx` と `Questionnaire.css` で「AIスキル棚卸し（セルフ診断）」関連用語に更新
    - _要件: 1.2_

- [x] 3. 推薦・応募・検索システム用語更新
  - [x] 3.1 推薦システム用語更新
    - `frontend/src/components/recommendations/RecommendationsList.tsx`、`RecommendationCard.tsx`、`OpportunityDetail.tsx` で「AIポジション／プロジェクト レコメンド」関連用語に更新
    - `frontend/src/services/recommendationService.ts` のメッセージを新用語に更新
    - _要件: 1.5_

  - [x] 3.2 応募システム用語更新
    - `frontend/src/components/recommendations/ApplicationTracker.tsx` で「自薦応募」「応募意向」関連用語に更新
    - すべての応募ステータス表示で新用語を使用
    - _要件: 2.1, 2.2, 2.3_

  - [ ]* 3.3 応募システム用語統一のプロパティテスト作成
    - **プロパティ 3: 応募システム用語統一**
    - **検証対象: 要件 2.3**

  - [x] 3.4 社内AI人材候補検索画面の用語更新
    - `frontend/src/components/public/PublicVeteranSearch.tsx` と `PublicVeteranSearch.css` で「社内AI人材候補検索」関連用語に更新
    - `frontend/src/components/public/VeteranSearchCard.tsx`、`VeteranProfileModal.tsx`、`SearchFiltersPanel.tsx` で人材関連用語を統一
    - `frontend/src/services/publicSearchService.ts` のメッセージを新用語に更新
    - _要件: 3.1, 3.2_

  - [ ]* 3.5 検索結果用語統一のプロパティテスト作成
    - **プロパティ 4: 検索結果用語統一**
    - **検証対象: 要件 3.2**

  - [x] 3.6 認証・サインアップ画面の用語更新
    - `frontend/src/components/auth/SignUpForm.tsx` でサインアップ関連メッセージを新用語に更新
    - `frontend/src/contexts/AuthContext.tsx` で認証関連メッセージを新用語に更新
    - `frontend/src/components/public/ContactForm.tsx` で問い合わせフォームの用語を更新
    - _要件: 1.1, 6.1, 6.2_

- [x] 4. チェックポイント - フロントエンド用語統一確認
  - すべてのテストが通ることを確認し、質問があればユーザーに確認する

- [x] 5. バックエンドメッセージ設定の更新
  - [x] 5.1 メッセージ設定サービス（message_config.py）の更新
    - `src/config/message_config.py` の `_initialize_default_config()` 内のすべてのメッセージを新用語に更新
    - success_messages: 「AIスキルポートフォリオ」「自薦応募」「AIスキル棚卸し」「社内AI人材候補」等の新用語を使用
    - error_messages: 同様に新用語に更新
    - info_messages: ウェルカムメッセージを「AI人材発掘・配置マッチングMVP（AI CoE支援）へようこそ」に更新、ヘルプメッセージも新用語に
    - term_mappings: 新しいレガシー→新用語マッピングに更新
    - `_initialize_log_templates()` のすべてのログテンプレートを新用語に更新（「社内AI人材候補」「AIスキルポートフォリオ」「自薦応募」「AIスキル棚卸し」「社内AI人材候補検索」等）
    - _要件: 4.1, 4.2, 4.3_

  - [x] 5.2 ブランディングロガー（branding_logger.py）の更新
    - `src/utils/branding_logger.py` のdocstringとコメントを双日TI向けに更新
    - `log_security_event` 等のメソッド内の「登録人材」→「社内AI人材候補」に更新
    - `log_business_event` 内の用語を更新
    - グローバルインスタンス名を適切に更新
    - _要件: 4.3_

  - [ ]* 5.3 APIレスポンス用語統一のプロパティテスト作成
    - **プロパティ 5: APIレスポンス用語統一**
    - **検証対象: 要件 4.1, 4.2**

  - [ ]* 5.4 ログメッセージ用語統一のプロパティテスト作成
    - **プロパティ 6: ログメッセージ用語統一**
    - **検証対象: 要件 4.3**

- [x] 6. バックエンドAPIハンドラーメッセージ更新
  - [x] 6.1 認証ハンドラーのメッセージ更新
    - `src/handlers/auth_handler.py` でエラーメッセージと成功メッセージを新用語に更新
    - _要件: 4.1, 4.2_

  - [x] 6.2 プロフィールハンドラーのメッセージ更新
    - `src/handlers/profile_handler.py` で「AIスキルポートフォリオ」関連メッセージに更新
    - _要件: 4.1, 4.2_

  - [x] 6.3 推薦・応募ハンドラーのメッセージ更新
    - `src/handlers/matching_handler.py` で「AIポジション／プロジェクト レコメンド」関連メッセージに更新
    - `src/handlers/application_handler.py` で「自薦応募」「応募意向」関連メッセージに更新
    - _要件: 4.1, 4.2_

  - [x] 6.4 検索・問い合わせハンドラーのメッセージ更新
    - `src/handlers/public_search_handler.py` で「社内AI人材候補検索」関連メッセージに更新
    - `src/handlers/contact_handler.py` で問い合わせ関連メッセージを新用語に更新
    - _要件: 4.1, 4.2_

  - [x] 6.5 AIスキル棚卸し・ビジネスタイトルハンドラーのメッセージ更新
    - `src/handlers/questionnaire_handler.py` で「AIスキル棚卸し（セルフ診断）」関連メッセージに更新
    - `src/handlers/business_title_handler.py` で「AIスキルポートフォリオ」文脈でのメッセージに更新
    - _要件: 4.1, 4.2_

- [x] 7. チェックポイント - バックエンドメッセージ更新確認
  - すべてのテストが通ることを確認し、質問があればユーザーに確認する

- [x] 8. AI生成コンテンツ設定の更新
  - [x] 8.1 AI コンテンツ設定（ai_content_config.py）の更新
    - `src/config/ai_content_config.py` の `_initialize_default_config()` を全面更新
    - `brand_context`: platform_nameを「AI人材発掘・配置マッチングMVP（AI CoE支援）」に、missionを「AI内製化を前進させるための人材発掘と適材配置」に、target_audienceを「社内AI人材候補（社員）」に更新
    - `tone_guidelines`: 社内向け信頼感あるトーン（過度に煽らない、誤解を招かない）に更新
    - `questionnaire_prompts`: system_prompt、context_prompt、fallback_promptをすべて双日TI向けAIスキル棚卸し文脈に更新（「社内AI人材候補」「AIスキル棚卸し（セルフ診断）」「AIポジション／プロジェクト レコメンド」「自薦応募」等の用語使用）
    - `recommendation_templates`: match_reason_template、system_context、tone_instructionを「AI内製化を前進させるための適材配置」文脈に更新
    - `business_title_context`: 双日TI向けAIスキルポートフォリオ文脈に更新
    - `apply_branding_context()` 内のterm_mappingsを新用語に更新
    - _要件: 5.1, 5.2, 5.3, 6.1, 6.2_

  - [ ]* 8.2 AI生成コンテンツ用語統一のプロパティテスト作成
    - **プロパティ 7: AI生成コンテンツ用語統一**
    - **検証対象: 要件 5.1, 5.2, 5.3**

- [x] 9. CSSテーマ・スタイル更新
  - [x] 9.1 テーマCSSの更新
    - `frontend/src/styles/theme.css` でCSS変数のコメントやカスタムプロパティ名を双日TI向けに更新
    - 色テーマは設計文書のbranding.themeに準拠（primary: #2C5282等）
    - _要件: 6.1, 8.4_

- [x] 10. チェックポイント - AI生成コンテンツ・テーマ更新確認
  - すべてのテストが通ることを確認し、質問があればユーザーに確認する

- [x] 11. 既存テストの用語更新
  - [x] 11.1 統合テストの用語更新
    - `tests/integration/` 配下の全テストファイルで旧用語を新用語に更新
    - `test_terminology_consistency.py`: 用語一貫性チェック対象を新用語に更新
    - `test_e2e_terminology_consistency.py`: E2E用語チェック対象を新用語に更新
    - `test_api_structure_invariance.py`: API構造不変性テストのメッセージを更新
    - `test_database_schema_invariance.py`: DBスキーマ不変性テストのメッセージを更新
    - `test_functional_behavior_invariance.py`: 機能動作不変性テストのメッセージを更新
    - `test_existing_test_compatibility.py`: 既存テスト互換性テストのメッセージを更新
    - `test_performance_impact.py`: パフォーマンス影響テストのメッセージを更新
    - `test_responsive_design_maintenance.py`: レスポンシブデザインテストのメッセージを更新
    - _要件: 7.4, 8.1_

  - [x] 11.2 フロントエンドテストの用語更新
    - `frontend/src/components/questionnaire/Questionnaire.test.tsx` で旧用語を新用語に更新
    - その他フロントエンドテストファイルで旧用語が使われている箇所を新用語に更新
    - _要件: 7.4_

  - [ ]* 11.3 システム不変性保証のプロパティテスト作成
    - **プロパティ 8: システム不変性保証**
    - **検証対象: 要件 7.1, 7.2, 7.3, 7.4**

  - [ ]* 11.4 画面間用語一貫性のプロパティテスト作成
    - **プロパティ 9: 画面間用語一貫性**
    - **検証対象: 要件 8.1**

  - [ ]* 11.5 レスポンシブデザイン維持のプロパティテスト作成
    - **プロパティ 10: レスポンシブデザイン維持**
    - **検証対象: 要件 8.4**

- [x] 12. 最終チェックポイント - 全機能動作確認
  - すべてのテストが通ることを確認し、質問があればユーザーに確認する
  - 全画面で旧用語（「製造業プラチナアドバイザリー」「登録人材」「スキル棚卸し」「参画機会レコメンド」「参画申請」「参画意向」「登録人材検索」等）が残っていないことを確認

## 注意事項

- `*` マークの付いたタスクはオプションで、より迅速なMVPのためにスキップ可能
- 各タスクは特定の要件への追跡可能性のため要件番号を参照
- チェックポイントで段階的な検証を実施
- プロパティテストは普遍的な正確性プロパティを検証
- コードロジック・API構造・データベーススキーマは一切変更しない（日本語文言・用語・メッセージトーンの更新のみ）
