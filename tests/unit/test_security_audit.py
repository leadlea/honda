"""
Unit tests for security audit system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.utils.security_audit import (
    SecurityEvent, SecurityEventType, RiskLevel, SecurityAuditor,
    security_auditor, audit_security_event, extract_request_info
)


class TestSecurityEvent:
    """Test cases for SecurityEvent."""
    
    def test_security_event_creation(self):
        """Test SecurityEvent creation."""
        event = SecurityEvent(
            event_type=SecurityEventType.LOGIN_SUCCESS.value,
            user_id='user123',
            timestamp='2023-01-01T00:00:00Z',
            risk_level=RiskLevel.LOW.value,
            source_ip='192.168.1.1',
            user_agent='Mozilla/5.0',
            action='login',
            result='success'
        )
        
        assert event.event_type == 'login_success'
        assert event.user_id == 'user123'
        assert event.risk_level == 'low'
        assert event.source_ip == '192.168.1.1'
        assert event.action == 'login'
        assert event.result == 'success'
    
    def test_security_event_to_dict(self):
        """Test SecurityEvent to_dict method."""
        event = SecurityEvent(
            event_type=SecurityEventType.PROFILE_ACCESS.value,
            user_id='user123',
            timestamp='2023-01-01T00:00:00Z',
            risk_level=RiskLevel.MEDIUM.value,
            details={'accessed_profile': 'user456'}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict['event_type'] == 'profile_access'
        assert event_dict['user_id'] == 'user123'
        assert event_dict['risk_level'] == 'medium'
        assert event_dict['details'] == {'accessed_profile': 'user456'}


class TestSecurityAuditor:
    """Test cases for SecurityAuditor."""
    
    def setup_method(self):
        """Set up test environment."""
        self.auditor = SecurityAuditor()
    
    @patch('src.utils.security_audit.logger')
    def test_log_event_success(self, mock_logger):
        """Test successful event logging."""
        event = SecurityEvent(
            event_type=SecurityEventType.LOGIN_SUCCESS.value,
            user_id='user123',
            timestamp='2023-01-01T00:00:00Z',
            risk_level=RiskLevel.LOW.value
        )
        
        result = self.auditor.log_event(event)
        
        assert result is True
        mock_logger.info.assert_called_once()
    
    @patch('src.utils.security_audit.logger')
    def test_log_event_high_risk_alert(self, mock_logger):
        """Test logging high-risk event triggers alert."""
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY.value,
            user_id='user123',
            timestamp='2023-01-01T00:00:00Z',
            risk_level=RiskLevel.CRITICAL.value
        )
        
        with patch.object(self.auditor, '_send_security_alert') as mock_alert:
            result = self.auditor.log_event(event)
            
            assert result is True
            mock_alert.assert_called_once_with(event)
    
    @patch('src.utils.security_audit.logger')
    def test_log_login_attempt_success(self, mock_logger):
        """Test logging successful login attempt."""
        self.auditor.log_login_attempt(
            user_id='user123',
            success=True,
            source_ip='192.168.1.1',
            user_agent='Mozilla/5.0'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'login_success' in call_args
        assert 'user123' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_log_login_attempt_failure(self, mock_logger):
        """Test logging failed login attempt."""
        self.auditor.log_login_attempt(
            user_id='user123',
            success=False,
            source_ip='192.168.1.1',
            failure_reason='invalid_password'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'login_failure' in call_args
        assert 'invalid_password' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_log_logout(self, mock_logger):
        """Test logging user logout."""
        self.auditor.log_logout(
            user_id='user123',
            source_ip='192.168.1.1'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'logout' in call_args
        assert 'user123' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_log_profile_access_own_profile(self, mock_logger):
        """Test logging access to own profile."""
        self.auditor.log_profile_access(
            user_id='user123',
            accessed_profile_id='user123',
            action='view',
            source_ip='192.168.1.1'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'profile_access' in call_args
        assert '"risk_level": "low"' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_log_profile_access_other_profile(self, mock_logger):
        """Test logging access to other user's profile."""
        self.auditor.log_profile_access(
            user_id='user123',
            accessed_profile_id='user456',
            action='view',
            source_ip='192.168.1.1'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'profile_access' in call_args
        assert '"risk_level": "medium"' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_log_permission_denied(self, mock_logger):
        """Test logging permission denied event."""
        self.auditor.log_permission_denied(
            user_id='user123',
            user_role='veteran',
            attempted_action='delete_user',
            resource='user:user456',
            source_ip='192.168.1.1'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'permission_denied' in call_args
        assert 'delete_user' in call_args
        assert '"risk_level": "medium"' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_log_role_change(self, mock_logger):
        """Test logging role change event."""
        self.auditor.log_role_change(
            admin_user_id='admin123',
            target_user_id='user456',
            old_role='veteran',
            new_role='admin',
            source_ip='192.168.1.1'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'role_change' in call_args
        assert '"risk_level": "high"' in call_args
        assert 'veteran' in call_args
        assert 'admin' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_log_admin_action(self, mock_logger):
        """Test logging admin action."""
        self.auditor.log_admin_action(
            admin_user_id='admin123',
            action='delete_user',
            target_resource='user:user456',
            details={'reason': 'policy_violation'},
            source_ip='192.168.1.1'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'admin_action' in call_args
        assert 'delete_user' in call_args
        assert '"risk_level": "high"' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_log_external_access(self, mock_logger):
        """Test logging external access."""
        self.auditor.log_external_access(
            external_user_id='recruiter123',
            action='search_profiles',
            resource='public_profiles',
            source_ip='203.0.113.1',
            user_agent='Mozilla/5.0'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'external_access' in call_args
        assert 'search_profiles' in call_args
        assert '"risk_level": "medium"' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_log_suspicious_activity(self, mock_logger):
        """Test logging suspicious activity."""
        self.auditor.log_suspicious_activity(
            user_id='user123',
            activity_type='multiple_failed_logins',
            details={'attempts': 10, 'time_window': '5_minutes'},
            source_ip='192.168.1.1'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'suspicious_activity' in call_args
        assert '"risk_level": "critical"' in call_args
        assert 'multiple_failed_logins' in call_args
    
    @patch('src.utils.security_audit.logger')
    def test_get_user_activity_summary(self, mock_logger):
        """Test getting user activity summary."""
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 1, 31, tzinfo=timezone.utc)
        
        summary = self.auditor.get_user_activity_summary(
            user_id='user123',
            start_date=start_date,
            end_date=end_date
        )
        
        assert summary['user_id'] == 'user123'
        assert summary['period']['start'] == start_date.isoformat()
        assert summary['period']['end'] == end_date.isoformat()
        assert 'total_events' in summary
        assert 'event_types' in summary
        
        mock_logger.info.assert_called_once()
    
    @patch('src.utils.security_audit.cloudwatch_logs')
    def test_send_to_cloudwatch_success(self, mock_cloudwatch):
        """Test sending logs to CloudWatch."""
        mock_cloudwatch.create_log_group.side_effect = mock_cloudwatch.exceptions.ResourceAlreadyExistsException()
        mock_cloudwatch.create_log_stream.side_effect = mock_cloudwatch.exceptions.ResourceAlreadyExistsException()
        mock_cloudwatch.put_log_events.return_value = {}
        
        log_entry = {'test': 'data'}
        
        # This is a private method, so we test it indirectly through log_event
        event = SecurityEvent(
            event_type=SecurityEventType.LOGIN_SUCCESS.value,
            user_id='user123',
            timestamp='2023-01-01T00:00:00Z',
            risk_level=RiskLevel.LOW.value
        )
        
        result = self.auditor.log_event(event)
        
        assert result is True
    
    @patch('src.utils.security_audit.logger')
    def test_send_security_alert(self, mock_logger):
        """Test sending security alert."""
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY.value,
            user_id='user123',
            timestamp='2023-01-01T00:00:00Z',
            risk_level=RiskLevel.CRITICAL.value,
            details={'threat_type': 'brute_force'}
        )
        
        self.auditor._send_security_alert(event)
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert 'SECURITY_ALERT' in call_args
        assert 'brute_force' in call_args


class TestSecurityAuditUtilities:
    """Test cases for security audit utility functions."""
    
    @patch('src.utils.security_audit.security_auditor.log_event')
    def test_audit_security_event(self, mock_log_event):
        """Test audit_security_event function."""
        mock_log_event.return_value = True
        
        audit_security_event(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            user_id='user123',
            risk_level=RiskLevel.LOW,
            source_ip='192.168.1.1'
        )
        
        mock_log_event.assert_called_once()
        event_arg = mock_log_event.call_args[0][0]
        assert event_arg.event_type == 'login_success'
        assert event_arg.user_id == 'user123'
        assert event_arg.risk_level == 'low'
        assert event_arg.source_ip == '192.168.1.1'
    
    def test_extract_request_info_with_headers(self):
        """Test extracting request info from Lambda event."""
        event = {
            'headers': {
                'X-Forwarded-For': '203.0.113.1, 192.168.1.1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            },
            'requestContext': {
                'requestId': 'req-123',
                'apiId': 'api-456',
                'identity': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        request_info = extract_request_info(event)
        
        assert request_info['source_ip'] == '203.0.113.1'  # First IP from X-Forwarded-For
        assert request_info['user_agent'] == 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        assert request_info['request_id'] == 'req-123'
        assert request_info['api_id'] == 'api-456'
    
    def test_extract_request_info_fallback_ip(self):
        """Test extracting request info with fallback IP."""
        event = {
            'headers': {},
            'requestContext': {
                'identity': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        request_info = extract_request_info(event)
        
        assert request_info['source_ip'] == '192.168.1.1'  # Fallback to identity.sourceIp
        assert request_info['user_agent'] is None
    
    def test_extract_request_info_empty_event(self):
        """Test extracting request info from empty event."""
        event = {}
        
        request_info = extract_request_info(event)
        
        assert request_info['source_ip'] is None
        assert request_info['user_agent'] is None
        assert request_info['request_id'] is None
        assert request_info['api_id'] is None


class TestSecurityEventTypes:
    """Test cases for security event types and risk levels."""
    
    def test_security_event_types(self):
        """Test SecurityEventType enum values."""
        assert SecurityEventType.LOGIN_SUCCESS.value == 'login_success'
        assert SecurityEventType.LOGIN_FAILURE.value == 'login_failure'
        assert SecurityEventType.PERMISSION_DENIED.value == 'permission_denied'
        assert SecurityEventType.SUSPICIOUS_ACTIVITY.value == 'suspicious_activity'
    
    def test_risk_levels(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == 'low'
        assert RiskLevel.MEDIUM.value == 'medium'
        assert RiskLevel.HIGH.value == 'high'
        assert RiskLevel.CRITICAL.value == 'critical'