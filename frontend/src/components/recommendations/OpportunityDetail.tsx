import React, { useState } from 'react';
import { Recommendation } from '../../types/profile';
import { termMappingService } from '../../services/termMappingService';
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
                  {opportunity.source === 'internal' ? '社内ポジション' : '社外ポジション'}
                </span>
                <span className="type-badge">{opportunity.type.replace('_', ' ')}</span>
              </div>
            </div>

            <div className="salary-section">
              <h4>💰 報酬</h4>
              <p className="salary-range">{formatSalaryRange()}</p>
            </div>

            <div className="description-section">
              <h4>📋 職務内容</h4>
              <div className="description-content">
                {opportunity.description.split('\n').map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
            </div>

            <div className="skills-section">
              <h4>🎯 必要スキル</h4>
              <div className="skills-grid">
                {opportunity.required_skills.map((skill, index) => (
                  <span key={index} className="skill-tag-large">{skill}</span>
                ))}
              </div>
            </div>

            <div className="match-analysis-section">
              <h4>🤖 AIマッチ分析</h4>
              <div className="match-reasons-detailed">
                {match_reasons
                  .sort((a, b) => b.weight - a.weight)
                  .map((reason, index) => (
                    <div key={index} className="match-reason-detailed">
                      <div className="reason-header">
                        <span className="reason-category">{reason.category}</span>
                        <span className="reason-weight">
                          {Math.round(reason.weight * 100)}% 関連性
                        </span>
                      </div>
                      <p className="reason-description">{reason.description}</p>
                    </div>
                  ))}
              </div>
            </div>

            <div className="timeline-section">
              <h4>📅 スケジュール</h4>
              <div className="timeline-info">
                <p><strong>投稿日:</strong> {new Date(opportunity.posted_date).toLocaleDateString('ja-JP')}</p>
                {opportunity.expiry_date && (
                  <p><strong>{termMappingService.mapLegacyTerm('応募')}締切:</strong> {new Date(opportunity.expiry_date).toLocaleDateString('ja-JP')}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="modal-actions">
          {status === 'applied' ? (
            <div className="applied-status">
              <span className="applied-badge">✅ {termMappingService.mapLegacyTerm('応募')}済み</span>
              <p>{termMappingService.mapLegacyTerm('応募')}日: {recommendation.applied_at ? new Date(recommendation.applied_at).toLocaleDateString('ja-JP') : '不明'}</p>
            </div>
          ) : (
            <>
              {!showApplicationForm ? (
                <div className="action-buttons">
                  <button 
                    className="apply-button"
                    onClick={() => setShowApplicationForm(true)}
                  >
                    このポジションに{termMappingService.mapLegacyTerm('応募')}
                  </button>
                  <button 
                    className="interest-button"
                    onClick={() => handleApply()}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? '送信中...' : termMappingService.mapLegacyTerm('興味表明')}
                  </button>
                </div>
              ) : (
                <div className="application-form">
                  <h4>{termMappingService.mapLegacyTerm('応募')}メモ（任意）</h4>
                  <textarea
                    value={applicationNotes}
                    onChange={(e) => setApplicationNotes(e.target.value)}
                    placeholder="このポジションへの関心について追加のメモやコメントを記入してください..."
                    rows={4}
                    className="application-notes"
                  />
                  <div className="form-actions">
                    <button 
                      className="submit-application-button"
                      onClick={handleApply}
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? `${termMappingService.mapLegacyTerm('応募')}送信中...` : `${termMappingService.mapLegacyTerm('応募')}を送信`}
                    </button>
                    <button 
                      className="cancel-button"
                      onClick={() => setShowApplicationForm(false)}
                      disabled={isSubmitting}
                    >
                      キャンセル
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