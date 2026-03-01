# 設計文書

## 概要

ダッシュボード統計表示機能は、既存のバックエンドAPIとフロントエンドコンポーネントを拡張して、社内AI人材候補（社員）の活動統計をリアルタイムで表示します。DynamoDBからAIスキル棚卸し、推薦、自薦応募、プロフィール閲覧データを取得し、ダッシュボードUIに表示します。

## アーキテクチャ

### システム構成

```mermaid
graph TB
    subgraph "フロントエンド"
        DASHBOARD[Dashboard Component]
        STATS_SERVICE[Statistics Service]
    end
    
    subgraph "API Gateway"
        API[/stats/{userId}]
    end
    
    subgraph "Lambda"
        STATS_LAMBDA[Statistics Handler]
    end
    
    subgraph "DynamoDB"
        TBL_Q[Questionnaires Table]
        TBL_REC[Recommendations Table]
        TBL_APP[Applications Table]
        TBL_PROF[VeteranProfiles Table]
    end
    
    DASHBOARD --> STATS_SERVICE
    STATS_SERVICE --> API
    API --> STATS_LAMBDA
    STATS_LAMBDA --> TBL_Q
    STATS_LAMBDA --> TBL_REC
    STATS_LAMBDA --> TBL_APP
    STATS_LAMBDA --> TBL_PROF
```

### データフロー

1. ユーザーがダッシュボードにアクセス
2. Dashboard コンポーネントが Statistics Service を呼び出し
3. Statistics Service が API Gateway 経由で Lambda 関数を呼び出し
4. Lambda 関数が DynamoDB から各テーブルのデータを並行取得
5. Lambda 関数が集計結果を返却
6. Dashboard が統計データを表示

## コンポーネントと インターフェース

### 1. Statistics Handler (Lambda)

**責任**: ユーザーの統計データを集計して返却

**主要機能**:
- 完了したAIスキル棚卸し数の取得
- AIポジション／プロジェクト レコメンド数の取得
- 自薦応募数の取得
- プロフィール閲覧数の取得
- 並行データ取得による高速化

**Lambda関数**: `stats-handler`

**API エンドポイント**:
```
GET /stats/{userId}
```

**レスポンス形式**:
```json
{
  "user_id": "string",
  "business_title": "Senior Software Architect",
  "statistics": {
    "completed_questionnaires": 0,
    "received_recommendations": 0,
    "submitted_applications": 0,
    "profile_views": 0
  },
  "last_updated": "2025-11-17T14:30:00Z"
}
```

**実装詳細**:
```python
# src/handlers/stats_handler.py

import boto3
from boto3.dynamodb.conditions import Key
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

ddb = boto3.resource("dynamodb")

def get_user_statistics(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    ユーザーの統計データを取得
    """
    user_id = event["pathParameters"]["userId"]
    
    # 並行でデータ取得
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_questionnaires = executor.submit(count_completed_questionnaires, user_id)
        future_recommendations = executor.submit(count_recommendations, user_id)
        future_applications = executor.submit(count_applications, user_id)
        future_views = executor.submit(get_profile_views, user_id)
        future_business_title = executor.submit(get_business_title, user_id)
        
        stats = {
            "completed_questionnaires": future_questionnaires.result(),
            "received_recommendations": future_recommendations.result(),
            "submitted_applications": future_applications.result(),
            "profile_views": future_views.result()
        }
        
        business_title = future_business_title.result()
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "user_id": user_id,
            "business_title": business_title,
            "statistics": stats,
            "last_updated": datetime.now(timezone.utc).isoformat()
        })
    }

def count_completed_questionnaires(user_id: str) -> int:
    """完了したAIスキル棚卸し数をカウント"""
    table = ddb.Table(f"{PREFIX}-questionnaires")
    response = table.query(
        IndexName="UserIdIndex",
        KeyConditionExpression=Key("user_id").eq(user_id),
        FilterExpression="status = :status",
        ExpressionAttributeValues={":status": "completed"}
    )
    return len(response.get("Items", []))

def count_recommendations(user_id: str) -> int:
    """推薦数をカウント"""
    table = ddb.Table(f"{PREFIX}-recommendations")
    response = table.query(
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    return len(response.get("Items", []))

def count_applications(user_id: str) -> int:
    """自薦応募数をカウント"""
    table = ddb.Table(f"{PREFIX}-applications")
    response = table.query(
        IndexName="UserIdIndex",
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    return len(response.get("Items", []))

def get_profile_views(user_id: str) -> int:
    """プロフィール閲覧数を取得"""
    table = ddb.Table(f"{PREFIX}-veteran-profiles")
    response = table.get_item(Key={"user_id": user_id})
    item = response.get("Item", {})
    return item.get("profile_views", 0)

def get_business_title(user_id: str) -> str:
    """AIスキルポートフォリオ見出しを取得"""
    table = ddb.Table(f"{PREFIX}-veteran-profiles")
    response = table.get_item(Key={"user_id": user_id})
    item = response.get("Item", {})
    return item.get("business_title", "")
```

### 2. Statistics Service (Frontend)

**責任**: バックエンドAPIを呼び出して統計データを取得

**主要機能**:
- 統計データの取得
- エラーハンドリング
- キャッシング（オプション）

**実装詳細**:
```typescript
// frontend/src/services/statisticsService.ts

import { get } from 'aws-amplify/api';
import { fetchAuthSession } from 'aws-amplify/auth';

export interface UserStatistics {
  completed_questionnaires: number;
  received_recommendations: number;
  submitted_applications: number;
  profile_views: number;
}

export interface DashboardData {
  business_title: string;
  statistics: UserStatistics;
}

class StatisticsService {
  async getDashboardData(userId: string): Promise<DashboardData> {
    try {
      const { tokens } = await fetchAuthSession();
      const idToken = tokens?.idToken?.toString();
      
      if (!idToken) {
        throw new Error('Not authenticated');
      }

      const response = await get({
        apiName: 'veteranTalentAPI',
        path: `/stats/${userId}`,
        options: {
          headers: {
            Authorization: `Bearer ${idToken}`,
            'Content-Type': 'application/json',
          },
        },
      }).response;

      const data = (await response.body.json()) as any;
      return {
        business_title: data.business_title || '',
        statistics: data.statistics
      };
    } catch (error) {
      console.error('Get dashboard data error:', error);
      // エラー時はデフォルト値を返す
      return {
        business_title: '',
        statistics: {
          completed_questionnaires: 0,
          received_recommendations: 0,
          submitted_applications: 0,
          profile_views: 0,
        }
      };
    }
  }
  
  // 後方互換性のため残す
  async getUserStatistics(userId: string): Promise<UserStatistics> {
    const data = await this.getDashboardData(userId);
    return data.statistics;
  }
}

export const statisticsService = new StatisticsService();
```

### 3. Dashboard Component (Frontend)

**責任**: 統計データを表示

**主要機能**:
- 統計データの取得と表示
- ローディング状態の管理
- エラーハンドリング

**実装詳細**:
```typescript
// frontend/src/components/dashboard/Dashboard.tsx

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { statisticsService, UserStatistics } from '../../services/statisticsService';

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    if (user && user.role === 'veteran') {
      loadDashboardData();
    }
  }, [user]);

  const loadDashboardData = async () => {
    if (!user) return;
    
    try {
      setLoadingStats(true);
      const data = await statisticsService.getDashboardData(user.user_id);
      setDashboardData(data);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoadingStats(false);
    }
  };

  const renderStatValue = (value: number | undefined) => {
    if (loadingStats) return '...';
    return value !== undefined ? value.toString() : '-';
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>{getWelcomeMessage()}</h1>
        {dashboardData?.business_title && (
          <p className="business-title">{dashboardData.business_title}</p>
        )}
        <p className="dashboard-subtitle">
          あなたのスキルを活かしたAIポジションを見つけましょう
        </p>
      </div>
      
      {/* ... existing quick actions ... */}
      
      <RoleBasedComponent allowedRoles={['veteran']}>
        <div className="dashboard-stats">
          <h2>あなたの統計</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(dashboardData?.statistics.completed_questionnaires)}
              </div>
              <div className="stat-label">完了したAIスキル棚卸し</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(dashboardData?.statistics.received_recommendations)}
              </div>
              <div className="stat-label">受信したレコメンド</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(dashboardData?.statistics.submitted_applications)}
              </div>
              <div className="stat-label">自薦応募した機会</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(dashboardData?.statistics.profile_views)}
              </div>
              <div className="stat-label">プロフィール閲覧数</div>
            </div>
          </div>
        </div>
      </RoleBasedComponent>
    </div>
  );
};
```

## データモデル

### DynamoDB クエリパターン

#### 1. 完了したAIスキル棚卸し数の取得

```python
# UserIdIndex を使用
table.query(
    IndexName="UserIdIndex",
    KeyConditionExpression=Key("user_id").eq(user_id),
    FilterExpression="status = :status",
    ExpressionAttributeValues={":status": "completed"}
)
```

#### 2. 推薦数の取得

```python
# user_id がパーティションキー
table.query(
    KeyConditionExpression=Key("user_id").eq(user_id)
)
```

#### 3. 自薦応募数の取得

```python
# UserIdIndex を使用
table.query(
    IndexName="UserIdIndex",
    KeyConditionExpression=Key("user_id").eq(user_id)
)
```

#### 4. プロフィール閲覧数の取得

```python
# user_id で直接取得
table.get_item(Key={"user_id": user_id})
# profile_views フィールドを参照
```

### プロフィール閲覧数の追跡

プロフィール閲覧数を追跡するため、VeteranProfiles テーブルに `profile_views` フィールドを追加:

```python
# プロフィール閲覧時に呼び出される
def increment_profile_views(user_id: str) -> None:
    table = ddb.Table(f"{PREFIX}-veteran-profiles")
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET profile_views = if_not_exists(profile_views, :zero) + :inc",
        ExpressionAttributeValues={":zero": 0, ":inc": 1}
    )
```

## エラーハンドリング

### エラー分類

1. **認証エラー** (401)
   - 無効なトークン
   - セッション期限切れ

2. **権限エラー** (403)
   - 他のユーザーの統計データへのアクセス試行

3. **データ取得エラー** (500)
   - DynamoDB接続エラー
   - クエリタイムアウト

### 回復戦略

- **部分的失敗**: 一部の統計データ取得に失敗した場合、取得できたデータのみ表示
- **完全失敗**: 全てのデータ取得に失敗した場合、デフォルト値（0または-）を表示
- **リトライ**: 一時的なエラーの場合、最大3回まで自動リトライ

## パフォーマンス最適化

### 並行データ取得

複数のDynamoDBクエリを並行実行することで、レスポンス時間を短縮:

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(count_completed_questionnaires, user_id),
        executor.submit(count_recommendations, user_id),
        executor.submit(count_applications, user_id),
        executor.submit(get_profile_views, user_id)
    ]
    results = [f.result() for f in futures]
```

### キャッシング（オプション）

頻繁にアクセスされる統計データをキャッシュ:

- **TTL**: 5分
- **キャッシュキー**: `stats:{user_id}`
- **無効化**: プロフィール更新、AIスキル棚卸し完了、自薦応募時

### DynamoDB最適化

- **GSI使用**: UserIdIndex を活用して効率的なクエリ
- **Projection**: 必要なフィールドのみ取得
- **BatchGetItem**: 複数アイテムの一括取得（将来的な拡張）

## テスト戦略

### 単体テスト

- Lambda関数の各カウント関数をモックDynamoDBでテスト
- エラーケース（テーブル不在、権限エラー）のテスト
- 並行実行の正確性テスト

### 統合テスト

- 実際のDynamoDBテーブルを使用したエンドツーエンドテスト
- 複数ユーザーの統計データ取得テスト
- パフォーマンステスト（レスポンス時間 < 2秒）

### フロントエンドテスト

- Dashboard コンポーネントのレンダリングテスト
- ローディング状態の表示テスト
- エラー時のフォールバック表示テスト

## スタイリング

### ビジネスタイトル表示

AIスキルポートフォリオ見出しは、ウェルカムメッセージとサブタイトルの間に表示されます：

```css
.business-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: #4a5568;
  margin: 0.5rem 0;
  font-style: italic;
}
```

レイアウト構造：
```
[ウェルカムメッセージ]
[AIスキルポートフォリオ見出し] ← 新規追加
[サブタイトル]
```

## セキュリティ考慮事項

### アクセス制御

- ユーザーは自分の統計データのみアクセス可能
- Cognito認証トークンで user_id を検証
- 管理者は全ユーザーの統計データにアクセス可能（将来的な拡張）

### データプライバシー

- 統計データは集計値のみ（個人情報を含まない）
- ログに機密情報を記録しない
- API レスポンスに不要なデータを含めない
