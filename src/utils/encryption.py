"""
Encryption utilities for data protection at rest and in transit.
Handles PII data encryption and secure data handling.
"""

import base64
import hashlib
import logging
import os
from typing import Any, Dict, Union

import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self):
        self.kms_client = boto3.client("kms")
        self.kms_key_id = os.environ.get("KMS_KEY_ID", "alias/default-test-key")
        self._fernet_key = None

    def _get_fernet_key(self) -> Fernet:
        """Get or create Fernet encryption key using KMS."""
        if self._fernet_key is None:
            try:
                # Use KMS to generate/retrieve data encryption key
                response = self.kms_client.generate_data_key(
                    KeyId=self.kms_key_id, KeySpec="AES_256"
                )
                key = base64.urlsafe_b64encode(response["Plaintext"][:32])
                self._fernet_key = Fernet(key)
            except ClientError as e:
                logger.error(f"Failed to get KMS key: {e}")
                # Fallback to environment-based key for development
                password = os.environ.get(
                    "ENCRYPTION_PASSWORD", "default-dev-key"
                ).encode()
                salt = os.environ.get("ENCRYPTION_SALT", "default-salt").encode()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                self._fernet_key = Fernet(key)

        return self._fernet_key

    def encrypt_data(self, data: Union[str, Dict[str, Any]]) -> str:
        """Encrypt sensitive data."""
        try:
            if isinstance(data, dict):
                data = str(data)

            fernet = self._get_fernet_key()
            encrypted_data = fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            fernet = self._get_fernet_key()
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def hash_pii(self, pii_data: str) -> str:
        """Create irreversible hash of PII data for indexing."""
        salt = os.environ.get("PII_HASH_SALT", "default-pii-salt").encode()
        return hashlib.pbkdf2_hmac("sha256", pii_data.encode(), salt, 100000).hex()


class PIIProtectionService:
    """Service for protecting Personally Identifiable Information."""

    # Define PII field patterns
    PII_FIELDS = {
        "email",
        "phone",
        "address",
        "ssn",
        "employee_id",
        "full_name",
        "birth_date",
        "personal_phone",
        "home_address",
    }

    SENSITIVE_FIELDS = {
        "salary",
        "performance_rating",
        "medical_info",
        "emergency_contact",
    }

    def __init__(self):
        self.encryption_service = EncryptionService()

    def protect_pii_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt PII fields in data dictionary."""
        protected_data = data.copy()

        for field, value in data.items():
            if self._is_pii_field(field) and value:
                try:
                    protected_data[field] = self.encryption_service.encrypt_data(
                        str(value)
                    )
                    protected_data[f"{field}_encrypted"] = True
                except Exception as e:
                    logger.error(f"Failed to encrypt PII field {field}: {e}")
                    # Don't store unencrypted PII
                    protected_data[field] = "[ENCRYPTION_FAILED]"

        return protected_data

    def unprotect_pii_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt PII fields in data dictionary."""
        unprotected_data = data.copy()

        for field, value in data.items():
            if field.endswith("_encrypted") and value:
                original_field = field.replace("_encrypted", "")
                if original_field in data:
                    try:
                        unprotected_data[
                            original_field
                        ] = self.encryption_service.decrypt_data(data[original_field])
                        del unprotected_data[field]  # Remove encryption flag
                    except Exception as e:
                        logger.error(
                            f"Failed to decrypt PII field {original_field}: {e}"
                        )
                        unprotected_data[original_field] = "[DECRYPTION_FAILED]"

        return unprotected_data

    def anonymize_for_public(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or anonymize PII for public display."""
        public_data = {}

        for field, value in data.items():
            if self._is_pii_field(field):
                if field == "email":
                    # Partially mask email
                    public_data[field] = self._mask_email(str(value))
                elif field == "phone":
                    # Partially mask phone
                    public_data[field] = self._mask_phone(str(value))
                elif field == "full_name":
                    # Show only first name and last initial
                    public_data[field] = self._mask_name(str(value))
                # Skip other PII fields for public view
            elif not self._is_sensitive_field(field):
                public_data[field] = value

        return public_data

    def _is_pii_field(self, field_name: str) -> bool:
        """Check if field contains PII data."""
        field_lower = field_name.lower()
        return any(pii_field in field_lower for pii_field in self.PII_FIELDS)

    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if field contains sensitive data."""
        field_lower = field_name.lower()
        return any(
            sensitive_field in field_lower for sensitive_field in self.SENSITIVE_FIELDS
        )

    def _mask_email(self, email: str) -> str:
        """Partially mask email address."""
        if "@" not in email:
            return email[:2] + "*" * (len(email) - 2)

        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = local[0] + "*"
        elif len(local) <= 4:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        else:
            # For longer emails, use fixed number of asterisks
            masked_local = local[0] + "***" + local[-1]

        return f"{masked_local}@{domain}"

    def _mask_phone(self, phone: str) -> str:
        """Partially mask phone number."""
        digits_only = "".join(filter(str.isdigit, phone))
        if len(digits_only) >= 4:
            # Use fixed 4 asterisks for consistency
            return "****" + digits_only[-4:]
        return "*" * len(phone)

    def _mask_name(self, name: str) -> str:
        """Show only first name and last initial."""
        parts = name.strip().split()
        if len(parts) == 1:
            return parts[0]
        elif len(parts) >= 2:
            return f"{parts[0]} {parts[-1][0]}."
        return name


# Global instances
encryption_service = EncryptionService()
pii_protection_service = PIIProtectionService()
