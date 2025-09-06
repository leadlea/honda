"""
Opportunity repository for DynamoDB operations
"""
import os
from typing import List, Optional
from datetime import datetime
import logging

from .base_repository import BaseRepository
from ..models.opportunity import Opportunity

logger = logging.getLogger(__name__)


class OpportunityRepository(BaseRepository):
    """Repository for opportunity operations"""
    
    def __init__(self):
        table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX', 'honda-veteran-talent-matching-dev')}-opportunities"
        super().__init__(table_name)
    
    def create_opportunity(self, opportunity: Opportunity) -> bool:
        """Create a new opportunity"""
        try:
            # Validate opportunity before saving
            errors = opportunity.validate()
            if errors:
                raise ValueError(f"Opportunity validation failed: {', '.join(errors)}")
            
            item = opportunity.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error creating opportunity: {e}")
            raise
    
    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get opportunity by ID"""
        try:
            item = self.get_item({'opportunity_id': opportunity_id})
            if item:
                return Opportunity.from_dynamodb_item(item)
            return None
        except Exception as e:
            logger.error(f"Error getting opportunity {opportunity_id}: {e}")
            raise
    
    def update_opportunity(self, opportunity: Opportunity) -> bool:
        """Update an existing opportunity"""
        try:
            # Validate opportunity before updating
            errors = opportunity.validate()
            if errors:
                raise ValueError(f"Opportunity validation failed: {', '.join(errors)}")
            
            # Update timestamp
            opportunity.update()
            
            item = opportunity.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error updating opportunity: {e}")
            raise
    
    def delete_opportunity(self, opportunity_id: str) -> bool:
        """Delete an opportunity"""
        try:
            return self.delete_item({'opportunity_id': opportunity_id})
        except Exception as e:
            logger.error(f"Error deleting opportunity {opportunity_id}: {e}")
            raise
    
    def get_opportunities_by_type(self, opportunity_type: str, limit: Optional[int] = None) -> List[Opportunity]:
        """Get opportunities by type"""
        try:
            items = self.query(
                key_condition_expression='#type = :type',
                expression_attribute_names={'#type': 'type'},
                expression_attribute_values={':type': opportunity_type},
                index_name='TypeDateIndex',
                limit=limit,
                scan_index_forward=False  # Most recent first
            )
            return [Opportunity.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting opportunities by type {opportunity_type}: {e}")
            raise
    
    def get_active_opportunities(self, limit: Optional[int] = None) -> List[Opportunity]:
        """Get all active opportunities"""
        try:
            items = self.scan(
                filter_expression='is_active = :active',
                expression_attribute_values={':active': True},
                limit=limit
            )
            return [Opportunity.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting active opportunities: {e}")
            raise
    
    def get_opportunities_by_company(self, company: str, limit: Optional[int] = None) -> List[Opportunity]:
        """Get opportunities by company"""
        try:
            items = self.scan(
                filter_expression='company = :company AND is_active = :active',
                expression_attribute_values={
                    ':company': company,
                    ':active': True
                },
                limit=limit
            )
            return [Opportunity.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting opportunities by company {company}: {e}")
            raise
    
    def search_opportunities_by_skills(self, skills: List[str], limit: Optional[int] = None) -> List[Opportunity]:
        """Search opportunities by required skills"""
        try:
            # Note: This is a scan operation which can be expensive for large datasets
            items = self.scan(
                filter_expression='is_active = :active',
                expression_attribute_values={':active': True},
                limit=limit
            )
            
            matching_opportunities = []
            for item in items:
                opportunity = Opportunity.from_dynamodb_item(item)
                
                # Check if any of the search skills match required skills
                required_skills_lower = [skill.lower() for skill in opportunity.required_skills]
                if any(skill.lower() in required_skills_lower for skill in skills):
                    matching_opportunities.append(opportunity)
            
            return matching_opportunities
        except Exception as e:
            logger.error(f"Error searching opportunities by skills: {e}")
            raise
    
    def get_opportunities_by_location(self, location: str, limit: Optional[int] = None) -> List[Opportunity]:
        """Get opportunities by location"""
        try:
            items = self.scan(
                filter_expression='contains(#location, :location) AND is_active = :active',
                expression_attribute_names={'#location': 'location'},
                expression_attribute_values={
                    ':location': location,
                    ':active': True
                },
                limit=limit
            )
            return [Opportunity.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting opportunities by location {location}: {e}")
            raise
    
    def get_recent_opportunities(self, days: int = 30, limit: Optional[int] = None) -> List[Opportunity]:
        """Get opportunities posted in the last N days"""
        try:
            cutoff_date = datetime.utcnow().replace(microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            cutoff_iso = cutoff_date.isoformat()
            
            items = self.scan(
                filter_expression='posted_date >= :cutoff AND is_active = :active',
                expression_attribute_values={
                    ':cutoff': cutoff_iso,
                    ':active': True
                },
                limit=limit
            )
            
            return [Opportunity.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting recent opportunities: {e}")
            raise
    
    def get_expired_opportunities(self) -> List[Opportunity]:
        """Get opportunities that have expired"""
        try:
            current_time = datetime.utcnow().isoformat()
            
            items = self.scan(
                filter_expression='expiry_date < :current_time AND is_active = :active',
                expression_attribute_values={
                    ':current_time': current_time,
                    ':active': True
                }
            )
            
            return [Opportunity.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting expired opportunities: {e}")
            raise
    
    def deactivate_expired_opportunities(self) -> int:
        """Deactivate all expired opportunities and return count"""
        try:
            expired_opportunities = self.get_expired_opportunities()
            count = 0
            
            for opportunity in expired_opportunities:
                opportunity.is_active = False
                opportunity.update()
                self.update_opportunity(opportunity)
                count += 1
            
            return count
        except Exception as e:
            logger.error(f"Error deactivating expired opportunities: {e}")
            raise
    
    def opportunity_exists(self, opportunity_id: str) -> bool:
        """Check if an opportunity exists"""
        try:
            return self.item_exists({'opportunity_id': opportunity_id})
        except Exception as e:
            logger.error(f"Error checking if opportunity exists {opportunity_id}: {e}")
            raise