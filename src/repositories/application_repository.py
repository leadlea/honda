"""
Application repository for DynamoDB operations
"""
import os
from typing import List, Optional
from datetime import datetime
import logging

from .base_repository import BaseRepository
from ..models.application import Application

logger = logging.getLogger(__name__)


class ApplicationRepository(BaseRepository):
    """Repository for application operations"""
    
    def __init__(self):
        table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX', 'honda-veteran-talent-matching-dev')}-applications"
        super().__init__(table_name)
    
    def create_application(self, application: Application) -> bool:
        """Create a new application"""
        try:
            errors = application.validate()
            if errors:
                raise ValueError(f"Application validation failed: {', '.join(errors)}")
            
            item = application.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error creating application: {e}")
            raise
    
    def get_application(self, application_id: str) -> Optional[Application]:
        """Get application by ID"""
        try:
            item = self.get_item({'application_id': application_id})
            if item:
                return Application.from_dynamodb_item(item)
            return None
        except Exception as e:
            logger.error(f"Error getting application {application_id}: {e}")
            raise
    
    def update_application(self, application: Application) -> bool:
        """Update an existing application"""
        try:
            errors = application.validate()
            if errors:
                raise ValueError(f"Application validation failed: {', '.join(errors)}")
            
            application.updated_at = datetime.utcnow().isoformat()
            item = application.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error updating application: {e}")
            raise
    
    def delete_application(self, application_id: str) -> bool:
        """Delete an application"""
        try:
            return self.delete_item({'application_id': application_id})
        except Exception as e:
            logger.error(f"Error deleting application {application_id}: {e}")
            raise
    
    def get_user_applications(self, user_id: str, limit: Optional[int] = None) -> List[Application]:
        """Get all applications for a user"""
        try:
            items = self.query(
                key_condition_expression='user_id = :user_id',
                expression_attribute_values={':user_id': user_id},
                index_name='UserIdIndex',
                limit=limit,
                scan_index_forward=False  # Most recent first
            )
            return [Application.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting applications for user {user_id}: {e}")
            raise
    
    def get_applications_for_opportunity(self, opportunity_id: str, limit: Optional[int] = None) -> List[Application]:
        """Get all applications for an opportunity"""
        try:
            items = self.query(
                key_condition_expression='opportunity_id = :opportunity_id',
                expression_attribute_values={':opportunity_id': opportunity_id},
                index_name='OpportunityIdIndex',
                limit=limit,
                scan_index_forward=False  # Most recent first
            )
            return [Application.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting applications for opportunity {opportunity_id}: {e}")
            raise
    
    def get_applications_by_status(self, status: str, limit: Optional[int] = None) -> List[Application]:
        """Get applications by status"""
        try:
            items = self.scan(
                filter_expression='#status = :status',
                expression_attribute_names={'#status': 'status'},
                expression_attribute_values={':status': status},
                limit=limit
            )
            return [Application.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting applications by status {status}: {e}")
            raise
    
    def get_user_applications_by_status(self, user_id: str, status: str, limit: Optional[int] = None) -> List[Application]:
        """Get user applications filtered by status"""
        try:
            applications = self.get_user_applications(user_id, limit)
            return [app for app in applications if app.status == status]
        except Exception as e:
            logger.error(f"Error getting {status} applications for user {user_id}: {e}")
            raise
    
    def get_active_applications(self, user_id: str) -> List[Application]:
        """Get active applications for a user"""
        try:
            applications = self.get_user_applications(user_id)
            return [app for app in applications if app.is_active()]
        except Exception as e:
            logger.error(f"Error getting active applications for user {user_id}: {e}")
            raise
    
    def update_application_status(self, application_id: str, new_status: str, 
                                reviewer_id: Optional[str] = None, notes: str = "") -> bool:
        """Update application status"""
        try:
            application = self.get_application(application_id)
            if not application:
                raise ValueError(f"Application {application_id} not found")
            
            application.update_status(new_status, reviewer_id, notes)
            return self.update_application(application)
        except Exception as e:
            logger.error(f"Error updating application status {application_id}: {e}")
            raise
    
    def withdraw_application(self, application_id: str, user_id: str) -> bool:
        """Withdraw an application (only by the applicant)"""
        try:
            application = self.get_application(application_id)
            if not application:
                raise ValueError(f"Application {application_id} not found")
            
            if application.user_id != user_id:
                raise ValueError("Only the applicant can withdraw their application")
            
            application.withdraw()
            return self.update_application(application)
        except Exception as e:
            logger.error(f"Error withdrawing application {application_id}: {e}")
            raise
    
    def check_existing_application(self, user_id: str, opportunity_id: str) -> Optional[Application]:
        """Check if user has already applied to an opportunity"""
        try:
            user_applications = self.get_user_applications(user_id)
            for app in user_applications:
                if app.opportunity_id == opportunity_id and app.is_active():
                    return app
            return None
        except Exception as e:
            logger.error(f"Error checking existing application for user {user_id}, opportunity {opportunity_id}: {e}")
            raise
    
    def get_applications_needing_review(self, limit: Optional[int] = None) -> List[Application]:
        """Get applications that need review"""
        try:
            return self.get_applications_by_status('submitted', limit)
        except Exception as e:
            logger.error(f"Error getting applications needing review: {e}")
            raise
    
    def get_application_statistics(self) -> dict:
        """Get application statistics"""
        try:
            all_applications = self.scan()
            
            stats = {
                'total': len(all_applications),
                'by_status': {},
                'by_type': {}
            }
            
            for item in all_applications:
                app = Application.from_dynamodb_item(item)
                
                # Count by status
                stats['by_status'][app.status] = stats['by_status'].get(app.status, 0) + 1
                
                # Count by type
                stats['by_type'][app.application_type] = stats['by_type'].get(app.application_type, 0) + 1
            
            return stats
        except Exception as e:
            logger.error(f"Error getting application statistics: {e}")
            raise
    
    def application_exists(self, application_id: str) -> bool:
        """Check if an application exists"""
        try:
            return self.item_exists({'application_id': application_id})
        except Exception as e:
            logger.error(f"Error checking if application exists {application_id}: {e}")
            raise