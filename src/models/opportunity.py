"""
Opportunity data model for DynamoDB
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json
import uuid


@dataclass
class Opportunity:
    """Opportunity data model"""
    opportunity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    required_skills: List[str] = field(default_factory=list)
    location: str = ""
    type: str = ""  # 'internal_transfer', 'external_position', 'consulting', 'project_based'
    source: str = ""  # 'internal', 'external'
    company: str = ""
    salary_range: Dict = field(default_factory=dict)  # {"min": int, "max": int, "currency": str}
    is_active: bool = True
    posted_date: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expiry_date: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item format"""
        item = {
            'opportunity_id': self.opportunity_id,
            'title': self.title,
            'description': self.description,
            'required_skills': json.dumps(self.required_skills),
            'location': self.location,
            'type': self.type,
            'source': self.source,
            'company': self.company,
            'salary_range': json.dumps(self.salary_range),
            'is_active': self.is_active,
            'posted_date': self.posted_date,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        if self.expiry_date:
            item['expiry_date'] = self.expiry_date
            
        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> 'Opportunity':
        """Create instance from DynamoDB item"""
        return cls(
            opportunity_id=item['opportunity_id'],
            title=item.get('title', ''),
            description=item.get('description', ''),
            required_skills=json.loads(item.get('required_skills', '[]')),
            location=item.get('location', ''),
            type=item.get('type', ''),
            source=item.get('source', ''),
            company=item.get('company', ''),
            salary_range=json.loads(item.get('salary_range', '{}')),
            is_active=item.get('is_active', True),
            posted_date=item.get('posted_date', datetime.utcnow().isoformat()),
            expiry_date=item.get('expiry_date'),
            created_at=item.get('created_at', datetime.utcnow().isoformat()),
            updated_at=item.get('updated_at', datetime.utcnow().isoformat())
        )

    def validate(self) -> List[str]:
        """Validate the opportunity data and return list of errors"""
        errors = []
        
        if not self.title:
            errors.append("title is required")
        
        if not self.description:
            errors.append("description is required")
        
        if not self.type:
            errors.append("type is required")
        
        valid_types = ['internal_transfer', 'external_position', 'consulting', 'project_based']
        if self.type and self.type not in valid_types:
            errors.append(f"type must be one of: {', '.join(valid_types)}")
        
        valid_sources = ['internal', 'external']
        if self.source and self.source not in valid_sources:
            errors.append(f"source must be one of: {', '.join(valid_sources)}")
        
        # Validate salary range format
        if self.salary_range:
            if 'min' in self.salary_range and not isinstance(self.salary_range['min'], (int, float)):
                errors.append("salary_range.min must be a number")
            if 'max' in self.salary_range and not isinstance(self.salary_range['max'], (int, float)):
                errors.append("salary_range.max must be a number")
            if 'min' in self.salary_range and 'max' in self.salary_range:
                if self.salary_range['min'] > self.salary_range['max']:
                    errors.append("salary_range.min cannot be greater than salary_range.max")
        
        return errors

    def is_expired(self) -> bool:
        """Check if the opportunity has expired"""
        if not self.expiry_date:
            return False
        
        try:
            expiry = datetime.fromisoformat(self.expiry_date.replace('Z', '+00:00'))
            return datetime.utcnow() > expiry.replace(tzinfo=None)
        except ValueError:
            return False

    def update(self, **kwargs) -> None:
        """Update opportunity fields and set updated_at timestamp"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow().isoformat()