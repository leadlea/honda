"""
Questionnaire and QuestionnaireResponse repositories for DynamoDB operations
"""
import os
from typing import List, Optional
from datetime import datetime
import logging

from .base_repository import BaseRepository
from ..models.questionnaire import Questionnaire, QuestionnaireResponse

logger = logging.getLogger(__name__)


class QuestionnaireRepository(BaseRepository):
    """Repository for questionnaire operations"""
    
    def __init__(self):
        table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX', 'honda-veteran-talent-matching-dev')}-questionnaires"
        super().__init__(table_name)
    
    def create_questionnaire(self, questionnaire: Questionnaire) -> bool:
        """Create a new questionnaire"""
        try:
            errors = questionnaire.validate()
            if errors:
                raise ValueError(f"Questionnaire validation failed: {', '.join(errors)}")
            
            item = questionnaire.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error creating questionnaire: {e}")
            raise
    
    def get_questionnaire(self, questionnaire_id: str) -> Optional[Questionnaire]:
        """Get questionnaire by ID"""
        try:
            item = self.get_item({'questionnaire_id': questionnaire_id})
            if item:
                return Questionnaire.from_dynamodb_item(item)
            return None
        except Exception as e:
            logger.error(f"Error getting questionnaire {questionnaire_id}: {e}")
            raise
    
    def get_user_questionnaires(self, user_id: str, active_only: bool = True) -> List[Questionnaire]:
        """Get questionnaires for a user"""
        try:
            items = self.query(
                key_condition_expression='user_id = :user_id',
                expression_attribute_values={':user_id': user_id},
                index_name='UserIdIndex'
            )
            
            questionnaires = [Questionnaire.from_dynamodb_item(item) for item in items]
            
            if active_only:
                questionnaires = [q for q in questionnaires if q.is_active and not q.is_expired()]
            
            return questionnaires
        except Exception as e:
            logger.error(f"Error getting questionnaires for user {user_id}: {e}")
            raise
    
    def deactivate_questionnaire(self, questionnaire_id: str) -> bool:
        """Deactivate a questionnaire"""
        try:
            questionnaire = self.get_questionnaire(questionnaire_id)
            if not questionnaire:
                raise ValueError(f"Questionnaire {questionnaire_id} not found")
            
            questionnaire.is_active = False
            item = questionnaire.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error deactivating questionnaire {questionnaire_id}: {e}")
            raise


class QuestionnaireResponseRepository(BaseRepository):
    """Repository for questionnaire response operations"""
    
    def __init__(self):
        table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX', 'honda-veteran-talent-matching-dev')}-questionnaire-responses"
        super().__init__(table_name)
    
    def create_response(self, response: QuestionnaireResponse) -> bool:
        """Create a new questionnaire response"""
        try:
            errors = response.validate()
            if errors:
                raise ValueError(f"Response validation failed: {', '.join(errors)}")
            
            item = response.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error creating questionnaire response: {e}")
            raise
    
    def get_response(self, user_id: str, response_id: str) -> Optional[QuestionnaireResponse]:
        """Get questionnaire response by user ID and response ID"""
        try:
            item = self.get_item({
                'user_id': user_id,
                'response_id': response_id
            })
            if item:
                return QuestionnaireResponse.from_dynamodb_item(item)
            return None
        except Exception as e:
            logger.error(f"Error getting response {response_id} for user {user_id}: {e}")
            raise
    
    def update_response(self, response: QuestionnaireResponse) -> bool:
        """Update an existing questionnaire response"""
        try:
            errors = response.validate()
            if errors:
                raise ValueError(f"Response validation failed: {', '.join(errors)}")
            
            response.updated_at = datetime.utcnow().isoformat()
            item = response.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error updating questionnaire response: {e}")
            raise
    
    def get_user_responses(self, user_id: str, limit: Optional[int] = None) -> List[QuestionnaireResponse]:
        """Get all responses for a user"""
        try:
            items = self.query(
                key_condition_expression='user_id = :user_id',
                expression_attribute_values={':user_id': user_id},
                limit=limit,
                scan_index_forward=False  # Most recent first
            )
            return [QuestionnaireResponse.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting responses for user {user_id}: {e}")
            raise
    
    def get_responses_for_questionnaire(self, questionnaire_id: str) -> List[QuestionnaireResponse]:
        """Get all responses for a specific questionnaire"""
        try:
            items = self.scan(
                filter_expression='questionnaire_id = :questionnaire_id',
                expression_attribute_values={':questionnaire_id': questionnaire_id}
            )
            return [QuestionnaireResponse.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting responses for questionnaire {questionnaire_id}: {e}")
            raise
    
    def get_completed_responses(self, user_id: str) -> List[QuestionnaireResponse]:
        """Get completed responses for a user"""
        try:
            responses = self.get_user_responses(user_id)
            return [r for r in responses if r.is_complete]
        except Exception as e:
            logger.error(f"Error getting completed responses for user {user_id}: {e}")
            raise
    
    def add_answer(self, user_id: str, response_id: str, question_id: str, answer: str) -> bool:
        """Add an answer to a questionnaire response"""
        try:
            response = self.get_response(user_id, response_id)
            if not response:
                raise ValueError(f"Response {response_id} not found for user {user_id}")
            
            response.add_response(question_id, answer)
            return self.update_response(response)
        except Exception as e:
            logger.error(f"Error adding answer to response {response_id}: {e}")
            raise
    
    def complete_response(self, user_id: str, response_id: str) -> bool:
        """Mark a questionnaire response as complete"""
        try:
            response = self.get_response(user_id, response_id)
            if not response:
                raise ValueError(f"Response {response_id} not found for user {user_id}")
            
            response.mark_complete()
            return self.update_response(response)
        except Exception as e:
            logger.error(f"Error completing response {response_id}: {e}")
            raise