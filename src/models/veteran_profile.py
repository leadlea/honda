"""
Veteran Profile data model for DynamoDB
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class VeteranProfile:
    """Veteran profile data model"""

    user_id: str
    business_title: str = ""
    skills: List[Dict] = field(
        default_factory=list
    )  # [{"name": str, "level": str, "years": int, "certifications": List[str]}]
    experiences: List[Dict] = field(
        default_factory=list
    )  # [{"title": str, "department": str, "duration": int, "achievements": List[str]}]
    preferences: Dict = field(
        default_factory=dict
    )  # {"preferred_roles": List[str], "work_style": str, "locations": List[str]}
    privacy_settings: Dict = field(
        default_factory=dict
    )  # {"is_publicly_visible": bool, "external_contact": bool}
    questionnaire_responses: List[Dict] = field(default_factory=list)
    is_publicly_visible: str = "false"  # "true" or "false" for GSI
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item format"""
        return {
            "user_id": self.user_id,
            "business_title": self.business_title,
            "skills": json.dumps(self.skills),
            "experiences": json.dumps(self.experiences),
            "preferences": json.dumps(self.preferences),
            "privacy_settings": json.dumps(self.privacy_settings),
            "questionnaire_responses": json.dumps(self.questionnaire_responses),
            "is_publicly_visible": self.is_publicly_visible,
            "last_updated": self.last_updated,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> "VeteranProfile":
        """Create instance from DynamoDB item"""
        # DynamoDBは既にPythonのネイティブ型で返すので、json.loads()は不要
        # ただし、文字列として保存されている場合もあるので、両方に対応
        def parse_field(value, default):
            if value is None:
                return default
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return default
            return value
        
        return cls(
            user_id=item["user_id"],
            business_title=item.get("business_title", ""),
            skills=parse_field(item.get("skills"), []),
            experiences=parse_field(item.get("experiences"), []),
            preferences=parse_field(item.get("preferences"), {}),
            privacy_settings=parse_field(item.get("privacy_settings"), {}),
            questionnaire_responses=parse_field(item.get("questionnaire_responses"), []),
            is_publicly_visible=item.get("is_publicly_visible", "false"),
            last_updated=item.get("last_updated", datetime.utcnow().isoformat()),
            created_at=item.get("created_at", datetime.utcnow().isoformat()),
        )

    def validate(self) -> List[str]:
        """Validate the profile data and return list of errors"""
        errors = []

        if not self.user_id:
            errors.append("user_id is required")

        # Validate skills format
        for skill in self.skills:
            if not isinstance(skill, dict):
                errors.append("Each skill must be a dictionary")
                continue
            required_fields = ["name", "level", "years"]
            for field_name in required_fields:
                if field_name not in skill:
                    errors.append(f"Skill missing required field: {field_name}")

        # Validate experiences format
        for exp in self.experiences:
            if not isinstance(exp, dict):
                errors.append("Each experience must be a dictionary")
                continue
            required_fields = ["title", "department", "duration"]
            for field_name in required_fields:
                if field_name not in exp:
                    errors.append(f"Experience missing required field: {field_name}")

        # Validate privacy settings
        if self.privacy_settings:
            if "is_publicly_visible" in self.privacy_settings:
                if not isinstance(self.privacy_settings["is_publicly_visible"], bool):
                    errors.append(
                        "privacy_settings.is_publicly_visible must be boolean"
                    )

        return errors

    def update_privacy_settings(self, settings: Dict) -> None:
        """Update privacy settings and sync is_publicly_visible field"""
        self.privacy_settings.update(settings)
        if "is_publicly_visible" in settings:
            self.is_publicly_visible = (
                "true" if settings["is_publicly_visible"] else "false"
            )
        self.last_updated = datetime.utcnow().isoformat()
