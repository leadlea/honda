"""
Application handler for managing job applications and interest expressions
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.application import Application
from ..models.opportunity import Opportunity
from ..models.user import User
from ..repositories.application_repository import ApplicationRepository
from ..repositories.opportunity_repository import OpportunityRepository
from ..repositories.user_repository import UserRepository
from ..services.application_status_service import ApplicationStatusService
from ..utils.auth_utils import extract_user_from_event
from ..utils.rbac import require_role, rbac_manager, Permission

logger = logging.getLogger(__name__)


class ApplicationHandler:
    """Handler for application-related operations"""
    
    def __init__(self):
        self.application_repo = ApplicationRepository()
        self.opportunity_repo = OpportunityRepository()
        self.user_repo = UserRepository()
    
    def submit_application(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Submit an application or express interest in an opportunity
        Requirements: 3.1, 3.2
        """
        try:
            # Verify authentication
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            user_id = user_info['user_id']
            
            # Parse request body
            body = json.loads(event.get('body', '{}'))
            opportunity_id = body.get('opportunity_id')
            application_type = body.get('application_type', 'interest')  # 'interest' or 'formal_application'
            cover_letter = body.get('cover_letter', '')
            additional_notes = body.get('additional_notes', '')
            
            if not opportunity_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'opportunity_id is required'})
                }
            
            # Verify opportunity exists and is active
            opportunity = self.opportunity_repo.get_opportunity(opportunity_id)
            if not opportunity:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'Opportunity not found'})
                }
            
            if not opportunity.is_active or opportunity.is_expired():
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Opportunity is no longer active'})
                }
            
            # Check for existing application
            existing_application = self.application_repo.check_existing_application(user_id, opportunity_id)
            if existing_application:
                return {
                    'statusCode': 409,
                    'body': json.dumps({
                        'error': 'You have already applied to this opportunity',
                        'existing_application_id': existing_application.application_id
                    })
                }
            
            # Create new application
            application = Application(
                user_id=user_id,
                opportunity_id=opportunity_id,
                application_type=application_type,
                cover_letter=cover_letter,
                additional_notes=additional_notes,
                status='submitted'
            )
            
            # Validate and save application
            errors = application.validate()
            if errors:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Validation failed', 'details': errors})
                }
            
            success = self.application_repo.create_application(application)
            if not success:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': 'Failed to create application'})
                }
            
            # Send notifications to stakeholders
            self._notify_stakeholders(application, opportunity, 'application_submitted')
            
            return {
                'statusCode': 201,
                'body': json.dumps({
                    'message': 'Application submitted successfully',
                    'application_id': application.application_id,
                    'status': application.status
                })
            }
            
        except Exception as e:
            logger.error(f"Error submitting application: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }
    
    def get_user_applications(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Get all applications for the authenticated user
        Requirements: 3.3
        """
        try:
            # Verify authentication
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            user_id = user_info['user_id']
            
            # Get query parameters
            query_params = event.get('queryStringParameters') or {}
            status_filter = query_params.get('status')
            limit = int(query_params.get('limit', 50))
            
            # Get applications
            if status_filter:
                applications = self.application_repo.get_user_applications_by_status(user_id, status_filter, limit)
            else:
                applications = self.application_repo.get_user_applications(user_id, limit)
            
            # Enrich with opportunity details
            enriched_applications = []
            for app in applications:
                app_data = app.to_dynamodb_item()
                
                # Get opportunity details
                opportunity = self.opportunity_repo.get_opportunity(app.opportunity_id)
                if opportunity:
                    app_data['opportunity'] = {
                        'title': opportunity.title,
                        'company': opportunity.company,
                        'location': opportunity.location,
                        'type': opportunity.type
                    }
                
                enriched_applications.append(app_data)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'applications': enriched_applications,
                    'total': len(enriched_applications)
                })
            }
            
        except Exception as e:
            logger.error(f"Error getting user applications: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }
    
    def get_application_details(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Get detailed information about a specific application
        Requirements: 3.3
        """
        try:
            # Verify authentication
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            user_id = user_info['user_id']
            application_id = event['pathParameters']['application_id']
            
            # Get application
            application = self.application_repo.get_application(application_id)
            if not application:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'Application not found'})
                }
            
            # Check if user owns this application or has admin permissions
            if application.user_id != user_id and not rbac_manager.has_permission(user_info['role'], Permission.MANAGE_APPLICATIONS):
                return {
                    'statusCode': 403,
                    'body': json.dumps({'error': 'Access denied'})
                }
            
            # Get opportunity details
            opportunity = self.opportunity_repo.get_opportunity(application.opportunity_id)
            
            # Prepare response
            app_data = application.to_dynamodb_item()
            if opportunity:
                app_data['opportunity'] = opportunity.to_dynamodb_item()
            
            return {
                'statusCode': 200,
                'body': json.dumps(app_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting application details: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }
    
    def withdraw_application(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Withdraw an application
        Requirements: 3.4
        """
        try:
            # Verify authentication
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            user_id = user_info['user_id']
            application_id = event['pathParameters']['application_id']
            
            # Withdraw application
            success = self.application_repo.withdraw_application(application_id, user_id)
            if not success:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Failed to withdraw application'})
                }
            
            # Get updated application for notification
            application = self.application_repo.get_application(application_id)
            opportunity = self.opportunity_repo.get_opportunity(application.opportunity_id)
            
            # Notify stakeholders
            self._notify_stakeholders(application, opportunity, 'application_withdrawn')
            
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Application withdrawn successfully'})
            }
            
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': str(e)})
            }
        except Exception as e:
            logger.error(f"Error withdrawing application: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }
    
    def update_application_status(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Update application status (admin/reviewer only)
        Requirements: 3.3, 3.4
        """
        try:
            # Verify authentication and admin permissions
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            # Check admin permissions
            if not rbac_manager.has_permission(user_info['role'], Permission.MANAGE_APPLICATIONS):
                return {
                    'statusCode': 403,
                    'body': json.dumps({'error': 'Insufficient permissions'})
                }
            
            application_id = event['pathParameters']['application_id']
            body = json.loads(event.get('body', '{}'))
            
            new_status = body.get('status')
            reviewer_notes = body.get('notes', '')
            
            if not new_status:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'status is required'})
                }
            
            # Update application status
            success = self.application_repo.update_application_status(
                application_id, 
                new_status, 
                user_info['user_id'], 
                reviewer_notes
            )
            
            if not success:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Failed to update application status'})
                }
            
            # Get updated application for notification
            application = self.application_repo.get_application(application_id)
            opportunity = self.opportunity_repo.get_opportunity(application.opportunity_id)
            
            # Notify stakeholders
            self._notify_stakeholders(application, opportunity, 'status_updated')
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Application status updated successfully',
                    'status': new_status
                })
            }
            
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': str(e)})
            }
        except Exception as e:
            logger.error(f"Error updating application status: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }
    
    def get_applications_for_opportunity(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Get all applications for a specific opportunity (admin only)
        Requirements: 3.3
        """
        try:
            # Verify authentication and admin permissions
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            # Check admin permissions
            if not rbac_manager.has_permission(user_info['role'], Permission.MANAGE_APPLICATIONS):
                return {
                    'statusCode': 403,
                    'body': json.dumps({'error': 'Insufficient permissions'})
                }
            
            opportunity_id = event['pathParameters']['opportunity_id']
            query_params = event.get('queryStringParameters') or {}
            limit = int(query_params.get('limit', 50))
            
            # Get applications for opportunity
            applications = self.application_repo.get_applications_for_opportunity(opportunity_id, limit)
            
            # Enrich with user details
            enriched_applications = []
            for app in applications:
                app_data = app.to_dynamodb_item()
                
                # Get user details (basic info only for privacy)
                user = self.user_repo.get_user(app.user_id)
                if user:
                    app_data['applicant'] = {
                        'name': user.name,
                        'email': user.email,
                        'department': user.department
                    }
                
                enriched_applications.append(app_data)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'applications': enriched_applications,
                    'total': len(enriched_applications)
                })
            }
            
        except Exception as e:
            logger.error(f"Error getting applications for opportunity: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }
    
    def _notify_stakeholders(self, application: Application, opportunity: Optional[Opportunity], event_type: str) -> None:
        """
        Send notifications to relevant stakeholders
        Requirements: 3.2, 3.4
        """
        try:
            # Get applicant details
            applicant = self.user_repo.get_user(application.user_id)
            if not applicant:
                logger.warning(f"Could not find applicant {application.user_id} for notification")
                return
            
            # Prepare notification data
            notification_data = {
                'event_type': event_type,
                'application_id': application.application_id,
                'opportunity_id': application.opportunity_id,
                'applicant': {
                    'name': applicant.name,
                    'email': applicant.email,
                    'department': applicant.department
                },
                'application': {
                    'type': application.application_type,
                    'status': application.status,
                    'submitted_at': application.submitted_at
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if opportunity:
                notification_data['opportunity'] = {
                    'title': opportunity.title,
                    'company': opportunity.company,
                    'type': opportunity.type
                }
            
            # Log notification (in a real implementation, this would send emails/messages)
            logger.info(f"Stakeholder notification: {json.dumps(notification_data)}")
            
            # TODO: Implement actual notification sending (email, Slack, etc.)
            # This could integrate with AWS SES, SNS, or other notification services
            
        except Exception as e:
            logger.error(f"Error sending stakeholder notifications: {e}")
            # Don't raise exception as notification failure shouldn't break the main flow

    def get_application_history(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Get application status history
        Requirements: 3.3
        """
        try:
            # Verify authentication
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            user_id = user_info['user_id']
            application_id = event['pathParameters']['application_id']
            
            # Get application to verify access
            application = self.application_repo.get_application(application_id)
            if not application:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'Application not found'})
                }
            
            # Check if user has access to this application
            user = self.user_repo.get_user(user_id)
            has_access = (
                user_id == application.user_id or  # Applicant
                user_id == application.reviewer_id or  # Reviewer
                user.role == 'admin'  # Admin
            )
            
            if not has_access:
                return {
                    'statusCode': 403,
                    'body': json.dumps({'error': 'Access denied'})
                }
            
            # Get history using status service
            status_service = ApplicationStatusService()
            result = status_service.get_application_history(application_id)
            
            if not result['success']:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': result['error']})
                }
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
            
        except Exception as e:
            logger.error(f"Error getting application history: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }

    def send_application_message(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Send a communication message for an application
        Requirements: 3.3, 3.4
        """
        try:
            # Verify authentication
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            user_id = user_info['user_id']
            application_id = event['pathParameters']['application_id']
            
            # Parse request body
            body = json.loads(event.get('body', '{}'))
            message = body.get('message', '').strip()
            message_type = body.get('message_type', 'general')
            
            if not message:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'message is required'})
                }
            
            # Get application to verify access
            application = self.application_repo.get_application(application_id)
            if not application:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'Application not found'})
                }
            
            # Check if user is involved in this application
            user = self.user_repo.get_user(user_id)
            has_access = (
                user_id == application.user_id or  # Applicant
                user_id == application.reviewer_id or  # Reviewer
                user.role == 'admin'  # Admin
            )
            
            if not has_access:
                return {
                    'statusCode': 403,
                    'body': json.dumps({'error': 'Access denied'})
                }
            
            # Send message using status service
            status_service = ApplicationStatusService()
            
            result = status_service.send_communication_message(
                application_id, user_id, message, message_type
            )
            
            if not result['success']:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': result['error']})
                }
            
            return {
                'statusCode': 201,
                'body': json.dumps({
                    'message': 'Message sent successfully',
                    'message_id': result['message_id'],
                    'sent_at': result['sent_at']
                })
            }
            
        except Exception as e:
            logger.error(f"Error sending application message: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }

    def get_application_communications(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Get all communications for an application
        Requirements: 3.3
        """
        try:
            # Verify authentication
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            user_id = user_info['user_id']
            application_id = event['pathParameters']['application_id']
            
            # Get communications using status service
            status_service = ApplicationStatusService()
            
            result = status_service.get_application_communications(application_id, user_id)
            
            if not result['success']:
                if result['error'] == 'Access denied':
                    return {
                        'statusCode': 403,
                        'body': json.dumps({'error': result['error']})
                    }
                elif result['error'] == 'Application not found':
                    return {
                        'statusCode': 404,
                        'body': json.dumps({'error': result['error']})
                    }
                else:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({'error': result['error']})
                    }
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
            
        except Exception as e:
            logger.error(f"Error getting application communications: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }

    def update_application_status_with_workflow(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Update application status with workflow validation
        Requirements: 3.3, 3.4
        """
        try:
            # Verify authentication and admin permissions
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Unauthorized'})
                }
            
            # Check admin permissions
            if not rbac_manager.has_permission(user_info['role'], Permission.MANAGE_APPLICATIONS):
                return {
                    'statusCode': 403,
                    'body': json.dumps({'error': 'Insufficient permissions'})
                }
            
            application_id = event['pathParameters']['application_id']
            body = json.loads(event.get('body', '{}'))
            
            new_status = body.get('status')
            notes = body.get('notes', '')
            
            if not new_status:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'status is required'})
                }
            
            # Update status using status service with workflow validation
            status_service = ApplicationStatusService()
            
            result = status_service.update_status_with_workflow(
                application_id, new_status, user_info['user_id'], notes
            )
            
            if not result['success']:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': result['error']})
                }
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Application status updated successfully',
                    'old_status': result['old_status'],
                    'new_status': result['new_status'],
                    'updated_by': result['updated_by'],
                    'timestamp': result['timestamp']
                })
            }
            
        except Exception as e:
            logger.error(f"Error updating application status with workflow: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }


# Lambda function handlers
def submit_application(event, context):
    """Lambda handler for submitting applications"""
    handler = ApplicationHandler()
    return handler.submit_application(event, context)


def get_user_applications(event, context):
    """Lambda handler for getting user applications"""
    handler = ApplicationHandler()
    return handler.get_user_applications(event, context)


def get_application_details(event, context):
    """Lambda handler for getting application details"""
    handler = ApplicationHandler()
    return handler.get_application_details(event, context)


def withdraw_application(event, context):
    """Lambda handler for withdrawing applications"""
    handler = ApplicationHandler()
    return handler.withdraw_application(event, context)


def update_application_status(event, context):
    """Lambda handler for updating application status"""
    handler = ApplicationHandler()
    return handler.update_application_status(event, context)


def get_applications_for_opportunity(event, context):
    """Lambda handler for getting applications for an opportunity"""
    handler = ApplicationHandler()
    return handler.get_applications_for_opportunity(event, context)



# Lambda function handlers
def get_application_history(event, context):
    """Lambda handler for getting application history"""
    handler = ApplicationHandler()
    return handler.get_application_history(event, context)


def send_application_message(event, context):
    """Lambda handler for sending application messages"""
    handler = ApplicationHandler()
    return handler.send_application_message(event, context)


def get_application_communications(event, context):
    """Lambda handler for getting application communications"""
    handler = ApplicationHandler()
    return handler.get_application_communications(event, context)


def update_application_status_with_workflow(event, context):
    """Lambda handler for updating application status with workflow"""
    handler = ApplicationHandler()
    return handler.update_application_status_with_workflow(event, context)