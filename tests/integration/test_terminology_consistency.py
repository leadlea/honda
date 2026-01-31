"""
Terminology Consistency Tests for Manufacturing Platinum Advisory
製造業プラチナアドバイザリー 用語一貫性テスト

This test suite verifies that terminology is consistent across all UI components and screens.
全UIコンポーネントと画面で用語が一貫していることを確認します。
"""

import pytest
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json


class TestTerminologyConsistency:
    """Test that terminology is consistent across all screens and components."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent
        self.frontend_src = self.project_root / "frontend" / "src"
        
        # Expected terminology mappings
        self.expected_terms = {
            "Honda Veteran Talent Bank": "製造業プラチナアドバイザリー",
            "ベテラン": "登録人材",
            "問診": "スキル棚卸し",
            "ベテランプロフィール": "スキルポートフォリオ",
            "推薦機会": "参画機会レコメンド",
            "応募": "参画申請",
            "興味表明": "参画意向",
            "ベテラン検索": "登録人材検索"
        }
        
        # Legacy terms that should not appear
        self.legacy_terms = list(self.expected_terms.keys())
        
        # New terms that should be used consistently
        self.new_terms = list(self.expected_terms.values())
        
        # File patterns to check
        self.file_patterns = [
            "**/*.tsx",
            "**/*.ts",
            "**/*.css",
            "**/*.json"
        ]
        
        # Directories to check
        self.check_directories = [
            self.frontend_src / "components",
            self.frontend_src / "services",
            self.frontend_src / "utils",
            self.frontend_src / "contexts",
            self.project_root / "src" / "config"
        ]
    
    def get_all_files_to_check(self) -> List[Path]:
        """Get all files that should be checked for terminology consistency."""
        files_to_check = []
        
        for directory in self.check_directories:
            if not directory.exists():
                continue
                
            for pattern in self.file_patterns:
                files_to_check.extend(directory.rglob(pattern.replace("**/", "")))
        
        return files_to_check
    
    def check_file_for_legacy_terms(self, file_path: Path) -> List[Tuple[str, int, str]]:
        """Check a file for legacy terms and return findings."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for legacy_term in self.legacy_terms:
                    if legacy_term in line:
                        findings.append((legacy_term, line_num, line.strip()))
        
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
        
        return findings
    
    def check_file_for_term_consistency(self, file_path: Path) -> Dict[str, List[Tuple[int, str]]]:
        """Check a file for consistent use of new terminology."""
        term_usage = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for new_term in self.new_terms:
                    if new_term in line:
                        if new_term not in term_usage:
                            term_usage[new_term] = []
                        term_usage[new_term].append((line_num, line.strip()))
        
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
        
        return term_usage
    
    def test_no_legacy_terms_in_frontend_components(self):
        """Test that no legacy terms appear in frontend components."""
        legacy_term_findings = {}
        
        component_files = []
        components_dir = self.frontend_src / "components"
        
        if components_dir.exists():
            for pattern in ["**/*.tsx", "**/*.ts", "**/*.css"]:
                component_files.extend(components_dir.rglob(pattern.replace("**/", "")))
        
        for file_path in component_files:
            findings = self.check_file_for_legacy_terms(file_path)
            if findings:
                legacy_term_findings[str(file_path.relative_to(self.project_root))] = findings
        
        if legacy_term_findings:
            error_message = "Legacy terms found in frontend components:\n"
            for file_path, findings in legacy_term_findings.items():
                error_message += f"\n{file_path}:\n"
                for term, line_num, line in findings:
                    error_message += f"  Line {line_num}: '{term}' in '{line}'\n"
            
            pytest.fail(error_message)
    
    def test_no_legacy_terms_in_services(self):
        """Test that no legacy terms appear in service files."""
        legacy_term_findings = {}
        
        service_files = []
        services_dir = self.frontend_src / "services"
        
        if services_dir.exists():
            for pattern in ["**/*.ts", "**/*.js"]:
                service_files.extend(services_dir.rglob(pattern.replace("**/", "")))
        
        for file_path in service_files:
            findings = self.check_file_for_legacy_terms(file_path)
            if findings:
                legacy_term_findings[str(file_path.relative_to(self.project_root))] = findings
        
        if legacy_term_findings:
            error_message = "Legacy terms found in service files:\n"
            for file_path, findings in legacy_term_findings.items():
                error_message += f"\n{file_path}:\n"
                for term, line_num, line in findings:
                    error_message += f"  Line {line_num}: '{term}' in '{line}'\n"
            
            pytest.fail(error_message)
    
    def test_no_legacy_terms_in_configuration_files(self):
        """Test that no legacy terms appear in configuration files."""
        legacy_term_findings = {}
        
        config_files = []
        config_dirs = [
            self.frontend_src / "config",
            self.project_root / "src" / "config"
        ]
        
        for config_dir in config_dirs:
            if config_dir.exists():
                for pattern in ["**/*.json", "**/*.ts", "**/*.py"]:
                    config_files.extend(config_dir.rglob(pattern.replace("**/", "")))
        
        for file_path in config_files:
            findings = self.check_file_for_legacy_terms(file_path)
            if findings:
                legacy_term_findings[str(file_path.relative_to(self.project_root))] = findings
        
        if legacy_term_findings:
            error_message = "Legacy terms found in configuration files:\n"
            for file_path, findings in legacy_term_findings.items():
                error_message += f"\n{file_path}:\n"
                for term, line_num, line in findings:
                    error_message += f"  Line {line_num}: '{term}' in '{line}'\n"
            
            pytest.fail(error_message)
    
    def test_consistent_term_usage_across_components(self):
        """Test that new terms are used consistently across all components."""
        term_usage_by_file = {}
        
        all_files = self.get_all_files_to_check()
        
        for file_path in all_files:
            term_usage = self.check_file_for_term_consistency(file_path)
            if term_usage:
                term_usage_by_file[str(file_path.relative_to(self.project_root))] = term_usage
        
        # Analyze consistency
        term_variations = {}
        
        for file_path, usage in term_usage_by_file.items():
            for term, occurrences in usage.items():
                if term not in term_variations:
                    term_variations[term] = {}
                
                term_variations[term][file_path] = len(occurrences)
        
        # Report term usage statistics
        print("\nTerm usage statistics:")
        for term, files in term_variations.items():
            total_usage = sum(files.values())
            file_count = len(files)
            print(f"  '{term}': {total_usage} occurrences across {file_count} files")
        
        # Check for potential inconsistencies
        inconsistencies = []
        
        # Check if related terms are used together appropriately
        related_terms = [
            ("製造業プラチナアドバイザリー", "登録人材"),
            ("スキル棚卸し", "スキルポートフォリオ"),
            ("参画機会レコメンド", "参画申請")
        ]
        
        for term1, term2 in related_terms:
            files_with_term1 = set(term_variations.get(term1, {}).keys())
            files_with_term2 = set(term_variations.get(term2, {}).keys())
            
            # Files that use one term but not the other might indicate inconsistency
            only_term1 = files_with_term1 - files_with_term2
            only_term2 = files_with_term2 - files_with_term1
            
            if only_term1:
                print(f"Files using '{term1}' but not '{term2}': {list(only_term1)}")
            if only_term2:
                print(f"Files using '{term2}' but not '{term1}': {list(only_term2)}")
        
        if inconsistencies:
            pytest.fail(f"Term usage inconsistencies found:\n" + "\n".join(inconsistencies))
    
    def test_dashboard_terminology_consistency(self):
        """Test that dashboard uses consistent terminology."""
        dashboard_files = [
            self.frontend_src / "components" / "dashboard" / "Dashboard.tsx",
            self.frontend_src / "components" / "dashboard" / "Dashboard.css"
        ]
        
        dashboard_terms = {}
        
        for file_path in dashboard_files:
            if not file_path.exists():
                continue
            
            term_usage = self.check_file_for_term_consistency(file_path)
            legacy_findings = self.check_file_for_legacy_terms(file_path)
            
            if legacy_findings:
                pytest.fail(f"Legacy terms found in dashboard: {legacy_findings}")
            
            dashboard_terms[str(file_path.relative_to(self.project_root))] = term_usage
        
        # Verify expected terms are present in dashboard
        expected_dashboard_terms = [
            "製造業プラチナアドバイザリー",
            "スキルポートフォリオ",
            "参画機会レコメンド",
            "参画申請状況"
        ]
        
        found_terms = set()
        for file_terms in dashboard_terms.values():
            found_terms.update(file_terms.keys())
        
        missing_terms = []
        for expected_term in expected_dashboard_terms:
            if expected_term not in found_terms:
                missing_terms.append(expected_term)
        
        if missing_terms:
            print(f"Warning: Expected dashboard terms not found: {missing_terms}")
    
    def test_profile_management_terminology_consistency(self):
        """Test that profile management components use consistent terminology."""
        profile_files = [
            self.frontend_src / "components" / "profile" / "ProfileManagement.tsx",
            self.frontend_src / "components" / "profile" / "UserProfile.tsx",
            self.frontend_src / "components" / "profile" / "BusinessTitleGenerator.tsx"
        ]
        
        profile_terms = {}
        
        for file_path in profile_files:
            if not file_path.exists():
                continue
            
            term_usage = self.check_file_for_term_consistency(file_path)
            legacy_findings = self.check_file_for_legacy_terms(file_path)
            
            if legacy_findings:
                pytest.fail(f"Legacy terms found in profile components: {legacy_findings}")
            
            profile_terms[str(file_path.relative_to(self.project_root))] = term_usage
        
        # Verify profile-specific terms
        expected_profile_terms = [
            "スキルポートフォリオ",
            "登録人材"
        ]
        
        found_terms = set()
        for file_terms in profile_terms.values():
            found_terms.update(file_terms.keys())
        
        for expected_term in expected_profile_terms:
            if expected_term not in found_terms:
                print(f"Warning: Expected profile term not found: {expected_term}")
    
    def test_questionnaire_terminology_consistency(self):
        """Test that questionnaire components use consistent terminology."""
        questionnaire_files = [
            self.frontend_src / "components" / "questionnaire" / "Questionnaire.tsx",
            self.frontend_src / "components" / "questionnaire" / "Questionnaire.css"
        ]
        
        questionnaire_terms = {}
        
        for file_path in questionnaire_files:
            if not file_path.exists():
                continue
            
            term_usage = self.check_file_for_term_consistency(file_path)
            legacy_findings = self.check_file_for_legacy_terms(file_path)
            
            if legacy_findings:
                pytest.fail(f"Legacy terms found in questionnaire components: {legacy_findings}")
            
            questionnaire_terms[str(file_path.relative_to(self.project_root))] = term_usage
        
        # Verify questionnaire-specific terms
        expected_questionnaire_terms = [
            "スキル棚卸し"
        ]
        
        found_terms = set()
        for file_terms in questionnaire_terms.values():
            found_terms.update(file_terms.keys())
        
        for expected_term in expected_questionnaire_terms:
            if expected_term not in found_terms:
                print(f"Warning: Expected questionnaire term not found: {expected_term}")
    
    def test_recommendations_terminology_consistency(self):
        """Test that recommendation components use consistent terminology."""
        recommendation_files = [
            self.frontend_src / "components" / "recommendations" / "RecommendationsList.tsx",
            self.frontend_src / "components" / "recommendations" / "RecommendationCard.tsx",
            self.frontend_src / "components" / "recommendations" / "ApplicationTracker.tsx"
        ]
        
        recommendation_terms = {}
        
        for file_path in recommendation_files:
            if not file_path.exists():
                continue
            
            term_usage = self.check_file_for_term_consistency(file_path)
            legacy_findings = self.check_file_for_legacy_terms(file_path)
            
            if legacy_findings:
                pytest.fail(f"Legacy terms found in recommendation components: {legacy_findings}")
            
            recommendation_terms[str(file_path.relative_to(self.project_root))] = term_usage
        
        # Verify recommendation-specific terms
        expected_recommendation_terms = [
            "参画機会レコメンド",
            "参画申請",
            "参画意向"
        ]
        
        found_terms = set()
        for file_terms in recommendation_terms.values():
            found_terms.update(file_terms.keys())
        
        for expected_term in expected_recommendation_terms:
            if expected_term not in found_terms:
                print(f"Warning: Expected recommendation term not found: {expected_term}")
    
    def test_public_search_terminology_consistency(self):
        """Test that public search components use consistent terminology."""
        search_files = [
            self.frontend_src / "components" / "public" / "PublicVeteranSearch.tsx",
            self.frontend_src / "components" / "public" / "VeteranSearchCard.tsx",
            self.frontend_src / "components" / "public" / "VeteranProfileModal.tsx"
        ]
        
        search_terms = {}
        
        for file_path in search_files:
            if not file_path.exists():
                continue
            
            term_usage = self.check_file_for_term_consistency(file_path)
            legacy_findings = self.check_file_for_legacy_terms(file_path)
            
            if legacy_findings:
                pytest.fail(f"Legacy terms found in search components: {legacy_findings}")
            
            search_terms[str(file_path.relative_to(self.project_root))] = term_usage
        
        # Verify search-specific terms
        expected_search_terms = [
            "登録人材検索",
            "登録人材"
        ]
        
        found_terms = set()
        for file_terms in search_terms.values():
            found_terms.update(file_terms.keys())
        
        for expected_term in expected_search_terms:
            if expected_term not in found_terms:
                print(f"Warning: Expected search term not found: {expected_term}")
    
    def test_branding_utils_consistency(self):
        """Test that branding utilities provide consistent terminology."""
        branding_utils_file = self.frontend_src / "utils" / "brandingUtils.ts"
        
        if not branding_utils_file.exists():
            pytest.skip("Branding utils file not found")
        
        try:
            with open(branding_utils_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check that all expected term mappings are present
            for legacy_term, new_term in self.expected_terms.items():
                if legacy_term not in content:
                    pytest.fail(f"Legacy term '{legacy_term}' not found in branding utils")
                if new_term not in content:
                    pytest.fail(f"New term '{new_term}' not found in branding utils")
            
            # Check that the mapping is correct
            if "TERM_MAPPINGS" in content:
                print("✓ TERM_MAPPINGS found in branding utils")
            else:
                pytest.fail("TERM_MAPPINGS not found in branding utils")
        
        except Exception as e:
            pytest.fail(f"Error reading branding utils: {e}")
    
    def test_message_config_consistency(self):
        """Test that message configuration uses consistent terminology."""
        message_config_file = self.project_root / "src" / "config" / "message_config.py"
        
        if not message_config_file.exists():
            pytest.skip("Message config file not found")
        
        try:
            with open(message_config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for legacy terms in messages
            legacy_findings = []
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for legacy_term in self.legacy_terms:
                    if legacy_term in line and not line.strip().startswith('#'):
                        legacy_findings.append((legacy_term, line_num, line.strip()))
            
            if legacy_findings:
                error_message = "Legacy terms found in message config:\n"
                for term, line_num, line in legacy_findings:
                    error_message += f"  Line {line_num}: '{term}' in '{line}'\n"
                pytest.fail(error_message)
            
            # Check that new terms are present
            new_term_count = 0
            for new_term in self.new_terms:
                if new_term in content:
                    new_term_count += 1
            
            if new_term_count == 0:
                pytest.fail("No new terms found in message config")
            
            print(f"✓ Found {new_term_count} new terms in message config")
        
        except Exception as e:
            pytest.fail(f"Error reading message config: {e}")
    
    def test_cross_component_term_consistency(self):
        """Test that the same concepts use the same terms across different components."""
        # Define concept groups that should use consistent terminology
        concept_groups = {
            "platform_name": ["製造業プラチナアドバイザリー"],
            "user_type": ["登録人材"],
            "profile": ["スキルポートフォリオ"],
            "assessment": ["スキル棚卸し"],
            "opportunities": ["参画機会レコメンド"],
            "applications": ["参画申請", "参画意向"],
            "search": ["登録人材検索"]
        }
        
        all_files = self.get_all_files_to_check()
        concept_usage = {concept: {} for concept in concept_groups.keys()}
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for concept, terms in concept_groups.items():
                    for term in terms:
                        if term in content:
                            if concept not in concept_usage:
                                concept_usage[concept] = {}
                            if term not in concept_usage[concept]:
                                concept_usage[concept][term] = []
                            concept_usage[concept][term].append(str(file_path.relative_to(self.project_root)))
            
            except Exception:
                continue
        
        # Analyze concept consistency
        inconsistencies = []
        
        for concept, term_usage in concept_usage.items():
            if len(term_usage) > 1:
                # Multiple terms used for the same concept
                print(f"Multiple terms used for concept '{concept}':")
                for term, files in term_usage.items():
                    print(f"  '{term}': {len(files)} files")
        
        # Report concept usage
        print("\nConcept usage summary:")
        for concept, term_usage in concept_usage.items():
            total_files = sum(len(files) for files in term_usage.values())
            if total_files > 0:
                print(f"  {concept}: {total_files} files")
            else:
                print(f"  {concept}: No usage found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])