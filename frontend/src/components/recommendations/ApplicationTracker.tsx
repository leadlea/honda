import React, { useState, useEffect } from 'react';
import { Application } from '../../types/profile';
import { RecommendationService } from '../../services/recommendationService';
import { useAuth } from '../../contexts/AuthContext';
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
      setError(err instanceof Error ? err.message : 'Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  const handleWithdrawApplication = async (applicationId: string) => {
    if (!window.confirm('Are you sure you want to withdraw this application?')) {
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
      setError(err instanceof Error ? err.message : 'Failed to withdraw application');
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
    return status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
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
        <p>Loading your applications...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="applications-error">
        <h3>Error Loading Applications</h3>
        <p>{error}</p>
        <button onClick={loadApplications} className="retry-button">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="applications-container">
      <div className="applications-header">
        <h2>My Applications</h2>
        <p>Track the status of your job applications</p>
        
        <div className="applications-controls">
          <div className="filter-controls">
            <label>Filter by status:</label>
            <select value={filter} onChange={(e) => setFilter(e.target.value as any)}>
              <option value="all">All Applications</option>
              <option value="active">Active Applications</option>
              <option value="completed">Completed Applications</option>
            </select>
          </div>
          
          <button onClick={loadApplications} className="refresh-button">
            Refresh
          </button>
        </div>
      </div>

      {sortedApplications.length === 0 ? (
        <div className="no-applications">
          <h3>No Applications Found</h3>
          <p>
            {filter === 'all' 
              ? "You haven't applied to any opportunities yet. Check out your recommendations to find suitable positions!"
              : `No ${filter} applications found.`
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
                    {application.opportunity.source === 'internal' ? 'Internal' : 'External'}
                  </span>
                  <span className="type-badge">
                    {application.opportunity.type.replace('_', ' ')}
                  </span>
                </div>

                <div className="timeline">
                  <div className="timeline-item">
                    <strong>Applied:</strong> {new Date(application.applied_at).toLocaleDateString()}
                  </div>
                  <div className="timeline-item">
                    <strong>Last Updated:</strong> {new Date(application.updated_at).toLocaleDateString()}
                  </div>
                </div>

                {application.notes && (
                  <div className="application-notes">
                    <h4>Your Notes:</h4>
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
                    Withdraw Application
                  </button>
                ) : null}
                
                <div className="application-id">
                  <small>Application ID: {application.application_id}</small>
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
            <span className="stat-label">Total Applications</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">
              {applications.filter(app => !['accepted', 'rejected', 'withdrawn'].includes(app.status)).length}
            </span>
            <span className="stat-label">Active Applications</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">
              {applications.filter(app => app.status === 'accepted').length}
            </span>
            <span className="stat-label">Accepted</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApplicationTracker;