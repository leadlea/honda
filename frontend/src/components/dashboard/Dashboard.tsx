import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import RoleBasedComponent from '../common/RoleBasedComponent';
import { statisticsService } from '../../services/statisticsService';
import { UserStatistics } from '../../types/profile';
import './Dashboard.css';

interface DashboardProps {
  onNavigate: (page: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const { user } = useAuth();
  const [statistics, setStatistics] = useState<UserStatistics | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    if (user && user.role === 'veteran') {
      loadStatistics();
    }
  }, [user]);

  const loadStatistics = async () => {
    if (!user) {
      console.log('[Dashboard] No user available, skipping statistics load');
      return;
    }
    
    console.log('[Dashboard] Loading statistics for user:', user.user_id);
    try {
      setLoadingStats(true);
      const stats = await statisticsService.getUserStatistics(user.user_id);
      console.log('[Dashboard] Statistics loaded:', stats);
      setStatistics(stats);
    } catch (error) {
      console.error('[Dashboard] Failed to load statistics:', error);
    } finally {
      setLoadingStats(false);
    }
  };

  const renderStatValue = (value: number | undefined) => {
    console.log('[Dashboard] renderStatValue called with:', value, 'loadingStats:', loadingStats);
    if (loadingStats) return '...';
    return value !== undefined ? value.toString() : '-';
  };

  if (!user) {
    return <div className="dashboard-loading">ダッシュボードを読み込み中...</div>;
  }

  const quickActions = [
    {
      title: 'AI問診を受ける',
      description: 'あなたのスキルと興味を評価するためのAI生成問診',
      action: () => onNavigate('questionnaire'),
      roles: ['veteran'] as const,
      color: 'blue',
    },
    {
      title: 'プロフィール管理',
      description: 'あなたの詳細プロフィールを編集・管理',
      action: () => onNavigate('profile'),
      roles: ['veteran'] as const,
      color: 'green',
    },
    {
      title: '推薦機会を見る',
      description: 'あなたに合った機会の推薦を確認',
      action: () => onNavigate('recommendations'),
      roles: ['veteran'] as const,
      color: 'purple',
    },
    {
      title: '応募状況を確認',
      description: 'あなたの応募状況と進捗を追跡',
      action: () => onNavigate('applications'),
      roles: ['veteran'] as const,
      color: 'teal',
    },
    {
      title: 'ベテラン検索',
      description: '公開されているベテランプロフィールを検索',
      action: () => onNavigate('public-search'),
      roles: ['external_recruiter'] as const,
      color: 'orange',
    },
    {
      title: 'システム管理',
      description: 'ユーザーと機会の管理',
      action: () => onNavigate('admin'),
      roles: ['admin'] as const,
      color: 'red',
    },
  ];

  const getWelcomeMessage = () => {
    switch (user.role) {
      case 'admin':
        return `管理者として${user.name}さん、おかえりなさい`;
      case 'external_recruiter':
        return `${user.name}さん、Honda Veteran Talent Bankへようこそ`;
      default:
        return `${user.name}さん、おかえりなさい`;
    }
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>{getWelcomeMessage()}</h1>
        <p className="dashboard-subtitle">
          {user.role === 'veteran' && 'あなたのスキルを活かした新しい機会を見つけましょう'}
          {user.role === 'external_recruiter' && '経験豊富なベテラン人材を見つけましょう'}
          {user.role === 'admin' && 'システムの管理と監視を行いましょう'}
        </p>
      </div>

      <div className="quick-actions">
        <h2>クイックアクション</h2>
        <div className="actions-grid">
          {quickActions.map((action, index) => (
            <RoleBasedComponent key={index} allowedRoles={action.roles}>
              <div
                className={`action-card ${action.color}`}
                onClick={action.action}
              >
                <h3>{action.title}</h3>
                <p>{action.description}</p>
                <div className="action-arrow">→</div>
              </div>
            </RoleBasedComponent>
          ))}
        </div>
      </div>

      <RoleBasedComponent allowedRoles={['veteran']}>
        <div className="dashboard-stats">
          <h2>あなたの統計</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(statistics?.completed_questionnaires)}
              </div>
              <div className="stat-label">完了した問診</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(statistics?.received_recommendations)}
              </div>
              <div className="stat-label">受信した推薦</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(statistics?.submitted_applications)}
              </div>
              <div className="stat-label">応募した機会</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(statistics?.profile_views)}
              </div>
              <div className="stat-label">プロフィール閲覧数</div>
            </div>
          </div>
        </div>
      </RoleBasedComponent>

      <RoleBasedComponent allowedRoles={['external_recruiter']}>
        <div className="dashboard-stats">
          <h2>検索統計</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-number">-</div>
              <div className="stat-label">利用可能なベテラン</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">-</div>
              <div className="stat-label">今月の検索数</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">-</div>
              <div className="stat-label">連絡したベテラン</div>
            </div>
          </div>
        </div>
      </RoleBasedComponent>
    </div>
  );
};

export default Dashboard;