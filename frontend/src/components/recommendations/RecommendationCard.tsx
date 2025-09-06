import React from 'react';
import { Recommendation } from '../../types/profile';
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
        return <span className="status-badge new">New</span>;
      case 'viewed':
        return <span className="status-badge viewed">Viewed</span>;
      case 'applied':
        return <span className="status-badge applied">Applied</span>;
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
    if (min === 0 && max === 0) return 'Salary not specified';
    
    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
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
            {opportunity.source === 'internal' ? 'Internal' : 'External'}
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
          <h4>Why this matches you:</h4>
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
          <h4>Key Skills Required:</h4>
          <div className="skills-tags">
            {opportunity.required_skills.slice(0, 5).map((skill, index) => (
              <span key={index} className="skill-tag">{skill}</span>
            ))}
            {opportunity.required_skills.length > 5 && (
              <span className="skill-tag more">+{opportunity.required_skills.length - 5} more</span>
            )}
          </div>
        </div>
      </div>

      <div className="card-actions">
        <button 
          className="view-details-button"
          onClick={onView}
        >
          View Details
        </button>
        
        {status !== 'applied' && (
          <button 
            className="dismiss-button"
            onClick={onDismiss}
            title="Dismiss this recommendation"
          >
            ✕
          </button>
        )}
      </div>

      <div className="card-footer">
        <small>
          Posted: {new Date(opportunity.posted_date).toLocaleDateString()}
          {opportunity.expiry_date && (
            <span> • Expires: {new Date(opportunity.expiry_date).toLocaleDateString()}</span>
          )}
        </small>
      </div>
    </div>
  );
};

export default RecommendationCard;