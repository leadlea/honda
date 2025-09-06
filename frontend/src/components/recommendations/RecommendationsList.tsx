import React, { useState, useEffect } from 'react';
import { Recommendation } from '../../types/profile';
import { RecommendationService } from '../../services/recommendationService';
import { useAuth } from '../../contexts/AuthContext';
import RecommendationCard from './RecommendationCard';
import OpportunityDetail from './OpportunityDetail';
import './RecommendationsList.css';

const RecommendationsList: React.FC = () => {
  const { user } = useAuth();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRecommendation, setSelectedRecommendation] = useState<Recommendation | null>(null);
  const [filter, setFilter] = useState<'all' | 'internal' | 'external'>('all');
  const [sortBy, setSortBy] = useState<'match_score' | 'date'>('match_score');

  useEffect(() => {
    if (user?.user_id) {
      loadRecommendations();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const loadRecommendations = async () => {
    if (!user?.user_id) return;

    try {
      setLoading(true);
      setError(null);
      const data = await RecommendationService.getRecommendations(user.user_id);
      setRecommendations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  };

  const handleViewRecommendation = async (recommendation: Recommendation) => {
    try {
      if (recommendation.status === 'generated') {
        await RecommendationService.markRecommendationAsViewed(recommendation.recommendation_id);
        setRecommendations(prev =>
          prev.map(r =>
            r.recommendation_id === recommendation.recommendation_id
              ? { ...r, status: 'viewed', viewed_at: new Date().toISOString() }
              : r
          )
        );
      }
      setSelectedRecommendation(recommendation);
    } catch (err) {
      console.error('Error marking recommendation as viewed:', err);
      setSelectedRecommendation(recommendation);
    }
  };

  const handleDismissRecommendation = async (recommendationId: string) => {
    try {
      await RecommendationService.dismissRecommendation(recommendationId);
      setRecommendations(prev =>
        prev.map(r =>
          r.recommendation_id === recommendationId
            ? { ...r, status: 'dismissed' }
            : r
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to dismiss recommendation');
    }
  };

  const handleApplyToOpportunity = async (opportunityId: string, notes?: string) => {
    if (!user?.user_id) return;

    try {
      await RecommendationService.applyToOpportunity(user.user_id, opportunityId, notes);
      
      // Update recommendation status
      setRecommendations(prev =>
        prev.map(r =>
          r.opportunity_id === opportunityId
            ? { ...r, status: 'applied', applied_at: new Date().toISOString() }
            : r
        )
      );

      // Close detail view
      setSelectedRecommendation(null);
      
      // Show success message
      alert('Application submitted successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply to opportunity');
    }
  };

  const filteredRecommendations = recommendations
    .filter(r => {
      if (r.status === 'dismissed') return false;
      if (filter === 'all') return true;
      return r.opportunity.source === filter;
    })
    .sort((a, b) => {
      if (sortBy === 'match_score') {
        return b.match_score - a.match_score;
      }
      return new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime();
    });

  if (loading) {
    return (
      <div className="recommendations-loading">
        <div className="loading-spinner"></div>
        <p>Loading your personalized recommendations...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recommendations-error">
        <h3>Error Loading Recommendations</h3>
        <p>{error}</p>
        <button onClick={loadRecommendations} className="retry-button">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="recommendations-container">
      <div className="recommendations-header">
        <h2>Recommended Opportunities</h2>
        <p>AI-powered recommendations based on your profile and preferences</p>
        
        <div className="recommendations-controls">
          <div className="filter-controls">
            <label>Filter by source:</label>
            <select value={filter} onChange={(e) => setFilter(e.target.value as any)}>
              <option value="all">All Opportunities</option>
              <option value="internal">Internal Only</option>
              <option value="external">External Only</option>
            </select>
          </div>
          
          <div className="sort-controls">
            <label>Sort by:</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
              <option value="match_score">Match Score</option>
              <option value="date">Date Generated</option>
            </select>
          </div>
        </div>
      </div>

      {filteredRecommendations.length === 0 ? (
        <div className="no-recommendations">
          <h3>No Recommendations Available</h3>
          <p>
            We're working on finding opportunities that match your profile. 
            Check back later or update your profile to get better recommendations.
          </p>
          <button onClick={loadRecommendations} className="refresh-button">
            Refresh Recommendations
          </button>
        </div>
      ) : (
        <div className="recommendations-grid">
          {filteredRecommendations.map((recommendation) => (
            <RecommendationCard
              key={recommendation.recommendation_id}
              recommendation={recommendation}
              onView={() => handleViewRecommendation(recommendation)}
              onDismiss={() => handleDismissRecommendation(recommendation.recommendation_id)}
            />
          ))}
        </div>
      )}

      {selectedRecommendation && (
        <OpportunityDetail
          recommendation={selectedRecommendation}
          onClose={() => setSelectedRecommendation(null)}
          onApply={handleApplyToOpportunity}
        />
      )}
    </div>
  );
};

export default RecommendationsList;