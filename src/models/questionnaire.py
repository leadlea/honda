"""
Questionnaire and QuestionnaireResponse data models for DynamoDB
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json
import uuid


@dataclass
class Questionnaire:
    """Questionnaire data model"""
    questionnaire_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = ""
    description: str = ""
    questions: List[Dict] = field(default_factory=list)  # [{"id": str, "question": str, "type": str, "options": List[str]}]
    responses: List[Dict] = field(default_factory=list)  # [{"question_id": str, "answer": str}]
    status: str = "draft"  # draft, active, completed, expired
    ai_generated: bool = False
    version: str = "1.0"
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    submitted_at: Optional[str] = None
    expires_at: Optional[str] = None

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item format"""
        item = {
            'questionnaire_id': self.questionnaire_id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'questions': json.dumps(self.questions),
            'responses': json.dumps(self.responses),
            'status': self.status,
            'ai_generated': self.ai_generated,
            'version': self.version,
            'is_active': self.is_active,
            'created_at': self.created_at
        }
        
        if self.submitted_at:
            item['submitted_at'] = self.submitted_at
        
        if self.expires_at:
            item['expires_at'] = self.expires_at
            
        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> 'Questionnaire':
        """Create instance from DynamoDB item"""
        return cls(
            questionnaire_id=item['questionnaire_id'],
            user_id=item.get('user_id', ''),
            title=item.get('title', ''),
            description=item.get('description', ''),
            questions=json.loads(item.get('questions', '[]')),
            responses=json.loads(item.get('responses', '[]')),
            status=item.get('status', 'draft'),
            ai_generated=item.get('ai_generated', False),
            version=item.get('version', '1.0'),
            is_active=item.get('is_active', True),
            created_at=item.get('created_at', datetime.utcnow().isoformat()),
            submitted_at=item.get('submitted_at'),
            expires_at=item.get('expires_at')
        )

    def validate(self) -> List[str]:
        """Validate the questionnaire data and return list of errors"""
        errors = []
        
        if not self.user_id:
            errors.append("user_id is required")
        
        if not self.questions:
            errors.append("questions list cannot be empty")
        
        # Validate questions format
        for i, question in enumerate(self.questions):
            if not isinstance(question, dict):
                errors.append(f"Question {i} must be a dictionary")
                continue
            
            required_fields = ['id', 'question', 'type']
            for field_name in required_fields:
                if field_name not in question:
                    errors.append(f"Question {i} missing required field: {field_name}")
            
            valid_types = ['text', 'multiple_choice', 'rating', 'boolean']
            if 'type' in question and question['type'] not in valid_types:
                errors.append(f"Question {i} type must be one of: {', '.join(valid_types)}")
        
        return errors

    def is_expired(self) -> bool:
        """Check if the questionnaire has expired"""
        if not self.expires_at:
            return False
        
        try:
            expiry = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.utcnow() > expiry.replace(tzinfo=None)
        except ValueError:
            return False


@dataclass
class QuestionnaireResponse:
    """Questionnaire response data model"""
    user_id: str
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    questionnaire_id: str = ""
    responses: Dict = field(default_factory=dict)  # {"question_id": "answer"}
    is_complete: bool = False
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item format"""
        item = {
            'user_id': self.user_id,
            'response_id': self.response_id,
            'questionnaire_id': self.questionnaire_id,
            'responses': json.dumps(self.responses),
            'is_complete': self.is_complete,
            'started_at': self.started_at,
            'updated_at': self.updated_at
        }
        
        if self.completed_at:
            item['completed_at'] = self.completed_at
            
        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> 'QuestionnaireResponse':
        """Create instance from DynamoDB item"""
        return cls(
            user_id=item['user_id'],
            response_id=item['response_id'],
            questionnaire_id=item.get('questionnaire_id', ''),
            responses=json.loads(item.get('responses', '{}')),
            is_complete=item.get('is_complete', False),
            started_at=item.get('started_at', datetime.utcnow().isoformat()),
            completed_at=item.get('completed_at'),
            updated_at=item.get('updated_at', datetime.utcnow().isoformat())
        )

    def validate(self) -> List[str]:
        """Validate the questionnaire response data and return list of errors"""
        errors = []
        
        if not self.user_id:
            errors.append("user_id is required")
        
        if not self.questionnaire_id:
            errors.append("questionnaire_id is required")
        
        if not isinstance(self.responses, dict):
            errors.append("responses must be a dictionary")
        
        return errors

    def add_response(self, question_id: str, answer: str) -> None:
        """Add or update a response to a question"""
        self.responses[question_id] = answer
        self.updated_at = datetime.utcnow().isoformat()

    def mark_complete(self) -> None:
        """Mark the questionnaire response as complete"""
        self.is_complete = True
        self.completed_at = datetime.utcnow().isoformat()
        self.updated_at = self.completed_at