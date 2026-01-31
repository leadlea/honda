import React from 'react';
import { Recommendation } from '../../types/profile';
import { termMappingService } from '../../services/termMappingService';
import './RecommendationCard.css';

interface RecommendationCardProps {
  recommendation: Recommendation;
  onView: () => void;
  onDismiss: () => void;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onView,
  onDismiss,
}) => {
  const { opportunity, match_score, match_reasons, status } = recommendation;

  const getStatusBadge = () => {
    switch (status) {
      case 'generated':
        return <span className="status-badge new">新着</span>;
      case 'viewed':
        return <span className="status-badge viewed">確認済み</span>;
      case 'applied':
        return <span className="status-badge applied">{termMappingService.mapLegacyTerm('応募')}済み</span>;
      default:
        return null;
    }
  };

  const getTypeIcon = () => {
    switch (opportunity.type) {
      case 'internal_transfer':
        return '🏢';
      case 'external_position':
        return '🌐';
      case 'consulting':
        return '💼';
      case 'project_based':
        return '📋';
      default:
        return '💼';
    }
  };

  const formatSalaryRange = () => {
    const { min, max, currency } = opportunity.salary_range;
    if (min === 0 && max === 0) return '給与情報なし';
    
    const formatter = new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: currency || 'JPY',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    });

    if (min === max) return formatter.format(min);
    return `${formatter.format(min)} - ${formatter.format(max)}`;
  };

  const getMatchScoreColor = () => {
    if (match_score >= 0.8) return 'excellent';
    if (match_score >= 0.6) return 'good';
    if (match_score >= 0.4) return 'fair';
    return 'poor';
  };

  const topMatchReasons = match_reasons
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 3);

  return (
    <div className={`recommendation-card ${status}`}>
      <div className="card-header">
        <div className="title-section">
          <span className="type-icon">{getTypeIcon()}</span>
          <h3 className="opportunity-title">{opportunity.title}</h3>
          {getStatusBadge()}
        </div>
        
        <div className="match-score">
          <div className={`score-circle ${getMatchScoreColor()}`}>
            <span className="score-value">{Math.round(match_score * 100)}%</span>
            <span className="score-label">Match</span>
          </div>
        </div>
      </div>

      <div className="card-content">
        <div className="company-info">
          <strong>{opportunity.company}</strong>
          <span className="location">📍 {opportunity.location}</span>
        </div>

        <div className="opportunity-meta">
          <span className="source-badge source-{opportunity.source}">
            {opportunity.source === 'internal' ? '社内' : '社外'}
          </span>
          <span className="type-badge">{opportunity.type.replace('_', ' ')}</span>
        </div>

        <p className="description">
          {opportunity.description.length > 150
            ? `${opportunity.description.substring(0, 150)}...`
            : opportunity.description}
        </p>

        <div className="salary-info">
          <strong>💰 {formatSalaryRange()}</strong>
        </div>

        <div className="match-reasons">
          <h4>あなたにマッチする理由:</h4>
          <ul>
            {topMatchReasons.map((reason, index) => (
              <li key={index} className="match-reason">
                <span className="reason-category">{reason.category}:</span>
                <span className="reason-description">{reason.description}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="required-skills">
          <h4>必要なスキル:</h4>
          <div className="skills-tags">
            {opportunity.required_skills.slice(0, 5).map((skill, index) => (
              <span key={index} className="skill-tag">{skill}</span>
            ))}
            {opportunity.required_skills.length > 5 && (
              <span className="skill-tag more">+{opportunity.required_skills.length - 5} 他</span>
            )}
          </div>
        </div>
      </div>

      <div className="card-actions">
        <button 
          className="view-details-button"
          onClick={onView}
        >
          詳細を見る
        </button>
        
        {status !== 'applied' && (
          <button 
            className="dismiss-button"
            onClick={onDismiss}
            title={`この${termMappingService.mapLegacyTerm('推薦')}を却下`}
          >
            ✕
          </button>
        )}
      </div>

      <div className="card-footer">
        <small>
          投稿日: {new Date(opportunity.posted_date).toLocaleDateString('ja-JP')}
          {opportunity.expiry_date && (
            <span> • 期限: {new Date(opportunity.expiry_date).toLocaleDateString('ja-JP')}</span>
          )}
        </small>
      </div>
    </div>
  );
};

export default RecommendationCard;