"""
Branding Logger for 双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）platform.
Provides centralized logging with consistent terminology for AI CoE support operations.
"""

import logging
from typing import Any, Dict, Optional

from ..config.message_config import message_config


class BrandingLogger:
    """Centralized logger with branding-consistent terminology for 双日TI AI人材発掘・配置マッチングMVP."""
    
    def __init__(self, name: str = __name__):
        """Initialize branding logger with specified name."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Add handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_user_login(self, user_id: str) -> None:
        """Log user login event."""
        message = message_config.format_log_message('user_login', user_id=user_id)
        self.logger.info(message)
    
    def log_user_logout(self, user_id: str) -> None:
        """Log user logout event."""
        message = message_config.format_log_message('user_logout', user_id=user_id)
        self.logger.info(message)
    
    def log_profile_updated(self, user_id: str) -> None:
        """Log skill portfolio update event."""
        message = message_config.format_log_message('profile_updated', user_id=user_id)
        self.logger.info(message)
    
    def log_application_submitted(self, user_id: str, opportunity_id: str) -> None:
        """Log participation application submission event."""
        message = message_config.format_log_message(
            'application_submitted', 
            user_id=user_id, 
            opportunity_id=opportunity_id
        )
        self.logger.info(message)
    
    def log_application_withdrawn(self, user_id: str, opportunity_id: str) -> None:
        """Log participation application withdrawal event."""
        message = message_config.format_log_message(
            'application_withdrawn', 
            user_id=user_id, 
            opportunity_id=opportunity_id
        )
        self.logger.info(message)
    
    def log_questionnaire_completed(self, user_id: str) -> None:
        """Log skill inventory completion event."""
        message = message_config.format_log_message('questionnaire_completed', user_id=user_id)
        self.logger.info(message)
    
    def log_recommendation_generated(self, user_id: str) -> None:
        """Log participation opportunity recommendation generation event."""
        message = message_config.format_log_message('recommendation_generated', user_id=user_id)
        self.logger.info(message)
    
    def log_search_performed(self, query: str) -> None:
        """Log registered talent search event."""
        message = message_config.format_log_message('search_performed', query=query)
        self.logger.info(message)
    
    def log_error_occurred(self, error_type: str, error_message: str) -> None:
        """Log error event."""
        message = message_config.format_log_message(
            'error_occurred', 
            error_type=error_type, 
            message=error_message
        )
        self.logger.error(message)
    
    def log_api_request(self, method: str, endpoint: str, user_id: Optional[str] = None) -> None:
        """Log API request event."""
        message = message_config.format_log_message(
            'api_request', 
            method=method, 
            endpoint=endpoint, 
            user_id=user_id or 'anonymous'
        )
        self.logger.info(message)
    
    def log_api_response(self, status_code: int, endpoint: str) -> None:
        """Log API response event."""
        message = message_config.format_log_message(
            'api_response', 
            status_code=status_code, 
            endpoint=endpoint
        )
        self.logger.info(message)
    
    def log_database_operation(self, operation: str, table: str) -> None:
        """Log database operation event."""
        message = message_config.format_log_message(
            'database_operation', 
            operation=operation, 
            table=table
        )
        self.logger.debug(message)
    
    def log_ai_generation(self, generation_type: str, user_id: str) -> None:
        """Log AI generation event."""
        message = message_config.format_log_message(
            'ai_generation', 
            type=generation_type, 
            user_id=user_id
        )
        self.logger.info(message)
    
    def log_system_startup(self) -> None:
        """Log system startup event."""
        message = message_config.format_log_message('system_startup')
        self.logger.info(message)
    
    def log_system_shutdown(self) -> None:
        """Log system shutdown event."""
        message = message_config.format_log_message('system_shutdown')
        self.logger.info(message)
    
    def log_custom_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log custom event with details."""
        message = f"カスタムイベント: {event_type} - {details}"
        self.logger.info(message)
    
    def log_security_event(self, event_type: str, user_id: Optional[str], details: str) -> None:
        """Log security-related event."""
        user_info = f"社内AI人材候補ID: {user_id}" if user_id else "匿名ユーザー"
        message = f"セキュリティイベント: {event_type} - {user_info} - {details}"
        self.logger.warning(message)
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = "") -> None:
        """Log performance metric."""
        message = f"パフォーマンス指標: {metric_name} = {value} {unit}"
        self.logger.info(message)
    
    def log_business_event(self, event_type: str, user_id: str, details: Dict[str, Any]) -> None:
        """Log business-related event."""
        message = f"ビジネスイベント: {event_type} - 社内AI人材候補ID: {user_id} - {details}"
        self.logger.info(message)


# Global instance for easy access
branding_logger = BrandingLogger('ai_talent_matching_mvp')


def get_branding_logger(name: str = None) -> BrandingLogger:
    """Get a branding logger instance with optional custom name."""
    if name:
        return BrandingLogger(name)
    return branding_logger