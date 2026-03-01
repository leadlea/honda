import React, { useState, useEffect } from 'react';
import { Application } from '../../types/profile';
import { RecommendationService } from '../../services/recommendationService';
import { useAuth } from '../../contexts/AuthContext';
import { termMappingService } from '../../services/termMappingService';
import './ApplicationTracker.css';

const ApplicationTracker: React.FC = () => {
  const { user } = useAuth();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  useEffect(() => {
    if (user?.user_id) {
      loadApplications();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const loadApplications = async () => {
    if (!user?.user_id) return;

    try {
      setLoading(true);
      setError(null);
      const data = await RecommendationService.getApplications(user.user_id);
      setApplications(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '自薦応募の読み込みに失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleWithdrawApplication = async (applicationId: string) => {
    if (!window.confirm('この自薦応募を取り下げてもよろしいですか？')) {
      return;
    }

    try {
      await RecommendationService.withdrawApplication(applicationId);
      setApplications(prev =>
        prev.map(app =>
          app.application_id === applicationId
            ? { ...app, status: 'withdrawn', updated_at: new Date().toISOString() }
            : app
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : '自薦応募の取り下げに失敗しました');
    }
  };

  const getStatusIcon = (status: Application['status']) => {
    switch (status) {
      case 'submitted':
        return '📤';
      case 'under_review':
        return '👀';
      case 'interview_scheduled':
        return '📅';
      case 'accepted':
        return '✅';
      case 'rejected':
        return '❌';
      case 'withdrawn':
        return '↩️';
      default:
        return '📋';
    }
  };

  const getStatusColor = (status: Application['status']) => {
    switch (status) {
      case 'submitted':
        return 'blue';
      case 'under_review':
        return 'orange';
      case 'interview_scheduled':
        return 'purple';
      case 'accepted':
        return 'green';
      case 'rejected':
        return 'red';
      case 'withdrawn':
        return 'gray';
      default:
        return 'blue';
    }
  };

  const formatStatus = (status: Application['status']) => {
    const statusMap: Record<Application['status'], string> = {
      'submitted': '自薦応募済み',
      'under_review': '審査中',
      'interview_scheduled': '面接予定',
      'accepted': '承認',
      'rejected': '不採用',
      'withdrawn': '取り下げ'
    };
    return statusMap[status] || status;
  };

  const filteredApplications = applications.filter(app => {
    if (filter === 'all') return true;
    if (filter === 'active') {
      return !['accepted', 'rejected', 'withdrawn'].includes(app.status);
    }
    if (filter === 'completed') {
      return ['accepted', 'rejected', 'withdrawn'].includes(app.status);
    }
    return true;
  });

  const sortedApplications = filteredApplications.sort((a, b) => 
    new Date(b.applied_at).getTime() - new Date(a.applied_at).getTime()
  );

  if (loading) {
    return (
      <div className="applications-loading">
        <div className="loading-spinner"></div>
        <p>あなたの自薦応募を読み込み中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="applications-error">
        <h3>自薦応募の読み込みエラー</h3>
        <p>{error}</p>
        <button onClick={loadApplications} className="retry-button">
          再試行
        </button>
      </div>
    );
  }

  return (
    <div className="applications-container">
      <div className="applications-header">
        <h2>私の自薦応募</h2>
        <p>自薦応募状況を追跡します</p>
        
        <div className="applications-controls">
          <div className="filter-controls">
            <label>ステータスでフィルター:</label>
            <select value={filter} onChange={(e) => setFilter(e.target.value as any)}>
              <option value="all">すべての自薦応募</option>
              <option value="active">進行中の自薦応募</option>
              <option value="completed">完了した自薦応募</option>
            </select>
          </div>
          
          <button onClick={loadApplications} className="refresh-button">
            更新
          </button>
        </div>
      </div>

      {sortedApplications.length === 0 ? (
        <div className="no-applications">
          <h3>自薦応募が見つかりません</h3>
          <p>
            {filter === 'all' 
              ? `まだ機会に自薦応募していません。${termMappingService.getLocalizedTerm('navigation_recommendations')}をチェックして適切なポジションを見つけましょう！`
              : `${filter === 'active' ? '進行中' : '完了した'}の自薦応募が見つかりません。`
            }
          </p>
        </div>
      ) : (
        <div className="applications-list">
          {sortedApplications.map((application) => (
            <div key={application.application_id} className="application-card">
              <div className="application-header">
                <div className="opportunity-info">
                  <h3>{application.opportunity.title}</h3>
                  <p className="company-name">{application.opportunity.company}</p>
                  <span className="location">📍 {application.opportunity.location}</span>
                </div>
                
                <div className="status-section">
                  <span className={`status-badge status-${getStatusColor(application.status)}`}>
                    {getStatusIcon(application.status)} {formatStatus(application.status)}
                  </span>
                </div>
              </div>

              <div className="application-content">
                <div className="opportunity-meta">
                  <span className={`source-badge source-${application.opportunity.source}`}>
                    {application.opportunity.source === 'internal' ? '社内' : '社外'}
                  </span>
                  <span className="type-badge">
                    {application.opportunity.type.replace('_', ' ')}
                  </span>
                </div>

                <div className="timeline">
                  <div className="timeline-item">
                    <strong>自薦応募日:</strong> {new Date(application.applied_at).toLocaleDateString('ja-JP')}
                  </div>
                  <div className="timeline-item">
                    <strong>最終更新:</strong> {new Date(application.updated_at).toLocaleDateString('ja-JP')}
                  </div>
                </div>

                {application.notes && (
                  <div className="application-notes">
                    <h4>あなたのメモ:</h4>
                    <p>{application.notes}</p>
                  </div>
                )}

                <div className="opportunity-summary">
                  <p>{application.opportunity.description.substring(0, 200)}...</p>
                </div>
              </div>

              <div className="application-actions">
                {application.status === 'submitted' || application.status === 'under_review' ? (
                  <button 
                    className="withdraw-button"
                    onClick={() => handleWithdrawApplication(application.application_id)}
                  >
                    自薦応募を取り下げ
                  </button>
                ) : null}
                
                <div className="application-id">
                  <small>自薦応募ID: {application.application_id}</small>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="applications-summary">
        <div className="summary-stats">
          <div className="stat-item">
            <span className="stat-number">{applications.length}</span>
            <span className="stat-label">総自薦応募数</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">
              {applications.filter(app => !['accepted', 'rejected', 'withdrawn'].includes(app.status)).length}
            </span>
            <span className="stat-label">進行中の自薦応募</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">
              {applications.filter(app => app.status === 'accepted').length}
            </span>
            <span className="stat-label">承認済み</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApplicationTracker;