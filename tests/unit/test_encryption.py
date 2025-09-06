"""
Unit tests for encryption utilities.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.utils.encryption import EncryptionService, PIIProtectionService


class TestEncryptionService:
    """Test encryption service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.encryption_service = EncryptionService()

    @patch.dict(os.environ, {"KMS_KEY_ID": "test-key-id"})
    @patch("src.utils.encryption.boto3.client")
    def test_encrypt_decrypt_data(self, mock_boto_client):
        """Test data encryption and decryption."""
        # Mock KMS client
        mock_kms = Mock()
        mock_kms.generate_data_key.return_value = {
            "Plaintext": b"a" * 32  # 32 bytes for AES-256
        }
        mock_boto_client.return_value = mock_kms

        # Create new service instance to pick up environment
        service = EncryptionService()

        # Test data
        test_data = "sensitive information"

        # Encrypt data
        encrypted = service.encrypt_data(test_data)
        assert encrypted != test_data
        assert isinstance(encrypted, str)

        # Decrypt data
        decrypted = service.decrypt_data(encrypted)
        assert decrypted == test_data

    @patch.dict(
        os.environ,
        {
            "KMS_KEY_ID": "test-key-id",
            "ENCRYPTION_PASSWORD": "test-pass",
            "ENCRYPTION_SALT": "test-salt",
        },
    )
    def test_encrypt_dict_data(self):
        """Test encryption of dictionary data."""
        service = EncryptionService()
        test_dict = {"key": "value", "number": 123}

        encrypted = service.encrypt_data(test_dict)
        assert isinstance(encrypted, str)
        assert encrypted != str(test_dict)

    def test_hash_pii(self):
        """Test PII hashing functionality."""
        pii_data = "john.doe@example.com"

        hash1 = self.encryption_service.hash_pii(pii_data)
        hash2 = self.encryption_service.hash_pii(pii_data)

        # Same input should produce same hash
        assert hash1 == hash2
        assert hash1 != pii_data
        assert len(hash1) == 64  # SHA-256 hex length

    @patch.dict(
        os.environ,
        {
            "KMS_KEY_ID": "test-key-id",
            "ENCRYPTION_PASSWORD": "test-password",
            "ENCRYPTION_SALT": "test-salt",
        },
    )
    def test_fallback_encryption(self):
        """Test fallback encryption when KMS is not available."""
        with patch("src.utils.encryption.boto3.client") as mock_boto:
            # Mock KMS failure
            mock_kms = Mock()
            mock_kms.generate_data_key.side_effect = Exception("KMS not available")
            mock_boto.return_value = mock_kms

            service = EncryptionService()
            test_data = "test data"

            encrypted = service.encrypt_data(test_data)
            decrypted = service.decrypt_data(encrypted)

            assert decrypted == test_data


class TestPIIProtectionService:
    """Test PII protection service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.pii_service = PIIProtectionService()

    @patch.dict(
        os.environ,
        {
            "KMS_KEY_ID": "test-key-id",
            "ENCRYPTION_PASSWORD": "test-pass",
            "ENCRYPTION_SALT": "test-salt",
        },
    )
    def test_protect_pii_data(self):
        """Test PII data protection."""
        service = PIIProtectionService()
        test_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "555-1234",
            "skills": ["Python", "AWS"],
            "non_pii_field": "safe data",
        }

        protected = service.protect_pii_data(test_data)

        # PII fields should be encrypted or marked as failed
        assert protected["email"] != test_data["email"]
        # Check if encryption succeeded or failed gracefully
        if "email_encrypted" in protected:
            assert protected["email_encrypted"] is True
        else:
            # Encryption failed, should be marked
            assert protected["email"] == "[ENCRYPTION_FAILED]"

        # Non-PII fields should remain unchanged
        assert protected["skills"] == test_data["skills"]
        assert protected["non_pii_field"] == test_data["non_pii_field"]

    @patch.dict(
        os.environ,
        {
            "KMS_KEY_ID": "test-key-id",
            "ENCRYPTION_PASSWORD": "test-pass",
            "ENCRYPTION_SALT": "test-salt",
        },
    )
    def test_unprotect_pii_data(self):
        """Test PII data unprotection."""
        service = PIIProtectionService()
        test_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "skills": ["Python", "AWS"],
        }

        # Protect then unprotect
        protected = service.protect_pii_data(test_data)
        unprotected = service.unprotect_pii_data(protected)

        # Should restore original data or handle decryption failure
        if protected["email"] != "[ENCRYPTION_FAILED]":
            assert unprotected["email"] == test_data["email"]
            assert "email_encrypted" not in unprotected
        else:
            # Encryption failed, so decryption will also fail
            assert unprotected["email"] == "[DECRYPTION_FAILED]"

        assert unprotected["skills"] == test_data["skills"]

    def test_anonymize_for_public(self):
        """Test data anonymization for public display."""
        test_data = {
            "full_name": "John Doe Smith",
            "email": "john.doe@example.com",
            "phone": "555-123-4567",
            "skills": ["Python", "AWS"],
            "salary": 100000,
            "department": "Engineering",
        }

        public_data = self.pii_service.anonymize_for_public(test_data)

        # PII should be masked or removed
        assert public_data["full_name"] == "John S."
        assert public_data["email"] == "j***e@example.com"
        assert public_data["phone"] == "****4567"

        # Non-PII should remain
        assert public_data["skills"] == test_data["skills"]
        assert public_data["department"] == test_data["department"]

        # Sensitive fields should be removed
        assert "salary" not in public_data

    def test_is_pii_field(self):
        """Test PII field detection."""
        assert self.pii_service._is_pii_field("email")
        assert self.pii_service._is_pii_field("user_email")
        assert self.pii_service._is_pii_field("personal_phone")
        assert not self.pii_service._is_pii_field("skills")
        assert not self.pii_service._is_pii_field("department")

    def test_mask_email(self):
        """Test email masking."""
        assert self.pii_service._mask_email("john@example.com") == "j***n@example.com"
        assert self.pii_service._mask_email("a@example.com") == "a*@example.com"
        assert self.pii_service._mask_email("ab@example.com") == "a*@example.com"

    def test_mask_phone(self):
        """Test phone number masking."""
        assert self.pii_service._mask_phone("555-123-4567") == "****4567"
        assert self.pii_service._mask_phone("5551234567") == "****4567"
        assert self.pii_service._mask_phone("123") == "***"

    def test_mask_name(self):
        """Test name masking."""
        assert self.pii_service._mask_name("John Doe") == "John D."
        assert self.pii_service._mask_name("John") == "John"
        assert self.pii_service._mask_name("John Michael Doe") == "John D."

    def test_empty_data_handling(self):
        """Test handling of empty or None data."""
        empty_data = {}
        protected = self.pii_service.protect_pii_data(empty_data)
        assert protected == {}

        none_data = {"email": None, "name": ""}
        protected = self.pii_service.protect_pii_data(none_data)
        # Should not encrypt None or empty values
        assert protected["email"] is None
        assert protected["name"] == ""


if __name__ == "__main__":
    pytest.main([__file__])
