"""
Public Profile and Contact Request data models for DynamoDB
"""
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class PublicProfile:
    """Public profile data model for external visibility"""

    profile_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    display_name: str = ""
    business_title: str = ""
    summary: str = ""
    skills: List[Dict] = field(default_factory=list)  # Detailed skills for search
    experiences: List[Dict] = field(default_factory=list)  # Experience details
    certifications: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    experience_years: int = 0
    location: str = ""
    availability: str = ""  # 'available', 'limited', 'not_available'
    preferred_roles: List[str] = field(default_factory=list)
    work_style: str = ""
    contact_preferences: Dict = field(
        default_factory=dict
    )  # {"allow_contact": bool, "preferred_method": str}
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_synced_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item format"""
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "business_title": self.business_title,
            "summary": self.summary,
            "skills": json.dumps(self.skills),
            "experiences": json.dumps(self.experiences),
            "certifications": json.dumps(self.certifications),
            "achievements": json.dumps(self.achievements),
            "experience_years": self.experience_years,
            "location": self.location,
            "availability": self.availability,
            "preferred_roles": json.dumps(self.preferred_roles),
            "work_style": self.work_style,
            "contact_preferences": json.dumps(self.contact_preferences),
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_synced_at": self.last_synced_at,
        }

    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> "PublicProfile":
        """Create instance from DynamoDB item"""
        return cls(
            profile_id=item["profile_id"],
            user_id=item.get("user_id", ""),
            display_name=item.get("display_name", ""),
            business_title=item.get("business_title", ""),
            summary=item.get("summary", ""),
            skills=json.loads(item.get("skills", "[]")),
            experiences=json.loads(item.get("experiences", "[]")),
            certifications=json.loads(item.get("certifications", "[]")),
            achievements=json.loads(item.get("achievements", "[]")),
            experience_years=int(item.get("experience_years", 0)),
            location=item.get("location", ""),
            availability=item.get("availability", ""),
            preferred_roles=json.loads(item.get("preferred_roles", "[]")),
            work_style=item.get("work_style", ""),
            contact_preferences=json.loads(item.get("contact_preferences", "{}")),
            is_active=item.get("is_active", True),
            created_at=item.get("created_at", datetime.utcnow().isoformat()),
            updated_at=item.get("updated_at", datetime.utcnow().isoformat()),
            last_synced_at=item.get("last_synced_at", datetime.utcnow().isoformat()),
        )

    def validate(self) -> List[str]:
        """Validate the public profile data and return list of errors"""
        errors = []

        if not self.user_id:
            errors.append("user_id is required")

        if not self.display_name:
            errors.append("display_name is required")

        if not self.business_title:
            errors.append("business_title is required")

        valid_availability = ["available", "limited", "not_available"]
        if self.availability and self.availability not in valid_availability:
            errors.append(
                f"availability must be one of: {', '.join(valid_availability)}"
            )

        if self.experience_years < 0:
            errors.append("experience_years cannot be negative")

        return errors

    def sync_from_veteran_profile(self, veteran_profile) -> None:
        """Sync data from veteran profile"""
        self.business_title = veteran_profile.business_title

        # Copy skills with details
        self.skills = veteran_profile.skills.copy() if veteran_profile.skills else []

        # Copy experiences
        self.experiences = (
            veteran_profile.experiences.copy() if veteran_profile.experiences else []
        )

        # Extract certifications from skills
        self.certifications = []
        for skill in self.skills:
            if skill.get("certifications"):
                self.certifications.extend(skill["certifications"])

        # Extract achievements from experiences
        self.achievements = []
        for exp in self.experiences:
            if exp.get("achievements"):
                self.achievements.extend(exp["achievements"])

        # Calculate total experience years
        total_years = sum(exp.get("duration", 0) for exp in self.experiences)
        self.experience_years = total_years

        # Copy preferences
        if hasattr(veteran_profile, "preferences") and veteran_profile.preferences:
            self.preferred_roles = veteran_profile.preferences.get(
                "preferred_roles", []
            )
            self.work_style = veteran_profile.preferences.get("work_style", "")

        # Update sync timestamp
        self.last_synced_at = datetime.utcnow().isoformat()
        self.updated_at = self.last_synced_at

    def update(self, **kwargs) -> None:
        """Update profile fields and set updated_at timestamp"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary format for API responses"""
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "business_title": self.business_title,
            "summary": self.summary,
            "skills": self.skills,
            "experiences": self.experiences,
            "certifications": self.certifications,
            "achievements": self.achievements,
            "experience_years": self.experience_years,
            "location": self.location,
            "availability": self.availability,
            "preferred_roles": self.preferred_roles,
            "work_style": self.work_style,
            "contact_preferences": self.contact_preferences,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_updated": self.updated_at,  # Alias for compatibility
        }


@dataclass
class ContactRequest:
    """Contact request data model for external recruiter communications"""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    profile_id: str = ""
    requester_name: str = ""
    requester_email: str = ""
    requester_company: str = ""
    message: str = ""
    opportunity_title: str = ""
    status: str = "pending"  # 'pending', 'forwarded', 'declined', 'spam'
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    processed_at: Optional[str] = None
    processed_by: Optional[str] = None
    response_notes: str = ""

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item format"""
        item = {
            "request_id": self.request_id,
            "profile_id": self.profile_id,
            "requester_name": self.requester_name,
            "requester_email": self.requester_email,
            "requester_company": self.requester_company,
            "message": self.message,
            "opportunity_title": self.opportunity_title,
            "status": self.status,
            "created_at": self.created_at,
            "response_notes": self.response_notes,
        }

        if self.processed_at:
            item["processed_at"] = self.processed_at
        if self.processed_by:
            item["processed_by"] = self.processed_by

        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> "ContactRequest":
        """Create instance from DynamoDB item"""
        return cls(
            request_id=item["request_id"],
            profile_id=item.get("profile_id", ""),
            requester_name=item.get("requester_name", ""),
            requester_email=item.get("requester_email", ""),
            requester_company=item.get("requester_company", ""),
            message=item.get("message", ""),
            opportunity_title=item.get("opportunity_title", ""),
            status=item.get("status", "pending"),
            created_at=item.get("created_at", datetime.utcnow().isoformat()),
            processed_at=item.get("processed_at"),
            processed_by=item.get("processed_by"),
            response_notes=item.get("response_notes", ""),
        )

    def validate(self) -> List[str]:
        """Validate the contact request data and return list of errors"""
        errors = []

        if not self.profile_id:
            errors.append("profile_id is required")

        if not self.requester_name:
            errors.append("requester_name is required")

        if not self.requester_email:
            errors.append("requester_email is required")

        if not self.message:
            errors.append("message is required")

        valid_statuses = ["pending", "forwarded", "declined", "spam"]
        if self.status not in valid_statuses:
            errors.append(f"status must be one of: {', '.join(valid_statuses)}")

        # Basic email validation
        if self.requester_email and "@" not in self.requester_email:
            errors.append("requester_email must be a valid email address")

        return errors

    def process(self, status: str, processor_id: str, notes: str = "") -> None:
        """Process the contact request"""
        self.status = status
        self.processed_at = datetime.utcnow().isoformat()
        self.processed_by = processor_id
        self.response_notes = notes

    def is_pending(self) -> bool:
        """Check if the contact request is still pending"""
        return self.status == "pending"
