"""
Recommendation data model for DynamoDB
"""
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Recommendation:
    """Recommendation data model"""

    user_id: str
    recommendation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    opportunity_id: str = ""
    match_score: float = 0.0
    match_reasons: List[Dict] = field(
        default_factory=list
    )  # [{"category": str, "description": str, "weight": float}]
    status: str = "generated"  # 'generated', 'viewed', 'applied', 'dismissed'
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    viewed_at: Optional[str] = None
    applied_at: Optional[str] = None
    dismissed_at: Optional[str] = None

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item format"""
        item = {
            "user_id": self.user_id,
            "recommendation_id": self.recommendation_id,
            "opportunity_id": self.opportunity_id,
            "match_score": self.match_score,
            "match_reasons": json.dumps(self.match_reasons),
            "status": self.status,
            "generated_at": self.generated_at,
        }

        if self.viewed_at:
            item["viewed_at"] = self.viewed_at
        if self.applied_at:
            item["applied_at"] = self.applied_at
        if self.dismissed_at:
            item["dismissed_at"] = self.dismissed_at

        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> "Recommendation":
        """Create instance from DynamoDB item"""
        return cls(
            user_id=item["user_id"],
            recommendation_id=item["recommendation_id"],
            opportunity_id=item.get("opportunity_id", ""),
            match_score=float(item.get("match_score", 0.0)),
            match_reasons=json.loads(item.get("match_reasons", "[]")),
            status=item.get("status", "generated"),
            generated_at=item.get("generated_at", datetime.utcnow().isoformat()),
            viewed_at=item.get("viewed_at"),
            applied_at=item.get("applied_at"),
            dismissed_at=item.get("dismissed_at"),
        )

    def validate(self) -> List[str]:
        """Validate the recommendation data and return list of errors"""
        errors = []

        if not self.user_id:
            errors.append("user_id is required")

        if not self.opportunity_id:
            errors.append("opportunity_id is required")

        if not isinstance(self.match_score, (int, float)):
            errors.append("match_score must be a number")
        elif not (0.0 <= self.match_score <= 1.0):
            errors.append("match_score must be between 0.0 and 1.0")

        valid_statuses = ["generated", "viewed", "applied", "dismissed"]
        if self.status not in valid_statuses:
            errors.append(f"status must be one of: {', '.join(valid_statuses)}")

        # Validate match reasons format
        for reason in self.match_reasons:
            if not isinstance(reason, dict):
                errors.append("Each match reason must be a dictionary")
                continue
            required_fields = ["category", "description", "weight"]
            for field_name in required_fields:
                if field_name not in reason:
                    errors.append(f"Match reason missing required field: {field_name}")

            if "weight" in reason and not isinstance(reason["weight"], (int, float)):
                errors.append("Match reason weight must be a number")

        return errors

    def mark_viewed(self) -> None:
        """Mark recommendation as viewed"""
        if self.status == "generated":
            self.status = "viewed"
            self.viewed_at = datetime.utcnow().isoformat()

    def mark_applied(self) -> None:
        """Mark recommendation as applied"""
        self.status = "applied"
        self.applied_at = datetime.utcnow().isoformat()
        if not self.viewed_at:
            self.viewed_at = self.applied_at

    def mark_dismissed(self) -> None:
        """Mark recommendation as dismissed"""
        self.status = "dismissed"
        self.dismissed_at = datetime.utcnow().isoformat()
        if not self.viewed_at:
            self.viewed_at = self.dismissed_at
