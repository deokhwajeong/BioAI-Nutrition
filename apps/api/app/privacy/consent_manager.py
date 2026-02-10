"""
Dynamic Consent Manager.

Manages fine-grained, revocable consent for health data sharing.
When consent is revoked, associated graph edges are severed in real-time.

Patent-relevant: The real-time consent propagation that instantly affects
the data processing pipeline (edges disappear from the health graph,
cached calculations are invalidated) is the inventive step.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class ConsentScope(str, Enum):
    """Granular data categories that can be independently consented."""

    GLUCOSE_DATA = "glucose_data"
    ACTIVITY_DATA = "activity_data"
    SLEEP_DATA = "sleep_data"
    GENETIC_DATA = "genetic_data"
    MEAL_DATA = "meal_data"
    MEDICATION_DATA = "medication_data"
    WEIGHT_DATA = "weight_data"
    HEART_RATE_DATA = "heart_rate_data"

    # Derived data
    METABOLIC_STATE = "metabolic_state"
    NUTRIENT_BUDGET = "nutrient_budget"
    RECOMMENDATIONS = "recommendations"

    # Sharing scopes
    HOUSEHOLD_SHARING = "household_sharing"
    RESEARCH_SHARING = "research_sharing"
    PROVIDER_SHARING = "provider_sharing"


class ConsentAction(str, Enum):
    GRANTED = "granted"
    REVOKED = "revoked"


@dataclass
class ConsentRecord:
    """A single consent decision with full audit metadata."""

    user_id: str
    scope: ConsentScope
    action: ConsentAction
    timestamp: datetime
    expires_at: Optional[datetime] = None
    reason: str = ""
    ip_hash: str = ""  # Hashed IP for audit without PII
    consent_version: str = "1.0"

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


@dataclass
class ConsentState:
    """Current consent state for a user — all active scopes."""

    user_id: str
    granted_scopes: Set[ConsentScope] = field(default_factory=set)
    revoked_scopes: Set[ConsentScope] = field(default_factory=set)
    last_updated: Optional[datetime] = None

    def is_granted(self, scope: ConsentScope) -> bool:
        """Check if a specific scope is currently consented."""
        return scope in self.granted_scopes and scope not in self.revoked_scopes

    def get_allowed_biomarkers(self) -> Set[str]:
        """Map consent scopes to allowed biomarker types."""
        scope_to_biomarkers = {
            ConsentScope.GLUCOSE_DATA: {"glucose"},
            ConsentScope.ACTIVITY_DATA: {"steps", "exercise", "activity_calories"},
            ConsentScope.SLEEP_DATA: {"sleep"},
            ConsentScope.GENETIC_DATA: {"genotype"},
            ConsentScope.HEART_RATE_DATA: {"heart_rate", "hrv"},
            ConsentScope.MEAL_DATA: {"meal"},
            ConsentScope.WEIGHT_DATA: {"weight"},
        }

        allowed: Set[str] = set()
        for scope in self.granted_scopes:
            if scope not in self.revoked_scopes:
                allowed.update(scope_to_biomarkers.get(scope, set()))
        return allowed


class DynamicConsentManager:
    """Manages real-time consent with propagation to the data pipeline.

    Patent-relevant: When consent is revoked:
    1. The consent state is updated immediately
    2. Registered revocation callbacks are fired
    3. Graph edges connected to the revoked data are severed
    4. Cached computations using revoked data are invalidated
    5. An audit log entry is created

    This ensures that revoked data stops affecting recommendations
    within the same request cycle — not eventually, but immediately.
    """

    def __init__(self):
        self._states: Dict[str, ConsentState] = {}
        self._audit_log: List[ConsentRecord] = []
        self._revocation_callbacks: List[
            Callable[[str, ConsentScope], None]
        ] = []

    def register_revocation_callback(
        self, callback: Callable[[str, ConsentScope], None]
    ) -> None:
        """Register a callback to fire when consent is revoked.

        Used by the graph engine, cache layer, and recommendation
        engine to react to consent changes in real-time.
        """
        self._revocation_callbacks.append(callback)

    def grant_consent(
        self,
        user_id: str,
        scope: ConsentScope,
        reason: str = "",
        expires_at: Optional[datetime] = None,
    ) -> ConsentRecord:
        """Grant consent for a specific data scope."""
        state = self._get_or_create_state(user_id)
        state.granted_scopes.add(scope)
        state.revoked_scopes.discard(scope)
        state.last_updated = datetime.utcnow()

        record = ConsentRecord(
            user_id=user_id,
            scope=scope,
            action=ConsentAction.GRANTED,
            timestamp=datetime.utcnow(),
            expires_at=expires_at,
            reason=reason,
        )
        self._audit_log.append(record)
        return record

    def revoke_consent(
        self,
        user_id: str,
        scope: ConsentScope,
        reason: str = "",
    ) -> ConsentRecord:
        """Revoke consent for a specific data scope.

        This triggers immediate propagation via registered callbacks.
        """
        state = self._get_or_create_state(user_id)
        state.revoked_scopes.add(scope)
        state.granted_scopes.discard(scope)
        state.last_updated = datetime.utcnow()

        record = ConsentRecord(
            user_id=user_id,
            scope=scope,
            action=ConsentAction.REVOKED,
            timestamp=datetime.utcnow(),
            reason=reason,
        )
        self._audit_log.append(record)

        # Fire revocation callbacks for real-time propagation
        for callback in self._revocation_callbacks:
            try:
                callback(user_id, scope)
            except Exception:
                pass  # Don't let callback failures block revocation

        return record

    def check_consent(self, user_id: str, scope: ConsentScope) -> bool:
        """Check if a user has granted consent for a scope."""
        state = self._states.get(user_id)
        if state is None:
            return False

        # Check for expiry
        self._check_expiry(user_id, scope)

        return state.is_granted(scope)

    def get_consent_state(self, user_id: str) -> ConsentState:
        """Get the full consent state for a user."""
        return self._get_or_create_state(user_id)

    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        scope: Optional[ConsentScope] = None,
    ) -> List[ConsentRecord]:
        """Retrieve consent audit log with optional filters."""
        records = self._audit_log
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        if scope:
            records = [r for r in records if r.scope == scope]
        return records

    def filter_data_by_consent(
        self,
        user_id: str,
        data: Dict[str, Any],
        scope_mapping: Dict[str, ConsentScope],
    ) -> Dict[str, Any]:
        """Filter a data dictionary to only include consented fields.

        Patent-relevant: This is called at every pipeline stage to ensure
        revoked data doesn't leak into computations.
        """
        state = self._get_or_create_state(user_id)
        filtered: Dict[str, Any] = {}

        for key, value in data.items():
            scope = scope_mapping.get(key)
            if scope is None:
                # No consent requirement for this field
                filtered[key] = value
            elif state.is_granted(scope):
                filtered[key] = value
            # Else: field is silently dropped

        return filtered

    def _get_or_create_state(self, user_id: str) -> ConsentState:
        if user_id not in self._states:
            self._states[user_id] = ConsentState(user_id=user_id)
        return self._states[user_id]

    def _check_expiry(self, user_id: str, scope: ConsentScope) -> None:
        """Check and process expired consent records."""
        grants = [
            r
            for r in self._audit_log
            if r.user_id == user_id
            and r.scope == scope
            and r.action == ConsentAction.GRANTED
        ]
        for grant in grants:
            if grant.is_expired:
                # Auto-revoke expired consent
                self.revoke_consent(
                    user_id, scope, reason="Consent expired automatically"
                )
