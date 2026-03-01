"""
双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）
問い合わせハンドラー - AIポジションオーナーとのコミュニケーション管理

AIポジションオーナー（各部門／AI CoE）と社内AI人材候補間の
問い合わせリクエストおよびコミュニケーションを管理します。
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from src.models.public_profile import ContactRequest
from src.repositories.public_profile_repository import (
    ContactRequestRepository,
    PublicProfileRepository,
)
from src.repositories.user_repository import UserRepository
from src.services.bedrock_client import BedrockClient
from src.utils.security_audit import RiskLevel, SecurityEventType, audit_security_event

logger = logging.getLogger(__name__)


class ContactHandler:
    def __init__(self):
        self.contact_repo = ContactRequestRepository()
        self.profile_repo = PublicProfileRepository()
        self.user_repo = UserRepository()
        self.bedrock_client = BedrockClient()

    def submit_contact_request(self, event: Dict, context: Any) -> Dict:
        """
        AIポジションオーナーからの問い合わせリクエスト送信を処理します。
        社内AI人材候補への接触申請を管理します。
        """
        try:
            # Parse request body
            body = json.loads(event.get("body", "{}"))
            profile_id = event["pathParameters"]["profileId"]

            # Validate required fields
            required_fields = [
                "requester_name",
                "requester_email",
                "requester_company",
                "message",
            ]
            missing_fields = [field for field in required_fields if not body.get(field)]

            if missing_fields:
                return {
                    "statusCode": 400,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps(
                        {
                            "error": "Missing required fields",
                            "missing_fields": missing_fields,
                        }
                    ),
                }

            # Verify profile exists and is publicly accessible
            profile = self.profile_repo.get_public_profile(profile_id)
            if not profile:
                return {
                    "statusCode": 404,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps(
                        {
                            "error": "Profile not found",
                            "message": "The requested veteran profile is not available",
                        }
                    ),
                }

            # Check if profile allows contact
            contact_prefs = profile.get("contact_preferences", {})
            if not contact_prefs.get("allow_contact", True):
                return {
                    "statusCode": 403,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps(
                        {
                            "error": "問い合わせ不可",
                            "message": "この社内AI人材候補は外部からの問い合わせを無効にしています",
                        }
                    ),
                }

            # Rate limiting check
            if self._is_rate_limited(body["requester_email"], profile_id):
                return {
                    "statusCode": 429,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps(
                        {
                            "error": "Rate limit exceeded",
                            "message": "Too many contact requests. Please wait before sending another request.",
                        }
                    ),
                }

            # Spam detection
            spam_score = self._detect_spam(body)
            if spam_score > 0.8:
                # Auto-reject high spam score
                audit_security_event(
                    SecurityEventType.SUSPICIOUS_ACTIVITY,
                    body["requester_email"],
                    RiskLevel.HIGH,
                    action="spam_contact_request_blocked",
                    details={"profile_id": profile_id, "spam_score": spam_score},
                )
                return {
                    "statusCode": 400,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps(
                        {
                            "error": "Request rejected",
                            "message": "Your request could not be processed",
                        }
                    ),
                }

            # Create contact request
            contact_request = ContactRequest(
                profile_id=profile_id,
                requester_name=body["requester_name"],
                requester_email=body["requester_email"],
                requester_company=body.get("requester_company", ""),
                message=body["message"],
                opportunity_title=body.get("opportunity_title", ""),
                status="pending",
            )

            # Save to database
            success = self.contact_repo.create_request(contact_request)

            if not success:
                return {
                    "statusCode": 500,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps(
                        {
                            "error": "Failed to submit request",
                            "message": "Unable to process your contact request at this time",
                        }
                    ),
                }

            # Send notification to veteran (async)
            self._notify_veteran_of_contact_request(profile, contact_request)

            # Log security event
            audit_security_event(
                SecurityEventType.EXTERNAL_ACCESS,
                body["requester_email"],
                RiskLevel.MEDIUM,
                action="contact_request_submitted",
                details={
                    "profile_id": profile_id,
                    "request_id": contact_request.request_id,
                    "company": body.get("requester_company", ""),
                },
            )

            return {
                "statusCode": 201,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "request_id": contact_request.request_id,
                        "status": "submitted",
                        "message": "Your contact request has been submitted and will be reviewed.",
                    }
                ),
            }

        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "error": "Invalid JSON",
                        "message": "Request body must be valid JSON",
                    }
                ),
            }
        except Exception as e:
            logger.error(f"Error in submit_contact_request: {str(e)}")
            return {
                "statusCode": 500,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "error": "Internal server error",
                        "message": "Failed to process contact request",
                    }
                ),
            }

    def get_contact_requests(self, event: Dict, context: Any) -> Dict:
        """
        社内AI人材候補向けの問い合わせリクエストを取得します（内部利用）。
        認証が必要です。
        """
        try:
            # This would require authentication in a real implementation
            user = event.get("user")  # From auth middleware
            if not user:
                return {
                    "statusCode": 401,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps({"error": "Authentication required"}),
                }

            # Get user's public profile
            profile = self.profile_repo.get_profile_by_user_id(user["user_id"])
            if not profile:
                return {
                    "statusCode": 404,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps({"error": "Profile not found"}),
                }

            # Get contact requests
            requests = self.contact_repo.get_requests_for_profile(profile.profile_id)

            # Format requests for response
            formatted_requests = []
            for req in requests:
                formatted_requests.append(
                    {
                        "request_id": req.request_id,
                        "requester_name": req.requester_name,
                        "requester_company": req.requester_company,
                        "opportunity_title": req.opportunity_title,
                        "message": req.message,
                        "status": req.status,
                        "created_at": req.created_at,
                        "processed_at": req.processed_at,
                    }
                )

            return {
                "statusCode": 200,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "requests": formatted_requests,
                        "total_count": len(formatted_requests),
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Error in get_contact_requests: {str(e)}")
            return {
                "statusCode": 500,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "error": "Internal server error",
                        "message": "Failed to retrieve contact requests",
                    }
                ),
            }

    def process_contact_request(self, event: Dict, context: Any) -> Dict:
        """
        問い合わせリクエストを処理します（承認／拒否）。
        社内AI人材候補の認証が必要です。
        """
        try:
            user = event.get("user")
            if not user:
                return {
                    "statusCode": 401,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps({"error": "Authentication required"}),
                }

            request_id = event["pathParameters"]["requestId"]
            body = json.loads(event.get("body", "{}"))

            action = body.get("action")  # 'approve', 'decline', 'spam'
            notes = body.get("notes", "")

            if action not in ["approve", "decline", "spam"]:
                return {
                    "statusCode": 400,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps(
                        {
                            "error": "Invalid action",
                            "message": "Action must be approve, decline, or spam",
                        }
                    ),
                }

            # Get contact request
            contact_request = self.contact_repo.get_request(request_id)
            if not contact_request:
                return {
                    "statusCode": 404,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps({"error": "Contact request not found"}),
                }

            # Verify user owns the profile
            profile = self.profile_repo.get_profile(contact_request.profile_id)
            if not profile or profile.get("user_id") != user["user_id"]:
                return {
                    "statusCode": 403,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps({"error": "Access denied"}),
                }

            # Process the request
            status_map = {"approve": "forwarded", "decline": "declined", "spam": "spam"}

            success = self.contact_repo.process_request(
                request_id, status_map[action], user["user_id"], notes
            )

            if not success:
                return {
                    "statusCode": 500,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps({"error": "Failed to process request"}),
                }

            # If approved, facilitate contact
            if action == "approve":
                self._facilitate_contact(contact_request, user, notes)

            # Log the action
            audit_security_event(
                SecurityEventType.ADMIN_ACTION,
                user["user_id"],
                RiskLevel.MEDIUM,
                action=f"contact_request_{action}",
                details={
                    "request_id": request_id,
                    "requester_email": contact_request.requester_email,
                },
            )

            return {
                "statusCode": 200,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "request_id": request_id,
                        "status": status_map[action],
                        "message": f"Contact request has been {action}d",
                    }
                ),
            }

        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "headers": self._get_cors_headers(),
                "body": json.dumps({"error": "Invalid JSON"}),
            }
        except Exception as e:
            logger.error(f"Error in process_contact_request: {str(e)}")
            return {
                "statusCode": 500,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "error": "Internal server error",
                        "message": "Failed to process contact request",
                    }
                ),
            }

    def get_contact_statistics(self, event: Dict, context: Any) -> Dict:
        """
        問い合わせリクエストの統計を取得します（管理者専用）。
        AI人材発掘・配置マッチングMVPの問い合わせ状況を把握します。
        """
        try:
            user = event.get("user")
            if not user or user.get("role") != "admin":
                return {
                    "statusCode": 403,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps({"error": "Admin access required"}),
                }

            stats = self.contact_repo.get_request_statistics()

            return {
                "statusCode": 200,
                "headers": self._get_cors_headers(),
                "body": json.dumps({"statistics": stats}),
            }

        except Exception as e:
            logger.error(f"Error in get_contact_statistics: {str(e)}")
            return {
                "statusCode": 500,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "error": "Internal server error",
                        "message": "Failed to retrieve statistics",
                    }
                ),
            }

    def _is_rate_limited(self, requester_email: str, profile_id: str) -> bool:
        """問い合わせ送信者のレート制限をチェックします"""
        try:
            # Get recent requests from this email to this profile
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            # This is a simplified check - in production, you'd use a proper rate limiting service
            recent_requests = self.contact_repo.get_recent_requests(days=1)

            email_requests = [
                req
                for req in recent_requests
                if req.requester_email == requester_email
                and req.profile_id == profile_id
            ]

            # Allow max 3 requests per email per profile per day
            return len(email_requests) >= 3

        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False  # Don't block on error

    def _detect_spam(self, request_data: Dict) -> float:
        """
        AIを使用して問い合わせリクエストのスパムを検出します。
        スパムスコア（0.0〜1.0）を返します。
        """
        try:
            # Use AI to analyze the message for spam indicators
            prompt = f"""
Analyze this contact request for spam indicators. Consider:
1. Generic/template language
2. Suspicious links or contact information
3. Unrealistic job offers
4. Poor grammar/spelling (if excessive)
5. Overly promotional language

Contact Request:
Company: {request_data.get('requester_company', '')}
Name: {request_data.get('requester_name', '')}
Email: {request_data.get('requester_email', '')}
Message: {request_data.get('message', '')}
Opportunity: {request_data.get('opportunity_title', '')}

Return only a spam score between 0.0 (definitely not spam) and 1.0 (definitely spam).
Score: """

            response = self.bedrock_client.generate_text(
                prompt=prompt, max_tokens=50, temperature=0.1
            )

            # Extract score from response
            try:
                score_text = response.strip()
                # Look for a number between 0 and 1
                import re

                score_match = re.search(r"(\d+\.?\d*)", score_text)
                if score_match:
                    score = float(score_match.group(1))
                    return min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
            except Exception:  # nosec B110
                pass

            # Fallback: simple keyword-based detection
            return self._simple_spam_detection(request_data)

        except Exception as e:
            logger.error(f"Error in spam detection: {str(e)}")
            return 0.0  # Don't block on error

    def _simple_spam_detection(self, request_data: Dict) -> float:
        """シンプルなキーワードベースのスパム検出フォールバック"""
        spam_keywords = [
            "guaranteed income",
            "work from home",
            "no experience required",
            "click here",
            "limited time",
            "act now",
            "make money fast",
            "free money",
            "earn $",
            "investment opportunity",
        ]

        message = request_data.get("message", "").lower()
        company = request_data.get("requester_company", "").lower()

        spam_count = sum(
            1 for keyword in spam_keywords if keyword in message or keyword in company
        )

        # Simple scoring based on keyword count
        if spam_count >= 3:
            return 0.9
        elif spam_count >= 2:
            return 0.7
        elif spam_count >= 1:
            return 0.4
        else:
            return 0.1

    def _notify_veteran_of_contact_request(
        self, profile: Dict, contact_request: ContactRequest
    ):
        """社内AI人材候補に新しい問い合わせリクエストの通知を送信します"""
        try:
            # In a real implementation, this would send an email or push notification
            # For now, we'll just log it
            logger.info(
                f"Notification: New contact request for profile {profile['profile_id']} "
                f"from {contact_request.requester_company}"
            )

            # You could integrate with AWS SES, SNS, or other notification services here

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")

    def _facilitate_contact(
        self, contact_request: ContactRequest, veteran_user: Dict, notes: str
    ):
        """AIポジションオーナーと社内AI人材候補間の接触を仲介します"""
        try:
            # In a real implementation, this might:
            # 1. Send veteran's contact info to recruiter
            # 2. Send recruiter's info to veteran
            # 3. Set up a secure communication channel

            logger.info(
                f"Facilitating contact between {contact_request.requester_email} "
                f"and veteran {veteran_user['user_id']}"
            )

            # For now, just log the facilitation

        except Exception as e:
            logger.error(f"Error facilitating contact: {str(e)}")

    def _get_cors_headers(self) -> Dict:
        """外部API（問い合わせ機能）アクセス用CORSヘッダーを取得します"""
        return {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
        }


# Lambda function handlers
def submit_contact_request(event, context):
    """問い合わせリクエスト送信のLambdaハンドラー"""
    handler = ContactHandler()
    return handler.submit_contact_request(event, context)


def get_contact_requests(event, context):
    """問い合わせリクエスト取得のLambdaハンドラー"""
    handler = ContactHandler()
    return handler.get_contact_requests(event, context)


def process_contact_request(event, context):
    """問い合わせリクエスト処理のLambdaハンドラー"""
    handler = ContactHandler()
    return handler.process_contact_request(event, context)


def get_contact_statistics(event, context):
    """問い合わせ統計取得のLambdaハンドラー"""
    handler = ContactHandler()
    return handler.get_contact_statistics(event, context)
