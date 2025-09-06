import React, { useState } from 'react';
import { Recommendation } from '../../types/profile';
import './OpportunityDetail.css';

interface OpportunityDetailProps {
  recommendation: Recommendation;
  onClose: () => void;
  onApply: (opportunityId: string, notes?: string) => void;
}

const OpportunityDetail: React.FC<OpportunityDetailProps> = ({
  recommendation,
  onClose,
  onApply,
}) => {
  const [showApplicationForm, setShowApplicationForm] = useState(false);
  const [applicationNotes, setApplicationNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { opportunity, match_score, match_reasons, status } = recommendation;

  const handleApply = async () => {
    setIsSubmitting(true);
    try {
      await onApply(opportunity.opportunity_id, applicationNotes);
    } finally {
      setIsSubmitting(false);
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

  return (
    <div className="opportunity-detail-overlay">
      <div className="opportunity-detail-modal">
        <div className="modal-header">
          <div className="header-content">
            <div className="title-section">
              <span className="type-icon">{getTypeIcon()}</span>
              <h2>{opportunity.title}</h2>
            </div>
            <div className="match-score-large">
              <div className={`score-circle-large ${getMatchScoreColor()}`}>
                <span className="score-value">{Math.round(match_score * 100)}%</span>
                <span className="score-label">Match</span>
              </div>
            </div>
          </div>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>

        <div className="modal-content">
          <div className="opportunity-info">
            <div className="company-section">
              <h3>{opportunity.company}</h3>
              <div className="meta-info">
                <span className="location">📍 {opportunity.location}</span>
                <span className={`source-badge source-${opportunity.source}`}>
                  {opportunity.source === 'internal' ? 'Internal Position' : 'External Position'}
                </span>
                <span className="type-badge">{opportunity.type.replace('_', ' ')}</span>
              </div>
            </div>

            <div className="salary-section">
              <h4>💰 Compensation</h4>
              <p className="salary-range">{formatSalaryRange()}</p>
            </div>

            <div className="description-section">
              <h4>📋 Job Description</h4>
              <div className="description-content">
                {opportunity.description.split('\n').map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
            </div>

            <div className="skills-section">
              <h4>🎯 Required Skills</h4>
              <div className="skills-grid">
                {opportunity.required_skills.map((skill, index) => (
                  <span key={index} className="skill-tag-large">{skill}</span>
                ))}
              </div>
            </div>

            <div className="match-analysis-section">
              <h4>🤖 AI Match Analysis</h4>
              <div className="match-reasons-detailed">
                {match_reasons
                  .sort((a, b) => b.weight - a.weight)
                  .map((reason, index) => (
                    <div key={index} className="match-reason-detailed">
                      <div className="reason-header">
                        <span className="reason-category">{reason.category}</span>
                        <span className="reason-weight">
                          {Math.round(reason.weight * 100)}% relevance
                        </span>
                      </div>
                      <p className="reason-description">{reason.description}</p>
                    </div>
                  ))}
              </div>
            </div>

            <div className="timeline-section">
              <h4>📅 Timeline</h4>
              <div className="timeline-info">
                <p><strong>Posted:</strong> {new Date(opportunity.posted_date).toLocaleDateString()}</p>
                {opportunity.expiry_date && (
                  <p><strong>Application Deadline:</strong> {new Date(opportunity.expiry_date).toLocaleDateString()}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="modal-actions">
          {status === 'applied' ? (
            <div className="applied-status">
              <span className="applied-badge">✅ Application Submitted</span>
              <p>Applied on {recommendation.applied_at ? new Date(recommendation.applied_at).toLocaleDateString() : 'Unknown'}</p>
            </div>
          ) : (
            <>
              {!showApplicationForm ? (
                <div className="action-buttons">
                  <button 
                    className="apply-button"
                    onClick={() => setShowApplicationForm(true)}
                  >
                    Apply for This Position
                  </button>
                  <button 
                    className="interest-button"
                    onClick={() => handleApply()}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'Submitting...' : 'Express Interest'}
                  </button>
                </div>
              ) : (
                <div className="application-form">
                  <h4>Application Notes (Optional)</h4>
                  <textarea
                    value={applicationNotes}
                    onChange={(e) => setApplicationNotes(e.target.value)}
                    placeholder="Add any additional notes or comments about your interest in this position..."
                    rows={4}
                    className="application-notes"
                  />
                  <div className="form-actions">
                    <button 
                      className="submit-application-button"
                      onClick={handleApply}
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? 'Submitting Application...' : 'Submit Application'}
                    </button>
                    <button 
                      className="cancel-button"
                      onClick={() => setShowApplicationForm(false)}
                      disabled={isSubmitting}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default OpportunityDetail;