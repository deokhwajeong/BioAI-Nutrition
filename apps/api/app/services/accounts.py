"""Accounts: password hashing, bearer tokens, and full deletion of a user's data.

Passwords are hashed with scrypt (RFC 7914) from the standard library, with a random
16-byte salt per password and the parameters stored next to the hash so they can be raised
later without breaking existing accounts. Tokens are 32 random bytes (URL-safe); only their
SHA-256 digest is stored, so a database leak does not leak usable tokens.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from ..models.database import (
    Account,
    AuthToken,
    BiomarkerReading,
    ConsentAuditLog,
    Event,
    GeneticProfile,
    NutrientBudgetSnapshot,
    PersonalBaseline,
    User,
    UserTarget,
)

# scrypt cost: N=2^14, r=8, p=1 uses 16 MiB and takes tens of milliseconds, the
# interactive-login setting from the scrypt paper.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
TOKEN_TTL = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    candidate = hashlib.scrypt(
        password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=32
    )
    return hmac.compare_digest(candidate, _unb64(digest))


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_account_id() -> str:
    return "usr_" + secrets.token_hex(8)


def issue_token(db: Session, account: Account) -> tuple[str, datetime]:
    """Create a bearer token for ``account``; returns (token, expires_at)."""
    token = secrets.token_urlsafe(32)
    expires_at = _now() + TOKEN_TTL
    db.add(AuthToken(token_hash=_token_digest(token), account_id=account.id, expires_at=expires_at))
    db.commit()
    return token, expires_at


def account_for_token(db: Session, token: str) -> Account | None:
    row = db.get(AuthToken, _token_digest(token))
    if row is None:
        return None
    if row.expires_at <= _now():
        db.delete(row)
        db.commit()
        return None
    return row.account


def revoke_token(db: Session, token: str) -> None:
    row = db.get(AuthToken, _token_digest(token))
    if row is not None:
        db.delete(row)
        db.commit()


# Tables keyed by a plain user_id column (no foreign key to accounts).
_USER_ID_TABLES = (
    Event,
    UserTarget,
    BiomarkerReading,
    PersonalBaseline,
    GeneticProfile,
    ConsentAuditLog,
    NutrientBudgetSnapshot,
)


def delete_account_data(
    db: Session,
    account: Account,
    purge_runtime: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Delete the account and every stored row that belongs to it; returns counts per table.

    ``purge_runtime`` clears the in-process engine state (readings, consent, budgets) for the
    same user id. Nothing about the user is kept, including the consent audit trail: this is
    an erasure, not a deactivation.
    """
    user_id = account.id
    counts: dict[str, int] = {
        "daily_logs": len(account.daily_logs),
        "consents": len(account.consents),
        "tokens": len(account.tokens),
    }
    for model in _USER_ID_TABLES:
        counts[model.__tablename__] = (
            db.query(model).filter(model.user_id == user_id).delete(synchronize_session=False)
        )
    counts["users"] = db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.delete(account)  # cascades to tokens, consents, daily logs
    db.commit()
    if purge_runtime is not None:
        purge_runtime(user_id)
    return counts
