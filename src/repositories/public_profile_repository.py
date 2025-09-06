"""
Public Profile and Contact Request repositories for DynamoDB operations
"""
import logging
import os
from datetime import datetime
from typing import List, Optional

from ..models.public_profile import ContactRequest, PublicProfile
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PublicProfileRepository(BaseRepository):
    """Repository for public profile operations"""

    def __init__(self):
        table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX', 'honda-veteran-talent-matching-dev')}-public-profiles"
        super().__init__(table_name)

    def create_profile(self, profile: PublicProfile) -> bool:
        """Create a new public profile"""
        try:
            errors = profile.validate()
            if errors:
                raise ValueError(
                    f"Public profile validation failed: {', '.join(errors)}"
                )

            item = profile.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error creating public profile: {e}")
            raise

    def get_profile(self, profile_id: str) -> Optional[PublicProfile]:
        """Get public profile by ID"""
        try:
            item = self.get_item({"profile_id": profile_id})
            if item:
                return PublicProfile.from_dynamodb_item(item)
            return None
        except Exception as e:
            logger.error(f"Error getting public profile {profile_id}: {e}")
            raise

    def get_profile_by_user_id(self, user_id: str) -> Optional[PublicProfile]:
        """Get public profile by user ID"""
        try:
            items = self.query(
                key_condition_expression="user_id = :user_id",
                expression_attribute_values={":user_id": user_id},
                index_name="UserIdIndex",
            )

            if items:
                return PublicProfile.from_dynamodb_item(items[0])
            return None
        except Exception as e:
            logger.error(f"Error getting public profile for user {user_id}: {e}")
            raise

    def update_profile(self, profile: PublicProfile) -> bool:
        """Update an existing public profile"""
        try:
            errors = profile.validate()
            if errors:
                raise ValueError(
                    f"Public profile validation failed: {', '.join(errors)}"
                )

            profile.update()
            item = profile.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error updating public profile: {e}")
            raise

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a public profile"""
        try:
            return self.delete_item({"profile_id": profile_id})
        except Exception as e:
            logger.error(f"Error deleting public profile {profile_id}: {e}")
            raise

    def get_active_profiles(self, limit: Optional[int] = None) -> List[PublicProfile]:
        """Get all active public profiles"""
        try:
            items = self.scan(
                filter_expression="is_active = :active",
                expression_attribute_values={":active": True},
                limit=limit,
            )
            return [PublicProfile.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting active public profiles: {e}")
            raise

    def search_profiles_by_skills(
        self, skills: List[str], limit: Optional[int] = None
    ) -> List[PublicProfile]:
        """Search public profiles by skills"""
        try:
            active_profiles = self.get_active_profiles(limit)

            matching_profiles = []
            for profile in active_profiles:
                profile_skills_lower = [skill.lower() for skill in profile.skills]
                if any(skill.lower() in profile_skills_lower for skill in skills):
                    matching_profiles.append(profile)

            return matching_profiles
        except Exception as e:
            logger.error(f"Error searching profiles by skills: {e}")
            raise

    def search_profiles_by_location(
        self, location: str, limit: Optional[int] = None
    ) -> List[PublicProfile]:
        """Search public profiles by location"""
        try:
            items = self.scan(
                filter_expression="contains(#location, :location) AND is_active = :active",
                expression_attribute_names={"#location": "location"},
                expression_attribute_values={":location": location, ":active": True},
                limit=limit,
            )
            return [PublicProfile.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error searching profiles by location {location}: {e}")
            raise

    def get_profiles_by_availability(
        self, availability: str, limit: Optional[int] = None
    ) -> List[PublicProfile]:
        """Get profiles by availability status"""
        try:
            items = self.scan(
                filter_expression="availability = :availability AND is_active = :active",
                expression_attribute_values={
                    ":availability": availability,
                    ":active": True,
                },
                limit=limit,
            )
            return [PublicProfile.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting profiles by availability {availability}: {e}")
            raise

    def get_profiles_by_experience_range(
        self, min_years: int, max_years: int, limit: Optional[int] = None
    ) -> List[PublicProfile]:
        """Get profiles by experience years range"""
        try:
            items = self.scan(
                filter_expression="experience_years BETWEEN :min_years AND :max_years AND is_active = :active",
                expression_attribute_values={
                    ":min_years": min_years,
                    ":max_years": max_years,
                    ":active": True,
                },
                limit=limit,
            )
            return [PublicProfile.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(
                f"Error getting profiles by experience range {min_years}-{max_years}: {e}"
            )
            raise

    def sync_from_veteran_profile(self, user_id: str, veteran_profile) -> bool:
        """Sync public profile from veteran profile"""
        try:
            public_profile = self.get_profile_by_user_id(user_id)

            if not public_profile:
                # Create new public profile
                public_profile = PublicProfile(user_id=user_id)

            public_profile.sync_from_veteran_profile(veteran_profile)

            if public_profile.profile_id:
                return self.update_profile(public_profile)
            else:
                return self.create_profile(public_profile)
        except Exception as e:
            logger.error(f"Error syncing public profile for user {user_id}: {e}")
            raise

    def deactivate_profile(self, profile_id: str) -> bool:
        """Deactivate a public profile"""
        try:
            profile = self.get_profile(profile_id)
            if not profile:
                raise ValueError(f"Public profile {profile_id} not found")

            profile.is_active = False
            profile.update()
            return self.update_profile(profile)
        except Exception as e:
            logger.error(f"Error deactivating public profile {profile_id}: {e}")
            raise

    def search_public_profiles(self, filters: dict) -> List[dict]:
        """Search public profiles with multiple filters"""
        try:
            # Start with all active profiles
            profiles = self.get_active_profiles()

            # Convert to dict format for easier filtering
            profile_dicts = []
            for profile in profiles:
                profile_dict = profile.to_dict()
                profile_dicts.append(profile_dict)

            # Apply filters
            filtered_profiles = profile_dicts

            # Filter by skills
            if "skills" in filters and filters["skills"]:
                filtered_profiles = [
                    p
                    for p in filtered_profiles
                    if any(
                        skill.lower()
                        in [s.get("name", "").lower() for s in p.get("skills", [])]
                        for skill in filters["skills"]
                    )
                ]

            # Filter by experience level
            if "experience_level" in filters:
                level_map = {
                    "junior": (0, 3),
                    "mid": (3, 8),
                    "senior": (8, 15),
                    "expert": (15, 100),
                }
                if filters["experience_level"] in level_map:
                    min_years, max_years = level_map[filters["experience_level"]]
                    filtered_profiles = [
                        p
                        for p in filtered_profiles
                        if min_years <= p.get("experience_years", 0) <= max_years
                    ]

            # Filter by department
            if "department" in filters:
                filtered_profiles = [
                    p
                    for p in filtered_profiles
                    if any(
                        filters["department"].lower()
                        in exp.get("department", "").lower()
                        for exp in p.get("experiences", [])
                    )
                ]

            # Filter by location
            if "location" in filters:
                filtered_profiles = [
                    p
                    for p in filtered_profiles
                    if filters["location"].lower() in p.get("location", "").lower()
                ]

            # Filter by availability
            if "availability" in filters:
                filtered_profiles = [
                    p
                    for p in filtered_profiles
                    if p.get("availability", "") == filters["availability"]
                ]

            # Filter by years of experience range
            if "min_years" in filters:
                filtered_profiles = [
                    p
                    for p in filtered_profiles
                    if p.get("experience_years", 0) >= filters["min_years"]
                ]

            if "max_years" in filters:
                filtered_profiles = [
                    p
                    for p in filtered_profiles
                    if p.get("experience_years", 0) <= filters["max_years"]
                ]

            return filtered_profiles

        except Exception as e:
            logger.error(f"Error searching public profiles: {e}")
            raise

    def get_public_profile(self, profile_id: str) -> Optional[dict]:
        """Get public profile as dict for external API"""
        try:
            profile = self.get_profile(profile_id)
            if profile and profile.is_active:
                return profile.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting public profile {profile_id}: {e}")
            raise

    def get_available_categories(self) -> dict:
        """Get available categories for filtering"""
        try:
            profiles = self.get_active_profiles()

            categories = {
                "skills": set(),
                "departments": set(),
                "locations": set(),
                "availability_options": set(),
                "experience_levels": ["junior", "mid", "senior", "expert"],
            }

            for profile in profiles:
                profile_dict = profile.to_dict()

                # Collect skills
                for skill in profile_dict.get("skills", []):
                    if skill.get("name"):
                        categories["skills"].add(skill["name"])

                # Collect departments
                for exp in profile_dict.get("experiences", []):
                    if exp.get("department"):
                        categories["departments"].add(exp["department"])

                # Collect locations
                if profile_dict.get("location"):
                    categories["locations"].add(profile_dict["location"])

                # Collect availability options
                if profile_dict.get("availability"):
                    categories["availability_options"].add(profile_dict["availability"])

            # Convert sets to sorted lists
            return {
                "skills": sorted(list(categories["skills"])),
                "departments": sorted(list(categories["departments"])),
                "locations": sorted(list(categories["locations"])),
                "availability_options": sorted(
                    list(categories["availability_options"])
                ),
                "experience_levels": categories["experience_levels"],
            }

        except Exception as e:
            logger.error(f"Error getting available categories: {e}")
            raise


class ContactRequestRepository(BaseRepository):
    """Repository for contact request operations"""

    def __init__(self):
        table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX', 'honda-veteran-talent-matching-dev')}-contact-requests"
        super().__init__(table_name)

    def create_request(self, request: ContactRequest) -> bool:
        """Create a new contact request"""
        try:
            errors = request.validate()
            if errors:
                raise ValueError(
                    f"Contact request validation failed: {', '.join(errors)}"
                )

            item = request.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error creating contact request: {e}")
            raise

    def get_request(self, request_id: str) -> Optional[ContactRequest]:
        """Get contact request by ID"""
        try:
            item = self.get_item({"request_id": request_id})
            if item:
                return ContactRequest.from_dynamodb_item(item)
            return None
        except Exception as e:
            logger.error(f"Error getting contact request {request_id}: {e}")
            raise

    def update_request(self, request: ContactRequest) -> bool:
        """Update an existing contact request"""
        try:
            errors = request.validate()
            if errors:
                raise ValueError(
                    f"Contact request validation failed: {', '.join(errors)}"
                )

            item = request.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error updating contact request: {e}")
            raise

    def get_requests_for_profile(
        self, profile_id: str, limit: Optional[int] = None
    ) -> List[ContactRequest]:
        """Get all contact requests for a profile"""
        try:
            items = self.query(
                key_condition_expression="profile_id = :profile_id",
                expression_attribute_values={":profile_id": profile_id},
                index_name="ProfileIdDateIndex",
                limit=limit,
                scan_index_forward=False,  # Most recent first
            )
            return [ContactRequest.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(
                f"Error getting contact requests for profile {profile_id}: {e}"
            )
            raise

    def get_pending_requests(self, limit: Optional[int] = None) -> List[ContactRequest]:
        """Get all pending contact requests"""
        try:
            items = self.scan(
                filter_expression="#status = :status",
                expression_attribute_names={"#status": "status"},
                expression_attribute_values={":status": "pending"},
                limit=limit,
            )
            return [ContactRequest.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting pending contact requests: {e}")
            raise

    def get_requests_by_status(
        self, status: str, limit: Optional[int] = None
    ) -> List[ContactRequest]:
        """Get contact requests by status"""
        try:
            items = self.scan(
                filter_expression="#status = :status",
                expression_attribute_names={"#status": "status"},
                expression_attribute_values={":status": status},
                limit=limit,
            )
            return [ContactRequest.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting contact requests by status {status}: {e}")
            raise

    def process_request(
        self, request_id: str, status: str, processor_id: str, notes: str = ""
    ) -> bool:
        """Process a contact request"""
        try:
            request = self.get_request(request_id)
            if not request:
                raise ValueError(f"Contact request {request_id} not found")

            request.process(status, processor_id, notes)
            return self.update_request(request)
        except Exception as e:
            logger.error(f"Error processing contact request {request_id}: {e}")
            raise

    def get_requests_by_company(
        self, company: str, limit: Optional[int] = None
    ) -> List[ContactRequest]:
        """Get contact requests by requester company"""
        try:
            items = self.scan(
                filter_expression="requester_company = :company",
                expression_attribute_values={":company": company},
                limit=limit,
            )
            return [ContactRequest.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting contact requests by company {company}: {e}")
            raise

    def get_recent_requests(
        self, days: int = 30, limit: Optional[int] = None
    ) -> List[ContactRequest]:
        """Get contact requests from the last N days"""
        try:
            cutoff_date = datetime.utcnow().replace(microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            cutoff_iso = cutoff_date.isoformat()

            items = self.scan(
                filter_expression="created_at >= :cutoff",
                expression_attribute_values={":cutoff": cutoff_iso},
                limit=limit,
            )

            return [ContactRequest.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting recent contact requests: {e}")
            raise

    def get_request_statistics(self) -> dict:
        """Get contact request statistics"""
        try:
            all_requests = self.scan()

            stats = {"total": len(all_requests), "by_status": {}, "by_company": {}}

            for item in all_requests:
                request = ContactRequest.from_dynamodb_item(item)

                # Count by status
                stats["by_status"][request.status] = (
                    stats["by_status"].get(request.status, 0) + 1
                )

                # Count by company
                company = request.requester_company or "Unknown"
                stats["by_company"][company] = stats["by_company"].get(company, 0) + 1

            return stats
        except Exception as e:
            logger.error(f"Error getting contact request statistics: {e}")
            raise

    def request_exists(self, request_id: str) -> bool:
        """Check if a contact request exists"""
        try:
            return self.item_exists({"request_id": request_id})
        except Exception as e:
            logger.error(f"Error checking if contact request exists {request_id}: {e}")
            raise
