"""
Application data model for DynamoDB
"""
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Application:
    """Application data model"""

    application_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    opportunity_id: str = ""
    status: str = "submitted"  # 'submitted', 'under_review', 'interview_scheduled', 'accepted', 'rejected', 'withdrawn'
    application_type: str = "interest"  # 'interest', 'formal_application'
    cover_letter: str = ""
    additional_notes: str = ""
    submitted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    reviewed_at: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_notes: str = ""

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item format"""
        item = {
            "application_id": self.application_id,
            "user_id": self.user_id,
            "opportunity_id": self.opportunity_id,
            "status": self.status,
            "application_type": self.application_type,
            "cover_letter": self.cover_letter,
            "additional_notes": self.additional_notes,
            "submitted_at": self.submitted_at,
            "updated_at": self.updated_at,
            "reviewer_notes": self.reviewer_notes,
        }

        if self.reviewed_at:
            item["reviewed_at"] = self.reviewed_at
        if self.reviewer_id:
            item["reviewer_id"] = self.reviewer_id

        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> "Application":
        """Create instance from DynamoDB item"""
        return cls(
            application_id=item["application_id"],
            user_id=item.get("user_id", ""),
            opportunity_id=item.get("opportunity_id", ""),
            status=item.get("status", "submitted"),
            application_type=item.get("application_type", "interest"),
            cover_letter=item.get("cover_letter", ""),
            additional_notes=item.get("additional_notes", ""),
            submitted_at=item.get("submitted_at", datetime.utcnow().isoformat()),
            updated_at=item.get("updated_at", datetime.utcnow().isoformat()),
            reviewed_at=item.get("reviewed_at"),
            reviewer_id=item.get("reviewer_id"),
            reviewer_notes=item.get("reviewer_notes", ""),
        )

    def validate(self) -> List[str]:
        """Validate the application data and return list of errors"""
        errors = []

        if not self.user_id:
            errors.append("user_id is required")

        if not self.opportunity_id:
            errors.append("opportunity_id is required")

        valid_statuses = [
            "submitted",
            "under_review",
            "interview_scheduled",
            "accepted",
            "rejected",
            "withdrawn",
        ]
        if self.status not in valid_statuses:
            errors.append(f"status must be one of: {', '.join(valid_statuses)}")

        valid_types = ["interest", "formal_application"]
        if self.application_type not in valid_types:
            errors.append(f"application_type must be one of: {', '.join(valid_types)}")

        return errors

    def update_status(
        self, new_status: str, reviewer_id: Optional[str] = None, notes: str = ""
    ) -> None:
        """Update application status with reviewer information"""
        self.status = new_status
        self.updated_at = datetime.utcnow().isoformat()

        if reviewer_id:
            self.reviewer_id = reviewer_id
            self.reviewed_at = self.updated_at

        if notes:
            self.reviewer_notes = notes

    def withdraw(self) -> None:
        """Withdraw the application"""
        self.status = "withdrawn"
        self.updated_at = datetime.utcnow().isoformat()

    def is_active(self) -> bool:
        """Check if the application is still active (not in final state)"""
        final_states = ["accepted", "rejected", "withdrawn"]
        return self.status not in final_states
