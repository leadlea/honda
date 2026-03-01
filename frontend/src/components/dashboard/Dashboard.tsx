import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import RoleBasedComponent from '../common/RoleBasedComponent';
import { statisticsService } from '../../services/statisticsService';
import { UserStatistics } from '../../types/profile';
import { termMappingService } from '../../services/termMappingService';
import { getBrandedMessage, applyBrandingTone } from '../../utils/brandingUtils';
import './Dashboard.css';

interface DashboardProps {
  onNavigate: (page: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const { user } = useAuth();
  const [statistics, setStatistics] = useState<UserStatistics | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  const loadStatistics = useCallback(async () => {
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
  }, [user]);

  useEffect(() => {
    if (user && user.role === 'veteran') {
      loadStatistics();
    }
  }, [user, loadStatistics]);

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
      title: getBrandedMessage('questionnaire', 'title'),
      description: getBrandedMessage('questionnaire', 'helpText'),
      action: () => onNavigate('questionnaire'),
      roles: ['veteran'] as const,
      color: 'blue',
    },
    {
      title: getBrandedMessage('profile', 'title'),
      description: applyBrandingTone('あなたのAIスキルポートフォリオを編集・管理'),
      action: () => onNavigate('profile'),
      roles: ['veteran'] as const,
      color: 'green',
    },
    {
      title: getBrandedMessage('recommendations', 'title'),
      description: getBrandedMessage('recommendations', 'subtitle'),
      action: () => onNavigate('recommendations'),
      roles: ['veteran'] as const,
      color: 'purple',
    },
    {
      title: getBrandedMessage('applications', 'title'),
      description: getBrandedMessage('applications', 'subtitle'),
      action: () => onNavigate('applications'),
      roles: ['veteran'] as const,
      color: 'teal',
    },
    {
      title: getBrandedMessage('search', 'title'),
      description: getBrandedMessage('search', 'subtitle'),
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
    const brandedWelcome = getBrandedMessage('welcome', 'title');
    switch (user.role) {
      case 'admin':
        return `管理者として${user.name}さん、${brandedWelcome}`;
      case 'external_recruiter':
        return `${user.name}さん、${brandedWelcome}`;
      default:
        return `${user.name}さん、おかえりなさい`;
    }
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>{getWelcomeMessage()}</h1>
        <p className="dashboard-subtitle">
          {user.role === 'veteran' && applyBrandingTone('あなたのAIスキルを活かした最適なAIポジションを見つけましょう', 'trustworthy_internal')}
          {user.role === 'external_recruiter' && getBrandedMessage('search', 'subtitle')}
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
          <h2>あなたのAI活動統計</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(statistics?.completed_questionnaires)}
              </div>
              <div className="stat-label">完了した{termMappingService.getLocalizedTerm('navigation_questionnaire')}</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(statistics?.received_recommendations)}
              </div>
              <div className="stat-label">受信した{termMappingService.mapLegacyTerm('推薦')}</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(statistics?.submitted_applications)}
              </div>
              <div className="stat-label">{termMappingService.mapLegacyTerm('応募')}した機会</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {renderStatValue(statistics?.profile_views)}
              </div>
              <div className="stat-label">AIスキルポートフォリオ閲覧数</div>
            </div>
          </div>
        </div>
      </RoleBasedComponent>

      <RoleBasedComponent allowedRoles={['external_recruiter']}>
        <div className="dashboard-stats">
          <h2>社内AI人材候補検索統計</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-number">-</div>
              <div className="stat-label">利用可能な{termMappingService.getLocalizedTerm('navigation_talent')}</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">-</div>
              <div className="stat-label">今月の検索数</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">-</div>
              <div className="stat-label">連絡した{termMappingService.getLocalizedTerm('navigation_talent')}</div>
            </div>
          </div>
        </div>
      </RoleBasedComponent>
    </div>
  );
};

export default Dashboard;