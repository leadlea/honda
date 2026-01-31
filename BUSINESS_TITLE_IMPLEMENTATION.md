# ビジネスタイトル生成機能 実装完了

## 概要

要件6「ベテラン社員として、自分のスキルと経験に基づいたユニークなビジネスタイトルを生成してもらいたい」の実装が完了しました。

## 実装内容

### バックエンド (Python/Lambda)

#### 1. ハンドラー実装
- **ファイル**: `src/handlers/business_title_handler.py`
- **機能**:
  - `generate_business_titles`: AI駆動のビジネスタイトル生成
  - `select_business_title`: タイトル選択とプロフィール更新
  - `regenerate_business_titles`: 追加コンテキストでの再生成
  - `get_title_history`: タイトル生成・選択履歴の取得

#### 2. AI統合
- **ファイル**: `src/services/ai_utils.py`
- **AIモデル**: AWS Bedrock Claude Sonnet 4 (問診生成と同じモデル)
- **プロンプト**: スキル、経験、キャリア興味に基づいた5つのユニークなタイトル生成

#### 3. API エンドポイント
- **設定ファイル**: `serverless.yml`
- **エンドポイント**:
  - `POST /profiles/{userId}/business-title` - タイトル生成
  - `PUT /profiles/{userId}/business-title` - タイトル選択
  - `POST /profiles/{userId}/business-title/regenerate` - タイトル再生成
  - `GET /profiles/{userId}/business-title/history` - 履歴取得

### フロントエンド (React/TypeScript)

#### 1. コンポーネント
- **ファイル**: `frontend/src/components/profile/BusinessTitleGenerator.tsx`
- **機能**:
  - AI生成ボタン
  - タイトル候補表示（適合度スコア付き）
  - タイトル選択機能
  - 再生成ボタン
  - カスタムタイトル入力
  - プレビュー表示

#### 2. サービス層
- **ファイル**: `frontend/src/services/profileService.ts`
- **メソッド**:
  - `generateBusinessTitle(userId)`: タイトル生成
  - `selectBusinessTitle(userId, title)`: タイトル選択
  - `regenerateBusinessTitle(userId, context?)`: タイトル再生成
  - `getBusinessTitleHistory(userId)`: 履歴取得

#### 3. スタイリング
- **ファイル**: `frontend/src/components/profile/BusinessTitleGenerator.css`
- **デザイン**: モダンなカードベースUI、適合度バッジ、プレビューカード

## 受入基準の達成状況

### ✅ 1. システムがベテランのプロフィールを分析する時、スキル、経験、専門分野に基づいてユニークなビジネスタイトルを生成すること
- AI (Bedrock Claude) がプロフィールデータを分析
- スキル、経験、キャリア興味を考慮
- 5つのユニークなタイトル候補を生成

### ✅ 2. 生成されたタイトルがベテランの専門性と価値提案を明確に表現すること
- 各タイトルに説明文（reasoning）を付与
- フォーカスエリア（focus_areas）を明示
- 市場適合度（market_appeal）を評価

### ✅ 3. ベテランが生成されたタイトルを確認し、必要に応じて修正や再生成を要求できること
- タイトル候補の一覧表示
- 選択機能の実装
- 再生成ボタンの実装
- カスタムタイトル入力機能

### ✅ 4. タイトルが社内外での検索やマッチングに活用されること
- プロフィールの`business_title`フィールドに保存
- 検索・マッチング機能で利用可能
- 履歴管理により変更追跡が可能

## テスト

### 単体テスト
- **ファイル**: `tests/unit/test_business_title_handler.py`
- **カバレッジ**: 全ハンドラーメソッド
- **テストケース**:
  - 正常系: タイトル生成、選択、再生成、履歴取得
  - 異常系: 認証エラー、権限エラー、プロフィール未存在
  - エッジケース: 無効なJSON、必須フィールド欠落

## デプロイ

### バックエンド
```bash
serverless deploy
```

### フロントエンド
```bash
cd frontend
npm run build
aws s3 sync build/ s3://honda-veteran-bank-frontend
```

## 使用方法

### ユーザーフロー
1. ベテラン社員がプロフィール管理画面にアクセス
2. 「ビジネスタイトル生成」タブを選択
3. 「AIで生成」ボタンをクリック
4. 5つのタイトル候補が表示される（適合度スコア付き）
5. 気に入ったタイトルを選択、または「再生成」で新しい候補を取得
6. 選択したタイトルがプロフィールに保存される
7. プレビューで確認

### API使用例

#### タイトル生成
```bash
curl -X POST \
  https://api.example.com/profiles/user123/business-title \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

#### タイトル選択
```bash
curl -X PUT \
  https://api.example.com/profiles/user123/business-title \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Senior Software Architect"}'
```

## 技術仕様

### AIプロンプト
- **温度**: 0.8 (創造性を重視)
- **最大トークン**: 2000
- **入力**: スキル、経験、キャリア興味、現在の役職
- **出力**: JSON形式（タイトル、説明、フォーカスエリア、市場適合度）

### データモデル
```python
{
  "titles": [
    {
      "title": "Senior Software Architect",
      "description": "Combines technical expertise with leadership",
      "focus_areas": ["Architecture", "Leadership", "Innovation"],
      "market_appeal": "high"
    }
  ],
  "recommended_title": "Senior Software Architect",
  "reasoning": "Best reflects technical and leadership skills"
}
```

### 履歴管理
- 最新10件の生成履歴を保存
- 選択履歴を無制限に保存
- タイムスタンプ付き

## セキュリティ

- AWS Cognito認証必須
- ベテラン役割のみアクセス可能
- CORS設定済み
- 入力バリデーション実装

## パフォーマンス

- Lambda タイムアウト: 29秒
- メモリ: 1024MB
- Bedrock レスポンス時間: 通常2-5秒
- キャッシング: Bedrock Optimizer使用

## 今後の改善案

1. タイトル候補の多言語対応
2. 業界別テンプレート
3. A/Bテストによる推薦精度向上
4. ユーザーフィードバック収集
5. タイトルの効果測定（マッチング率への影響）

## 関連ドキュメント

- [要件定義書](.kiro/specs/veteran-talent-matching/requirements.md)
- [設計文書](.kiro/specs/veteran-talent-matching/design.md)
- [実装計画](.kiro/specs/veteran-talent-matching/tasks.md)
