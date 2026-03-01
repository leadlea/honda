"""
Performance Impact Tests for Branding Updates
ブランディング更新パフォーマンス影響確認テスト

Verifies that branding configuration updates do not negatively impact system performance.
ブランディング設定更新がシステムパフォーマンスに悪影響を与えないことを検証します。

要件: 7.3 - すべての機能的動作を維持する
"""

import time
import pytest

from src.config.message_config import MessageConfig
from src.config.ai_content_config import AIContentConfig
from src.utils.branding_logger import BrandingLogger


class TestMessageConfigPerformance:
    """MessageConfig service performance tests."""

    def test_initialization_time(self):
        """MessageConfig initialization should complete within 100ms."""
        start = time.perf_counter()
        config = MessageConfig()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert config is not None
        assert elapsed_ms < 100, f"MessageConfig init took {elapsed_ms:.2f}ms, expected < 100ms"

    def test_get_message_retrieval_time(self):
        """Message retrieval should complete within 5ms per call."""
        config = MessageConfig()

        keys_and_types = [
            ("profile_updated", "success"),
            ("application_failed", "error"),
            ("welcome_message", "info"),
            ("authentication_failed", "error"),
            ("questionnaire_completed", "success"),
        ]

        for key, msg_type in keys_and_types:
            start = time.perf_counter()
            result = config.get_message(key, msg_type)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert result  # non-empty
            assert elapsed_ms < 5, (
                f"get_message('{key}', '{msg_type}') took {elapsed_ms:.2f}ms, expected < 5ms"
            )

    def test_format_log_message_time(self):
        """Log message formatting should complete within 5ms per call."""
        config = MessageConfig()

        templates = [
            ("user_login", {"user_id": "u-001"}),
            ("application_submitted", {"user_id": "u-001", "opportunity_id": "o-001"}),
            ("search_performed", {"query": "AI engineer"}),
            ("error_occurred", {"error_type": "ValidationError", "message": "invalid"}),
        ]

        for template_key, kwargs in templates:
            start = time.perf_counter()
            result = config.format_log_message(template_key, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert result
            assert elapsed_ms < 5, (
                f"format_log_message('{template_key}') took {elapsed_ms:.2f}ms, expected < 5ms"
            )

    def test_map_legacy_term_time(self):
        """Term mapping lookups should complete within 5ms per call."""
        config = MessageConfig()

        for term in list(config.term_mappings.keys())[:5]:
            start = time.perf_counter()
            result = config.map_legacy_term(term)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert result
            assert elapsed_ms < 5, (
                f"map_legacy_term('{term}') took {elapsed_ms:.2f}ms, expected < 5ms"
            )

    def test_bulk_message_retrieval_time(self):
        """Retrieving 100 messages should complete within 100ms total."""
        config = MessageConfig()
        keys = list(config.success_messages.keys()) + list(config.error_messages.keys())

        start = time.perf_counter()
        for _ in range(100):
            for key in keys[:3]:
                config.get_message(key, "success")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, (
            f"100 bulk message retrievals took {elapsed_ms:.2f}ms, expected < 100ms"
        )


class TestAIContentConfigPerformance:
    """AIContentConfig service performance tests."""

    def test_initialization_time(self):
        """AIContentConfig initialization should complete within 100ms."""
        start = time.perf_counter()
        config = AIContentConfig()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert config is not None
        assert elapsed_ms < 100, f"AIContentConfig init took {elapsed_ms:.2f}ms, expected < 100ms"

    def test_get_questionnaire_prompt_time(self):
        """Questionnaire prompt retrieval should complete within 5ms."""
        config = AIContentConfig()

        for prompt_type in ["system_prompt", "context_prompt", "fallback_prompt"]:
            start = time.perf_counter()
            result = config.get_questionnaire_prompt(prompt_type)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert result
            assert elapsed_ms < 5, (
                f"get_questionnaire_prompt('{prompt_type}') took {elapsed_ms:.2f}ms, expected < 5ms"
            )

    def test_get_recommendation_template_time(self):
        """Recommendation template retrieval should complete within 5ms."""
        config = AIContentConfig()

        for tpl_type in ["match_reason_template", "system_context", "tone_instruction"]:
            start = time.perf_counter()
            result = config.get_recommendation_template(tpl_type)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert result
            assert elapsed_ms < 5, (
                f"get_recommendation_template('{tpl_type}') took {elapsed_ms:.2f}ms, expected < 5ms"
            )

    def test_apply_branding_context_time(self):
        """Branding context application should complete within 5ms."""
        config = AIContentConfig()
        sample_text = "社内AI人材候補がAIスキル棚卸し（セルフ診断）を完了し、AIポジション／プロジェクト レコメンドを確認しました。自薦応募を検討中です。"

        start = time.perf_counter()
        result = config.apply_branding_context(sample_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result
        assert elapsed_ms < 5, (
            f"apply_branding_context took {elapsed_ms:.2f}ms, expected < 5ms"
        )


class TestBrandingLoggerPerformance:
    """BrandingLogger performance tests."""

    def test_initialization_time(self):
        """BrandingLogger initialization should complete within 100ms."""
        start = time.perf_counter()
        logger = BrandingLogger("perf_test")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert logger is not None
        assert elapsed_ms < 100, f"BrandingLogger init took {elapsed_ms:.2f}ms, expected < 100ms"

    def test_log_operations_time(self):
        """Individual log operations should complete within 10ms each."""
        logger = BrandingLogger("perf_test")

        operations = [
            ("log_user_login", {"user_id": "u-001"}),
            ("log_profile_updated", {"user_id": "u-001"}),
            ("log_questionnaire_completed", {"user_id": "u-001"}),
            ("log_recommendation_generated", {"user_id": "u-001"}),
            ("log_search_performed", {"query": "AI engineer"}),
        ]

        for method_name, kwargs in operations:
            method = getattr(logger, method_name)
            start = time.perf_counter()
            method(**kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert elapsed_ms < 10, (
                f"{method_name} took {elapsed_ms:.2f}ms, expected < 10ms"
            )


class TestJSONConfigLoadingPerformance:
    """JSON configuration file loading performance tests."""

    def test_term_mapping_json_load_time(self):
        """term-mapping.json loading via MessageConfig should complete within 100ms."""
        start = time.perf_counter()
        config = MessageConfig()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify data was loaded from JSON
        assert len(config.term_mappings) > 0
        assert len(config.success_messages) > 0
        assert len(config.error_messages) > 0
        assert elapsed_ms < 100, (
            f"JSON config loading took {elapsed_ms:.2f}ms, expected < 100ms"
        )

    def test_repeated_initialization_consistency(self):
        """Multiple initializations should have consistent performance."""
        times = []
        for _ in range(5):
            start = time.perf_counter()
            MessageConfig()
            times.append((time.perf_counter() - start) * 1000)

        avg_ms = sum(times) / len(times)
        max_ms = max(times)

        assert avg_ms < 100, f"Average init time {avg_ms:.2f}ms, expected < 100ms"
        assert max_ms < 200, f"Max init time {max_ms:.2f}ms, expected < 200ms"
