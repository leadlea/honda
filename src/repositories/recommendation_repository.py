"""
Recommendation repository for DynamoDB operations
"""
import os
from typing import List, Optional
from datetime import datetime
import logging

from .base_repository import BaseRepository
from ..models.recommendation import Recommendation

logger = logging.getLogger(__name__)


class RecommendationRepository(BaseRepository):
    """Repository for recommendation operations"""
    
    def __init__(self):
        table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX', 'honda-veteran-talent-matching-dev')}-recommendations"
        super().__init__(table_name)
    
    def create_recommendation(self, recommendation: Recommendation) -> bool:
        """Create a new recommendation"""
        try:
            # Validate recommendation before saving
            errors = recommendation.validate()
            if errors:
                raise ValueError(f"Recommendation validation failed: {', '.join(errors)}")
            
            item = recommendation.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error creating recommendation: {e}")
            raise
    
    def get_recommendation(self, user_id: str, recommendation_id: str) -> Optional[Recommendation]:
        """Get recommendation by user ID and recommendation ID"""
        try:
            item = self.get_item({
                'user_id': user_id,
                'recommendation_id': recommendation_id
            })
            if item:
                return Recommendation.from_dynamodb_item(item)
            return None
        except Exception as e:
            logger.error(f"Error getting recommendation {recommendation_id} for user {user_id}: {e}")
            raise
    
    def update_recommendation(self, recommendation: Recommendation) -> bool:
        """Update an existing recommendation"""
        try:
            # Validate recommendation before updating
            errors = recommendation.validate()
            if errors:
                raise ValueError(f"Recommendation validation failed: {', '.join(errors)}")
            
            item = recommendation.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error updating recommendation: {e}")
            raise
    
    def delete_recommendation(self, user_id: str, recommendation_id: str) -> bool:
        """Delete a recommendation"""
        try:
            return self.delete_item({
                'user_id': user_id,
                'recommendation_id': recommendation_id
            })
        except Exception as e:
            logger.error(f"Error deleting recommendation {recommendation_id} for user {user_id}: {e}")
            raise
    
    def get_user_recommendations(self, user_id: str, limit: Optional[int] = None) -> List[Recommendation]:
        """Get all recommendations for a user"""
        try:
            items = self.query(
                key_condition_expression='user_id = :user_id',
                expression_attribute_values={':user_id': user_id},
                limit=limit,
                scan_index_forward=False  # Most recent first
            )
            return [Recommendation.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {e}")
            raise
    
    def get_user_recommendations_by_status(self, user_id: str, status: str, limit: Optional[int] = None) -> List[Recommendation]:
        """Get user recommendations filtered by status"""
        try:
            items = self.query(
                key_condition_expression='user_id = :user_id',
                expression_attribute_values={':user_id': user_id},
                limit=limit,
                scan_index_forward=False
            )
            
            # Filter by status (DynamoDB doesn't support filtering on sort key in query)
            filtered_recommendations = []
            for item in items:
                recommendation = Recommendation.from_dynamodb_item(item)
                if recommendation.status == status:
                    filtered_recommendations.append(recommendation)
            
            return filtered_recommendations
        except Exception as e:
            logger.error(f"Error getting {status} recommendations for user {user_id}: {e}")
            raise
    
    def get_unviewed_recommendations(self, user_id: str, limit: Optional[int] = None) -> List[Recommendation]:
        """Get unviewed recommendations for a user"""
        return self.get_user_recommendations_by_status(user_id, 'generated', limit)
    
    def get_viewed_recommendations(self, user_id: str, limit: Optional[int] = None) -> List[Recommendation]:
        """Get viewed recommendations for a user"""
        return self.get_user_recommendations_by_status(user_id, 'viewed', limit)
    
    def get_applied_recommendations(self, user_id: str, limit: Optional[int] = None) -> List[Recommendation]:
        """Get applied recommendations for a user"""
        return self.get_user_recommendations_by_status(user_id, 'applied', limit)
    
    def mark_recommendation_viewed(self, user_id: str, recommendation_id: str) -> bool:
        """Mark a recommendation as viewed"""
        try:
            recommendation = self.get_recommendation(user_id, recommendation_id)
            if not recommendation:
                raise ValueError(f"Recommendation {recommendation_id} not found for user {user_id}")
            
            recommendation.mark_viewed()
            return self.update_recommendation(recommendation)
        except Exception as e:
            logger.error(f"Error marking recommendation {recommendation_id} as viewed: {e}")
            raise
    
    def mark_recommendation_applied(self, user_id: str, recommendation_id: str) -> bool:
        """Mark a recommendation as applied"""
        try:
            recommendation = self.get_recommendation(user_id, recommendation_id)
            if not recommendation:
                raise ValueError(f"Recommendation {recommendation_id} not found for user {user_id}")
            
            recommendation.mark_applied()
            return self.update_recommendation(recommendation)
        except Exception as e:
            logger.error(f"Error marking recommendation {recommendation_id} as applied: {e}")
            raise
    
    def mark_recommendation_dismissed(self, user_id: str, recommendation_id: str) -> bool:
        """Mark a recommendation as dismissed"""
        try:
            recommendation = self.get_recommendation(user_id, recommendation_id)
            if not recommendation:
                raise ValueError(f"Recommendation {recommendation_id} not found for user {user_id}")
            
            recommendation.mark_dismissed()
            return self.update_recommendation(recommendation)
        except Exception as e:
            logger.error(f"Error marking recommendation {recommendation_id} as dismissed: {e}")
            raise
    
    def get_recommendations_for_opportunity(self, opportunity_id: str, limit: Optional[int] = None) -> List[Recommendation]:
        """Get all recommendations for a specific opportunity"""
        try:
            items = self.scan(
                filter_expression='opportunity_id = :opportunity_id',
                expression_attribute_values={':opportunity_id': opportunity_id},
                limit=limit
            )
            return [Recommendation.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting recommendations for opportunity {opportunity_id}: {e}")
            raise
    
    def get_high_score_recommendations(self, user_id: str, min_score: float = 0.7, limit: Optional[int] = None) -> List[Recommendation]:
        """Get high-scoring recommendations for a user"""
        try:
            recommendations = self.get_user_recommendations(user_id, limit)
            return [rec for rec in recommendations if rec.match_score >= min_score]
        except Exception as e:
            logger.error(f"Error getting high score recommendations for user {user_id}: {e}")
            raise
    
    def batch_create_recommendations(self, recommendations: List[Recommendation]) -> bool:
        """Create multiple recommendations in batch"""
        try:
            # Validate all recommendations first
            for recommendation in recommendations:
                errors = recommendation.validate()
                if errors:
                    raise ValueError(f"Recommendation validation failed: {', '.join(errors)}")
            
            # Convert to DynamoDB items
            items = [rec.to_dynamodb_item() for rec in recommendations]
            
            return self.batch_write_items(items)
        except Exception as e:
            logger.error(f"Error batch creating recommendations: {e}")
            raise
    
    def delete_old_recommendations(self, days_old: int = 90) -> int:
        """Delete recommendations older than specified days"""
        try:
            cutoff_date = datetime.utcnow().replace(microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
            cutoff_iso = cutoff_date.isoformat()
            
            items = self.scan(
                filter_expression='generated_at < :cutoff',
                expression_attribute_values={':cutoff': cutoff_iso}
            )
            
            count = 0
            for item in items:
                recommendation = Recommendation.from_dynamodb_item(item)
                self.delete_recommendation(recommendation.user_id, recommendation.recommendation_id)
                count += 1
            
            return count
        except Exception as e:
            logger.error(f"Error deleting old recommendations: {e}")
            raise
    
    def recommendation_exists(self, user_id: str, recommendation_id: str) -> bool:
        """Check if a recommendation exists"""
        try:
            return self.item_exists({
                'user_id': user_id,
                'recommendation_id': recommendation_id
            })
        except Exception as e:
            logger.error(f"Error checking if recommendation exists: {e}")
            raise