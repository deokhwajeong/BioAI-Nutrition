"""
services/privacy.py

Provides helpers for privacy and PII handling.
"""

import hashlib
import logging
import re
from typing import Any

class PIIFilter(logging.Filter):
    """
    Logging filter that masks personally identifiable information (PII) such as emails
    and phone numbers in log messages. This is a best-effort approach and may need
    to be extended based on application-specific data formats.
    """

    email_pattern = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")
    phone_pattern = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._mask_pii(str(record.msg))
        if record.args:
            record.args = tuple(self._mask_pii(str(a)) for a in record.args)
        return True

    def _mask_pii(self, value: str) -> str:
        value = self.email_pattern.sub("<email>", value)
        value = self.phone_pattern.sub("<phone>", value)
        return value

def hash_identifier(identifier: str, pepper: str) -> str:
    """
    Hashes a user identifier together with a secret pepper to create a
    pseudonymous string. The same identifier+pepper combination will always
    produce the same hash, but without the pepper the hash cannot be reversed.
    """
    hasher = hashlib.sha256()
    hasher.update((identifier + pepper).encode("utf-8"))
    return hasher.hexdigest()
