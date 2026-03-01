"""
End-to-End Terminology Consistency Tests
エンドツーエンド用語一貫性テスト

Verifies terminology consistency across the entire user journey:
Frontend components → Backend API responses → AI-generated content → Config/Logging

ユーザージャーニー全体で用語の一貫性を検証します。
Validates: All Requirements (1-8)
"""

import pytest
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


class TestEndToEndTerminologyConsistency:
    """
    End-to-end test verifying terminology consistency across the complete user journey.

    User journey layers tested:
    1. Frontend UI components (React/TypeScript)
    2. Frontend services and utilities
    3. Backend API handlers (Python/Lambda)
    4. Backend services and business logic
    5. Configuration files (JSON/Python)
    6. AI content generation prompts and templates
    7. System logging messages
    """

    def setup_method(self):
        """Setup test fixtures with terminology definitions."""
        self.project_root = Path(__file__).parent.parent.parent
        self.frontend_src = self.project_root / "frontend" / "src"
        self.backend_src = self.project_root / "src"

        # Oldest legacy terms that must NOT appear in user-facing content.
        # These are the original Honda/ベテラン era terms.
        self.forbidden_legacy_terms = [
            "Honda Veteran Talent Bank",
            "Veteran Talent",
            "ベテラン人材",
            "ベテラン登録",
            "ベテラン情報",
            "ベテラン一覧",
            "ベテラン詳細",
            "ベテラン検索",
            "ベテランプロフィール",
        ]

        # Patterns that indicate a legitimate use of legacy terms
        # (e.g., inside mapping definitions, map_legacy_term() calls, etc.)
        self.legitimate_context_patterns = [
            r"map_legacy_term\s*\(",       # Calling the mapping function
            r"mapLegacyTerm\s*\(",         # TS version of mapping function
            r"TERM_MAPPINGS",              # Mapping constant definition
            r"term_mappings",              # Python mapping dict
            r"legacy_terms",               # Legacy terms dict key
            r"expected_terms",             # Test expected terms
            r"requiredTerms",              # Validation list
            r"legacyTerm",                 # Variable holding legacy term
            r"legacy_term",               # Python variable
            r"self\.legacy_terms",         # Test fixture
            r"self\.forbidden_legacy_terms",  # Test fixture
            r"self\.expected_terms",       # Test fixture
            r"contains_legacy_terms",      # Validation function
            r"validateTermConsistency",    # Validation method
            r"validateBrandingConsistency", # Validation method
        ]

        # Files/patterns to exclude from checks
        self.exclude_patterns = [
            "node_modules",
            ".git",
            "__pycache__",
            ".kiro",
            "package-lock.json",
            "package.json",
            ".test.",
            "_test.",
            "test_",
            "SUMMARY",
            "GUIDE",
            "README",
        ]

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if a file should be excluded from terminology checks."""
        path_str = str(file_path)
        for pattern in self.exclude_patterns:
            if pattern in path_str:
                return True
        return False

    def _read_file_content(self, file_path: Path) -> str:
        """Safely read file content."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _is_legitimate_context(self, line: str) -> bool:
        """Check if a line uses legacy terms in a legitimate context."""
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("*"):
            return True
        # Skip docstrings
        if stripped.startswith('"""') or stripped.startswith("'''"):
            return True
        # Check for legitimate mapping/validation contexts
        for pattern in self.legitimate_context_patterns:
            if re.search(pattern, line):
                return True
        # JSON key context: legacy term appears as a key in a mapping dict
        if re.search(r'["\'].*["\']:\s*["\']', line):
            return True
        # String literal in an array (e.g., validation lists of legacy terms)
        # Matches lines like: 'Honda Veteran Talent Bank', or "ベテラン検索"
        if re.match(r"^\s*['\"].*['\"],?\s*$", stripped):
            return True
        return False

    def _find_forbidden_terms(
        self, content: str, term: str
    ) -> List[Tuple[int, str]]:
        """Find forbidden term occurrences, excluding legitimate contexts."""
        findings = []
        for line_num, line in enumerate(content.split("\n"), 1):
            if term in line and not self._is_legitimate_context(line):
                findings.append((line_num, line.strip()))
        return findings

    # ----------------------------------------------------------------
    # Layer 1: Frontend Components (Requirements 1, 2, 3)
    # ----------------------------------------------------------------

    def test_frontend_components_no_forbidden_legacy_terms(self):
        """
        Verify no forbidden legacy terms exist in frontend components.
        Validates: Requirements 1.1-1.5, 2.1-2.3, 3.1-3.2
        """
        components_dir = self.frontend_src / "components"
        if not components_dir.exists():
            pytest.skip("Frontend components directory not found")

        violations = {}
        for ext in ["*.tsx", "*.ts", "*.css"]:
            for file_path in components_dir.rglob(ext):
                if self._should_exclude(file_path):
                    continue
                content = self._read_file_content(file_path)
                for term in self.forbidden_legacy_terms:
                    findings = self._find_forbidden_terms(content, term)
                    if findings:
                        rel_path = str(file_path.relative_to(self.project_root))
                        if rel_path not in violations:
                            violations[rel_path] = []
                        for line_num, line in findings:
                            violations[rel_path].append(
                                f"Line {line_num}: forbidden term '{term}' in: {line}"
                            )

        if violations:
            msg = "Forbidden legacy terms found in frontend components:\n"
            for path, issues in violations.items():
                msg += f"\n  {path}:\n"
                for issue in issues:
                    msg += f"    {issue}\n"
            pytest.fail(msg)

    def test_frontend_services_no_forbidden_legacy_terms(self):
        """
        Verify no forbidden legacy terms in frontend services
        (excluding legitimate mapping definitions).
        Validates: Requirements 1.1-1.5
        """
        services_dir = self.frontend_src / "services"
        if not services_dir.exists():
            pytest.skip("Frontend services directory not found")

        violations = {}
        for ext in ["*.ts", "*.tsx"]:
            for file_path in services_dir.rglob(ext):
                if self._should_exclude(file_path):
                    continue
                content = self._read_file_content(file_path)
                for term in self.forbidden_legacy_terms:
                    findings = self._find_forbidden_terms(content, term)
                    if findings:
                        rel_path = str(file_path.relative_to(self.project_root))
                        if rel_path not in violations:
                            violations[rel_path] = []
                        for line_num, line in findings:
                            violations[rel_path].append(
                                f"Line {line_num}: forbidden term '{term}' in: {line}"
                            )

        if violations:
            msg = "Forbidden legacy terms found in frontend services:\n"
            for path, issues in violations.items():
                msg += f"\n  {path}:\n"
                for issue in issues:
                    msg += f"    {issue}\n"
            pytest.fail(msg)

    # ----------------------------------------------------------------
    # Layer 2: Backend Handlers (Requirements 4)
    # ----------------------------------------------------------------

    def test_backend_handlers_no_forbidden_legacy_terms(self):
        """
        Verify no forbidden legacy terms in backend API handlers
        (excluding legitimate mapping/conversion calls).
        Validates: Requirements 4.1, 4.2
        """
        handlers_dir = self.backend_src / "handlers"
        if not handlers_dir.exists():
            pytest.skip("Backend handlers directory not found")

        violations = {}
        for file_path in handlers_dir.rglob("*.py"):
            if self._should_exclude(file_path):
                continue
            content = self._read_file_content(file_path)
            for term in self.forbidden_legacy_terms:
                findings = self._find_forbidden_terms(content, term)
                if findings:
                    rel_path = str(file_path.relative_to(self.project_root))
                    if rel_path not in violations:
                        violations[rel_path] = []
                    for line_num, line in findings:
                        violations[rel_path].append(
                            f"Line {line_num}: forbidden term '{term}' in: {line}"
                        )

        if violations:
            msg = "Forbidden legacy terms found in backend handlers:\n"
            for path, issues in violations.items():
                msg += f"\n  {path}:\n"
                for issue in issues:
                    msg += f"    {issue}\n"
            pytest.fail(msg)

    def test_backend_services_no_forbidden_legacy_terms(self):
        """
        Verify no forbidden legacy terms in backend services.
        Validates: Requirements 4.1, 4.2, 5.1-5.3
        """
        services_dir = self.backend_src / "services"
        if not services_dir.exists():
            pytest.skip("Backend services directory not found")

        violations = {}
        for file_path in services_dir.rglob("*.py"):
            if self._should_exclude(file_path):
                continue
            content = self._read_file_content(file_path)
            for term in self.forbidden_legacy_terms:
                findings = self._find_forbidden_terms(content, term)
                if findings:
                    rel_path = str(file_path.relative_to(self.project_root))
                    if rel_path not in violations:
                        violations[rel_path] = []
                    for line_num, line in findings:
                        violations[rel_path].append(
                            f"Line {line_num}: forbidden term '{term}' in: {line}"
                        )

        if violations:
            msg = "Forbidden legacy terms found in backend services:\n"
            for path, issues in violations.items():
                msg += f"\n  {path}:\n"
                for issue in issues:
                    msg += f"    {issue}\n"
            pytest.fail(msg)

    # ----------------------------------------------------------------
    # Layer 3: Configuration Files (Requirements 6, 8)
    # ----------------------------------------------------------------

    def test_term_mapping_config_completeness(self):
        """
        Verify term-mapping.json contains all required sections.
        Validates: Requirements 6.3, 8.1
        """
        config_path = self.backend_src / "config" / "term-mapping.json"
        if not config_path.exists():
            pytest.fail("term-mapping.json not found")

        content = self._read_file_content(config_path)
        config = json.loads(content)

        assert "termMappings" in config, "Missing 'termMappings' section"
        assert "legacy_terms" in config["termMappings"], "Missing 'legacy_terms'"
        assert "ui_labels" in config["termMappings"], "Missing 'ui_labels'"
        assert "branding" in config, "Missing 'branding' section"
        assert "messages" in config, "Missing 'messages' section"

        messages = config["messages"]
        assert "success" in messages, "Missing success messages"
        assert "errors" in messages, "Missing error messages"
        assert "info" in messages, "Missing info messages"

    def test_message_config_service_loads(self):
        """
        Verify MessageConfig service loads and provides messages correctly.
        Validates: Requirements 4.1, 4.2
        """
        from src.config.message_config import MessageConfig

        config = MessageConfig()

        assert config.validate_config(), "MessageConfig validation failed"

        # Verify key messages exist and are non-empty
        assert config.get_success_message("profile_updated") != ""
        assert config.get_success_message("application_submitted") != ""
        assert config.get_error_message("authentication_failed") != ""

        # Verify no forbidden legacy terms in user-facing messages
        for key, msg in config.success_messages.items():
            for term in self.forbidden_legacy_terms:
                assert term not in msg, (
                    f"Forbidden term '{term}' in success message '{key}': {msg}"
                )

        for key, msg in config.error_messages.items():
            for term in self.forbidden_legacy_terms:
                assert term not in msg, (
                    f"Forbidden term '{term}' in error message '{key}': {msg}"
                )

    # ----------------------------------------------------------------
    # Layer 4: AI Content Generation (Requirements 5)
    # ----------------------------------------------------------------

    def test_ai_content_config_no_forbidden_legacy_terms(self):
        """
        Verify AI content config has no forbidden legacy terms.
        Validates: Requirements 5.1, 5.2, 5.3
        """
        from src.config.ai_content_config import AIContentConfig

        config = AIContentConfig()

        for key, prompt in config.questionnaire_prompts.items():
            for term in self.forbidden_legacy_terms:
                assert term not in prompt, (
                    f"Forbidden term '{term}' in questionnaire prompt '{key}'"
                )

        for key, template in config.recommendation_templates.items():
            for term in self.forbidden_legacy_terms:
                assert term not in template, (
                    f"Forbidden term '{term}' in recommendation template '{key}'"
                )

        for term in self.forbidden_legacy_terms:
            assert term not in config.business_title_context, (
                f"Forbidden term '{term}' in business title context"
            )

    def test_ai_content_config_validates(self):
        """
        Verify AI content config passes validation.
        Validates: Requirements 5.1, 5.2, 5.3
        """
        from src.config.ai_content_config import AIContentConfig

        config = AIContentConfig()
        assert config.validate_config(), "AIContentConfig validation failed"

    # ----------------------------------------------------------------
    # Layer 5: Logging (Requirements 4.3)
    # ----------------------------------------------------------------

    def test_log_templates_no_forbidden_legacy_terms(self):
        """
        Verify log message templates have no forbidden legacy terms.
        Validates: Requirements 4.3
        """
        from src.config.message_config import MessageConfig

        config = MessageConfig()

        for key, template in config.log_templates.items():
            for term in self.forbidden_legacy_terms:
                assert term not in template, (
                    f"Forbidden term '{term}' in log template '{key}': {template}"
                )

    def test_branding_logger_no_forbidden_terms(self):
        """
        Verify BrandingLogger source has no forbidden legacy terms.
        Validates: Requirements 4.3
        """
        logger_path = self.backend_src / "utils" / "branding_logger.py"
        if not logger_path.exists():
            pytest.skip("branding_logger.py not found")

        content = self._read_file_content(logger_path)
        for term in self.forbidden_legacy_terms:
            findings = self._find_forbidden_terms(content, term)
            assert not findings, (
                f"Forbidden term '{term}' found in branding_logger.py"
            )

    # ----------------------------------------------------------------
    # Layer 6: Cross-Layer User Journey (Requirements 1-3, 8)
    # ----------------------------------------------------------------

    def test_user_journey_registration_to_application(self):
        """
        Simulate the user journey from registration through application,
        verifying terminology consistency at each step.

        Journey: Sign Up → Dashboard → Questionnaire → Profile →
                 Recommendations → Application

        Validates: Requirements 1-3, 8.1
        """
        journey_files = {
            "1_signup": self.frontend_src / "components" / "auth" / "SignUpForm.tsx",
            "2_dashboard": self.frontend_src / "components" / "dashboard" / "Dashboard.tsx",
            "3_questionnaire": self.frontend_src / "components" / "questionnaire" / "Questionnaire.tsx",
            "4_profile": self.frontend_src / "components" / "profile" / "ProfileManagement.tsx",
            "5_recommendations": self.frontend_src / "components" / "recommendations" / "RecommendationsList.tsx",
            "6_application": self.frontend_src / "components" / "recommendations" / "ApplicationTracker.tsx",
        }

        journey_violations = {}

        for step, file_path in journey_files.items():
            if not file_path.exists():
                continue

            content = self._read_file_content(file_path)

            for term in self.forbidden_legacy_terms:
                findings = self._find_forbidden_terms(content, term)
                if findings:
                    if step not in journey_violations:
                        journey_violations[step] = []
                    for line_num, line in findings:
                        journey_violations[step].append(
                            f"Line {line_num}: '{term}' in: {line}"
                        )

        if journey_violations:
            msg = "User journey terminology violations:\n"
            for step, issues in journey_violations.items():
                msg += f"\n  Step {step}:\n"
                for issue in issues:
                    msg += f"    {issue}\n"
            pytest.fail(msg)

    def test_user_journey_search_flow(self):
        """
        Verify terminology consistency in the search user journey.

        Journey: Search Page → Search Results → Profile Modal → Contact

        Validates: Requirements 3.1, 3.2, 8.1
        """
        search_files = {
            "1_search": self.frontend_src / "components" / "public" / "PublicVeteranSearch.tsx",
            "2_results": self.frontend_src / "components" / "public" / "VeteranSearchCard.tsx",
            "3_profile_modal": self.frontend_src / "components" / "public" / "VeteranProfileModal.tsx",
            "4_contact": self.frontend_src / "components" / "public" / "ContactForm.tsx",
        }

        violations = {}

        for step, file_path in search_files.items():
            if not file_path.exists():
                continue

            content = self._read_file_content(file_path)

            for term in self.forbidden_legacy_terms:
                findings = self._find_forbidden_terms(content, term)
                if findings:
                    if step not in violations:
                        violations[step] = []
                    for line_num, line in findings:
                        violations[step].append(
                            f"Line {line_num}: '{term}' in: {line}"
                        )

        if violations:
            msg = "Search journey terminology violations:\n"
            for step, issues in violations.items():
                msg += f"\n  Step {step}:\n"
                for issue in issues:
                    msg += f"    {issue}\n"
            pytest.fail(msg)

    def test_backend_api_journey_consistency(self):
        """
        Verify terminology consistency across all backend API handlers
        that a user would interact with during their journey.

        Validates: Requirements 4.1, 4.2, 7.1
        """
        handler_files = {
            "auth": self.backend_src / "handlers" / "auth_handler.py",
            "profile": self.backend_src / "handlers" / "profile_handler.py",
            "questionnaire": self.backend_src / "handlers" / "questionnaire_handler.py",
            "matching": self.backend_src / "handlers" / "matching_handler.py",
            "application": self.backend_src / "handlers" / "application_handler.py",
            "business_title": self.backend_src / "handlers" / "business_title_handler.py",
            "public_search": self.backend_src / "handlers" / "public_search_handler.py",
            "contact": self.backend_src / "handlers" / "contact_handler.py",
        }

        violations = {}

        for handler_name, file_path in handler_files.items():
            if not file_path.exists():
                continue

            content = self._read_file_content(file_path)

            for term in self.forbidden_legacy_terms:
                findings = self._find_forbidden_terms(content, term)
                if findings:
                    if handler_name not in violations:
                        violations[handler_name] = []
                    for line_num, line in findings:
                        violations[handler_name].append(
                            f"Line {line_num}: '{term}' in: {line}"
                        )

        if violations:
            msg = "Backend API handler terminology violations:\n"
            for handler, issues in violations.items():
                msg += f"\n  {handler}_handler:\n"
                for issue in issues:
                    msg += f"    {issue}\n"
            pytest.fail(msg)

    # ----------------------------------------------------------------
    # Layer 7: Term Mapping Consistency (Requirements 6.3, 8.1)
    # ----------------------------------------------------------------

    def test_term_mapping_bidirectional_consistency(self):
        """
        Verify that term mappings in config files are consistent
        between frontend (JSON) and backend (Python) layers.

        Validates: Requirements 6.3, 8.1
        """
        json_config_path = self.backend_src / "config" / "term-mapping.json"
        if not json_config_path.exists():
            pytest.skip("term-mapping.json not found")

        json_content = self._read_file_content(json_config_path)
        json_config = json.loads(json_content)
        json_mappings = json_config.get("termMappings", {}).get("legacy_terms", {})

        from src.config.message_config import MessageConfig

        backend_config = MessageConfig()
        backend_mappings = backend_config.term_mappings

        # Verify all backend mappings exist in JSON config
        for legacy, new in backend_mappings.items():
            assert legacy in json_mappings, (
                f"Backend mapping '{legacy}' → '{new}' missing from JSON config"
            )
            assert json_mappings[legacy] == new, (
                f"Mapping mismatch for '{legacy}': "
                f"JSON='{json_mappings[legacy]}', Backend='{new}'"
            )

    def test_branding_utils_term_mappings_match_config(self):
        """
        Verify frontend brandingUtils TERM_MAPPINGS match the JSON config.

        Validates: Requirements 6.3, 8.1
        """
        branding_utils_path = self.frontend_src / "utils" / "brandingUtils.ts"
        if not branding_utils_path.exists():
            pytest.skip("brandingUtils.ts not found")

        content = self._read_file_content(branding_utils_path)

        json_config_path = self.backend_src / "config" / "term-mapping.json"
        if not json_config_path.exists():
            pytest.skip("term-mapping.json not found")

        json_content = self._read_file_content(json_config_path)
        json_config = json.loads(json_content)
        json_mappings = json_config.get("termMappings", {}).get("legacy_terms", {})

        # Verify key mappings from JSON config appear in brandingUtils
        key_mappings_to_check = [
            ("社内AI人材候補", json_mappings.get("ベテラン", "")),
            ("AIスキル棚卸し（セルフ診断）", json_mappings.get("問診", "")),
            ("AIスキルポートフォリオ", json_mappings.get("ベテランプロフィール", "")),
            ("AIポジション／プロジェクト レコメンド", json_mappings.get("推薦機会", "")),
            ("自薦応募", json_mappings.get("応募", "")),
            ("応募意向", json_mappings.get("興味表明", "")),
            ("社内AI人材候補検索", json_mappings.get("ベテラン検索", "")),
        ]

        for new_term, expected_value in key_mappings_to_check:
            assert new_term in content or expected_value in content, (
                f"Term '{new_term}' (or '{expected_value}') not found in brandingUtils.ts"
            )

    # ----------------------------------------------------------------
    # Layer 8: Full Stack Consistency (Requirements 7, 8)
    # ----------------------------------------------------------------

    def test_no_forbidden_terms_across_entire_codebase(self):
        """
        Comprehensive scan: verify no forbidden legacy terms exist
        in user-facing code across the entire source codebase.

        Validates: Requirements 7.3, 7.4, 8.1
        """
        scan_dirs = [
            (self.frontend_src / "components", ["*.tsx", "*.ts", "*.css"]),
            (self.frontend_src / "services", ["*.ts"]),
            (self.frontend_src / "utils", ["*.ts"]),
            (self.frontend_src / "contexts", ["*.tsx", "*.ts"]),
            (self.backend_src / "handlers", ["*.py"]),
            (self.backend_src / "services", ["*.py"]),
            (self.backend_src / "utils", ["*.py"]),
        ]

        all_violations = {}

        for scan_dir, patterns in scan_dirs:
            if not scan_dir.exists():
                continue

            for pattern in patterns:
                for file_path in scan_dir.rglob(pattern):
                    if self._should_exclude(file_path):
                        continue

                    content = self._read_file_content(file_path)
                    rel_path = str(file_path.relative_to(self.project_root))

                    for term in self.forbidden_legacy_terms:
                        findings = self._find_forbidden_terms(content, term)
                        if findings:
                            if rel_path not in all_violations:
                                all_violations[rel_path] = []
                            for line_num, line in findings:
                                all_violations[rel_path].append(
                                    f"Line {line_num}: '{term}'"
                                )

        if all_violations:
            msg = f"Forbidden legacy terms found in {len(all_violations)} files:\n"
            for path, issues in sorted(all_violations.items()):
                msg += f"\n  {path}: {len(issues)} occurrence(s)\n"
                for issue in issues[:3]:
                    msg += f"    {issue}\n"
                if len(issues) > 3:
                    msg += f"    ... and {len(issues) - 3} more\n"
            pytest.fail(msg)

    def test_message_tone_consistency(self):
        """
        Verify message tone is consistent across frontend and backend.
        Messages should use polite form (です/ます調) consistently.

        Validates: Requirements 6.1, 6.2
        """
        from src.config.message_config import MessageConfig

        config = MessageConfig()

        # Polite form endings in Japanese
        polite_endings = ["ました", "です", "ません", "います", "ください", "しょう"]

        for key, msg in config.success_messages.items():
            if any(c in msg for c in "あいうえおかきくけこ"):
                has_polite = any(ending in msg for ending in polite_endings)
                assert has_polite, (
                    f"Success message '{key}' may not use polite form: {msg}"
                )

        for key, msg in config.error_messages.items():
            if any(c in msg for c in "あいうえおかきくけこ"):
                has_polite = any(ending in msg for ending in polite_endings)
                assert has_polite, (
                    f"Error message '{key}' may not use polite form: {msg}"
                )

    def test_api_handler_entry_points_preserved(self):
        """
        Verify that API handler entry points are preserved after terminology update.
        Handlers should still export the expected callable functions.

        Validates: Requirements 7.1, 7.3
        """
        # Verify handler files exist and define expected entry points
        handler_files = {
            "auth_handler.py": "handler",
            "profile_handler.py": "handler",
            "matching_handler.py": "lambda_handler",
            "application_handler.py": "handler",
            "public_search_handler.py": "handler",
        }

        handlers_dir = self.backend_src / "handlers"
        for filename, entry_point in handler_files.items():
            file_path = handlers_dir / filename
            if not file_path.exists():
                continue
            content = self._read_file_content(file_path)
            assert f"def {entry_point}(" in content, (
                f"{filename} should define '{entry_point}' function"
            )

    def test_config_files_internal_consistency(self):
        """
        Verify that configuration files are internally consistent -
        success/error message keys referenced in handlers exist in config.

        Validates: Requirements 4.1, 4.2, 8.1
        """
        from src.config.message_config import MessageConfig

        config = MessageConfig()

        required_success_keys = [
            "profile_updated",
            "application_submitted",
            "questionnaire_completed",
            "authentication_success",
        ]

        required_error_keys = [
            "profile_validation_failed",
            "application_failed",
            "authentication_failed",
            "authorization_failed",
            "validation_error",
        ]

        for key in required_success_keys:
            msg = config.get_success_message(key)
            assert msg != f"Success: {key}", (
                f"Success message key '{key}' not found in config"
            )

        for key in required_error_keys:
            msg = config.get_error_message(key)
            assert msg != f"Error: {key}", (
                f"Error message key '{key}' not found in config"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
