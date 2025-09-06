"""
Unit tests for Contact Handler
"""

import json
from unittest.mock import Mock, patch


from src.handlers.contact_handler import ContactHandler
from src.models.public_profile import ContactRequest


class TestContactHandler:
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = ContactHandler()

        # Mock profile data
        self.mock_profile = {
            "profile_id": "profile_123",
            "user_id": "user_123",
            "display_name": "John Doe",
            "business_title": "Senior Software Engineer",
            "contact_preferences": {"allow_contact": True},
            "is_active": True,
        }

        # Mock contact request data
        self.mock_contact_request = ContactRequest(
            request_id="req_123",
            profile_id="profile_123",
            requester_name="Jane Smith",
            requester_email="jane@company.com",
            requester_company="Tech Corp",
            message="We have an exciting opportunity for you",
            opportunity_title="Senior Developer Position",
            status="pending",
        )

        # Mock user data
        self.mock_user = {
            "user_id": "user_123",
            "email": "john@honda.com",
            "role": "veteran",
        }

    @patch("src.handlers.contact_handler.ContactRequestRepository")
    @patch("src.handlers.contact_handler.PublicProfileRepository")
    @patch("src.handlers.contact_handler.audit_security_event")
    def test_submit_contact_request_success(
        self, mock_log, mock_profile_repo_class, mock_contact_repo_class
    ):
        """Test successful contact request submission"""
        # Setup
        mock_profile_repo = Mock()
        mock_profile_repo_class.return_value = mock_profile_repo
        mock_profile_repo.get_public_profile.return_value = self.mock_profile

        mock_contact_repo = Mock()
        mock_contact_repo_class.return_value = mock_contact_repo
        mock_contact_repo.create_request.return_value = True

        event = {
            "pathParameters": {"profileId": "profile_123"},
            "body": json.dumps(
                {
                    "requester_name": "Jane Smith",
                    "requester_email": "jane@company.com",
                    "requester_company": "Tech Corp",
                    "message": "We have an exciting opportunity for you",
                    "opportunity_title": "Senior Developer Position",
                }
            ),
        }

        # Execute
        handler = ContactHandler()
        result = handler.submit_contact_request(event, {})

        # Verify
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert "request_id" in body
        assert body["status"] == "submitted"

        # Verify repository calls
        mock_profile_repo.get_public_profile.assert_called_once_with("profile_123")
        mock_contact_repo.create_request.assert_called_once()
        mock_log.assert_called_once()

    @patch("src.handlers.contact_handler.PublicProfileRepository")
    def test_submit_contact_request_profile_not_found(self, mock_profile_repo_class):
        """Test contact request with non-existent profile"""
        # Setup
        mock_profile_repo = Mock()
        mock_profile_repo_class.return_value = mock_profile_repo
        mock_profile_repo.get_public_profile.return_value = None

        event = {
            "pathParameters": {"profileId": "nonexistent"},
            "body": json.dumps(
                {
                    "requester_name": "Jane Smith",
                    "requester_email": "jane@company.com",
                    "requester_company": "Tech Corp",
                    "message": "Test message",
                }
            ),
        }

        # Execute
        handler = ContactHandler()
        result = handler.submit_contact_request(event, {})

        # Verify
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "Profile not found" in body["error"]

    @patch("src.handlers.contact_handler.PublicProfileRepository")
    def test_submit_contact_request_contact_disabled(self, mock_profile_repo_class):
        """Test contact request when contact is disabled"""
        # Setup
        mock_profile_repo = Mock()
        mock_profile_repo_class.return_value = mock_profile_repo

        profile_no_contact = self.mock_profile.copy()
        profile_no_contact["contact_preferences"] = {"allow_contact": False}
        mock_profile_repo.get_public_profile.return_value = profile_no_contact

        event = {
            "pathParameters": {"profileId": "profile_123"},
            "body": json.dumps(
                {
                    "requester_name": "Jane Smith",
                    "requester_email": "jane@company.com",
                    "requester_company": "Tech Corp",
                    "message": "Test message",
                }
            ),
        }

        # Execute
        handler = ContactHandler()
        result = handler.submit_contact_request(event, {})

        # Verify
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert "Contact not allowed" in body["error"]

    def test_submit_contact_request_missing_fields(self):
        """Test contact request with missing required fields"""
        event = {
            "pathParameters": {"profileId": "profile_123"},
            "body": json.dumps(
                {
                    "requester_name": "Jane Smith",
                    # Missing required fields
                }
            ),
        }

        result = self.handler.submit_contact_request(event, {})

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing required fields" in body["error"]
        assert "missing_fields" in body

    def test_submit_contact_request_invalid_json(self):
        """Test contact request with invalid JSON"""
        event = {"pathParameters": {"profileId": "profile_123"}, "body": "invalid json"}

        result = self.handler.submit_contact_request(event, {})

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Invalid JSON" in body["error"]

    @patch("src.handlers.contact_handler.ContactRequestRepository")
    @patch("src.handlers.contact_handler.PublicProfileRepository")
    def test_submit_contact_request_rate_limited(
        self, mock_profile_repo_class, mock_contact_repo_class
    ):
        """Test rate limiting functionality"""
        # Setup
        mock_profile_repo = Mock()
        mock_profile_repo_class.return_value = mock_profile_repo
        mock_profile_repo.get_public_profile.return_value = self.mock_profile

        mock_contact_repo = Mock()
        mock_contact_repo_class.return_value = mock_contact_repo

        # Mock recent requests to trigger rate limit
        recent_requests = [
            Mock(requester_email="jane@company.com", profile_id="profile_123")
            for _ in range(3)
        ]
        mock_contact_repo.get_recent_requests.return_value = recent_requests

        # Mock the handler's rate limit check
        handler = ContactHandler()
        handler._is_rate_limited = Mock(return_value=True)

        event = {
            "pathParameters": {"profileId": "profile_123"},
            "body": json.dumps(
                {
                    "requester_name": "Jane Smith",
                    "requester_email": "jane@company.com",
                    "requester_company": "Tech Corp",
                    "message": "Test message",
                }
            ),
        }

        # Execute
        result = handler.submit_contact_request(event, {})

        # Verify
        assert result["statusCode"] == 429
        body = json.loads(result["body"])
        assert "Rate limit exceeded" in body["error"]

    @patch("src.handlers.contact_handler.ContactRequestRepository")
    @patch("src.handlers.contact_handler.PublicProfileRepository")
    def test_get_contact_requests_success(
        self, mock_profile_repo_class, mock_contact_repo_class
    ):
        """Test successful retrieval of contact requests"""
        # Setup
        mock_profile_repo = Mock()
        mock_profile_repo_class.return_value = mock_profile_repo
        mock_profile_repo.get_profile_by_user_id.return_value = Mock(
            profile_id="profile_123"
        )

        mock_contact_repo = Mock()
        mock_contact_repo_class.return_value = mock_contact_repo
        mock_contact_repo.get_requests_for_profile.return_value = [
            self.mock_contact_request
        ]

        event = {"user": self.mock_user}

        # Execute
        handler = ContactHandler()
        result = handler.get_contact_requests(event, {})

        # Verify
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "requests" in body
        assert body["total_count"] == 1
        assert body["requests"][0]["request_id"] == "req_123"

    def test_get_contact_requests_no_auth(self):
        """Test contact requests retrieval without authentication"""
        event = {}  # No user

        result = self.handler.get_contact_requests(event, {})

        assert result["statusCode"] == 401
        body = json.loads(result["body"])
        assert "Authentication required" in body["error"]

    @patch("src.handlers.contact_handler.ContactRequestRepository")
    @patch("src.handlers.contact_handler.PublicProfileRepository")
    @patch("src.handlers.contact_handler.audit_security_event")
    def test_process_contact_request_approve(
        self, mock_log, mock_profile_repo_class, mock_contact_repo_class
    ):
        """Test approving a contact request"""
        # Setup
        mock_contact_repo = Mock()
        mock_contact_repo_class.return_value = mock_contact_repo
        mock_contact_repo.get_request.return_value = self.mock_contact_request
        mock_contact_repo.process_request.return_value = True

        mock_profile_repo = Mock()
        mock_profile_repo_class.return_value = mock_profile_repo
        mock_profile_repo.get_profile.return_value = self.mock_profile

        event = {
            "user": self.mock_user,
            "pathParameters": {"requestId": "req_123"},
            "body": json.dumps(
                {"action": "approve", "notes": "Looks like a good opportunity"}
            ),
        }

        # Execute
        handler = ContactHandler()
        result = handler.process_contact_request(event, {})

        # Verify
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "forwarded"

        # Verify repository calls
        mock_contact_repo.process_request.assert_called_once_with(
            "req_123", "forwarded", "user_123", "Looks like a good opportunity"
        )
        mock_log.assert_called_once()

    @patch("src.handlers.contact_handler.ContactRequestRepository")
    def test_process_contact_request_invalid_action(self, mock_contact_repo_class):
        """Test processing contact request with invalid action"""
        event = {
            "user": self.mock_user,
            "pathParameters": {"requestId": "req_123"},
            "body": json.dumps({"action": "invalid_action"}),
        }

        result = self.handler.process_contact_request(event, {})

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Invalid action" in body["error"]

    @patch("src.handlers.contact_handler.ContactRequestRepository")
    def test_process_contact_request_not_found(self, mock_contact_repo_class):
        """Test processing non-existent contact request"""
        # Setup
        mock_contact_repo = Mock()
        mock_contact_repo_class.return_value = mock_contact_repo
        mock_contact_repo.get_request.return_value = None

        event = {
            "user": self.mock_user,
            "pathParameters": {"requestId": "nonexistent"},
            "body": json.dumps({"action": "approve"}),
        }

        # Execute
        handler = ContactHandler()
        result = handler.process_contact_request(event, {})

        # Verify
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "Contact request not found" in body["error"]

    @patch("src.handlers.contact_handler.ContactRequestRepository")
    def test_get_contact_statistics_success(self, mock_contact_repo_class):
        """Test successful statistics retrieval"""
        # Setup
        mock_contact_repo = Mock()
        mock_contact_repo_class.return_value = mock_contact_repo
        mock_stats = {
            "total": 100,
            "by_status": {"pending": 20, "forwarded": 60, "declined": 20},
            "by_company": {"Tech Corp": 30, "Other Corp": 70},
        }
        mock_contact_repo.get_request_statistics.return_value = mock_stats

        admin_user = self.mock_user.copy()
        admin_user["role"] = "admin"

        event = {"user": admin_user}

        # Execute
        handler = ContactHandler()
        result = handler.get_contact_statistics(event, {})

        # Verify
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["statistics"] == mock_stats

    def test_get_contact_statistics_non_admin(self):
        """Test statistics retrieval by non-admin user"""
        event = {"user": self.mock_user}  # Regular user, not admin

        result = self.handler.get_contact_statistics(event, {})

        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert "Admin access required" in body["error"]

    def test_is_rate_limited(self):
        """Test rate limiting logic"""
        # Mock recent requests
        recent_requests = [
            Mock(requester_email="jane@company.com", profile_id="profile_123")
            for _ in range(3)
        ]

        self.handler.contact_repo.get_recent_requests = Mock(
            return_value=recent_requests
        )

        # Should be rate limited (3 requests >= limit)
        assert self.handler._is_rate_limited("jane@company.com", "profile_123") == True

        # Different email should not be rate limited
        assert (
            self.handler._is_rate_limited("other@company.com", "profile_123") == False
        )

    def test_simple_spam_detection(self):
        """Test simple spam detection"""
        # High spam content
        spam_request = {
            "message": "guaranteed income work from home no experience required",
            "requester_company": "make money fast corp",
        }

        spam_score = self.handler._simple_spam_detection(spam_request)
        assert spam_score >= 0.7  # Should be high spam score

        # Normal content
        normal_request = {
            "message": "We have a software engineering position that matches your skills",
            "requester_company": "Honda Motors",
        }

        normal_score = self.handler._simple_spam_detection(normal_request)
        assert normal_score <= 0.4  # Should be low spam score

    @patch("src.handlers.contact_handler.BedrockClient")
    def test_detect_spam_with_ai(self, mock_bedrock_class):
        """Test AI-based spam detection"""
        # Setup
        mock_bedrock = Mock()
        mock_bedrock_class.return_value = mock_bedrock
        mock_bedrock.generate_text.return_value = "0.8"

        request_data = {"message": "Test message", "requester_company": "Test Corp"}

        # Execute
        handler = ContactHandler()
        spam_score = handler._detect_spam(request_data)

        # Verify
        assert spam_score == 0.8
        mock_bedrock.generate_text.assert_called_once()

    def test_get_cors_headers(self):
        """Test CORS headers"""
        headers = self.handler._get_cors_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Access-Control-Allow-Origin"] == "*"
        assert "Access-Control-Allow-Headers" in headers
        assert "Access-Control-Allow-Methods" in headers


# Test Lambda function handlers
class TestLambdaHandlers:
    @patch("src.handlers.contact_handler.ContactHandler")
    def test_submit_contact_request_lambda(self, mock_handler_class):
        """Test submit contact request Lambda handler"""
        from src.handlers.contact_handler import submit_contact_request

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.submit_contact_request.return_value = {"statusCode": 201}

        event = {}
        context = {}

        result = submit_contact_request(event, context)

        assert result["statusCode"] == 201
        mock_handler.submit_contact_request.assert_called_once_with(event, context)

    @patch("src.handlers.contact_handler.ContactHandler")
    def test_get_contact_requests_lambda(self, mock_handler_class):
        """Test get contact requests Lambda handler"""
        from src.handlers.contact_handler import get_contact_requests

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.get_contact_requests.return_value = {"statusCode": 200}

        event = {}
        context = {}

        result = get_contact_requests(event, context)

        assert result["statusCode"] == 200
        mock_handler.get_contact_requests.assert_called_once_with(event, context)

    @patch("src.handlers.contact_handler.ContactHandler")
    def test_process_contact_request_lambda(self, mock_handler_class):
        """Test process contact request Lambda handler"""
        from src.handlers.contact_handler import process_contact_request

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.process_contact_request.return_value = {"statusCode": 200}

        event = {}
        context = {}

        result = process_contact_request(event, context)

        assert result["statusCode"] == 200
        mock_handler.process_contact_request.assert_called_once_with(event, context)

    @patch("src.handlers.contact_handler.ContactHandler")
    def test_get_contact_statistics_lambda(self, mock_handler_class):
        """Test get contact statistics Lambda handler"""
        from src.handlers.contact_handler import get_contact_statistics

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.get_contact_statistics.return_value = {"statusCode": 200}

        event = {}
        context = {}

        result = get_contact_statistics(event, context)

        assert result["statusCode"] == 200
        mock_handler.get_contact_statistics.assert_called_once_with(event, context)
